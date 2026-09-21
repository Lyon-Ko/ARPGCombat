"""Real PIE socket trajectories; no simulated hit assertions."""
import unreal as u
import json,time
from pathlib import Path
native_trace_state={'phase':'wait','at':time.monotonic(),'index':0,'results':[]}
native_trace_cases=[(s,d) for s in ('Attack1','Attack2','Attack3','Attack4','Boss.Combo1') for d in (140,220,300)]
def native_trace_tick(delta):
    s=native_trace_state; now=time.monotonic()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:return
    if s['phase']=='wait':
        people=u.GameplayStatics.get_all_actors_of_class(world,u.CombatCharacter)
        if len(people)!=2:return
        s['player']=next(p for p in people if not p.is_boss);s['boss']=next(p for p in people if p.is_boss);s['phase']='next'
    if s['phase']=='next':
        if s['index']==len(native_trace_cases):
            out=Path(u.Paths.project_saved_dir())/'Acceptance/NativeTracePIE.json';out.write_text(json.dumps(s['results'],indent=2),encoding='utf-8')
            print('TRACE_COMPLETE',[(r['skill'],r['distance'],r['damage']) for r in s['results']]);s['phase']='done';u.unregister_slate_post_tick_callback(native_trace_handle);return
        skill,distance=native_trace_cases[s['index']]
        a=s['boss'] if skill.startswith('Boss') else s['player'];b=s['player'] if skill.startswith('Boss') else s['boss']
        for p in (a,b):p.reset_combat_state()
        s['boss'].get_controller().get_editor_property('state_tree_component').stop_logic('Trace diagnostics')
        a.set_actor_location(u.Vector(0,0,100),False,True);b.set_actor_location(u.Vector(distance,0,100),False,True)
        a.set_actor_rotation(u.Rotator(0,0,0),True);b.set_actor_rotation(u.Rotator(pitch=0,yaw=180,roll=0),True);a.set_combat_target(b)
        s.update(phase='prepare',at=now,a=a,b=b,skill=skill,distance=distance,samples=[])
    elif s['phase']=='prepare' and now-s['at']>.15:
        tag=u.GameplayTag();tag.import_text('(TagName="Combat.Skill.'+s['skill']+'")')
        assert s['a'].request_skill_by_tag(tag)
        s.update(phase='record',at=now,hp=s['b'].get_health())
    elif s['phase']=='record':
        mesh=s['a'].get_editor_property('mesh');anim=mesh.get_anim_instance();m=anim.get_current_active_montage()
        s['samples'].append({'elapsed':s['a'].get_skill_elapsed_time(),'montage':anim.montage_get_position(m) if m else -1,'base':list(mesh.get_socket_location('BladeBase').to_tuple()),'tip':list(mesh.get_socket_location('BladeTip').to_tuple()),'target':list(s['b'].get_actor_location().to_tuple()),'health':s['b'].get_health()})
        if now-s['at']>1.1:
            s['results'].append({'skill':s['skill'],'distance':s['distance'],'damage':s['hp']-s['b'].get_health(),'samples':s['samples']});s['index']+=1;s['phase']='next'
native_trace_handle=u.register_slate_post_tick_callback(native_trace_tick)
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
print('TRACE_STARTED')
