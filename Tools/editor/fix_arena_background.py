import unreal as u
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
if not any(a.get_actor_label()=='Combat_SkyAtmosphere' for a in actors.get_all_level_actors()):
    sky=actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0));sky.set_actor_label('Combat_SkyAtmosphere')
for actor in actors.get_all_level_actors():
    if isinstance(actor,u.DirectionalLight):
        actor.light_component.set_editor_property('atmosphere_sun_light',True)
        actor.set_actor_rotation(u.Rotator(pitch=-48,yaw=-32,roll=0),False)
    if actor.get_actor_label()=='Combat_BossSpawn': actor.set_actor_rotation(u.Rotator(yaw=180),False)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/Combat/Maps/L_CombatArena')
print('SKY_BACKGROUND_SAVED')
