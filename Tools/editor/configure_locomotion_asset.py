"""Create the Details-editable asset, importing the legacy INI only on first creation."""
import configparser
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
asset_path = '/Game/Combat/Config/DA_Locomotion'
legacy = root / 'Config/Locomotion.ini'
schema = (root / 'Source/Combat/Public/CombatLocomotionParameters.inl').read_text(encoding='utf-8')


def snake(name):
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)).lower()


asset = u.load_asset(asset_path)
created = asset is None
imported = {}
backup = None
if created:
    ini = configparser.ConfigParser(interpolation=None)
    if legacy.exists():
        ini.read(legacy, encoding='utf-8-sig')
    for match in re.finditer(r'^LOCO_(FLOAT|BOOL)\((\w+), (\w+), (\w+), ([^,]+), (.*)\)$', schema, re.M):
        kind, member, section, key, default, rest = match.groups()
        if legacy.exists() and ini.has_option(section, key):
            value = ini.getfloat(section, key) if kind == 'FLOAT' else ini.getboolean(section, key)
        else:
            value = float(default) if kind == 'FLOAT' else default == 'true'
        if kind == 'FLOAT':
            lo, hi, _ = rest.split(', ', 2)
            assert math.isfinite(value) and float(lo) <= value <= float(hi), (section, key, value)
        imported[snake(member)] = value
    assert len(imported) == len(re.findall(r'^LOCO_(?:FLOAT|BOOL)\(', schema, re.M))
    assert imported['animation_jog_speed'] < imported['animation_fast_speed']
    assert imported['camera_pitch_min'] <= imported['camera_pitch_max']
    assert imported['camera_locked_min_distance'] <= imported['camera_locked_max_distance']
    assert imported['camera_hide_distance'] < imported['camera_reveal_distance']
    assert imported['jump_count'] == int(imported['jump_count'])
    factory = u.DataAssetFactory()
    factory.set_editor_property('data_asset_class', u.CombatLocomotionConfig)
    asset = u.AssetToolsHelpers.get_asset_tools().create_asset('DA_Locomotion', '/Game/Combat/Config', u.CombatLocomotionConfig, factory)
    assert asset
    for prop, value in imported.items():
        asset.set_editor_property(prop, value)
        assert math.isclose(float(asset.get_editor_property(prop)), float(value), rel_tol=1e-6, abs_tol=1e-6), prop
    assert u.EditorAssetLibrary.save_loaded_asset(asset)

assert isinstance(asset, u.CombatLocomotionConfig)
player_bp = u.load_asset('/Game/Combat/Characters/BP_CombatPlayer')
u.get_default_object(player_bp.generated_class()).set_editor_property('locomotion_config', asset)
assert u.CombatEditorLibrary.compile_and_save(player_bp)
assert u.get_default_object(player_bp.generated_class()).get_editor_property('locomotion_config') == asset

if created and legacy.exists():
    folder = root / 'Saved/LocomotionMigration'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / ('Locomotion_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.ini')
    shutil.copy2(legacy, backup)
    assert hashlib.sha256(legacy.read_bytes()).digest() == hashlib.sha256(backup.read_bytes()).digest()
    # Conversion complete: only remove the exact migrated file, retaining its verified backup.
    legacy.unlink()

report = dict(asset=asset.get_path_name(), created=created, imported_values=imported,
              imported_count=len(imported), legacy_backup=str(backup) if backup else None)
out = root / 'Saved/Acceptance/LocomotionAssetMigration.json'
out.parent.mkdir(parents=True, exist_ok=True)
if created or not out.exists():
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('LOCOMOTION_DATA_ASSET_READY', asset.get_path_name(), 'imported', len(imported), 'backup', backup)
