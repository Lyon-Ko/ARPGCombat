"""Opt-in PIE regression. Importing this module never starts PIE or a test.

After coordinator approval: runpy.run_path(...)["start"](). The live runner is
retained in builtins._combat_arena_regression. All waits yield to Slate.
"""
import builtins
import collections
import datetime
import json
import math
from pathlib import Path
import statistics
import sys
import time
import traceback
import unreal as u

KEY = "_combat_arena_regression"
VENDOR = Path(__file__).resolve().parents[1] / "vendor/python311"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
try:
    import orjson as _orjson
    SERIALIZER = {"backend": "orjson", "version": _orjson.__version__, "vendor": str(VENDOR)}
except ImportError as exc:
    _orjson = None
    SERIALIZER = {"backend": "stdlib-json", "fallback_reason": str(exc)}

def assert_finite_json(value):
    """orjson maps NaN/Inf to null; reject them explicitly instead of changing evidence."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("Non-finite float in evidence; refusing silent null conversion")
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, (list, tuple)):
            pending.extend(item)


def tag(name):
    value = u.GameplayTag()
    if not value.import_text('(TagName="' + name + '")'):
        raise ValueError("GameplayTag conversion failed: " + name)
    return value


def tag_name(value):
    return str(value.get_editor_property("tag_name"))


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(xyz(a), xyz(b))))


class ArenaRegression:
    def __init__(self, fps_caps=(30, 60), fights_per_cap=10,
                 fight_timeout=180.0, require_paragon=True, output_name=None):
        if tuple(fps_caps) not in ((30,), (60,), (30, 60), (60, 30)):
            raise ValueError("fps_caps must contain 30 and/or 60, without duplicates")
        if fights_per_cap < 1 or fight_timeout < 10:
            raise ValueError("Invalid round count or timeout")
        self.caps = tuple(fps_caps)
        self.rounds = int(fights_per_cap)
        self.fight_timeout = float(fight_timeout)
        self.require_paragon = require_paragon
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = output_name or "arena_regression_" + stamp + ".json"
        if Path(name).name != name or not name.endswith(".json"):
            raise ValueError("output_name must be a JSON filename, not a path")
        self.path = Path(u.Paths.project_saved_dir()) / "Acceptance" / name
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.report = {"schema": 1, "status": "starting", "started_utc": stamp,
                       "accepts_twenty_rounds": False,
                       "execution": "real PIE actors; no time dilation or health tuning",
                       "requested_fps_caps": self.caps, "fights_per_cap": self.rounds,
                       "planned_natural_fights": len(self.caps)*self.rounds,
                       "planned_passive_death_round": {"fps_cap": self.caps[0], "round": self.rounds} if len(self.caps)*self.rounds > 1 else None,
                       "fight_timeout_world_seconds": self.fight_timeout,
                       "standalone_injected_cases": [], "input_cases": [], "natural_fights": [],
                       "assertions": [], "timing": {}, "events": [],
                       "limitations": ["Synthetic ReceiveCombatHit cases test public hit receipt, not weapon trace geometry.",
                                       "Natural fights use real movement and public player input methods; Boss StateTree remains active.",
                                       "Frame cap requests are verified against observed world-time steps; no fixed timestep or speedup is applied.",
                                       "Component residual checks cover components owned/attached to the two characters; world transient actors are separately counted."]}
        self.world = self.player = self.boss = self.ai = self.brain = None
        self.handle = None
        self.bindings = []
        self.skill_serial = collections.Counter()
        self.current = None
        self.fps = None
        self.frame_steps = []
        self.last_world_time = None
        self.last_save = 0.0
        self.inject_id = 1_600_000_000
        self.old_cap = None
        self.old_seed = None
        self.cancelled = False
        self.controller = None
        self.held_keys = set()
        self.old_paused = None
        self.boot_wall = time.monotonic()
        self.generator = self.run()

    def world_time(self):
        return float(u.GameplayStatics.get_time_seconds(self.world))

    def save(self):
        save_started = time.perf_counter()
        self.report["updated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.report["elapsed_wall_seconds"] = round(time.monotonic()-self.boot_wall, 3)
        self.report["persistence_format"] = "accelerated-json-v3; identical fields/history/save cadence; timings cover prior completed saves"
        self.report["serializer"] = SERIALIZER
        timing = self.report.setdefault("persistence_timing", {"attempts": 0, "serialization_ms_total": 0.0,
            "write_replace_ms_total": 0.0, "total_ms_total": 0.0, "max_total_ms": 0.0})
        temp = self.path.with_suffix(".tmp")
        assert_finite_json(self.report)
        payload = (_orjson.dumps(self.report) if _orjson is not None
                   else json.dumps(self.report, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        serialized = time.perf_counter()
        temp.write_bytes(payload)
        try:
            temp.replace(self.path)
        except PermissionError:
            # Windows readers can briefly hold the JSON without delete-sharing.
            # Preserve the complete .tmp journal and retry on the next Slate tick;
            # never sleep/block the game thread or turn a file-reader race into a
            # gameplay failure. The main report remains the prior atomic version.
            self.report["persistence_retry_count"] = self.report.get("persistence_retry_count", 0)+1
            self.report["pending_report_journal"] = str(temp)
            return
        finally:
            finished = time.perf_counter()
            duration = (finished-save_started)*1000
            timing["attempts"] += 1
            timing["serialization_ms_total"] += (serialized-save_started)*1000
            timing["write_replace_ms_total"] += (finished-serialized)*1000
            timing["total_ms_total"] += duration
            timing["max_total_ms"] = max(timing["max_total_ms"], duration)
        self.report.pop("pending_report_journal", None)
        self.last_save = time.monotonic()

    def check(self, name, ok, **evidence):
        row = {"name": name, "pass": bool(ok), "fps_cap": self.fps, **evidence}
        self.report["assertions"].append(row)
        if self.current is not None:
            self.current.setdefault("assertions", []).append(row)
        self.save()
        return bool(ok)

    def wait(self, seconds, wall_limit=None):
        start = self.world_time()
        wall = time.monotonic()
        while self.world_time()-start < seconds:
            if time.monotonic()-wall > (wall_limit or seconds*3+5):
                raise TimeoutError("World stopped advancing during nonblocking wait")
            yield

    def key(self, name, pressed):
        # Track before dispatch so cleanup also releases a key if dispatch raises.
        if pressed:
            self.held_keys.add(name)
        accepted = u.CombatEditorLibrary.inject_player_key(self.controller, name, pressed)
        if not pressed:
            self.held_keys.discard(name)
        # InputKey returns handled, not delivery success; polled WASD may return
        # false even though PlayerInput stored its state. Assert gameplay effects.
        self.event("key", self.player, key=name, pressed=pressed, handled=bool(accepted))

    def release_keys(self):
        errors = []
        for name in list(self.held_keys):
            try:
                self.key(name, False)
            except Exception as exc:
                errors.append(name + ": " + repr(exc))
        if errors:
            raise RuntimeError("Key release failures: " + "; ".join(errors))

    def tap(self, name, duration=.055):
        self.key(name, True)
        try:
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                yield
        finally:
            self.key(name, False)
        yield  # Allow PC to consume the queued key on a game tick.

    def state(self, actor):
        anim = actor.get_editor_property("mesh").get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        return {"alive": actor.is_alive(), "busy": actor.is_busy(),
                "parry": actor.is_parry_window_active(), "health": actor.get_health(),
                "max_health": actor.get_max_health(), "poise": actor.get_poise(),
                "max_poise": actor.get_max_poise(), "active_skill": tag_name(actor.get_active_skill_tag()),
                "phase_two": bool(actor.get_editor_property("phase_two")),
                "custom_time_dilation": float(actor.get_editor_property("custom_time_dilation")),
                "location": xyz(actor.get_actor_location()), "montage": montage.get_path_name() if montage else None}

    def role(self, actor):
        return "player" if actor == self.player else "boss" if actor == self.boss else "other"

    def event(self, kind, actor, **values):
        row = {"type": kind, "actor": self.role(actor), "world_time": round(self.world_time(), 6),
               "wall_time": round(time.monotonic()-self.boot_wall, 6), **values}
        if self.current is not None:
            row["stage"] = self.current.get("stage", "isolated")
            self.current.setdefault("events", []).append(row)
        else:
            self.report["events"].append(row)

    def on_feedback(self, source, target, cue, location, intensity):
        combo = self.current is not None and self.current.get("name") == "default_four_hit_chain"
        self.event("feedback", source, target=self.role(target), cue=tag_name(cue),
                   location=xyz(location), intensity=float(intensity),
                   **({"target_health": target.get_health(), "source_skill": tag_name(source.get_active_skill_tag())}
                      if combo and target in (self.player, self.boss) else {}))

    def on_started(self, actor, skill):
        self.skill_serial[self.role(actor)] += 1
        self.event("skill_started", actor, skill=tag_name(skill), location=xyz(actor.get_actor_location()),
                   velocity=xyz(actor.get_velocity()))

    def on_ended(self, actor, skill):
        self.event("skill_ended", actor, skill=tag_name(skill), location=xyz(actor.get_actor_location()),
                   velocity=xyz(actor.get_velocity()), interrupted=bool(actor.get_editor_property("last_skill_interrupted")))

    def on_death(self, actor):
        self.event("death", actor)

    def stop_ai(self):
        self.brain.stop_logic("ArenaRegression isolated setup")
        self.ai.stop_movement()

    def reset_isolated(self):
        self.release_keys()
        for actor in (self.player, self.boss):
            actor.attack_released()
            actor.reset_combat_state()
            actor.get_editor_property("character_movement").stop_movement_immediately()
        self.stop_ai()
        self.player.set_combat_target(self.boss)
        self.boss.set_combat_target(self.player)

    def components(self, actor):
        result = {}
        components = list(actor.get_components_by_class(u.ActorComponent))
        for attr in ("mesh", "weapon_mesh"):
            components += list(actor.get_editor_property(attr).get_children_components(True))
        for comp in components:
            if u.SystemLibrary.is_valid(comp):
                result[comp.get_path_name()] = comp.get_class().get_name()
        return result

    def residuals(self):
        projectiles = u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatProjectile)
        owned = [p.get_path_name() for p in projectiles if p.get_owner() in (self.player, self.boss)]
        components = {self.role(a): sorted(set(self.components(a))-set(self.baseline[self.role(a)]))
                      for a in (self.player, self.boss)}
        return {"owned_projectiles": owned, "world_projectile_count": len(projectiles),
                "new_character_components": components}

    def assert_clean(self, label, revived=False):
        residual = self.residuals()
        self.check(label+".projectiles", not residual["owned_projectiles"], **residual)
        self.check(label+".components", not any(residual["new_character_components"].values()), **residual)
        for actor in (self.player, self.boss):
            s = self.state(actor)
            clean = not s["busy"] and not s["parry"] and s["active_skill"] in ("None", "", "Invalid")
            self.check(label+"."+self.role(actor)+".idle", clean, observed=s)
            if revived:
                self.check(label+"."+self.role(actor)+".revived",
                           s["alive"] and abs(s["health"]-s["max_health"]) < .01
                           and abs(s["poise"]-s["max_poise"]) < .01
                           and not s["phase_two"] and abs(s["custom_time_dilation"]-1) < .001,
                           observed=s)
                self.check(label+"."+self.role(actor)+".montage_stopped", s["montage"] is None, observed=s)

    def hit(self, receiver, attacker, damage=5, instance=None, parryable=True):
        if instance is None:
            self.inject_id += 1
            instance = self.inject_id
        hit = u.CombatHit(attacker=attacker, damage=float(damage), poise_damage=0.0,
                          location=receiver.get_actor_location(), direction=u.Vector(-1, 0, 0),
                          parryable=parryable, attack_instance=instance)
        return receiver.receive_combat_hit(hit)

    def defense_cases(self):
        for name, at, back, expected in [("front_inside", .10, False, u.CombatHitResult.PARRIED),
                                         ("front_near_end", .15, False, u.CombatHitResult.PARRIED),
                                         ("front_outside", .24, False, u.CombatHitResult.DAMAGED),
                                         ("back_inside", .10, True, u.CombatHitResult.DAMAGED)]:
            case = {"name": name, "fps_cap": self.fps, "kind": "injected_hit_receipt", "events": []}
            self.report["standalone_injected_cases"].append(case)
            self.current = case
            self.reset_isolated()
            p = self.player.get_actor_location()
            self.player.set_actor_rotation(u.Rotator(roll=0, pitch=0, yaw=0), True)
            self.boss.set_actor_location(u.Vector(p.x+(-350 if back else 350), p.y, p.z), False, True)
            yield from self.wait(.2)
            self.player.parry_pressed()
            started = self.world_time()
            active = tag_name(self.player.get_active_skill_tag()) == "Combat.Skill.Parry"
            self.check(name+".activated", active)
            if not active:
                continue
            skill_started = self.world_time()-self.player.get_skill_elapsed_time()
            yield from self.wait(at)
            # Preserve the observed BeginSkill origin even if Parry has ended.
            elapsed = self.world_time()-skill_started
            tolerance = 1.5/self.fps+.005
            scheduled = at-.0001 <= elapsed <= at+tolerance and (elapsed <= .2 if at < .2 else elapsed > .2)
            before = self.player.get_health()
            result = self.hit(self.player, self.boss)
            case.update(requested_elapsed=at, receipt_elapsed=elapsed, scheduling_tolerance=tolerance,
                        world_since_public_parry_call=self.world_time()-started,
                        result=str(result), health_before=before, health_after=self.player.get_health())
            self.check(name+".timing", scheduled, requested=at, actual=elapsed, tolerance=tolerance)
            self.check(name+".result", result == expected, expected=str(expected), actual=str(result))
            expected_health = before if expected == u.CombatHitResult.PARRIED else before-5
            self.check(name+".health", abs(self.player.get_health()-expected_health) < .01)
        case = {"name": "dedup_interleaved", "fps_cap": self.fps, "kind": "injected_hit_receipt"}
        self.report["standalone_injected_cases"].append(case)
        self.current = case
        self.reset_isolated()
        self.inject_id += 2
        old, new = self.inject_id-1, self.inject_id
        before = self.player.get_health()
        results = [self.hit(self.player, self.boss, instance=i) for i in (old, old, new, old)]
        self.check("dedup.sequence", results == [u.CombatHitResult.DAMAGED, u.CombatHitResult.MISS,
                                                  u.CombatHitResult.DAMAGED, u.CombatHitResult.MISS],
                   actual=[str(r) for r in results])
        self.check("dedup.health", abs(before-self.player.get_health()-10) < .01)
        self.current = None

    def lifecycle_cases(self):
        case = {"name": "cancel_death_retry", "fps_cap": self.fps,
                "kind": "isolated lifecycle; explicit lethal hit injection; NOT a natural fight", "events": []}
        self.report["standalone_injected_cases"].append(case)
        self.current = case
        self.reset_isolated()
        p = self.player.get_actor_location()
        self.boss.set_actor_location(u.Vector(p.x+1500, p.y, p.z), False, True)
        activated = self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.AOE"))
        self.check("lifecycle.aoe_activated", activated)
        if activated:
            yield from self.wait(.12)
            self.boss.show_area_warning()  # Public composition hook, marked isolated lifecycle.
            self.boss.emit_skill_projectile()
            case["spawned_before_cancel"] = self.residuals()
            self.check("lifecycle.projectile_precondition", bool(case["spawned_before_cancel"]["owned_projectiles"]))
        hp = self.player.get_health()
        self.boss.cancel_current_skill()
        yield from self.wait(1.5)
        self.assert_clean("cancel")
        self.check("cancel.no_late_damage", abs(hp-self.player.get_health()) < .01)
        # A previous canceled skill may legitimately retain its cooldown. Reset
        # this independent death fixture rather than misclassifying that as a bug.
        self.reset_isolated()
        p = self.player.get_actor_location()
        self.boss.set_actor_location(u.Vector(p.x+1500, p.y, p.z), False, True)
        activated = self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.AOE"))
        self.check("lifecycle.death_skill_activated", activated)
        if activated:
            self.boss.show_area_warning()
            self.boss.emit_skill_projectile()
        result = self.hit(self.boss, self.player, self.boss.get_max_health()*2, parryable=False)
        self.check("death.result", result == u.CombatHitResult.KILLED, result=str(result))
        yield from self.wait(.2)
        self.check("death.dead", not self.boss.is_alive())
        self.check("death.rejects_skill", not self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.AOE")))
        self.assert_clean("death")
        yield from self.tap("R")
        self.stop_ai()
        yield from self.wait(.25)
        self.assert_clean("retry", revived=True)
        self.check("retry.parry_cooldown_cleared", self.player.get_skill_cooldown_remaining(tag("Combat.Skill.Parry")) <= .001)
        self.player.parry_pressed()
        self.check("retry.input_works", tag_name(self.player.get_active_skill_tag()) == "Combat.Skill.Parry")
        self.player.cancel_current_skill()
        self.current = None
        yield from self.cancel_reopen_case()

    def cancel_reopen_case(self):
        case = {"name": "cancel_armed_timer_then_reopen", "fps_cap": self.fps,
                "kind": "isolated lifecycle; explicit public AreaRelease hook; NOT a natural fight",
                "events": []}
        self.report["standalone_injected_cases"].append(case)
        self.current = case
        self.reset_isolated()
        p = self.player.get_actor_location()
        self.boss.set_actor_location(u.Vector(p.x+200, p.y, p.z), False, True)
        yield from self.wait(.2)
        self.check("reopen.aoe_started", self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.AOE")))
        self.boss.show_area_warning()
        self.boss.detonate_area()  # Arm the real .18s timer before interruption.
        armed_at = self.world_time()
        hp = self.player.get_health()
        yield from self.wait(.04)
        self.boss.cancel_current_skill()
        self.check("reopen.old_skill_ended", not self.boss.is_busy())
        activated = self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.LeapBack"))
        self.check("reopen.successor_started", activated)
        # The old timer is due at .18s; successor's projectile is authored later
        # (.27/.95s), so this interval has no legitimate successor damage.
        yield from self.wait(.16)
        self.check("reopen.old_deadline_observed", self.world_time()-armed_at >= .18,
                   elapsed_since_arm=self.world_time()-armed_at)
        self.check("reopen.no_old_timer_damage", abs(self.player.get_health()-hp) < .01,
                   health_before=hp, health_after=self.player.get_health(),
                   successor=tag_name(self.boss.get_active_skill_tag()))
        self.check("reopen.successor_not_cleared", tag_name(self.boss.get_active_skill_tag()) == "Combat.Skill.Boss.LeapBack")
        self.boss.cancel_current_skill()
        yield from self.wait(.35)
        self.assert_clean("reopen.final_cancel")
        self.current = None

    def input_cases(self):
        yield from self.default_chain_case()
        directions = [("W",), ("W", "D"), ("D",), ("S", "D"),
                      ("S",), ("S", "A"), ("A",), ("W", "A")]
        for keys, expected_degrees in zip(directions, range(0, 360, 45)):
            self.reset_isolated()
            if self.player.get_editor_property("target_locked"):
                self.player.toggle_target_lock()
            self.controller.set_control_rotation(u.Rotator(roll=0, pitch=0, yaw=0))
            self.player.set_actor_rotation(u.Rotator(roll=0, pitch=0, yaw=0), True)
            p = self.player.get_actor_location()
            self.boss.set_actor_location(u.Vector(p.x+1800, p.y, p.z), False, True)
            yield from self.wait(.3)
            case = {"name": "dash_" + "_".join(keys), "fps_cap": self.fps,
                    "kind": "real_PC_InputKey", "events": []}
            self.report["input_cases"].append(case)
            self.current = case
            for key in keys:
                self.key(key, True)
            yield
            before = self.player.get_actor_location()
            started = self.world_time()
            try:
                yield from self.tap("LeftShift", .01)
                self.check(case["name"]+".started", tag_name(self.player.get_active_skill_tag()) == "Combat.Skill.Dash")
            finally:
                self.release_keys()
            yield from self.wait(.32)
            after = self.player.get_actor_location()
            dx, dy = after.x-before.x, after.y-before.y
            length = math.hypot(dx, dy)
            observed = math.degrees(math.atan2(dy, dx)) % 360
            error = abs((observed-expected_degrees+180) % 360-180)
            # 250 cm configured dash; allow one frame of approach / braking.
            tolerance_cm = 35 + 650/self.fps
            self.check(case["name"]+".trajectory", abs(length-250) <= tolerance_cm and error <= 12,
                       distance_cm=length, expected_cm=250, tolerance_cm=tolerance_cm,
                       observed_angle=observed, expected_angle=expected_degrees, angle_error=error,
                       elapsed=self.world_time()-started)
        self.reset_isolated()
        case = {"name": "double_jump", "fps_cap": self.fps, "kind": "real_PC_InputKey", "events": []}
        self.report["input_cases"].append(case)
        self.current = case
        yield from self.wait(.3)
        ground = self.player.get_actor_location().z
        yield from self.tap("SpaceBar")
        yield from self.wait(.12)
        first = int(self.player.get_editor_property("jump_current_count"))
        self.check("jump.first", first == 1 and self.player.get_actor_location().z > ground+10, count=first)
        yield from self.tap("SpaceBar")
        yield from self.wait(.08)
        second = int(self.player.get_editor_property("jump_current_count"))
        self.check("jump.second", second == 2 and self.player.get_velocity().z > 0,
                   count=second, velocity_z=self.player.get_velocity().z)
        yield from self.tap("SpaceBar")
        self.check("jump.third_rejected", int(self.player.get_editor_property("jump_current_count")) == 2)
        yield from self.wait(1.6)
        self.check("jump.landing_reset", int(self.player.get_editor_property("jump_current_count")) == 0,
                   height_above_start=self.player.get_actor_location().z-ground)
        case = {"name": "pause_resume", "fps_cap": self.fps, "kind": "real_PC_InputKey", "events": []}
        self.report["input_cases"].append(case)
        self.current = case
        yield from self.tap("P")
        self.check("pause.key_pauses", u.GameplayStatics.is_game_paused(self.world))
        paused_time = self.world_time()
        deadline = time.monotonic()+.25
        while time.monotonic() < deadline:
            yield
        self.check("pause.world_frozen", abs(self.world_time()-paused_time) < .001,
                   world_advance=self.world_time()-paused_time, wall_observation_seconds=.25)
        yield from self.tap("P")
        self.check("pause.key_resumes", not u.GameplayStatics.is_game_paused(self.world))
        yield from self.wait(.1)
        self.check("pause.world_resumes", self.world_time() > paused_time+.05)
        self.current = None
        yield from self.air_input_cases()

    def default_chain_case(self):
        """Four separate real clicks, authored combo windows and weapon traces."""
        self.reset_isolated()
        case = {"name": "default_four_hit_chain", "fps_cap": self.fps,
                "kind": "real_PC_InputKey; isolated stationary AI target; no data/HP tuning",
                "events": [], "fixture_distance_cm": 220,
                "expected_damage": [18, 22, 26, 38], "expected_total_damage": 104,
                "queue_at_actual_skill_elapsed": .36}
        self.report["input_cases"].append(case)
        self.current = case
        expected = ["Combat.Skill.Attack"+str(i) for i in range(1, 5)]
        try:
            for actor in (self.player, self.boss):
                definitions = list(u.get_default_object(actor.get_class()).get_editor_property("skill_definitions"))
                rows = [{"path": d.get_path_name(), "tag": tag_name(d.get_editor_property("skill_tag")),
                         "next": tag_name(d.get_editor_property("next_skill_tag")),
                         "damage": float(d.get_editor_property("damage"))} for d in definitions if d]
                installed = {r["tag"] for r in rows}
                missing = [r for r in rows if r["next"] not in ("", "None", "Invalid") and r["next"] not in installed]
                self.check("chain."+self.role(actor)+".cdo_next_resolves", not missing,
                           definitions=rows, missing=missing)
                self.check("chain."+self.role(actor)+".example_not_default",
                           not any(t.startswith("Combat.Skill.Example.") for t in installed), installed=sorted(installed))
                if actor == self.player:
                    by_tag = {r["tag"]: r for r in rows}
                    actual = [by_tag.get(t) for t in expected]
                    self.check("chain.default_links_and_damage",
                        all(actual) and [r["next"] for r in actual[:3]] == expected[1:]
                        and actual[3]["next"] in ("", "None", "Invalid")
                        and [r["damage"] for r in actual] == [18, 22, 26, 38], observed=actual)
            z = self.player.get_actor_location().z
            self.player.set_actor_location(u.Vector(0, 0, z), False, True)
            self.boss.set_actor_location(u.Vector(220, 0, z), False, True)
            self.player.set_actor_rotation(u.Rotator(roll=0, pitch=0, yaw=0), True)
            self.boss.set_actor_rotation(u.Rotator(roll=0, pitch=0, yaw=180), True)
            self.controller.set_control_rotation(u.Rotator(roll=0, pitch=0, yaw=0))
            yield from self.wait(.3)
            hp = self.boss.get_health()
            case["health_before"] = hp
            before = len(case["events"])
            started_at, wall_at = self.world_time(), time.monotonic()
            queued = set()
            yield from self.tap("LeftMouseButton", .04)
            while self.world_time()-started_at < 6 and time.monotonic()-wall_at < 12:
                active = tag_name(self.player.get_active_skill_tag())
                if active in expected[:3] and active not in queued and self.player.get_skill_elapsed_time() >= .36:
                    queued.add(active)
                    self.event("combo_click", self.player, predecessor=active,
                               skill_elapsed=self.player.get_skill_elapsed_time())
                    yield from self.tap("LeftMouseButton", .04)
                ended = [e for e in case["events"][before:] if e["type"] == "skill_ended" and e["actor"] == "player"]
                if ended and ended[-1]["skill"] == expected[-1] and not self.player.is_busy():
                    break
                yield
            events = case["events"][before:]
            starts = [e["skill"] for e in events if e["type"] == "skill_started" and e["actor"] == "player"]
            ends = [e for e in events if e["type"] == "skill_ended" and e["actor"] == "player"]
            hits = [e for e in events if e["type"] == "feedback" and e["actor"] == "player"
                    and e.get("target") == "boss" and e.get("cue") == "Combat.Cue.Hit"]
            healths = [hp]+[e["target_health"] for e in hits]
            damage = [healths[i]-healths[i+1] for i in range(len(healths)-1)]
            self.check("chain.completed_before_timeout", bool(ends) and ends[-1]["skill"] == expected[-1]
                       and not self.player.is_busy() and self.world_time()-started_at < 6
                       and time.monotonic()-wall_at < 12,
                       world_elapsed=self.world_time()-started_at, wall_elapsed=time.monotonic()-wall_at,
                       world_timeout_seconds=6, wall_timeout_seconds=12)
            self.check("chain.started_order", starts == expected, observed=starts)
            self.check("chain.ended_order_and_semantics",
                       [e["skill"] for e in ends] == expected and [e["interrupted"] for e in ends] == [True, True, True, False], observed=ends)
            self.check("chain.four_real_hits", [e["source_skill"] for e in hits] == expected
                       and damage == [18, 22, 26, 38], observed_damage=damage, hits=hits)
            self.check("chain.total_damage", abs(hp-self.boss.get_health()-104) < .01,
                       health_before=hp, health_after=self.boss.get_health())
            self.check("chain.four_discrete_clicks", sum(e["type"] == "key" and e.get("key") == "LeftMouseButton"
                       and e.get("pressed") is True for e in events) == 4, queued_predecessors=sorted(queued))
            after_hp, after_starts = self.boss.get_health(), len(starts)
            yield from self.wait(.55)
            final_starts = [e for e in case["events"][before:] if e["type"] == "skill_started" and e["actor"] == "player"]
            self.check("chain.window_cleanup_behavior", not self.player.is_busy()
                       and not self.player.is_parry_window_active() and abs(self.boss.get_health()-after_hp) < .01
                       and len(final_starts) == after_starts,
                       observation="Public idle/no late damage/no buffered restart; private hit/combo flags are not reflected",
                       observed=self.state(self.player))
            self.check("chain.held_keys_released", not self.held_keys, held_keys=sorted(self.held_keys))
        finally:
            self.release_keys()
            self.reset_isolated()
            self.current = None

    def air_input_cases(self):
        for direction in ("W", "S"):
            self.reset_isolated()
            if self.player.is_target_locked():
                self.player.toggle_target_lock()
            self.controller.set_control_rotation(u.Rotator(roll=0, pitch=0, yaw=0))
            self.player.set_actor_rotation(u.Rotator(roll=0, pitch=0, yaw=0), True)
            case = {"name": "running_air_dash_"+direction, "fps_cap": self.fps,
                    "kind": "real_PC_InputKey", "events": []}
            self.report["input_cases"].append(case)
            self.current = case
            yield from self.wait(.25)
            try:
                self.key("W", True)
                yield from self.wait(.35)
                self.check(case["name"]+".running_precondition", self.player.get_velocity().x > 100,
                           velocity=xyz(self.player.get_velocity()))
                yield from self.tap("SpaceBar", .025)
                yield from self.wait(.08)
                self.check(case["name"]+".air_precondition",
                           self.player.get_editor_property("character_movement").is_falling())
                if direction == "S":
                    self.key("W", False)
                    self.key("S", True)
                yield
                case["pre_dash_velocity"] = xyz(self.player.get_velocity())
                case["pre_dash_position_diagnostic_only"] = xyz(self.player.get_actor_location())
                yield from self.tap("LeftShift", .01)
                # Exact public BeginSkill event captures position before movement.
                starts = [e for e in case["events"] if e["type"] == "skill_started"
                          and e.get("skill") == "Combat.Skill.Dash" and e["actor"] == "player"]
                self.check(case["name"]+".started", len(starts) == 1)
                self.release_keys()
                if starts:
                    start = starts[0]
                    deadline = self.world_time()+1
                    while self.player.is_busy() and self.world_time() < deadline:
                        yield from self.wait(.001)
                    ends = [e for e in case["events"] if e["type"] == "skill_ended"
                            and e.get("skill") == "Combat.Skill.Dash" and e["actor"] == "player"]
                    self.check(case["name"]+".ended", len(ends) == 1)
                    if ends:
                        end = ends[0]
                        dx, dy = (end["location"][i]-start["location"][i] for i in (0, 1))
                        length = math.hypot(dx, dy)
                        expected = 0 if direction == "W" else 180
                        heading = math.degrees(math.atan2(dy, dx)) % 360
                        error = abs((heading-expected+180) % 360-180)
                        tolerance = 25+650/self.fps
                        self.check(case["name"]+".trajectory", abs(length-250) <= tolerance and error <= 12,
                                   start_location=start["location"], end_location=end["location"],
                                   velocity_at_start=start["velocity"], expected_direction_degrees=expected,
                                   observed_direction_degrees=heading, distance_cm=length,
                                   expected_distance_cm=250, tolerance_cm=tolerance,
                                   duration=end["world_time"]-start["world_time"])
            finally:
                self.release_keys()
            yield from self.wait(1.5)

        self.reset_isolated()
        case = {"name": "air_pause_release", "fps_cap": self.fps,
                "kind": "real_PC_InputKey", "events": []}
        self.report["input_cases"].append(case)
        self.current = case
        yield from self.wait(.25)
        try:
            self.key("SpaceBar", True)
            yield from self.wait(.08)
            self.check("pause_release.air_precondition",
                       self.player.get_editor_property("character_movement").is_falling())
            self.key("LeftMouseButton", True)
            yield
            yield from self.tap("P", .01)
            self.check("pause_release.paused", u.GameplayStatics.is_game_paused(self.world))
            self.key("LeftMouseButton", False)
            self.key("SpaceBar", False)
            deadline = time.monotonic()+.15
            while time.monotonic() < deadline:
                yield
            yield from self.tap("P", .01)
            self.check("pause_release.resumed", not u.GameplayStatics.is_game_paused(self.world))
            # Wait for the legitimate Air1 recovery before requesting jump #2.
            deadline = self.world_time()+1.2
            while self.player.is_busy() and self.world_time() < deadline:
                yield from self.wait(.001)
            self.check("pause_release.still_airborne",
                       self.player.get_editor_property("character_movement").is_falling())
            yield from self.tap("SpaceBar", .025)
            self.check("pause_release.second_jump", int(self.player.get_editor_property("jump_current_count")) == 2)
            yield from self.tap("SpaceBar", .025)
            self.check("pause_release.third_jump_rejected", int(self.player.get_editor_property("jump_current_count")) == 2)
            yield from self.wait(.4)
            started = [e["skill"] for e in case["events"] if e["type"] == "skill_started" and e["actor"] == "player"]
            self.check("pause_release.legitimate_air_attack", "Combat.Skill.Air1" in started, skills=started)
            self.check("pause_release.no_residual_plunge", "Combat.Skill.Plunge" not in started, skills=started)
        finally:
            self.release_keys()
        yield from self.wait(1.5)
        self.reset_isolated()
        case = {"name": "target_lock_Q", "fps_cap": self.fps,
                "kind": "real_PC_InputKey", "events": []}
        self.report["input_cases"].append(case)
        self.current = case
        before = self.player.is_target_locked()
        yield from self.tap("Q")
        self.check("target_lock.first_toggle", self.player.is_target_locked() != before,
                   initial=before, observed=self.player.is_target_locked())
        yield from self.tap("Q")
        self.check("target_lock.second_toggle", self.player.is_target_locked() == before,
                   initial=before, observed=self.player.is_target_locked())
        self.current = None

    def summarize_round(self, row):
        events = [e for e in row.get("events", []) if e.get("stage") == "combat"]
        row["skill_start_counts"] = dict(collections.Counter(e["actor"]+":"+e["skill"] for e in events if e["type"] == "skill_started"))
        row["cue_counts"] = dict(collections.Counter(e["cue"] for e in events if e["type"] == "feedback"))
        row["hit_events"] = sum(e.get("cue") == "Combat.Cue.Hit" for e in events)
        row["parry_events"] = sum(e.get("cue") == "Combat.Cue.Parry" for e in events)
        row["pass"] = all(a["pass"] for a in row.get("assertions", []))

    def natural_fight(self, number):
        self.reset_isolated()
        yield from self.wait(.3)
        self.ai.set_editor_property("random_seed", 731+number)
        row = {"round": number, "fps_cap": self.fps, "kind": "natural_input_bot_fight",
               "stage": "combat",
               "seed": 731+number, "events": [], "input_counts": {},
               "strategy": {"minimum_skill_observation_seconds": .24,
                            "aoe_flash_response_seconds": .055,
                            "combo_single_press_elapsed": .36,
                            "defense_attack_protection_seconds": .32,
                            "note": "AOE recognition precedes flash response; flash response is not a new .24s recognition delay."},
               "starting_player": self.state(self.player), "starting_boss": self.state(self.boss),
               "peak_owned_projectiles": 0, "peak_new_components": 0,
               "phase_two_observed": False, "movement_distance_cm": 0.0}
        passive = (len(self.caps)*self.rounds > 1 and self.fps == self.caps[0] and number == self.rounds)
        row["strategy"]["name"] = "passive_no_attack_death_coverage" if passive else "active_reactive_swordfighter"
        row["strategy"]["purpose"] = ("Approach normally, then receive unmodified Boss attacks without attack/parry/dash input; natural defeat coverage."
                                       if passive else "Real reactive combat for natural victory and skill coverage.")
        self.report["natural_fights"].append(row)
        self.current = row
        if not self.player.get_editor_property("target_locked"):
            self.player.toggle_target_lock()
        initial_player = xyz(self.player.get_actor_location())
        initial_boss = xyz(self.boss.get_actor_location())
        self.ai.reset_brain()
        start_world, start_wall = self.world_time(), time.monotonic()
        row["combat_started_world_time"] = start_world
        row["phase_transitions"] = [{"world_time": start_world, "phase_two": bool(self.boss.get_editor_property("phase_two")),
                                     "boss_health": self.boss.get_health(), "stage": "combat"}]
        last_phase = bool(self.boss.get_editor_property("phase_two"))
        last_location = self.player.get_actor_location()
        next_attack = next_defense = 0.0
        attack_token = None
        defended_token = None
        protected_until = 0.0
        release_at = None
        observed_skill = None
        observation_at = start_world
        next_snapshot = start_world
        while self.player.is_alive() and self.boss.is_alive():
            now = self.world_time()
            elapsed = now-start_world
            if elapsed > self.fight_timeout or time.monotonic()-start_wall > self.fight_timeout*2+20:
                row["outcome"] = "timeout"
                break
            pos, target_pos = self.player.get_actor_location(), self.boss.get_actor_location()
            row["movement_distance_cm"] += distance(pos, last_location)
            last_location = pos
            phase = bool(self.boss.get_editor_property("phase_two"))
            row["phase_two_observed"] |= phase
            if phase != last_phase:
                row["phase_transitions"].append({"world_time": now, "phase_two": phase,
                                                 "boss_health": self.boss.get_health(), "stage": "combat"})
                last_phase = phase
            d = distance(pos, target_pos)
            if not self.player.is_busy() and d > 150:
                self.player.add_movement_input(u.Vector((target_pos.x-pos.x)/max(d, 1),
                                                        (target_pos.y-pos.y)/max(d, 1), 0), 1.0, False)
            current_skill = tag_name(self.boss.get_active_skill_tag())
            boss_start = round(now-self.boss.get_skill_elapsed_time(), 3) if self.boss.is_busy() else None
            boss_token = (current_skill, self.skill_serial["boss"])
            if boss_token != observed_skill:
                observed_skill, observation_at = boss_token, now
            # One defensive decision per observed action. AOE is first recognized
            # during its long warning, then executed in response to the real flash.
            release = next((e for e in reversed(row["events"])
                            if e.get("cue") == "Combat.Cue.AreaRelease" and e["actor"] == "boss"
                            and e["world_time"] >= (boss_start if boss_start is not None else now)-.005), None)
            aoe = current_skill.endswith(".AOE")
            observed_long_enough = now-observation_at >= .24
            reaction_due = observed_long_enough
            if aoe:
                reaction_due = observed_long_enough and release is not None and now-release["world_time"] >= .055
            elif current_skill.endswith(".DashSlash"):
                reaction_due = observed_long_enough and self.boss.get_skill_elapsed_time() >= .42
            if (not passive and now >= next_defense and reaction_due and self.boss.is_busy() and d < 600
                    and defended_token != boss_token):
                use_parry = aoe or ((number+int(elapsed*2)) % 3) != 0
                method = "parry_pressed" if use_parry else "dash_pressed"
                getattr(self.player, method)()
                row["input_counts"][method] = row["input_counts"].get(method, 0)+1
                self.event("bot_decision", self.player, decision=method, observed_boss_skill=current_skill,
                           observed_for=now-observation_at,
                           player_skill_after_request=tag_name(self.player.get_active_skill_tag()),
                           flash_reaction_seconds=now-release["world_time"] if release else None)
                defended_token = boss_token
                protected_until = now+.32
                next_defense = now+.52
            if release_at is not None and now >= release_at:
                self.player.attack_released()
                row["input_counts"]["attack_released"] = row["input_counts"].get("attack_released", 0)+1
                release_at = None
            player_skill = tag_name(self.player.get_active_skill_tag())
            player_elapsed = self.player.get_skill_elapsed_time()
            player_token = (player_skill, self.skill_serial["player"])
            # Authoring places grounded combo-open at .305/.315/.315/.335s.
            # A single press at .36s advances a stage without repeatedly writing
            # the .18s input buffer. Do not cancel a fresh parry with an attack.
            chain_ready = (player_skill in ("Combat.Skill.Attack1", "Combat.Skill.Attack2", "Combat.Skill.Attack3")
                           and player_elapsed >= .36 and player_token != attack_token)
            attack_ready = not self.player.is_busy() or chain_ready
            hold_for_aoe = aoe and observed_long_enough and (release is None or now-release["world_time"] < .28)
            if (not passive and now >= next_attack and now >= protected_until and d < 300
                    and attack_ready and not hold_for_aoe):
                self.player.attack_pressed()
                attack_token = player_token
                row["input_counts"]["attack_pressed"] = row["input_counts"].get("attack_pressed", 0)+1
                release_at = now+.055
                next_attack = now+.20
            if now >= next_snapshot:
                residual = self.residuals()
                row["peak_owned_projectiles"] = max(row["peak_owned_projectiles"], len(residual["owned_projectiles"]))
                row["peak_new_components"] = max(row["peak_new_components"], sum(map(len, residual["new_character_components"].values())))
                row["live"] = {"world_elapsed": round(elapsed, 3), "player": self.state(self.player), "boss": self.state(self.boss)}
                next_snapshot = now+.2
            yield
        self.player.attack_released()
        self.stop_ai()
        row.setdefault("outcome", "victory" if self.player.is_alive() else "defeat")
        row["combat_ended_world_time"] = self.world_time()
        row["stage"] = "outcome_and_retry"
        row.update(duration_world_seconds=self.world_time()-start_world,
                   duration_wall_seconds=time.monotonic()-start_wall,
                   player_end=self.state(self.player), boss_end=self.state(self.boss),
                   ai_actions_executed=int(self.ai.get_editor_property("actions_executed")))
        self.check("fight.natural_outcome", row["outcome"] in ("victory", "defeat"), outcome=row["outcome"])
        self.check("fight.real_movement", row["movement_distance_cm"] > 25, distance_cm=row["movement_distance_cm"])
        self.check("fight.ai_executed", row["ai_actions_executed"] > 0)
        self.check("fight.real_damage", any(e.get("cue") == "Combat.Cue.Hit" for e in row["events"]))
        if passive:
            self.check("fight.passive_natural_defeat", row["outcome"] == "defeat", outcome=row["outcome"])
            self.check("fight.passive_no_combat_input", not row["input_counts"], input_counts=row["input_counts"])
        if row["outcome"] == "timeout":
            self.reset_isolated()  # Cleanup only; timeout remains FAIL, never converted to victory.
        else:
            yield from self.tap("R")
            self.stop_ai()
        yield from self.wait(.4)
        self.assert_clean("fight.retry", revived=True)
        row["post_retry"] = {"world_time": self.world_time(), "player": self.state(self.player), "boss": self.state(self.boss)}
        self.check("fight.retry_position", distance(self.player.get_actor_location(), u.Vector(*initial_player)) < 10
                   and distance(self.boss.get_actor_location(), u.Vector(*initial_boss)) < 10)
        self.summarize_round(row)
        self.current = None
        self.save()

    def setup(self):
        while self.world is None:
            self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
            if time.monotonic()-self.boot_wall > 20:
                raise TimeoutError("Start an approved PIE session first; no game world found")
            yield
        actors = list(u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatCharacter))
        players = [a for a in actors if not a.get_editor_property("is_boss")]
        bosses = [a for a in actors if a.get_editor_property("is_boss")]
        if len(players) != 1 or len(bosses) != 1:
            raise RuntimeError("Expected exactly one live CombatCharacter player and boss")
        self.player, self.boss = players[0], bosses[0]
        if not callable(getattr(self.player, "is_target_locked", None)):
            raise RuntimeError("Rebuilt CombatCharacter.is_target_locked getter is required")
        self.controller = self.player.get_controller()
        if not isinstance(self.controller, u.PlayerController) or not callable(getattr(u.CombatEditorLibrary, "inject_player_key", None)):
            raise RuntimeError("Rebuilt PIE-only CombatEditorLibrary.inject_player_key and a PlayerController are required")
        self.old_paused = u.GameplayStatics.is_game_paused(self.world)
        if self.old_paused:
            raise RuntimeError("Start from an unpaused PIE world")
        self.ai = self.boss.get_controller()
        if not isinstance(self.ai, u.CombatAIController):
            raise RuntimeError("Boss needs the real CombatAIController / StateTree")
        self.brain = self.ai.get_editor_property("state_tree_component")
        self.old_seed = self.ai.get_editor_property("random_seed")
        self.old_cap = u.SystemLibrary.get_console_variable_float_value("t.MaxFPS")
        self.report["actors"] = []
        for actor in actors:
            mesh = actor.get_editor_property("mesh").get_skinned_asset()
            skeleton = mesh.get_editor_property("skeleton") if mesh else None
            skeleton_path = skeleton.get_path_name() if skeleton else ""
            expected_source = "/ParagonGreystone/" if actor == self.boss else "/ParagonKwang/"
            if mesh is None or (self.require_paragon and expected_source not in skeleton_path):
                raise RuntimeError("Configured production Paragon skeletal mesh required; no placeholder acceptance")
            self.report["actors"].append({"role": self.role(actor), "actor": actor.get_path_name(), "mesh": mesh.get_path_name(), "skeleton": skeleton_path})
            for name, callback in [("on_combat_feedback", self.on_feedback), ("on_skill_started", self.on_started),
                                   ("on_skill_ended", self.on_ended), ("on_combat_death", self.on_death)]:
                delegate = actor.get_editor_property(name)
                delegate.add_callable(callback)
                self.bindings.append((delegate, callback))
        self.reset_isolated()
        yield from self.wait(.5)
        self.baseline = {self.role(a): self.components(a) for a in actors}
        self.report["component_baseline"] = self.baseline
        self.report["status"] = "running"

    def run(self):
        yield from self.setup()
        for cap in self.caps:
            self.fps = cap
            u.SystemLibrary.execute_console_command(self.world, "t.MaxFPS " + str(cap))
            yield from self.wait(1.0)
            self.frame_steps = []
            yield from self.input_cases()
            yield from self.defense_cases()
            yield from self.lifecycle_cases()
            for number in range(1, self.rounds+1):
                yield from self.natural_fight(number)
            steps = sorted(self.frame_steps)
            timing = {"samples": len(steps), "requested_cap": cap,
                      "median_world_step": statistics.median(steps) if steps else None,
                      "p95_world_step": steps[min(len(steps)-1, int(len(steps)*.95))] if steps else None,
                      "max_world_step": max(steps) if steps else None}
            timing["observed_median_fps"] = 1/timing["median_world_step"] if steps else None
            self.report["timing"][str(cap)] = timing
            self.check("fps.observed", len(steps) >= 100 and abs(timing["observed_median_fps"]-cap)/cap <= .15,
                       **timing, allowed_relative_error=.15)
        self.check("suite.natural_round_count", len(self.report["natural_fights"]) == self.rounds*len(self.caps))
        fights = self.report["natural_fights"]
        outcomes = collections.Counter(r["outcome"] for r in fights)
        total = len(fights)
        self.report["natural_outcome_summary"] = {
            "victories": outcomes["victory"], "defeats": outcomes["defeat"],
            "timeouts": outcomes["timeout"], "total": total,
            "defeat_rate": outcomes["defeat"]/total if total else None,
            "timeout_rate": outcomes["timeout"]/total if total else None,
            "assertion_failure_rate": sum(not r["pass"] for r in fights)/total if total else None}
        self.report["natural_outcome_summary"]["by_strategy"] = {
            name: dict(collections.Counter(r["outcome"] for r in fights if r["strategy"]["name"] == name))
            for name in sorted({r["strategy"]["name"] for r in fights})}
        self.check("coverage.natural_victory", outcomes["victory"] >= 1, count=outcomes["victory"])
        self.check("coverage.natural_defeat", outcomes["defeat"] >= 1, count=outcomes["defeat"])
        self.check("coverage.phase_two", any(r["phase_two_observed"] for r in fights))
        self.check("coverage.natural_projectile", any(r["peak_owned_projectiles"] > 0 for r in fights))
        self.check("coverage.natural_parry", any(r["parry_events"] > 0 for r in fights))
        self.report["status"] = "passed" if all(a["pass"] for a in self.report["assertions"]) else "failed"
        self.report["accepts_twenty_rounds"] = (self.report["status"] == "passed"
                                                and set(self.caps) == {30, 60}
                                                and self.rounds >= 10)

    def tick(self, delta):
        try:
            if self.world is not None:
                if not u.SystemLibrary.is_valid(self.world):
                    raise RuntimeError("PIE world ended while regression was running")
                now = self.world_time()
                if self.last_world_time is not None and now-self.last_world_time > .00001:
                    self.frame_steps.append(now-self.last_world_time)
                self.last_world_time = now
            next(self.generator)
            if time.monotonic()-self.last_save > 1:
                self.save()
        except StopIteration:
            self.cleanup()
        except Exception:
            self.report["status"] = "failed"
            self.report["error"] = traceback.format_exc()
            self.cleanup()

    def cleanup(self):
        errors = []
        try:
            self.release_keys()
        except Exception as exc:
            errors.append("held_keys: " + repr(exc))
        try:
            self.generator.close()  # Run suspended tap / scenario finally blocks.
        except Exception as exc:
            errors.append("generator_finally: " + repr(exc))
        if self.handle is not None:
            try:
                u.unregister_slate_post_tick_callback(self.handle)
            except Exception as exc:
                errors.append("callback: " + repr(exc))
            self.handle = None
        for delegate, callback in self.bindings:
            try:
                delegate.remove_callable(callback)
            except Exception as exc:
                errors.append("delegate: " + repr(exc))
        self.bindings.clear()
        try:
            restore_world = self.world if self.world and u.SystemLibrary.is_valid(self.world) else u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            if self.old_cap is not None and restore_world:
                u.SystemLibrary.execute_console_command(restore_world, "t.MaxFPS " + str(self.old_cap))
            if self.world and u.SystemLibrary.is_valid(self.world):
                if self.old_paused is not None:
                    u.GameplayStatics.set_game_paused(self.world, self.old_paused)
                if self.player and u.SystemLibrary.is_valid(self.player):
                    self.player.attack_released()
                if self.ai and u.SystemLibrary.is_valid(self.ai) and self.old_seed is not None:
                    self.ai.set_editor_property("random_seed", self.old_seed)
                    self.ai.reset_brain()
        except Exception as exc:
            errors.append("restore: " + repr(exc))
        if errors:
            self.report["cleanup_errors"] = errors
            if self.report["status"] == "passed":
                self.report["status"] = "failed"
            self.report["accepts_twenty_rounds"] = False
        self.save()


def start(**kwargs):
    previous = getattr(builtins, KEY, None)
    if previous and previous.handle is not None:
        raise RuntimeError("A regression runner is already active; use status()/stop()")
    runner = ArenaRegression(**kwargs)
    setattr(builtins, KEY, runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return status()


def status():
    runner = getattr(builtins, KEY, None)
    if runner is None:
        return {"status": "not_started"}
    return {"status": runner.report["status"], "report_path": str(runner.path),
            "fps_cap": runner.fps, "natural_fights_recorded": len(runner.report["natural_fights"]),
            "current": runner.current.get("name", runner.current.get("round")) if runner.current else None,
            "failed_assertions": sum(not a["pass"] for a in runner.report["assertions"]),
            "active": runner.handle is not None}


def stop():
    runner = getattr(builtins, KEY, None)
    if runner and runner.handle is not None:
        runner.report["status"] = "stopped"
        runner.report["accepts_twenty_rounds"] = False
        runner.cleanup()
    return status()
