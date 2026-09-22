"""Prepare the current player's target rig for official locomotion retargeting.

Run through Tools/Combat.ps1 python. Does not alter the player or source packs.
"""
import json
from pathlib import Path
import unreal as u

MESH = '/Game/Combat/Characters/SK_CombatKwang'
RIG = '/Game/Combat/Animations/Retarget/IK_CombatKwang'
mesh = u.load_asset(MESH)
assert mesh, MESH
rig = u.load_asset(RIG)
if not rig:
    rig = u.AssetToolsHelpers.get_asset_tools().create_asset(
        RIG.rsplit('/', 1)[1], RIG.rsplit('/', 1)[0],
        u.IKRigDefinition, u.IKRigDefinitionFactory())
    assert rig
    controller = u.IKRigController.get_controller(rig)
    assert controller.set_skeletal_mesh(mesh)
    assert controller.apply_auto_generated_retarget_definition(), 'Kwang template not recognized'
else:
    controller = u.IKRigController.get_controller(rig)
    assert controller.get_skeletal_mesh() == mesh, 'Existing rig has a different target'

chains = controller.get_retarget_chains()
assert chains, 'Missing retarget chains'
assert str(controller.get_retarget_root()) == 'pelvis'
assert u.EditorAssetLibrary.save_loaded_asset(rig)
report = {
    'status': 'target_rig_prepared_source_animation_pending',
    'mesh': MESH,
    'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
    'rig': RIG,
    'pelvis': str(controller.get_retarget_root()),
    'chains': [str(chain.chain_name) for chain in chains],
    'note': 'No animation retargeted or gameplay binding changed yet.',
}
output = Path(u.Paths.project_saved_dir()) / 'Acceptance' / 'KwangRetargetPreparation.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
