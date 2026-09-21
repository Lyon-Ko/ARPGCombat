"""Asynchronous real-PIE smoke matrix. Run, then poll `combat_probe_results`."""
import unreal as u
import time
import json
from pathlib import Path

combat_probe_results=[]
combat_probe_state={'phase':'wait_world','at':time.monotonic(),'index':0}
combat_probe_cases=['Attack1','Attack2','Attack3','Attack4','DashStrike','Air1','Air2','Plunge','Parry','Riposte','Dash',
                    'Boss.Combo1','Boss.Combo2','Boss.Combo3','Boss.AOE','Boss.DashSlash','Boss.LeapLeft','Boss.LeapRight','Boss.LeapBack']
def combat_probe_tag(name):
    value=u.GameplayTag()
    assert value.import_text('(TagName="'+name+'")')
    return value

def combat_probe_tick(delta):
    global combat_probe_handle
    s=combat_probe_state
    now=time.monotonic()
    try:
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            if now-s['at']>20: raise RuntimeError('PIE world unavailable')
            return
        if s['phase']=='wait_world':
            people=u.GameplayStatics.get_all_actors_of_class(world,u.CombatCharacter)
            if len(people)!=2:
                if now-s['at']>20: raise RuntimeError('Expected player and boss; found '+str(len(people)))
                return
            s['player']=next(p for p in people if not p.get_editor_property('is_boss'))
            s['boss']=next(p for p in people if p.get_editor_property('is_boss'))
            ai=s['boss'].get_controller()
            if ai:
                ai.get_editor_property('state_tree_component').stop_logic('Editor skill matrix')
            s['phase']='start'
        if s['phase']=='start':
            if s['index']>=len(combat_probe_cases):
                report='\n\n## Actual PIE skill matrix\n```json\n'+json.dumps(combat_probe_results,indent=2)+'\n```\n'
                with (Path(u.Paths.project_dir())/'Docs/EditorProgress.md').open('a',encoding='utf-8') as out: out.write(report)
                print('PIE_MATRIX_FINISHED',json.dumps(combat_probe_results))
                u.unregister_slate_post_tick_callback(combat_probe_handle)
                u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
                s['phase']='complete'
                return
            skill=combat_probe_cases[s['index']]
            attacker=s['boss'] if skill.startswith('Boss.') else s['player']
            target=s['player'] if skill.startswith('Boss.') else s['boss']
            for p in (attacker,target): p.reset_combat_state()
            ai=s['boss'].get_controller()
            if ai: ai.get_editor_property('state_tree_component').stop_logic('Editor skill matrix')
            air=skill in ('Air1','Air2','Plunge')
            attacker.set_actor_location(u.Vector(0,0,450 if skill=='Plunge' else 250 if air else 100),False,True)
            target.set_actor_location(u.Vector(140,0,100),False,True)
            attacker.set_actor_rotation(u.Rotator(0,0,0),True)
            target.set_actor_rotation(u.Rotator(pitch=0,yaw=180,roll=0),True)
            attacker.set_combat_target(target)
            target.set_combat_target(attacker)
            if air: attacker.get_editor_property('character_movement').set_movement_mode(u.MovementMode.MOVE_FALLING)
            s.update(phase='prepare',at=now,attacker=attacker,target=target,skill=skill)
        elif s['phase'] in ('prepare','air2_setup'):
            if now-s['at']<.08: return
            attacker=s['attacker']; target=s['target']; skill=s['skill']
            if skill=='Air2' and s['phase']=='prepare':
                assert attacker.request_skill_by_tag(combat_probe_tag('Combat.Skill.Air1')),'Air2 setup Air1 failed'
                s.update(phase='air2_setup',at=now)
                return
            if skill=='Air2' and now-s['at']<.34: return
            if skill=='DashStrike': attacker.request_skill_by_tag(combat_probe_tag('Combat.Skill.Dash'))
            if skill=='Riposte':
                attacker.request_skill_by_tag(combat_probe_tag('Combat.Skill.Parry'))
                incoming=u.CombatHit(attacker=target,damage=1.0,poise_damage=0.0,location=attacker.get_actor_location(),direction=u.Vector(-1,0,0),attack_instance=10000+s['index'])
                print('RIPOSTE_SETUP',attacker.receive_combat_hit(incoming))
            hp=target.get_health()
            activated=attacker.request_skill_by_tag(combat_probe_tag('Combat.Skill.'+skill))
            definition=attacker.get_active_skill_definition()
            s.update(phase='observe',at=now,attacker=attacker,target=target,hp=hp,skill=skill,activated=activated,
                     duration=definition.get_editor_property('duration') if definition else 1.0,seen_montage=False,start_location=attacker.get_actor_location())
        elif s['phase']=='observe':
            a=s['attacker']
            anim=a.get_editor_property('mesh').get_anim_instance()
            if anim and anim.get_current_active_montage(): s['seen_montage']=True
            if now-s['at']>=s['duration']+.3:
                location=a.get_actor_location()
                origin=s['start_location']
                distance=((location.x-origin.x)**2+(location.y-origin.y)**2+(location.z-origin.z)**2)**.5
                combat_probe_results.append({'skill':s['skill'],'activated':s['activated'],'montage_observed':s['seen_montage'],
                    'damage':round(s['hp']-s['target'].get_health(),2),'movement_cm':round(distance,1),'ended_cleanly':not a.is_busy(),
                    'anim_instance':anim.get_class().get_name() if anim else None})
                print('PIE_SKILL_RESULT',json.dumps(combat_probe_results[-1]))
                s['index']+=1; s['phase']='start'
    except Exception as error:
        print('PIE_MATRIX_ERROR',repr(error))
        s['phase']='failed'; s['error']=repr(error)
        u.unregister_slate_post_tick_callback(combat_probe_handle)

combat_probe_handle=u.register_slate_post_tick_callback(combat_probe_tick)
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
print('PIE_MATRIX_STARTED')
