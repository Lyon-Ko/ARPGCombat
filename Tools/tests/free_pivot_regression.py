"""PIE integration: free turns, authored yaw and lock separation."""
import builtins
import runpy
from pathlib import Path
import unreal as u

Base = runpy.run_path(str(Path(__file__).with_name('ground_locomotion_regression.py')))['Regression']


class FreePivotRegression(Base):
    def __init__(self):
        super().__init__()
        self.path = self.path.with_name('FreePivotRegression.json')

    def start_free(self, side):
        yield from self.fixture()
        self.key('W', True)
        yield from self.wait(.6)
        self.key('W', False)
        self.key('S', True)
        if side:
            self.key(side, True)
        end = self.now() + .3
        while not self.anim.is_pivoting() and self.now() < end:
            yield
        montage = self.anim.get_current_active_montage()
        expected = 'Left' if side == 'A' else 'Right' if side == 'D' else ''
        self.check('free_selection_' + str(side), bool(montage) and
                   montage.get_name().startswith('AM_FreePivot_' + expected), montage=str(montage))

    def run(self):
        for side, target in [('A', -135.), ('D', 135.), (None, 180.)]:
            yield from self.start_free(side)
            start = self.now()
            peak_speed = 0.
            while self.anim.is_pivoting() and self.now() - start < 2.5:
                yaw = self.player.get_actor_rotation().yaw
                speed = self.player.get_velocity().length()
                peak_speed = max(peak_speed, speed)
                self.report['samples'].append(dict(side=side, time=self.now()-start,
                    yaw=yaw, speed=speed, progress=self.anim.get_editor_property('pivot_progress')))
                yield
            self.check('free_completes_' + str(side), not self.anim.is_pivoting())
            yaw_error = abs((self.player.get_actor_rotation().yaw - target + 180) % 360 - 180)
            self.check('free_final_facing_' + str(side), yaw_error < 7, error=yaw_error)
            self.check('free_velocity_finite_' + str(side), 100 < peak_speed < 1200, speed=peak_speed)
        yield from self.reversal('A', 'D', True, 'Left')
        self.check('locked_keeps_original', self.anim.get_current_active_montage().get_name().startswith('AM_Pivot_Left'))


old = getattr(builtins, '_free_pivot_regression', None)
assert not old or old.handle is None
runner = FreePivotRegression()
builtins._free_pivot_regression = runner
runner.handle = u.register_slate_post_tick_callback(runner.tick)
