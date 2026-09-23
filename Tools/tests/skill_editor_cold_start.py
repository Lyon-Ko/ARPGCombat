"""Read saved assets after a real editor restart and exercise the actual toolkit lifecycle."""
import datetime
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report={'status':'running','checks':[], 'scope':'Saved asset reload and toolkit open/close in a fresh editor; not visual screenshot approval'}
path=ROOT/'Saved/Acceptance'/('SkillEditorColdStart_'+stamp+'.json')

def check(name,value,**detail):
    report['checks'].append(dict(name=name,passed=bool(value),**detail))

check('no_pie_before_check',u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is None)
base='/Game/Combat/SkillEditorExamples/'
asset_set=u.load_asset(base+'DA_ExampleSkillSet')
check('saved_set_loaded',asset_set is not None)
skills=list(asset_set.get_editor_property('skills'))
check('six_saved_skills',len(skills)==6)
check('all_data_driven',all(s.get_editor_property('data_driven') for s in skills))
check('valid_reloaded_assets',not u.CombatSkillEditorLibrary.validate_skill_assets([asset_set]))
check('saved_missile_event_type',skills[2].get_editor_property('events')[0].get_editor_property('type')==u.CombatSkillEventType.PROJECTILE)
missile=skills[2].get_editor_property('events')[0].get_editor_property('projectile')
check('saved_guidance_mode',missile.get_editor_property('motion')==u.CombatProjectileMotion.GUIDED)
bp=u.load_asset(base+'BP_SkillEditorPlayer')
check('equipped_example_blueprint',u.get_default_object(bp.generated_class()).get_editor_property('designer_skill_set')==asset_set)
original=u.load_asset('/Game/Combat/Characters/BP_CombatPlayer')
check('original_blueprint_unmodified',u.get_default_object(original.generated_class()).get_editor_property('designer_skill_set') is None)
legacy=u.load_asset('/Game/Combat/Skills/DA_Attack1')
check('legacy_execution_mode',not legacy.get_editor_property('data_driven'))
check('legacy_next_preserved',str(legacy.get_editor_property('next_skill_tag').get_editor_property('tag_name'))=='Combat.Skill.Attack2')
subsystem=u.get_editor_subsystem(u.AssetEditorSubsystem)
for asset in (asset_set,missile,u.load_asset(base+'Buff_Burn'),skills[0]):
    u.CombatSkillEditorLibrary.open_skill_editor(asset)
    closed=subsystem.close_all_editors_for_asset(asset)
    check('toolkit_open_close.'+asset.get_name(),closed>0,closed_count=closed)
report['binaries']={name:hashlib.sha256((ROOT/'Binaries/Win64'/name).read_bytes()).hexdigest() for name in ('UnrealEditor-Combat.dll','UnrealEditor-CombatEditor.dll')}
report['status']='passed' if all(c['passed'] for c in report['checks']) else 'failed'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print({'report':str(path),'status':report['status'],'checks':len(report['checks'])})
# Leave the actual workbench open for the user. No data is changed by inspection.
u.CombatSkillEditorLibrary.open_skill_editor(asset_set)
