"""Opt-in final paused PIE handoff; never launches PIE or saves assets/config."""
import builtins
import datetime
import hashlib
import json
import time
from pathlib import Path
import unreal as u

KEY = '_combat_final_handoff'
KEYS = ('W', 'A', 'S', 'D', 'LeftMouseButton', 'RightMouseButton', 'LeftShift', 'SpaceBar', 'P', 'Q', 'R')
SETTINGS = {'sg.'+name+'Quality': 2 for name in ('ViewDistance', 'AntiAliasing', 'Shadow', 'GlobalIllumination',
    'Reflection', 'PostProcess', 'Texture', 'Effects', 'Foliage', 'Shading')}
SETTINGS.update({'sg.ResolutionQuality': 100, 'r.ScreenPercentage': 100, 'r.VSync': 0,
                 'r.MotionBlurQuality': 0, 'r.Streaming.PoolSize': 2048, 't.MaxFPS': 60})


def active_others(owner=None):
    return [k for k, v in vars(builtins).items() if k.startswith('_combat_') and v is not owner and getattr(v, 'handle', None) is not None]


class Handoff:
    def __init__(self):
        self.handle = self.pc = self.world = None
        self.finished = False
        self.phase, self.at = 'setup', time.monotonic()
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / ('FinalHandoff_'+stamp+'.json')
        self.report = {'status': 'running', 'started_utc': stamp, 'errors': [], 'assertions': [],
                       'scope': 'Paused final PIE handoff; screenshot is not performance evidence'}

    def check(self, name, passed, detail=None):
        self.report['assertions'].append({'name': name, 'pass': bool(passed), 'detail': detail})
        if not passed:
            raise AssertionError(name+': '+str(detail))

    def release(self):
        if self.pc and u.SystemLibrary.is_valid(self.pc):
            for key in KEYS:
                try:
                    u.CombatEditorLibrary.inject_player_key(self.pc, key, False)
                except Exception as exc:
                    self.report['errors'].append('release '+key+': '+str(exc))

    def conditions(self):
        names = ('mass.FullyParallel', 'stats.AutoEnableNamedEventsWhenProfiling', 'r.GPUCsvStatsEnabled')
        values = {n: u.SystemLibrary.get_console_variable_int_value(n) for n in names}
        self.check('instrumentation_and_mass', not u.TraceUtilLibrary.is_tracing() and all(v == 0 for v in values.values()), values)
        return values

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error:
            self.report['errors'].append(str(error))
        self.release()
        try:
            if self.world and u.SystemLibrary.is_valid(self.world):
                u.GameplayStatics.set_game_paused(self.world, True)
        except Exception as exc:
            self.report['errors'].append('keep_paused: '+str(exc))
        finally:
            if self.handle is not None:
                try:
                    u.unregister_slate_post_tick_callback(self.handle)
                except Exception as exc:
                    self.report['errors'].append('callback_unregister: '+str(exc))
                else:
                    self.handle = None
        self.report['active_project_callbacks_after_unregister'] = active_others()
        if self.report['active_project_callbacks_after_unregister']:
            self.report['errors'].append('Unexpected active project callback')
        self.phase = self.report['status'] = 'failed' if self.report['errors'] else 'passed'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open('x', encoding='utf-8') as stream:
                json.dump(self.report, stream, ensure_ascii=False, indent=2)
        except Exception as exc:
            self.phase = self.report['status'] = 'failed'
            self.report['errors'].append('report_write: '+str(exc))
            u.log_error(str(self.report['errors']))
        print('FINAL_HANDOFF', self.phase, str(self.path))

    def tick(self, delta):
        if self.finished: return  # A failed unregister must never rerun setup.
        try:
            if time.monotonic()-self.at > 20:
                raise TimeoutError('Handoff phase timeout: '+self.phase)
            if self.phase == 'setup':
                self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
                self.check('existing_pie', bool(self.world))
                people = u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatCharacter)
                self.check('two_characters', len(people) == 2)
                self.player = next(a for a in people if not a.is_boss)
                self.boss = next(a for a in people if a.is_boss)
                self.pc = self.player.get_controller()
                self.check('viewport_1080p', tuple(self.pc.get_viewport_size()) == (1920, 1080))
                self.report['conditions_before'] = self.conditions()
                self.release()
                if u.GameplayStatics.is_game_paused(self.world):
                    u.GameplayStatics.set_game_paused(self.world, False)
                for actor in people:
                    actor.reset_combat_state()
                self.pc.set_control_rotation(u.Rotator(pitch=-12, yaw=0))
                for name, value in SETTINGS.items():
                    u.SystemLibrary.execute_console_command(self.world, name+' '+str(value))
                u.CombatEditorLibrary.inject_player_key(self.pc, 'P', True)
                self.phase, self.at = 'observe_pause', time.monotonic()
            elif self.phase == 'observe_pause':
                if not u.GameplayStatics.is_game_paused(self.world):
                    return
                self.release()  # P release occurs on a later Slate callback.
                self.phase, self.at = 'hud_wait', time.monotonic()
            elif self.phase == 'hud_wait' and time.monotonic()-self.at >= .3:
                self.report['settings'] = {n: u.SystemLibrary.get_console_variable_float_value(n) for n in SETTINGS}
                self.check('high_readback', all(abs(self.report['settings'][n]-v) < .01 for n, v in SETTINGS.items()))
                self.report['conditions_final'] = self.conditions()
                self.check('normal_global_speed', abs(u.GameplayStatics.get_global_time_dilation(self.world)-1) < .001)
                self.report['actors'] = [{'boss': a.is_boss, 'health': a.get_health(), 'busy': a.is_busy(),
                    'active_skill': str(a.get_active_skill_tag().get_editor_property('tag_name'))} for a in (self.player, self.boss)]
                self.check('full_health_idle', self.player.get_health() == 300 and self.boss.get_health() == 1500
                           and not self.player.is_busy() and not self.boss.is_busy())
                down = []
                for name in KEYS:
                    key = u.Key(); key.set_editor_property('key_name', name)
                    if self.pc.is_input_key_down(key): down.append(name)
                self.check('all_keys_released', not down, down)
                self.check('no_other_runner', not active_others(self))
                next_tag = str(u.load_asset('/Game/Combat/Skills/DA_Attack3').next_skill_tag.get_editor_property('tag_name'))
                self.check('default_attack3_next', next_tag == 'Combat.Skill.Attack4', next_tag)
                self.report['dll_sha256'] = {n: hashlib.sha256((Path(u.Paths.project_dir())/'Binaries/Win64'/n).read_bytes()).hexdigest()
                    for n in ('UnrealEditor-Combat.dll', 'UnrealEditor-CombatEditor.dll')}
                self.shots = Path(u.Paths.project_saved_dir())/'Screenshots'
                self.before = set(self.shots.rglob('*.png'))
                u.SystemLibrary.execute_console_command(self.world, 'Shot SHOWUI')
                self.phase, self.at = 'screenshot', time.monotonic()
            elif self.phase == 'screenshot':
                files = [p for p in set(self.shots.rglob('*.png'))-self.before if p.stat().st_size > 0]
                if files:
                    self.report['screenshots'] = [str(p.resolve()) for p in sorted(files)]
                    self.check('paused_final', u.GameplayStatics.is_game_paused(self.world))
                    self.finish()
        except Exception as exc:
            self.finish(exc)


def start():
    if active_others(): raise RuntimeError('Another Combat runner is active')
    runner = Handoff(); setattr(builtins, KEY, runner)
    try:
        runner.handle = u.register_slate_post_tick_callback(runner.tick)
    except Exception as exc:
        runner.finish('callback_register: '+str(exc))
    return status()


def status():
    r = getattr(builtins, KEY, None)
    return {'status': r.phase, 'active': r.handle is not None, 'report': str(r.path)} if r else {'status': 'idle'}


def stop():
    r = getattr(builtins, KEY, None)
    if r and r.handle is not None: r.finish('Stopped before completion')
    return status()
