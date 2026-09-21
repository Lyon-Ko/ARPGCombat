"""Repair the known legacy probe aliasing error, then reload and validate defaults."""
import datetime
import json
from pathlib import Path
import unreal as u

editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert not editor.is_in_play_in_editor(), 'Stop PIE first'
attack3 = u.load_asset('/Game/Combat/Skills/DA_Attack3')
attack4 = u.load_asset('/Game/Combat/Skills/DA_Attack4')
before = str(attack3.next_skill_tag.get_editor_property('tag_name'))
assert before in ('Combat.Skill.Example.CrescentBurst', 'Combat.Skill.Attack4'), before
attack3.set_editor_property('next_skill_tag', attack4.skill_tag)
assert u.EditorAssetLibrary.save_loaded_asset(attack3, False)
ok, message = u.EditorLoadingAndSavingUtils.reload_packages(
    [attack3.get_outermost()], u.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
assert ok and not str(message), str(message)
attack3 = u.load_asset('/Game/Combat/Skills/DA_Attack3')
after = str(attack3.next_skill_tag.get_editor_property('tag_name'))
assert after == 'Combat.Skill.Attack4', after
definitions = {}
for character in ('Player', 'Boss'):
    bp = u.load_asset('/Game/Combat/Characters/BP_Combat'+character)
    values = list(u.get_default_object(bp.generated_class()).skill_definitions)
    tags = {str(d.skill_tag.get_editor_property('tag_name')) for d in values}
    rows = []
    for definition in values:
        next_tag = str(definition.next_skill_tag.get_editor_property('tag_name'))
        assert next_tag in ('None', '') or next_tag in tags, (character, definition.get_path_name(), next_tag)
        rows.append({'asset': definition.get_path_name(), 'next_tag': next_tag})
    definitions[character] = rows
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report = {'status': 'passed', 'utc': stamp, 'before': before, 'after_reloaded': after,
          'cause': 'Legacy probe retained a live GameplayTag property wrapper instead of an independent value.',
          'scope': 'Repair and disk reload of defaults; actual input-chain test remains separate.', 'definitions': definitions}
output = Path(u.Paths.project_saved_dir()) / 'Acceptance' / ('DefaultChainRepair_'+stamp+'.json')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('DEFAULT_CHAIN_REPAIRED', str(output))
