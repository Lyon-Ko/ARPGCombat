"""Opt-in UE trace around RuntimeProfile's real three-bout deferred-JSON capture.

Import is inert. The editor owner calls start() in an existing authorized PIE.
start(max_capture_seconds=60) is an intentionally partial, bounded diagnostic;
the default 180 seconds allows the unchanged three-bout scenario to finish.
No game/GC tuning is added. RuntimeProfile's existing High setup is retained.

UE 5.8.2 source: Core/Private/ProfilingDebugging/TraceAuxiliary.cpp:1553,
Core/Private/Misc/CoreMisc.cpp:526, Launch/Private/LaunchEngineLoop.cpp:5636,
Plugins/TraceUtilities/Source/TraceUtilities/Public/TraceUtilLibrary.h.
"""
import builtins
import hashlib
import math
from pathlib import Path
import runpy
import time
import traceback
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name("runtime_profile.py")))
KEY = "_combat_trace_profile"
CHANNELS = ("cpu", "frame", "bookmark", "contextswitch")
NAMED_CVAR = "stats.AutoEnableNamedEventsWhenProfiling"


def contextswitch_evidence(enabled_readback, messages):
    denial = next((line for line in messages if "contextswitch" in line.lower()
                   and any(word in line.lower() for word in
                           ("cannot", "unable", "denied", "privilege", "unknown", "failed"))), None)
    return {"enabled_readback": enabled_readback,
            "availability": "unavailable" if denial or not enabled_readback else "unverified",
            "reason_if_unavailable": denial or (None if enabled_readback else
                "No enabled channel readback; inspect retained engine messages. Permission is not assumed."),
            "event_presence": "Not verified until offline Insights analysis",
            "evidence_priority": "Explicit engine denial overrides channel API readback"}


