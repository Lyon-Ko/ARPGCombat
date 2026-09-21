"""Opt-in isolated new-tag chain proof. Load this file, then call start().

Requires stopped PIE and clean target packages; never discards unsaved edits.
Uses real PC InputKey, stops Boss AI only for the isolated damage fixture.
"""
import builtins
import datetime
import hashlib
import json
import time
from pathlib import Path

import unreal as u

KEY = '_combat_skill_extension_final'
BP = '/Game/Combat/Characters/BP_CombatPlayer'
ATTACK3 = '/Game/Combat/Skills/DA_Attack3'
EXAMPLE = '/Game/Combat/Skills/Examples/DA_Example_CrescentBurst'
EXPECTED = ['Combat.Skill.Attack1', 'Combat.Skill.Attack2',
            'Combat.Skill.Attack3', 'Combat.Skill.Example.CrescentBurst']


def tag_name(tag):
    return str(tag.get_editor_property('tag_name'))


def world():
    return u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()


class Verification:
    def __init__(self):
        self.handle = None
        self.player = self.boss = None
        self.bindings = []
        self.mutated = self.requested_pie = False
        self.finalized = False
        self.phase = 'setup'
        self.at = time.monotonic()
        self.release_at = 0
        self.queued = set()
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / ('SkillExtensionFinal_' + stamp + '.json')
        self.report = {'status': 'running', 'started_utc': stamp, 'accepts_twenty_rounds': False,
                       'scope': 'isolated real PC InputKey chain; Boss AI stopped; no numeric tuning',
                       'errors': [], 'assertions': [], 'started': [], 'ended': [], 'timeline': []}
        project = Path(u.Paths.project_dir()).resolve()
        self.report['dlls'] = []
        for name in ('UnrealEditor-Combat.dll', 'UnrealEditor-CombatEditor.dll'):
            path = project / 'Binaries' / 'Win64' / name
            self.report['dlls'].append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                        'bytes': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns})

    def check(self, name, condition, detail=None):
        self.report['assertions'].append({'name': name, 'passed': bool(condition), 'detail': detail})
        if not condition:
            raise AssertionError(name + ': ' + str(detail))

    def setup(self):
        bp, attack, example = map(u.load_asset, (BP, ATTACK3, EXAMPLE))
        self.check('assets_exist', all((bp, attack, example)))
        packages = [asset.get_outermost() for asset in (bp, attack, example)]
        dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        self.check('target_packages_clean', not any(p in dirty for p in packages),
                   'Save your original BP/Attack3/Example edits before running; no changes were discarded.')
        cdo = u.get_default_object(bp.generated_class())
        self.original_paths = [d.get_path_name() for d in cdo.get_editor_property('skill_definitions')]
        self.original_next = tag_name(attack.get_editor_property('next_skill_tag'))
        # Rebuild from immutable text: get_editor_property can expose an alias
        # into the asset's struct storage rather than a detached value.
        self.original_next_value = u.GameplayTag()
        self.check('independent_next_from_text', self.original_next_value.import_text(
            '(TagName="' + self.original_next + '")'))
        self.report['original'] = {'skill_definitions': self.original_paths, 'attack3_next': self.original_next}
        self.check('default_attack3_next_is_attack4', self.original_next == 'Combat.Skill.Attack4', self.original_next)
        self.check('default_attack4_installed', any(tag_name(d.skill_tag) == 'Combat.Skill.Attack4'
                   for d in cdo.get_editor_property('skill_definitions')))
        self.check('independent_next_snapshot_initial', tag_name(self.original_next_value) == self.original_next)
        self.check('example_new_tag', tag_name(example.skill_tag) == EXPECTED[-1])
        self.check('example_not_already_installed', example.get_path_name() not in self.original_paths)
        self.mutated = True
        attack.set_editor_property('next_skill_tag', example.skill_tag)
        self.check('independent_next_snapshot_after_mutation', tag_name(self.original_next_value) == self.original_next,
                   tag_name(self.original_next_value))
        cdo.set_editor_property('skill_definitions', [u.load_asset(p) for p in self.original_paths] + [example])
        self.check('temporary_compile', u.CombatEditorLibrary.compile_and_save(bp))
        self.check('temporary_data_save', u.EditorAssetLibrary.save_loaded_asset(attack, False))
        self.phase = 'wait_pie'
        self.at = time.monotonic()
        self.requested_pie = True
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()

    def on_started(self, actor, skill):
        self.report['started'].append(tag_name(skill))

    def on_ended(self, actor, skill):
        self.report['ended'].append({'tag': tag_name(skill), 'interrupted': bool(actor.last_skill_interrupted)})

    def release(self):
        if self.player:
            pc = self.player.get_controller()
            if pc:
                u.CombatEditorLibrary.inject_player_key(pc, 'LeftMouseButton', False)
            self.player.attack_released()
        self.release_at = 0

    def begin_finish(self, error=None):
        if error:
            self.report['errors'].append(str(error))
        if self.phase == 'finishing':
            return
        self.phase = 'finishing'
        self.at = time.monotonic()
        try:
            self.release()
        except Exception as exc:
            self.report['errors'].append('release: ' + str(exc))
        for delegate, callback in self.bindings:
            try:
                delegate.remove_callable(callback)
            except Exception as exc:
                self.report['errors'].append('delegate cleanup: ' + str(exc))
        self.bindings.clear()
        if self.requested_pie:
            try:
                u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
            except Exception as exc:
                self.report['errors'].append('end PIE: ' + str(exc))

    def restore(self):
        if not self.mutated:
            return
        bp, attack = map(u.load_asset, (BP, ATTACK3))
        cdo = u.get_default_object(bp.generated_class())
        cdo.set_editor_property('skill_definitions', [u.load_asset(p) for p in self.original_paths])
        self.check('independent_next_snapshot_before_restore', tag_name(self.original_next_value) == self.original_next)
        attack.set_editor_property('next_skill_tag', self.original_next_value)
        self.check('restore_compile_save', u.CombatEditorLibrary.compile_and_save(bp))
        self.check('restore_data_save', u.EditorAssetLibrary.save_loaded_asset(attack, False))
        self.check('PIE_stopped_before_reload', not world())
        # Non-interactive negative mode will not discard newly dirty packages.
        reloaded, message = u.EditorLoadingAndSavingUtils.reload_packages(
            [bp.get_outermost(), attack.get_outermost()], u.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
        self.check('actual_package_reload', reloaded and not str(message), str(message))
        bp, attack = map(u.load_asset, (BP, ATTACK3))
        cdo = u.get_default_object(bp.generated_class())
        actual = [d.get_path_name() for d in cdo.get_editor_property('skill_definitions')]
        next_tag = tag_name(attack.get_editor_property('next_skill_tag'))
        self.report['restored_readback'] = {'skill_definitions': actual, 'attack3_next': next_tag}
        self.check('defaults_restored_after_reload', actual == self.original_paths and next_tag == self.original_next)
        self.mutated = False

    def finalize(self):
        if self.finalized:
            return
        self.finalized = True
        try:
            self.restore()
        except Exception as exc:
            self.report['errors'].append('RESTORE FAILED: ' + str(exc))
        finally:
            if self.handle is not None:
                u.unregister_slate_post_tick_callback(self.handle)
                self.handle = None
            self.phase = 'failed' if self.report['errors'] else 'passed'
            self.report['status'] = self.phase
            self.report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Unique evidence never overwrites the historical probe or another run.
            with self.path.open('x', encoding='utf-8') as stream:
                json.dump(self.report, stream, ensure_ascii=False, indent=2)
            print('SKILL_EXTENSION_FINAL', self.phase, str(self.path))

    def tick(self, delta):
        now = time.monotonic()
        try:
            if self.phase == 'finishing':
                if not world():
                    self.finalize()
                elif now - self.at > 15:
                    self.report['errors'].append('PIE did not stop within 15 seconds')
                    self.finalize()
                return
            if self.phase == 'wait_pie':
                if now - self.at > 20:
                    raise TimeoutError('PIE startup timeout')
                game = world()
                if not game:
                    return
                actors = u.GameplayStatics.get_all_actors_of_class(game, u.CombatCharacter)
                if len(actors) != 2:
                    return
                self.player = next(a for a in actors if not a.is_boss)
                self.boss = next(a for a in actors if a.is_boss)
                self.boss.get_controller().state_tree_component.stop_logic('Isolated extension proof')
                self.player.set_actor_location(u.Vector(0, 0, 100), False, True)
                self.boss.set_actor_location(u.Vector(220, 0, 110), False, True)
                self.player.set_actor_rotation(u.Rotator(yaw=0), True)
                self.boss.set_actor_rotation(u.Rotator(yaw=180), True)
                self.player.set_combat_target(self.boss)
                self.hp = self.boss.get_health()
                for name, callback in (('on_skill_started', self.on_started), ('on_skill_ended', self.on_ended)):
                    delegate = getattr(self.player, name)
                    delegate.add_callable(callback)
                    self.bindings.append((delegate, callback))
                self.phase, self.at = 'settle', now
            elif self.phase == 'settle' and now - self.at > .2:
                u.CombatEditorLibrary.inject_player_key(self.player.get_controller(), 'LeftMouseButton', True)
                self.release_at = now + .04
                self.phase, self.at = 'observe', now
            elif self.phase == 'observe':
                p = self.player
                if self.release_at and now >= self.release_at:
                    self.release()
                tag = tag_name(p.get_active_skill_tag())
                if tag in EXPECTED[:3] and tag not in self.queued and p.get_skill_elapsed_time() > .23:
                    u.CombatEditorLibrary.inject_player_key(p.get_controller(), 'LeftMouseButton', True)
                    self.release_at = now + .04
                    self.queued.add(tag)
                self.report['timeline'].append({'seconds': now-self.at, 'tag': tag, 'health': self.boss.get_health()})
                if len(self.report['ended']) >= 4 and not p.is_busy():
                    damage = self.hp - self.boss.get_health()
                    self.report['damage'] = damage
                    self.check('exact_four_start_tags', self.report['started'] == EXPECTED, self.report['started'])
                    # RequestSkillByTag cancels each predecessor to enter its
                    # successor. These three combo transitions are intentional.
                    self.check('exact_four_combo_ends', [r['tag'] for r in self.report['ended']] == EXPECTED
                               and [r['interrupted'] for r in self.report['ended']] == [True, True, True, False],
                               self.report['ended'])
                    self.check('total_damage_130', abs(damage - 130) < .001, damage)
                    self.check('ended_cleanly', not p.is_busy() and not p.last_skill_interrupted)
                    self.begin_finish()
                elif now-self.at > 9:
                    raise TimeoutError('Four-hit chain did not end normally within 9 seconds')
        except Exception as exc:
            if self.phase == 'finishing':
                self.report['errors'].append(str(exc))
                self.finalize()
            else:
                self.begin_finish(exc)


def start():
    if world() or u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Stop PIE before explicitly starting the isolated extension verification')
    for key, runner in vars(builtins).items():
        if key.startswith('_combat_') and getattr(runner, 'handle', None) is not None:
            raise RuntimeError('Another Combat runner is active: ' + key)
    runner = Verification()
    setattr(builtins, KEY, runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    try:
        runner.setup()
    except Exception as exc:
        runner.begin_finish(exc)
    return status()


def status():
    runner = getattr(builtins, KEY, None)
    return {'status': runner.phase, 'report': str(runner.path), 'errors': runner.report['errors']} if runner else {'status': 'idle'}


def stop():
    runner = getattr(builtins, KEY, None)
    if runner and runner.handle is not None:
        runner.begin_finish('Stopped by caller; verification incomplete')
    return status()
