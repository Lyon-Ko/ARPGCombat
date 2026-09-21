import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/UEproject/Combat/SourceAssets')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath='D:/UEproject/UE-ANIMATION/Exchange/SKM_Manny_Simple.fbx')
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
world=arm.matrix_world.copy();arm.parent=None;arm.matrix_world=world
arm.name='root'; arm.animation_data_clear()
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
body_world=body.matrix_world.copy();body.parent=arm;body.matrix_world=body_world
for o in list(bpy.context.scene.objects):
    if o not in [arm,body]:bpy.data.objects.remove(o,do_unlink=True)
scene=bpy.context.scene;scene.render.fps=60
P=arm.pose.bones
for p in P:p.rotation_mode='QUATERNION'
rest={p.name:p.matrix_basis.copy() for p in P}
def update():bpy.context.view_layer.update()
def rotate_world(n,axis,angle):
    p=P[n];pivot=p.head.copy();p.matrix=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(angle),4,axis)@Matrix.Translation(-pivot)@p.matrix;update()
def aim(n,child,target):
    p=P[n];h=p.head.copy();old=P[child].head-h;new=Vector(target)-h
    if old.length<.001 or new.length<.001:return
    q=old.normalized().rotation_difference(new.normalized());p.matrix=Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@p.matrix;update()
def limb(a,b,c,target,pole):
    h=P[a].head.copy();mid=P[b].head.copy();end=P[c].head.copy();target=Vector(target)
    l1=(mid-h).length;l2=(end-mid).length;v=target-h;d=min(v.length,l1+l2-.1);d=max(d,abs(l1-l2)+.1);v.normalize()
    pol=Vector(pole)-h;pol=pol-v*pol.dot(v)
    if pol.length<.001:pol=Vector((1,0,0))
    pol.normalize();along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along));elbow=h+v*along+pol*height
    aim(a,b,elbow);aim(b,c,h+v*d)
def hand_direction(n,d):
    z=Vector(d).normalized();x=Vector((0,0,1)).cross(z)
    if x.length<.1:x=Vector((1,0,0))
    x.normalize();y=z.cross(x).normalized();m=Matrix((x,y,z)).transposed().to_4x4();m.translation=P[n].head;P[n].matrix=m;update()
def finger_tip(n,previous,target):
    p=P[n];h=p.head.copy();v=(h-P[previous].head).normalized();d=(Vector(target)-h).normalized();q=v.rotation_difference(d);p.matrix=Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@p.matrix;update()
def grip_right():
    h=P['hand_r'].matrix.copy();inv=h.inverted()
    for finger in ['index','middle','ring','pinky']:
        a,b,c=[f'{finger}_{i}_r' for i in ['01','02','03']];z=(inv@P[a].head).z
        aim(a,b,h@Vector((-12,-2.2,z)));aim(b,c,h@Vector((-10.6,-5.0,z)));finger_tip(c,b,h@Vector((-8,-5.3,z)))
    aim('thumb_01_r','thumb_02_r',h@Vector((-5,-3,5.0)))
    aim('thumb_02_r','thumb_03_r',h@Vector((-7.6,-5,2.8)))
    finger_tip('thumb_03_r','thumb_02_r',h@Vector((-9,-5,1)))
BASE=dict(r=(-24,-36,125),l=(21,-28,130),d=(.05,-.8,.6),tw=0,bend=4,hip=(0,0,-5),fr=(-15,-14,8),fl=(17,18,8))
def pose(**kwargs):q=BASE.copy();q.update(kwargs);return q
guard=pose()
high=pose(r=(-22,-5,165),l=(17,-26,142),d=(-.15,.25,.96),tw=-32,bend=-7,hip=(-3,4,-9),fr=(-16,3,8),fl=(18,27,8))
right=pose(r=(-45,-1,135),l=(13,-26,129),d=(-.9,.35,.17),tw=-48,bend=7,hip=(-6,2,-10))
left=pose(r=(36,-24,116),l=(21,-7,137),d=(.8,-.25,-.55),tw=47,bend=15,hip=(4,-6,-11),fr=(-17,-27,8),fl=(18,22,8))
low=pose(r=(-22,-15,89),l=(22,-30,135),d=(-.65,-.3,-.65),tw=-30,bend=20,hip=(-4,0,-15))
thrust=pose(r=(-8,-60,125),l=(22,-25,135),d=(0,-1,.02),tw=28,bend=17,hip=(0,-13,-12),fr=(-17,-33,8),fl=(20,26,8))
down=pose(r=(-8,-39,103),l=(17,-24,125),d=(.06,-.72,-.69),tw=22,bend=27,hip=(0,-9,-16),fr=(-16,-27,8),fl=(18,21,8))
back=pose(r=(-34,13,136),l=(18,-26,132),d=(-.6,.7,.36),tw=-58,bend=10,hip=(-6,8,-13))
specs=[]
def clip(name,duration,keys,damage=None,extra=None):
    specs.append(dict(name=name,duration=duration,keys=keys,damage=damage,extra=extra or {}))
