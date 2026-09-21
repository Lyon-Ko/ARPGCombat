"""Opt-in isolated PIE StateTree scenarios. Importing never starts a runner.

Uses ArenaRegression's public generator/wait, event, reset, hit and JSON helpers.
Never run concurrently with arena_regression. No private AI selection is called.
"""
import builtins
import collections
from pathlib import Path
import runpy
import time
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name("arena_regression.py")))
ArenaRegression = BASE["ArenaRegression"]
tag, tag_name, xyz = BASE["tag"], BASE["tag_name"], BASE["xyz"]
KEY = "_combat_arena_ai_scenarios"


class AIScenarios(ArenaRegression):
    def __init__(self, seeds=32, output_name=None):
        if not 1 <= seeds <= 128:
            raise ValueError("seeds must be 1..128")
        super().__init__(fps_caps=(60,), fights_per_cap=1, require_paragon=False,
                         output_name=output_name or "arena_ai_scenarios.json")
        self.seeds = seeds
        self.report.update(execution="ISOLATED AI scenarios: transforms/reset and explicit health injection; NOT natural fights",
                           selections=[], distributions={}, phase_samples=[], scope="StateTree public runtime behavior")
        self.report["limitations"] = [
            "Paired distributions are descriptive samples, not guaranteed probability ratios.",
            "Health injection is confined to the explicit half-health scenario; no fabricated selected skills.",
            "Phase transition count means observed false-to-true transitions, not internal assignment count.",
            "Wall fixture uses arena west wall at x=-2500; a capsule sweep must confirm blocking."]

    def on_started(self, actor, skill):
        super().on_started(actor, skill)
        if actor == self.boss and self.current is not None:
            self.current.setdefault("boss_starts", []).append({"skill": tag_name(skill), "time": self.world_time()})

    def setup(self, separation=400, wall=False):
        self.reset_isolated()
        self.player.set_editor_property("target_locked", False)
        bx = -2380.0 if wall else 0.0
        z = self.boss.get_actor_location().z
        self.boss.set_actor_location_and_rotation(u.Vector(bx, 0, z), u.Rotator(yaw=0), False, True)
        self.player.set_actor_location_and_rotation(u.Vector(bx+separation, 0, z), u.Rotator(yaw=180), False, True)

    def wall_evidence(self):
        capsule = self.boss.get_editor_property("capsule_component")
        start = self.boss.get_actor_location()
        leap = next(d for d in self.boss.get_editor_property("skill_definitions")
                    if tag_name(d.get_editor_property("skill_tag")) == "Combat.Skill.Boss.LeapBack")
        amount = float(leap.get_editor_property("movement_distance"))
        direction = leap.get_editor_property("movement_direction_local")
        length = max((direction.x**2+direction.y**2+direction.z**2)**.5, .0001)
        end = u.Vector(start.x+direction.x/length*amount, start.y+direction.y/length*amount, start.z+direction.z/length*amount)
        # Explicit WorldStatic object query, verified in local PythonStub.
        hit = u.SystemLibrary.capsule_trace_single_for_objects(
            self.world, start, end, capsule.get_scaled_capsule_radius(), capsule.get_scaled_capsule_half_height(),
            [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1], False, [self.player, self.boss], u.DrawDebugTrace.NONE)
        # HitResult's HasNativeBreak maps GameplayStatics.BreakHitResult to
        # StructBase.to_tuple: blocking_hit, initial_overlap, time, distance, ...
        # Protected raw fields cannot be read with get_editor_property.
        values = hit.to_tuple() if hit is not None else None
        return {"start": xyz(start), "end": xyz(end), "hit": hit is not None,
                "time": float(values[2]) if values else None,
                "blocking": bool(values[0]) if values else False}

    def selection(self, action, seed, separation=400, wall=False):
        self.setup(separation, wall)
        yield from self.wait(.08)
        row = {"name": "selection", "action": action, "seed": seed, "separation_cm": separation,
               "wall": wall, "boss_starts": [], "events": []}
        self.current = row
        self.report["selections"].append(row)
        if wall:
            row["wall_sweep"] = self.wall_evidence()
            evidence = row["wall_sweep"]
            self.check("wall.fixture_blocks_retreat", evidence["blocking"] and evidence["time"] < .65, sweep=evidence)
        if action != "neutral":
            getattr(self.player, {"Attack": "attack_pressed", "Parry": "parry_pressed", "Dash": "dash_pressed"}[action])()
            self.player.attack_released()
        active = tag_name(self.player.get_active_skill_tag())
        self.check("player.actual_action", action == "neutral" or action in active, requested=action, actual=active)
        self.ai.set_editor_property("random_seed", seed)
        row["reaction_min"] = float(self.ai.get_editor_property("reaction_min"))
        row["reaction_max"] = float(self.ai.get_editor_property("reaction_max"))
        started = self.world_time()
        self.ai.reset_brain()
        row["snapshot_skill"] = tag_name(self.ai.get_editor_property("observed_target_skill"))
        row["snapshot_location"] = xyz(self.ai.get_editor_property("observed_target_location"))
        self.check("ai.observed_executed_action", row["snapshot_skill"] == active, actual=active, observed=row["snapshot_skill"])
        wall_start = time.monotonic()
        while not row["boss_starts"] and self.world_time()-started < 4:
            if time.monotonic()-wall_start > 12:
                raise TimeoutError("StateTree scenario world stalled")
            yield
        self.check("ai.real_skill_started", bool(row["boss_starts"]))
        if row["boss_starts"]:
            first = row["boss_starts"][0]
            row["selected"] = first["skill"]
            row["reaction_observed"] = first["time"]-started
            # A frame may straddle reset/start; upper bound allows two 30-Hz frames.
            self.check("ai.reaction_min", row["reaction_observed"] >= row["reaction_min"]-.04, seconds=row["reaction_observed"])
            if separation == 400 and not wall:
                self.check("ai.reaction_max", row["reaction_observed"] <= row["reaction_max"]+.08, seconds=row["reaction_observed"])
            if wall:
                self.check("wall.no_blocked_leap_back", row["selected"] != "Combat.Skill.Boss.LeapBack", selected=row["selected"])
        self.stop_ai()
        self.boss.cancel_current_skill()
        self.player.cancel_current_skill()
        self.current = None
        self.save()

    def phase_case(self):
        self.setup(1200)
        self.current = {"name": "half_health_explicit_injection", "events": [], "boss_starts": []}
        self.report["phase_case"] = self.current
        started = self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.AOE"))
        self.check("phase.aoe_started", started)
        if not started:
            return
        yield from self.wait(.1)
        self.hit(self.boss, self.player, damage=self.boss.get_max_health()*.51, parryable=False)
        self.check("phase.injected_below_half", self.boss.get_health() < self.boss.get_max_health()*.5,
                   health=self.boss.get_health(), poise_damage=0, synthetic=True)
        transitions, previous = 0, False
        deadline = self.world_time()+7
        wall_deadline = time.monotonic()+20
        while self.boss.is_busy() and self.world_time() < deadline:
            if time.monotonic() > wall_deadline:
                raise TimeoutError("Phase scenario world stopped advancing")
            phase = bool(self.boss.get_editor_property("phase_two"))
            self.report["phase_samples"].append({"time": self.world_time(), "busy": True, "phase": phase})
            transitions += int(phase and not previous)
            previous = phase
            yield
        self.check("phase.aoe_completed", not self.boss.is_busy())
        self.check("phase.deferred_during_aoe", not any(r["phase"] for r in self.report["phase_samples"]))
        for _ in range(12):
            phase = bool(self.boss.get_editor_property("phase_two"))
            transitions += int(phase and not previous)
            previous = phase
            yield
        self.check("phase.single_observed_transition", previous and transitions == 1, transitions=transitions)
        self.current = None

    def run(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world or u.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError("Requires an existing unpaused approved PIE session")
        actors = list(u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatCharacter))
        players = [a for a in actors if not a.get_editor_property("is_boss")]
        bosses = [a for a in actors if a.get_editor_property("is_boss")]
        if len(players) != 1 or len(bosses) != 1:
            raise RuntimeError("Expected exactly one player and one boss")
        self.player, self.boss = players[0], bosses[0]
        self.ai = self.boss.get_controller()
        if not isinstance(self.ai, u.CombatAIController):
            raise RuntimeError("Requires actual CombatAIController")
        self.brain = self.ai.get_editor_property("state_tree_component")
        self.old_seed = self.ai.get_editor_property("random_seed")
        self.old_paused = False
        self.report["status"] = "running"
        delegate = self.boss.get_editor_property("on_skill_started")
        delegate.add_callable(self.on_started)
        self.bindings.append((delegate, self.on_started))
        for seed in range(731, 731+self.seeds):
            for action in ("neutral", "Attack", "Parry", "Dash"):
                yield from self.selection(action, seed)
        for seed in range(731, 735):
            yield from self.selection("neutral", seed, 180)
            yield from self.selection("neutral", seed, 850)
            yield from self.selection("Attack", seed, 400, True)
        for action in ("neutral", "Attack", "Parry", "Dash"):
            self.report["distributions"][action] = dict(collections.Counter(
                r.get("selected", "NO_SELECTION") for r in self.report["selections"]
                if r["action"] == action and r["separation_cm"] == 400 and not r["wall"]))
        yield from self.phase_case()
        self.report["status"] = "passed" if all(a["pass"] for a in self.report["assertions"]) else "failed"

    def cleanup(self):
        try:
            if self.brain and self.world and u.SystemLibrary.is_valid(self.world):
                self.reset_isolated()
        finally:
            super().cleanup()


def start(**kwargs):
    for key in (KEY, "_combat_arena_regression"):
        previous = getattr(builtins, key, None)
        if previous and previous.handle is not None:
            raise RuntimeError("Another arena runner is active; stop it first")
    runner = AIScenarios(**kwargs)
    setattr(builtins, KEY, runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return status()


def status():
    runner = getattr(builtins, KEY, None)
    return {"status": runner.report["status"], "active": runner.handle is not None,
            "report_path": str(runner.path), "selections": len(runner.report["selections"])} if runner else {"status": "not_started"}


def stop():
    runner = getattr(builtins, KEY, None)
    if runner and runner.handle is not None:
        runner.report["status"] = "stopped"
        runner.cleanup()
    return status()
