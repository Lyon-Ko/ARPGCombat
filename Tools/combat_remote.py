"""Project-scoped CLI using Epic's bundled remote execution protocol."""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get('COMBAT_ENGINE', r'D:\UE5.8\UE_5.8'))
sys.path.insert(0, str(ENGINE / 'Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python'))
import remote_execution


def execute(code: str, timeout: float = 15) -> dict:
    config = remote_execution.RemoteExecutionConfig()
    # Every short-lived client has its own loopback callback port.
    with socket.socket() as candidate:
        candidate.bind(('127.0.0.1', 0))
        config.command_endpoint = ('127.0.0.1', candidate.getsockname()[1])
    remote = remote_execution.RemoteExecution(config)
    remote.start()
    try:
        deadline = time.monotonic() + timeout
        expected = os.path.normcase(os.path.realpath(ROOT))
        while time.monotonic() < deadline:
            matches = [n for n in remote.remote_nodes if os.path.normcase(os.path.realpath(n.get('project_root', ''))) == expected and n.get('project_name') == 'Combat']
            if matches:
                if len(matches) != 1:
                    raise RuntimeError('Multiple Combat editor instances found; close duplicate instances')
                remote.open_command_connection(matches[0]['node_id'])
                # Recheck actual project identity in the target process before caller code.
                guard = "import unreal, os\nassert os.path.normcase(os.path.realpath(unreal.Paths.project_dir())) == " + repr(expected) + ", 'Project identity mismatch'\n"
                return remote.run_command(guard + code, unattended=True, exec_mode=remote_execution.MODE_EXEC_FILE)
            time.sleep(0.15)
        raise TimeoutError(f'No remote editor for {ROOT}. Start Tools/Combat.ps1 editor. Discovered: {remote.remote_nodes}')
    finally:
        remote.stop()


def status() -> dict:
    return execute("import json\nprint(json.dumps({'project': unreal.Paths.project_dir(), 'engine': unreal.SystemLibrary.get_engine_version(), 'pie': unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()}))")


def execute_file(path: Path) -> dict:
    resolved = path.expanduser().resolve(strict=True)
    source = resolved.read_text(encoding='utf-8-sig')
    # ExecuteFile scans the entire command for '.py' to guess a filename.
    # Encode both strings so docstrings/paths cannot trigger that heuristic.
    source64 = base64.b64encode(source.encode('utf-8')).decode('ascii')
    path64 = base64.b64encode(str(resolved).encode('utf-8')).decode('ascii')
    code = (
        "globals()['__file__'] = __import__('base64').b64decode(" + repr(path64) + ").decode('utf-8')\n"
        "globals()['__name__'] = '__main__'\n"
        "exec(compile(__import__('base64').b64decode(" + repr(source64) + "), "
        "globals()['__file__'], 'exec'), globals(), globals())"
    )
    # Use the shared console globals: functions/runner handles survive later --code calls.
    return execute(code)


def list_assets(path: str = '/Game') -> dict:
    return execute('import json\nprint(json.dumps(unreal.EditorAssetLibrary.list_assets(' + repr(path) + ', recursive=True)))')


def pie(action: str) -> dict:
    if action not in ('start', 'stop', 'status'):
        raise ValueError('PIE action must be start, stop, or status')
    if action == 'status':
        return status()
    method = 'editor_request_begin_play' if action == 'start' else 'editor_request_end_play'
    return execute('unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).' + method + '()')


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    assets = sub.add_parser('list_assets'); assets.add_argument('path', nargs='?', default='/Game')
    run = sub.add_parser('run_python'); group = run.add_mutually_exclusive_group(required=True); group.add_argument('--code'); group.add_argument('--file', type=Path)
    play = sub.add_parser('pie'); play.add_argument('action', choices=['start', 'stop', 'status'])
    args = parser.parse_args()
    try:
        if args.command == 'status': result = status()
        elif args.command == 'list_assets': result = list_assets(args.path)
        elif args.command == 'pie': result = pie(args.action)
        else: result = execute_file(args.file) if args.file else execute(args.code)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get('success') else 1)
    except Exception as error:
        print(json.dumps({'success': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

