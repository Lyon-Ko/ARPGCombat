import runpy
import unreal as u
from pathlib import Path
print(runpy.run_path(str(Path(u.Paths.project_dir()) / 'Tools/profiling/gc_profile.py'))['start']())
