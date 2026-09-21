"""Original procedural FX geometry. Blender 5.x, centimeter export for UE."""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    node = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(node.outputs['BSDF'], output.inputs['Surface'])
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = .25
    node.inputs['Roughness'].default_value = .35
    node.inputs['Emission Color'].default_value = (*color, 1)
    node.inputs['Emission Strength'].default_value = .75
    mat.use_backface_culling = False
    return mat

def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    return obj

verts, faces = [], []
N = 80
for i in range(N+1):
    t = -1+2*i/N
    y = 90*t
    bow = 45*(1-t*t)
    width = .25+9.75*max(0,1-t*t)**.65
    z = 4*t*t
    for x, dz in [(bow, 1.5), (bow-width, 1.5), (bow, -1.5), (bow-width, -1.5)]:
        verts.append((x, y, z+dz))
for i in range(N):
    a, b = 4*i, 4*(i+1)
    faces.extend([(a,a+1,b+1,b), (a+2,b+2,b+3,a+3),
                  (a,b,b+2,a+2), (a+1,a+3,b+3,b+1)])
faces.extend([(0,2,3,1),(4*N,4*N+1,4*N+3,4*N+2)])
# Origin at the geometric bounds center, no object-level rotation/scale.
center = [(min(v[k] for v in verts)+max(v[k] for v in verts))/2 for k in range(3)]
verts = [tuple(v[k]-center[k] for k in range(3)) for v in verts]
wave = mesh('SM_SwordWave', verts, faces, material('M_SwordWave_Orange', (1,.18,.012)))

verts, faces = [], []
N = 160
for i in range(N):
    theta = 2*math.pi*i/N
    for radius, z in [(51,.25),(49,.25),(51,0),(49,0)]:
        verts.append((radius*math.cos(theta), radius*math.sin(theta), z))
for i in range(N):
    a, b = 4*i, 4*((i+1)%N)
    faces.extend([(a,a+1,b+1,b), (a+2,b+2,b+3,a+3),
                  (a,b,b+2,a+2), (a+1,a+3,b+3,b+1)])
ring = mesh('SM_WarningRing', verts, faces, material('M_WarningRing_Amber', (1,.32,.025)))

report = {'authorship': 'Original procedural geometry; no third-party source',
          'license': 'Project original asset; no third-party restrictions',
          'units': 'cm', 'collision': 'None authored; runtime controls collision', 'assets': []}
for obj in (wave, ring):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')), use_selection=True,
        object_types={'MESH'}, axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', bake_anim=False, use_mesh_modifiers=True,
        mesh_smooth_type='FACE', add_leaf_bones=False)
    report['assets'].append({'name': obj.name, 'bounds_min_cm': [min(v.co[k] for v in obj.data.vertices) for k in range(3)],
        'bounds_max_cm': [max(v.co[k] for v in obj.data.vertices) for k in range(3)],
        'size_cm': list(obj.dimensions), 'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons),
        'local_forward': '+X' if obj == wave else 'XY plane; +Z normal',
        'closed_volume': True, 'backface_culling': False})

scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.render.resolution_x = 1100
scene.render.resolution_y = 850
scene.render.resolution_percentage = 100
scene.world.color = (.12,.12,.12)
scene.view_settings.view_transform = 'AgX'
bpy.ops.object.light_add(type='AREA', location=(0,-60,220))
light = bpy.context.object
light.data.energy = 180000
light.data.shape = 'DISK'
light.data.size = 200
bpy.ops.object.camera_add(location=(180,-210,290))
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 245
scene.camera = camera
def aim(point):
    camera.rotation_euler = (Vector(point)-camera.location).to_track_quat('-Z','Y').to_euler()
aim((0,0,0))
for obj in (wave, ring):
    wave.hide_render = obj != wave
    ring.hide_render = obj != ring
    scene.render.filepath = str(OUT/(obj.name+'_Preview.png'))
    bpy.ops.render.render(write_still=True)
wave.hide_render = ring.hide_render = False
# Both retained at origin in source, independently toggle visibility for inspection.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CombatFXMeshes.blend'))
(OUT/'mesh_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VFX_MESHES_READY', json.dumps(report))
