"""Idempotent native Paragon adaptation. Original packs are read-only inputs.

Blade sockets derive from actual skin-weighted vertex extents recorded by
probe_blade_geometry.py; hit windows derive from sampled native blade motion.
"""
import unreal as u
import json
from pathlib import Path

ROOT='/Game/Combat'
assets=u.AssetToolsHelpers.get_asset_tools()
def duplicate(source,path):
    obj=u.load_asset(path) or u.EditorAssetLibrary.duplicate_asset(source,path)
    assert obj,(source,path)
    return obj
def tag(name):
    value=u.GameplayTag(); assert value.import_text('(TagName="Combat.Event.'+name+'")'); return value
def sequence(hero,name):
    source='/Game/Paragon'+hero+'/Characters/Heroes/'+hero+'/Animations/'+name
    path=ROOT+'/Animations/Native/'+hero+'/A_'+name
    seq=duplicate(source,path)
    u.AnimationLibrary.remove_all_animation_notify_tracks(seq)
    seq.set_editor_property('enable_root_motion',False)
    seq.set_editor_property('force_root_lock',True)
    u.EditorAssetLibrary.save_loaded_asset(seq)
    return seq
def montage(hero,name,clip,rate=1,events=None):
    seq=sequence(hero,clip)
    path=ROOT+'/Animations/Native/'+hero+'/AM_'+name
    factory=u.AnimMontageFactory(); factory.source_animation=seq; factory.target_skeleton=seq.get_editor_property('skeleton')
    asset=u.load_asset(path) or assets.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.AnimMontage,factory)
    tracks=list(asset.get_editor_property('slot_anim_tracks'))
    track=tracks[0].get_editor_property('anim_track')
    segments=list(track.get_editor_property('anim_segments'))
    segments[0].set_editor_property('anim_reference',seq)
    segments[0].set_editor_property('anim_end_time',seq.get_editor_property('sequence_length'))
    track.set_editor_property('anim_segments',segments)
    tracks[0].set_editor_property('anim_track',track)
    asset.set_editor_property('slot_anim_tracks',tracks)
    asset.set_editor_property('rate_scale',rate)
    for prop,time in [('blend_in',.045),('blend_out',.08)]:
        blend=asset.get_editor_property(prop); blend.set_editor_property('blend_time',time); asset.set_editor_property(prop,blend)
    u.AnimationLibrary.remove_all_animation_notify_tracks(asset)
    if events:
        u.AnimationLibrary.add_animation_notify_track(asset,'CombatEvents')
        for time,event in sorted(events):
            notify=u.AnimationLibrary.add_animation_notify_event(asset,'CombatEvents',time,u.CombatAnimNotify_Event)
            notify.set_editor_property('event_tag',tag(event))
    u.EditorAssetLibrary.save_loaded_asset(asset)
    return asset

