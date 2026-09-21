"""Offline full-report serializer benchmark; never imports or operates Unreal."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tools/vendor/python311'))
import orjson

source = ROOT / 'Saved/Acceptance/arena_acceptance_20260921T185232088295Z.json'
raw = source.read_bytes()
data = json.loads(raw)

def validate(value):
    if isinstance(value, float):
        assert math.isfinite(value), 'Nonfinite source value cannot silently become JSON null'
    elif isinstance(value, dict):
        assert all(isinstance(k, str) for k in value)
        for child in value.values():
            validate(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate(child)

validate(data)
results = {}
for name, encode in (
    ('stdlib_pretty', lambda: json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')),
    ('stdlib_compact', lambda: json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')),
    ('orjson_compact', lambda: orjson.dumps(data)),
):
    samples = []
    for attempt in range(9):
        started = time.perf_counter()
        payload = encode()
        serialized = time.perf_counter()
        destination = ROOT / 'Saved/Acceptance/SerializerBenchmarkOutput.json'
        temporary = destination.with_suffix('.tmp')
        temporary.write_bytes(payload)
        temporary.replace(destination)
        finished = time.perf_counter()
        assert json.loads(payload) == data, name + ' changed report values'
        samples.append({'serialize_ms': (serialized-started)*1000,
                        'write_replace_ms': (finished-serialized)*1000,
                        'total_ms': (finished-started)*1000})
    results[name] = {'bytes': len(payload), 'roundtrip_equal': True,
        'median_ms': {key: statistics.median(row[key] for row in samples) for key in samples[0]},
        'samples': samples}
report = {'source': str(source), 'sha256': hashlib.sha256(raw).hexdigest(),
    'python': sys.version, 'orjson_version': orjson.__version__,
    'orjson_module': orjson.__file__, 'runs_each': 9, 'results': results,
    'scope': 'Offline serialization and atomic write of identical complete baseline JSON; not gameplay frame timing.'}
assert source.read_bytes() == raw
out = ROOT / 'Saved/Acceptance/SerializerBenchmark.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({name: result['median_ms'] for name, result in results.items()}, indent=2))
