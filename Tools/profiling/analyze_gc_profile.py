"""Offline wall-time correlation; preserves every CSV frame and GC event."""
import argparse
import csv
import json
from pathlib import Path
import runpy

def analyze(report_path):
    report = json.loads(report_path.read_bytes())
    observation = report['gc_observation']
    csv_path = Path(report['performance_capture']['expected_path'])
    performance = runpy.run_path(str(Path(__file__).parents[1] / 'tests/analyze_performance.py'))['analyze'](csv_path, 0)
    ignored = set(performance['ignored_metadata_or_header_lines'])
    rows = list(csv.reader(csv_path.open(encoding='utf-8-sig', newline='')))
    header_index = next(i for i, row in enumerate(rows) if 'FrameTime' in row)
    header = rows[header_index]
    columns = {name: header.index(name) for name in ('FrameTime', 'GameThreadTime', 'GPUTime')}
    anchor = next(x['wall_since_start'] for x in observation['csv_command_anchors'] if x['command'] == 'CsvProfile START')
    stop = next(x['wall_since_start'] for x in observation['csv_command_anchors'] if x['command'] == 'CsvProfile STOP')
    events = [x for x in observation['events'] if anchor <= x['start_wall_since_start'] <= stop]
    ticks = [x for x in observation['tick_samples'] if x[2]]
    slow_ticks = [x for x in ticks if x[1] > 10]
    elapsed = 0.0
    hitches = []
    for line, row in enumerate(rows[header_index+1:], header_index+2):
        if line in ignored:
            continue
        frame_ms = float(row[columns['FrameTime']])
        begin, end = anchor+elapsed, anchor+elapsed+frame_ms/1000
        elapsed += frame_ms/1000
        if frame_ms <= 20:
            continue
        near_gc = sorted(events, key=lambda x: abs(x['end_wall_since_start']-end))[:1]
        near_tick = sorted(slow_ticks, key=lambda x: abs(x[0]+x[1]/1000-end))[:1]
        hitches.append({'csv_line': line, 'approx_start_wall': begin, 'approx_end_wall': end,
            'frame_ms': frame_ms, 'game_thread_ms': float(row[columns['GameThreadTime']]),
            'gpu_ms': float(row[columns['GPUTime']]),
            'nearest_gc': near_gc[0] if near_gc else None,
            'nearest_gc_end_offset_seconds': near_gc[0]['end_wall_since_start']-end if near_gc else None,
            'nearest_slow_tick': near_tick[0] if near_tick else None,
            'nearest_slow_tick_end_offset_seconds': near_tick[0][0]+near_tick[0][1]/1000-end if near_tick else None})
    return {'source_report': str(report_path.resolve()), 'performance': performance,
        'alignment_note': 'CSV START wall anchor plus cumulative FrameTime; possible one-frame offset. Nearest event is not proof of causation; inspect offset and duration.',
        'csv_duration_seconds': elapsed, 'command_span_seconds': stop-anchor,
        'gc_policy_unchanged': observation['gc_policy_unchanged'], 'hook_removed': observation['hook_removed'],
        'capture_gc_events': events, 'capture_tick_count': len(ticks),
        'capture_tick_max_ms': max((x[1] for x in ticks), default=0),
        'capture_slow_ticks_over_10ms': slow_ticks, 'all_hitches_over_20ms': hitches}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.report)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'hitches': len(result['all_hitches_over_20ms']),
        'gc_events': len(result['capture_gc_events']), 'slow_ticks': len(result['capture_slow_ticks_over_10ms']),
        'frame_statistics': result['performance']['metrics']['frame']['statistics']}))
