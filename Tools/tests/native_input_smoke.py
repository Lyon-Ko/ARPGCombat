"""Observe Native Windows input via computer-use automation only. Import is inert; start()/finish() are explicit."""
import builtins
import collections
import datetime
import json
import math
from pathlib import Path
import time
import unreal as u

KEY = '_combat_native_input_smoke'

def pos(value):
    return [float(value.x), float(value.y), float(value.z)]

def skill_name(value):
    return str(value.get_editor_property('tag_name'))

class Observer:
    def __init__(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world or u.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError('An unpaused approved PIE session is required')
        actors = u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatCharacter)
        self.player = next(a for a in actors if not a.get_editor_property('is_boss'))
        self.boss = next(a for a in actors if a.get_editor_property('is_boss'))
        self.controller = self.player.get_controller()
        self.ai = self.boss.get_controller()
        self.brain = self.ai.get_editor_property('state_tree_component')
        self.handle = None
        self.bindings = []
        self.events = []
        self.samples = []
        self.observed_keys = {}
        for name in ('W', 'SpaceBar', 'LeftShift', 'LeftMouseButton', 'RightMouseButton'):
            key = u.Key()
            key.set_editor_property('key_name', name)
            self.observed_keys[name] = key
        self.wall_start = time.monotonic()
        self.started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.player.attack_released()
        self.player.reset_combat_state()
        self.boss.reset_combat_state()
        self.brain.stop_logic('Native OS input observation')
        self.ai.stop_movement()
        # Setup only. All subsequent combat / locomotion inputs come from Native Windows input via computer-use automation.
        self.player.set_combat_target(self.boss)
        self.boss.set_combat_target(self.player)
        if self.player.is_target_locked():
            self.player.toggle_target_lock()
        location = self.player.get_actor_location()
        forward = self.player.get_actor_forward_vector()
        self.boss.set_actor_location(u.Vector(location.x+170*forward.x,
            location.y+170*forward.y, location.z), False, True)
        for actor in (self.player, self.boss):
            for name, callback in (('on_skill_started', self.started), ('on_skill_ended', self.ended),
                                    ('on_combat_feedback', self.cue)):
                delegate = actor.get_editor_property(name)
                delegate.add_callable(callback)
                self.bindings.append((delegate, callback))
        self.record_sample()

    def now(self):
        return float(u.GameplayStatics.get_time_seconds(self.world))

    def event(self, kind, actor, **values):
        self.events.append({'kind': kind, 'actor': 'player' if actor == self.player else 'boss',
                            'world_time': self.now(), **values})

    def started(self, actor, skill):
        self.event('skill_started', actor, skill=skill_name(skill))

    def ended(self, actor, skill):
        self.event('skill_ended', actor, skill=skill_name(skill))

    def cue(self, source, target, cue, location, intensity):
        self.event('cue', source, cue=skill_name(cue), location=pos(location), intensity=float(intensity))

    def record_sample(self):
        self.samples.append({'world_time': self.now(), 'position': pos(self.player.get_actor_location()),
            'jump_count': int(self.player.get_editor_property('jump_current_count')),
            'falling': self.player.get_editor_property('character_movement').is_falling(),
            'keys_down': [name for name, key in self.observed_keys.items() if self.controller.is_input_key_down(key)],
            'controller_yaw': float(self.controller.get_control_rotation().yaw)})

    def tick(self, delta):
        try:
            if not u.SystemLibrary.is_valid(self.world):
                self.finish('PIE ended')
                return
            self.record_sample()
        except Exception as exc:
            self.finish(repr(exc))

    def finish(self, error=None):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        for delegate, callback in self.bindings:
            delegate.remove_callable(callback)
        self.bindings.clear()
        steps = list(zip(self.samples, self.samples[1:]))
        travel = sum(math.dist(a['position'], b['position']) for a,b in steps)
        yaw_deltas = [abs((b['controller_yaw']-a['controller_yaw']+180)%360-180) for a,b in steps]
        starts = collections.Counter(e['skill'] for e in self.events
            if e['kind']=='skill_started' and e['actor']=='player')
        report = {'started_utc': self.started_utc, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status': 'observer_error' if error else 'observed', 'error': error,
            'duration_wall_seconds': time.monotonic()-self.wall_start,
            'source': 'Native Windows input via computer-use automation; observer injected no keys and made no health/skill tuning changes.',
            'setup': 'Reset both characters, stop Boss AI, Boss 170cm in front, unlock camera.',
            'observations': {'player_skill_starts': dict(starts),
                'attack1_observed': starts['Combat.Skill.Attack1'] > 0,
                'parry_observed': starts['Combat.Skill.Parry'] > 0,
                'dash_observed': starts['Combat.Skill.Dash'] > 0,
                'max_jump_count': max(s['jump_count'] for s in self.samples),
                'highest_z_cm': max(s['position'][2] for s in self.samples),
                'rise_above_start_cm': max(s['position'][2] for s in self.samples)-self.samples[0]['position'][2],
                'position_path_cm': travel, 'controller_yaw_change_degrees': sum(yaw_deltas),
                'key_down_sample_counts': dict(collections.Counter(name for s in self.samples for name in s['keys_down'])),
                'yaw_change_samples': sum(d > .01 for d in yaw_deltas)},
            'limitations': ['Position changes can include authored attack/dash movement; they do not alone prove W input.',
                'Yaw changes are observations, not raw mouse events. Operator records which OS actions were issued.',
                'No requirement for two jumps; OS automation spacing may not suit a double jump.'],
            'events': self.events, 'samples': self.samples}
        folder = Path(u.Paths.project_saved_dir()).resolve()/'Acceptance'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/'NativeInputSmoke.json'
        if path.exists():
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            path.replace(folder/('NativeInputSmoke_previous_'+stamp+'.json'))
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if u.SystemLibrary.is_valid(self.player):
            self.player.attack_released()
        if u.SystemLibrary.is_valid(self.ai):
            self.ai.reset_brain()
        return {'report_path': str(path), 'observations': report['observations'], 'error': error}

def start():
    for key in (KEY, '_combat_arena_regression', '_combat_arena_ai_scenarios',
                '_combat_arena_ai_near', '_combat_arena_spatial_visual'):
        old = getattr(builtins, key, None)
        if old and old.handle is not None:
            raise RuntimeError('Another input/test observer is active')
    observer = Observer()
    setattr(builtins, KEY, observer)
    observer.handle = u.register_slate_post_tick_callback(observer.tick)
    return {'status': 'observing', 'instructions': 'Use OS left/right click, Shift, Space, W and mouse, then finish().'}

def finish():
    observer = getattr(builtins, KEY, None)
    if observer is None or observer.handle is None:
        return {'status': 'not_active'}
    return observer.finish()
