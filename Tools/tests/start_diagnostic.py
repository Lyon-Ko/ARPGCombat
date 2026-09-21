"""Explicitly authorized single-round diagnostic bootstrap; run through project remote CLI."""
import unreal as u
import runpy
import json
from pathlib import Path

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert world is not None, 'PIE required'
was_paused = u.GameplayStatics.is_game_paused(world)
u.GameplayStatics.set_game_paused(world, False)
settings = {name: 2 for name in ('sg.ViewDistanceQuality', 'sg.AntiAliasingQuality',
    'sg.ShadowQuality', 'sg.GlobalIlluminationQuality', 'sg.ReflectionQuality',
    'sg.PostProcessQuality', 'sg.TextureQuality', 'sg.EffectsQuality',
    'sg.FoliageQuality', 'sg.ShadingQuality')}
settings.update({'r.ScreenPercentage': 100, 't.MaxFPS': 60, 'r.Streaming.PoolSize': 2048})
before = {name: u.SystemLibrary.get_console_variable_float_value(name) for name in settings}
for name, value in settings.items():
    u.SystemLibrary.execute_console_command(world, name+' '+str(value))
controller = u.GameplayStatics.get_player_controller(world, 0)
environment = {'viewport_actual': list(controller.get_viewport_size()), 'viewport_source': 'PlayerController.get_viewport_size',
               'initially_paused': was_paused,
               'cvars_before': before, 'cvars_requested': settings,
               'cvars_after': {name: u.SystemLibrary.get_console_variable_float_value(name) for name in settings}}
api = runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/arena_regression.py'))
print(api['start'](fps_caps=(60,), fights_per_cap=1))
import builtins
runner = builtins._combat_arena_regression
runner.report['diagnostic_environment'] = environment
runner.save()
print(json.dumps(environment))
