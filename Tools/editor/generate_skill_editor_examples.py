"""Create isolated skill-editor examples and test arena; never overwrite existing packages."""
import unreal as u

ROOT='/Game/Combat/SkillEditorExamples'
skill_set=u.CombatSkillEditorLibrary.create_examples()
player_path=ROOT+'/BP_SkillEditorPlayer'
if not u.EditorAssetLibrary.does_asset_exist(player_path):
    player=u.EditorAssetLibrary.duplicate_asset('/Game/Combat/Characters/BP_CombatPlayer',player_path)
    if not player or not u.CombatSkillEditorLibrary.equip_skill_set(skill_set,player):
        raise RuntimeError('Could not create an equipped example player')
    if not u.CombatEditorLibrary.compile_and_save(player):
        raise RuntimeError('Could not compile equipped example player')
map_path=ROOT+'/L_SkillEditorTest'
if not u.EditorAssetLibrary.does_asset_exist(map_path):
    result=u.EditorAssetLibrary.duplicate_asset('/Game/Combat/Maps/L_CombatArena',map_path)
    if not result:
        raise RuntimeError('Could not create isolated skill-editor arena')
    u.EditorAssetLibrary.save_loaded_asset(result)
assets=[u.load_asset(p) for p in u.EditorAssetLibrary.list_assets(ROOT,recursive=True) if not p.endswith('L_SkillEditorTest.L_SkillEditorTest')]
errors=list(u.CombatSkillEditorLibrary.validate_skill_assets([a for a in assets if a]))
print({'skill_set':skill_set.get_path_name(),'test_map':map_path,'errors':errors})
if errors:
    raise RuntimeError('Skill editor example validation failed')
