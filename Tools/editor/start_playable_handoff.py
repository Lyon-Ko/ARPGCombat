"""Warm a real 1080p high PIE, observe StateTree, then pause safely for reviewer."""
import unreal as u
import time,json
from pathlib import Path
handoff_state={'phase':'wait','at':time.monotonic()}
def handoff_tick(delta):
    s=handoff_state;now=time.monotonic()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:return
    if s['phase']=='wait':
        people=u.GameplayStatics.get_all_actors_of_class(world,u.CombatCharacter)
        if len(people)!=2:return
        s['p']=next(p for p in people if not p.is_boss);s['b']=next(p for p in people if p.is_boss)
        pc=s['p'].get_controller();pc.set_control_rotation(u.Rotator(pitch=-12,yaw=0))
        for cmd in ['sg.ViewDistanceQuality 3','sg.AntiAliasingQuality 3','sg.ShadowQuality 3','sg.GlobalIlluminationQuality 3','sg.ReflectionQuality 3','sg.PostProcessQuality 3','sg.TextureQuality 3','sg.EffectsQuality 3','sg.FoliageQuality 3','sg.ShadingQuality 3','r.ScreenPercentage 100']:
            u.SystemLibrary.execute_console_command(world,cmd)
        s['p'].set_actor_location(u.Vector(-250,0,96),False,True);s['b'].set_actor_location(u.Vector(250,0,108),False,True)
        s.update(phase='observe',at=now,frames=[],health=s['p'].get_health())
    elif s['phase']=='observe':
        s['frames'].append(delta)
        if now-s['at']>8:
            p=s['p'];b=s['b'];ai=b.get_controller();pc=p.get_controller()
            result={'viewport':list(pc.get_viewport_size()),'ai_actions_executed':ai.get_editor_property('actions_executed'),'ai_state_tree':ai.get_editor_property('combat_state_tree').get_path_name(),'player_health_after_ai':p.get_health(),'player_anim_class':p.mesh.get_anim_instance().get_class().get_name(),'boss_anim_class':b.mesh.get_anim_instance().get_class().get_name(),'frame_samples':s['frames'],'note':'Warmup/slate deltas only, not formal GPU/performance acceptance. Reset and paused for root reviewer.'}
            for actor in (p,b):actor.reset_combat_state()
            pc.set_control_rotation(u.Rotator(pitch=-12,yaw=0));u.GameplayStatics.set_game_paused(world,True)
            out=Path(u.Paths.project_saved_dir())/'Acceptance/PlayableHandoff.json';out.write_text(json.dumps(result,indent=2),encoding='utf-8')
            print('PLAYABLE_HANDOFF',result['viewport'],result['ai_actions_executed'],result['player_health_after_ai'])
            s.update(phase='paused_ready',report=result);u.unregister_slate_post_tick_callback(handoff_handle)
handoff_handle=u.register_slate_post_tick_callback(handoff_tick)
assert u.CombatEditorLibrary.start_pie_window(1920,1080)
print('1080P_PIE_START_REQUESTED')
