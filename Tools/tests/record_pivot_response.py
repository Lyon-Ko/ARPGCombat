"""Passive PIE input/montage recorder. User reproduces; no input is injected."""
import builtins
import json
import time
from pathlib import Path
import unreal as u


class Recorder:
    def __init__(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        self.player = u.GameplayStatics.get_player_pawn(self.world, 0)
        self.pc = self.player.get_controller()
        self.anim = self.player.mesh.get_anim_instance()
        self.started = time.monotonic()
        self.rows = []
        self.keys = {}
        for name in ('W', 'A', 'S', 'D'):
            key = u.Key()
            key.set_editor_property('key_name', name)
            self.keys[name] = key
        self.handle = None

    def tick(self, dt):
        montage = self.anim.get_current_active_montage()
        velocity = self.player.get_velocity()
        self.rows.append(dict(wall=time.monotonic()-self.started,
            game=u.GameplayStatics.get_time_seconds(self.world), dt=dt,
            keys=''.join(n for n,k in self.keys.items() if self.pc.is_input_key_down(k)),
            pivot=self.anim.is_pivoting(), busy=self.player.is_busy(),
            locked=self.player.is_target_locked(), falling=self.player.character_movement.is_falling(),
            montage=montage.get_name() if montage else None,
            any_montage=self.anim.is_any_montage_playing(),
            position=self.anim.montage_get_position(montage) if montage else 0.,
            progress=self.anim.get_editor_property('pivot_progress'),
            yaw=self.player.get_actor_rotation().yaw, camera=self.pc.get_control_rotation().yaw,
            velocity=[velocity.x,velocity.y,velocity.z]))
        if time.monotonic() - self.started > 240:
            self.finish()

    def finish(self):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        path = Path(u.Paths.project_saved_dir()) / 'Acceptance/PivotUserInputTrace.json'
        path.write_text(json.dumps(self.rows), encoding='utf-8')
        print('USER_PIVOT_TRACE_SAVED', len(self.rows))


old = getattr(builtins, '_pivot_user_recorder', None)
if old and old.handle is not None:
    old.finish()
recorder = Recorder()
builtins._pivot_user_recorder = recorder
recorder.handle = u.register_slate_post_tick_callback(recorder.tick)
print('USER_PIVOT_TRACE_STARTED')
