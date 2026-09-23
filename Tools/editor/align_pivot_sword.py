"""Bake a late-pivot two-bone arm correction to the matching Jog sword phase.

Lower body, pelvis, root and PivotYaw are preserved. The spine recovers to
the donor pose before the arm correction. Call align(write=True)
only after checking the dry-run metrics. Run outside PIE.
"""
import json
import math
import shutil
from pathlib import Path
import unreal as u

P = u.AnimPoseExtensions
CS = u.AnimPoseSpaces.WORLD
ROOT = '/Game/Combat/Animations/Native/Kwang/'


def smooth(value):
    x = max(0., min(1., value))
    return x*x*x*(10. + x*(-15. + 6.*x))


def arm(pose, donor, side, alpha, soft_reach=False):
    upper, lower, hand = ['upperarm_'+side, 'lowerarm_'+side, 'hand_'+side]
    a, b, c = [P.get_bone_pose(pose, bone, CS) for bone in (upper, lower, hand)]
    target = P.get_bone_pose(donor, hand, CS)
    end = c.translation * (1-alpha) + target.translation * alpha
    rotation = u.MathLibrary.quat_slerp(c.rotation, target.rotation, alpha)
    length_a = (b.translation-a.translation).length()
    length_b = (c.translation-b.translation).length()
    delta = end-a.translation
    direction = delta.normal()
    distance = max(abs(length_a-length_b)+.001, min(delta.length(), length_a+length_b-.001))
    if soft_reach:
        # Smoothly cap reach at 90% of limb length. The quadratic shoulder of
        # the limit has continuous slope, avoiding a snap at the reach boundary.
        total = length_a+length_b
        low, width = .87*total, .03*total
        excess = max(0., min(distance-low, 2*width))
        limited = distance if distance <= low else low+excess-excess*excess/(4*width)
        distance = distance*(1-alpha)+limited*alpha
    end = a.translation + direction*distance
    desired_elbow = b.translation*(1-alpha) + P.get_bone_pose(donor, lower, CS).translation*alpha
    pole = desired_elbow-a.translation
    pole = pole-direction*pole.dot(direction)
    if pole.length() < .01:
        pole = (b.translation-a.translation)-direction*(b.translation-a.translation).dot(direction)
    pole = pole.normal()
    along = (distance*distance+length_a*length_a-length_b*length_b)/(2*distance)
    height = math.sqrt(max(0., length_a*length_a-along*along))
    elbow = a.translation+direction*along+pole*height
    correction = u.MathLibrary.quat_find_between_vectors(b.translation-a.translation, elbow-a.translation)
    a.rotation = u.MathLibrary.multiply_quat_quat(correction, a.rotation)
    pose = P.set_bone_pose(pose, a, upper, CS)
    b, c = [P.get_bone_pose(pose, bone, CS) for bone in (lower, hand)]
    correction = u.MathLibrary.quat_find_between_vectors(c.translation-b.translation, end-b.translation)
    b.rotation = u.MathLibrary.multiply_quat_quat(correction, b.rotation)
    pose = P.set_bone_pose(pose, b, lower, CS)
    c = P.get_bone_pose(pose, hand, CS)
    c.rotation = rotation
    return P.set_bone_pose(pose, c, hand, CS)


def tip(pose):
    weapon = P.get_bone_pose(pose, 'weapon_r', CS)
    return u.MathLibrary.transform_location(weapon, u.Vector(0, -147, 0))


