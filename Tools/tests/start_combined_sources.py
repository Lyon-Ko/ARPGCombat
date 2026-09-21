import runpy, unreal as u
from pathlib import Path
print(runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/combined_sources.py'))['start']())
