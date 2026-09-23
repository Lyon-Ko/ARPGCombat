"""Transient pose lineup for visual review, never saved into the arena map."""
import builtins
from pathlib import Path
import unreal as u

editor = u.get_editor_subsystem(u.EditorActorSubsystem)
old = getattr(builtins, '_pivot_preview_actors', [])
for actor in old:
    if u.SystemLibrary.is_valid(actor):
        editor.destroy_actor(actor)
actors = []
builtins._pivot_preview_actors = actors
mesh = u.load_asset('/Game/Combat/Characters/SK_CombatKwang')
floor = editor.spawn_actor_from_class(u.StaticMeshActor, u.Vector(-150, 0, 9995), transient=True)
actors.append(floor)
floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
floor.set_actor_scale3d(u.Vector(15, 18, .05))
light = editor.spawn_actor_from_class(u.DirectionalLight, u.Vector(0, 0, 10500),
                                      u.Rotator(pitch=-55, yaw=135), transient=True)
actors.append(light)
light.light_component.set_intensity(5.)
times = globals().get('review_times', (.05, .4, .7, 1., 1.4))
for row, direction in enumerate(('Left', 'Right')):
    sequence = u.load_asset('/Game/Combat/Animations/Native/Kwang/A_FreePivot_' + direction)
    curve_times, curve_yaws = u.AnimationLibrary.get_float_keys(sequence, 'PivotYaw')
    for column, time in enumerate(times):
        time = min(time, sequence.get_play_length())
        yaw = curve_yaws[min(round(time * 60), len(curve_yaws) - 1)]
        actor = editor.spawn_actor_from_class(u.SkeletalMeshActor,
            u.Vector(row * -360, (column - 2) * 250, 10000),
            u.Rotator(yaw=yaw - 90), transient=True)
        actors.append(actor)
        actor.set_actor_label(f'PivotReview_{direction}_{time:.2f}')
        component = actor.skeletal_mesh_component
        component.set_skeletal_mesh_asset(mesh)
        assert u.CombatEditorLibrary.sample_animation_preview(component, sequence, time)
camera = editor.spawn_actor_from_class(u.CameraActor, u.Vector(1350, 0, 11100),
                                       u.Rotator(pitch=-35, yaw=180), transient=True)
actors.append(camera)
camera.camera_component.set_field_of_view(58.)
builtins._pivot_preview_camera = camera
u.AutomationLibrary.take_high_res_screenshot(2200, 1400,
    str(Path(u.Paths.project_saved_dir()) / 'Acceptance' / globals().get('review_filename', 'SwordPivotLineup.png')),
    camera=camera, delay=1.)
