"""Remove 24 leading frames from the baked left pivot, preserving remaining poses."""
import json
from pathlib import Path
import shutil
import unreal as u

root = '/Game/Combat/Animations/Native/Kwang/'
sequence = u.load_asset(root + 'A_FreePivot_Left')
montage = u.load_asset(root + 'AM_FreePivot_Left')
assert sequence and montage
assert abs(sequence.get_play_length() - 1.5) < .001, 'Expected original 1.5-second clip; do not trim twice'
assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
project = Path(u.Paths.project_dir())
backup = project / 'Saved/Backups/LeftPivotTrim'
backup.mkdir(parents=True, exist_ok=True)
for name in ('A_FreePivot_Left', 'AM_FreePivot_Left'):
    source = project / ('Content/Combat/Animations/Native/Kwang/' + name + '.uasset')
    destination = backup / source.name
    assert not destination.exists(), 'Backup exists; inspect before repeating'
    shutil.copy2(source, destination)

pose = u.AnimPoseExtensions
options = u.AnimPoseEvaluationOptions()
options.extract_root_motion = False
options.incorporate_root_motion_into_pose = True
frames = 66
poses = [pose.get_anim_pose_at_time(sequence, .4 + frame / 60., options) for frame in range(frames + 1)]
bones = [str(n) for n in pose.get_bone_names(poses[0]) if not str(n).startswith('VB ')]
tracks = {bone: [pose.get_bone_pose(p, bone) for p in poses] for bone in bones}
old_times, old_yaws = u.AnimationLibrary.get_float_keys(sequence, 'PivotYaw')
assert len(old_times) == 91 and abs(old_times[24] - .4) < .001
offset = old_yaws[24]
# Preserve the curve's shape while making the cropped start zero and end -180.
yaws = [(value - offset) * (-180. / (old_yaws[-1] - offset)) for value in old_yaws[24:]]
controller = sequence.controller
controller.open_bracket('Trim left pivot leading 0.4 seconds', True)
try:
    controller.set_number_of_frames(u.FrameNumber(frames), True)
    for bone, keys in tracks.items():
        assert controller.set_bone_track_keys(bone, [v.translation for v in keys],
            [v.rotation for v in keys], [v.scale3d for v in keys], True)
finally:
    controller.close_bracket(True)
u.AnimationLibrary.remove_curve(sequence, 'PivotYaw')
u.AnimationLibrary.add_curve(sequence, 'PivotYaw')
u.AnimationLibrary.add_float_curve_keys(sequence, 'PivotYaw', [i / 60. for i in range(frames + 1)], yaws)
assert u.EditorAssetLibrary.save_loaded_asset(sequence)

tracks = list(montage.get_editor_property('slot_anim_tracks'))
track = tracks[0].get_editor_property('anim_track')
segments = list(track.get_editor_property('anim_segments'))
assert len(segments) == 1 and segments[0].get_editor_property('anim_reference') == sequence
segments[0].set_editor_property('anim_start_time', 0.)
segments[0].set_editor_property('anim_end_time', sequence.get_play_length())
track.set_editor_property('anim_segments', segments)
tracks[0].set_editor_property('anim_track', track)
montage.set_editor_property('slot_anim_tracks', tracks)
assert u.CombatEditorLibrary.rebuild_montage(montage)
assert abs(montage.get_play_length() - 1.1) < .001

report = dict(removed_seconds=.4, removed_frames=24, new_duration=sequence.get_play_length(),
    montage_duration=montage.get_play_length(), source_start=.7, source_end=1.8,
    upper_phase=.4, yaw_start=yaws[0], yaw_end=yaws[-1], backup=str(backup))
(project / 'Saved/Acceptance/LeftPivotTrim.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
metadata_path = project / 'Saved/Acceptance/A_FreePivot_Left.json'
if metadata_path.exists():
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata.update(frames=66, duration=1.1, source_start=.7, source_end=1.8,
                    upper_phase=.4, yaw_degrees=-180., leading_frames_trimmed=24)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
print(json.dumps(report))
