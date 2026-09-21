import datetime
import json
from pathlib import Path
import runpy
import time
import unreal as u

project = Path(u.Paths.project_dir()).resolve()
api = runpy.run_path(str(project/'Tools/tests/arena_regression.py'))
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
r = api['ArenaRegression'](fps_caps=(60,),fights_per_cap=1,output_name='SerializerUE_'+stamp+'.json')
source = project/'Saved/Acceptance/arena_acceptance_20260921T185232088295Z.json'
r.report = json.loads(source.read_text(encoding='utf-8'))
r.report['serializer_smoke_only'] = 'Copy of baseline evidence used solely for serialization validation; not another gameplay run.'
start = time.perf_counter()
r.save()
duration = (time.perf_counter()-start)*1000
disk = json.loads(r.path.read_bytes())
assert disk['natural_fights'] == r.report['natural_fights']
assert disk['assertions'] == r.report['assertions']
rejections = []
for value in (float('nan'),float('inf'),float('-inf')):
    try:
        api['assert_finite_json']({'nested':[value]})
    except ValueError:
        rejections.append(True)
    else:
        rejections.append(False)
assert all(rejections)
print(json.dumps({'backend':api['SERIALIZER'],'save_ms':duration,'copied_report':str(r.path),
                  'gameplay_fields_equal':True,'nonfinite_rejected':rejections}))
