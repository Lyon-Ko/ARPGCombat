"""A new finisher behavior authored solely in BP, montage notifies and data."""
import unreal as u

ROOT='/Game/Combat'
def copy(source,destination):
    return u.load_asset(destination) or u.EditorAssetLibrary.duplicate_asset(source,destination)

montage=copy(u.load_asset(ROOT+'/Skills/DA_Attack4').get_editor_property('montage').get_path_name(),ROOT+'/Animations/Montages/AM_Example_CrescentBurst')
track='ExtensionEvents'
if not u.AnimationLibrary.is_valid_anim_notify_track_name(montage,track): u.AnimationLibrary.add_animation_notify_track(montage,track)
u.AnimationLibrary.remove_animation_notify_events_by_track(montage,track)
for at,event in [(.04,'AreaWarning'),(.49,'AreaRelease')]:
    notify=u.AnimationLibrary.add_animation_notify_event(montage,track,at,u.CombatAnimNotify_Event)
    tag=u.GameplayTag()
    assert tag.import_text('(TagName="Combat.Event.'+event+'")')
    notify.set_editor_property('event_tag',tag)
ability=copy(ROOT+'/Abilities/GA_Attack4',ROOT+'/Abilities/Examples/GA_CrescentBurst')
editor=u.BlueprintGraphEditor.get_graph_editor_by_name(ability,'Gameplay Ability Graph')
if not u.EditorAssetLibrary.get_metadata_tag(ability,'ExtensionComment'):
    editor.add_comment_node('扩展技能：弧月爆发。蒙太奇在 0.04 秒预警、0.49 秒闪光，0.18 秒后爆炸。仅 BP / 蒙太奇 / 数据。',u.Vector2D(0,-500),u.Vector2D(1500,180))
    u.EditorAssetLibrary.set_metadata_tag(ability,'ExtensionComment','1')
assert u.CombatEditorLibrary.compile_and_save(ability)
data=copy(ROOT+'/Skills/DA_Attack4',ROOT+'/Skills/Examples/DA_Example_CrescentBurst')
data.set_editor_property('montage',montage)
data.set_editor_property('ability_class',ability.generated_class())
new_tag=u.GameplayTag()
assert new_tag.import_text('(TagName="Combat.Skill.Example.CrescentBurst")')
data.set_editor_property('skill_tag',new_tag)
data.set_editor_property('damage',32)
data.set_editor_property('poise_damage',55)
data.set_editor_property('area_radius',260)
data.set_editor_property('cooldown',1.2)
for asset in (montage,ability,data): u.EditorAssetLibrary.save_loaded_asset(asset)
print('EXTENSION_CREATED',data.get_path_name(),'Install: append to player SkillDefinitions and change Attack3 NextSkillTag to Combat.Skill.Example.CrescentBurst. No C++ logic changes.')
