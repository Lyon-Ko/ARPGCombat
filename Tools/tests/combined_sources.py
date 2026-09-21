"""Actual blade sweep + projectile/AOE composition, isolated from natural bouts."""
import builtins
import datetime
from pathlib import Path
import runpy
import unreal as u
BASE = runpy.run_path(str(Path(__file__).with_name('arena_regression.py')))
KEY = '_combat_combined_sources'

class Combined(BASE['ArenaRegression']):
    def __init__(self):
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        super().__init__(fps_caps=(60,),fights_per_cap=1,output_name='CombinedSources_'+stamp+'.json')
        self.definition=None
        self.original={}
        self.restart_on=None
        self.report['combined_cases']=[]
        self.report['execution']='Isolated real TraceHitWindow/CombatProjectile/DoAreaDamage; no ReceiveCombatHit injection'

    def pause_montage(self):
        anim=self.player.get_editor_property('mesh').get_anim_instance()
        montage=anim.get_current_active_montage()
        if not montage:
            raise RuntimeError('Actual Attack1 montage required')
        anim.montage_pause(montage)

    def on_feedback(self, source,target,cue,location,intensity):
        super().on_feedback(source,target,cue,location,intensity)
        name=BASE['tag_name'](cue)
        if source==self.player and name==self.restart_on:
            self.restart_on=None  # exactly one reentrant restart
            self.player.cancel_current_skill()
            activated=self.player.request_skill_by_tag(BASE['tag']('Combat.Skill.Attack1'))
            self.current['reentrant_restart']={'world_time':self.world_time(),'activated':bool(activated)}
            if activated:
                self.pause_montage()
                if name=='Combat.Cue.Hit':
                    self.player.open_hit_window()

    def fixture(self,name):
        self.reset_isolated()
        yield from self.wait(.3)
        self.current={'name':name,'events':[]}
        self.report['combined_cases'].append(self.current)
        p=self.player.get_actor_location()
        self.player.set_actor_rotation(u.Rotator(roll=0,pitch=0,yaw=0),True)
        self.boss.set_actor_location(u.Vector(p.x+400,p.y,p.z),False,True)
        self.check(name+'.activated',self.player.request_skill_by_tag(BASE['tag']('Combat.Skill.Attack1')))
        self.pause_montage()
        yield from self.wait(.05)

    def move_target_to_actual_blade(self):
        source=self.player.get_editor_property('mesh') if self.player.get_editor_property('trace_from_character_mesh') else self.player.get_editor_property('weapon_mesh')
        tip_name=self.player.get_editor_property('trace_end_socket')
        if not source.does_socket_exist(tip_name):
            raise RuntimeError('Real blade tip socket required for trace fixture')
        tip=source.get_socket_location(tip_name)
        before=self.boss.get_actor_location()
        target=u.Vector(tip.x,tip.y,max(tip.z,before.z))
        self.boss.set_actor_location(target,False,True)
        self.current['blade_fixture']={'socket':str(tip_name),'world_tip':BASE['xyz'](tip),'target':BASE['xyz'](target)}

    def run(self):
        self.world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world or u.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError('Approved unpaused PIE required')
        actors=u.GameplayStatics.get_all_actors_of_class(self.world,u.CombatCharacter)
        self.player=next(a for a in actors if not a.get_editor_property('is_boss'))
        self.boss=next(a for a in actors if a.get_editor_property('is_boss'))
        self.controller=self.player.get_controller()
        self.check('viewport.actual1080',tuple(self.controller.get_viewport_size())==(1920,1080),actual=list(self.controller.get_viewport_size()))
        self.ai=self.boss.get_controller()
        self.brain=self.ai.get_editor_property('state_tree_component')
        self.old_seed=self.ai.get_editor_property('random_seed')
        self.old_cap=u.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
        self.old_paused=False
        u.SystemLibrary.execute_console_command(self.world,'t.MaxFPS 60')
        self.fps=60
        for actor in (self.player,self.boss):
            for name,callback in [('on_skill_started',self.on_started),('on_skill_ended',self.on_ended),('on_combat_feedback',self.on_feedback)]:
                delegate=actor.get_editor_property(name);delegate.add_callable(callback)
                self.bindings.append((delegate,callback))
        self.definition=next(d for d in self.player.get_editor_property('skill_definitions') if BASE['tag_name'](d.get_editor_property('skill_tag'))=='Combat.Skill.Attack1')
        self.original={name:self.definition.get_editor_property(name) for name in ('duration','cooldown')}
        self.report['temporary_definition_fields']={'path':self.definition.get_path_name(),'original':dict(self.original),'test_values':{'duration':5.0,'cooldown':0.0},'saved_to_content':False}
        self.definition.set_editor_property('duration',5.0)
        self.definition.set_editor_property('cooldown',0.0)
        damage=float(self.definition.get_editor_property('damage'))
        self.report['unchanged_damage']=damage
        self.report['status']='running'
        for source in ('projectile','aoe'):
            yield from self.fixture('blade_window_after_'+source)
            before=self.boss.get_health()
            self.player.open_hit_window()
            if source=='projectile':
                self.player.emit_skill_projectile()
                owned=[p.get_path_name() for p in u.GameplayStatics.get_all_actors_of_class(self.world,u.CombatProjectile) if p.get_owner()==self.player]
                self.check('projectile.actual_spawn',bool(owned),actors=owned)
            else:
                self.player.show_area_warning()
                self.player.detonate_area()
            deadline=self.world_time()+.8
            while self.boss.get_health()==before and self.world_time()<deadline:
                yield from self.wait(.001)
            self.check(source+'.independent_damage',abs(before-self.boss.get_health()-damage)<.01,
                       before=before,after=self.boss.get_health(),expected_damage=damage)
            self.move_target_to_actual_blade()
            yield from self.wait(.15)
            self.check(source+'.blade_separate_damage',abs(before-self.boss.get_health()-2*damage)<.01,
                       before=before,after=self.boss.get_health(),expected_total=2*damage)
            yield from self.wait(.2)
            self.check(source+'.same_window_dedup',abs(before-self.boss.get_health()-2*damage)<.01,
                       after=self.boss.get_health())
            self.player.cancel_current_skill()
        yield from self.fixture('trace_callback_same_definition_restart')
        before=self.boss.get_health()
        self.move_target_to_actual_blade()
        self.restart_on='Combat.Cue.Hit'
        self.player.open_hit_window()
        yield from self.wait(.2)
        hits=[e for e in self.current['events'] if e.get('cue')=='Combat.Cue.Hit' and e['actor']=='player']
        restarted=self.current.get('reentrant_restart',{})
        self.check('trace.restart_activated',restarted.get('activated',False),restart=restarted)
        self.check('trace.old_iteration_not_reentered',len(hits)==2 and hits[0]['world_time']!=hits[1]['world_time'],hits=hits)
        self.check('trace.new_window_once',abs(before-self.boss.get_health()-2*damage)<.01,before=before,after=self.boss.get_health())
        self.restart_on=None
        yield from self.fixture('aoe_release_callback_same_definition_restart')
        before=self.boss.get_health()
        self.restart_on='Combat.Cue.AreaRelease'
        self.player.show_area_warning()
        self.player.detonate_area()
        yield from self.wait(.35)
        self.check('aoe.restart_activated',self.current.get('reentrant_restart',{}).get('activated',False))
        self.check('aoe.old_release_cannot_arm_new_execution',abs(self.boss.get_health()-before)<.01,
                   before=before,after=self.boss.get_health())
        self.restart_on=None
        self.current=None
        self.report['status']='passed' if all(a['pass'] for a in self.report['assertions']) else 'failed'

    def cleanup(self):
        try:
            self.restart_on=None
            if self.brain and self.world and u.SystemLibrary.is_valid(self.world):
                self.reset_isolated()
        finally:
            if self.definition:
                for name,value in self.original.items():
                    self.definition.set_editor_property(name,value)
                self.report['temporary_definition_restored']={name:self.definition.get_editor_property(name) for name in self.original}
            super().cleanup()

def start():
    for key in (KEY,'_combat_arena_regression','_combat_build11_regression','_combat_arena_ai_scenarios','_combat_arena_ai_near','_combat_arena_spatial_visual','_combat_native_input_smoke'):
        if getattr(getattr(builtins,key,None),'handle',None) is not None:
            raise RuntimeError('Another runner is active')
    runner=Combined();setattr(builtins,KEY,runner)
    runner.handle=u.register_slate_post_tick_callback(runner.tick);runner.save()
    return str(runner.path)

def stop():
    runner=getattr(builtins,KEY,None)
    if runner and runner.handle is not None:
        runner.report['status']='stopped';runner.cleanup()
