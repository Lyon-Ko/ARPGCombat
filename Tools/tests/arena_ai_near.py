"""Explicitly authorized 180cm neutral/Parry paired supplement, not natural bouts."""
import builtins
import collections
import datetime
from pathlib import Path
import runpy
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name('arena_ai_scenarios.py')))
KEY = '_combat_arena_ai_near'

class NearAI(BASE['AIScenarios']):
    def selection(self, action, seed, separation=400, wall=False):
        if separation == 400 and not wall and action in ('neutral', 'Parry'):
            yield from super().selection(action, seed, 180, False)

    def phase_case(self):
        return
        yield

    def run(self):
        self.report['reference_full_suite'] = 'arena_ai_scenarios_20260921T181713Z.json'
        self.report['scope'] = '64 real first-action observations at 180cm; paired neutral/Parry; no health injection'
        yield from super().run()
        rows = self.report['selections']
        self.report['distributions'] = {action: dict(collections.Counter(r.get('selected', 'NO_SELECTION')
            for r in rows if r['action'] == action)) for action in ('neutral', 'Parry')}
        pairs = {}
        for row in rows:
            pairs.setdefault(row['seed'], {})[row['action']] = row.get('selected')
        changed = sum(p.get('neutral') != p.get('Parry') for p in pairs.values())
        self.report['paired_changed_count'] = changed
        self.report['paired_seed_count'] = len(pairs)
        self.check('near.complete_64_observations', len(rows) == 64 and len(pairs) == 32)
        self.check('near.observed_action_response_changes', changed > 0, changed=changed)
        self.report['status'] = 'passed' if all(a['pass'] for a in self.report['assertions']) else 'failed'

def start():
    for key in (KEY, '_combat_arena_ai_scenarios', '_combat_arena_regression', '_combat_arena_spatial_visual'):
        prior = getattr(builtins, key, None)
        if prior and prior.handle is not None:
            raise RuntimeError('Another regression runner is active')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    runner = NearAI(seeds=32, output_name='arena_ai_near_'+stamp+'.json')
    setattr(builtins, KEY, runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return {'report_path': str(runner.path), 'active': True}

def stop():
    runner = getattr(builtins, KEY, None)
    if runner and runner.handle is not None:
        runner.report['status'] = 'stopped'
        runner.cleanup()
