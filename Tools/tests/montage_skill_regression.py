"""Opt-in native Montage tests. All runtime fixtures are transient duplicates, never saved."""
import builtins
import datetime
from pathlib import Path
import runpy
import unreal as u

BASE=runpy.run_path(str(Path(__file__).with_name('skill_editor_regression.py')))
KEY='_combat_montage_regression'

class MontageRunner(BASE['Runner']):
    def __init__(self):
        super().__init__()
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.path=BASE['ROOT']/'Saved/Acceptance'/('MontageSkills_'+stamp+'.json')
        self.report['scope']='Native Montage notifications and named graph windows in actual PIE; transient fixtures'

    def native(self,index=1):
        s=self.skill(index,1)
        montage=u.SystemLibrary.duplicate_object(u.load_asset('/Game/Combat/Animations/Native/Kwang/AM_Attack1'),s,'Montage')
        self.keep.append(montage)
        montage.set_editor_property('rate_scale',1)
        u.AnimationLibrary.remove_all_animation_notify_tracks(montage)
        u.AnimationLibrary.add_animation_notify_track(montage,'SkillTest')
        s.set_editor_property('montage',montage);s.set_editor_property('duration',montage.get_play_length());s.set_editor_property('use_montage_notifies',True)
        return s,montage

    def point(self,montage,at,event):
        notify=u.AnimationLibrary.add_animation_notify_event(montage,'SkillTest',at,u.CombatAnimNotify_SkillAction)
        notify.set_editor_property('action',event)
        return notify

    def window(self,montage,start,end,kind,name):
        notify=u.AnimationLibrary.add_animation_notify_state_event(montage,'SkillTest',start,end-start,u.CombatAnimNotifyState_SkillWindow)
        notify.set_editor_property('window_type',kind);notify.set_editor_property('window_name',name)
        return notify

    def run(self):
        self.world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        actors=u.GameplayStatics.get_all_actors_of_class(self.world,u.CombatCharacter)
        self.player=next(a for a in actors if not a.is_boss);self.boss=next(a for a in actors if a.is_boss)
        self.cap=u.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
        E=u.CombatSkillEventType;W=u.CombatSkillWindowType
        for fps in (30,60):
            u.SystemLibrary.execute_console_command(self.world,'t.MaxFPS '+str(fps)); prefix=str(fps)+'.'
            s,m=self.native();length=m.get_play_length()
            bullet=self.projectile();action=self.event(E.PROJECTILE,projectile=bullet)
            self.point(m,.12,action)
            # A poison legacy array would double the shot if both paths were still executed.
            s.set_editor_property('events',[self.event(E.PROJECTILE,at=.05,projectile=bullet)])
            self.reset([s]);hp=self.boss.get_health();self.activate(s)
            yield from self.wait(length+.4)
            self.check(prefix+'native.single_source',abs(hp-self.boss.get_health()-20)<.01,damage=hp-self.boss.get_health())
            self.check(prefix+'native.normal_end',not self.player.is_busy())

            s,m=self.native();follow=self.skill(2,1)
            self.window(m,.25,.55,W.DERIVATION,'Combo_A')
            rule=u.CombatSkillDerivation();rule.set_editor_property('target_skill',follow.get_editor_property('skill_tag'));rule.set_editor_property('input_tag',BASE['tag']('Combat.Input.Attack'));rule.set_editor_property('window_name','Combo_A')
            rule.set_editor_property('window_start',99);rule.set_editor_property('window_end',100)
            s.set_editor_property('derivations',[rule]);self.reset([s,follow]);self.activate(s)
            yield from self.wait(.16)
            self.player.request_skill_by_input_tag(BASE['tag']('Combat.Input.Attack'))
            yield from self.wait(.18)
            self.check(prefix+'native.named_window_derivation',BASE['tag_name'](self.player.get_active_skill_tag()).endswith('Sample2'))
            self.check(prefix+'native.old_window_closed',not self.player.skill_runtime.is_montage_window_open('Combo_A'))

            self.reset([s,follow]);self.activate(s);self.player.request_skill_by_input_tag(BASE['tag']('Combat.Input.Attack'))
            yield from self.wait(.36)
            self.check(prefix+'native.buffer_expired',BASE['tag_name'](self.player.get_active_skill_tag()).endswith('Sample1'))
            self.check(prefix+'native.state_open',self.player.skill_runtime.is_montage_window_open('Combo_A'))
            self.player.cancel_current_skill()
            self.check(prefix+'native.cancel_closes_state',not self.player.skill_runtime.is_montage_window_open('Combo_A'))

            self.reset([s]);self.activate(s);yield from self.wait(.3)
            self.player.cancel_current_skill();self.activate(s);yield from self.wait(.08)
            self.check(prefix+'native.restart_ignores_outgoing_end',self.player.is_busy() and not self.player.skill_runtime.is_montage_window_open('Combo_A'))
            yield from self.wait(.23)
            self.check(prefix+'native.restart_new_window',self.player.skill_runtime.is_montage_window_open('Combo_A'))
            yield from self.wait(.3)
            self.check(prefix+'native.state_closes_naturally',not self.player.skill_runtime.is_montage_window_open('Combo_A'))

            # Windows are per-character even though both characters share the exact same notify objects.
            self.reset([s]);other=u.CombatSkillEditorLibrary.spawn_preview_target(u.Vector(0,700,100),False);self.spawned.append(other)
            other.mesh.set_skeletal_mesh_asset(self.player.mesh.get_skeletal_mesh_asset())
            other.mesh.set_anim_instance_class(self.player.mesh.get_anim_instance().get_class())
            other.equip_runtime_skills([s]);self.activate(s);yield from self.wait(.22)
            other.request_skill_by_tag(s.get_editor_property('skill_tag'));yield from self.wait(.3)
            self.check(prefix+'native.shared_montage_both_open',self.player.skill_runtime.is_montage_window_open('Combo_A') and other.skill_runtime.is_montage_window_open('Combo_A'))
            self.player.cancel_current_skill()
            self.check(prefix+'native.shared_montage_isolated',other.skill_runtime.is_montage_window_open('Combo_A'))
            other.destroy_actor()

            # State windows and scoped buff cleanup on interruption.
            s,m=self.native();buff=self.new(u.CombatBuffDefinition);buff.set_editor_property('buff_tag',BASE['tag']('Combat.Buff.Power'))
            self.point(m,.08,self.event(E.APPLY_BUFF,buff=buff,skill_scoped=True))
            self.window(m,.2,.45,W.CANCEL,'Cancel')
            follow=self.skill(2,1);self.reset([s,follow]);self.activate(s);yield from self.wait(.13)
            self.check(prefix+'native.buff_applied',self.player.skill_runtime.get_buff_stacks(buff)==1)
            yield from self.wait(.13)
            self.check(prefix+'native.cancel_window_allows_switch',self.activate(follow))
            self.check(prefix+'native.buff_scope_cleanup',self.player.skill_runtime.get_buff_stacks(buff)==0)

            s,m=self.native();bullet=self.projectile(speed=100,max_speed=100)
            self.point(m,.08,self.event(E.PROJECTILE,projectile=bullet,bursts=4,burst_interval=.1))
            self.reset([s]);self.activate(s);yield from self.wait(.14)
            self.check(prefix+'native.burst_first',len(self.active_projectiles())==1)
            self.player.cancel_current_skill();yield from self.wait(.4)
            self.check(prefix+'native.burst_cancel_cleanup',not self.active_projectiles())

        # Authoring payload Time has no authority over native track placement.
        s,m=self.native();buff=self.new(u.CombatBuffDefinition);buff.set_editor_property('buff_tag',BASE['tag']('Combat.Buff.Power'));buff.set_editor_property('duration',3)
        self.point(m,.2,self.event(E.APPLY_BUFF,at=999,buff=buff))
        self.reset([s]);self.activate(s);yield from self.wait(.3)
        self.check('native.payload_time_ignored',self.player.skill_runtime.get_buff_stacks(buff)==1)

        s,m=self.native();self.point(m,m.get_play_length(),self.event(E.APPLY_BUFF,buff=buff))
        self.reset([s]);self.activate(s);yield from self.wait(m.get_play_length()+.2)
        self.check('native.end_frame_event',self.player.skill_runtime.get_buff_stacks(buff)==1)

        s,m=self.native();self.point(m,.35,self.event(E.APPLY_BUFF,buff=buff));self.window(m,.2,.5,W.DERIVATION,'Skipped')
        self.reset([s]);self.activate(s);yield from self.wait(.1)
        self.player.mesh.get_anim_instance().montage_set_position(m,.6)
        yield from self.wait(.1)
        self.check('native.seek_does_not_replay_skipped_action',self.player.skill_runtime.get_buff_stacks(buff)==0)
        self.check('native.seek_does_not_open_skipped_window',not self.player.skill_runtime.is_montage_window_open('Skipped'))

        s,m=self.native();bullet=self.projectile(speed=100,max_speed=100)
        self.point(m,.08,self.event(E.PROJECTILE,projectile=bullet,bursts=3,burst_interval=.18))
        self.window(m,.1,.5,W.DERIVATION,'Paused')
        self.reset([s]);self.activate(s);yield from self.wait(.16)
        anim=self.player.mesh.get_anim_instance();anim.montage_pause(m);count=len(self.active_projectiles())
        yield from self.wait(.3)
        self.check('native.pause_retains_state',self.player.skill_runtime.is_montage_window_open('Paused'))
        self.check('native.pause_stops_pending_bursts',len(self.active_projectiles())==count)
        anim.montage_resume(m);yield from self.wait(.3)
        self.check('native.resume_continues_bursts',len(self.active_projectiles())>count)

def start():
    for key in (KEY,'_combat_skill_editor_regression','_combat_arena_regression'):
        if getattr(getattr(builtins,key,None),'handle',None) is not None:raise RuntimeError('Active runner: '+key)
    runner=MontageRunner();setattr(builtins,KEY,runner);runner.handle=u.register_slate_post_tick_callback(runner.tick);return str(runner.path)

def status():
    r=getattr(builtins,KEY,None)
    return {'status':r.report['status'],'checks':len(r.report['assertions']),'path':str(r.path)} if r else {'status':'not_started'}
