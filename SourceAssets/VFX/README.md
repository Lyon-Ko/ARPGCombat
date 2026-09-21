# Original combat FX meshes

Created procedurally in Blender 5.1.1 for this project, without external assets. Source geometry has no third-party license restrictions.

- `SM_SwordWave.fbx`: local **+X propagation**, spans Y = -90..90 cm. Bow depth X = 45.25 cm, maximum band width 10 cm, local slab thickness 3 cm. Tips bend upward by 4 cm, making total Z bounds 7 cm. Origin is centered on geometric bounds. Bounds: (-22.625, -90, -3.5) .. (22.625, 90, 3.5) cm.
- `SM_WarningRing.fbx`: XY ring, centerline radius 50 cm, inner radius 49 cm, outer radius 51 cm. Width 2 cm, thickness 0.25 cm. Origin is at ground level Z = 0. Bounds: (-51, -51, 0) .. (51, 51, 0.25) cm. To show a gameplay radius R, use uniform XY scale R / 50; thickness can be controlled independently.

Both are closed manifold volumes with UV0 and recalculated outward normals. They do not provide physics or hit collision. Disable collision on rendering components and automatic collision generation during UE import. Use an emissive, two-sided UE material (orange for Boss); FBX material names are placeholders for assignment, not a claim that Blender shader nodes transfer to UE. Add a small runtime ground offset to the ring if needed to avoid z-fighting.

`CombatFXMeshes.blend` retains both meshes at the origin; toggle one off when inspecting the other. `build_vfx_meshes.py` regenerates both FBXs, source scene, and individually rendered previews. `validate_vfx_meshes.py` reimports the FBXs in a fresh centimeter scene and checks bounds, manifold edges, and zero-area faces. `mesh_manifest.json` records generated topology and dimensions; `fbx_validation.json` records actual round-trip results.

Preview PNGs are local Blender renders. No UE import or runtime effect integration has been performed by this task.
