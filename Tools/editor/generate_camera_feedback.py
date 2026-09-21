"""Create editable impact camera feedback; run only in the coordinated UE editor.

API verified against UE 5.8.2 Intermediate/PythonStub/unreal.py and
Engine/Plugins/Cameras/EngineCameras/Source/EngineCameras/Public/Shakes/
LegacyCameraShake.h. This file has only been statically validated until executed.
"""
import json
import unreal as u


ROOT = "/Game/Combat"
SHAKE_PATH = ROOT + "/VFX/BP_CombatHitCameraShake"
CHARACTER_PATHS = (
    ROOT + "/Characters/BP_CombatPlayer",
    ROOT + "/Characters/BP_CombatBoss",
)


def require_asset(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError("Required asset missing: " + path)
    return asset


def compile_and_save(bp):
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):
        raise RuntimeError("Blueprint compile failed: " + bp.get_path_name())
    if not u.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False):
        raise RuntimeError("Blueprint save failed: " + bp.get_path_name())


def main():
    # Validate dependencies before modifying any assets.
    characters = [require_asset(path) for path in CHARACTER_PATHS]
    parry = require_asset(ROOT + "/Skills/DA_Parry")
    parry_flash = require_asset(ROOT + "/VFX/NS_ParryFlash")
    shake = u.load_asset(SHAKE_PATH)
    if shake is None:
        factory = u.BlueprintFactory()
        factory.set_editor_property("parent_class", u.LegacyCameraShake)
        shake = u.AssetToolsHelpers.get_asset_tools().create_asset(
            "BP_CombatHitCameraShake", ROOT + "/VFX", u.Blueprint, factory
        )
        if shake is None:
            raise RuntimeError("Could not create camera shake Blueprint")
    if not u.BlueprintEditorLibrary.compile_blueprint(shake):
        raise RuntimeError("Initial camera shake compilation failed")
    defaults = u.get_default_object(shake.generated_class())
    if not isinstance(defaults, u.LegacyCameraShake):
        raise RuntimeError("Existing camera shake has an incompatible parent")
    defaults.set_editor_property("single_instance", True)
    defaults.set_editor_property("oscillation_duration", 0.12)
    defaults.set_editor_property("oscillation_blend_in_time", 0.015)
    defaults.set_editor_property("oscillation_blend_out_time", 0.075)
    defaults.set_editor_property("rot_oscillation", u.ROscillator(
        pitch=u.FOscillator(amplitude=0.25, frequency=35.0),
        yaw=u.FOscillator(), roll=u.FOscillator()))
    defaults.set_editor_property("loc_oscillation", u.VOscillator(
        x=u.FOscillator(), y=u.FOscillator(),
        z=u.FOscillator(amplitude=1.0, frequency=40.0)))
    defaults.set_editor_property("fov_oscillation", u.FOscillator())
    compile_and_save(shake)
    shake_class = shake.generated_class()
    for character in characters:
        u.get_default_object(character.generated_class()).set_editor_property(
            "hit_camera_shake", shake_class)
        compile_and_save(character)
        assigned = u.get_default_object(character.generated_class()).get_editor_property("hit_camera_shake")
        if assigned != shake_class:
            raise RuntimeError("Camera shake assignment did not persist: " + character.get_path_name())
    # Touch only the Parry definition; retain every other skill's HitEffect.
    parry.set_editor_property("hit_effect", parry_flash)
    if not u.EditorAssetLibrary.save_loaded_asset(parry, only_if_is_dirty=False):
        raise RuntimeError("Could not save Parry feedback")
    settings = u.get_default_object(shake_class)
    report = {
        "shake": SHAKE_PATH,
        "characters": list(CHARACTER_PATHS),
        "duration": settings.get_editor_property("oscillation_duration"),
        "pitch_amplitude": settings.get_editor_property("rot_oscillation").pitch.amplitude,
        "z_amplitude_cm": settings.get_editor_property("loc_oscillation").z.amplitude,
        "parry_hit_effect": parry.get_editor_property("hit_effect").get_path_name(),
        "visual_and_pause_toggle_validation": "pending PIE",
    }
    u.log("CAMERA_FEEDBACK " + json.dumps(report))
    return report


if __name__ == "__main__":
    main()
