"""Opt-in, non-blocking PIE tests for designer skill runtime. Never edits saved assets."""
import builtins
import datetime
import hashlib
import json
import time
import traceback
from pathlib import Path
import unreal as u

KEY = '_combat_skill_editor_regression'
ROOT = Path(u.Paths.project_dir()).resolve()

def tag(name):
    result = u.GameplayTag()
    result.import_text('(TagName="'+name+'")')
    return result

def tag_name(value):
    return str(value.get_editor_property('tag_name'))

class Runner:
    def __init__(self):
        self.handle = None
        self.keep = []
        self.spawned = []
        self.report = {'status': 'running', 'scope': 'isolated real PIE runtime; transient definitions; no saved asset edits', 'assertions': [], 'performance': []}
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.path = ROOT/'Saved/Acceptance'/('SkillEditor_'+stamp+'.json')
        self.report['binary_sha256'] = hashlib.sha256((ROOT/'Binaries/Win64/UnrealEditor-Combat.dll').read_bytes()).hexdigest()
        self.steps = self.run()
        self.deadline = time.monotonic()+240
        self.cap = None

    def check(self, name, passed, **details):
        self.report['assertions'].append(dict(name=name, passed=bool(passed), **details))
        if not passed:
            u.log_warning('SkillEditor FAIL: '+name+' '+str(details))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding='utf-8')

    def tick(self, delta):
        try:
            if time.monotonic()>self.deadline:
                raise TimeoutError('Skill editor regression exceeded 240 seconds')
            next(self.steps)
        except StopIteration:
            self.report['status'] = 'passed' if all(x['passed'] for x in self.report['assertions']) else 'failed'
            self.cleanup()
        except Exception:
            self.report['status'] = 'error'
            self.report['error'] = traceback.format_exc()
            u.log_error(self.report['error'])
            self.cleanup()

    def cleanup(self):
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        if hasattr(self, 'player'):
            self.player.reset_combat_state()
            self.boss.reset_combat_state()
            self.boss.get_controller().get_editor_property('state_tree_component').stop_logic('test ended')
        if self.cap is not None:
            u.SystemLibrary.execute_console_command(self.world, 't.MaxFPS '+str(self.cap))
        for actor in self.spawned:
            if u.SystemLibrary.is_valid(actor):
                actor.destroy_actor()
        self.save()

    def wait(self, seconds):
        end = u.GameplayStatics.get_time_seconds(self.world)+seconds
        while u.GameplayStatics.get_time_seconds(self.world)<end:
            yield

    def new(self, cls):
        obj = u.new_object(cls)
        self.keep.append(obj)
        return obj

    def skill(self, index=1, duration=.6):
        obj = self.new(u.CombatSkillDefinition)
        obj.set_editor_property('data_driven', True)
        obj.set_editor_property('skill_tag', tag('Combat.Skill.Editor.Sample'+str(index)))
        obj.set_editor_property('duration', duration)
        obj.set_editor_property('cooldown', 0)
        return obj

    def event(self, kind, at=.05, **fields):
        obj = u.CombatSkillEvent()
        obj.set_editor_property('type', kind)
        obj.set_editor_property('time', at)
        for key,value in fields.items():
            obj.set_editor_property(key,value)
        return obj

    def projectile(self, **fields):
        p=self.new(u.CombatProjectileDefinition)
        p.set_editor_property('speed', 1600)
        p.set_editor_property('max_speed', 1600)
        for key,value in fields.items():
            p.set_editor_property(key,value)
        return p

    def reset(self, skills):
        self.player.reset_combat_state()
        self.boss.reset_combat_state()
        self.boss.get_controller().get_editor_property('state_tree_component').stop_logic('skill editor fixture')
        self.player.set_actor_location(u.Vector(0,0,100),False,True)
        self.player.set_actor_rotation(u.Rotator(),True)
        self.boss.set_actor_location(u.Vector(650,0,100),False,True)
        self.player.set_combat_target(self.boss)
        self.player.equip_runtime_skills(skills)
        self.player.set_editor_property('hit_stop_duration',0)
        self.boss.set_editor_property('hit_stop_duration',0)

    def active_projectiles(self):
        return list(u.GameplayStatics.get_all_actors_of_class(self.world,u.CombatProjectile))

    def activate(self, skill):
        return self.player.request_skill_by_tag(skill.get_editor_property('skill_tag'))

    def obstacle(self, location, size):
        actor=u.CombatSkillEditorLibrary.spawn_preview_obstacle(location,size)
        self.spawned.append(actor)
        return actor

    def run(self):
        self.world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not self.world:
            raise RuntimeError('Start a Skill Editor PIE preview first')
        actors=u.GameplayStatics.get_all_actors_of_class(self.world,u.CombatCharacter)
        self.player=next(a for a in actors if not a.get_editor_property('is_boss'))
        self.boss=next(a for a in actors if a.get_editor_property('is_boss'))
        self.cap=u.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
        E=u.CombatSkillEventType
        for fps in (30,60):
            u.SystemLibrary.execute_console_command(self.world,'t.MaxFPS '+str(fps))
            prefix=str(fps)+'.'
            bullet=self.projectile()
            s=self.skill(); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet)])
            self.reset([s]); hp=self.boss.get_health()
            self.check(prefix+'projectile.activate',self.activate(s))
            yield from self.wait(.9)
            self.check(prefix+'projectile.damage_once',abs(hp-self.boss.get_health()-20)<.01,damage=hp-self.boss.get_health())
            self.check(prefix+'skill.normal_end',not self.player.is_busy())

            # Input buffer and exact branch choice with two independently granted specs.
            a=self.skill(1,1); b=self.skill(2,1)
            rule=u.CombatSkillDerivation()
            rule.set_editor_property('target_skill',b.get_editor_property('skill_tag'))
            rule.set_editor_property('input_tag',tag('Combat.Input.Attack'))
            rule.set_editor_property('window_start',.3); rule.set_editor_property('window_end',.8)
            a.set_editor_property('derivations',[rule]); self.reset([a,b]); self.activate(a)
            yield from self.wait(.23)
            self.player.request_skill_by_input_tag(tag('Combat.Input.Attack'))
            yield from self.wait(.12)
            self.check(prefix+'derive.buffered_input',tag_name(self.player.get_active_skill_tag()).endswith('Sample2'))

            # Completed derivation must happen after the outgoing GAS instance has ended.
            rule.set_editor_property('trigger',u.CombatDerivationTrigger.COMPLETED)
            rule.set_editor_property('window_start',0); rule.set_editor_property('window_end',.2)
            a.set_editor_property('duration',.2); a.set_editor_property('derivations',[rule]); self.reset([a,b]); self.activate(a)
            yield from self.wait(.35)
            self.check(prefix+'derive.completed',tag_name(self.player.get_active_skill_tag()).endswith('Sample2'))

            # Persistent, scoped and stacked effects have different lifetimes.
            buff=self.new(u.CombatBuffDefinition)
            buff.set_editor_property('buff_tag',tag('Combat.Buff.Power'))
            buff.set_editor_property('duration',.4); buff.set_editor_property('max_stacks',3)
            buff.set_editor_property('damage_multiplier',1.5)
            self.reset([s]); runtime=self.player.get_editor_property('skill_runtime')
            runtime.add_buff(buff,self.player,False); runtime.add_buff(buff,self.player,False)
            self.check(prefix+'buff.stacking',runtime.get_buff_stacks(buff)==2)
            self.activate(s); self.player.cancel_current_skill()
            self.check(prefix+'buff.persistent_on_cancel',runtime.get_buff_stacks(buff)==2)
            yield from self.wait(.5)
            self.check(prefix+'buff.expired',runtime.get_buff_stacks(buff)==0)
            self.activate(s); runtime.add_buff(buff,self.player,True); self.player.cancel_current_skill()
            self.check(prefix+'buff.scoped_cleanup',runtime.get_buff_stacks(buff)==0)

            burn=self.new(u.CombatBuffDefinition); burn.set_editor_property('buff_tag',tag('Combat.Buff.Burn'))
            burn.set_editor_property('duration',.35); burn.set_editor_property('period',.1); burn.set_editor_property('health_per_period',-5)
            self.reset([s]); hp=self.boss.get_health(); self.boss.get_editor_property('skill_runtime').add_buff(burn,self.player,False)
            yield from self.wait(.45)
            self.check(prefix+'buff.periodic_damage',abs(hp-self.boss.get_health()-15)<.01,damage=hp-self.boss.get_health())

            # Explicit interrupt reason and armor suppression.
            armor=self.new(u.CombatBuffDefinition); armor.set_editor_property('buff_tag',tag('Combat.Buff.Armor')); armor.set_editor_property('super_armor',True)
            self.reset([s]); self.activate(s); runtime.add_buff(armor,self.player,False)
            self.check(prefix+'interrupt.armor_blocks_hit',not self.player.try_interrupt_skill(u.CombatInterruptReason.HIT) and self.player.is_busy())
            self.check(prefix+'interrupt.poise_break',self.player.try_interrupt_skill(u.CombatInterruptReason.POISE_BREAK) and not self.player.is_busy())

            # A missile turns toward an offset target and resolves one explosion.
            missile=self.projectile(motion=u.CombatProjectileMotion.GUIDED,speed=900,max_speed=1500,acceleration=400,explosion_radius=220,turn_degrees_per_second=180,guidance_delay=0)
            s.set_editor_property('duration',2); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=missile,aim_at_target=False)])
            self.reset([s]); self.boss.set_actor_location(u.Vector(650,240,100),False,True); hp=self.boss.get_health(); self.activate(s)
            yield from self.wait(1.4)
            self.check(prefix+'missile.guided_damage',hp>self.boss.get_health(),damage=hp-self.boss.get_health())
            self.check(prefix+'missile.destroy_after_impact',len(self.active_projectiles())==0)

            # Delayed bursts must not leak out of a cancelled execution.
            bullet.set_editor_property('speed',100); bullet.set_editor_property('max_speed',100)
            s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet,bursts=3,burst_interval=.2)])
            self.reset([s]); self.activate(s); yield from self.wait(.1)
            self.check(prefix+'burst.first_spawn',len(self.active_projectiles())==1)
            self.player.cancel_current_skill(); yield from self.wait(.5)
            self.check(prefix+'burst.cancel_cleanup',len(self.active_projectiles())==0)
            # Normal end preserves the released projectile; reset always removes it.
            s.set_editor_property('duration',.12); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet)])
            self.reset([s]); self.activate(s); yield from self.wait(.22)
            self.check(prefix+'projectile.survives_normal_end',len(self.active_projectiles())==1)
            self.player.reset_combat_state()
            self.check(prefix+'projectile.reset_cleanup',len(self.active_projectiles())==0)

        # Collision, lifetime, rejection and stacking tests use actual runtime objects.
        yield from self.edge_cases()
        # Deterministic invalid assets must be rejected by the editor's actual validator.
        bad=self.skill(); bad.set_editor_property('events',[self.event(E.PROJECTILE)])
        self.check('validation.missing_projectile',bool(u.CombatSkillEditorLibrary.validate_skill_assets([bad])))
        # Fixed spawn count, explicit observed frame samples (not a performance guarantee).
        bullet=self.projectile(speed=100,max_speed=100,lifetime=3)
        s=self.skill(duration=2); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet,pattern=u.CombatFirePattern.RING,count=128)])
        self.reset([s]); self.boss.set_actor_location(u.Vector(2000,2000,100),False,True); self.activate(s)
        yield from self.wait(.08)
        count=len(self.active_projectiles()); samples=[]; wall_samples=[]; last=u.GameplayStatics.get_time_seconds(self.world); wall_last=time.perf_counter()
        for _ in range(60):
            yield
            now=u.GameplayStatics.get_time_seconds(self.world); samples.append((now-last)*1000); last=now
            wall_now=time.perf_counter(); wall_samples.append((wall_now-wall_last)*1000); wall_last=wall_now
        self.report['performance'].append(dict(spawned=count,world_steps_ms=samples,slate_wall_steps_ms=wall_samples,mean_ms=sum(wall_samples)/len(wall_samples),max_ms=max(wall_samples),interpretation='Observed Slate callback intervals during fixed projectile workload; not GPU frame timings or a stable-fps claim'))
        self.check('stress.spawn_128',count==128,observed=count)

    def edge_cases(self):
        E=u.CombatSkillEventType
        bullet=self.projectile(speed=50000,max_speed=50000)
        s=self.skill(duration=.5); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet,aim_at_target=False)])
        self.reset([s]); hp=self.boss.get_health()
        wall=self.obstacle(u.Vector(350,0,150),u.Vector(2,300,300))
        self.activate(s); yield from self.wait(.2)
        self.check('collision.high_speed_thin_wall',self.boss.get_health()==hp and not self.active_projectiles())
        wall.destroy_actor()

        # Spawn inside blocking geometry must consume the projectile without hitting behind it.
        self.reset([s]); hp=self.boss.get_health(); wall=self.obstacle(u.Vector(90,0,135),u.Vector(30,80,100))
        self.activate(s); yield from self.wait(.2)
        self.check('collision.initial_overlap',self.boss.get_health()==hp and not self.active_projectiles())
        wall.destroy_actor()

        bullet.set_editor_property('speed',1600); bullet.set_editor_property('max_speed',1600); bullet.set_editor_property('bounces',1)
        self.reset([s]); self.boss.set_actor_location(u.Vector(-300,0,100),False,True); hp=self.boss.get_health()
        wall=self.obstacle(u.Vector(350,0,150),u.Vector(10,300,300)); self.activate(s)
        yield from self.wait(.9)
        self.check('collision.bounce_damage',abs(hp-self.boss.get_health()-20)<.01,damage=hp-self.boss.get_health()); wall.destroy_actor()

        # Piercing two actors still hits each actor only once despite multiple mesh components.
        bullet.set_editor_property('bounces',0); bullet.set_editor_property('penetrations',1)
        self.reset([s]); other=u.CombatSkillEditorLibrary.spawn_preview_target(u.Vector(350,0,100),True); self.spawned.append(other)
        hp1=other.get_health(); hp2=self.boss.get_health(); self.activate(s); yield from self.wait(.55)
        self.check('collision.pierce_two_targets',abs(hp1-other.get_health()-20)<.01 and abs(hp2-self.boss.get_health()-20)<.01,damage1=hp1-other.get_health(),damage2=hp2-self.boss.get_health())
        other.destroy_actor()

        bullet.set_editor_property('penetrations',0); bullet.set_editor_property('explosion_radius',250); bullet.set_editor_property('edge_damage_fraction',1)
        self.reset([s]); hp=self.boss.get_health(); self.activate(s); yield from self.wait(.6)
        self.check('explosion.no_direct_double_damage',abs(hp-self.boss.get_health()-20)<.01,damage=hp-self.boss.get_health())
        bullet.set_editor_property('stack_direct_and_explosion',True)
        self.reset([s]); hp=self.boss.get_health(); self.activate(s); yield from self.wait(.6)
        self.check('explosion.explicit_stack',abs(hp-self.boss.get_health()-40)<.01,damage=hp-self.boss.get_health())

        bullet.set_editor_property('explosion_radius',0); bullet.set_editor_property('speed',100); bullet.set_editor_property('max_speed',100); bullet.set_editor_property('lifetime',.15)
        self.reset([s]); self.activate(s); yield from self.wait(.3)
        self.check('projectile.lifetime_expiry',not self.active_projectiles())
        bullet.set_editor_property('lifetime',5); bullet.set_editor_property('max_distance',10)
        self.reset([s]); self.activate(s); yield from self.wait(.3)
        self.check('projectile.distance_expiry',not self.active_projectiles())

        # Default cancel policy can be explicitly changed without affecting reset cleanup.
        bullet.set_editor_property('max_distance',10000); bullet.set_editor_property('destroy_on_interrupt',False)
        self.reset([s]); self.activate(s); yield from self.wait(.1); self.player.cancel_current_skill()
        self.check('projectile.keep_on_cancel',len(self.active_projectiles())==1)
        self.player.reset_combat_state(); self.check('projectile.reset_overrides_keep',not self.active_projectiles())

        # Verify numerical effect application, not only buff bookkeeping.
        bullet=self.projectile(); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet)])
        buff=self.new(u.CombatBuffDefinition); buff.set_editor_property('buff_tag',tag('Combat.Buff.Power')); buff.set_editor_property('duration',.8); buff.set_editor_property('max_stacks',3); buff.set_editor_property('damage_multiplier',1.5)
        self.reset([s]); rt=self.player.get_editor_property('skill_runtime'); rt.add_buff(buff,self.player,False); rt.add_buff(buff,self.player,False)
        hp=self.boss.get_health(); self.activate(s); yield from self.wait(.6)
        self.check('buff.actual_damage_multiplier',abs(hp-self.boss.get_health()-45)<.01,damage=hp-self.boss.get_health())
        yield from self.wait(.3); hp=self.boss.get_health(); self.activate(s); yield from self.wait(.6)
        self.check('buff.multiplier_removed',abs(hp-self.boss.get_health()-20)<.01,damage=hp-self.boss.get_health())

        # Incoming force priority and denied reasons are independently configurable.
        a=self.skill(1,1); b=self.skill(2,1)
        a.set_editor_property('interrupt_resistance',10); b.set_editor_property('force_interrupt',True); b.set_editor_property('interrupt_priority',5)
        self.reset([a,b]); self.activate(a)
        self.check('interrupt.priority_rejected',self.player.request_skill_detailed(b.get_editor_property('skill_tag'))==u.CombatSkillRequestResult.UNINTERRUPTIBLE)
        b.set_editor_property('interrupt_priority',11)
        self.check('interrupt.priority_accepted',self.activate(b))
        tags=u.GameplayTagContainer(); tags.import_text('(GameplayTags=((TagName="Combat.Buff.Power")))')
        a.set_editor_property('exclusive_tags',tags); b.set_editor_property('exclusive_tags',tags)
        self.reset([a,b]); self.activate(a)
        self.check('interrupt.exclusion',self.player.request_skill_detailed(b.get_editor_property('skill_tag'))==u.CombatSkillRequestResult.BLOCKED)
        a.set_editor_property('allowed_interrupts',[])
        self.check('interrupt.reason_denied',not self.player.try_interrupt_skill(u.CombatInterruptReason.HIT))
        self.check('interrupt.death_forces_cleanup',self.player.try_interrupt_skill(u.CombatInterruptReason.DEATH))

        # A buffered input outside the look-ahead duration expires.
        a=self.skill(1,1); b=self.skill(2,1); r=u.CombatSkillDerivation(); r.set_editor_property('target_skill',b.get_editor_property('skill_tag')); r.set_editor_property('input_tag',tag('Combat.Input.Attack')); r.set_editor_property('window_start',.7); r.set_editor_property('window_end',.9); a.set_editor_property('derivations',[r])
        self.reset([a,b]); self.activate(a); self.player.request_skill_by_input_tag(tag('Combat.Input.Attack')); yield from self.wait(.8)
        self.check('derive.expired_buffer',not tag_name(self.player.get_active_skill_tag()).endswith('Sample2'))

        # No old projectile may trigger hit derivation on a newly activated execution.
        bullet=self.projectile(speed=400,max_speed=400,destroy_on_interrupt=False)
        old=self.skill(1,.2); old.set_editor_property('events',[self.event(E.PROJECTILE,projectile=bullet)])
        new=self.skill(2,2); target=self.skill(3,1)
        r=u.CombatSkillDerivation(); r.set_editor_property('target_skill',target.get_editor_property('skill_tag')); r.set_editor_property('trigger',u.CombatDerivationTrigger.HIT); r.set_editor_property('window_end',2); new.set_editor_property('derivations',[r])
        self.reset([old,new,target]); self.activate(old); yield from self.wait(.3); self.activate(new); yield from self.wait(1.3)
        self.check('derive.old_projectile_isolation',tag_name(self.player.get_active_skill_tag()).endswith('Sample2'))

        # Limited steering, target loss and reacquisition are observed on live actors.
        missile=self.projectile(motion=u.CombatProjectileMotion.GUIDED,speed=300,max_speed=300,guidance_delay=0,turn_degrees_per_second=30,acquire_half_angle=180,lost_target=u.CombatLostTarget.DESTROY)
        s=self.skill(duration=2); s.set_editor_property('events',[self.event(E.PROJECTILE,projectile=missile,aim_at_target=False)])
        self.reset([s]); self.boss.set_actor_location(u.Vector(600,600,100),False,True); self.activate(s); yield from self.wait(.25)
        actors=self.active_projectiles()
        self.check('missile.turn_rate_limit',len(actors)==1 and 0<abs(actors[0].get_actor_rotation().yaw)<10,rotation=actors[0].get_actor_rotation().yaw if actors else None)
        self.boss.set_actor_location(u.Vector(10000,10000,100),False,True); yield from self.wait(.15)
        self.check('missile.lost_target_destroy',not self.active_projectiles())

        missile.set_editor_property('lost_target',u.CombatLostTarget.REACQUIRE); missile.set_editor_property('turn_degrees_per_second',360); missile.set_editor_property('speed',800); missile.set_editor_property('max_speed',800)
        self.reset([s]); self.boss.set_actor_location(u.Vector(10000,10000,100),False,True); self.activate(s); yield from self.wait(.2)
        other=u.CombatSkillEditorLibrary.spawn_preview_target(u.Vector(650,150,100),True); self.spawned.append(other); hp=other.get_health()
        yield from self.wait(1)
        self.check('missile.reacquire_new_target',other.get_health()<hp,damage=hp-other.get_health()); other.destroy_actor()

        # Stacked periodic effects kill through the same death path and clear on reset.
        lethal=self.new(u.CombatBuffDefinition); lethal.set_editor_property('buff_tag',tag('Combat.Buff.Burn')); lethal.set_editor_property('period',.05); lethal.set_editor_property('health_per_period',-10000)
        self.reset([s]); self.boss.get_editor_property('skill_runtime').add_buff(lethal,self.player,False); yield from self.wait(.15)
        self.check('buff.periodic_death_cleanup',not self.boss.is_alive() and self.boss.get_editor_property('skill_runtime').get_buff_stacks(lethal)==0)

        # Native data execution plays an actual montage without executing its legacy notify logic twice.
        montage=u.load_asset('/Game/Combat/Animations/Native/Kwang/AM_Attack1')
        s=self.skill(duration=montage.get_play_length()); s.set_editor_property('montage',montage)
        bullet=self.projectile(); s.set_editor_property('events',[self.event(E.PROJECTILE,at=.15,projectile=bullet)])
        self.reset([s]); hp=self.boss.get_health(); self.activate(s)
        self.check('montage.actual_play',self.player.get_editor_property('mesh').get_anim_instance().get_current_active_montage()==montage)
        yield from self.wait(montage.get_play_length()/max(.01,montage.get_editor_property('rate_scale'))+.5)
        self.check('montage.event_once',abs(hp-self.boss.get_health()-20)<.01,damage=hp-self.boss.get_health())
        self.check('montage.completion_cleanup',not self.player.is_busy())
        tail=self.new(u.CombatBuffDefinition); tail.set_editor_property('buff_tag',tag('Combat.Buff.Power')); tail.set_editor_property('duration',2)
        s.set_editor_property('events',[self.event(E.APPLY_BUFF,at=montage.get_play_length(),buff=tail)])
        self.reset([s]); self.activate(s)
        yield from self.wait(montage.get_play_length()/max(.01,montage.get_editor_property('rate_scale'))+.15)
        self.check('montage.final_frame_event',self.player.get_editor_property('skill_runtime').get_buff_stacks(tail)==1)

        a=self.skill(1,1); b=self.skill(2,1); wrong=self.skill(3,1)
        a.set_editor_property('next_skill_tag',wrong.get_editor_property('skill_tag'))
        r=u.CombatSkillDerivation(); r.set_editor_property('target_skill',b.get_editor_property('skill_tag')); r.set_editor_property('input_tag',tag('Combat.Input.Attack')); r.set_editor_property('window_end',1)
        a.set_editor_property('derivations',[r]); self.reset([a,b,wrong]); self.activate(a); self.player.attack_pressed(); self.player.attack_released()
        self.check('derive.legacy_next_does_not_override_graph',tag_name(self.player.get_active_skill_tag()).endswith('Sample2'))

        control=self.new(u.CombatBuffDefinition); control.set_editor_property('buff_tag',tag('Combat.Buff.Slow')); control.set_editor_property('interrupt_on_apply',True)
        s=self.skill(duration=1); s.set_editor_property('allowed_interrupts',[]); self.reset([s]); self.activate(s)
        rt=self.player.get_editor_property('skill_runtime'); rt.add_buff(control,self.boss,False)
        self.check('buff.control_immunity',self.player.is_busy() and rt.get_buff_stacks(control)==0)
        s.set_editor_property('allowed_interrupts',[u.CombatInterruptReason.CONTROL]); rt.add_buff(control,self.boss,False)
        self.check('buff.control_interrupt',not self.player.is_busy() and rt.get_buff_stacks(control)==1)

def start():
    for key in (KEY,'_combat_arena_regression','_combat_combined_sources','_combat_default_chain_only'):
        if getattr(getattr(builtins,key,None),'handle',None) is not None:
            raise RuntimeError('Another runner is active: '+key)
    runner=Runner(); setattr(builtins,KEY,runner)
    runner.handle=u.register_slate_post_tick_callback(runner.tick)
    return str(runner.path)

def status():
    runner=getattr(builtins,KEY,None)
    return dict(status=runner.report['status'],assertions=len(runner.report['assertions']),path=str(runner.path)) if runner else {'status':'not_started'}

def stop():
    runner=getattr(builtins,KEY,None)
    if runner and runner.handle is not None:
        runner.report['status']='stopped'; runner.cleanup()
    return status()