clip('A_Player_Sword_01',.62,[(0,guard),(.13,right),(.23,pose(r=(-25,-42,132),d=(-.5,-.85,0),tw=-10,hip=(-2,-4,-9))),(.33,left),(.62,guard)],[.23,.36])
clip('A_Player_Sword_02',.68,[(0,left),(.14,pose(r=(31,-1,146),d=(.82,.45,.3),tw=45)),(.28,pose(r=(9,-46,134),d=(.1,-.95,-.3),tw=5)),(.41,low),(.68,guard)],[.25,.43])
clip('A_Player_Sword_03',.72,[(0,low),(.18,pose(r=(-36,6,83),d=(-.3,.4,-.85),tw=-39,bend=27,hip=(-5,3,-19))),(.32,pose(r=(-8,-40,122),d=(.1,-.9,.4),tw=10,hip=(0,-8,-11))),(.44,high),(.72,guard)],[.29,.46],{'launch':.37})
clip('A_Player_Sword_04',.9,[(0,high),(.27,pose(r=(-12,3,172),d=(0,.4,.92),tw=-17,bend=-10,hip=(0,0,-8))),(.43,down),(.55,pose(r=(13,-39,92),d=(.2,-.6,-.78),tw=38,bend=33,hip=(0,-10,-20))),(.9,guard)],[.39,.57],{'flash':.4,'knockdown':.48})
clip('A_Player_Parry',.5,[(0,guard),(.1,pose(r=(0,-40,148),l=(17,-32,142),d=(-.92,0,.4),tw=12,bend=0)),(.28,pose(r=(-4,-34,146),d=(-.87,.1,.5),tw=0,hip=(0,5,-9))),(.5,guard)],None,{'parry_start':.08,'parry_end':.28})
clip('A_Player_Riposte',.8,[(0,guard),(.18,back),(.31,thrust),(.46,pose(r=(-6,-58,126),d=(0,-1,0),tw=32,bend=22,hip=(0,-16,-14),fr=(-17,-36,8))),(.8,guard)],[.29,.48],{'flash':.31})
clip('A_Player_DashStrike',.72,[(0,guard),(.16,back),(.3,pose(r=(-12,-49,132),d=(-.5,-.86,0),tw=4,bend=24,hip=(0,-13,-15),fr=(-16,-35,8),fl=(18,34,8))),(.43,left),(.72,guard)],[.28,.45],{'dash_start':.08,'dash_end':.29})
airguard=pose(hip=(0,0,3),fr=(-17,10,26),fl=(18,19,35),bend=12)
clip('A_Player_Air_01',.65,[(0,airguard),(.12,right),(.3,pose(r=(25,-36,125),d=(.8,-.5,-.2),tw=50,hip=(0,0,6),fr=(-19,10,31),fl=(20,17,40))),(.65,airguard)],[.22,.36])
clip('A_Player_Air_02',.72,[(0,airguard),(.15,high),(.31,pose(r=(-8,-47,111),d=(0,-.7,-.7),tw=23,bend=25,hip=(0,0,6),fr=(-18,5,30),fl=(20,25,42))),(.72,airguard)],[.26,.42])
clip('A_Player_Plunge',.86,[(0,airguard),(.22,pose(r=(-6,-23,142),d=(0,0,-1),bend=27,hip=(0,0,4),fr=(-18,12,36),fl=(18,27,47))),(.42,pose(r=(-5,-28,104),d=(0,-.1,-1),bend=35,hip=(0,-4,-22),fr=(-22,-18,8),fl=(23,21,8))),(.61,down),(.86,guard)],[.36,.56],{'land':.42,'flash':.42})
clip('A_Boss_Combo_01',1.08,[(0,guard),(.38,back),(.55,pose(r=(-22,-45,131),d=(-.6,-.8,0),tw=-6,bend=20,hip=(0,-9,-14))),(.72,left),(1.08,guard)],[.53,.75],{'telegraph':.05})
clip('A_Boss_Combo_02',1.1,[(0,left),(.33,pose(r=(32,2,145),d=(.95,.2,.2),tw=52,bend=9)),(.55,pose(r=(0,-47,121),d=(0,-1,0),tw=0,bend=22,hip=(0,-8,-15))),(.73,low),(1.1,guard)],[.51,.77],{'telegraph':.03})
clip('A_Boss_Combo_03',1.35,[(0,guard),(.47,high),(.65,pose(r=(-5,-13,173),d=(0,.4,.9),tw=-12,bend=-10)),(.82,down),(1.0,pose(r=(-6,-40,88),d=(.1,-.4,-.92),bend=38,hip=(0,-10,-24))), (1.35,guard)],[.78,1.04],{'telegraph':.05,'flash':.81})
clip('A_Boss_ChargeAOE',1.8,[(0,guard),(.55,pose(r=(-10,-24,155),d=(0,0,1),tw=-10,bend=-5,hip=(0,0,-18))),(.97,high),(1.18,down),(1.42,pose(r=(-5,-27,88),d=(0,0,-1),hip=(0,-8,-26),bend=39)),(1.8,guard)],[1.16,1.45],{'telegraph':.08,'charge_start':.1,'flash':1.18,'aoe':1.18})
clip('A_Boss_FrontDashSlash',1.12,[(0,guard),(.4,back),(.57,thrust),(.74,left),(1.12,guard)],[.55,.78],{'telegraph':.02,'dash_start':.34,'dash_end':.58})
for side,sign in [('L',1),('R',-1),('Back',0)]:
    jump=pose(r=(-27,4,158),d=(-.3,.4,.85),tw=-35,bend=10,hip=(sign*9,13 if sign==0 else 0,8),fr=(-18,7,27),fl=(18,24,39))
    release=pose(r=(8,-44,119),d=(.25,-.92,-.3),tw=31,bend=20,hip=(sign*6,10 if sign==0 else 0,4),fr=(-18,12,25),fl=(19,21,35))
    clip('A_Boss_JumpWave_'+side,1.16,[(0,guard),(.28,jump),(.52,release),(.72,down),(1.16,guard)],[.48,.65],{'telegraph':.03,'jump':.16,'projectile':.52,'movement_direction':side})
