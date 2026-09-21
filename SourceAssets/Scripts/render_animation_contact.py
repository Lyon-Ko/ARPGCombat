import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('D:/UEproject/Combat/SourceAssets');O=R/'Animations/Preview';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'Characters/Player_ArmoredSwordsman.blend'))
old=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH');world=body.matrix_world.copy();body.parent=None;body.matrix_world=world
bpy.data.objects.remove(old,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(R/'Animations/A_Player_Sword_01.fbx'))
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for o in list(bpy.context.scene.objects):
    if o.type=='MESH' and o!=body:bpy.data.objects.remove(o,do_unlink=True)
for m in body.modifiers:
    if m.type=='ARMATURE':m.object=arm
body.parent=arm;body.matrix_world=world
with bpy.data.libraries.load(str(R/'Weapons/SM_Player_LongSword.blend'),link=False) as (src,dst):dst.objects=['SM_Player_LongSword']
sword=dst.objects[0];bpy.context.collection.objects.link(sword)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.render.resolution_x=650;sc.render.resolution_y=650;sc.render.resolution_percentage=100;sc.world.color=(.12,.12,.12)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.04));floor=bpy.context.object;mat=bpy.data.materials.new('Floor');mat.diffuse_color=(.06,.07,.09,1);floor.data.materials.append(mat)
for loc,power in [((-3,-4,5),1300),((3,2,4),1300),((3,-1,3),700)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=4;l.rotation_euler=(Vector((0,0,1))-l.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(3,-6,3));cam=bpy.context.object;cam.rotation_euler=(Vector((0,-.1,1.1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.7;sc.camera=cam
report=[]
# FBX importer preserves 60fps and source keys.
print('FRAME_RANGE',sc.frame_start,sc.frame_end,sc.render.fps,flush=True)
for i,t in enumerate([0,.13,.27,.36]):
    sc.frame_set(round(t*60)+1);bpy.context.view_layer.update();socket=Matrix(((0,1,0,-9),(0,0,1,-2.5),(1,0,0,0),(0,0,0,1)));sword.matrix_world=arm.matrix_world@arm.pose.bones['hand_r'].matrix@socket
    path=O/f'Sword01_{i}.png';sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    report.append({'image':str(path),'time':t,'hand_world':list(arm.matrix_world@arm.pose.bones['hand_r'].head)})
(O/'preview_manifest.json').write_text(json.dumps(report,indent=2))
sc.frame_set(17);bpy.context.view_layer.update();sword.matrix_world=arm.matrix_world@arm.pose.bones['hand_r'].matrix@socket
center=arm.matrix_world@arm.pose.bones['hand_r'].matrix@Vector((-7,-2,0));cam.location=center+Vector((.5,-.7,.4));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.42;sc.render.filepath=str(O/'Grip_Closeup.png');bpy.ops.render.render(write_still=True)
