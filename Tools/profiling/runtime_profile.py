"""Opt-in supplementary 3–10 bout profile; import never starts PIE or capture."""
import builtins
import datetime
import hashlib
from pathlib import Path
import runpy
import time
import traceback
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
FORMAL = runpy.run_path(str(PROJECT / "Tools/tests/start_acceptance.py"))
Acceptance = FORMAL["Acceptance"]
ArenaRegression = FORMAL["BASE"]["ArenaRegression"]
KEY = "_combat_runtime_profile"


class RuntimeProfile(Acceptance):
    def __init__(self, fights_per_cap=3):
        if type(fights_per_cap) is not int or not 3 <= fights_per_cap <= 10:
            raise ValueError("fights_per_cap must be an integer from 3 through 10")
        self.defer_writes = False
        self.deferred_requests = 0
        self.finishing = False
        self.finalized = False
        self.drain_started = None
        self.stable_since = None
        self.last_csv_stat = None
        super().__init__()
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.caps, self.rounds = (60,), fights_per_cap
        self.path = self.path.with_name("runtime_profile_"+stamp+".json")
        self.csv_name = "Combat_Supplemental_1080pHigh_60_"+stamp+".csv"
        self.csv_path = self.csv_path.with_name(self.csv_name)
        self.report.update(supplemental_profile=True, accepts_twenty_rounds=False,
                           requested_fps_caps=[60], fights_per_cap=self.rounds, planned_natural_fights=self.rounds,
                           planned_passive_death_round={"fps_cap":60,"round":self.rounds})
        self.report["execution"] = f"Supplementary real {self.rounds}-bout profile, same input bot/StateTree/effects; final bout passive natural defeat; NOT formal twenty-bout acceptance"
        self.report["performance_capture"].update(filename=self.csv_name, expected_path=str(self.csv_path),
            scope=f"{self.rounds} 60fps natural bouts and retry operations; existing input/defense/lifecycle warmup precedes capture; no long frames removed")
        self.report["write_strategy"] = {"mode":"defer_full_report_during_capture_and_csv_drain",
            "deferred_save_requests":0, "events_and_assertions":"All retained in memory without thinning",
            "final_write":"One complete report only after STOP and stable-file drain; abnormal process termination can lose in-memory evidence",
            "formal_comparison":"Formal acceptance retains its existing synchronous save cadence unchanged"}

    def save(self):
        self.report["accepts_twenty_rounds"] = False
        if self.defer_writes:
            self.deferred_requests += 1
            self.last_save = time.monotonic()
            return
        super().save()

    def natural_fight(self, number):
        if number == 1:
            self.report["acceptance_environment"]["requested_caps"] = [60]
            self.old_gpu_csv = u.SystemLibrary.get_console_variable_float_value("r.GPUCsvStatsEnabled")
            u.SystemLibrary.execute_console_command(self.world,"r.GPUCsvStatsEnabled 1")
            yield from self.wait(.1)
            capture = self.report["performance_capture"]
            capture.update(gpu_csv_before=self.old_gpu_csv,
                gpu_csv_active=u.SystemLibrary.get_console_variable_float_value("r.GPUCsvStatsEnabled"),
                pre_capture_wall_seconds=time.monotonic()-self.boot_wall,
                pre_capture_completed_bouts=len(self.report["natural_fights"]),
                warmup="Existing ArenaRegression input_cases, defense_cases and lifecycle_cases at60fps")
            self.check("capture.gpu_detail_enabled",capture["gpu_csv_active"]==1)
            # From this point even assertion-triggered saves only update fixed counters.
            self.defer_writes = True
            self.csv_command("CsvProfile STARTFILE="+self.csv_name)
            self.csv_command("CsvProfile START")
            self.csv_active = True
            capture.update(status="capture_requested",start_world_time=self.world_time())
        # Bypass only Acceptance's ten-bout CSV wrapper, not the real bot or assertions.
        yield from ArenaRegression.natural_fight(self,number)
        if number == self.rounds:
            self.stop_csv(f"completed_{self.rounds}_supplemental_bouts")

    def run(self):
        # Inherits exact viewport/High readback, DLL hashes, all warmup, all real
        # bouts and assertion checks, plus formal wrapper's CSV completion check.
        yield from super().run()
        self.report["accepts_twenty_rounds"] = False
        self.report["acceptance_environment"]["requested_caps"] = [60]

    def tick(self, delta):
        if self.finishing:
            if self.finalized:
                return
            try:
                self.drain()
            except Exception:
                self.record_failure("drain")
                self.finalize_once()
            return
        try:
            if self.world is not None:
                if not u.SystemLibrary.is_valid(self.world):
                    raise RuntimeError("PIE world ended during supplemental profile")
                now = self.world_time()
                if self.last_world_time is not None and now-self.last_world_time>.00001:
                    self.frame_steps.append(now-self.last_world_time)
                self.last_world_time = now
            next(self.generator)
            if time.monotonic()-self.last_save>1:
                self.save()
        except StopIteration:
            self.cleanup()
        except Exception:
            self.report["status"] = "failed"
            self.report["error"] = traceback.format_exc()
            self.cleanup()

    def cleanup(self):
        if self.finishing:
            return
        self.finishing = True
        self.defer_writes = True
        self.report["accepts_twenty_rounds"] = False
        self.drain_started = time.monotonic()
        try:
            self.generator.close()
            if self.world and u.SystemLibrary.is_valid(self.world):
                self.stop_csv("supplemental_cleanup")
        except Exception:
            self.record_failure("stop_csv_or_generator_close")
        try:
            self.release_keys()
        except Exception:
            self.record_failure("immediate_key_release")
        try:
            if self.player and u.SystemLibrary.is_valid(self.player):
                self.player.attack_released()
        except Exception:
            self.record_failure("immediate_attack_release")
        # Keep the Slate callback alive: never serialize on the STOP frame.

    def record_failure(self, phase):
        self.report["status"] = "failed"
        self.report.setdefault("supplemental_cleanup_errors",[]).append({"phase":phase,"error":traceback.format_exc()})

    def drain(self):
        now = time.monotonic()
        state = None
        if self.csv_path.exists():
            stat = self.csv_path.stat()
            state = (stat.st_size,stat.st_mtime_ns)
        if state != self.last_csv_stat:
            self.last_csv_stat, self.stable_since = state, now
        stable = bool(state and state[0]>0 and self.stable_since is not None
                      and now-self.stable_since>=1 and now-self.drain_started>=2)
        never_started = self.report["performance_capture"]["status"]=="not_started"
        if not stable and not never_started and now-self.drain_started<20:
            return
        self.report["performance_capture"]["post_stop_drain"] = {
            "stable":stable,"drain_wall_seconds":now-self.drain_started,
            "bytes":state[0] if state else 0,"minimum_stop_to_write_seconds":2,
            "note":"Stability is not CSV validity; analyze every CSV frame with warmup0 separately"}
        if not stable and not never_started:
            self.report["status"] = "failed"
        if stable:
            with self.csv_path.open("rb") as stream:
                self.report["performance_capture"]["sha256"] = hashlib.file_digest(stream,"sha256").hexdigest()
        self.finalize_once()

    def finalize_once(self):
        if self.finalized:
            return
        self.finalized = True
        # Parent cleanup catches restoration failures separately and unregisters
        # the callback. Never run it twice if final serialization then fails.
        try:
            super().cleanup()
        except Exception:
            self.record_failure("parent_cleanup")
        finally:
            # Defensive unregister only when parent did not already clear handle.
            if self.handle is not None:
                try:
                    u.unregister_slate_post_tick_callback(self.handle)
                except Exception:
                    self.record_failure("callback_unregister")
                self.handle = None
        self.report["write_strategy"]["deferred_save_requests"] = self.deferred_requests
        self.report["accepts_twenty_rounds"] = False
        self.defer_writes = False
        try:
            self.save()
        except Exception:
            self.record_failure("final_report_write")
            u.log_error("Supplemental profile final report could not be saved; in-memory report retained in builtins: " + traceback.format_exc())


def start(fights_per_cap=3):
    keys = (KEY,"_combat_arena_regression","_combat_arena_ai_scenarios","_combat_arena_ai_near",
            "_combat_arena_spatial_visual","_combat_build11_regression","_combat_combined_sources","_combat_native_input_smoke")
    for key in keys:
        other = getattr(builtins,key,None)
        if other and other.handle is not None:
            raise RuntimeError("Another runner is active; stop it before supplemental profiling")
    runner = RuntimeProfile(fights_per_cap=fights_per_cap)
    setattr(builtins,KEY,runner)
    # Existing formal/isolated guards already recognize the standard arena key.
    setattr(builtins,"_combat_arena_regression",runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return status()


def status():
    r = getattr(builtins,KEY,None)
    return {"status":r.report["status"],"active":r.handle is not None,"draining":r.finishing,
            "supplemental_profile":True,"accepts_twenty_rounds":False,"bouts":len(r.report["natural_fights"]),
            "deferred_save_requests":r.deferred_requests,"report_path":str(r.path)} if r else {"status":"not_started"}


def stop():
    r = getattr(builtins,KEY,None)
    if r and r.handle is not None and not r.finishing:
        r.report["status"] = "stopped"
        r.cleanup()
    return status()
