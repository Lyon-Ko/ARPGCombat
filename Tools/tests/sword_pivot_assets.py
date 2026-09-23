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
upper = ['clavicle_l', 'clavicle_r', 'weapon_r', 'index_01_l', 'index_01_r',
         'thumb_01_l', 'thumb_01_r', 'upperarm_twist_01_l', 'upperarm_twist_01_r']
report = []
for direction, suffix, start, upper_phase in [('Left', 'L_180_Rfoot', .7, .4), ('Right', 'R_180_Lfoot', .6, 0.)]:
    output = u.load_asset('/Game/Combat/Animations/Native/Kwang/A_FreePivot_' + direction)
    source = u.load_asset('/Game/Combat/Animations/Retarget/Raw/RT_M_Neutral_Run_Turn_' + suffix)
    assert output and source
    assert not output.get_editor_property('enable_root_motion')
    errors = dict(lower_cm=0., lower_degrees=0., grip_cm=0., grip_degrees=0., root_cm=0., root_degrees=0.)
    errors['matched_tip_cm'] = 0.
    frame_count = round(output.get_play_length() * 60) + 1
    for frame in range(frame_count):
        time = frame / 60.
        result = pose.get_anim_pose_at_time(output, time, options)
        base = pose.get_anim_pose_at_time(source, start + time, options)
        sword = pose.get_anim_pose_at_time(donor, (upper_phase + time) % donor.get_play_length(), options)
        root = pose.get_bone_pose(result, 'root')
        errors['root_cm'] = max(errors['root_cm'], root.translation.length())
        errors['root_degrees'] = max(errors['root_degrees'], abs(root.rotation.rotator().yaw))
        if time >= output.get_play_length() - .2 - .001:
            actual_weapon = pose.get_bone_pose(result, 'weapon_r', u.AnimPoseSpaces.WORLD)
            expected_weapon = pose.get_bone_pose(sword, 'weapon_r', u.AnimPoseSpaces.WORLD)
            tip = u.Vector(0, -147, 0)
            errors['matched_tip_cm'] = max(errors['matched_tip_cm'],
                (u.MathLibrary.transform_location(actual_weapon, tip) - u.MathLibrary.transform_location(expected_weapon, tip)).length())
        if direction == 'Left' and time >= .75:
            for side in ('r', 'l'):
                shoulder, elbow, wrist = [pose.get_bone_pose(result, n+'_'+side, u.AnimPoseSpaces.WORLD).translation
                                          for n in ('upperarm','lowerarm','hand')]
                reach = (wrist-shoulder).length()/((elbow-shoulder).length()+(wrist-elbow).length())
                assert reach < .93, ('elbow_near_lock', time, side, reach)
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
    assert max(v for k,v in errors.items() if k != 'matched_tip_cm') < .25, errors
    assert errors['matched_tip_cm'] < 2., errors
    report.append(dict(direction=direction, sampled_frames=frame_count, yaw=yaws[-1], max_errors=errors, passed=True))
path = Path(u.Paths.project_saved_dir()) / 'Acceptance' / 'SwordPivotAssets.json'
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
