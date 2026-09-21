import unreal as u
import json

ROOT = '/Game/Combat/Automation'
assets = u.AssetToolsHelpers.get_asset_tools()
def create(name, cls, factory):
    return u.load_asset(ROOT+'/'+name) or assets.create_asset(name, ROOT, cls, factory)

factory = u.BlueprintFactory()
factory.set_editor_property('parent_class', u.Actor)
bp = create('BP_GraphProbe', u.Blueprint, factory)
editor = u.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'HelloWorld')
if not editor:
    editor = u.BlueprintGraphEditor.create_and_edit_function_graph(bp, 'HelloWorld')
    node = editor.add_call_function_node('/Script/Engine.KismetSystemLibrary.PrintString')
    node.find_input_pin('InString').set_pin_value('COMBAT_NATIVE_GRAPH_EXECUTED')
    node.find_input_pin('bPrintToLog').set_pin_value('true')
    node.set_node_pos(u.IntPoint(320, 0))
    assert editor.find_graph_entry_pin().try_create_connection(node.find_execute_pin())
u.BlueprintEditorLibrary.compile_blueprint(bp)
assert not editor.list_nodes_with_errors()
u.EditorAssetLibrary.save_loaded_asset(bp)
actor = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(bp.generated_class(), u.Vector(0,0,-10000))
actor.call_method('HelloWorld')
u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(actor)

sequence = u.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle')
mf = u.AnimMontageFactory()
mf.set_editor_property('source_animation', sequence)
mf.set_editor_property('target_skeleton', sequence.get_editor_property('skeleton'))
montage = create('AM_NotifyProbe', u.AnimMontage, mf)
track = 'CombatProbe'
if not u.AnimationLibrary.is_valid_anim_notify_track_name(montage, track):
    u.AnimationLibrary.add_animation_notify_track(montage, track)
u.AnimationLibrary.remove_animation_notify_events_by_track(montage, track)
state = u.AnimationLibrary.add_animation_notify_state_event(montage, track, 0.1, 0.2, u.AnimNotifyState_TimedNiagaraEffect)
assert state
wf = u.WidgetBlueprintFactory()
wf.set_editor_property('parent_class', u.UserWidget)
widget = create('WBP_WidgetProbe', u.WidgetBlueprint, wf)
u.BlueprintEditorLibrary.compile_blueprint(widget)
fx = u.load_asset(ROOT+'/NS_TemplateProbe') or u.EditorAssetLibrary.duplicate_asset('/Niagara/DefaultAssets/Templates/Systems/DirectionalBurst', ROOT+'/NS_TemplateProbe')
for asset in [bp,montage,widget,fx]:
    assert asset
    assert u.EditorAssetLibrary.save_loaded_asset(asset, False)
packages = [a.get_outermost() for a in [bp,montage,widget,fx]]
print('RELOAD_RESULT', u.EditorLoadingAndSavingUtils.reload_packages(packages))
bp = u.load_asset(ROOT+'/BP_GraphProbe')
editor = u.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'HelloWorld')
assert len(editor.list_all_nodes()) >= 2 and not editor.list_nodes_with_errors()
actor = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(bp.generated_class(), u.Vector(0,0,-10000))
actor.call_method('HelloWorld')
u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(actor)
montage = u.load_asset(ROOT+'/AM_NotifyProbe')
events = u.AnimationLibrary.get_animation_notify_events(montage)
assert len(events) == 1
print('MILESTONE_PASS', json.dumps({'graph_nodes':len(editor.list_all_nodes()),'notify_count':len(events),'widget':str(u.load_asset(ROOT+'/WBP_WidgetProbe')),'niagara':str(u.load_asset(ROOT+'/NS_TemplateProbe'))}))
