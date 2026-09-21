"""Opt-in Mass scheduling comparison; no PIE, trace or GC changes on import."""
import builtins
import runpy
from pathlib import Path
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name('runtime_profile.py')))
RuntimeProfile = BASE['RuntimeProfile']
KEY = '_combat_mass_profile'
CVAR = 'mass.FullyParallel'


class MassProfile(RuntimeProfile):
    def __init__(self):
        self.mass_before = None
        super().__init__()
        stamp = self.path.stem.removeprefix('runtime_profile_')
        self.path = self.path.with_name('MassSingleThread_' + stamp + '.json')
        self.csv_name = 'Combat_MassSingleThread_1080pHigh_60_' + stamp + '.csv'
        self.csv_path = self.csv_path.with_name(self.csv_name)
        self.report['performance_capture'].update(filename=self.csv_name, expected_path=str(self.csv_path))
        self.report['mass_comparison'] = {
            'cvar': CVAR, 'requested': 0, 'before': None,
            'source': 'Engine/Source/Runtime/MassEntity/Private/MassProcessingPhaseManager.cpp:36,154,576-585',
            'meaning': 'Runs existing Mass phase processors serially; does not disable StateTree or processors',
            'limitations': 'Global Mass scheduling comparison, not editor-only disable; same three-bout bot/seed/High/deferred full JSON; not formal twenty; all long frames retained; no trace or GC changes'}

    def command_world(self):
        return self.world if self.world and u.SystemLibrary.is_valid(self.world) else u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()

    def run(self):
        self.mass_before = u.SystemLibrary.get_console_variable_int_value(CVAR)
        self.report['mass_comparison']['before'] = self.mass_before
        if self.mass_before not in (0, 1):
            raise RuntimeError('Unexpected Mass boolean CVar value')
        u.SystemLibrary.execute_console_command(self.command_world(), CVAR + ' 0')
        actual = u.SystemLibrary.get_console_variable_int_value(CVAR)
        self.report['mass_comparison']['active_readback'] = actual
        if actual != 0:
            raise RuntimeError('Mass single-thread readback failed')
        yield from super().run()

    def cleanup(self):
        # Parent handles a valid PIE world. End capture through editorWorld if
        # PIE disappeared, before starting its stable-file drain.
        if not self.finishing and self.csv_active and not (self.world and u.SystemLibrary.is_valid(self.world)):
            try:
                u.SystemLibrary.execute_console_command(self.command_world(), 'CsvProfile STOP')
                self.csv_active = False
                self.report['mass_comparison']['stop_world_fallback'] = True
            except Exception:
                self.record_failure('mass_stop_csv_fallback')
        super().cleanup()

    def finalize_once(self):
        if self.finalized:
            return
        try:
            if self.mass_before is not None:
                u.SystemLibrary.execute_console_command(self.command_world(), CVAR + ' ' + str(self.mass_before))
                actual = u.SystemLibrary.get_console_variable_int_value(CVAR)
                self.report['mass_comparison'].update(restored_readback=actual,
                    restore_after_drain=self.report['performance_capture'].get('post_stop_drain'))
                if actual != self.mass_before:
                    raise RuntimeError('Mass CVar restoration readback failed')
        except Exception:
            self.record_failure('mass_restore')
        finally:
            super().finalize_once()  # Always unregister, restore parent state and save full evidence.


def start():
    for key, other in vars(builtins).items():
        if key.startswith('_combat_') and getattr(other, 'handle', None) is not None:
            raise RuntimeError('Another Combat runner is active: ' + key)
    runner = MassProfile()
    for key in (KEY, BASE['KEY'], '_combat_arena_regression'):
        setattr(builtins, key, runner)
    try:
        runner.handle = u.register_slate_post_tick_callback(runner.tick)
        runner.save()
    except Exception:
        if runner.handle is not None:
            u.unregister_slate_post_tick_callback(runner.handle)
            runner.handle = None
        raise
    return status()


def status():
    return BASE['status']()


def stop():
    return BASE['stop']()
