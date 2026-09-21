"""Isolated queued-launch/reset and coarse-frame real-R StateTree regression."""
import builtins
import datetime
import math
from pathlib import Path
import runpy
import time
import unreal as u
BASE = runpy.run_path(str(Path(__file__).with_name('arena_regression.py')))
KEY = '_combat_build11_regression'

class Regression(BASE['ArenaRegression']):
    def __init__(self):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        super().__init__(fps_caps=(60,), fights_per_cap=1, output_name='Build11_Directed_'+stamp+'.json')
        self.awaiting_reset = False
        self.reset_seen = None
        self.report['directed_cases'] = []
        self.report['execution'] = 'Isolated explicit LaunchCharacter / lethal lifecycle hit / real R input; not natural bouts'

    def observe_reset(self):
        if self.awaiting_reset and self.reset_seen is None and self.player.is_alive():
            self.reset_seen = self.world_time()
            self.current['reset_first_observed_world_time'] = self.reset_seen

    def on_started(self, actor, skill):
        self.observe_reset()
        super().on_started(actor, skill)

    def tick(self, delta):
        if self.player:
            self.observe_reset()
        super().tick(delta)

    def new_case(self, name):
        self.current = {'name': name, 'events': [], 'samples': []}
        self.report['directed_cases'].append(self.current)

    def run(self):
        self.world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world or u.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError('Approved unpaused PIE required')
        actors = u.GameplayStatics.get_all_actors_of_class(self.world, u.CombatCharacter)
        self.player = next(a for a in actors if not a.get_editor_property('is_boss'))
        self.boss = next(a for a in actors if a.get_editor_property('is_boss'))
        self.controller = self.player.get_controller()
        self.ai = self.boss.get_controller()
        self.brain = self.ai.get_editor_property('state_tree_component')
        self.old_seed = self.ai.get_editor_property('random_seed')
        self.old_cap = u.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
        self.old_paused = False
        for actor in (self.player, self.boss):
            for name, callback in [('on_skill_started',self.on_started),('on_skill_ended',self.on_ended),('on_combat_feedback',self.on_feedback)]:
                delegate = actor.get_editor_property(name)
                delegate.add_callable(callback)
                self.bindings.append((delegate,callback))
        self.report['status'] = 'running'
        u.SystemLibrary.execute_console_command(self.world,'t.MaxFPS 60')
        self.fps = 60
        for actor in (self.player,self.boss):
            self.reset_isolated()
            yield from self.wait(.4)
            self.new_case('queued_launch_reset_'+self.role(actor))
            before = actor.get_actor_location()
            actor.launch_character(u.Vector(0,-600,480),True,True)
            actor.add_movement_input(u.Vector(0,1,0),1,False)
            self.current['queued_velocity'] = [0,-600,480]
            self.current['before'] = BASE['xyz'](before)
            actor.reset_combat_state()
            self.stop_ai()  # Stop AI only; do not clear movement again in test.
            yield from self.wait(.4)
            self.check('pending.reset_position_'+self.role(actor), BASE['distance'](before,actor.get_actor_location()) < 10,
                       before=BASE['xyz'](before),after=BASE['xyz'](actor.get_actor_location()))
            self.check('pending.reset_velocity_'+self.role(actor), actor.get_velocity().length() < 1,
                       velocity=BASE['xyz'](actor.get_velocity()))
        for cap in (60,2):
            for seed in (731,739):
                self.awaiting_reset = False
                self.reset_isolated()
                u.SystemLibrary.execute_console_command(self.world,'t.MaxFPS 60')
                yield from self.wait(.4)
                expected_boss = self.boss.get_actor_location()
                expected_player = self.player.get_actor_location()
                self.new_case('real_R_pending_launch_cap%d_seed%d'%(cap,seed))
                self.ai.set_editor_property('random_seed',seed)
                self.player.launch_character(u.Vector(0,500,450),True,True)
                self.hit(self.player,self.boss,self.player.get_max_health()*2,parryable=False)
                self.check('death.pending_precondition',not self.player.is_alive())
                u.SystemLibrary.execute_console_command(self.world,'t.MaxFPS '+str(cap))
                self.fps = cap
                yield from self.wait(.6)
                self.check('death.cleared_pending_velocity',self.player.get_velocity().length() < 1,
                           velocity=BASE['xyz'](self.player.get_velocity()))
                # Queue a boss launch before PC consumes R. No game tick between.
                self.boss.launch_character(u.Vector(0,-600,480),True,True)
                self.boss.add_movement_input(u.Vector(0,1,0),1,False)
                self.awaiting_reset, self.reset_seen = True, None
                submitted = self.world_time()
                self.current['R_submitted_world_time'] = submitted
                self.key('R',True)
                wall_limit = time.monotonic()+5
                while self.reset_seen is None:
                    if time.monotonic()>wall_limit:
                        raise TimeoutError('R did not produce observable alive reset')
                    yield
                self.key('R',False)
                self.current['first_reset_positions'] = {'player':BASE['xyz'](self.player.get_actor_location()),
                                                        'boss':BASE['xyz'](self.boss.get_actor_location())}
                self.current['actual_input_processing_step'] = self.reset_seen-submitted
                self.check('retry.first_reset_player_position', BASE['distance'](expected_player,self.player.get_actor_location()) < 10)
                self.check('retry.first_reset_boss_position', BASE['distance'](expected_boss,self.boss.get_actor_location()) < 10,
                           expected=BASE['xyz'](expected_boss),actual=BASE['xyz'](self.boss.get_actor_location()))
                if cap==2:
                    self.check('reaction.real_coarse_frame',self.reset_seen-submitted >= .19,
                               actual_step=self.reset_seen-submitted)
                deadline = self.world_time()+3
                while not any(e['type']=='skill_started' and e['actor']=='boss' for e in self.current['events']):
                    if self.world_time()>deadline:
                        raise TimeoutError('AI never selected a skill after real R reset')
                    yield from self.wait(.001)
                first = next(e for e in self.current['events'] if e['type']=='skill_started' and e['actor']=='boss')
                delay = first['world_time']-self.reset_seen
                minimum = float(self.ai.get_editor_property('reaction_min'))
                self.check('reaction.no_pre_entry_delta_credit',delay >= minimum-.0001,
                           first_skill=first['skill'],reset_observed=self.reset_seen,skill_started=first['world_time'],
                           actual_delay=delay,required_min=minimum,
                           note='Delay measured from observed Reset processing, not R submission; legal >=minimum action is allowed.')
                self.awaiting_reset = False
                self.stop_ai()
                self.boss.cancel_current_skill()
        self.current = None
        self.report['status'] = 'passed' if all(a['pass'] for a in self.report['assertions']) else 'failed'

    def cleanup(self):
        try:
            self.awaiting_reset = False
            if self.brain and self.world and u.SystemLibrary.is_valid(self.world):
                self.reset_isolated()
        finally:
            super().cleanup()

def start():
    for key in (KEY,'_combat_arena_regression','_combat_arena_ai_scenarios','_combat_arena_ai_near','_combat_arena_spatial_visual','_combat_native_input_smoke'):
        if getattr(getattr(builtins,key,None),'handle',None) is not None:
            raise RuntimeError('Another runner is active')
    runner = Regression()
    setattr(builtins,KEY,runner)
    runner.handle = u.register_slate_post_tick_callback(runner.tick)
    runner.save()
    return str(runner.path)

def stop():
    runner=getattr(builtins,KEY,None)
    if runner and runner.handle is not None:
        runner.report['status']='stopped'
        runner.cleanup()
