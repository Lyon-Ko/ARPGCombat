"""Checks unowned SpawnSystemAtLocation auto-destruction in actual PIE."""
import builtins
import json
import time
from pathlib import Path
import unreal as u


class LifetimeProbe:
    def __init__(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        assert self.world and not u.GameplayStatics.is_game_paused(self.world)
        self.names = ['NS_FinalMetalHit', 'NS_FinalParryFlash', 'NS_FinalAOERelease']
        self.systems = [u.load_asset('/Game/Combat/VFX/' + name) for name in self.names]
        self.rows = []
        self.references = []
        self.handle = None
        self.phase = 0
        self.at = 0
        self.started = time.monotonic()
        self.status = 'running'

    def tick(self, delta):
        try:
            if time.monotonic() - self.started > 45:
                raise TimeoutError('Lifetime probe timed out')
            now = u.GameplayStatics.get_time_seconds(self.world)
            if self.phase % 2 == 0:
                if self.phase == 6:
                    self.status = 'passed' if all(not row['valid_after_2_seconds'] for row in self.rows) else 'failed'
                    self.finish()
                    return
                for name, system in zip(self.names, self.systems):
                    for index in range(5):
                        component = u.NiagaraFunctionLibrary.spawn_system_at_location(
                            self.world, system, u.Vector(100 + index * 20, 300, 140),
                            auto_destroy=True, auto_activate=True,
                            pooling_method=u.NCPoolMethod.NONE, pre_cull_check=False)
                        assert component and u.SystemLibrary.is_valid(component), name
                        self.references.append((name, component))
                self.at = now
                self.phase += 1
            elif now - self.at >= 2.1:
                remaining = []
                for name, component in self.references:
                    invalidated_wrapper = False
                    try:
                        valid = u.SystemLibrary.is_valid(component)
                    except TypeError as error:
                        # UE GC can invalidate the retained Python wrapper after
                        # auto-destruction; it can no longer marshal to UObject.
                        if 'Cannot nativize' not in str(error):
                            raise
                        valid = False
                        invalidated_wrapper = True
                    row = {'system': name, 'round': self.phase // 2 + 1,
                           'valid_after_2_seconds': valid,
                           'wrapper_invalidated_by_gc': invalidated_wrapper,
                           'active': component.is_active() if valid else False}
                    self.rows.append(row)
                    if valid:
                        remaining.append(component)
                # Do not deactivate surviving instances: that would hide a failed test.
                assert not remaining, 'Unowned one-shot components survived 2.1 seconds'
                self.phase += 1
        except Exception as error:
            self.status = 'failed: ' + repr(error)
            self.finish()

    def finish(self):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / 'VFXLifetime.json'
        path.write_text(json.dumps({'status': self.status, 'spawned': len(self.references),
                                   'observations': self.rows}, indent=2), encoding='utf-8')
        print('VFX_LIFETIME', self.status, 'spawned', len(self.references))


def start():
    capture = getattr(builtins, '_combat_vfx_capture', None)
    if capture and capture.handle is not None:
        raise RuntimeError('Finish visual capture first')
    previous = getattr(builtins, '_combat_vfx_lifetime', None)
    if previous and previous.handle is not None:
        raise RuntimeError('Lifetime probe already running')
    runner = LifetimeProbe()
    builtins._combat_vfx_lifetime = runner
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    return runner.status
