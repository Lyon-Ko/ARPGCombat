"""Observe Python GC and Slate test callback costs without changing GC policy."""
import builtins
import gc
from pathlib import Path
import runpy
import time
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name('runtime_profile.py')))
KEY = '_combat_gc_profile'


class GCProfile(BASE['RuntimeProfile']):
    def __init__(self):
        super().__init__()
        self.path = self.path.with_name(self.path.name.replace('runtime_profile_', 'gc_profile_'))
        self.csv_name = self.csv_name.replace('Combat_Supplemental_', 'Combat_GCObserved_')
        self.csv_path = self.csv_path.with_name(self.csv_name)
        self.report['performance_capture'].update(filename=self.csv_name, expected_path=str(self.csv_path))
        self.gc_before = (gc.isenabled(), gc.get_threshold())
        self.gc_events = []
        self.tick_samples = []
        self.gc_pending = {}
        self.command_anchors = []
        self.hook = self.observe_gc
        self.observing = True
        self.report['gc_observation'] = {'mode': 'Python GC enabled; original thresholds unchanged',
            'enabled_before': self.gc_before[0], 'threshold_before': list(self.gc_before[1]),
            'hook_policy': 'perf_counter/monotonic and in-memory Python records only; no Unreal or disk calls',
            'tick_scope': 'Slate runner callback body, including synchronous Python GC if inside it; excludes final drain serialization',
            'tick_columns': ['start_wall_since_start', 'duration_ms', 'csv_active_at_start', 'slate_delta_seconds'],
            'alignment': 'CSV START command wall anchor; cumulative CSV FrameTime approximates relative time with a possible one-frame offset'}

    def observe_gc(self, phase, info):
        generation = info['generation']
        if phase == 'start':
            self.gc_pending[generation] = (time.perf_counter(), time.monotonic()-self.boot_wall)
        elif phase == 'stop':
            end = time.perf_counter()
            start = self.gc_pending.pop(generation, None)
            if start is not None:
                self.gc_events.append({'generation': generation, 'start_wall_since_start': start[1],
                    'end_wall_since_start': time.monotonic()-self.boot_wall,
                    'duration_ms': (end-start[0])*1000, 'collected': info.get('collected'),
                    'uncollectable': info.get('uncollectable')})

    def csv_command(self, command):
        self.command_anchors.append({'command': command, 'wall_since_start': time.monotonic()-self.boot_wall})
        super().csv_command(command)

    def tick(self, delta):
        start = time.perf_counter()
        wall = time.monotonic()-self.boot_wall
        active = self.csv_active
        try:
            super().tick(delta)
        finally:
            if self.observing:
                self.tick_samples.append((wall, (time.perf_counter()-start)*1000, active, delta))

    def finalize_once(self):
        if self.finalized:
            return
        self.observing = False
        if self.hook in gc.callbacks:
            gc.callbacks.remove(self.hook)
        observation = self.report['gc_observation']
        observation.update(events=self.gc_events, tick_samples=self.tick_samples,
            slow_callbacks_over_10ms=[list(x) for x in self.tick_samples if x[1]>10],
            csv_command_anchors=self.command_anchors,
            enabled_after=gc.isenabled(), threshold_after=list(gc.get_threshold()),
            hook_removed=self.hook not in gc.callbacks,
            gc_policy_unchanged=(gc.isenabled(), gc.get_threshold()) == self.gc_before,
            tick_count=len(self.tick_samples),
            tick_max_ms=max((x[1] for x in self.tick_samples), default=0),
            tick_total_ms=sum(x[1] for x in self.tick_samples),
            finalization_excluded='Final drain/hash/report serialization is outside CSV and not included in tick samples')
        super().finalize_once()


def start():
    for key in (KEY, '_combat_runtime_profile', '_combat_arena_regression',
                '_combat_arena_ai_scenarios', '_combat_arena_ai_near',
                '_combat_arena_spatial_visual', '_combat_combined_sources',
                '_combat_build11_regression', '_combat_native_input_smoke'):
        other = getattr(builtins, key, None)
        if other and other.handle is not None:
            raise RuntimeError('Another runner is active')
    if not gc.isenabled():
        raise RuntimeError('GC must already be enabled for this unchanged-policy observation')
    runner = GCProfile()
    setattr(builtins, KEY, runner)
    setattr(builtins, '_combat_runtime_profile', runner)
    setattr(builtins, '_combat_arena_regression', runner)
    gc.callbacks.append(runner.hook)
    try:
        runner.handle = u.register_slate_post_tick_callback(runner.tick)
        runner.save()
    except Exception:
        if runner.hook in gc.callbacks:
            gc.callbacks.remove(runner.hook)
        if runner.handle is not None:
            u.unregister_slate_post_tick_callback(runner.handle)
            runner.handle = None
        raise
    return {'report_path': str(runner.path), 'active': True}


def stop():
    return BASE['stop']()
