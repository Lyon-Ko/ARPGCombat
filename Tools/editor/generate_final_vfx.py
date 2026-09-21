"""Bounded combat particle authoring. Run only under the VFX remote handoff.

Creates new single-emitter systems, preserving old systems for before/after
comparison. Skill references change only after all replacement systems compile.
No montage, Blueprint, StateTree, crescent or warning-ring mutation.
"""
from pathlib import Path
import unreal as u

ROOT = '/Game/Combat/VFX/'
LIB = u.CombatEditorLibrary


def material(name, shape):
    path = ROOT + name
    asset = u.load_asset(path)
    if asset is None:
        asset = u.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT.rstrip('/'), u.Material, u.MaterialFactoryNew())
    assert isinstance(asset, u.Material), path
    ml = u.MaterialEditingLibrary
    ml.delete_all_material_expressions(asset)
    asset.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    asset.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    asset.set_editor_property('two_sided', True)
    # Feedback is emitted at hit/capsule centers. A short glint must remain
    # readable when its center intersects armor; sprites remain tightly sized.
    asset.set_editor_property('disable_depth_test', shape == 'flash')
    ml.set_material_usage(asset, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    ml.set_material_usage(asset, u.MaterialUsage.MATUSAGE_NIAGARA_RIBBONS)
    uv = ml.create_material_expression(asset, u.MaterialExpressionTextureCoordinate, -700, 100)
    age = ml.create_material_expression(asset, u.MaterialExpressionParticleRelativeTime, -700, 260)
    color = ml.create_material_expression(asset, u.MaterialExpressionVectorParameter if shape == 'ribbon' else u.MaterialExpressionParticleColor, -300, -100)
    if shape == 'ribbon':
        color.set_editor_property('parameter_name', 'RibbonTint')
        color.set_editor_property('default_value', u.LinearColor(.04, .9, 1.8, 1))
    mask = ml.create_material_expression(asset, u.MaterialExpressionCustom, -420, 150)
    mask.set_editor_property('description', 'Narrow authored ' + shape + ', short particle-age fade')
    mask.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    custom_inputs = []
    for name in ('UV', 'Age'):
        item = u.CustomInput()
        item.set_editor_property('input_name', name)
        custom_inputs.append(item)
    mask.set_editor_property('inputs', custom_inputs)
    expressions = {
        'spark': 'float2 p=abs(UV*2-1); float a=saturate((1-p.x)*8)*saturate((1-p.y-p.x*.65)*5);',
        'flash': 'float2 p=abs(UV*2-1); float2 t=saturate(1-p); float a=max(saturate((.10*t.x*t.x-p.y)*60)*t.x, saturate((.10*t.y*t.y-p.x)*60)*t.y); a=max(a,saturate((.13-length(p))*12));',
        'ribbon': 'float a=saturate((.5-abs(UV.y-.5))*5);',
    }
    mask.set_editor_property('code', expressions[shape] + ' return a*saturate((1-Age)*2);')
    assert ml.connect_material_expressions(uv, '', mask, 'UV')
    assert ml.connect_material_expressions(age, '', mask, 'Age')
    ml.connect_material_property(color, 'RGB', u.MaterialProperty.MP_EMISSIVE_COLOR)
    ml.connect_material_property(mask, '', u.MaterialProperty.MP_OPACITY)
    ml.recompile_material(asset)
    assert u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
    return asset


def module_inputs(system):
    """Read actual reflected names; refuse guessed or hidden inputs."""
    result = []
    emitter = module = None
    for line in LIB.inspect_niagara(system).splitlines():
        if line.startswith('EMITTER '):
            emitter = line[8:].rsplit(' enabled=', 1)[0]
        elif line.startswith(' MODULE '):
            module = line[8:].split(' script=', 1)[0]
        elif line.startswith('  INPUT ') and line.endswith('hidden=0'):
            result.append((emitter, module, line[8:].split(' type=', 1)[0]))
    return result


def set_input(system, module_prefix, suffix, value, optional=False):
    matches = [item for item in module_inputs(system)
               if item[1].startswith(module_prefix) and item[2] == 'Module.' + suffix]
    if not matches and optional:
        return False
    assert len(matches) == 1, (system.get_name(), module_prefix, suffix, matches)
    emitter, module, name = matches[0]
    assert LIB.set_niagara_input(system, emitter, module, name, str(value)), (emitter, module, name, value)
    print('VFX_INPUT', system.get_name(), emitter, module, name, value)
    return True


def lifetime(system, minimum, maximum):
    if not set_input(system, 'InitializeParticle', 'Lifetime', maximum, optional=True):
        set_input(system, 'InitializeParticle', 'Lifetime Min', minimum)
        set_input(system, 'InitializeParticle', 'Lifetime Max', maximum)


def set_switch(system, module_prefix, name, value):
    modules = {(emitter, module) for emitter, module, _ in module_inputs(system)
               if module.startswith(module_prefix)}
    assert len(modules) == 1, (system.get_name(), module_prefix, modules)
    emitter, module = modules.pop()
    assert LIB.set_niagara_input(system, emitter, module, name, value), (module, name, value)


def burst(name, template, mat, color, size, count, duration, sparks=False):
    emitter = u.load_asset('/Niagara/DefaultAssets/Templates/Emitters/' + template)
    assert emitter, template
    system = LIB.create_niagara_from_emitter(ROOT + name, emitter)
    assert system, name
    # UE 5.8 enum assets: lifecycle 1=Self; loop behavior 1=Once.
    set_switch(system, 'EmitterState', 'Life Cycle Mode', 'NewEnumerator1')
    set_switch(system, 'EmitterState', 'Loop Behavior', 'NewEnumerator1')
    set_switch(system, 'ParticleState', 'Kill Particles When Lifetime Has Elapsed', 'true')
    set_input(system, 'SpawnBurst', 'Spawn Count', count)
    set_input(system, 'SpawnBurst', 'Spawn Time', 0.0)
    lifetime(system, duration * .65, duration)
    set_input(system, 'EmitterState', 'Loop Duration', duration)
    if sparks:
        set_input(system, 'AddVelocity', 'Velocity Speed', 300.0)
        # Shape-specific radius is hidden by this template's static context;
        # the active shape scale controls the whole spawn volume instead.
        set_input(system, 'ShapeLocation', 'Non Uniform Scale', '(X=0.02,Y=0.02,Z=0.02)')
    assert LIB.set_combat_niagara_renderers(system, mat, color, u.Vector2D(*size), 3.0)
    assert LIB.compile_and_save_niagara(system), name
    return system


def repair_ribbons(ribbon_mat=None):
    if ribbon_mat is None:
        ribbon_mat = material('M_CombatThinRibbon', 'ribbon')
    assert ribbon_mat
    ribbons = {}
    for boss, name, tint, width in (
        (False, 'NS_PlayerBladeRibbon', u.LinearColor(.1, 1.4, 2.0, 1), 4.0),
        (True, 'NS_BossBladeRibbon', u.LinearColor(2.0, .45, .04, 1), 5.5),
    ):
        system = u.load_asset(ROOT + name)
        assert system, name
        assert LIB.add_niagara_spawn_rate(system, 'LocationBasedRibbon'), name
        set_input(system, 'SpawnRate', 'SpawnRate', 120.0)
        set_switch(system, 'EmitterState', 'Life Cycle Mode', 'NewEnumerator1')
        set_switch(system, 'EmitterState', 'Loop Behavior', 'NewEnumerator1')
        set_input(system, 'EmitterState', 'Loop Duration', .5)
        lifetime(system, .08, .10)
        # Ribbon ParticleColor does not consume the user renderer binding in
        # this template. A material instance supplies the explicit blade tint.
        mi_name = 'MI_BossBladeRibbon' if boss else 'MI_PlayerBladeRibbon'
        mi = u.load_asset(ROOT + mi_name) or u.AssetToolsHelpers.get_asset_tools().create_asset(
            mi_name, ROOT.rstrip('/'), u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
        u.MaterialEditingLibrary.set_material_instance_parent(mi, ribbon_mat)
        u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, 'RibbonTint', tint)
        assert u.EditorAssetLibrary.save_loaded_asset(mi, only_if_is_dirty=False)
        assert LIB.set_combat_niagara_renderers(system, mi, tint, u.Vector2D(2, 2), width)
        assert LIB.compile_and_save_niagara(system)
        ribbons[boss] = system
    return ribbons


def main():
    spark_mat = material('M_CombatMetalSpark', 'spark')
    flash_mat = material('M_CombatReleaseGlint', 'flash')
    ribbon_mat = material('M_CombatThinRibbon', 'ribbon')
    hit = burst('NS_FinalMetalHit', 'OmnidirectionalBurst', spark_mat,
                u.LinearColor(5.0, 1.35, .12, 1), (9.0, 1.25), 11, .19, sparks=True)
    parry = burst('NS_FinalParryFlash', 'SimpleSpriteBurst', flash_mat,
                  u.LinearColor(.3, 4.5, 7.0, 1), (42.0, 42.0), 1, .11)
    aoe = burst('NS_FinalAOERelease', 'SimpleSpriteBurst', flash_mat,
                u.LinearColor(5.0, 1.8, .28, 1), (105.0, 105.0), 1, .16)
    ribbons = repair_ribbons(ribbon_mat)
    changed = []
    for path in u.EditorAssetLibrary.list_assets('/Game/Combat/Skills', recursive=True):
        skill = u.load_asset(path)
        if not isinstance(skill, u.CombatSkillDefinition):
            continue
        skill.set_editor_property('cast_effect', None)
        skill.set_editor_property('hit_effect', parry if skill.get_name() == 'DA_Parry' else hit)
        skill.set_editor_property('trail_effect', ribbons['DA_Boss_' in path])
        skill.set_editor_property('area_release_effect', aoe)
        assert u.EditorAssetLibrary.save_loaded_asset(skill, only_if_is_dirty=False)
        changed.append(path)
    report = '\n'.join(LIB.inspect_niagara(s) for s in [hit, parry, aoe, *ribbons.values()])
    dest = Path(u.Paths.project_saved_dir()) / 'Acceptance' / 'VFXAuthoredProperties.txt'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(report + '\nSKILLS\n' + '\n'.join(changed), encoding='utf-8')
    print('FINAL_VFX_AUTHORED', len(changed), 'skills; visual verification still required')


if __name__ == '__main__':
    main()
