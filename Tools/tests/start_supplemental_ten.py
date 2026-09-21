import runpy
import unreal as u
from pathlib import Path
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
pc = u.GameplayStatics.get_player_controller(world, 0)
preflight = {'viewport': list(pc.get_viewport_size()),
    'mass': u.SystemLibrary.get_console_variable_int_value('mass.FullyParallel'),
    'trace': u.TraceUtilLibrary.is_tracing(),
    'named': u.SystemLibrary.get_console_variable_float_value('stats.AutoEnableNamedEventsWhenProfiling'),
    'global': u.GameplayStatics.get_global_time_dilation(world),
    'paused': u.GameplayStatics.is_game_paused(world)}
assert preflight['viewport'] == [1920, 1080] and preflight['mass'] == 0, preflight
assert not preflight['trace'] and preflight['named'] == 0 and preflight['global'] == 1 and not preflight['paused'], preflight
print(preflight)
print(runpy.run_path(str(Path(u.Paths.project_dir()) / 'Tools/profiling/runtime_profile.py'))['start'](fights_per_cap=10))
