"""Read native skeletons and clip poses without mutating original Paragon assets."""
import unreal as u
import json
from pathlib import Path

report={}
for hero,mesh_name,clips in [
 ('Kwang','Kwang_GDC',['Idle','PrimaryAttack_A_Slow','PrimaryAttack_B_Slow','PrimaryAttack_C_Slow','PrimaryAttack_D_Slow','PrimaryAttack_Air','Ability_RMB','Ability_R','Ability_R_Intro','Ability_Q_Throw','Stun_Start','Death_Bwd']),
 ('Greystone','Greystone',['Idle','Attack_A_Fast','Attack_B_Fast','Attack_C_Fast','Attack_D_Fast','Jump_Melee','Attack_RMB','Ability_E','Ability_Q','Ability_R','Death'])]:
    root='/Game/Paragon'+hero+'/Characters/Heroes/'+hero
    mesh=u.load_asset(root+'/Meshes/'+mesh_name)
    skeleton=mesh.get_editor_property('skeleton')
    pose=u.AnimPoseExtensions.get_reference_pose(skeleton)
    bones=[str(n) for n in pose.get_bone_names()]
    relevant=[b for b in bones if any(n in b.lower() for n in ['weapon','sword','blade','hand_r','root'])]
    def transform(t):
        return {'p':list(t.translation.to_tuple()),'r':list(t.rotation.rotator().to_tuple())}
    record={'mesh':mesh.get_path_name(),'bones':bones,'reference':{b:transform(pose.get_bone_pose(b,u.AnimPoseSpaces.WORLD)) for b in relevant},'sockets':{},'clips':{}}
    for n in pose.get_socket_names(): record['sockets'][str(n)]=transform(u.AnimPoseExtensions.get_socket_pose(pose,n,u.AnimPoseSpaces.WORLD))
    for name in clips:
        clip=u.load_asset(root+'/Animations/'+name)
        if not clip: continue
        length=clip.get_editor_property('sequence_length')
        entry={'duration':length,'root_motion':clip.get_editor_property('enable_root_motion'),'notifies':[str(e) for e in u.AnimationLibrary.get_animation_notify_events(clip)],'samples':[]}
        for fraction in [0,.15,.25,.35,.45,.55,.65,.8,.95]:
            time=length*fraction
            animated=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,u.AnimPoseEvaluationOptions())
            entry['samples'].append({'t':time,'bones':{b:transform(animated.get_bone_pose(b,u.AnimPoseSpaces.WORLD)) for b in relevant}})
        record['clips'][name]=entry
    report[hero]=record
out=Path(u.Paths.project_saved_dir())/'Acceptance/NativeAnimationInventory.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NATIVE_INVENTORY',str(out))
for hero,data in report.items(): print(hero,'weapon bones',list(data['reference']),'sockets',list(data['sockets']),'clips',[(n,round(c['duration'],3)) for n,c in data['clips'].items()])
