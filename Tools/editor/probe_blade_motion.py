import unreal as u
import json
from pathlib import Path
report={}
for hero,clips,bone,tip in [('Kwang',['PrimaryAttack_A_Slow','PrimaryAttack_B_Slow','PrimaryAttack_C_Slow','PrimaryAttack_D_Slow','PrimaryAttack_Air','Ability_RMB','Ability_R','Ability_R_Intro','Ability_Q_Throw'],'weapon_r',u.Vector(0,-147,0)),('Greystone',['Attack_A_Fast','Attack_B_Fast','Attack_C_Fast','Attack_D_Fast','Jump_Melee','Ability_E','Ability_Q','Ability_R'],'sword_top',u.Vector(0,0,78))]:
    report[hero]={}
    for name in clips:
        clip=u.load_asset('/Game/Paragon'+hero+'/Characters/Heroes/'+hero+'/Animations/'+name)
        duration=clip.get_editor_property('sequence_length')
        samples=[]
        for i in range(21):
            time=duration*i/20
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,u.AnimPoseEvaluationOptions())
            pos=pose.get_bone_pose(bone,u.AnimPoseSpaces.WORLD).transform_location(tip)
            samples.append({'t':round(time,3),'tip':[round(v,1) for v in pos.to_tuple()]})
        report[hero][name]=samples
out=Path(u.Paths.project_saved_dir())/'Acceptance/NativeBladeMotion.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
