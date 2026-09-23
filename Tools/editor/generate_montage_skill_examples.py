"""Create native Montage examples without changing the original Montage or V1 examples."""
import unreal as u

ROOT='/Game/Combat/SkillEditorExamples/Montage'
tools=u.AssetToolsHelpers.get_asset_tools()

def tag(name):
    value=u.GameplayTag(); value.import_text('(TagName="'+name+'")'); return value

def event(kind,time,**fields):
    value=u.CombatSkillEvent(); value.set_editor_property('type',kind); value.set_editor_property('time',time)
    for key,item in fields.items():value.set_editor_property(key,item)
    return value

skills=[]
for index,suffix in enumerate(('Strike','Followup')):
    path=ROOT+'/DA_'+suffix
    skill=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if skill:
        skills.append(skill);continue
    skill=tools.create_asset('DA_'+suffix,ROOT,u.CombatSkillDefinition,u.CombatSkillAssetFactory())
    montage=u.load_asset('/Game/Combat/Animations/Native/Kwang/AM_Attack'+str(index+1))
    length=montage.get_play_length()
    skill.set_editor_property('use_montage_notifies',False)
    skill.set_editor_property('montage',montage)
    skill.set_editor_property('duration',length)
    skill.set_editor_property('skill_tag',tag('Combat.Skill.Montage.'+suffix))
    skill.set_editor_property('cooldown',.1)
    if not index:
        skill.set_editor_property('input_tag',tag('Combat.Input.Attack'));skill.set_editor_property('priority',200)
    E=u.CombatSkillEventType
    skill.set_editor_property('events',[
        event(E.PROJECTILE,length*.2,projectile=u.load_asset('/Game/Combat/SkillEditorExamples/Projectile_Piercing'),label='发射剑气'),
        event(E.APPLY_BUFF,length*.1,buff=u.load_asset('/Game/Combat/SkillEditorExamples/Buff_Power'),skill_scoped=True,label='技能期间增伤'),
        event(E.HIT_WINDOW,length*.3,duration=length*.2,label='近战'),
        event(E.CANCEL_WINDOW,length*.7,duration=length*.25,label='取消窗口')])
    if not index:
        rule=u.CombatSkillDerivation();rule.set_editor_property('target_skill',tag('Combat.Skill.Montage.Followup'));rule.set_editor_property('input_tag',tag('Combat.Input.Attack'));rule.set_editor_property('window_start',length*.4);rule.set_editor_property('window_end',length*.85);skill.set_editor_property('derivations',[rule])
    converted=u.CombatSkillEditorLibrary.convert_to_montage_notifies(skill,ROOT+'/AM_'+suffix)
    if not converted:raise RuntimeError('Migration failed: '+path)
    u.EditorAssetLibrary.save_loaded_asset(converted)
    u.EditorAssetLibrary.save_loaded_asset(skill)
    skills.append(skill)

set_path=ROOT+'/DA_MontageSkills'
if u.EditorAssetLibrary.does_asset_exist(set_path):
    collection=u.load_asset(set_path)
else:
    collection=tools.create_asset('DA_MontageSkills',ROOT,u.CombatSkillSet,u.CombatSkillSetAssetFactory())
    collection.set_editor_property('skills',skills);u.EditorAssetLibrary.save_loaded_asset(collection)
errors=list(u.CombatSkillEditorLibrary.validate_skill_assets([collection]))
print({'collection':collection.get_path_name(),'errors':errors,'montages':[s.get_editor_property('montage').get_path_name() for s in skills]})
if errors:raise RuntimeError('Native Montage example validation failed')