def align(write=False, source_root=ROOT, sides=('Left','Right')):
    assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
    donor = u.load_asset(ROOT+'A_Jog_Fwd')
    options = u.AnimPoseEvaluationOptions()
    options.extract_root_motion = False
    options.incorporate_root_motion_into_pose = True
    reports = []
    for side, offset in [('Left', .4), ('Right', 0.)]:
        if side not in sides:
            continue
        sequence = u.load_asset(ROOT+'A_FreePivot_'+side)
        source = u.load_asset(source_root+'A_FreePivot_'+side)
        assert source and not u.AnimationLibrary.does_curve_exist(source, 'PivotUpperPhase', u.RawCurveTrackTypes.RCT_FLOAT), 'Use the original pre-correction source'
        length = sequence.get_play_length()
        count = round(length*60)+1
        original = [P.get_anim_pose_at_time(source, i/60., options) for i in range(count)]
        bones = [str(n) for n in P.get_bone_names(original[0]) if not str(n).startswith('VB ')]
        keys = {bone: [] for bone in bones}
        metrics = []
        for frame, pose in enumerate(original):
            time = frame/60.
            running = P.get_anim_pose_at_time(donor, (offset+time)%donor.get_play_length(), options)
            before = (tip(pose)-tip(running)).length()
            # Fully aligned by the final .25 s, before the current .20 s fade.
            alpha = smooth((time-(length-.5))/.25)
            if alpha > 0:
                for spine in ('spine_01','spine_02','spine_03'):
                    current = P.get_bone_pose(pose, spine)
                    target = P.get_bone_pose(running, spine)
                    current.rotation = u.MathLibrary.quat_slerp(current.rotation, target.rotation, alpha)
                    current.translation = current.translation*(1-alpha)+target.translation*alpha
                    pose = P.set_bone_pose(pose,current,spine)
                for hand in ('r', 'l'):
                    pose = arm(pose, running, hand, alpha, soft_reach=(side == 'Left'))
                for ik, deform in [('ik_hand_gun','hand_r'), ('ik_hand_l','hand_l'), ('ik_hand_r','hand_r')]:
                    pose = P.set_bone_pose(pose, P.get_bone_pose(pose, deform, CS), ik, CS)
            after = (tip(pose)-tip(running)).length()
            metrics.append(dict(time=time, alpha=alpha, before_tip_cm=before, after_tip_cm=after))
            for bone in bones:
                keys[bone].append(P.get_bone_pose(pose,bone))
        full = [m for m in metrics if m['time'] >= length-.2-.0001]
        report = dict(side=side, max_aligned_tip_error_cm=max(m['after_tip_cm'] for m in full),
                      before_max_tip_error_cm=max(m['before_tip_cm'] for m in full), samples=metrics)
        reports.append(report)
        if write:
            assert report['max_aligned_tip_error_cm'] < 5., report
            project = Path(u.Paths.project_dir())
            backup = project/'Saved/Backups/PivotSwordPhase'
            backup.mkdir(parents=True, exist_ok=True)
            filename = 'A_FreePivot_'+side+'.uasset'
            if not (backup/filename).exists():
                shutil.copy2(project/'Content/Combat/Animations/Native/Kwang'/filename, backup/filename)
            controller = sequence.controller
            controller.open_bracket('Match pivot sword to running phase', True)
            try:
                for bone, track in keys.items():
                    assert controller.set_bone_track_keys(bone, [v.translation for v in track],
                        [v.rotation for v in track], [v.scale3d for v in track], True)
            finally:
                controller.close_bracket(True)
            for curve, values in [('PivotUpperPhase',[(offset+i/60.)/donor.get_play_length() for i in range(count)]),
                                  ('PivotSwordMatch',[m['alpha'] for m in metrics])]:
                if u.AnimationLibrary.does_curve_exist(sequence,curve,u.RawCurveTrackTypes.RCT_FLOAT):
                    u.AnimationLibrary.remove_curve(sequence,curve)
                u.AnimationLibrary.add_curve(sequence,curve)
                u.AnimationLibrary.add_float_curve_keys(sequence,curve,[i/60. for i in range(count)],values)
            assert u.EditorAssetLibrary.save_loaded_asset(sequence)
    path = Path(u.Paths.project_saved_dir())/'Acceptance/PivotSwordPhase.json'
    path.write_text(json.dumps(dict(written=write, clips=reports),indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k!='samples'} for r in reports]))
    return reports
