"""Copy evidence, gzip original CSVs, or record local files by path and SHA-256."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'Docs/Evidence/Final_20260922'
FIXED = [
    'Saved/Build_DefaultChain_14.log',
    'Saved/Acceptance/DefaultChain_AssetValidation.json',
    'Saved/Acceptance/DefaultChain_ColdStart.json',
    'Saved/Acceptance/DefaultChainRepair_20260921T195055491298Z.json',
    'Saved/Acceptance/SkillExtensionFinal_20260921T194848720875Z.json',
    'Saved/Acceptance/SkillExtensionFinal_20260921T195256502504Z.json',
    'Saved/Acceptance/default_chain_only_20260921T195607760663Z.json',
    'Saved/Acceptance/arena_acceptance_20260921T192140351854Z.json',
    'Saved/Acceptance/Performance_1080pHigh_60_20260921T192140351854Z.json',
    'Saved/Acceptance/runtime_profile_20260921T193559409889Z.json',
    'Saved/Acceptance/Performance_Supplemental_1080pHigh_60_20260921T193559409889Z.json',
    'Saved/Acceptance/gc_profile_20260921T194436862733Z.json',
    'Saved/Acceptance/GCAnalysis_20260921T194436862733Z.json',
    'Saved/Acceptance/trace_profile_20260921T200209859752Z.json',
    'Saved/Acceptance/MassSingleThread_20260921T201336033106Z.json',
    'Saved/Acceptance/arena_ai_scenarios_20260921T193914Z.json',
    'Saved/Acceptance/arena_ai_near_20260921T194032Z.json',
    'Saved/Acceptance/arena_spatial_visual_20260921T194122Z.json',
    'Saved/Screenshots/WindowsEditor/ScreenShot00008.png',
    'Saved/Screenshots/WindowsEditor/ScreenShot00009.png',
    'Saved/Build_AreaReentry_13.log',
    'Saved/Acceptance/Build13_AssetValidation.json',
    'Saved/Acceptance/CLIFileProbe.json',
    'Saved/Acceptance/CLIFilePersistence.json',
    'Saved/Acceptance/SkillExtensionNewTagPIE.json',
    'Saved/Acceptance/Build11_Directed_20260921T191304332667Z.json',
    'Saved/Acceptance/CombinedSources_20260921T191815227899Z.json',
    'Saved/Acceptance/CombinedSources_20260921T192102267435Z.json',
    'Saved/Acceptance/arena_acceptance_20260921T185232088295Z.json',
    'Saved/Acceptance/Performance_1080pHigh_60_20260921T185232088295Z.json',
    'Saved/Acceptance/PersistenceBenchmark_20260921_baseline.json',
    'Saved/Acceptance/SerializerBenchmark.json',
    'Saved/Acceptance/CombatNativeFocusedOutput.json',
    'Saved/Acceptance/VFXLifetime.json',
    'Saved/Acceptance/VFXHandoff.json',
    'Saved/Acceptance/VFXFinalReloadedProperties.txt',
    'Saved/Acceptance/VFX_final_hit.png',
    'Saved/Acceptance/VFX_final_parry.png',
    'Saved/Acceptance/VFX_final_aoe.png',
    'Saved/Acceptance/VFX_final_wave.png',
    'Saved/Acceptance/VFX_final_warning.png',
    'Saved/Acceptance/VFX_ribbonactive_player_ribbon.png',
    'Saved/Acceptance/VFX_ribbonactive_boss_ribbon.png',
    'Saved/Screenshots/WindowsEditor/ScreenShot00005.png',
    'Saved/Screenshots/WindowsEditor/ScreenShot00006.png',
    'Saved/Screenshots/WindowsEditor/ScreenShot00007.png',
]

def source_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError('Evidence must be an existing file in this project: '+str(path))
    return path

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def validate_inputs(copies, csvs, references):
    """Complete preflight before creating directories, hashing, or writing files."""
    sources = copies + csvs + references
    source_keys = [str(p).casefold() for p in sources]
    if len(source_keys) != len(set(source_keys)):
        raise ValueError('Duplicate evidence input across copy, CSV, or reference modes')
    targets = [p.name for p in copies] + [p.name+'.gz' for p in csvs] + ['manifest.json']
    target_keys = [name.casefold() for name in targets]
    if len(target_keys) != len(set(target_keys)):
        raise ValueError('Evidence basename collision (including reserved manifest.json); use unique source names')
    output_paths = {str((DESTINATION / name).resolve()).casefold() for name in targets}
    if output_paths.intersection(source_keys):
        raise ValueError('An evidence output would overwrite an input file')

def report_summary(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('status') not in ('passed', 'failed'):
        raise ValueError('Final report must have a terminal passed/failed status: '+str(path))
    assertions = data.get('assertions')
    fights = data.get('natural_fights')
    if not isinstance(assertions, list) or not isinstance(fights, list):
        raise ValueError('Final report must contain assertions and natural_fights lists: '+str(path))
    return {
        'source': str(path),
        'status': data['status'],
        'accepts_twenty_rounds': data.get('accepts_twenty_rounds'),
        'assertions': {
            'total': len(assertions),
            'passed': sum(a.get('pass') is True for a in assertions),
            'failed': sum(a.get('pass') is False for a in assertions),
            'unclassified': sum(a.get('pass') is not True and a.get('pass') is not False for a in assertions),
            'failed_names': [a.get('name') for a in assertions if a.get('pass') is False],
        },
        'rounds': {
            'recorded': len(fights),
            'passed': sum(f.get('pass') is True for f in fights),
            'failed': sum(f.get('pass') is False for f in fights),
            'unclassified': sum(f.get('pass') is not True and f.get('pass') is not False for f in fights),
            'outcomes': dict(Counter(f.get('outcome', 'unreported') for f in fights)),
            'by_round': [{k: f.get(k) for k in ('round', 'fps_cap', 'outcome', 'pass')} for f in fights],
        },
        'natural_outcome_summary': data.get('natural_outcome_summary'),
        'interpretation': 'Actual report fields and counts only; failures remain failures. Victory/defeat outcomes are distinct from assertion pass/fail.',
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extra', action='append', default=[], help='Explicit additional report/log/image path')
    parser.add_argument('--csv', action='append', default=[], help='Original CSV; stored losslessly as gzip')
    parser.add_argument('--reference', action='append', default=[], help='Existing project file; hash and record its local path without copying (repeatable)')
    parser.add_argument('--final-report', help='Terminal primary acceptance JSON; copied unless already selected as an extra or reference')
    args = parser.parse_args()
    # Resolve the complete input set before writing, so a missing report fails early.
    copies = [source_path(p) for p in FIXED+args.extra]
    csvs = [source_path(p) for p in args.csv]
    recording = source_path('Saved/Acceptance/CombatNativeFocusedOutput.wav')
    references = [recording] + [source_path(p) for p in args.reference]
    final_report_path = source_path(args.final_report) if args.final_report else None
    if final_report_path and final_report_path not in copies + csvs + references:
        copies.append(final_report_path)
    validate_inputs(copies, csvs, references)
    final_report = report_summary(final_report_path) if final_report_path else None
    DESTINATION.mkdir(parents=True, exist_ok=True)
    items = []
    for source in copies:
        destination = DESTINATION / source.name
        original_hash = digest(source)
        shutil.copyfile(source, destination)
        assert digest(destination) == original_hash
        items.append({'source': str(source), 'artifact': destination.name, 'bytes': source.stat().st_size,
                      'sha256': original_hash, 'storage': 'byte_identical_copy'})
    for source in csvs:
        destination = DESTINATION / (source.name+'.gz')
        original_hash = digest(source)
        with source.open('rb') as src, destination.open('wb') as dst:
            with gzip.GzipFile(filename=source.name, mode='wb', fileobj=dst, mtime=0) as compressed:
                shutil.copyfileobj(src, compressed)
        with gzip.open(destination, 'rb') as restored:
            assert hashlib.file_digest(restored, 'sha256').hexdigest() == original_hash
        items.append({'source': str(source), 'artifact': destination.name, 'bytes': source.stat().st_size,
                      'sha256': original_hash, 'storage': 'lossless_gzip',
                      'artifact_bytes': destination.stat().st_size, 'artifact_sha256': digest(destination)})
    for source in references:
        items.append({'source': str(source), 'bytes': source.stat().st_size, 'sha256': digest(source),
                      'storage': 'local_reference_only',
                      'note': 'File remains at its project-local source path; not copied or compressed into Git evidence.'})
    manifest = {'schema': 2, 'items': items, 'final_report': final_report,
        'interpretation': 'Reports retain their actual pass/fail and build scope; this manifest does not upgrade a failed or older test to final acceptance. The old SkillExtensionNewTagPIE defaults_restored field was disproved by the later detached-tag and disk-reload verification. The 192140 twenty-bout report lacked an exact four-hit-chain check and does not validate the repaired final default chain; see the later run.',
        'scope': {
            'trace_profile_20260921T200209859752Z.json': 'Three-bout trace sampling executed 154 assertions, all passed, but the original report status is FAILED because Trace.Stop was incorrectly judged synchronously before its asynchronous disconnect. The original FAILED report is retained and is not upgraded by the later disconnect or trace analysis. Instrumentation changes observation overhead; this is not final twenty-bout acceptance.',
            'MassSingleThread_20260921T201336033106Z.json': 'Supplemental three-bout sample: 161 of 162 assertions passed; coverage.natural_projectile failed. The original FAILED report is retained. This limited sample does not establish final twenty-bout acceptance.',
            'final_acceptance': 'Use only the newly completed report explicitly selected by --final-report as the primary twenty-bout conclusion. If final_report is null, this manifest identifies no final acceptance verdict.',
        },
        'images': 'VFX images are isolated slow-motion evidence; ScreenShot00005/6 and 00008/9 are wall-camera fixtures; ScreenShot00007 is normal-speed 192140-run round2. See the respective report for timestamps.',
        'csv_policy': 'Every original numeric frame is preserved. gzip changes storage only; decompressed SHA-256 is verified. Analyze with --warmup-frames 0.',
        'audio_policy': 'Focused output capture is automation evidence, not a claim of human play or per-effect listening review.',
        'reference_policy': 'Local references are SHA-256 checked when this tool runs but are not portable archive contents. Keep their original project files; no copied artifact or decompression verification is claimed for references.'}
    (DESTINATION/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'directory': str(DESTINATION), 'items': len(items), 'all_copy_and_decompression_hashes_verified': True}))

if __name__ == '__main__':
    main()
