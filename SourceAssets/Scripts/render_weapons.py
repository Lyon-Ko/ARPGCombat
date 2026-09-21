import bpy
from pathlib import Path
from mathutils import Vector
R=Path('D:/UEproject/Combat/SourceAssets')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for i,name in enumerate(['SM_Player_LongSword','SM_Boss_Greatsword']):
    with bpy.data.libraries.load(str(R/'Weapons'/(name+'.blend')),link=False) as (src,dst):dst.objects=[name]
    o=dst.objects[0];bpy.context.collection.objects.link(o);o.location.y=i*.42;o.location.z=.045
    if i:
        for m in o.data.materials:
            if 'Accent' in m.name:
                m.diffuse_color=(1,.18,.02,1)
                p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(1,.18,.02,1);p.inputs['Emission Color'].default_value=(1,.18,.02,1)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=32;sc.render.resolution_x=1400;sc.render.resolution_y=800;sc.render.resolution_percentage=100;sc.world.color=(.1,.1,.1)
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.035));mat=bpy.data.materials.new('Floor');mat.diffuse_color=(.025,.035,.045,1);bpy.context.object.data.materials.append(mat)
for loc,power,size in [((.5,-2,3),900,4),((1,3,2),600,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.size=size;l.rotation_euler=(Vector((.5,.2,0))-l.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.6,-1.6,2.6));cam=bpy.context.object;cam.rotation_euler=(Vector((.6,.2,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.9;sc.camera=cam;sc.render.filepath=str(R/'Weapons/Weapons_Preview.png');bpy.ops.render.render(write_still=True)
