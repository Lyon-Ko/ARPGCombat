import unreal as u

ROOT='/Game/Combat'
assets=u.AssetToolsHelpers.get_asset_tools()
assert hasattr(u,'CombatEditorLibrary'),'Editor helper build required'

def blueprint(path,parent):
    bp=u.load_asset(path)
    if not bp:
        factory=u.BlueprintFactory(); factory.set_editor_property('parent_class',parent)
        bp=assets.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.Blueprint,factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    return bp

blend=u.load_asset(ROOT+'/Animations/BS_CombatLocomotion') or u.EditorAssetLibrary.duplicate_asset('/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run',ROOT+'/Animations/BS_CombatLocomotion')
anim=u.CombatEditorLibrary.create_locomotion(ROOT+'/Animations/ABP_Combat',u.CombatAnimInstance,u.load_asset(ROOT+'/Characters/SK_CombatSkeleton'),blend,u.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop'))
assert anim,'AnimBlueprint construction/compile failed'
tree=u.CombatEditorLibrary.create_combat_state_tree(ROOT+'/AI/ST_CombatBoss',['/Script/Combat.CombatStateTreeSelectTask','/Script/Combat.CombatStateTreeExecuteTask','/Script/Combat.CombatStateTreeRecoverTask'])
assert tree,'StateTree construction/compile failed'
controller=blueprint(ROOT+'/AI/BP_CombatAI',u.CombatAIController)
u.get_default_object(controller.generated_class()).set_editor_property('combat_state_tree',tree)
u.EditorAssetLibrary.save_loaded_asset(controller)
widget=u.CombatEditorLibrary.create_hud(ROOT+'/UI/WBP_CombatHUD',u.CombatHUDWidget)
if not widget: print('PENDING_EDITOR_REBUILD: styled WBP variable collision; using native HUD temporarily for independent combat validation')

for is_boss,label in [(False,'Player'),(True,'Boss')]:
    bp=blueprint(ROOT+'/Characters/BP_Combat'+label,u.CombatCharacter)
    cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('is_boss',is_boss)
    cdo.set_editor_property('initial_health',1500 if is_boss else 300)
    cdo.set_editor_property('initial_poise',180 if is_boss else 100)
    cdo.set_editor_property('footstep_sounds',[u.load_asset(ROOT+'/Audio/SW_Footstep')])
    cdo.set_editor_property('death_sound',u.load_asset(ROOT+'/Audio/SW_Burst'))
    cdo.set_editor_property('default_camera_distance',560)
    mesh=cdo.get_editor_property('mesh')
    mesh.set_skeletal_mesh_asset(u.load_asset(ROOT+'/Characters/SK_'+label+'_ArmoredSwordsman'))
    mesh.set_editor_property('relative_location',u.Vector(0,0,-96))
    mesh.set_editor_property('relative_rotation',u.Rotator(pitch=0,yaw=-90,roll=0))
    mesh.set_anim_instance_class(anim.generated_class())
    if is_boss: mesh.set_editor_property('relative_scale3d',u.Vector(1.18,1.18,1.18))
    weapon=cdo.get_editor_property('weapon_mesh')
    weapon_asset=u.load_asset(ROOT+'/Weapons/SM_'+label+('_Greatsword' if is_boss else '_LongSword'))
    for socket_name,distance in [('BladeBase',12),('BladeTip',137 if is_boss else 106)]:
        socket=weapon_asset.find_socket(socket_name)
        if not socket:
            socket=u.StaticMeshSocket(outer=weapon_asset)
            socket.set_editor_property('socket_name',socket_name)
            socket.set_editor_property('relative_location',u.Vector(distance,0,0))
            weapon_asset.add_socket(socket)
    u.EditorAssetLibrary.save_loaded_asset(weapon_asset)
    weapon.set_static_mesh(weapon_asset)
    cdo.set_editor_property('weapon_blade_length',137 if is_boss else 106)
    cdo.set_editor_property('skill_definitions',[u.load_asset(p) for p in u.EditorAssetLibrary.list_assets(ROOT+'/Skills') if ('DA_Boss_' in p)==is_boss and 'Example' not in p])
    if is_boss:
        cdo.set_editor_property('ai_controller_class',controller.generated_class())
        cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    assert u.CombatEditorLibrary.compile_and_save(bp),bp.get_path_name()
    print('CHARACTER_CONFIGURED',bp.get_path_name())
mode=blueprint(ROOT+'/Blueprints/BP_CombatGameMode',u.CombatGameMode)
defaults=u.get_default_object(mode.generated_class())
defaults.set_editor_property('default_pawn_class',u.load_asset(ROOT+'/Characters/BP_CombatPlayer').generated_class())
defaults.set_editor_property('boss_class',u.load_asset(ROOT+'/Characters/BP_CombatBoss').generated_class())
defaults.set_editor_property('battle_music',u.load_asset(ROOT+'/Audio/SW_BattleMusic'))
defaults.set_editor_property('music_volume',.35)
defaults.set_editor_property('hud_widget_class',widget.generated_class() if widget else u.CombatHUDWidget)
defaults.set_editor_property('boss_spawn_transform',u.Transform(location=u.Vector(600,0,100),rotation=u.Rotator(pitch=0,yaw=180,roll=0)))
u.EditorAssetLibrary.save_loaded_asset(mode)
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
levels.load_level(ROOT+'/Maps/L_CombatArena')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',mode.generated_class())
actor_subsystem=u.get_editor_subsystem(u.EditorActorSubsystem)
for actor in actor_subsystem.get_all_level_actors():
    if actor.get_actor_label()=='Combat_Boss': actor_subsystem.destroy_actor(actor)
boss=actor_subsystem.spawn_actor_from_class(u.load_asset(ROOT+'/Characters/BP_CombatBoss').generated_class(),u.Vector(600,0,100),u.Rotator(pitch=0,yaw=180,roll=0))
boss.set_actor_label('Combat_Boss')
assert u.EditorLoadingAndSavingUtils.save_map(world,ROOT+'/Maps/L_CombatArena')
print('PRESENTATION_ASSETS',anim.get_path_name(),tree.get_path_name(),widget.get_path_name() if widget else 'STYLED_HUD_PENDING_REBUILD')
