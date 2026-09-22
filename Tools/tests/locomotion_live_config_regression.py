"""Exercise unsaved Data Asset edits (the Details property path) and real physics."""
import builtins
from pathlib import Path
import re
import runpy
import unreal as u

Base = runpy.run_path(str(Path(__file__).with_name('ground_locomotion_regression.py')))['Regression']


class LiveConfigRegression(Base):
    def __init__(self):
        super().__init__()
        self.path = self.path.with_name('LocomotionLiveConfig.json')
        self.config = u.CombatLocomotionSubsystem.get_for_world(self.world)
        self.asset = self.config.get_configuration()
        self.check('data_asset_bound', isinstance(self.asset, u.CombatLocomotionConfig) and
                   self.player.get_editor_property('locomotion_config') == self.asset)
        schema = (Path(u.Paths.project_dir()) / 'Source/Combat/Public/CombatLocomotionParameters.inl').read_text(encoding='utf-8')
        self.properties = {}
        for kind, member, section, key in re.findall(r'^LOCO_(FLOAT|BOOL)\((\w+), (\w+), (\w+),', schema, re.M):
            prop = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', member)).lower()
            self.properties[(section, key)] = (prop, kind)
        self.original = self.snapshot()
        self.owned_values = dict(self.original)
        self.was_dirty = self.asset.get_outer() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        self.original_braking = self.config.get_parameter('Pivot', 'BrakingDeceleration')

    def snapshot(self):
        return {prop: self.asset.get_editor_property(prop) for prop, _ in self.properties.values()}

    def write(self, changes=None):
        assert self.snapshot() == self.owned_values, 'Asset changed externally; stopping without overwriting it'
        values = dict(self.original)
        for key, value in (changes or {}).items():
            prop, kind = self.properties[key]
            values[prop] = (value.lower() == 'true' if isinstance(value, str) else bool(value)) if kind == 'BOOL' else float(value)
        for prop, value in values.items():
            self.asset.set_editor_property(prop, value)
        self.owned_values = self.snapshot()

    def run(self):
        self.check('custom_movement_component', isinstance(self.move, u.CombatMovementComponent))
        revision = self.config.get_revision()
        self.write({('Movement', 'ForwardSpeed'): 220, ('Movement', 'BackwardSpeed'): 180,
                    ('Movement', 'LeftSpeed'): 200, ('Movement', 'RightSpeed'): 260, ('Animation', 'PlayRate'): .75,
                    ('Animation', 'JogSpeed'): 220, ('Camera', 'Distance'): 400, ('Camera', 'FOV'): 80})
        yield from self.wait(.4)
        self.check('unsaved_details_edit_applies', self.config.get_revision() > revision and not self.config.get_last_error())
        yield from self.fixture()
        self.key('W', True)
        yield from self.wait(.5)
        self.check('live_speed_applied', abs(self.player.get_velocity().length() - 220) < 2)
        self.check('live_animation_rate', abs(self.anim.get_editor_property('animation_play_rate') - .75) < .001)
        self.check('live_animation_threshold', abs(self.anim.get_editor_property('speed') - 350) < 2)
        # A preceding locked-camera case may leave the boom at 1000cm; allow its
        # intentionally smoothed return instead of assuming a 560cm start.
        deadline = self.now() + 2.
        while abs(self.player.camera_boom.get_editor_property('target_arm_length') - 400) >= 2 and self.now() < deadline:
            yield
        self.check('live_camera', abs(self.player.camera.get_editor_property('field_of_view') - 80) < .01 and
                   abs(self.player.camera_boom.get_editor_property('target_arm_length') - 400) < 2,
                   fov=self.player.camera.get_editor_property('field_of_view'),
                   distance=self.player.camera_boom.get_editor_property('target_arm_length'))
        for key, speed in [('S', 180), ('A', 200), ('D', 260)]:
            yield from self.fixture(locked=True)
            self.key(key, True)
            yield from self.wait(.5)
            self.check('live_directional_speed_' + key, abs(self.player.get_velocity().length() - speed) < 5,
                       expected=speed, actual=self.player.get_velocity().length())

        good_revision = self.config.get_revision()
        self.write({('Movement', 'Acceleration'): -10})
        yield from self.wait(.4)
        self.check('invalid_value_rejected_atomically', self.config.get_revision() == good_revision and
                   bool(self.config.get_last_error()) and self.config.get_parameter('Movement', 'ForwardSpeed') == 220)
        self.write({('Animation', 'JogSpeed'): 900, ('Animation', 'FastSpeed'): 650})
        yield from self.wait(.4)
        self.check('invalid_field_relationship_preserves_last_good', self.config.get_revision() == good_revision and
                   self.config.get_parameter('Movement', 'ForwardSpeed') == 220)

        self.write({('Pivot', 'BrakingDeceleration'): 300, ('Pivot', 'TurnRate'): 360,
                    ('Pivot', 'PlayRate'): .5})
        yield from self.wait(.4)
        self.check('valid_config_recovers', self.config.get_revision() > good_revision and not self.config.get_last_error())
        yield from self.reversal()
        yield from self.wait(.25)
        self.check('pivot_does_not_zero_velocity', self.player.get_velocity().x > 200 and not self.anim.is_pivot_accelerating())
        if self.anim.get_editor_property('free_pivot_left'):
            self.check('authored_turn_waits_for_clip_not_turn_rate', abs(self.player.get_actor_rotation().yaw) < 10)
        else:
            self.check('live_turn_rate', 50 < abs(self.player.get_actor_rotation().yaw) < 120)
        revision = self.config.get_revision()
        self.write({('Pivot', 'BrakingDeceleration'): 1800, ('Pivot', 'TurnRate'): 1080,
                    ('Pivot', 'ReverseAcceleration'): 300, ('Pivot', 'PlayRate'): .5})
        yield from self.wait(.3)
        self.check('reload_during_pivot', self.config.get_revision() > revision and self.anim.is_pivoting())
        deadline = self.now() + 1.5
        while not self.anim.is_pivot_accelerating() and self.now() < deadline:
            yield
        self.check('pivot_reverse_phase_reached', self.anim.is_pivot_accelerating())
        speed_before = -self.player.get_velocity().x
        yield from self.wait(.2)
        speed_after = -self.player.get_velocity().x
        self.check('live_reverse_acceleration', 30 < speed_after - speed_before < 95,
                   before=speed_before, after=speed_after)
        montage = self.anim.get_current_active_montage()
        position = self.anim.montage_get_position(montage)
        start = self.now()
        yield from self.wait(.2)
        ratio = (self.anim.montage_get_position(montage) - position) / (self.now() - start)
        self.check('live_pivot_play_rate', .42 < ratio < .58, observed=ratio)
        self.write({('Pivot', 'ReverseAcceleration'): 2400, ('Pivot', 'PlayRate'): .5})
        yield from self.wait(.4)
        self.check('live_reverse_acceleration_increase', -self.player.get_velocity().x > 500)
        self.write({('Pivot', 'Enabled'): 'false'})
        yield from self.wait(.4)
        self.check('disabling_pivot_releases_movement', not self.anim.is_pivoting() and self.player.get_velocity().length() > 400)
        self.write()
        yield from self.wait(.4)
        self.check('configuration_restored', not self.config.get_last_error() and
                   self.config.get_parameter('Pivot', 'BrakingDeceleration') == self.original_braking)

    def finish(self, error=None):
        try:
            if self.snapshot() == self.owned_values:
                for prop, value in self.original.items():
                    self.asset.set_editor_property(prop, value)
                self.config.reload_configuration()
                self.report['asset_values_restored'] = True
                # EditorAssetLibrary saving is blocked during PIE. The caller
                # may save the restored editor asset after ending the session.
                self.report['asset_save_deferred_until_pie_ends'] = not self.was_dirty
            else:
                error = (error or '') + '\nExternal asset edit preserved; automatic restore skipped.'
        except Exception as exc:
            error = (error or '') + '\nAsset restore failed: ' + repr(exc)
        finally:
            super().finish(error)


for key in ('_ground_locomotion_regression', '_ground_locomotion_visual', '_locomotion_live_config'):
    old = getattr(builtins, key, None)
    assert not old or old.handle is None, 'Another runner is active'
runner = LiveConfigRegression()
builtins._locomotion_live_config = runner
runner.handle = u.register_slate_post_tick_callback(runner.tick)
