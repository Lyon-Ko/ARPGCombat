"""Read-only cold-start verification. Import is inert; explicitly call run()."""
import datetime
import hashlib
import json
from pathlib import Path
import unreal as u

# Build14 identities independently retained in DefaultChain_ColdStart.json.
EXPECTED_DLLS = {
    'UnrealEditor-Combat.dll': '6a342f29753325a62bf1fe1982214c1031b1d203f2ae7d231d8164454f6b441a',
    'UnrealEditor-CombatEditor.dll': 'aa2822f0597f988aadd99d34add025847f3fe33ce1be211eb8c5ce81de26d35d'}


def tag_name(value):
    return str(value.get_editor_property('tag_name'))


def run():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = Path(u.Paths.project_saved_dir())/'Acceptance'/('FinalColdStart_'+stamp+'.json')
    report = {'status': 'running', 'utc': stamp, 'checks': [], 'errors': [],
              'scope': 'Read-only non-PIE map, assets, graph links, default chains, instrumentation and Build14 DLL identity; no compilation, save or PIE start'}

    def check(name, passed, detail=None):
        report['checks'].append({'name': name, 'pass': bool(passed), 'detail': detail})

    try:
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        worlds = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor.is_in_play_in_editor() or worlds.get_game_world():
            raise RuntimeError('Requires non-PIE cold-start editor')
        world = worlds.get_editor_world()
        report['editor_map'] = world.get_path_name() if world else None
        check('arena_map', report['editor_map'] == '/Game/Combat/Maps/L_CombatArena.L_CombatArena', report['editor_map'])
        report['conditions'] = {n: u.SystemLibrary.get_console_variable_int_value(n) for n in
            ('mass.FullyParallel', 'stats.AutoEnableNamedEventsWhenProfiling')}
        report['conditions']['trace_is_tracing'] = bool(u.TraceUtilLibrary.is_tracing())
        check('mass0_named0_trace_off', all(v == 0 for v in report['conditions'].values()), report['conditions'])
        report['dlls'] = {}
        for name, expected in EXPECTED_DLLS.items():
            actual = hashlib.sha256((Path(u.Paths.project_dir())/'Binaries/Win64'/name).read_bytes()).hexdigest()
            report['dlls'][name] = actual
            check('dll_identity:'+name, actual == expected, {'expected': expected, 'actual': actual})

        paths = u.EditorAssetLibrary.list_assets('/Game/Combat', True)
        assets, blueprints, montages = {}, [], []
        for path in paths:
            asset = u.load_asset(path)
            check('asset_load:'+path, bool(asset))
            if asset: assets[path] = asset
        check('216_assets', len(paths) == 216 and len(assets) == 216, len(assets))
        skill_montages = set()
        for path, asset in assets.items():
            if isinstance(asset, u.CombatSkillDefinition):
                montage = asset.get_editor_property('montage')
                check('skill_montage:'+path, bool(montage))
                if montage: skill_montages.add(montage.get_path_name())
        for path, asset in assets.items():
            if isinstance(asset, u.Blueprint):
                blueprints.append(path)
                check('generated_class:'+path, bool(asset.generated_class()))
                if '/Abilities/' in path:
                    graph = u.BlueprintGraphEditor.get_graph_editor_by_name(asset, 'Gameplay Ability Graph')
                    if not graph:
                        check('ability_graph:'+path, False)
                        continue
                    nodes = graph.list_all_nodes()
                    tasks = [n for n in nodes if n.get_class().get_name() == 'K2Node_LatentAbilityCall']
                    check('ability_graph:'+path, not graph.list_nodes_with_errors() and len(nodes) >= 30,
                          {'nodes': len(nodes), 'errors': len(graph.list_nodes_with_errors())})
                    check('latent_OnEvent_connected:'+path, any(pin.list_connected_pins() for task in tasks
                        for pin in task.list_output_pins() if str(pin.get_pin_name()) == 'OnEvent'))
            if isinstance(asset, u.AnimMontage) and ('/Montages/' in path or asset.get_path_name() in skill_montages):
                montages.append(path)
                check('montage_notifications:'+path, asset.get_editor_property('sequence_length') > 0
                      and bool(u.AnimationLibrary.get_animation_notify_events(asset)))
        report['counts'] = {'assets': len(assets), 'blueprints': len(blueprints), 'skill_montages': len(montages)}
        check('33_blueprints', len(blueprints) == 33, len(blueprints))
        check('39_skill_montages', len(montages) == 39, len(montages))
        attack3 = u.load_asset('/Game/Combat/Skills/DA_Attack3')
        check('attack3_next_attack4', tag_name(attack3.next_skill_tag) == 'Combat.Skill.Attack4', tag_name(attack3.next_skill_tag))
        report['definitions'] = {}
        for role in ('Player', 'Boss'):
            bp = u.load_asset('/Game/Combat/Characters/BP_Combat'+role)
            values = list(u.get_default_object(bp.generated_class()).skill_definitions)
            tags = {tag_name(d.skill_tag) for d in values}
            if role == 'Player':
                check('player_default_table', 'Combat.Skill.Attack4' in tags and 'Combat.Skill.Example.CrescentBurst' not in tags, sorted(tags))
            rows = [{'path': d.get_path_name(), 'next': tag_name(d.next_skill_tag)} for d in values]
            report['definitions'][role] = rows
            check('all_next_resolve:'+role, all(r['next'] in ('', 'None') or r['next'] in tags for r in rows), rows)
    except Exception as exc:
        report['errors'].append(repr(exc))
    report['status'] = 'passed' if not report['errors'] and report['checks'] and all(c['pass'] for c in report['checks']) else 'failed'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print('FINAL_COLD_START', report['status'], str(output))
    return {'status': report['status'], 'report': str(output), 'checks': len(report['checks'])}
