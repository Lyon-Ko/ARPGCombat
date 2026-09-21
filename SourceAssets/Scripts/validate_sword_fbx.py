import bpy,json
from pathlib import Path
R=Path('D:/UEproject/Combat/SourceAssets')
def clear():bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
clear();bpy.ops.import_scene.fbx(filepath='D:/UEproject/UE-ANIMATION/Exchange/SKM_Manny_Simple.fbx')
a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');reference={b.name:b.head_local.copy() for b in a.data.bones}
report=[]
for path in sorted((R/'Animations').glob('*.fbx')):
    clear();bpy.ops.import_scene.fbx(filepath=str(path));a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    assert set(reference)==set(b.name for b in a.data.bones),path.name
    err=max((reference[b.name]-b.head_local).length for b in a.data.bones)
    assert err<.005,(path.name,err)
    meta=json.loads(path.with_suffix('.json').read_text());action=a.animation_data.action;assert action
    positions=[]
    for f in [1,round(meta['frames']*.25),round(meta['frames']*.5),meta['frames']]:
        bpy.context.scene.frame_set(f);bpy.context.view_layer.update();positions.append(a.pose.bones['hand_r'].head.copy())
    motion=max((x-y).length for x in positions for y in positions)
    assert motion>.2,(path.name,'no motion',motion)
    report.append({'file':path.name,'bones':len(reference),'max_rest_head_error_cm':err,'sample_hand_motion_cm':motion,'fbx_bytes':path.stat().st_size,'pass':True})
(R/'Animations/fbx_validation.json').write_text(json.dumps(report,indent=2));print('VALIDATION_PASSED',len(report))
