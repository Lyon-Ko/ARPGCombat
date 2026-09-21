import runpy, unreal as u
from pathlib import Path
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert world and not u.GameplayStatics.is_game_paused(world)
assert abs(u.GameplayStatics.get_global_time_dilation(world)-1)<.001
assert tuple(u.GameplayStatics.get_player_controller(world,0).get_viewport_size())==(1920,1080)
print(runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/combined_sources.py'))['start']())
