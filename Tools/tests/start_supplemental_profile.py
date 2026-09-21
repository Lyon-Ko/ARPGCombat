import runpy
import unreal as u
from pathlib import Path

api = runpy.run_path(str(Path(u.Paths.project_dir()) / 'Tools/profiling/runtime_profile.py'))
print(api['start']())
