"""PIE integration regression using actual player key input and montage events.

Run with Tools/Combat.ps1 python -File after starting an empty arena PIE.
Results: Saved/Acceptance/GroundLocomotion.json. Does not modify assets.
"""
import builtins
import json
from pathlib import Path
import traceback
import unreal as u


def tag(name):
    value = u.GameplayTag()
    assert value.import_text(f'(TagName="{name}")')
    return value


class Regression:
    def __init__(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        assert self.world and not u.GameplayStatics.is_game_paused(self.world)
        self.player = u.GameplayStatics.get_player_pawn(self.world, 0)
        self.pc = self.player.get_controller()
        self.anim = self.player.mesh.get_anim_instance()
        self.move = self.player.character_movement
        self.player.retry_encounter()
        self.boss = self.player.get_combat_target()
        assert self.boss
        self.report = {'status': 'running', 'checks': [], 'samples': []}
        self.path = Path(u.Paths.project_saved_dir()) / 'Acceptance/GroundLocomotion.json'
        self.path.parent.mkdir(exist_ok=True)
        self.handle = None
        self.generator = self.run()

    def check(self, name, condition, **data):
        self.report['checks'].append(dict(name=name, passed=bool(condition), **data))
        assert condition, f'{name}: {data}'

    def key(self, name, down):
        u.CombatEditorLibrary.inject_player_key(self.pc, name, down)

    def release(self):
        for name in ('W', 'A', 'S', 'D', 'SpaceBar', 'LeftMouseButton', 'LeftShift', 'RightMouseButton'):
            self.key(name, False)
        self.player.attack_released()

    def now(self):
        return u.GameplayStatics.get_time_seconds(self.world)

    def wait(self, seconds):
        end = self.now() + seconds
        while self.now() < end:
            yield

    def fixture(self, locked=False):
        self.release()
        self.player.reset_combat_state()
        self.boss.reset_combat_state()
        self.boss.get_controller().get_editor_property('state_tree_component').stop_logic('Locomotion regression')
        self.boss.get_controller().stop_movement()
        self.player.set_actor_location_and_rotation(u.Vector(0, 0, 100), u.Rotator(yaw=0), False, True)
        self.boss.set_actor_location_and_rotation(u.Vector(1800, 0, 110), u.Rotator(yaw=180), False, True)
        self.player.set_editor_property('target_locked', locked)
        self.pc.set_control_rotation(u.Rotator(pitch=-12, yaw=0))
        yield from self.wait(.4)

    def reversal(self, first='W', second='S', locked=False, expected='Fwd'):
        yield from self.fixture(locked)
        self.key(first, True)
        yield from self.wait(.3)
        self.check(f'{first}_running', self.player.get_velocity().length() > 160)
        self.key(first, False)
        self.key(second, True)
        end = self.now() + .2
        while not self.anim.is_pivoting() and self.now() < end:
            yield
        montage = self.anim.get_current_active_montage()
        prefix = f'AM_Pivot_{expected}' if locked or not self.anim.get_editor_property('free_pivot_left') else 'AM_FreePivot_'
        self.check(f'pivot_{first}_{second}_{locked}', self.anim.is_pivoting() and montage and
                   montage.get_name().startswith(prefix), montage=str(montage))

    def active(self):
        return str(self.player.get_active_skill_tag().get_editor_property('tag_name'))

    def complete_reversal(self, label, free=False):
        montage = self.anim.get_current_active_montage()
        length = montage.get_play_length()
        position = self.anim.montage_get_position(montage)
        start = self.now() - position
        # Actual desired input, independent of actor yaw during the turn.
        incoming = self.player.get_velocity().normal()
        reverse = incoming * -1.
        samples = []
        while self.anim.is_pivoting() and self.now() - start < length + 1.:
            elapsed = self.now() - start
            progress = self.anim.get_editor_property('pivot_progress')
            samples.append(dict(elapsed=elapsed, progress=progress,
                reverse_speed=self.player.get_velocity().dot(reverse),
                acceleration=self.move.get_current_acceleration().length(),
                reverse_acceleration=self.move.get_current_acceleration().dot(reverse),
                reversing=self.anim.is_pivot_accelerating(),
                yaw=self.player.get_actor_rotation().yaw))
            yield
        self.report['samples'].append(dict(case=label, clip_length=length, frames=samples))
        self.check(label + '_full_window', not self.anim.is_pivoting() and
                   self.now() - start >= length - .04,
                   elapsed=self.now() - start, clip_length=length)
        braking = [s for s in samples if not s['reversing']]
        reversing = [s for s in samples if s['reversing']]
        self.check(label + '_brakes_before_reverse', braking and reversing and
                   max(s['reverse_speed'] for s in braking) < 1. and
                   min(s['elapsed'] for s in reversing) > .25)
        self.check(label + '_gradual_braking', any(.08 < s['elapsed'] < .2 and s['reverse_speed'] < -100 for s in braking))
        self.check(label + '_gradual_reverse_acceleration', any(20 < s['reverse_speed'] < 400 for s in reversing) and
                   max(s['reverse_speed'] for s in reversing) > 450)
        self.check(label + '_original_playback_rate', max(abs(s['progress'] * length - min(s['elapsed'], length))
                   for s in samples) < .08)
        self.check(label + '_full_clip_seen', max(s['progress'] for s in samples) > .98)
        if free:
            if montage.get_name().startswith('AM_FreePivot_'):
                segment = montage.get_editor_property('slot_anim_tracks')[0].get_editor_property('anim_track').get_editor_property('anim_segments')[0]
                clip = segment.get_editor_property('anim_reference')
                times, yaws = u.AnimationLibrary.get_float_keys(clip, 'PivotYaw')
                errors = []
                for sample in samples:
                    index = min(round(sample['progress'] * length * 60), len(yaws) - 1)
                    errors.append(abs(abs(sample['yaw']) - abs(yaws[index])))
                self.check(label + '_authored_turn_timing', max(errors) < 12, max_error=max(errors))
            else:
                early = [s for s in samples if .3 <= s['elapsed'] <= .4]
                self.check(label + '_fast_turn', bool(early) and min(abs(s['yaw']) for s in early) > 170.)
        yield from self.wait(.3)
        self.check(label + '_acceleration_after_turn', self.player.get_velocity().dot(reverse) > 160.)

    def run(self):
        for hero in ('Kwang', 'Greystone'):
            root = f'/Game/Combat/Animations/Native/{hero}'
            bs = u.load_asset(root + '/BS_Locomotion2D')
            self.check(hero + '_locomotion_original_rate', all(
                abs(s.get_editor_property('rate_scale') - 1.) < .001 and
                abs(s.get_editor_property('animation').get_editor_property('rate_scale') - 1.) < .001
                for s in bs.get_editor_property('sample_data')))
            for direction in ('Fwd', 'Bwd', 'Left', 'Right'):
                montage = u.load_asset(root + '/AM_Pivot_' + direction)
                sequence = u.load_asset(root + '/A_Jog_' + direction + '_Pivot180')
                source = u.load_asset(f'/Game/Paragon{hero}/Characters/Heroes/{hero}/Animations/Jog_{direction}_Pivot180')
                segment = montage.get_editor_property('slot_anim_tracks')[0].get_editor_property('anim_track').get_editor_property('anim_segments')[0]
                self.check(hero + '_' + direction + '_full_original_clip',
                    abs(montage.get_play_length() - source.get_play_length()) < .001 and
                    abs(segment.get_editor_property('anim_start_time')) < .001 and
                    abs(segment.get_editor_property('anim_end_time') - source.get_play_length()) < .001 and
                    abs(segment.get_editor_property('anim_play_rate') - 1.) < .001 and
                    abs(sequence.get_editor_property('rate_scale') - 1.) < .001 and
                    abs(montage.get_editor_property('rate_scale') - 1.) < .001)
        # Four strafe directions use the incoming travel direction.
        for first, second, expected in [('W', 'S', 'Fwd'), ('S', 'W', 'Bwd'),
                                        ('A', 'D', 'Left'), ('D', 'A', 'Right')]:
            yield from self.reversal(first, second, True, expected)
            yield from self.complete_reversal(expected)
            self.check(f'pivot_{expected}_returns', not self.anim.is_pivoting())
            self.check(f'locked_{expected}_facing', abs(self.player.get_actor_rotation().yaw) < 35)
        yield from self.reversal()
        yield from self.complete_reversal('free', free=True)
        self.check('free_reversal_faces_travel', self.player.get_actor_forward_vector().dot(
            self.player.get_velocity().normal()) > .9)

        yield from self.reversal()
        self.release()
        yield from self.wait(.04)
        self.check('release_stops_pivot', not self.anim.is_pivoting())

        yield from self.reversal()
        self.player.jump()
        yield from self.wait(.06)
        self.check('jump_stops_pivot', self.move.is_falling() and not self.anim.is_pivoting())
        yield from self.wait(.4)
        self.check('no_air_pivot', not self.anim.is_pivoting())

        for skill, method in [('Attack1', self.player.attack_pressed),
                              ('Dash', self.player.dash_pressed), ('Parry', self.player.parry_pressed)]:
            yield from self.reversal()
            method()
            self.player.attack_released()
            self.check(f'{skill}_preempts_pivot', not self.anim.is_pivoting() and
                       self.active() == 'Combat.Skill.' + skill, active=self.active())
            self.release()
            yield from self.wait(.1)
            self.check(f'{skill}_no_pivot_during_skill', not self.anim.is_pivoting())

        yield from self.fixture()
        self.key('W', True)
        yield from self.wait(.3)
        self.player.attack_pressed()
        self.player.attack_released()
        self.check('attack_removes_run_velocity', self.player.get_velocity().length() < 1)
        yield from self.wait(.2)
        self.check('movement_cannot_cancel_startup', self.active() == 'Combat.Skill.Attack1')
        yield from self.wait(.3)
        self.check('movement_cancels_recovery', not self.player.is_busy() and
                   self.player.get_editor_property('last_skill_interrupted'))
        yield from self.wait(.2)
        self.check('movement_resumes', self.player.get_velocity().length() > 160)

        yield from self.fixture()
        self.player.attack_pressed()
        self.player.attack_released()
        yield from self.wait(.7)
        self.check('finish_notify_completes', not self.player.is_busy() and
                   not self.player.get_editor_property('last_skill_interrupted'))

        yield from self.fixture()
        self.player.attack_pressed()
        self.player.attack_released()
        yield from self.wait(.35)
        self.player.attack_pressed()
        self.player.attack_released()
        self.check('combo_transitions_to_attack2', self.active() == 'Combat.Skill.Attack2', active=self.active())
        # A finishing notify from an outgoing montage must not finish Attack2.
        event = tag('Combat.Event.Finish')
        data = u.GameplayEventData()
        data.set_editor_property('event_tag', event)
        data.set_editor_property('optional_object', u.load_asset('/Game/Combat/Animations/Native/Kwang/AM_Attack1'))
        u.AbilitySystemLibrary.send_gameplay_event_to_actor(self.player, event, data)
        self.check('old_notify_ignored', self.active() == 'Combat.Skill.Attack2')
        # External montage replacement should release gameplay during blending.
        self.player.play_anim_montage(self.player.get_editor_property('hit_react_montage'))
        yield from self.wait(.03)
        self.check('external_montage_interrupt_releases_busy', not self.player.is_busy())

        yield from self.reversal()
        hit = u.CombatHit(attacker=self.boss, damage=1., poise_damage=0.,
                          location=self.player.get_actor_location(), direction=u.Vector(-1, 0, 0),
                          parryable=False, attack_instance=98101)
        self.player.receive_combat_hit(hit)
        self.check('hit_reaction_preempts_pivot', not self.anim.is_pivoting())
        yield from self.reversal()
        hit.set_editor_property('damage', 9999.)
        hit.set_editor_property('attack_instance', 98102)
        self.player.receive_combat_hit(hit)
        self.check('death_preempts_pivot', not self.player.is_alive() and not self.anim.is_pivoting())
        yield from self.fixture()
        self.check('reset_clears_pivot', self.player.is_alive() and not self.anim.is_pivoting())

    def tick(self, dt):
        try:
            next(self.generator)
        except StopIteration:
            self.finish()
        except Exception:
            self.finish(traceback.format_exc())

    def finish(self, error=None):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        self.release()
        self.player.reset_combat_state()
        self.boss.reset_combat_state()
        self.player.set_editor_property('target_locked', False)
        self.report.update(status='failed' if error else 'passed', error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding='utf-8')
        print('GROUND_LOCOMOTION_REGRESSION', self.report['status'], len(self.report['checks']), error)


if __name__ == '__main__':
    old = getattr(builtins, '_ground_locomotion_regression', None)
    assert not old or old.handle is None, 'Regression already running'
    runner = Regression()
    builtins._ground_locomotion_regression = runner
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
