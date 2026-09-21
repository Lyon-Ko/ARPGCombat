import builtins
import gc
import datetime
import json
from pathlib import Path
import unreal as u

keys = ['_combat_mass_profile', '_combat_trace_profile', '_combat_default_chain_only', '_combat_gc_profile', '_combat_arena_regression', '_combat_runtime_profile',
        '_combat_arena_ai_scenarios', '_combat_arena_spatial_visual',
        '_combat_arena_ai_near', '_combat_combined_sources',
        '_combat_build11_regression', '_combat_native_input_smoke']
rows = []
for key in keys:
    runner = getattr(builtins, key, None)
    if runner:
        rows.append(dict(runner=key, status=runner.report['status'],
                         callback_active=runner.handle is not None,
                         held_keys=list(getattr(runner, 'held_keys', [])),
                         delegate_bindings=len(getattr(runner, 'bindings', [])),
                         cleanup_errors=runner.report.get('cleanup_errors')))
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
pc = u.GameplayStatics.get_player_controller(world, 0)
report = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              runners=rows, pie_valid=u.SystemLibrary.is_valid(world),
              paused=u.GameplayStatics.is_game_paused(world),
              viewport_actual=list(pc.get_viewport_size()),
              global_time_dilation=u.GameplayStatics.get_global_time_dilation(world),
              gpu_csv=u.SystemLibrary.get_console_variable_float_value('r.GPUCsvStatsEnabled'),
              python_gc_enabled=gc.isenabled(), python_gc_threshold=list(gc.get_threshold()),
              trace_connected=u.TraceUtilLibrary.is_tracing(),
              named_events=u.SystemLibrary.get_console_variable_float_value('stats.AutoEnableNamedEventsWhenProfiling'),
              mass_fully_parallel=u.SystemLibrary.get_console_variable_int_value('mass.FullyParallel'),
              gc_observer_hook_removed=not any(getattr(getattr(cb, '__self__', None), 'hook', None) is cb for cb in gc.callbacks))
report['clean'] = all(not r['callback_active'] and not r['held_keys'] and
                      not r['delegate_bindings'] and not r['cleanup_errors'] for r in rows)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / ('FinalRemoteCleanup_'+stamp+'.json')
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
