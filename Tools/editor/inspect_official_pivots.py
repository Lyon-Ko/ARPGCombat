"""Run in the downloaded official sample with PythonScript commandlet."""
import json
from pathlib import Path
import unreal as u

root = '/Game/Characters/UEFN_Mannequin'
registry = u.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
paths = [f'{root}/Animations/Run/M_Neutral_Run_Turn_{turn}_180_{foot}foot'
         for turn in ('L', 'R') for foot in ('L', 'R')]
rows = []
for path in paths:
    asset = u.load_asset(path)
    assert asset, path
    samples = []
    for index in range(21):
        time = asset.get_play_length() * index / 20
        transform = u.AnimationLibrary.extract_root_track_transform(asset, time)
        samples.append(dict(time=time, yaw=transform.rotation.rotator().yaw,
                            x=transform.translation.x, y=transform.translation.y,
                            z=transform.translation.z))
    rows.append(dict(path=path, duration=asset.get_play_length(), samples=samples))
clean_paths = []
for path in paths:
    clean_path = '/Game/Combat/Animations/OfficialSource/' + path.rsplit('/', 1)[1]
    clean = u.load_asset(clean_path) or u.EditorAssetLibrary.duplicate_asset(path, clean_path)
    u.AnimationLibrary.remove_all_animation_notify_tracks(clean)
    assert u.EditorAssetLibrary.save_loaded_asset(clean)
    clean_paths.append(clean_path)
registry.scan_paths_synchronous(['/Game/Combat/Animations/OfficialSource'], True)
pending = clean_paths + [root + '/Meshes/SKM_UEFN_Mannequin']
dependencies = set()
options = u.AssetRegistryDependencyOptions(include_soft_package_references=False,
    include_hard_package_references=True, include_searchable_names=False,
    include_soft_management_references=False, include_hard_management_references=False)
while pending:
    package = pending.pop()
    if package in dependencies or not package.startswith('/Game/'):
        continue
    dependencies.add(package)
    pending.extend(str(n) for n in (registry.get_dependencies(package, options) or []))
output = Path('F:/ARPGCombat/Saved/Acceptance/OfficialPivotSources.json')
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(dict(clips=rows, clean_paths=clean_paths, dependencies=sorted(dependencies)), indent=2), encoding='utf-8')
print('OFFICIAL_PIVOT_INSPECTION_COMPLETE', len(dependencies))
