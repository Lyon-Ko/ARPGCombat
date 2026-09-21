import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('D:/UEproject/Combat/SourceAssets');SCALE=Matrix.Scale(.01,4)
def mat(name,color,metal=0,rough=.4):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if 'Accent' in name:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=2
    return m
def reset():bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mesh(name,verts,faces,material,bone=None):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.matrix_world=SCALE;o.data.materials.append(material)
    if bone:
        o.vertex_groups.new(name=bone).add(list(range(len(verts))),1,'REPLACE');o.parent=arm;o.matrix_world=SCALE
        mod=o.modifiers.new('Skeleton','ARMATURE');mod.object=arm
    parts.append(o)
    return o
def box(name,c,dim,material,bone):
    x,y,z=c;a,b,d=[v/2 for v in dim];v=[(x+i*a,y+j*b,z+k*d) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    o=mesh(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material,bone);return o
def rings(name,levels,material,bone,n=24):
    v=[]
    for z,cx,cy,rx,ry in levels:
        for j in range(n):a=2*math.pi*j/n;v.append((cx+math.cos(a)*rx,cy+math.sin(a)*ry,z))
    f=[]
    for k in range(len(levels)-1):
        for j in range(n):a=k*n+j;b=k*n+(j+1)%n;f.append((a,b,b+n,a+n))
    f.extend([tuple(reversed(range(n))),tuple(range((len(levels)-1)*n,len(levels)*n))]);return mesh(name,v,f,material,bone)
def tube(name,a,b,radii,material,bone,n=16):
    a=Vector(a);b=Vector(b);d=(b-a).normalized();x=d.cross(Vector((0,1,0))).normalized();y=d.cross(x).normalized();v=[]
    for t,rx,ry in radii:
        c=a.lerp(b,t)
        for j in range(n):q=2*math.pi*j/n;v.append(tuple(c+x*math.cos(q)*rx+y*math.sin(q)*ry))
    f=[]
    for k in range(len(radii)-1):
        for j in range(n):a1=k*n+j;b1=k*n+(j+1)%n;f.append((a1,b1,b1+n,a1+n))
    f.extend([tuple(reversed(range(n))),tuple(range((len(radii)-1)*n,len(radii)*n))]);return mesh(name,v,f,material,bone)
def stud(c,bone):rings('Rivet',[(c[2]-.6,c[0],c[1],.65,.65),(c[2],c[0],c[1],.9,.9),(c[2]+.6,c[0],c[1],.45,.45)],trim,bone,8)
def finish_mesh(name):
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    for f in o.data.polygons:f.use_smooth=True
    bevel=o.modifiers.new('Forged bevels','BEVEL');bevel.width=.25;bevel.segments=2
    try:bpy.ops.object.modifier_apply(modifier=bevel.name)
    except Exception:pass
    return o
def export(path,objects,anim=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,axis_forward='-Y',axis_up='Z',use_armature_deform_only=False,bake_anim=anim,apply_unit_scale=True,armature_nodetype='NULL',mesh_smooth_type='FACE')
def setup_render(path,side=False):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.render.resolution_x=900;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
    sc.world.color=(.08,.08,.1)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));floor=bpy.context.object;floor.name='RenderFloor';floor.data.materials.append(mat('PreviewFloor',(.035,.045,.065),.2,.4))
    for name,loc,power,size,col in [('Key',(-3,-4,5),1000,4,(.8,.9,1)),('Rim',(3,2,4),1500,3,(1,.7,.4)),('Fill',(3,-2,2),500,3,(.4,.65,1))]:
        bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.name=name;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.data.color=col;l.rotation_euler=(Vector((0,0,1))-l.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(3.2,-.6,1.5) if side else (2.25,-4.2,2.05));cam=bpy.context.object;cam.rotation_euler=(Vector((0,-.02,.99))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.26;sc.camera=cam;sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
for boss in [False,True]:
    reset();bpy.ops.import_scene.fbx(filepath='D:/UEproject/UE-ANIMATION/Exchange/SKM_Manny_Simple.fbx');arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');w=arm.matrix_world.copy();arm.parent=None;arm.matrix_world=w;arm.name='root';arm.animation_data_clear()
    body=next(o for o in bpy.context.scene.objects if o.type=='MESH');w=body.matrix_world.copy();body.parent=arm;body.matrix_world=w
    for o in list(bpy.context.scene.objects):
        if o not in [arm,body]:bpy.data.objects.remove(o,do_unlink=True)
    prefix='Boss' if boss else 'Player';metal=mat(prefix+'_Metal',(.055,.065,.072) if boss else (.04,.095,.15),.85,.3);trim=mat(prefix+'_Trim',(.46,.29,.10) if boss else (.22,.32,.4),.8,.28);cloth=mat(prefix+'_Cloth',(.065,.019,.013) if boss else (.014,.028,.05),0,.85);under=mat(prefix+'_Undersuit',(.023,.027,.032),.25,.65);accent=mat(prefix+'_Accent',(1,.19,.018) if boss else (.015,.6,.85),.35,.22)
    body.data.materials.clear();body.data.materials.append(under)
    for p in body.data.polygons:p.material_index=0
    parts=[body];wide=1.13 if boss else 1
    rings('Cuirass',[(105,0,0,15*wide,12),(114,0,0,17*wide,13),(133,0,0,24*wide,15),(143,0,0,23*wide,14),(149,0,0,15*wide,11)],metal,'spine_04')
    rings('CuirassLowerBand',[(108,0,0,16*wide,12.7),(111,0,0,16.6*wide,13)],trim,'spine_04')
    for sign in [-1,1]:
        verts=[(0,-15.4,139),(sign*21*wide,-11.5,139),(sign*16*wide,-12.5,120),(0,-14.2,115)]
        mesh('BreastplateFacet',verts,[(0,1,2,3)],trim,'spine_04')
        for z in [119,126,133]:stud((sign*15*wide,-14,z),'spine_04')
    mesh('ChestEmblem',[(-3,-16,138),(3,-16,138),(0,-16.3,127),(0,-17,133)],[(0,1,3),(1,2,3),(2,0,3)],accent,'spine_04')
    for j in range(3):rings('AbdominalLame',[(97+j*4,0,0,16.2*wide+j*.7,12.7),(100+j*4,0,0,17*wide+j*.7,13.2)],metal if j%2==0 else trim,'spine_01')
    rings('Gorget',[(148,0,0,11,10),(152,0,0,10,9),(156,0,0,8,8)],trim,'neck_01')
    rings('FullHelm',[(157,0,-.4,8,9.2),(161,0,-.6,10.1,11.5),(168,0,-.7,11.1,12),(174,0,0,10.4,11),(180,0,0,6.5,8),(183,0,0,1.2,3)],metal,'head')
    box('VisorShadow',(0,-12.1,168.4),(17.5,.65,3.4),under,'head')
    box('VisorLight',(0,-12.5,168.5),(15.7,.28,.9),accent,'head')
    mesh('NasalGuard',[(-1,-12.9,173),(1,-12.9,173),(1.6,-13.8,162),(-1.6,-13.8,162)],[(0,1,2,3)],trim,'head')
    for sign in [-1,1]:
        mesh('CheekGuard',[(sign*2,-13.3,166),(sign*8,-11.8,166),(sign*7,-10.8,158),(sign*2.5,-12,160)],[(0,1,2,3)],metal,'head')
        for j in range(3):box('Breather',(sign*(3.5+j*1.3),-12.3,162.8),(0.6,.45,2),under,'head')
    tube('HelmCrest',(0,1,176),(0,-1,187 if boss else 184),[(0,3,8),(.8,1.8,6),(1,.4,2)],trim,'head')
    for side,sign in [('r',-1),('l',1)]:
        bones=arm.data.bones
        a=bones['upperarm_'+side].head_local;b=bones['lowerarm_'+side].head_local;c=bones['hand_'+side].head_local
        for j in range(3 if boss else 2):
            start=a.lerp(b,.06+j*.13);end=a.lerp(b,.27+j*.13)
            tube('LayeredPauldron',start,end,[(0,13.8*wide-j*.8,13*wide-j*.7),(.7,14.2*wide-j*.8,13.8*wide-j*.7),(1,12*wide-j*.8,12.3*wide-j*.7)],metal if j%2==0 else trim,'upperarm_'+side)
        tube('UpperArmPlate',a,b,[(.46,8.7,8.2),(.76,8,7.5),(.87,7.5,7)],metal,'upperarm_'+side)
        tube('Vambrace',b,c,[(.1,8.3,7.7),(.24,8.9,8),(.72,7.2,6.7),(.9,6.4,6)],metal,'lowerarm_'+side)
        tube('WristBand',b,c,[(.83,6.8,6.4),(.93,6.6,6.1)],trim,'lowerarm_'+side)
        a=bones['thigh_'+side].head_local;b=bones['calf_'+side].head_local;c=bones['foot_'+side].head_local
        tube('Cuisses',a,b,[(.14,11.3,11.4),(.34,11.4,11),(.76,9.4,9.7),(.88,9,9)],metal,'thigh_'+side)
        rings('KneeCop',[(b.z-6,b.x,b.y-2,9,10),(b.z,b.x,b.y-2,11,12),(b.z+6,b.x,b.y-2,9,10)],trim,'calf_'+side)
        tube('Greave',b,c,[(.17,9,9),(.28,9.7,9.2),(.68,7.5,7),(.95,6.5,6)],metal,'calf_'+side)
        tube('GreaveTrim',b,c,[(.22,9.9,9.4),(.28,10,9.5)],trim,'calf_'+side)
        box('Sabatons',(c.x,-6,6),(14,27,9),metal,'foot_'+side)
        for j in range(3):box('ToeLames',(c.x,-13+j*5,10),(13.8,1.2,1),trim,'foot_'+side)
        mesh('FauldTasset',[(sign*3,-14,99),(sign*17,-12,99),(sign*21,-12,77),(sign*5,-16,76)],[(0,1,2,3)],metal,'thigh_'+side)
        mesh('TassetTrim',[(sign*5,-16.3,78),(sign*21,-12.3,79),(sign*21,-12.3,76),(sign*5,-16.3,75)],[(0,1,2,3)],trim,'thigh_'+side)
    # Scalloped cloth cape and split front tabard, fully skinned to torso/pelvis.
    cape_y=19 if boss else 17
    for j in range(6):
        x0=-22+j*44/6;x1=-22+(j+1)*44/6
        mesh('CapePanel',[(x0,10,146),(x1,10,146),(x1*1.15,cape_y+7,68+(j%2)*4),(x0*1.15,cape_y+7,68+((j+1)%2)*4)],[(0,1,2,3)],cloth,'spine_03')
    for sign in [-1,1]:mesh('Tabard',[(sign*.8,-14.5,101),(sign*8,-14.5,101),(sign*9,-17,64),(sign*1.3,-17,67)],[(0,1,2,3)],cloth,'pelvis')
    character=finish_mesh('SK_'+prefix+'_ArmoredSwordsman');export(R/'Characters'/(character.name+'.fbx'),[arm,character]);bpy.ops.wm.save_as_mainfile(filepath=str(R/'Characters'/(prefix+'_ArmoredSwordsman.blend')))
    setup_render(R/'Characters'/(prefix+'_Front.png'));bpy.context.scene.camera.location=(3.4,-.15,1.8);bpy.context.scene.camera.rotation_euler=(Vector((0,0,1))-bpy.context.scene.camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.render.filepath=str(R/'Characters'/(prefix+'_Side.png'));bpy.ops.render.render(write_still=True)
    print('CHARACTER_COMPLETE',prefix,flush=True)
reset();parts=[];arm=None
blade=mat('Sword_Blade',(.42,.48,.55),.93,.2);trim=mat('Sword_Trim',(.3,.22,.10),.8,.25);grip=mat('Sword_Grip',(.025,.02,.018),0,.7);accent=mat('Sword_Accent',(.02,.65,.9),.5,.22)
for boss in [False,True]:
    if parts:
        reset();parts=[]
    length=137 if boss else 106;width=5.7 if boss else 3.6
    # Diamond cross section, sharpened edge geometry, tapered tip. Origin is grip center.
    v=[]
    for x,w,t in [(12,width,1.2),(length-22,width*.82,.9),(length,0,.05)]:v.extend([(x,-w,0),(x,0,t),(x,w,0),(x,0,-t)])
    faces=[(0,3,2,1)]
    for k in range(2):
        for j in range(4):faces.append((k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j))
    mesh('Blade',v,faces,blade)
    box('Fuller',(length*.43,0,1.02),(length*.6,.9,.12),trim,None)
    box('Crossguard',(9,0,0),(3,34 if boss else 27,4),trim,None)
    for sign in [-1,1]:mesh('GuardWing',[(7,sign*10,-1.8),(9,sign*18,-1.8),(15,sign*17,-1.8),(11,sign*9,-1.8),(7,sign*10,1.8),(9,sign*18,1.8),(15,sign*17,1.8),(11,sign*9,1.8)],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],trim)
    tube('LeatherGrip',(-16,0,0),(7,0,0),[(0,2.2,2.2),(1,2,2)],grip,None,12)
    for j in range(9):tube('GripBinding',(-15+j*2.4,0,0),(-14.3+j*2.4,0,0),[(0,2.35,2.35),(1,2.35,2.35)],trim,None,12)
    tube('Pommel',(-21,0,0),(-16,0,0),[(0,1.6,1.6),(.4,4.4,4.4),(.75,4.4,4.4),(1,2.3,2.3)],trim,None,12)
    box('GuardInlay',(10,0,2.2),(3,5,.5),accent,None)
    sword=finish_mesh('SM_Boss_Greatsword' if boss else 'SM_Player_LongSword');export(R/'Weapons'/(sword.name+'.fbx'),[sword]);bpy.ops.wm.save_as_mainfile(filepath=str(R/'Weapons'/(sword.name+'.blend')))
(R/'Characters/character_manifest.json').write_text(json.dumps({'skeleton':'SK_Mannequin, source SKM_Manny_Simple; 88 Blender bones plus root armature node','units':'centimeters in FBX; modeled in armature local cm; world scale 0.01','player':'SK_Player_ArmoredSwordsman.fbx','boss':'SK_Boss_ArmoredSwordsman.fbx','boss_recommended_actor_scale':1.18,'materials':['Metal','Trim','Cloth','Undersuit','Accent'],'armor':'Original authored mesh, rigid weights per anatomical plate on Manny skeleton','weapons':{'SM_Player_LongSword.fbx':{'blade_axis':'+X','socket':'hand_r','socket_location_cm':[-9,-2.5,0],'socket_rotation_matrix_rows':[[0,1,0],[0,0,1],[1,0,0]],'blade_start_cm':12,'blade_tip_cm':106},'SM_Boss_Greatsword.fbx':{'blade_axis':'+X','socket':'hand_r','socket_location_cm':[-9,-2.5,0],'socket_rotation_matrix_rows':[[0,1,0],[0,0,1],[1,0,0]],'blade_start_cm':12,'blade_tip_cm':137}}},indent=2))
