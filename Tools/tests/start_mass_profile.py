import runpy
import unreal as u
from pathlib import Path
preflight = {'trace_connected': u.TraceUtilLibrary.is_tracing(),
             'named_events': u.SystemLibrary.get_console_variable_float_value('stats.AutoEnableNamedEventsWhenProfiling'),
             'mass_fully_parallel': u.SystemLibrary.get_console_variable_float_value('mass.FullyParallel')}
print(preflight)
assert not preflight['trace_connected'] and preflight['named_events'] == 0, preflight
assert preflight['mass_fully_parallel'] == 1, preflight
print(runpy.run_path(str(Path(u.Paths.project_dir()) / 'Tools/profiling/mass_profile.py'))['start']())
