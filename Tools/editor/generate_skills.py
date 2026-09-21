"""Editable GAS graphs: montage task -> explicit tag branches -> native blocks."""
import unreal as u
from pathlib import Path
import json

ROOT='/Game/Combat'
assets=u.AssetToolsHelpers.get_asset_tools()
assert hasattr(u,'CombatGameplayAbility'), 'Runtime build/reload required'

SKILLS={
 'Attack1':('A_Player_Sword_01',18,18,70,'Attack2'),
 'Attack2':('A_Player_Sword_02',22,20,80,'Attack3'),
 'Attack3':('A_Player_Sword_03',26,24,100,'Attack4'),
 'Attack4':('A_Player_Sword_04',38,40,110,''),
 'DashStrike':('A_Player_DashStrike',32,30,260,''),
 'Air1':('A_Player_Air_01',22,18,70,'Air2'),
 'Air2':('A_Player_Air_02',30,24,80,''),
 'Plunge':('A_Player_Plunge',50,60,500,''),
 'Parry':('A_Player_Parry',0,0,0,''),
 'Riposte':('A_Player_Riposte',85,100,120,''),
 'Boss.Combo1':('A_Boss_Combo_01',24,30,170,'Boss.Combo2'),
 'Boss.Combo2':('A_Boss_Combo_02',27,32,170,'Boss.Combo3'),
 'Boss.Combo3':('A_Boss_Combo_03',38,45,210,''),
 'Boss.AOE':('A_Boss_ChargeAOE',65,65,0,''),
 'Boss.DashSlash':('A_Boss_FrontDashSlash',40,40,700,''),
 'Boss.LeapLeft':('A_Boss_JumpWave_L',28,30,450,''),
 'Boss.LeapRight':('A_Boss_JumpWave_R',28,30,450,''),
 'Boss.LeapBack':('A_Boss_JumpWave_Back',28,30,500,''),
 'Dash':('MM_Dash',0,0,250,''),
}
BLOCKS=[('HitOpen','OpenHitWindow'),('HitClose','CloseHitWindow'),('Move','StartSkillMovement'),
        ('Projectile','EmitSkillProjectile'),('AreaWarning','ShowAreaWarning'),('AreaRelease','DetonateArea'),
        ('ComboOpen','OpenComboWindow'),('Cancelable','SetCancelable'),('Finish','FinishSkill')]

def tag(text):
    value=u.GameplayTag()
    assert value.import_text('(TagName="'+text+'")')
    assert str(value.get_editor_property('tag_name'))==text
    return value

def load_or_create(path, cls, factory):
    return u.load_asset(path) or assets.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],cls,factory)

def link(a,b):
    assert a.is_valid() and b.is_valid(), (str(a),str(b))
    assert a.try_create_connection(b), (a.get_pin_name(),b.get_pin_name())

def call(ed,name,x,y):
    node=ed.add_call_function_node(name)
    assert node,name
    node.set_node_pos(u.IntPoint(x,y))
    return node

def available_node(ed,needle,x,y):
    names=ed.list_available_nodes([])
    candidates=[name for name in names if needle.lower() in name.replace(' ','').lower()]
    if needle=='ActivateAbility':
        candidates=[name for name in candidates if name.endswith('ActivateAbility') and 'TryActivate' not in name and 'Wait' not in name]
    assert candidates,(needle,[name for name in names if 'Montage' in name or 'Activate' in name])
    node=ed.create_node_from_name(candidates[0],u.Vector2D(x,y),[])
    assert node,(needle,candidates)
    return node

