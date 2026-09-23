"""Idempotent non-runtime assets. Run with Tools/Combat.ps1 python -File ..."""
import unreal as u
from pathlib import Path
import json
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arena_checker_floor import create_checker_material

ROOT = '/Game/Combat'
assets = u.AssetToolsHelpers.get_asset_tools()
actors = u.get_editor_subsystem(u.EditorActorSubsystem)

def create(path, cls, factory):
    return u.load_asset(path) or assets.create_asset(path.rsplit('/',1)[1], path.rsplit('/',1)[0], cls, factory)

def concrete():
    path = ROOT+'/Materials/M_ArenaConcrete'
    material = create(path, u.Material, u.MaterialFactoryNew())
    lib = u.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    color = lib.create_material_expression(material,u.MaterialExpressionConstant3Vector,-400,-150)
    color.set_editor_property('constant',u.LinearColor(.19,.205,.22,1))
    lib.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough = lib.create_material_expression(material,u.MaterialExpressionConstant,-400,30)
    rough.set_editor_property('r',.82)
    lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    noise = lib.create_material_expression(material,u.MaterialExpressionNoise,-650,240)
    noise.set_editor_property('scale',.075)
    noise.set_editor_property('levels',2)
    noise.set_editor_property('output_min',.74)
    noise.set_editor_property('output_max',.88)
    lib.connect_material_property(noise,'',u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(material)
    u.EditorAssetLibrary.save_loaded_asset(material)
    return material

def arena(material):
    path = ROOT+'/Maps/L_CombatArena'
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if u.EditorAssetLibrary.does_asset_exist(path):
        levels.load_level(path)
    else:
        u.EditorLoadingAndSavingUtils.new_blank_map(False)
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith('Combat_'):
            actors.destroy_actor(actor)
    cube = u.load_asset('/Engine/BasicShapes/Cube')
    def block(label, loc, size, block_material=None):
        a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*loc))
        a.set_actor_label('Combat_'+label)
        a.static_mesh_component.set_static_mesh(cube)
        a.static_mesh_component.set_material(0,block_material or material)
        a.static_mesh_component.set_collision_profile_name('BlockAll')
        a.set_actor_scale3d(u.Vector(*(v/100 for v in size)))
        return a
    block('Floor',(0,0,-50),(5000,5000,100),create_checker_material())
    block('WallNorth',(0,2550,200),(5200,100,400))
    block('WallSouth',(0,-2550,200),(5200,100,400))
    block('WallEast',(2550,0,200),(100,5000,400))
    block('WallWest',(-2550,0,200),(100,5000,400))
    sun=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1800),u.Rotator(pitch=-48,yaw=-32,roll=0))
    sun.set_actor_label('Combat_Sun')
    sun.light_component.set_editor_property('intensity',3.0)
    sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,1000))
    sky.set_actor_label('Combat_Sky')
    sky.light_component.set_editor_property('intensity',1.0)
    sky.light_component.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap',u.load_asset('/Engine/EngineResources/DefaultTextureCube'))
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    exposure=actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector(0,0,0))
    exposure.set_actor_label('Combat_Exposure')
    exposure.set_editor_property('unbound',True)
    settings=exposure.get_editor_property('settings')
    settings.set_editor_property('override_auto_exposure_min_brightness',True)
    settings.set_editor_property('override_auto_exposure_max_brightness',True)
    settings.set_editor_property('auto_exposure_min_brightness',1.0)
    settings.set_editor_property('auto_exposure_max_brightness',1.0)
    settings.set_editor_property('override_depth_of_field_focal_distance',True)
    settings.set_editor_property('depth_of_field_focal_distance',0.0)
    exposure.set_editor_property('settings',settings)
    start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(-600,0,100),u.Rotator(0,0,0))
    start.set_actor_label('Combat_PlayerStart')
    boss=actors.spawn_actor_from_class(u.TargetPoint,u.Vector(600,0,100),u.Rotator(pitch=0,yaw=180,roll=0))
    boss.set_actor_label('Combat_BossSpawn')
    boss.set_editor_property('tags',['Combat.BossSpawn'])
    nav=actors.spawn_actor_from_class(u.NavMeshBoundsVolume,u.Vector(0,0,250))
    nav.set_actor_label('Combat_NavBounds')
    # Brush geometry is authored by the editor helper when it is compiled.
    if hasattr(u,'CombatEditorLibrary'):
        u.CombatEditorLibrary.build_nav_bounds(nav,u.Vector(5000,5000,1000))
    else:
        # The actor factory supplies a validated 200 cm cube brush.
        nav.set_actor_scale3d(u.Vector(25,25,5))
    levels.set_level_viewport_camera_info(u.Vector(-1450,-1900,1450),u.Rotator(pitch=-30,yaw=52,roll=0),'')
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),path)
    print('ARENA_SAVED',path,'actors',len(actors.get_all_level_actors()))

