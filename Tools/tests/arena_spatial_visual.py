"""Opt-in isolated spatial PIE checks; never imports/starts another live runner."""
import builtins
from pathlib import Path
import runpy
import unreal as u

BASE = runpy.run_path(str(Path(__file__).with_name("arena_regression.py")))
ArenaRegression = BASE["ArenaRegression"]
tag, tag_name, xyz, distance = (BASE[n] for n in ("tag", "tag_name", "xyz", "distance"))
KEY = "_combat_arena_spatial_visual"


class SpatialVisual(ArenaRegression):
    def __init__(self, output_name="arena_spatial_visual.json", screenshots=False):
        super().__init__(fps_caps=(60,), fights_per_cap=1, require_paragon=False, output_name=output_name)
        self.screenshots = screenshots
        self.report.update(execution="ISOLATED transforms, public input and direct Montage stop; NOT natural fights",
                           spatial_cases=[], screenshot_requests=[])
        self.report["limitations"] = [
            "Arena wall inner faces assumed at x/y +/-2500cm, height400cm; changed maps require fixture review.",
            "Camera inside-wall assertion uses known rectangular arena geometry, not arbitrary mesh penetration.",
            "Free rotation uses public controller yaw input; this is not an OS mouse test.",
            "Shot SHOWUI uses UE viewport capture; screenshot request does not prove file or visual acceptance."]

    def fixture(self, position, yaw):
        self.reset_isolated()
        self.player.set_editor_property("target_locked", False)
        self.player.set_actor_location_and_rotation(u.Vector(*position), u.Rotator(yaw=yaw), False, True)
        self.boss.set_actor_location_and_rotation(u.Vector(700,700,position[2]), u.Rotator(yaw=180), False, True)
        self.controller.set_control_rotation(u.Rotator(pitch=-12,yaw=yaw,roll=0))

    def shot(self, label):
        if self.screenshots:
            # Native UE screenshot system writes to Saved/Screenshots/<platform>.
            u.SystemLibrary.execute_console_command(self.world, "Shot SHOWUI")
            self.report["screenshot_requests"].append({"label": label, "world_time": self.world_time(),
                "directory": str(Path(u.Paths.project_saved_dir()) / "Screenshots")})

    def run(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world or u.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError("Requires approved unpaused PIE")
        actors = list(u.GameplayStatics.get_all_actors_of_class(self.world,u.CombatCharacter))
        players = [a for a in actors if not a.get_editor_property("is_boss")]
        bosses = [a for a in actors if a.get_editor_property("is_boss")]
        if len(players)!=1 or len(bosses)!=1:
            raise RuntimeError("Expected one player and one boss")
        self.player,self.boss = players[0],bosses[0]
        self.controller = self.player.get_controller()
        self.ai = self.boss.get_controller()
        if not isinstance(self.ai,u.CombatAIController):
            raise RuntimeError("Requires Combat AI controller")
        self.brain = self.ai.get_editor_property("state_tree_component")
        self.old_seed = self.ai.get_editor_property("random_seed")
        self.old_paused = False
        self.report["status"] = "running"
        for actor in (self.player,self.boss):
            for name,callback in (("on_skill_started",self.on_started),("on_skill_ended",self.on_ended),("on_combat_feedback",self.on_feedback)):
                delegate = actor.get_editor_property(name)
                delegate.add_callable(callback)
                self.bindings.append((delegate,callback))
        z = self.player.get_actor_location().z
        # Facing inward, no WASD: real DashPressed defaults backwards into wall.
        walls = (("west",(-2380,0,z),0),("east",(2380,0,z),180),
                 ("south",(0,-2380,z),90),("north",(0,2380,z),-90))
        for name,position,yaw in walls:
            for airborne in (False,True):
                self.fixture(position,yaw)
                yield from self.wait(.1)
                if airborne:
                    self.player.jump()
                    yield from self.wait(.07)
                falling = self.player.get_editor_property("character_movement").is_falling()
                row = {"name": name+("_air" if airborne else "_ground"), "events": [], "samples": []}
                self.current = row
                self.report["spatial_cases"].append(row)
                self.player.dash_pressed()
                activated = tag_name(self.player.get_active_skill_tag())=="Combat.Skill.Dash"
                start = self.world_time()
                while self.world_time()-start < .35:
                    row["samples"].append(xyz(self.player.get_actor_location()))
                    yield from self.wait(.001)
                radius = self.player.get_editor_property("capsule_component").get_scaled_capsule_radius()
                safe = all(abs(p[0])+radius <= 2502 and abs(p[1])+radius <= 2502 for p in row["samples"])
                self.check("wall_dash."+row["name"], activated and safe and falling==airborne, activated=activated, falling=falling, radius=radius,
                           start=position, finish=xyz(self.player.get_actor_location()))
        self.current = None
        self.fixture((-2380,0,z),0)
        yield from self.wait(.4)
        boom = self.player.get_editor_property("camera_boom")
        camera = self.player.get_editor_property("camera")
        camera_pos = camera.get_world_location()
        unfixed = boom.get_unfixed_camera_position()
        retraction = distance(camera_pos,unfixed)
        self.check("camera.wall_retracts_and_stays_inside", boom.is_collision_fix_applied() and retraction>10
                   and abs(camera_pos.x)<2500 and abs(camera_pos.y)<2500,
                   camera=xyz(camera_pos), unfixed=xyz(unfixed), retraction_cm=retraction)
        player_capsule = self.player.get_editor_property("capsule_component")
        boss_capsule = self.boss.get_editor_property("capsule_component")
        self.check("camera.close_hides_player_only", self.player.is_hidden_for_close_camera()
                   and not self.boss.is_hidden_for_close_camera(),
                   player_hidden=self.player.is_hidden_for_close_camera(),
                   boss_hidden=self.boss.is_hidden_for_close_camera())
        collision_before = {"player": str(player_capsule.get_collision_enabled()),
                            "boss": str(boss_capsule.get_collision_enabled())}
        self.check("camera.close_preserves_collision", player_capsule.get_collision_enabled() != u.CollisionEnabled.NO_COLLISION
                   and boss_capsule.get_collision_enabled() != u.CollisionEnabled.NO_COLLISION,
                   collision=collision_before)
        self.shot("wall_camera")
        yield from self.wait(.2)  # UE captures on a later render tick; preserve fixture.
        self.fixture((0,0,z),0)
        yield from self.wait(.4)
        self.check("camera.away_reveals_player", not self.player.is_hidden_for_close_camera(),
                   hidden=self.player.is_hidden_for_close_camera())
        self.check("camera.away_preserves_collision", collision_before == {
                   "player": str(player_capsule.get_collision_enabled()), "boss": str(boss_capsule.get_collision_enabled())})
        self.player.toggle_target_lock()
        locked = self.player.is_target_locked()
        yield from self.wait(.2)
        self.player.toggle_target_lock()
        unlocked = not self.player.is_target_locked()
        before = self.controller.get_control_rotation().yaw
        for _ in range(8):
            self.player.add_controller_yaw_input(3.0)
            yield from self.wait(.001)
        after = self.controller.get_control_rotation().yaw
        self.check("camera.q_toggle_and_free_rotation", locked and unlocked and abs((after-before+180)%360-180)>1,
                   locked=locked,unlocked=unlocked,yaw_before=before,yaw_after=after)
        self.shot("free_camera")
        yield from self.wait(.2)
        self.fixture((0,0,z),0)
        baseline = set(self.components(self.boss))
        self.current = {"name":"direct_montage_stop", "events":[]}
        self.report["spatial_cases"].append(self.current)
        self.boss.request_skill_by_tag(tag("Combat.Skill.Boss.AOE"))
        yield from self.wait(.12)
        anim = self.boss.get_editor_property("mesh").get_anim_instance()
        montage = anim.get_current_active_montage()
        if montage:
            anim.montage_stop(.05,montage)
        yield from self.wait(1.5)
        residual = sorted(set(self.components(self.boss))-baseline)
        ended = [e for e in self.current["events"] if e["type"]=="skill_ended"]
        releases = [e for e in self.current["events"] if e.get("cue")=="Combat.Cue.AreaRelease"]
        self.check("montage.direct_stop_cleans", montage is not None and not self.boss.is_busy()
                   and not residual and len(ended)==1 and not releases,
                   residual=residual,ended=len(ended),late_releases=len(releases))
        self.current = None
        self.report["status"] = "passed" if all(a["pass"] for a in self.report["assertions"]) else "failed"

    def cleanup(self):
        try:
            if self.brain and self.world and u.SystemLibrary.is_valid(self.world):
                self.reset_isolated()
        finally:
            super().cleanup()


def start(**kwargs):
    for key in (KEY,"_combat_arena_regression","_combat_arena_ai_scenarios"):
        previous = getattr(builtins,key,None)
        if previous and previous.handle is not None:
            raise RuntimeError("Another arena runner is active; stop it first")
    runner = SpatialVisual(**kwargs)
    setattr(builtins,KEY,runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return status()


def status():
    runner = getattr(builtins,KEY,None)
    return {"status":runner.report["status"],"active":runner.handle is not None,
            "report_path":str(runner.path),"assertions":len(runner.report["assertions"])} if runner else {"status":"not_started"}


def stop():
    runner = getattr(builtins,KEY,None)
    if runner and runner.handle is not None:
        runner.report["status"] = "stopped"
        runner.cleanup()
    return status()
