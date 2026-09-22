"""Full idempotent authoring entrypoint, after coordinator build/reload."""
import runpy
from pathlib import Path
import unreal
base=Path(unreal.Paths.project_dir())/'Tools/editor'
for script in ['generate_foundation.py','fix_arena_background.py','import_source_assets.py','generate_montages.py','generate_skills.py','generate_presentation.py','generate_native_characters.py','configure_ground_locomotion.py','configure_locomotion_asset.py','generate_skill_example.py','generate_fx_meshes.py','generate_blade_ribbons.py','generate_camera_feedback.py','generate_final_vfx.py','validate_assets.py']:
    print('PIPELINE_STAGE',script)
    runpy.run_path(str(base/script),run_name='__main__')
print('PIPELINE_GENERATION_FINISHED')