clip('A_Sword_GuardIdle',1.8,[(0,guard),(.9,pose(r=(-24,-37,126),l=(21,-29,131),d=(.05,-.8,.6),bend=3,hip=(0,0,-4.5))),(1.8,guard)])
def interpolate(a,b,t):
    t=t*t*(3-2*t);out={}
    for k in a:
        if isinstance(a[k],tuple):out[k]=tuple(x+(y-x)*t for x,y in zip(a[k],b[k]))
        else:out[k]=a[k]+(b[k]-a[k])*t
    return out
def apply(q):
    for n,m in rest.items():P[n].matrix_basis=m
    update();pel=P['pelvis'];m=pel.matrix.copy();m.translation+=Vector(q['hip']);pel.matrix=m;update()
    rotate_world('pelvis','Z',q['tw']*.2)
    for n,f in [('spine_01',.25),('spine_03',.35),('spine_05',.4)]:
        rotate_world(n,'Z',q['tw']*.8*f);rotate_world(n,'X',-q['bend']*f)
    rotate_world('head','Z',-q['tw']*.35)
    limb('thigh_r','calf_r','foot_r',q['fr'],(-20,-70,45));limb('thigh_l','calf_l','foot_l',q['fl'],(20,-70,45))
    limb('upperarm_r','lowerarm_r','hand_r',q['r'],(-70,0,110));limb('upperarm_l','lowerarm_l','hand_l',q['l'],(60,0,110))
    hand_direction('hand_r',q['d'])
    grip_right()
    for side in ['l']:
        for finger in ['index','middle','ring','pinky']:
            for segment in ['01','02','03']:
                n=f'{finger}_{segment}_{side}'
                if n in P:P[n].rotation_quaternion=Quaternion((0,0,1),math.radians(55 if segment=='01' else 65))
    update()
def export(path):
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,axis_forward='-Y',axis_up='Z',use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_simplify_factor=0,apply_unit_scale=True,armature_nodetype='NULL')
manifest=[]
first_only='--first' in sys.argv
for spec in specs[:1] if first_only else specs:
    action=bpy.data.actions.new(spec['name']);action.use_fake_user=True;arm.animation_data_create();arm.animation_data.action=action
    end=round(spec['duration']*60)+1;scene.frame_start=1;scene.frame_end=end
    samples=[]
    for frame in range(1,end+1):
        scene.frame_set(frame);t=(frame-1)/60;keys=spec['keys'];idx=next((i for i in range(len(keys)-1) if keys[i+1][0]>=t),len(keys)-2)
        t0,a=keys[idx];t1,b=keys[idx+1];q=interpolate(a,b,max(0,min(1,(t-t0)/(t1-t0))));apply(q)
        for p in P:
            p.keyframe_insert(data_path='location',frame=frame,group=p.name);p.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert(data_path='scale',frame=frame,group=p.name)
        if frame%3==1:samples.append({'time':round(t,3),'hand_cm':list(P['hand_r'].head),'blade_direction':list(P['hand_r'].matrix.to_3x3().col[2].normalized())})
    export(ROOT/'Animations'/(spec['name']+'.fbx'))
    entry={k:v for k,v in spec.items() if k!='keys'};entry.update(fps=60,frames=end,sword_axis='+X',root_motion=False,hand_trajectory=samples,sword_socket={'bone':'hand_r','location_cm':[-9,-2.5,0],'rotation_matrix_rows':[[0,1,0],[0,0,1],[1,0,0]],'mapping':'Sword X -> Hand Z; Sword Y -> Hand X; Sword Z -> Hand Y'})
    if spec['damage']:entry['notify']={'DamageStart':spec['damage'][0],'DamageEnd':spec['damage'][1]}
    else:entry['notify']={}
    entry['notify'].update(spec['extra']);manifest.append(entry)
    (ROOT/'Animations'/(spec['name']+'.json')).write_text(json.dumps(entry,indent=2))
    print('EXPORTED',spec['name'],flush=True)
(ROOT/'Animations/animation_manifest.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Animations/SwordCombat_AnimationLibrary.blend'))
