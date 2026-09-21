"""Formal 20-bout + UE CSV entry. Import is inert; call start() only when authorized."""
import builtins
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import runpy
import time
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name('arena_regression.py')))
KEY = '_combat_arena_regression'

def runtime_metadata(project):
    result = {'engine_version': u.SystemLibrary.get_engine_version(),
              'build_version': u.SystemLibrary.get_build_version(),
              'os': platform.platform(), 'machine_architecture': platform.machine(),
              'python_processor': platform.processor(), 'binaries': []}
    # Observe actual scheduling/instrumentation; never alter these conditions.
    result['profiling_conditions'] = {
        'cvars': {name: u.SystemLibrary.get_console_variable_int_value(name) for name in (
            'mass.FullyParallel', 'mass.UseProcessingQueue', 'stats.AutoEnableNamedEventsWhenProfiling')},
        'trace_is_tracing': bool(u.TraceUtilLibrary.is_tracing()),
        'interpretation': 'Read-only snapshot; named-events value is the auto-enable policy, not proof of an active trace.'}
    for name in ('UnrealEditor-Combat.dll', 'UnrealEditor-CombatEditor.dll'):
        path = project/'Binaries/Win64'/name
        if path.exists():
            result['binaries'].append({'path': str(path), 'size': path.stat().st_size,
                'mtime_utc': datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat(),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    # Runtime log evidence rather than a hardcoded future build / adapter label.
    logs = list((project/'Saved/Logs').glob('Combat*.log'))
    if logs:
        log = max(logs, key=lambda p: p.stat().st_mtime)
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
        pattern = re.compile(r'LogInit: OS:|Using Default RHI:|Chosen .*Adapter|RHI Adapter Info:|LogRHI:.*(?:Name:|Driver Version:|Driver Date:)|LogD3D12RHI:.*(?:Found D3D12 adapter|Driver Version:)')
        result['hardware_rendering_log_evidence'] = {'path': str(log),
            'mtime_utc': datetime.datetime.fromtimestamp(log.stat().st_mtime, datetime.timezone.utc).isoformat(),
            'lines': [line for line in lines if pattern.search(line)],
            'interpretation': 'Newest Combat log observed at run time; includes discovered adapters as well as chosen-adapter evidence.'}
    return result

class Acceptance(BASE['ArenaRegression']):
    def __init__(self):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        super().__init__(fps_caps=(30, 60), fights_per_cap=10,
                         output_name='arena_acceptance_'+stamp+'.json')
        self.csv_name = 'Combat_1080pHigh_60_'+stamp+'.csv'
        self.csv_path = Path(u.Paths.project_saved_dir()).resolve()/'Profiling/CSV'/self.csv_name
        self.csv_active = False
        self.old_gpu_csv = None
        self.shot_before = None
        self.shot_directory = Path(u.Paths.project_saved_dir()).resolve()/'Screenshots'
        self.report['performance_capture'] = {'filename': self.csv_name,
            'expected_path': str(self.csv_path), 'status': 'not_started',
            'warmup_frames_to_exclude': 0,
            'scope': 'All 60fps bouts 1..10, including reset, test callbacks, JSON persistence and all slow frames.',
            'analysis': 'analyze_performance.py <CSV> --warmup-frames 0; do not remove long frames or callback overhead.'}

    def on_started(self, actor, skill):
        super().on_started(actor, skill)
        if (self.fps == 30 and self.current and self.current.get('kind') == 'natural_input_bot_fight'
                and self.current.get('round') == 2 and actor == self.player
                and self.world_time()-self.current.get('combat_started_world_time', self.world_time()) > 3
                and 'natural_combat_screenshot' not in self.report):
            self.shot_before = {str(p) for p in self.shot_directory.rglob('*.png')}
            self.report['natural_combat_screenshot'] = {'round': 2, 'fps_cap': 30,
                'request_world_time': self.world_time(), 'stage': 'combat',
                'global_time_dilation': u.GameplayStatics.get_global_time_dilation(self.world),
                'player_custom_time_dilation': float(self.player.get_editor_property('custom_time_dilation')),
                'viewport': list(self.controller.get_viewport_size()),
                'note': 'Normal natural bout; native hitstop remains enabled. UE Shot SHOWUI captures a later render frame. Screenshot overhead stays in 30fps timings, outside 60fps CSV.'}
            u.SystemLibrary.execute_console_command(self.world, 'Shot SHOWUI')

    def tick(self, delta):
        super().tick(delta)
        shot = self.report.get('natural_combat_screenshot')
        if shot and 'path' not in shot and self.world and self.world_time()-shot['request_world_time'] >= .2:
            new = [p for p in self.shot_directory.rglob('*.png') if str(p) not in self.shot_before]
            if new:
                path = min(new, key=lambda p: p.stat().st_mtime)
                shot.update(path=str(path), file_bytes=path.stat().st_size, file_observed_world_time=self.world_time())

    def csv_command(self, command):
        u.SystemLibrary.execute_console_command(self.world, command)
        self.report['performance_capture'].setdefault('commands', []).append({
            'command': command, 'world_time': self.world_time(), 'wall_since_start': time.monotonic()-self.boot_wall})

    def stop_csv(self, reason):
        if self.csv_active:
            self.csv_command('CsvProfile STOP')
            self.csv_active = False
            self.report['performance_capture'].update(status='stop_requested', stop_reason=reason,
                                                       stop_world_time=self.world_time())

    def natural_fight(self, number):
        if self.fps == 60 and number == 1:
            self.old_gpu_csv = u.SystemLibrary.get_console_variable_float_value('r.GPUCsvStatsEnabled')
            u.SystemLibrary.execute_console_command(self.world, 'r.GPUCsvStatsEnabled 1')
            yield from self.wait(.1)
            capture = self.report['performance_capture']
            capture.update(gpu_csv_before=self.old_gpu_csv,
                           gpu_csv_active=u.SystemLibrary.get_console_variable_float_value('r.GPUCsvStatsEnabled'),
                           pre_capture_wall_seconds=time.monotonic()-self.boot_wall,
                           pre_capture_completed_bouts=len(self.report['natural_fights']))
            self.check('capture.gpu_detail_enabled', capture['gpu_csv_active'] == 1)
            self.check('capture.prewarmed_30fps_bouts', capture['pre_capture_completed_bouts'] == 10)
            self.csv_command('CsvProfile STARTFILE='+self.csv_name)
            self.csv_command('CsvProfile START')
            self.csv_active = True
            capture.update(status='capture_requested', start_world_time=self.world_time())
        yield from super().natural_fight(number)
        if self.fps == 60 and number == 10:
            self.stop_csv('completed_all_ten_60fps_bouts')

    def run(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world:
            raise RuntimeError('Existing authorized floating PIE required; this entry does not launch UE/PIE')
        u.GameplayStatics.set_game_paused(self.world, False)
        pc = u.GameplayStatics.get_player_controller(self.world, 0)
        if not pc:
            raise RuntimeError('Actual PIE PlayerController required')
        groups = ('ViewDistance','AntiAliasing','Shadow','GlobalIllumination','Reflection',
                  'PostProcess','Texture','Effects','Foliage','Shading')
        settings = {'sg.'+name+'Quality': 2 for name in groups}
        settings.update({'sg.ResolutionQuality': 100, 'r.ScreenPercentage': 100, 'r.VSync': 0,
                         'r.Streaming.PoolSize': 2048, 'r.MotionBlurQuality': 0})
        before = {name: u.SystemLibrary.get_console_variable_float_value(name) for name in settings}
        for name, value in settings.items():
            u.SystemLibrary.execute_console_command(self.world, name+' '+str(value))
        after = {name: u.SystemLibrary.get_console_variable_float_value(name) for name in settings}
        project = Path(u.Paths.project_dir()).resolve()
        self.report['acceptance_environment'] = {'viewport_actual': list(pc.get_viewport_size()),
            'viewport_source': 'PlayerController.get_viewport_size', 'map': self.world.get_path_name(),
            'mode': 'PIE', 'requested_caps': [30, 60], 'cvars_before': before,
            'cvars_requested': settings, 'cvars_after': after, 'runtime_build_hardware': runtime_metadata(project)}
        self.check('environment.exact_1080p_viewport', tuple(pc.get_viewport_size()) == (1920, 1080),
                   actual=list(pc.get_viewport_size()))
        self.check('environment.high_settings_readback', all(abs(after[n]-v) < .001 for n,v in settings.items()),
                   actual=after)
        yield from super().run()
        self.report['status'] = 'finalizing_capture'
        self.report['accepts_twenty_rounds'] = False
        # CsvProfile STOP writes asynchronously; keep ticking, never block UE.
        deadline = time.monotonic()+30
        previous_size, stable_since, stable = None, None, False
        while time.monotonic() < deadline:
            size = self.csv_path.stat().st_size if self.csv_path.exists() else 0
            if size > 0 and size == previous_size:
                if stable_since is not None and time.monotonic()-stable_since >= 1:
                    stable = True
                    break
            else:
                previous_size, stable_since = size, time.monotonic()
            yield
        ready = stable and self.csv_path.exists() and self.csv_path.stat().st_size > 0
        self.report['performance_capture'].update(status='file_observed' if ready else 'missing_file',
            bytes=self.csv_path.stat().st_size if ready else 0,
            note='Nonzero stable file observed; offline CSV parser must still validate completeness and columns.')
        self.check('capture.file_written', ready)
        passed = all(a['pass'] for a in self.report['assertions'])
        self.report['status'] = 'passed' if passed else 'failed'
        self.report['accepts_twenty_rounds'] = passed and len(self.report['natural_fights']) == 20

    def cleanup(self):
        try:
            if self.world and u.SystemLibrary.is_valid(self.world):
                self.stop_csv('exception_or_stop_cleanup')
                if self.old_gpu_csv is not None:
                    u.SystemLibrary.execute_console_command(self.world, 'r.GPUCsvStatsEnabled '+str(self.old_gpu_csv))
                    self.report['performance_capture']['gpu_csv_restored'] = u.SystemLibrary.get_console_variable_float_value('r.GPUCsvStatsEnabled')
        except Exception as exc:
            self.report['performance_capture']['cleanup_error'] = repr(exc)
            self.report['status'] = 'failed'
            self.report['accepts_twenty_rounds'] = False
        finally:
            super().cleanup()

def start():
    for key in (KEY, '_combat_arena_ai_scenarios', '_combat_arena_ai_near', '_combat_arena_spatial_visual',
                '_combat_build11_regression', '_combat_combined_sources', '_combat_native_input_smoke'):
        previous = getattr(builtins, key, None)
        if previous and previous.handle is not None:
            raise RuntimeError('Another test runner is active; stop it before acceptance')
    runner = Acceptance()
    setattr(builtins, KEY, runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return status()

def status():
    return BASE['status']()

def stop():
    return BASE['stop']()
