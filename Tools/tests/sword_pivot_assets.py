"""Verify baked lower-body fidelity, sword hierarchy, root and turn curves."""
import json
import math
from pathlib import Path
import unreal as u

pose = u.AnimPoseExtensions
options = u.AnimPoseEvaluationOptions()
options.incorporate_root_motion_into_pose = True
options.extract_root_motion = False
donor = u.load_asset('/Game/Combat/Animations/Native/Kwang/A_Jog_Fwd')
lower = ['pelvis', 'thigh_l', 'calf_l', 'foot_l', 'ball_l', 'thigh_r', 'calf_r', 'foot_r', 'ball_r']
upper = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r',
         'upperarm_r', 'lowerarm_r', 'hand_r', 'weapon_r', 'index_01_l', 'index_01_r',
         'thumb_01_l', 'thumb_01_r', 'upperarm_twist_01_l', 'upperarm_twist_01_r']
report = []
for direction, suffix, start in [('Left', 'L_180_Rfoot', .3), ('Right', 'R_180_Lfoot', .6)]:
    output = u.load_asset('/Game/Combat/Animations/Native/Kwang/A_FreePivot_' + direction)
    source = u.load_asset('/Game/Combat/Animations/Retarget/Raw/RT_M_Neutral_Run_Turn_' + suffix)
    assert output and source
    assert not output.get_editor_property('enable_root_motion')
    errors = dict(lower_cm=0., lower_degrees=0., grip_cm=0., grip_degrees=0., root_cm=0., root_degrees=0.)
    for frame in range(91):
        time = frame / 60.
        result = pose.get_anim_pose_at_time(output, time, options)
        base = pose.get_anim_pose_at_time(source, start + time, options)
        sword = pose.get_anim_pose_at_time(donor, time % donor.get_play_length(), options)
        root = pose.get_bone_pose(result, 'root')
        errors['root_cm'] = max(errors['root_cm'], root.translation.length())
        errors['root_degrees'] = max(errors['root_degrees'], abs(root.rotation.rotator().yaw))
        for group, bones, reference in [('lower', lower, base), ('grip', upper, sword)]:
            for bone in bones:
                actual = pose.get_bone_pose(result, bone)
                expected = pose.get_bone_pose(reference, bone)
                errors[group + '_cm'] = max(errors[group + '_cm'], (actual.translation - expected.translation).length())
                errors[group + '_degrees'] = max(errors[group + '_degrees'],
                    math.degrees(u.MathLibrary.quat_angular_distance(actual.rotation, expected.rotation)))
    times, yaws = u.AnimationLibrary.get_float_keys(output, 'PivotYaw')
    expected_yaw = -180 if direction == 'Left' else 180
    assert abs(yaws[-1] - expected_yaw) < .1
    assert max(errors.values()) < .25, errors
    report.append(dict(direction=direction, sampled_frames=91, yaw=yaws[-1], max_errors=errors, passed=True))
path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / 'SwordPivotAssets.json'
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
