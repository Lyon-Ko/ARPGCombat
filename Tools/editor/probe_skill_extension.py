"""Normal-input four-hit chain ending in a separately tagged BP/data skill.
Temporarily append definition and redirect Attack3.NextSkillTag; restore both.
"""
import unreal as u
import time,json
from pathlib import Path
extension_bp=u.load_asset('/Game/Combat/Characters/BP_CombatPlayer')
extension_cdo=u.get_default_object(extension_bp.generated_class())
extension_original=list(extension_cdo.get_editor_property('skill_definitions'))
extension_data=u.load_asset('/Game/Combat/Skills/Examples/DA_Example_CrescentBurst')
extension_attack3=u.load_asset('/Game/Combat/Skills/DA_Attack3')
extension_next=extension_attack3.get_editor_property('next_skill_tag')
extension_attack3.set_editor_property('next_skill_tag',extension_data.skill_tag)
extension_cdo.set_editor_property('skill_definitions',extension_original+[extension_data])
assert u.CombatEditorLibrary.compile_and_save(extension_bp)
extension_cdo=u.get_default_object(extension_bp.generated_class())
extension_state={'phase':'wait','at':time.monotonic(),'queued':set(),'seen':[],'timeline':[],'release_at':0}
def restore_extension():
    extension_cdo.set_editor_property('skill_definitions',extension_original)
    extension_attack3.set_editor_property('next_skill_tag',extension_next)
    u.EditorAssetLibrary.save_loaded_asset(extension_bp,False)
    u.EditorAssetLibrary.save_loaded_asset(extension_attack3,False)
def extension_tick(delta):
    s=extension_state;now=time.monotonic()
    try:
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            if now-s['at']>20:raise RuntimeError('PIE startup timeout')
            return
        if s['phase']=='wait':
            people=u.GameplayStatics.get_all_actors_of_class(world,u.CombatCharacter)
            if len(people)!=2:return
            p=next(p for p in people if not p.is_boss);b=next(p for p in people if p.is_boss)
            b.get_controller().get_editor_property('state_tree_component').stop_logic('Extension proof')
            p.set_actor_location(u.Vector(0,0,100),False,True);b.set_actor_location(u.Vector(220,0,110),False,True)
            p.set_actor_rotation(u.Rotator(yaw=0),True);b.set_actor_rotation(u.Rotator(yaw=180),True);p.set_combat_target(b)
            s.update(phase='start',at=now,p=p,b=b,hp=b.get_health())
            print('EXTENSION_SETUP_TAGS',[str(d.skill_tag.get_editor_property('tag_name')) for d in p.skill_definitions],str(extension_attack3.next_skill_tag))
        elif s['phase']=='start' and now-s['at']>.2:
            u.CombatEditorLibrary.inject_player_key(s['p'].get_controller(),'LeftMouseButton',True)
            s.update(phase='observe',at=now,release_at=now+.04)
        elif s['phase']=='observe':
            p=s['p'];b=s['b'];pc=p.get_controller()
            if s['release_at'] and now>=s['release_at']:
                u.CombatEditorLibrary.inject_player_key(pc,'LeftMouseButton',False);s['release_at']=0
            skill=str(p.get_active_skill_tag().get_editor_property('tag_name'))
            if p.is_busy() and skill not in s['seen']:s['seen'].append(skill)
            if skill in ('Combat.Skill.Attack1','Combat.Skill.Attack2','Combat.Skill.Attack3') and skill not in s['queued'] and p.get_skill_elapsed_time()>.23:
                print('EXTENSION_CHAIN_INPUT',skill,p.get_skill_elapsed_time(),str(p.get_active_skill_definition().next_skill_tag))
                u.CombatEditorLibrary.inject_player_key(pc,'LeftMouseButton',True);s['release_at']=now+.04;s['queued'].add(skill)
            s['timeline'].append({'elapsed':p.get_skill_elapsed_time(),'tag':skill,'health':b.get_health()})
            if ('Combat.Skill.Example.CrescentBurst' in s['seen'] and not p.is_busy()) or now-s['at']>7:
                u.CombatEditorLibrary.inject_player_key(pc,'LeftMouseButton',False)
                result={'ability':extension_data.ability_class.get_path_name(),'data':extension_data.get_path_name(),'skill_tag':str(extension_data.skill_tag.get_editor_property('tag_name')),'seen_chain':s['seen'],'damage':s['hp']-b.get_health(),'ended_cleanly':not p.is_busy(),'timeline':s['timeline']}
                restore_extension()
                result['defaults_restored']=extension_attack3.next_skill_tag==extension_next and list(extension_cdo.skill_definitions)==extension_original
                out=Path(u.Paths.project_saved_dir())/'Acceptance/SkillExtensionNewTagPIE.json';out.write_text(json.dumps(result,indent=2),encoding='utf-8')
                print('EXTENSION_PIE_RESULT',result['seen_chain'],result['damage'],result['ended_cleanly'],result['defaults_restored'])
                s['phase']='complete';u.unregister_slate_post_tick_callback(extension_handle);u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    except Exception as error:
        restore_extension();s.update(phase='failed',error=str(error));print('EXTENSION_FAILED',str(error));u.unregister_slate_post_tick_callback(extension_handle)
extension_handle=u.register_slate_post_tick_callback(extension_tick)
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
print('EXTENSION_STARTED')
