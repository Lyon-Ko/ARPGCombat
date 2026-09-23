"""Measure A/D reversal input, montage onset and visible actor turn separately."""
import builtins
import json
import traceback
from pathlib import Path
import unreal as u


class Diagnostic:
    def __init__(self, continuous=False):
        self.continuous = continuous
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        self.player = u.GameplayStatics.get_player_pawn(self.world, 0)
        self.pc = self.player.get_controller()
        self.anim = self.player.mesh.get_anim_instance()
        self.keys = {}
        for name in ('A', 'D'):
            key = u.Key()
            key.set_editor_property('key_name', name)
            self.keys[name] = key
        self.performance = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
        self.throttle = self.performance.get_editor_property('bThrottleCPUWhenNotForeground')
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
        self.pc.set_ignore_look_input(True)
        self.rows = []
        self.handle = None
        self.run = self.cases()

    def key(self, name, pressed):
        u.CombatEditorLibrary.inject_player_key(self.pc, name, pressed)

    def now(self):
        return u.GameplayStatics.get_time_seconds(self.world)

    def wait(self, seconds):
        end = self.now() + seconds
        while self.now() < end:
            yield

    def cases(self):
        for camera in ((0.,) if self.continuous else (0., 45., 90.)):
            for index, (first, second) in enumerate([('A', 'D'), ('D', 'A')]):
                if not self.continuous or index == 0:
                    for key in ('W', 'A', 'S', 'D'):
                        self.key(key, False)
                    self.player.reset_combat_state()
                    self.player.set_editor_property('target_locked', False)
                    self.player.character_movement.stop_movement_immediately()
                    self.player.set_actor_location_and_rotation(u.Vector(0, 0, 100), u.Rotator(yaw=camera), False, True)
                    self.pc.set_control_rotation(u.Rotator(yaw=camera, pitch=-12))
                    yield from self.wait(.6)
                self.key(first, True)
                yield from self.wait(2.)
                initial_yaw = self.player.get_actor_rotation().yaw
                self.key(first, False)
                self.key(second, True)
                start = self.now()
                row = dict(case=first+'_'+second, camera=camera, initial_yaw=initial_yaw,
                           control_yaw=self.pc.get_control_rotation().yaw,
                           initial_speed=self.player.get_velocity().length(), frames=[])
                self.rows.append(row)
                while self.now() - start < 2.:
                    montage = self.anim.get_current_active_montage()
                    yaw = self.player.get_actor_rotation().yaw
                    row['frames'].append(dict(t=self.now()-start, pivot=self.anim.is_pivoting(),
                        montage=montage.get_name() if montage else None,
                        position=self.anim.montage_get_position(montage) if montage else 0.,
                        yaw=yaw, turn=abs((yaw-initial_yaw+180)%360-180),
                        speed=self.player.get_velocity().length(),
                        A=self.pc.is_input_key_down(self.keys['A']), D=self.pc.is_input_key_down(self.keys['D'])))
                    yield

    def tick(self, dt):
        try:
            next(self.run)
        except StopIteration:
            self.finish()
        except Exception:
            self.finish(traceback.format_exc())

    def finish(self, error=None):
        u.unregister_slate_post_tick_callback(self.handle)
        self.handle = None
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground', self.throttle)
        self.pc.set_ignore_look_input(False)
        for key in ('A', 'D', 'W', 'S'):
            self.key(key, False)
        report = dict(error=error, cases=self.rows)
        filename = 'PivotResponseContinuous.json' if self.continuous else 'PivotResponseStable.json'
        path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / filename
        path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('PIVOT_RESPONSE_DIAGNOSTIC', error or 'complete')


if __name__ == '__main__':
    runner = Diagnostic()
    builtins._pivot_response_diagnostic = runner
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
