"""Coordinated native PIE visual evidence, isolated real skill activations.

Invoke start('before') / start('after') after the root's REMOTE GRANTED.
Uses public skills, deterministic placement, stopped boss AI and slow game time.
No injected hits. Restores time dilation and boss AI on finish/error.
"""
import builtins
import json
import time
from pathlib import Path
import unreal as u

KEY = '_combat_vfx_capture'


def tag(name):
    value = u.GameplayTag()
    assert value.import_text('(TagName="Combat.Skill.' + name + '")')
    return value


class Capture:
    def __init__(self, label, ribbons_only=False):
        if not label.replace('_', '').isalnum():
            raise ValueError('Invalid capture label')
        self.label = label
        self.ribbons_only = ribbons_only
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if self.world is None or u.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError('Active unpaused PIE is required')
        people = u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatCharacter)
        self.player = next(a for a in people if not a.get_editor_property('is_boss'))
        self.boss = next(a for a in people if a.get_editor_property('is_boss'))
        self.controller = self.player.get_controller()
        self.ai = self.boss.get_controller()
        self.brain = self.ai.get_editor_property('state_tree_component')
        self.old_dilation = u.GameplayStatics.get_global_time_dilation(self.world)
        self.directory = Path(u.Paths.project_saved_dir()) / 'Acceptance'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events = []
        self.shots = []
        self.pending = []
        self.case = ''
        self.handle = None
        self.started = time.monotonic()
        self.status = 'running'
        self.parry_due = None
        self.bound = []
        self.generator = self.run()

    def now(self):
        return u.GameplayStatics.get_time_seconds(self.world)

    def wait(self, duration):
        until = self.now() + duration
        while self.now() < until:
            yield

    def feedback(self, source, target, cue, location, intensity):
        name = str(cue.get_editor_property('tag_name'))
        self.events.append({'case': self.case, 'cue': name, 'time': self.now(),
                            'source': source.get_name(), 'location': [location.x, location.y, location.z]})
        suffix = None
        if self.case == 'hit' and name == 'Combat.Cue.Hit':
            suffix = 'hit'
        elif self.case == 'aoe' and name == 'Combat.Cue.AreaWarning':
            self.pending.append((self.now() + .15, 'warning'))
        elif self.case == 'aoe' and name == 'Combat.Cue.AreaRelease':
            suffix = 'aoe'
        elif self.case == 'parry' and name == 'Combat.Cue.AreaRelease':
            self.parry_due = self.now() + .04
        elif self.case == 'parry' and name == 'Combat.Cue.Parry':
            suffix = 'parry'
        if suffix:
            self.pending.append((self.now() + (.055 if suffix == 'hit' else .025), suffix))

    def shot(self, suffix):
        if suffix in [item['label'] for item in self.shots]:
            return
        path = (self.directory / ('VFX_' + self.label + '_' + suffix + '.png')).resolve()
        u.SystemLibrary.execute_console_command(self.world, 'Shot SHOWUI filename="' + str(path) + '" -nosuffix')
        self.shots.append({'label': suffix, 'path': str(path), 'request_time': self.now()})

    def fixture(self, separation=160):
        self.pending.clear()
        self.parry_due = None
        for actor in (self.player, self.boss):
            actor.attack_released()
            actor.reset_combat_state()
            actor.get_editor_property('character_movement').stop_movement_immediately()
        self.brain.stop_logic('VFX isolated native screenshot capture')
        self.ai.stop_movement()
        z = self.player.get_actor_location().z
        self.player.set_actor_location_and_rotation(u.Vector(0, 0, z), u.Rotator(yaw=0), False, True)
        self.boss.set_actor_location_and_rotation(u.Vector(separation, 0, z), u.Rotator(yaw=180), False, True)
        self.player.set_combat_target(self.boss)
        self.boss.set_combat_target(self.player)
        self.player.set_editor_property('target_locked', False)
        self.controller.set_control_rotation(u.Rotator(pitch=-12, yaw=0))

    def run(self):
        for actor in (self.player, self.boss):
            delegate = actor.get_editor_property('on_combat_feedback')
            delegate.add_callable(self.feedback)
            self.bound.append(delegate)
        u.GameplayStatics.set_global_time_dilation(self.world, .3)
        cases = [('player_ribbon', 'Attack1'), ('boss_ribbon', 'Boss.Combo1')] if self.ribbons_only else [
            ('hit', 'Attack1'), ('aoe', 'Boss.AOE'), ('parry', 'Boss.AOE'), ('wave', 'Boss.LeapBack')]
        for case, skill in cases:
            self.case = case
            self.fixture(420 if case == 'wave' or self.ribbons_only else 180)
            yield from self.wait(.25)
            actor = self.player if case in ('hit', 'player_ribbon') else self.boss
            assert actor.request_skill_by_tag(tag(skill)), ('Activation failed', skill)
            deadline = self.now() + 3.2
            while self.now() < deadline:
                if self.ribbons_only and actor.is_busy() and actor.get_skill_elapsed_time() >= (.21 if case == 'player_ribbon' else .24):
                    self.shot(case)
                if case == 'wave':
                    projectiles = u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatProjectile)
                    if projectiles:
                        self.shot('wave')
                yield
            self.shot(case + '_settled')
            yield from self.wait(.1)
        self.status = 'captured'

    def tick(self, delta):
        try:
            if time.monotonic() - self.started > 90:
                raise TimeoutError('VFX capture exceeded 90 seconds')
            if self.parry_due is not None and self.now() >= self.parry_due:
                self.parry_due = None
                self.player.parry_pressed()
            ready = [item for item in self.pending if self.now() >= item[0]]
            self.pending = [item for item in self.pending if self.now() < item[0]]
            for _, suffix in ready:
                self.shot(suffix)
            next(self.generator)
        except StopIteration:
            self.finish()
        except Exception as error:
            self.status = 'failed: ' + repr(error)
            self.finish()

    def finish(self):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        for delegate in self.bound:
            delegate.remove_callable(self.feedback)
        self.bound.clear()
        u.GameplayStatics.set_global_time_dilation(self.world, self.old_dilation)
        for actor in (self.player, self.boss):
            actor.attack_released()
            actor.reset_combat_state()
        self.brain.restart_logic()
        report = {'status': self.status, 'mode': 'isolated actual skills, stopped AI, game dilation .3',
                  'events': self.events, 'screenshot_requests': self.shots,
                  'limitation': 'Requests must be verified by opening actual PNG files; this is not final acceptance.'}
        (self.directory / ('VFX_' + self.label + '_capture.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('VFX_CAPTURE_FINISHED', self.status)


def start(label, ribbons_only=False):
    for key in ('_combat_arena_regression', '_combat_arena_ai_scenarios', '_combat_arena_spatial_visual'):
        active = getattr(builtins, key, None)
        if active and active.handle is not None:
            raise RuntimeError('Another coordinated runner is active: ' + key)
    previous = getattr(builtins, KEY, None)
    if previous and previous.handle is not None:
        raise RuntimeError('A VFX capture is already active')
    runner = Capture(label, ribbons_only)
    setattr(builtins, KEY, runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    return {'status': runner.status, 'label': label}