class TraceProfile(BASE["RuntimeProfile"]):
    def __init__(self, max_capture_seconds=180, max_trace_mib=512):
        if not math.isfinite(max_capture_seconds) or not 1 <= max_capture_seconds <= 600:
            raise ValueError("max_capture_seconds must be finite and within 1..600")
        if not isinstance(max_trace_mib, int) or not 1 <= max_trace_mib <= 2048:
            raise ValueError("max_trace_mib must be an integer within 1..2048")
        super().__init__()
        self.path = self.path.with_name(self.path.name.replace("runtime_profile_", "trace_profile_"))
        self.csv_name = self.csv_name.replace("Combat_Supplemental_", "Combat_TraceObserved_")
        self.csv_path = self.csv_path.with_name(self.csv_name)
        self.trace_path = self.csv_path.parent.parent / "Traces" / self.csv_name.replace(".csv", ".utrace")
        if self.trace_path.exists():
            raise RuntimeError("Unique trace destination already exists")
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_requested = False
        self.trace_stopped = False
        self.trace_seen = False
        self.trace_started_wall = None
        self.trace_stopped_wall = None
        self.trace_stop_requested_wall = None
        self.trace_stop_pending = False
        self.trace_stop_fallback_requested = False
        self.trace_settings_restored = False
        self.last_size_poll = 0.0
        self.trace_last_stat = None
        self.trace_stable_since = None
        self.named_before = None
        self.channels_before = {}
        self.trace_log_path = None
        self.trace_log_offset = 0
        self.capture_ticks = 0
        self.capture_tick_total_ms = 0.0
        self.capture_tick_max_ms = 0.0
        self.max_capture_seconds = float(max_capture_seconds)
        self.max_trace_bytes = max_trace_mib * 1024 * 1024
        self.report["performance_capture"].update(filename=self.csv_name, expected_path=str(self.csv_path))
        self.report["trace_capture"] = {
            "status": "not_started", "raw_trace_path": str(self.trace_path),
            "requested_channels": list(CHANNELS), "commands": [],
            "max_capture_wall_seconds": self.max_capture_seconds,
            "max_runner_wall_seconds": self.max_capture_seconds + 120,
            "max_trace_bytes": self.max_trace_bytes, "size_poll_interval_seconds": 1,
            "disconnect_timeout_seconds": 5,
            "ownership": "Refuse existing trace; stop only the connection requested by this runner",
            "named_events": {"method": NAMED_CVAR,
                "semantics": "Engine adds/removes its own named-event reference while CPU tracing; restore original CVar, never clear the global counter"},
            "limitations": [
                "Trace, named events, context-switch collection, CSV and the unchanged test callback add measurement overhead; this is diagnosis, not an uninstrumented frame-rate result.",
                "The 1-second size watchdog and Slate-tick wall-time watchdog can overshoot; they cannot interrupt a blocked editor or recover from process termination.",
                "A requested or enabled ContextSwitch channel does not prove scheduling events were captured; verify the trace. Engine denial messages are retained after capture.",
                "Trace starts in the CSV START hook and stops in the CSV STOP hook. Commands share a callback but boundaries are not claimed to be cycle-identical.",
                "All raw frames/events are retained. Limit-triggered stop is incomplete, never a three-bout or twenty-bout pass.",
                "Stable trace file and hash verify the artifact only; Insights analysis must establish useful event coverage. Trace timestamps may include engine uptime/tail history, so select export intervals using bookmarks/frames.",
            ],
        }

    def command_world(self):
        if self.world and u.SystemLibrary.is_valid(self.world):
            return self.world
        return u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()

    def trace_command(self, command):
        started = time.perf_counter()
        entry = {"command": command, "wall_since_start": time.monotonic() - self.boot_wall,
                 "world_time": self.world_time() if self.world and u.SystemLibrary.is_valid(self.world) else None}
        self.report["trace_capture"]["commands"].append(entry)
        try:
            u.SystemLibrary.execute_console_command(self.command_world(), command)
        finally:
            entry["command_call_ms"] = (time.perf_counter() - started) * 1000

    def start_trace(self):
        if u.TraceUtilLibrary.is_tracing():
            raise RuntimeError("Another trace is connected; this runner will not stop or replace it")
        capture = self.report["trace_capture"]
        self.channels_before = {name: bool(u.TraceUtilLibrary.is_channel_enabled(name)) for name in CHANNELS}
        self.named_before = u.SystemLibrary.get_console_variable_float_value(NAMED_CVAR)
        capture["channels_before"] = self.channels_before.copy()
        capture["named_events"]["before"] = self.named_before
        logs = list((BASE["PROJECT"] / "Saved/Logs").glob("Combat*.log"))
        if logs:
            self.trace_log_path = max(logs, key=lambda path: path.stat().st_mtime)
            self.trace_log_offset = self.trace_log_path.stat().st_size
            capture["engine_log"] = str(self.trace_log_path)
        self.trace_command(NAMED_CVAR + " 1")
        if u.SystemLibrary.get_console_variable_float_value(NAMED_CVAR) != 1:
            raise RuntimeError("Named-event auto toggler did not enable")
        capture["named_events"]["configured"] = 1
        # No other runner/trace owner may intervene between the guard and command.
        self.trace_requested = True
        self.trace_started_wall = time.monotonic()
        self.trace_command('Trace.File "' + self.trace_path.as_posix() + '" ' + ",".join(CHANNELS))
        capture.update(status="start_requested", start_wall_since_start=self.trace_started_wall - self.boot_wall)
        self.trace_command("Trace.Status")

    def stop_trace(self, reason):
        capture = self.report["trace_capture"]
        if self.trace_requested:
            if self.trace_stopped or self.trace_stop_pending:
                return
            # UE disconnect is asynchronous. Own the pending request before issuing
            # it, and never interpret same-callback is_tracing() as stop failure.
            self.trace_stop_pending = True
            self.trace_stop_requested_wall = time.monotonic()
            capture.update(status="stop_requested", stop_reason=reason,
                           stop_requested_wall_since_start=self.trace_stop_requested_wall - self.boot_wall)
            if u.TraceUtilLibrary.is_tracing():
                u.TraceUtilLibrary.trace_bookmark("CombatTrace_CSV_STOP_" + reason)
            self.trace_command("Trace.Stop")
        elif self.named_before is not None:
            self.restore_trace_settings()

    def poll_trace_stop(self):
        """One nonblocking poll per Slate/drain step; at most one delayed fallback."""
        if self.trace_stopped:
            if not self.trace_settings_restored:
                self.restore_trace_settings()
            return True
        if not self.trace_stop_pending:
            return False
        capture = self.report["trace_capture"]
        now = time.monotonic()
        if not u.TraceUtilLibrary.is_tracing():
            self.trace_stopped = True
            self.trace_stop_pending = False
            self.trace_stopped_wall = now
            capture.update(status="stopped", stop_wall_since_start=now - self.boot_wall,
                           disconnect_observed_seconds=now - self.trace_stop_requested_wall)
            self.restore_trace_settings()
            return True
        if now - self.trace_stop_requested_wall >= 5 and not self.trace_stop_fallback_requested:
            self.trace_stop_fallback_requested = True
            capture["stop_timeout"] = {"seconds": now - self.trace_stop_requested_wall,
                "reason": "Owned trace remained connected for at least 5 seconds after Trace.Stop"}
            self.report["status"] = "failed"
            call = {"call": "TraceUtilLibrary.stop_tracing", "wall_since_start": now - self.boot_wall}
            capture.setdefault("fallback_calls", []).append(call)
            # No immediate second query: the fallback is also asynchronous.
            call["returned"] = bool(u.TraceUtilLibrary.stop_tracing())
        return False

    def restore_trace_settings(self):
        capture = self.report["trace_capture"]
        if self.named_before is not None:
            if u.SystemLibrary.get_console_variable_float_value(NAMED_CVAR) != self.named_before:
                self.trace_command(NAMED_CVAR + " " + str(self.named_before))
            after = u.SystemLibrary.get_console_variable_float_value(NAMED_CVAR)
            capture["named_events"].update(after=after, restored=after == self.named_before)
            if after != self.named_before:
                raise RuntimeError("Named-event CVar restoration failed")
        # Trace.Stop leaves channel toggles enabled. Restore only requested channels.
        for name, before in self.channels_before.items():
            if bool(u.TraceUtilLibrary.is_channel_enabled(name)) != before:
                u.TraceUtilLibrary.toggle_channel(name, before)
        after_channels = {name: bool(u.TraceUtilLibrary.is_channel_enabled(name)) for name in self.channels_before}
        capture["channels_restored"] = after_channels == self.channels_before
        capture["channels_after"] = after_channels
        if after_channels != self.channels_before:
            raise RuntimeError("Trace channel restoration failed")
        self.trace_settings_restored = True

    def csv_command(self, command):
        if command == "CsvProfile START":
            self.start_trace()
        try:
            super().csv_command(command)
        finally:
            if command == "CsvProfile STOP":
                self.stop_trace("csv_stop")

    def tick(self, delta):
        measured = self.csv_active and not self.finishing
        started = time.perf_counter()
        try:
            self.poll_trace_stop()
            if not self.finishing:
                now = time.monotonic()
                if now - self.boot_wall > self.max_capture_seconds + 120:
                    self.report["status"] = "stopped"
                    self.report["trace_capture"]["limit_reached"] = "runner_wall_time"
                    self.cleanup()
                    return
                if self.trace_requested and not self.trace_stopped and not self.trace_stop_pending:
                    if not self.trace_seen and u.TraceUtilLibrary.is_tracing():
                        self.trace_seen = True
                        enabled = {name: bool(u.TraceUtilLibrary.is_channel_enabled(name)) for name in CHANNELS}
                        self.report["trace_capture"]["enabled_channels_readback"] = enabled
                        if not all(enabled[name] for name in ("cpu", "frame", "bookmark")):
                            raise RuntimeError("Required trace channels did not enable")
                        u.TraceUtilLibrary.trace_bookmark("CombatTrace_CSV_START_OBSERVED")
                    if not self.trace_seen and now - self.trace_started_wall > 2:
                        raise RuntimeError("Trace connection was not observed within 2 seconds")
                    limit = "capture_wall_time" if now - self.trace_started_wall >= self.max_capture_seconds else None
                    if now - self.last_size_poll >= 1:
                        self.last_size_poll = now
                        if self.trace_path.exists() and self.trace_path.stat().st_size > self.max_trace_bytes:
                            limit = "trace_bytes"
                    if limit:
                        self.report["status"] = "stopped"
                        self.report["trace_capture"]["limit_reached"] = limit
                        self.cleanup()
                        return
            super().tick(delta)
        except Exception:
            self.report["status"] = "failed"
            self.report["trace_capture"]["error"] = traceback.format_exc()
            self.cleanup()
        finally:
            if measured:
                elapsed = (time.perf_counter() - started) * 1000
                self.capture_ticks += 1
                self.capture_tick_total_ms += elapsed
                self.capture_tick_max_ms = max(self.capture_tick_max_ms, elapsed)

    def cleanup(self):
        # The fallback works even when the PIE world has ended or generator.close fails.
        try:
            super().cleanup()
        finally:
            try:
                self.stop_trace("cleanup")
            except Exception:
                self.record_failure("owned_trace_stop_or_restore")

    def drain(self):
        if self.trace_requested:
            self.poll_trace_stop()
            now = time.monotonic()
            state = None
            if self.trace_path.exists():
                stat = self.trace_path.stat()
                state = (stat.st_size, stat.st_mtime_ns)
            if state != self.trace_last_stat:
                self.trace_last_stat, self.trace_stable_since = state, now
            stable = bool(state and state[0] > 0 and self.trace_stopped
                          and self.trace_stable_since is not None and now - self.trace_stable_since >= 1
                          and now - self.drain_started >= 2)
            if not stable and now - self.drain_started < 20:
                return
            capture = self.report["trace_capture"]
            capture.update(file_stable=stable, bytes=state[0] if state else 0, connected_after_stop=bool(u.TraceUtilLibrary.is_tracing()))
            if not stable or capture["connected_after_stop"] or capture.get("stop_timeout"):
                self.report["status"] = "failed"
            elif "sha256" not in capture:
                with self.trace_path.open("rb") as stream:
                    capture["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        super().drain()

    def finalize_once(self):
        if self.finalized:
            return
        try:
            self.stop_trace("finalize")
            self.poll_trace_stop()
        except Exception:
            self.record_failure("final_trace_restore")
        capture = self.report["trace_capture"]
        if capture.get("stop_timeout") or (self.trace_requested and not self.trace_stopped):
            self.report["status"] = "failed"
        capture["settings_restore_pending"] = self.named_before is not None and not self.trace_settings_restored
        capture["runner_callback_observation"] = {"samples": self.capture_ticks,
            "max_ms": self.capture_tick_max_ms, "total_ms": self.capture_tick_total_ms,
            "scope": "Captured Slate runner callback, including trace watchdog; excludes native trace work outside callback and finalization"}
        if self.trace_log_path:
            try:
                with self.trace_log_path.open("rb") as stream:
                    stream.seek(self.trace_log_offset)
                    text = stream.read(262144).decode("utf-8", errors="replace")
                capture["engine_trace_messages"] = [line for line in text.splitlines()
                    if any(word in line.lower() for word in ("trace", "channel", "named event"))][-100:]
            except Exception as exc:
                capture["engine_log_read_error"] = repr(exc)
        context_enabled = capture.get("enabled_channels_readback", {}).get("contextswitch", False)
        capture["contextswitch"] = contextswitch_evidence(context_enabled, capture.get("engine_trace_messages", []))
        super().finalize_once()


def start(max_capture_seconds=180, max_trace_mib=512):
    for name in (KEY, "_combat_gc_profile", "_combat_runtime_profile", "_combat_arena_regression",
                 "_combat_arena_ai_scenarios", "_combat_arena_ai_near", "_combat_arena_spatial_visual",
                 "_combat_build11_regression", "_combat_combined_sources", "_combat_native_input_smoke"):
        previous = getattr(builtins, name, None)
        if previous and previous.handle is not None:
            raise RuntimeError("Another runner is active")
    if not hasattr(u, "TraceUtilLibrary"):
        raise RuntimeError("Existing TraceUtilities reflection is required; this tool installs nothing")
    if u.TraceUtilLibrary.is_tracing():
        raise RuntimeError("Another trace is connected; leave it untouched")
    if Path(u.Paths.project_dir()).resolve() != BASE["PROJECT"]:
        raise RuntimeError("Wrong project: expected " + str(BASE["PROJECT"]))
    runner = TraceProfile(max_capture_seconds, max_trace_mib)
    setattr(builtins, KEY, runner)
    setattr(builtins, "_combat_runtime_profile", runner)
    setattr(builtins, "_combat_arena_regression", runner)
    try:
        runner.handle = u.register_slate_post_tick_callback(runner.tick)
        runner.save()
    except Exception:
        if runner.handle is not None:
            u.unregister_slate_post_tick_callback(runner.handle)
            runner.handle = None
        raise
    return status()


def status():
    runner = getattr(builtins, KEY, None)
    if not runner:
        return {"status": "not_started"}
    return {"status": runner.report["status"], "active": runner.handle is not None,
            "draining": runner.finishing, "report_path": str(runner.path),
            "raw_trace_path": str(runner.trace_path), "trace_requested": runner.trace_requested,
            "trace_stopped": runner.trace_stopped, "trace_stop_pending": runner.trace_stop_pending,
            "bouts": len(runner.report["natural_fights"]),
            "accepts_twenty_rounds": False}


def stop():
    runner = getattr(builtins, KEY, None)
    if runner and runner.handle is not None and not runner.finishing:
        runner.report["status"] = "stopped"
        runner.cleanup()
    return status()
