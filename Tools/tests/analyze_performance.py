"""Offline UE CSV Profiler analysis. No Unreal dependency; all timing units are ms."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def percentile(values, p):
    ordered = sorted(values)
    position = (len(ordered)-1)*p
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(position-lo)


def summarize(values):
    if not values:
        return None
    worst_count = max(1, math.ceil(len(values)*.01))
    worst_mean = statistics.mean(sorted(values, reverse=True)[:worst_count])
    return {"samples": len(values), "mean_ms": statistics.mean(values),
            "median_ms": statistics.median(values), "p95_ms": percentile(values,.95),
            "p99_ms": percentile(values,.99), "max_ms": max(values),
            "one_percent_low_fps": 1000/worst_mean if worst_mean > 0 else None,
            "one_percent_tail_samples": worst_count,
            "over_threshold_fraction": {str(t): sum(v>t for v in values)/len(values) for t in (16.7,20.0,33.3)},
            "zero_samples": sum(v==0 for v in values)}


def analyze(path, warmup_frames, gpu_column=None):
    if warmup_frames < 0:
        raise ValueError("warmup_frames cannot be negative")
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    header_index = next((i for i,row in enumerate(rows) if "FrameTime" in row), None)
    if header_index is None:
        raise ValueError("No exact FrameTime header: input must be an uncompressed UE CSV Profiler CSV")
    header = rows[header_index]
    names = {"frame": "FrameTime", "gpu": gpu_column or "GPUTime",
             "render_thread": "RenderThreadTime", "game_thread": "GameThreadTime"}
    indices = {}
    for metric, name in names.items():
        if header.count(name)>1:
            raise ValueError("Ambiguous duplicate column: "+name)
        indices[metric] = header.index(name) if name in header else None
    samples, ignored, extended_headers = [], [], []
    for line,row in enumerate(rows[header_index+1:], header_index+2):
        if not row or row==header:
            ignored.append(line)
            continue
        # UE appends dynamically discovered stat columns to its final header.
        # It preserves the complete initial header prefix, so all selected timing
        # indices remain valid. This is a header row, never a numerical frame.
        if len(row) > len(header) and row[:len(header)] == header:
            extended_headers.append({'line': line, 'additional_columns': row[len(header):]})
            ignored.append(line)
            continue
        frame_index = indices["frame"]
        if len(row)<=frame_index:
            if row[0].lstrip().startswith("["):
                ignored.append(line)
                continue
            raise ValueError(f"Malformed data row at line {line}")
        try:
            frame = float(row[frame_index])
        except ValueError as exc:
            if row[0].lstrip().startswith("["):
                ignored.append(line)  # Metadata only after ruling out a numeric FrameTime.
                continue
            raise ValueError(f"Non-numeric FrameTime at line {line}: {row[frame_index]!r}") from exc
        if not math.isfinite(frame) or frame<0:
            raise ValueError(f"Invalid FrameTime at line {line}")
        samples.append((line,row))
    retained = samples[warmup_frames:]
    if not retained:
        raise ValueError("No samples remain after explicit warmup exclusion")
    report = {"input_csv": str(Path(path).resolve()), "unit": "milliseconds", "input_samples": len(samples),
              "warmup_frames_requested": warmup_frames, "excluded_warmup_frames": min(warmup_frames,len(samples)),
              "retained_frame_samples": len(retained), "ignored_metadata_or_header_lines": ignored,
              "extended_final_headers": extended_headers,
              "percentile_definition": "linear interpolation at (N-1)*p over sorted frame times",
              "one_percent_low_definition": "1000 / mean of the slowest ceil(N*0.01) retained timing samples; frame metric is FPS, thread/GPU metrics are timing-equivalent rates, not delivered FPS",
              "threshold_definition": "strictly greater than 16.7,20,33.3 milliseconds; fractions in [0,1]",
              "long_frame_policy": "No clipping, outlier removal or long-frame exclusion", "metrics": {}}
    for metric,index in indices.items():
        if index is None:
            report["metrics"][metric] = {"status":"missing_column", "expected_column":names[metric], "statistics":None}
            continue
        values,missing = [],[]
        for line,row in retained:
            if index>=len(row) or row[index].strip()=="":
                missing.append(line)
                continue
            value = float(row[index])
            if not math.isfinite(value) or value<0:
                raise ValueError(f"Invalid {names[metric]} at line {line}")
            values.append(value)
        report["metrics"][metric] = {"status":"partial" if missing else "present", "column":names[metric],
            "missing_sample_lines":missing, "statistics":summarize(values),
            "warning":"All timing values zero; do not interpret as measured performance" if values and not any(values) else None}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--warmup-frames",type=int,required=True,help="Explicit leading frame exclusion; use 0 to retain every frame")
    parser.add_argument("--gpu-column",help="Explicit exact GPU timing column override; no pass/category sums inferred")
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    result = json.dumps(analyze(args.csv,args.warmup_frames,args.gpu_column),ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(result+"\n",encoding="utf-8")
    print(result)


if __name__=="__main__":
    main()
