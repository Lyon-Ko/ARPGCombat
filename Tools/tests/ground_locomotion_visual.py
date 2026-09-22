"""Capture real PIE transitions at reduced global time; restore on completion."""
import builtins
from pathlib import Path
import runpy
import unreal as u

Regression = runpy.run_path(str(Path(__file__).with_name('ground_locomotion_regression.py')))['Regression']


class Visual(Regression):
    def __init__(self):
        super().__init__()
        self.path = self.path.with_name('GroundLocomotionVisual.json')
        self.original_dilation = u.GameplayStatics.get_global_time_dilation(self.world)
        self.report['shots'] = []

    def shot(self, name):
        path = (self.path.parent / f'Locomotion_{name}.png').resolve()
        montage = self.anim.get_current_active_montage()
        self.report['shots'].append(dict(path=str(path), time=self.now(), pivot=self.anim.is_pivoting(),
            montage=montage.get_name() if montage else None, skill=self.active()))
        u.SystemLibrary.execute_console_command(self.world, f'Shot SHOWUI filename="{path}" -nosuffix')
        yield
        yield

    def run(self):
        u.GameplayStatics.set_global_time_dilation(self.world, .5)
        yield from self.reversal()
        yield from self.wait(.1)
        yield from self.shot('free_plant')
        yield from self.wait(.25)
        yield from self.shot('free_turn')
        while self.anim.is_pivoting():
            yield
        yield from self.wait(.3)
        yield from self.shot('free_exit')
        yield from self.reversal('A', 'D', True, 'Left')
        yield from self.wait(.12)
        yield from self.shot('locked_strafe')
        self.player.attack_pressed()
        self.player.attack_released()
        yield from self.wait(.1)
        yield from self.shot('attack_from_pivot')
        yield from self.wait(.42)
        yield from self.shot('attack_to_move')

    def finish(self, error=None):
        u.GameplayStatics.set_global_time_dilation(self.world, self.original_dilation)
        super().finish(error)


old = getattr(builtins, '_ground_locomotion_regression', None)
assert not old or old.handle is None, 'Regression still running'
old = getattr(builtins, '_ground_locomotion_visual', None)
assert not old or old.handle is None, 'Capture already running'
runner = Visual()
builtins._ground_locomotion_visual = runner
runner.handle = u.register_slate_post_tick_callback(runner.tick)
