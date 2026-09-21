"""Correlate exported Mass editor scopes with containing engine frames."""
import argparse
import bisect
import csv
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('scopes', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
with args.scopes.open(encoding='utf-8-sig', newline='') as stream:
    rows = list(csv.DictReader(stream))
def events(name):
    return sorted(({'start':float(r['StartTime']), 'end':float(r['EndTime']),
                    'ms':1000*float(r['Duration'])} for r in rows if r['TimerName']==name), key=lambda r:r['start'])
frames = events('FEngineLoop::Tick')
mass = events('UMassEntityEditorSubsystem::Tick')
starts = [r['start'] for r in mass]
long = []
for frame in frames:
    if frame['ms'] <= 25:
        continue
    left = bisect.bisect_left(starts, frame['start']-0.000001)
    right = bisect.bisect_right(starts, frame['end']+0.000001)
    inside = [r for r in mass[left:right] if r['end'] <= frame['end']+0.000001]
    long.append(dict(frame, mass_scopes=inside, mass_ms=sum(r['ms'] for r in inside)))
result = {'input':str(args.scopes.resolve()), 'frame_count':len(frames), 'mass_scope_count':len(mass),
          'threshold_ms':25, 'long_frames':long, 'mass_max_ms':max((r['ms'] for r in mass),default=0),
          'native_csv_begin_max_ms':max((r['ms'] for r in events('UpdateCoreCsvStats_BeginFrame')),default=0),
          'native_csv_end_max_ms':max((r['ms'] for r in events('UpdateCoreCsvStats_EndFrame')),default=0),
          'scope':'All matching exported engine frames, including trace-tail and stop boundaries. This diagnoses containing CPU scopes; it is not a frame-rate acceptance result or proof of the scheduler cause.',
          'nested_wait_evidence':'Separate full GameThread export longframe_5449 identifies WaitWithNamedThreadsSupport and Mass ProcessingQueue waits inside the Mass editor scope.'}
args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('long_frames','scope','nested_wait_evidence')}))
print(json.dumps(sorted(long,key=lambda r:r['ms'],reverse=True)[:8]))
