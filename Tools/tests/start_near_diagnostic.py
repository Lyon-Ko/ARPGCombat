import runpy, unreal as u
from pathlib import Path
print(runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/arena_ai_near.py'))['start']())