def audio():
    files=sorted((Path(u.Paths.project_dir())/'SourceAssets/Audio/Ready').glob('*.wav'))
    tasks=[]
    for file in files:
        path=ROOT+'/Audio/'+file.stem
        existing=u.load_asset(path)
        digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if existing and u.EditorAssetLibrary.get_metadata_tag(existing,'CombatSourceSHA256')==digest:
            continue
        task=u.AssetImportTask()
        task.filename=str(file)
        task.destination_path=ROOT+'/Audio'
        task.automated=True
        task.replace_existing=True
        task.save=True
        tasks.append(task)
    if tasks: assets.import_asset_tasks(tasks)
    for file in files:
        wave=u.load_asset(ROOT+'/Audio/'+file.stem)
        assert wave,file.name
        u.EditorAssetLibrary.set_metadata_tag(wave,'CombatSourceSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
        u.EditorAssetLibrary.save_loaded_asset(wave)
    print('AUDIO_COUNT',len(u.EditorAssetLibrary.list_assets(ROOT+'/Audio')))

def effects():
    area=create(ROOT+'/Materials/M_AreaWarning',u.Material,u.MaterialFactoryNew())
    lib=u.MaterialEditingLibrary
    lib.delete_all_material_expressions(area)
    area.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    area.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    area.set_editor_property('two_sided',True)
    tint=lib.create_material_expression(area,u.MaterialExpressionVectorParameter,-350,0)
    tint.set_editor_property('parameter_name','Tint')
    tint.set_editor_property('default_value',u.LinearColor(1,.1,.015,1))
    opacity=lib.create_material_expression(area,u.MaterialExpressionScalarParameter,-350,160)
    opacity.set_editor_property('parameter_name','Opacity')
    opacity.set_editor_property('default_value',.65)
    uv=lib.create_material_expression(area,u.MaterialExpressionTextureCoordinate,-750,300)
    ring=lib.create_material_expression(area,u.MaterialExpressionCustom,-500,340)
    ring.set_editor_property('code','float r = length(UV - float2(0.5, 0.5)); return 0.12 + 0.88 * smoothstep(0.42, 0.48, r);')
    ring.set_editor_property('description','Crisp radial boundary with quiet interior')
    ring.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    custom_input=u.CustomInput()
    custom_input.set_editor_property('input_name','UV')
    ring.set_editor_property('inputs',[custom_input])
    lib.connect_material_expressions(uv,'',ring,'UV')
    alpha=lib.create_material_expression(area,u.MaterialExpressionMultiply,-160,200)
    lib.connect_material_expressions(opacity,'',alpha,'A')
    lib.connect_material_expressions(ring,'',alpha,'B')
    lib.connect_material_property(tint,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
    lib.recompile_material(area)
    u.EditorAssetLibrary.save_loaded_asset(area)
    templates={'NS_BladeTrail':'AttributeReaderTrails','NS_BossBladeTrail':'AttributeReaderTrails','NS_HitSparks':'DirectionalBurst','NS_ParryFlash':'RadialBurst','NS_AOEFlash':'SimpleExplosion','NS_Projectile':'DirectionalBurst','NS_AOEWarning':'RadialBurst'}
    for name,template in templates.items():
        path=ROOT+'/VFX/'+name
        fx=u.load_asset(path) or u.EditorAssetLibrary.duplicate_asset('/Niagara/DefaultAssets/Templates/Systems/'+template,path)
        assert fx, path
        if hasattr(u,'CombatEditorLibrary'):
            warm=name in ('NS_HitSparks','NS_AOEFlash','NS_AOEWarning','NS_BossBladeTrail','NS_Projectile')
            color=u.LinearColor(1,.32,.06,1) if warm else u.LinearColor(.12,.8,1,1)
            size={'NS_HitSparks':5,'NS_ParryFlash':24,'NS_AOEFlash':65,'NS_Projectile':18,'NS_AOEWarning':12,'NS_BladeTrail':6,'NS_BossBladeTrail':8}[name]
            assert u.CombatEditorLibrary.configure_niagara(fx,color,size,8),name
        u.EditorAssetLibrary.save_loaded_asset(fx)
    print('NIAGARA_COUNT',len(templates))

arena(concrete())
audio()
effects()
print('FOUNDATION_PASS')