for hero,label,source_mesh in [('Kwang','Player','Kwang_GDC'),('Greystone','Boss','Greystone')]:
    base='/Game/Paragon'+hero+'/Characters/Heroes/'+hero
    mesh=duplicate(base+'/Meshes/'+source_mesh,ROOT+'/Characters/SK_Combat'+hero)
    skeleton=mesh.get_editor_property('skeleton')
    socket_settings=[('BladeBase','weapon_r',u.Vector(0,-18,0)),('BladeTip','weapon_r',u.Vector(0,-147,0))] if hero=='Kwang' else [('BladeBase','sword_bottom',u.Vector(0,0,14)),('BladeTip','sword_top',u.Vector(0,0,78))]
    for socket_name,bone,offset in socket_settings:
        socket=mesh.find_socket(socket_name)
        if not socket:
            socket=u.SkeletalMeshSocket(outer=mesh)
            mesh.add_socket(socket,False)
            assert mesh.rename_socket(socket.get_editor_property('socket_name'),socket_name)
        socket.set_socket_parent(mesh,bone)
        socket.set_socket_local_transform(u.Transform(location=offset))
    u.EditorAssetLibrary.save_loaded_asset(mesh)
    idle=sequence(hero,'Idle'); jog=sequence(hero,'Jog_Fwd'); air=sequence(hero,'Jump_Apex' if hero=='Kwang' else 'Jump_Fall')
    path=ROOT+'/Animations/Native/'+hero+'/BS_Locomotion2D'
    blend=u.load_asset(path)
    if not blend:
        factory=u.BlendSpaceFactoryNew(); factory.target_skeleton=skeleton; factory.preview_skeletal_mesh=mesh
        blend=assets.create_asset('BS_Locomotion2D',path.rsplit('/',1)[0],u.BlendSpace,factory)
    params=list(blend.get_editor_property('blend_parameters'))
    params[0].set_editor_property('display_name','Speed')
    params[0].set_editor_property('min',0); params[0].set_editor_property('max',650); params[0].set_editor_property('grid_num',4)
    params[1].set_editor_property('display_name','Direction')
    params[1].set_editor_property('min',-180);params[1].set_editor_property('max',180);params[1].set_editor_property('grid_num',4)
    blend.set_editor_property('blend_parameters',params)
    samples=[]
    for direction,clip in [(-180,'Jog_Bwd'),(-90,'Jog_Left'),(0,'Jog_Fwd'),(90,'Jog_Right'),(180,'Jog_Bwd')]:
        directional=sequence(hero,clip)
        for speed,source,rate in [(0,idle,1),(350,directional,1),(650,directional,1)]:
            sample=u.BlendSample(); sample.set_editor_property('animation',source); sample.set_editor_property('sample_value',u.Vector(speed,direction,0)); sample.set_editor_property('rate_scale',rate)
            samples.append(sample)
    blend.set_editor_property('sample_data',samples)
    assert u.CombatEditorLibrary.rebuild_blend_space(blend)
    anim=u.CombatEditorLibrary.create_locomotion(ROOT+'/Animations/Native/'+hero+'/ABP_Combat'+hero+'2D',u.CombatAnimInstance,skeleton,blend,air)
    assert anim,hero
    bp=u.load_asset(ROOT+'/Characters/BP_Combat'+label); cdo=u.get_default_object(bp.generated_class())
    component=cdo.get_editor_property('mesh'); component.set_skeletal_mesh_asset(mesh); component.set_anim_instance_class(anim.generated_class())
    half_height=104 if hero=='Greystone' else 92
    cdo.get_editor_property('capsule_component').set_capsule_size(43 if hero=='Greystone' else 38,half_height,False)
    component.set_editor_property('relative_location',u.Vector(0,0,-half_height)); component.set_editor_property('relative_rotation',u.Rotator(pitch=0,yaw=-90,roll=0))
    component.set_editor_property('relative_scale3d',u.Vector(1.13,1.13,1.13) if hero=='Greystone' else u.Vector(1,1,1))
    cdo.set_editor_property('trace_from_character_mesh',True)
    cdo.set_editor_property('trace_start_socket','BladeBase'); cdo.set_editor_property('trace_end_socket','BladeTip')
    weapon=cdo.get_editor_property('weapon_mesh'); weapon.set_static_mesh(None); weapon.set_editor_property('hidden_in_game',True)
    cdo.set_editor_property('death_montage',montage(hero,'Death','Death_Bwd' if hero=='Kwang' else 'Death'))
    cdo.set_editor_property('hit_react_montage',montage(hero,'HitReact','Hitreact_Fwd' if hero=='Kwang' else 'HitReact_Front',1.6))
    assert u.CombatEditorLibrary.compile_and_save(bp)
    print('NATIVE_CHARACTER',label,mesh.get_path_name(),anim.get_path_name())

