import bpy
import bmesh
import json
from pathlib import Path

out = Path(__file__).resolve().parent
rows = []
for name in ('SM_SwordWave', 'SM_WarningRing'):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = .01
    bpy.ops.import_scene.fbx(filepath=str(out/(name+'.fbx')))
    obj = next(o for o in bpy.context.selected_objects if o.type == 'MESH')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    rows.append({'name': name, 'bounds_min_cm': [min(p[k] for p in points) for k in range(3)],
                 'bounds_max_cm': [max(p[k] for p in points) for k in range(3)],
                 'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
                 'zero_area_faces': sum(f.calc_area() < 1e-7 for f in bm.faces)})
    bm.free()
assert all(r['nonmanifold_edges'] == 0 and r['zero_area_faces'] == 0 for r in rows), rows
(out/'fbx_validation.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('VFX_FBX_VALID', json.dumps(rows))
