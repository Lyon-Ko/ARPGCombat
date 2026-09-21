import unreal as u
import json,math
from pathlib import Path
data=json.loads((Path(u.Paths.project_saved_dir())/'Acceptance/NativeTracePIE.json').read_text())
for case in data:
    minimum=(1e9,None,None)
    limits=(.11/.68,.215/.68) if case['skill'].startswith('Boss') else (.14,.32)
    for sample in case['samples']:
        if not limits[0]<sample['elapsed']<limits[1]: continue
        for i in range(21):
            point=[a+(b-a)*i/20 for a,b in zip(sample['base'],sample['tip'])]
            target=sample['target']; dz=max(0,abs(point[2]-target[2])-60)
            distance=math.sqrt((point[0]-target[0])**2+(point[1]-target[1])**2+dz**2)
            if distance<minimum[0]:minimum=(distance,sample['montage'],point)
    print('CLOSEST',case['skill'],case['distance'],'damage',case['damage'],'axis_distance',minimum)
