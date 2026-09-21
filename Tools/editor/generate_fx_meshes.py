"""Import original wave/ring meshes, author simple editable emissive materials."""
import unreal as u
from pathlib import Path
import hashlib
ROOT='/Game/Combat'
assets=u.AssetToolsHelpers.get_asset_tools()
for name in ('SM_SwordWave','SM_WarningRing'):
    source=Path(u.Paths.project_dir())/'SourceAssets/VFX'/(name+'.fbx')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    mesh=u.load_asset(ROOT+'/VFX/'+name)
    if not mesh or u.EditorAssetLibrary.get_metadata_tag(mesh,'CombatSourceSHA256')!=digest:
        options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False
        options.set_editor_property('automated_import_should_detect_type',False)
        options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
        options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=ROOT+'/VFX';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True;task.options=options
        assets.import_asset_tasks([task]);mesh=u.load_asset(ROOT+'/VFX/'+name)
    assert mesh,name
    u.EditorAssetLibrary.set_metadata_tag(mesh,'CombatSourceSHA256',digest)
    u.EditorAssetLibrary.save_loaded_asset(mesh)
    print('FX_MESH',name,mesh.get_bounds())
lib=u.MaterialEditingLibrary
for name,additive in [('M_SwordWave',True),('M_WarningRing',False)]:
    path=ROOT+'/Materials/'+name
    mat=u.load_asset(path) or assets.create_asset(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE if additive else u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);mat.set_editor_property('two_sided',True)
    tint=lib.create_material_expression(mat,u.MaterialExpressionVectorParameter,-500,0);tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',u.LinearColor(1,.20,.035,1))
    strength=lib.create_material_expression(mat,u.MaterialExpressionScalarParameter,-500,120);strength.set_editor_property('parameter_name','Glow');strength.set_editor_property('default_value',3.0 if additive else 1.8)
    mul=lib.create_material_expression(mat,u.MaterialExpressionMultiply,-220,0);lib.connect_material_expressions(tint,'',mul,'A');lib.connect_material_expressions(strength,'',mul,'B');lib.connect_material_property(mul,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity=lib.create_material_expression(mat,u.MaterialExpressionScalarParameter,-220,160);opacity.set_editor_property('parameter_name','Opacity');opacity.set_editor_property('default_value',.7 if additive else .8)
    lib.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY);lib.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
for path in u.EditorAssetLibrary.list_assets(ROOT+'/Skills',True):
    data=u.load_asset(path)
    if not isinstance(data,u.CombatSkillDefinition):continue
    if 'Boss_AOE' in path or 'CrescentBurst' in path:
        data.set_editor_property('area_mesh',u.load_asset(ROOT+'/VFX/SM_WarningRing'))
        data.set_editor_property('area_material',u.load_asset(ROOT+'/Materials/M_WarningRing'))
    if 'Boss_Leap' in path:
        if hasattr(data,'projectile_mesh'):
            data.set_editor_property('projectile_mesh',u.load_asset(ROOT+'/VFX/SM_SwordWave'))
            data.set_editor_property('projectile_material',u.load_asset(ROOT+'/Materials/M_SwordWave'))
            data.set_editor_property('projectile_collision_half_extent',u.Vector(24,85,20))
        else:print('PENDING_RUNTIME_BUILD_PROJECTILE',path)
    u.EditorAssetLibrary.save_loaded_asset(data)
print('FX_MESH_ASSETS_SAVED')
