"""Offline baseline-report persistence comparison; original evidence stays untouched."""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

root = Path(__file__).resolve().parents[2]
source = root/'Saved/Acceptance/arena_acceptance_20260921T185232088295Z.json'
raw = source.read_bytes()
data = json.loads(raw)
out = {'python': sys.version, 'source': str(source), 'source_bytes': len(raw),
       'source_sha256': hashlib.sha256(raw).hexdigest(), 'repetitions': 9,
       'measurement': 'Same object/fields, UTF-8 write_text+close+replace in Saved/Acceptance; no fsync, matches harness.',
       'results': {}}
target = root/'Saved/Acceptance/PersistenceBenchmark_scratch.json'
temp = target.with_suffix('.tmp')
for name, indent in [('indent2', 2), ('compact_default_encoder', None)]:
    samples = []
    for _ in range(9):
        start = time.perf_counter()
        text = json.dumps(data, ensure_ascii=False, indent=indent)
        serialized = time.perf_counter()
        temp.write_text(text, encoding='utf-8')
        temp.replace(target)
        end = time.perf_counter()
        samples.append({'serialization_ms': (serialized-start)*1000,
                        'write_replace_ms': (end-serialized)*1000, 'total_ms': (end-start)*1000})
    assert json.loads(text) == data
    out['results'][name] = {'bytes': len(text.encode('utf-8')), 'samples': samples,
        'median_ms': {key: statistics.median(s[key] for s in samples) for key in samples[0]}}
target.unlink()
assert source.read_bytes() == raw
path = root/'Saved/Acceptance/PersistenceBenchmark_20260921_baseline.json'
path.write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps({'report': str(path), 'results': {name:r['median_ms'] for name,r in out['results'].items()}}))
