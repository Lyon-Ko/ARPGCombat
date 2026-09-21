"""Explicit short default-chain validation. Import never starts PIE or testing."""
import builtins
import datetime
from pathlib import Path
import runpy
import statistics
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name('arena_regression.py')))
FORMAL = runpy.run_path(str(Path(__file__).with_name('start_acceptance.py')))
KEY = '_combat_default_chain_only'


class DefaultChainOnly(BASE['ArenaRegression']):
    def __init__(self):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        super().__init__(fps_caps=(30, 60), fights_per_cap=1,
                         output_name='default_chain_only_'+stamp+'.json')
        self.report.update(planned_natural_fights=0, planned_passive_death_round=None,
            scope='Only the unchanged default_four_hit_chain fixture at 30/60 caps; no natural bouts or CSV',
            release_provenance_from_coordinator={'content_tests_checkpoint': '3787b6c',
                'source_commit': '4542b8d', 'validation': 'DefaultChain_AssetValidation.json', 'runtime': 'Build14 linkage; unchanged Source4542b8d'})

    def run(self):
        yield from self.setup()
        self.report['runtime_build_hardware'] = FORMAL['runtime_metadata'](Path(__file__).resolve().parents[2])
        self.report['viewport_actual'] = list(self.controller.get_viewport_size())
        self.report['global_time_dilation'] = u.GameplayStatics.get_global_time_dilation(self.world)
        self.check('preflight.normal_time', abs(self.report['global_time_dilation']-1) < .001)
        for cap in self.caps:
            self.fps = cap
            u.SystemLibrary.execute_console_command(self.world, 't.MaxFPS '+str(cap))
            yield from self.wait(1)
            self.frame_steps = []
            yield from self.default_chain_case()
            yield from self.wait(1)
            median = statistics.median(self.frame_steps) if self.frame_steps else 0
            self.check('chain.cap_observed', median > 0 and abs(1/median-cap)/cap <= .15,
                       median_world_step=median, samples=len(self.frame_steps), requested_cap=cap,
                       allowed_relative_error=.15)
        self.report['status'] = 'passed' if all(a['pass'] for a in self.report['assertions']) else 'failed'
        self.report['accepts_twenty_rounds'] = False


def start():
    for key in (KEY, '_combat_arena_regression', '_combat_runtime_profile', '_combat_gc_profile',
                '_combat_arena_ai_scenarios', '_combat_arena_ai_near', '_combat_arena_spatial_visual',
                '_combat_combined_sources', '_combat_build11_regression', '_combat_native_input_smoke'):
        if getattr(getattr(builtins, key, None), 'handle', None) is not None:
            raise RuntimeError('Another test observer is active: '+key)
    runner = DefaultChainOnly()
    setattr(builtins, KEY, runner)
    setattr(builtins, '_combat_arena_regression', runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return status()


def status():
    runner = getattr(builtins, KEY, None)
    return {'status': runner.report['status'], 'active': runner.handle is not None,
            'report_path': str(runner.path)} if runner else {'status': 'not_started'}


def stop():
    runner = getattr(builtins, KEY, None)
    if runner and runner.handle is not None:
        runner.report['status'] = 'stopped'
        runner.cleanup()
    return status()

