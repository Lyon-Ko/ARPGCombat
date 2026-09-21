"""Explicitly authorized formal launch with read-only PIE preflight."""
import builtins
import json
from pathlib import Path
import runpy
import unreal as u

keys = ('_combat_arena_regression', '_combat_arena_ai_scenarios', '_combat_arena_ai_near',
        '_combat_arena_spatial_visual', '_combat_native_input_smoke')
active = [key for key in keys if getattr(getattr(builtins, key, None), 'handle', None) is not None]
assert not active, 'Active observers: '+str(active)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert world is not None, 'Actual PIE world required'
pc = u.GameplayStatics.get_player_controller(world, 0)
preflight = {'viewport': list(pc.get_viewport_size()),
    'paused': u.GameplayStatics.is_game_paused(world),
    'global_time_dilation': u.GameplayStatics.get_global_time_dilation(world),
    'active_runners': active, 'world': world.get_path_name(),
    'release_provenance_from_coordinator': {'content_tools_commit': '3a322b1',
        'editor_helper_commit': 'b480d8d', 'build_log': 'Build_Ribbon_10c.log', 'runtime': 'Build09 unchanged'}}
assert preflight['viewport'] == [1920,1080], preflight
assert not preflight['paused'], preflight
assert abs(preflight['global_time_dilation']-1) < .001, preflight
api = runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/start_acceptance.py'))
print(api['start']())
runner = builtins._combat_arena_regression
runner.report['formal_preflight'] = preflight
runner.save()
print(json.dumps(preflight))
