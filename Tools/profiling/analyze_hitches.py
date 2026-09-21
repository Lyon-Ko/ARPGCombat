"""List every >20ms CSV frame with largest recorded game-thread timing scopes."""
import argparse
import csv
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    origin = report['performance_capture']['start_world_time']
    checkpoints = []
    for fight in report['natural_fights']:
        for key in ('combat_started_world_time', 'combat_ended_world_time'):
            if key in fight:
                checkpoints.append({'round': fight['round'], 'event': key, 'world_time': fight[key]})
        if 'post_retry' in fight:
            checkpoints.append({'round': fight['round'], 'event': 'post_retry', 'world_time': fight['post_retry']['world_time']})
    hitches, elapsed, frame_count = [], 0.0, 0
    with args.csv.open(encoding='utf-8-sig', newline='') as stream:
        rows = csv.reader(stream)
        header = next(rows)
        index = header.index('FrameTime')
        cpu = [(i,n) for i,n in enumerate(header) if n.startswith(('Exclusive/GameThread/', 'Slate/GameThread/'))]
        totals = [(header.index(n),n) for n in ('GameThreadTime','RenderThreadTime','GPUTime','RHIThreadTime') if n in header]
        for line, row in enumerate(rows, 2):
            try:
                duration = float(row[index])
            except (ValueError, IndexError):
                continue  # Only this explanatory listing; strict full-frame parser is separate.
            frame_count += 1
            elapsed += duration/1000
            if duration <= 20:
                continue
            scopes = sorted([(n,float(row[i])) for i,n in cpu if i<len(row) and row[i]], key=lambda t:t[1], reverse=True)
            approx = origin+elapsed
            nearest = min(checkpoints, key=lambda p:abs(p['world_time']-approx)) if checkpoints else None
            hitches.append({'csv_line':line, 'frame_index':frame_count, 'frame_ms':duration,
                'approx_world_time':approx, 'elapsed_ms_from_frame_sum':elapsed*1000,
                'totals':{n:float(row[i]) for i,n in totals}, 'largest_cpu_scopes':scopes[:8],
                'nearest_checkpoint':nearest, 'checkpoint_offset_seconds':approx-nearest['world_time'] if nearest else None})
    output = {'csv':str(args.csv.resolve()), 'report':str(args.report.resolve()), 'frames_seen':frame_count,
        'threshold_ms':20, 'hitches':hitches,
        'scope':'All >20ms numeric frames; explanatory scope timings are recorded nested engine categories, not additive independent costs. World alignment from CSV frame sums is approximate (capture begins asynchronously). Original strict performance analysis retains every frame.'}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    for h in hitches:
        print(json.dumps({k:h[k] for k in ('frame_index','frame_ms','largest_cpu_scopes','nearest_checkpoint','checkpoint_offset_seconds')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
