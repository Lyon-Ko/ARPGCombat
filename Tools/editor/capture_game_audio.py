"""Official UE master-submix capture; invoke start()/stop() in separate calls.

Requires an active PIE world and the coordinator's remote grant. Never triggers
skills or changes sound settings. WAV export is asynchronous; inspect the file
after the completion callback/next editor ticks, not in a blocking editor loop.
"""
from pathlib import Path
import unreal as u


def pie_world():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if world is None:
        raise RuntimeError('An active PIE game world is required')
    return world


def start(seconds=12.0):
    u.AudioMixerLibrary.start_recording_output(pie_world(), seconds, None)
    print('GAME_MASTER_RECORDING_STARTED', seconds)


def stop(name='CombatActualMasterOutput'):
    if not name.replace('_', '').isalnum():
        raise ValueError('Use an alphanumeric recording name')
    directory = Path(u.Paths.project_saved_dir()) / 'Acceptance'
    directory.mkdir(parents=True, exist_ok=True)
    u.AudioMixerLibrary.stop_recording_output(pie_world(), u.AudioRecordingExportType.WAV_FILE,
                                             name, str(directory.resolve()), None, None)
    print('GAME_MASTER_WAV_EXPORT_REQUESTED', str(directory / (name + '.wav')))
