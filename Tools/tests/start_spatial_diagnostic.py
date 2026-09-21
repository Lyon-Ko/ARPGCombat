import runpy, unreal as u, datetime
from pathlib import Path
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
api=runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/arena_spatial_visual.py'))
print(api['start'](screenshots=True,output_name='arena_spatial_visual_'+stamp+'.json'))
