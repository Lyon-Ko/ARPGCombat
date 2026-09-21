"""Import authored FBX without modifying the mannequin/template skeleton."""
import unreal as u
from pathlib import Path
import json
import hashlib

root=Path(u.Paths.project_dir())
assets=u.AssetToolsHelpers.get_asset_tools()
skel_path='/Game/Combat/Characters/SK_CombatSkeleton'
skel=u.load_asset(skel_path) or u.EditorAssetLibrary.duplicate_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin',skel_path)
skel.set_editor_property('compatible_skeletons',[u.load_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin')])
u.EditorAssetLibrary.save_loaded_asset(skel)

def import_file(file,kind):
    dest='/Game/Combat/'+{'character':'Characters','animation':'Animations/Sequences','weapon':'Weapons'}[kind]
    path=dest+'/'+file.stem
    existing=u.load_asset(path)
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    if existing and u.EditorAssetLibrary.get_metadata_tag(existing,'CombatSourceSHA256')==digest: return existing
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.import_materials=kind!='animation'
    opt.import_textures=False
    opt.import_animations=kind=='animation'
    opt.import_mesh=kind!='animation'
    opt.import_as_skeletal=kind!='weapon'
    opt.mesh_type_to_import={'character':u.FBXImportType.FBXIT_SKELETAL_MESH,'animation':u.FBXImportType.FBXIT_ANIMATION,'weapon':u.FBXImportType.FBXIT_STATIC_MESH}[kind]
    if kind!='weapon': opt.skeleton=skel
    if kind=='character':
        opt.create_physics_asset=True
        opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        opt.skeletal_mesh_import_data.set_editor_property('import_morph_targets',False)
    if kind=='animation':
        opt.anim_sequence_import_data.set_editor_property('import_bone_tracks',True)
        opt.anim_sequence_import_data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    if kind=='weapon': opt.static_mesh_import_data.set_editor_property('combine_meshes',True)
    task=u.AssetImportTask()
    task.filename=str(file)
    task.destination_path=dest
    task.destination_name=file.stem
    task.automated=True
    task.replace_existing=True
    task.replace_existing_settings=True
    task.save=True
    task.options=opt
    task.factory=u.FbxFactory()
    assets.import_asset_tasks([task])
    result=u.load_asset(path)
    assert result, (str(file),list(task.imported_object_paths))
    u.EditorAssetLibrary.set_metadata_tag(result,'CombatSourceSHA256',digest)
    u.EditorAssetLibrary.save_loaded_asset(result)
    print('IMPORTED',result.get_path_name(),result.get_class().get_name())
    return result

for directory,kind in [('Characters','character'),('Weapons','weapon'),('Animations','animation')]:
    for file in sorted((root/'SourceAssets'/directory).glob('*.fbx')):
        import_file(file,kind)
u.EditorAssetLibrary.save_directory('/Game/Combat',only_if_is_dirty=True,recursive=True)
print('SOURCE_IMPORT_PASS')