def ability(skill):
    path=ROOT+'/Abilities/GA_'+skill.replace('.','_')
    factory=u.GameplayAbilitiesBlueprintFactory(); factory.set_editor_property('parent_class',u.CombatGameplayAbility)
    bp=load_or_create(path,u.GameplayAbilityBlueprint,factory)
    if u.EditorAssetLibrary.get_metadata_tag(bp,'CombatGraphVersion')=='4':
        assert u.CombatEditorLibrary.compile_and_save(bp)
        return bp
    ed=u.BlueprintGraphEditor.get_graph_editor_by_name(bp,'Gameplay Ability Graph')
    ed.remove_nodes(ed.list_all_nodes())
    for comment in ed.list_comment_nodes(): ed.remove_comment_node(comment)
    event=available_node(ed,'ActivateAbility',0,0)
    assert event,'K2_ActivateAbility override'
    event.set_node_pos(u.IntPoint(0,0))
    task=available_node(ed,'CombatPlayMontageAndEvents',450,0)
    print('TASK_NODE',skill,task.get_class().get_name(),[(str(p.get_pin_name()),str(p.get_pin_direction())) for p in task.list_all_pins()])
    link(event.find_output_pin('then'),task.find_execute_pin())
    definition=call(ed,'/Script/Combat.CombatGameplayAbility.GetSkillDefinition',0,270)
    montage=ed.add_get_member_variable_node('Montage','/Script/Combat.CombatSkillDefinition')
    montage.set_node_pos(u.IntPoint(230,270))
    link(definition.find_output_pin('ReturnValue'),montage.find_input_pin('self'))
    link(montage.find_output_pin('Montage'),task.find_input_pin('Montage'))
    character=call(ed,'/Script/Combat.CombatGameplayAbility.GetCombatCharacter',600,440)
    complete=call(ed,'/Script/Combat.CombatGameplayAbility.CompleteSkill',850,-140)
    link(task.find_output_pin('OnCompleted'),complete.find_execute_pin())
    interrupted=call(ed,'/Script/Combat.CombatGameplayAbility.CompleteSkill',850,70)
    assert interrupted.find_input_pin('bInterrupted').set_pin_value('true')
    link(task.find_output_pin('OnInterrupted'),interrupted.find_execute_pin())
    previous=task.find_output_pin('OnEvent')
    for index,(event_tag,method) in enumerate(BLOCKS):
        x=1050+index*440
        comparison=call(ed,'/Script/GameplayTags.BlueprintGameplayTagLibrary.EqualEqual_GameplayTag',x,450)
        link(task.find_output_pin('EventTag'),comparison.find_input_pin('A'))
        assert comparison.find_input_pin('B').set_pin_value('(TagName="Combat.Event.'+event_tag+'")')
        branch=ed.add_branch_node(); branch.set_node_pos(u.IntPoint(x,260))
        link(previous,branch.find_execute_pin())
        link(comparison.find_output_pin('ReturnValue'),branch.find_input_pin('Condition'))
        block=call(ed,'/Script/Combat.CombatCharacter.'+method,x,680)
        link(branch.find_output_pin('then'),block.find_execute_pin())
        link(character.find_output_pin('ReturnValue'),block.find_input_pin('self'))
        if method=='StartSkillMovement':
            if skill=='Plunge': block.find_input_pin('Direction').set_pin_value('0,0,-1')
            # Runtime handles target-relative direction for boss leap skills.
        previous=branch.find_output_pin('else')
        ed.add_comment_to_nodes('Combat.Event.'+event_tag+' → '+method,[comparison,branch,block],30)
    ed.add_comment_to_nodes('启动：数据资产决定蒙太奇；事件由实际动画通知发出',[event,task,definition,montage],40)
    ed.add_comment_to_nodes('正常结束 / 中断：清理技能、碰撞窗口及移动',[complete,interrupted],35)
    assert u.CombatEditorLibrary.compile_and_save(bp),path
    assert not ed.list_nodes_with_errors(),path
    u.EditorAssetLibrary.set_metadata_tag(bp,'CombatGraphVersion','4')
    u.EditorAssetLibrary.save_loaded_asset(bp)
    print('ABILITY_COMPILED',path,len(ed.list_all_nodes()))
    return bp

