"""Only locomotion phase handoff: vary entry phase and measure the return to BS."""
import builtins
import json
import traceback
from pathlib import Path
import unreal as u


class PhaseTest:
    def __init__(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        self.player = u.GameplayStatics.get_player_pawn(self.world, 0)
        self.pc = self.player.get_controller()
        self.anim = self.player.mesh.get_anim_instance()
        self.donor = u.load_asset('/Game/Combat/Animations/Native/Kwang/A_Jog_Fwd')
        self.pose_options = u.AnimPoseEvaluationOptions()
        self.performance = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
        self.original_throttle = self.performance.get_editor_property('bThrottleCPUWhenNotForeground')
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
        self.pc.set_ignore_look_input(True)
        self.rows = []
        self.handle = None
        self.generator = self.run()

    def key(self, name, down):
        u.CombatEditorLibrary.inject_player_key(self.pc,name,down)

    def now(self):
        return u.GameplayStatics.get_time_seconds(self.world)

    def wait(self, seconds):
        deadline = self.now()+seconds
        while self.now()<deadline:
            yield

    def run(self):
        for side in globals().get('test_sides', ('A','D')):
            for warmup in globals().get('test_warmups', (.6, 1., 1.4)):
                for key in ('W','A','S','D'):
                    self.key(key,False)
                self.player.reset_combat_state()
                self.player.character_movement.stop_movement_immediately()
                self.player.set_editor_property('target_locked',False)
                self.player.set_actor_location_and_rotation(u.Vector(0,0,100),u.Rotator(yaw=0),False,True)
                self.pc.set_control_rotation(u.Rotator(yaw=0,pitch=-12))
                yield from self.wait(.8)
                self.key(side,True)
                yield from self.wait(warmup)
                initial_phase = self.anim.get_editor_property('ground_animation_phase')
                self.key(side,False)
                self.key('D' if side=='A' else 'A',True)
                start = self.now()
                while not self.anim.is_pivoting() and self.now()-start<.2:
                    yield
                assert self.anim.is_pivoting(), 'Pivot not started'
                clip_length = self.anim.get_current_active_montage().get_play_length()
                row = dict(side=side,warmup=warmup,initial_phase=initial_phase,samples=[])
                self.rows.append(row)
                while self.anim.is_pivoting() and self.now()-start<2.:
                    actual = self.anim.get_editor_property('ground_animation_phase')
                    expected = self.anim.get_editor_property('pivot_expected_run_phase')
                    sample = dict(time=self.now()-start,
                        progress=self.anim.get_editor_property('pivot_progress'),actual=actual,expected=expected,
                        aligned=self.anim.get_editor_property('bPivotPhaseAligned'),
                        phase_error=abs((actual-expected+.5)%1-.5))
                    if sample['aligned'] and sample['progress']*clip_length >= clip_length-.2:
                        reference = u.AnimPoseExtensions.get_anim_pose_at_time(self.donor, actual*self.donor.get_play_length(), self.pose_options)
                        target = u.AnimPoseExtensions.get_bone_pose(reference, 'weapon_r', u.AnimPoseSpaces.WORLD)
                        current = self.player.mesh.get_bone_transform('weapon_r', u.RelativeTransformSpace.RTS_COMPONENT)
                        tip = u.Vector(0,-147,0)
                        sample['rendered_tip_error_cm'] = (u.MathLibrary.transform_location(current,tip)-u.MathLibrary.transform_location(target,tip)).length()
                    row['samples'].append(sample)
                    yield
                tail = [s for s in row['samples'] if s['progress']>.8]
                assert tail and all(s['aligned'] for s in tail), 'Base phase was not aligned before the tail'
                row['max_tail_phase_error'] = max(s['phase_error'] for s in tail)
                assert row['max_tail_phase_error']<.025, row['max_tail_phase_error']
                tips = [s['rendered_tip_error_cm'] for s in row['samples'] if 'rendered_tip_error_cm' in s]
                assert tips, 'No rendered tail samples'
                row['max_rendered_tip_error_cm'] = max(tips)
                assert max(tips)<5., max(tips)
                row['passed'] = True

    def tick(self,dt):
        try:
            next(self.generator)
        except StopIteration:
            self.finish()
        except Exception:
            self.finish(traceback.format_exc())

    def finish(self,error=None):
        u.unregister_slate_post_tick_callback(self.handle)
        self.handle=None
        for name in ('W','A','S','D'):
            self.key(name,False)
        self.pc.set_ignore_look_input(False)
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground', self.original_throttle)
        path=Path(u.Paths.project_saved_dir())/'Acceptance/PivotSwordPhaseRuntime.json'
        path.write_text(json.dumps(dict(status='failed' if error else 'passed',error=error,cases=self.rows),indent=2),encoding='utf-8')
        print('PIVOT_SWORD_PHASE',error or 'passed')


runner=PhaseTest()
builtins._pivot_sword_phase_test=runner
runner.handle=u.register_slate_post_tick_callback(runner.tick)