# Times below are SOURCE clip seconds (montage rate applies to both pose and notify).
# Primary swing sources contain long anticipation/hold recoveries; Finish trims those
# recoveries through the visible ability graph, preserving their different blade arcs.
specs={
 'Attack1':('Kwang','PrimaryAttack_A_Slow',1,.55,(.15,.28),.06),
 'Attack2':('Kwang','PrimaryAttack_B_Slow',1,.58,(.16,.29),.07),
 'Attack3':('Kwang','PrimaryAttack_C_Slow',1,.62,(.16,.29),.07),
 'Attack4':('Kwang','PrimaryAttack_D_Slow',1,.75,(.17,.31),.08),
 'DashStrike':('Kwang','PrimaryAttack_A_Slow',1.15,.64,(.15,.29),.035),
 'Air1':('Kwang','PrimaryAttack_Air',1.2,.65,(.20,.33),.08),
 'Air2':('Kwang','PrimaryAttack_C_Slow',1.1,.69,(.16,.30),.06),
 'Plunge':('Kwang','Ability_R',1.35,1.0,(.40,.65),.34),
 'Parry':('Kwang','Ability_RMB',1.2,.36,None,None),
 'Riposte':('Kwang','Ability_R',1.2,1.04,(.35,.61),.24),
 'Dash':('Kwang','Sprint_Fwd',1,.255,None,None),
 'Boss.Combo1':('Greystone','Attack_A_Fast',.68,.56,(.115,.205),.05),
 'Boss.Combo2':('Greystone','Attack_C_Fast',.68,.56,(.13,.23),.05),
 'Boss.Combo3':('Greystone','Attack_D_Fast',.62,.58,(.12,.225),.06),
 'Boss.AOE':('Greystone','Ability_R',1,1.65,None,None),
 'Boss.DashSlash':('Greystone','Ability_E',1,1.1,(.51,.66),.20),
 'Boss.LeapLeft':('Greystone','Jump_Melee',1,1.01,None,.035),
 'Boss.LeapRight':('Greystone','Jump_Melee',1,1.01,None,.035),
 'Boss.LeapBack':('Greystone','Jump_Melee',.95,1.01,None,.035),
}
report=[]
for skill,(hero,clip,rate,finish,hit,move) in specs.items():
    events=[]
    if hit: events.extend([(hit[0],'HitOpen'),(hit[1],'HitClose')])
    if move is not None: events.append((move,'Move'))
    if skill.startswith('Attack') or skill in ('Air1','Air2') or 'Combo' in skill:
        events.append(((hit[1]+.025),'ComboOpen'))
    if skill=='Boss.AOE': events.extend([(.08,'AreaWarning'),(.91,'AreaRelease')])
    if 'Leap' in skill: events.append((.27,'Projectile'))
    events.extend([(finish-.11,'Cancelable'),(finish,'Finish')])
    asset=montage(hero,skill.replace('.','_'),clip,rate,events)
    data=u.load_asset(ROOT+'/Skills/DA_'+skill.replace('.','_'))
    data.set_editor_property('montage',asset); data.set_editor_property('duration',finish/rate)
    if skill in ('Boss.Combo1','Boss.Combo2','Boss.Combo3'):
        # Native Greystone arms/blade extend ~125cm before the tip. Large old
        # Manny lunges pushed the hilt past close targets; use short pressure steps.
        data.set_editor_property('movement_distance',{'Boss.Combo1':30,'Boss.Combo2':35,'Boss.Combo3':55}[skill])
        data.set_editor_property('max_ai_range',220)
    if 'Leap' in skill: data.set_editor_property('movement_duration',.50)
    if skill=='Boss.DashSlash': data.set_editor_property('movement_duration',.35)
    if skill=='Boss.AOE':
        data.set_editor_property('cooldown',4.8)
        data.set_editor_property('max_ai_range',420)
    elif skill.startswith('Boss.') and 'Combo' not in skill: data.set_editor_property('cooldown',2.2)
    # Constant 12cm trace radius; geometry/notify timing do the targeting work.
    data.set_editor_property('trace_radius',12)
    u.EditorAssetLibrary.save_loaded_asset(data)
    report.append({'skill':skill,'montage':asset.get_path_name(),'source':clip,'duration':finish/rate,'events':events})
u.EditorAssetLibrary.save_directory(ROOT,True,True)
# Keep the arena empty until the player presses R to spawn the boss.
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
for actor in actors.get_all_level_actors():
    if actor.get_actor_label()=='Combat_Boss': actors.destroy_actor(actor)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert u.EditorLoadingAndSavingUtils.save_map(world,ROOT+'/Maps/L_CombatArena')
out=Path(u.Paths.project_saved_dir())/'Acceptance/NativeSkillAssets.json'; out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NATIVE_SKILLS_CONFIGURED',len(report))