def data(skill,config,bp):
    clip,damage,poise,movement,next_skill=config
    factory=u.DataAssetFactory(); factory.set_editor_property('data_asset_class',u.CombatSkillDefinition)
    asset=load_or_create(ROOT+'/Skills/DA_'+skill.replace('.','_'),u.CombatSkillDefinition,factory)
    montage=u.load_asset(ROOT+'/Animations/Montages/AM_'+skill.replace('.','_'))
    assert montage,skill
    for key,value in {'skill_tag':tag('Combat.Skill.'+skill),'ability_class':bp.generated_class(),'montage':montage,
                      'damage':damage,'poise_damage':poise,'movement_distance':movement,'movement_duration':.23 if skill=='Dash' else .18,
                      'duration':montage.get_editor_property('sequence_length')/montage.get_editor_property('rate_scale'),'cooldown':.35 if skill in ('Dash','Parry') else .1,
                      'air_only':skill in ('Air1','Air2','Plunge'),'can_interrupt':skill in ('Dash','Parry','DashStrike','Riposte','Plunge'),
                      'trace_reach':190 if not skill.startswith('Boss') else 235,
                      'cue_color':u.LinearColor(.12,.8,1,1) if not skill.startswith('Boss') else u.LinearColor(1,.16,.045,1)}.items():
        asset.set_editor_property(key,value)
    asset.set_editor_property('next_skill_tag',tag('Combat.Skill.'+next_skill) if next_skill else u.GameplayTag())
    # Only primary inputs are mapped; chain successors are selected through NextSkillTag.
    input_name={'Attack1':'Attack','Air1':'Attack','DashStrike':'Attack','Riposte':'Attack','Dash':'Dash','Parry':'Parry'}.get(skill)
    asset.set_editor_property('input_tag',tag('Combat.Input.'+input_name) if input_name else u.GameplayTag())
    asset.set_editor_property('priority',{'Riposte':100,'DashStrike':60,'Air1':40}.get(skill,0))
    fields={
        'hit_effect':u.load_asset(ROOT+'/VFX/NS_HitSparks'),'trail_effect':u.load_asset(ROOT+'/VFX/'+('NS_BossBladeTrail' if skill.startswith('Boss.') else 'NS_BladeTrail')),
        'hit_sound':u.load_asset(ROOT+'/Audio/SW_MetalClash_01'),'parry_sound':u.load_asset(ROOT+'/Audio/SW_Parry'),
        'cast_sound':u.load_asset(ROOT+'/Audio/'+('SW_Dash' if skill=='Dash' else 'SW_SwordSwing_01')),
        'cast_effect':u.load_asset(ROOT+'/VFX/NS_Projectile') if 'Leap' in skill else None,
        'area_mesh':u.load_asset('/Engine/BasicShapes/Cylinder'),'area_material':u.load_asset(ROOT+'/Materials/M_AreaWarning'),
        'air_attack_index':1 if skill=='Air1' else 2 if skill=='Air2' else 0,
        'movement_direction_local':u.Vector(0,-1,0) if skill=='Boss.LeapLeft' else u.Vector(0,1,0) if skill=='Boss.LeapRight' else u.Vector(-1,0,0) if skill=='Boss.LeapBack' else u.Vector(0,0,-1) if skill=='Plunge' else u.Vector(1,0,0),
        'launch_velocity_z':480 if 'Leap' in skill else 0,
        'max_ai_range':350 if 'Combo' in skill else 900 if skill=='Boss.DashSlash' else 650,
        'min_ai_range':270 if 'Leap' in skill else 0,
        'selection_weight':0 if skill in ('Boss.Combo2','Boss.Combo3') else 1,
        'ground_only':skill.startswith('Attack') or skill.startswith('Boss.'),
        'face_target':skill not in ('Dash','Parry'),
        'play_cast_sound_at_activation':skill=='Dash',
        'area_release_effect':u.load_asset(ROOT+'/VFX/NS_AOEFlash'),
    }
    for key,value in fields.items(): asset.set_editor_property(key,value)
    sound_index=int(skill[-1]) if skill.startswith('Attack') else 1
    asset.set_editor_property('cast_sound',u.load_asset(ROOT+'/Audio/'+('SW_Dash' if skill=='Dash' else 'SW_Burst' if skill=='Boss.AOE' else 'SW_SwordSwing_%02d'%sound_index)))
    asset.set_editor_property('hit_sound',u.load_asset(ROOT+'/Audio/SW_MetalClash_%02d'%sound_index))
    required={'Air1':'Combat.State.Air','DashStrike':'Combat.State.Dashing','Riposte':'Combat.State.RiposteReady'}.get(skill)
    if required:
        container=u.GameplayTagLibrary.make_gameplay_tag_container_from_tag(tag(required))
        asset.set_editor_property('activation_query',u.GameplayTagLibrary.make_gameplay_tag_query_match_all_tags(container))
    elif skill.startswith('Attack'):
        container=u.GameplayTagLibrary.make_gameplay_tag_container_from_tag(tag('Combat.State.Air'))
        asset.set_editor_property('activation_query',u.GameplayTagLibrary.make_gameplay_tag_query_match_no_tags(container))
    else:
        asset.set_editor_property('activation_query',u.GameplayTagQuery())
    u.EditorAssetLibrary.save_loaded_asset(asset)
    return asset

for skill,config in SKILLS.items():
    bp=ability(skill)
    data(skill,config,bp)
print('SKILLS_PASS',len(SKILLS))
