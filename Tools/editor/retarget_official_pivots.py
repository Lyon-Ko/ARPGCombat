"""Create an offline IK retargeter and export selected official animations.

Call retarget(source_mesh_path, animation_paths) after migrating their source
dependencies into the project. Only /Game/Combat output assets are authored.
"""
import unreal as u

ROOT = '/Game/Combat/Animations/Retarget'


def retarget(source_mesh_path, animation_paths):
    tools = u.AssetToolsHelpers.get_asset_tools()
    source_mesh = u.load_asset(source_mesh_path)
    target_mesh = u.load_asset('/Game/Combat/Characters/SK_CombatKwang')
    assert source_mesh and target_mesh
    source_rig = u.load_asset(ROOT + '/IK_OfficialPivotSource')
    if not source_rig:
        source_rig = tools.create_asset('IK_OfficialPivotSource', ROOT, u.IKRigDefinition,
                                       u.IKRigDefinitionFactory())
        controller = u.IKRigController.get_controller(source_rig)
        assert controller.set_skeletal_mesh(source_mesh)
        assert controller.apply_auto_generated_retarget_definition()
        assert controller.apply_auto_fbik()
        assert u.EditorAssetLibrary.save_loaded_asset(source_rig)
    assert u.IKRigController.get_controller(source_rig).get_skeletal_mesh() == source_mesh
    target_rig = u.load_asset(ROOT + '/IK_CombatKwang')
    assert target_rig
    target_controller = u.IKRigController.get_controller(target_rig)
    if target_controller.get_num_solvers() == 0:
        assert target_controller.apply_auto_fbik()
        assert u.EditorAssetLibrary.save_loaded_asset(target_rig)
    retargeter = u.load_asset(ROOT + '/RTG_OfficialPivot_Kwang')
    if not retargeter:
        retargeter = tools.create_asset('RTG_OfficialPivot_Kwang', ROOT, u.IKRetargeter,
                                       u.IKRetargetFactory())
        controller = u.IKRetargeterController.get_controller(retargeter)
        controller.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, source_rig)
        controller.set_ik_rig(u.RetargetSourceOrTarget.TARGET, target_rig)
        controller.add_default_ops()
        controller.auto_map_chains(u.AutoMapChainType.FUZZY, True)
        controller.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
        assert u.EditorAssetLibrary.save_loaded_asset(retargeter)
    inputs = u.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget = [u.EditorAssetLibrary.find_asset_data(p) for p in animation_paths]
    inputs.source_mesh = source_mesh
    inputs.target_mesh = target_mesh
    inputs.ik_retarget_asset = retargeter
    inputs.target_path = '/Game/Combat/Animations/Retarget/Raw'
    inputs.prefix = 'RT_'
    inputs.include_referenced_assets = False
    inputs.overwrite_existing_files = False
    results = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
    assert len(results) == len(animation_paths), 'Not every selected clip was retargeted'
    for result in results:
        sequence = result.get_asset()
        assert sequence.get_editor_property('skeleton') == target_mesh.get_editor_property('skeleton')
        assert u.EditorAssetLibrary.save_loaded_asset(sequence)
        print('RETARGETED', sequence.get_path_name())
    return [result.get_asset() for result in results]
