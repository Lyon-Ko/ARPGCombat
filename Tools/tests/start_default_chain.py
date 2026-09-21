import runpy
import unreal as u
from pathlib import Path
print(runpy.run_path(str(Path(u.Paths.project_dir()) / 'Tools/tests/default_chain_only.py'))['start']())
