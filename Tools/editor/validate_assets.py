"""Compile/save/reload checks, with explicit data/graph/link assertions."""
import unreal as u
import json

paths=u.EditorAssetLibrary.list_assets('/Game/Combat',True)
blueprints=[]
montages=[]
skill_montages={u.load_asset(p).get_editor_property('montage').get_path_name() for p in u.EditorAssetLibrary.list_assets('/Game/Combat/Skills',True) if isinstance(u.load_asset(p),u.CombatSkillDefinition)}
for path in paths:
    asset=u.load_asset(path)
    if isinstance(asset,u.Blueprint):
        assert u.CombatEditorLibrary.compile_and_save(asset),path
        blueprints.append(path)
    if isinstance(asset,u.AnimMontage) and ('/Montages/' in path or asset.get_path_name() in skill_montages):
        assert asset.get_editor_property('sequence_length')>0,path
        events=u.AnimationLibrary.get_animation_notify_events(asset)
        assert events,path+' no notify metadata'
        montages.append(path)
u.EditorAssetLibrary.save_directory('/Game/Combat',True,True)
# Reload only assets; map stays loaded and references are remapped by the editor.
packages=[u.load_asset(p).get_outermost() for p in blueprints+montages]
result=u.EditorLoadingAndSavingUtils.reload_packages(packages)
assert result[0],result
for path in blueprints:
    bp=u.load_asset(path)
    assert bp.generated_class(),path
    if '/Abilities/' in path:
        ed=u.BlueprintGraphEditor.get_graph_editor_by_name(bp,'Gameplay Ability Graph')
        assert not ed.list_nodes_with_errors(),path
        nodes=ed.list_all_nodes()
        assert len(nodes)>=30,(path,len(nodes))
        tasks=[n for n in nodes if n.get_class().get_name()=='K2Node_LatentAbilityCall']
        assert tasks,path+' no async montage task'
        assert any(p.list_connected_pins() for p in tasks[0].list_output_pins() if str(p.get_pin_name())=='OnEvent'),path
for path in montages:
    assert u.AnimationLibrary.get_animation_notify_events(u.load_asset(path)),path
print('VALIDATION_PASS',json.dumps({'blueprints_compiled_reloaded':len(blueprints),'montages_with_metadata_reloaded':len(montages),'assets_total':len(paths)}))
