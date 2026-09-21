import runpy, unreal as u, datetime
from pathlib import Path
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
api=runpy.run_path(str(Path(u.Paths.project_dir())/'Tools/tests/arena_ai_scenarios.py'))
print(api['start'](seeds=32,output_name='arena_ai_scenarios_'+stamp+'.json'))
