"""Offline local-space bone layering for a retargeted Kwang turn.

Call bake(source_path, output_path, start, end, upper_phase=0). The source
must already use Kwang's skeleton and retain the official root transform.
Root translation never becomes gameplay movement; yaw is exported separately.
"""
import json
import math
from pathlib import Path
import unreal as u

POSE = u.AnimPoseExtensions
LOCAL = u.AnimPoseSpaces.LOCAL
DONOR = '/Game/Combat/Animations/Native/Kwang/A_Jog_Fwd'


def mix(a, b, weight):
    result = u.Transform()
    result.translation = a.translation * (1 - weight) + b.translation * weight
    result.rotation = u.MathLibrary.quat_slerp(a.rotation, b.rotation, weight)
    result.scale3d = a.scale3d * (1 - weight) + b.scale3d * weight
    return result


def bake(source_path, output_path, start=0., end=None, upper_phase=0.):
    source, donor = u.load_asset(source_path), u.load_asset(DONOR)
    assert source and donor
    skeleton = donor.get_editor_property('skeleton')
    assert source.get_editor_property('skeleton') == skeleton
    assert not u.EditorAssetLibrary.does_asset_exist(output_path), 'Use a new output asset name'
    end = source.get_play_length() if end is None else end
    assert 0 <= start < end <= source.get_play_length() + .001
    frames = round((end - start) * 60)
    duration = frames / 60.
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_property('extract_root_motion', False)
    options.set_editor_property('incorporate_root_motion_into_pose', True)
    options.set_editor_property('evaluate_curves', False)
    reference = POSE.get_anim_pose_at_time(source, start, options)
    bones = [str(n) for n in POSE.get_bone_names(reference) if not str(n).startswith('VB ')]
    weights = {}
    for bone in bones:
        path = [str(n) for n in u.AnimationLibrary.find_bone_path_to_root(donor, bone)]
        # Both arms, fingers, twist bones, shoulder armour and weapon children
        # remain a coherent donor pose relative to the blended chest.
        weights[bone] = 1. if 'spine_03' in path else 0.
    weights.update(spine_01=.15, spine_02=.45, spine_03=.85)
    tracks = {bone: ([], [], []) for bone in bones}
    times, yaws = [], []
    previous_yaw = None
    yaw_unwrapped = 0.
    for frame in range(frames + 1):
        time = frame / 60.
        base = POSE.get_anim_pose_at_time(source, min(start + time, end), options)
        upper_time = (upper_phase + time) % donor.get_play_length()
        upper = POSE.get_anim_pose_at_time(donor, upper_time, options)
        root = POSE.get_bone_pose(base, 'root', LOCAL)
        yaw = root.rotation.rotator().yaw
        if previous_yaw is not None:
            yaw_unwrapped += (yaw - previous_yaw + 180.) % 360. - 180.
        previous_yaw = yaw
        times.append(time)
        yaws.append(yaw_unwrapped)
        mixed = base
        for bone in bones:
            result = POSE.get_bone_pose(base, bone, LOCAL)
            weight = weights[bone]
            if weight:
                result = mix(result, POSE.get_bone_pose(upper, bone, LOCAL), weight)
            if bone == 'root':
                result = u.Transform()
            mixed = POSE.set_bone_pose(mixed, result, bone, LOCAL)
        # Auxiliary IK bones live outside the deforming arm/leg hierarchy.
        # Reconstruct their final component-space targets after layering.
        for ik, deform in [('ik_hand_gun', 'hand_r'), ('ik_hand_l', 'hand_l'),
                           ('ik_hand_r', 'hand_r'), ('ik_foot_l', 'foot_l'),
                           ('ik_foot_r', 'foot_r')]:
            if ik in tracks and deform in tracks:
                mixed = POSE.set_bone_pose(mixed, POSE.get_bone_pose(
                    mixed, deform, u.AnimPoseSpaces.WORLD), ik, u.AnimPoseSpaces.WORLD)
        for bone in bones:
            result = POSE.get_bone_pose(mixed, bone, LOCAL)
            values = (result.translation, result.rotation, result.scale3d)
            assert all(math.isfinite(v) for v in (result.translation.x, result.translation.y,
                       result.translation.z, result.rotation.x, result.rotation.y,
                       result.rotation.z, result.rotation.w)), (bone, frame)
            for destination, value in zip(tracks[bone], values):
                destination.append(value)
    assert abs(yaws[-1]) > 120, 'Source is not a root-authored reversal turn'
    # Cropping may begin after a tiny authored turn; preserve a complete 180-degree
    # output curve while keeping its timing. Runtime scales it to the desired turn.
    target_yaw = math.copysign(180., yaws[-1])
    yaws = [value * target_yaw / yaws[-1] for value in yaws]
    factory = u.AnimSequenceFactory()
    factory.target_skeleton = skeleton
    factory.preview_skeletal_mesh = u.load_asset('/Game/Combat/Characters/SK_CombatKwang')
    output = u.AssetToolsHelpers.get_asset_tools().create_asset(
        output_path.rsplit('/', 1)[1], output_path.rsplit('/', 1)[0], u.AnimSequence, factory)
    assert output
    controller = output.controller
    controller.open_bracket('Bake sword upper body over official turn', False)
    try:
        controller.set_frame_rate(u.FrameRate(60, 1), False)
        controller.set_number_of_frames(u.FrameNumber(frames), False)
        for bone, values in tracks.items():
            assert controller.add_bone_curve(bone, False)
            assert controller.set_bone_track_keys(bone, *values, should_transact=False), bone
    finally:
        controller.close_bracket(False)
    output.set_editor_property('enable_root_motion', False)
    output.set_editor_property('force_root_lock', True)
    output.set_editor_property('rate_scale', 1.)
    u.AnimationLibrary.add_curve(output, 'PivotYaw')
    u.AnimationLibrary.add_float_curve_keys(output, 'PivotYaw', times, yaws)
    assert u.EditorAssetLibrary.save_loaded_asset(output)
    report = dict(source=source_path, donor=DONOR, output=output_path, frames=frames,
                  duration=duration, source_start=start, source_end=end,
                  yaw_degrees=yaws[-1], upper_phase=upper_phase, weights=weights,
                  root_motion=False, visual_review='pending')
    path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / (output.get_name() + '.json')
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'weights'}))
    return output
