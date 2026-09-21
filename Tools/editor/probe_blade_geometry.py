"""Derive real blade extents from skinned source vertices, read-only."""
import unreal as u
import json
from pathlib import Path
result={}
for hero,name,bones in [('Kwang','Kwang_GDC',['weapon_r']),('Greystone','Greystone',['sword_bottom','sword_top'])]:
    mesh=u.load_asset('/Game/Paragon'+hero+'/Characters/Heroes/'+hero+'/Meshes/'+name)
    dyn=u.DynamicMesh()
    dyn,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dyn,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    pose=u.AnimPoseExtensions.get_reference_pose(mesh.get_editor_property('skeleton'))
    ids={b:dyn.get_bone_index(b)[2] for b in bones}
    points={b:[] for b in bones}
    for vi in range(dyn.get_vertex_count()):
        _,weights,valid=dyn.get_vertex_bone_weights(vi)
        if not valid: continue
        for weight in weights:
            for b in bones:
                if weight.get_editor_property('bone_index')==ids[b] and weight.get_editor_property('weight')>.5:
                    position,ok=dyn.get_vertex_position(vi)
                    if ok: points[b].append(list(pose.get_bone_pose(b,u.AnimPoseSpaces.WORLD).inverse_transform_location(position).to_tuple()))
    result[hero]={b:{'count':len(ps),'min':[min(p[a] for p in ps) for a in range(3)],'max':[max(p[a] for p in ps) for a in range(3)]} for b,ps in points.items() if ps}
out=Path(u.Paths.project_saved_dir())/'Acceptance/BladeGeometry.json'
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print('BLADE_GEOMETRY',json.dumps(result))
