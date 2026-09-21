"""Run through Combat.ps1 only after explicit coordinator remote grant."""
from pathlib import Path
import unreal as u


def main():
    report = []
    for path in u.EditorAssetLibrary.list_assets('/Game/Combat/VFX', recursive=True):
        asset = u.load_asset(path)
        if isinstance(asset, u.NiagaraSystem):
            report.append(u.CombatEditorLibrary.inspect_niagara(asset))
    for path in u.EditorAssetLibrary.list_assets('/Game/Combat/Skills', recursive=True):
        asset = u.load_asset(path)
        if isinstance(asset, u.CombatSkillDefinition):
            report.append('SKILL ' + path)
            for prop in ('cast_effect', 'hit_effect', 'trail_effect', 'area_release_effect'):
                value = asset.get_editor_property(prop)
                report.append('  ' + prop + '=' + (value.get_path_name() if value else 'None'))
    output = Path(u.Paths.project_saved_dir()) / 'Acceptance' / 'VFXEmitterInspection.txt'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(report), encoding='utf-8')
    print('VFX_INSPECTION', str(output.resolve()))


if __name__ == '__main__':
    main()
