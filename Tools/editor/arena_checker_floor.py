"""Build a 100 cm world-aligned checker material for the combat arena floor."""
import unreal as u


MATERIAL_PATH = '/Game/Combat/Materials/M_ArenaChecker'
MAP_PATH = '/Game/Combat/Maps/L_CombatArena'


def create_checker_material():
    material = u.load_asset(MATERIAL_PATH)
    if not material:
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_ArenaChecker', '/Game/Combat/Materials', u.Material, u.MaterialFactoryNew()
        )
    if not material:
        raise RuntimeError('Could not create arena checker material')

    lib = u.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)

    def node(cls, x, y):
        return lib.create_material_expression(material, cls, x, y)

    position = node(u.MaterialExpressionWorldPosition, -1000, 0)
    cell_size = node(u.MaterialExpressionConstant, -1000, 300)
    cell_size.set_editor_property('r', 100.0)  # Unreal units: 100 cm per square.

    coordinates = []
    for axis, y in (('r', -200), ('g', 100)):
        mask = node(u.MaterialExpressionComponentMask, -800, y)
        mask.set_editor_property('r', axis == 'r')
        mask.set_editor_property('g', axis == 'g')
        mask.set_editor_property('b', False)
        mask.set_editor_property('a', False)
        lib.connect_material_expressions(position, '', mask, '')
        scaled = node(u.MaterialExpressionDivide, -600, y)
        lib.connect_material_expressions(mask, '', scaled, 'A')
        lib.connect_material_expressions(cell_size, '', scaled, 'B')
        square = node(u.MaterialExpressionFloor, -400, y)
        lib.connect_material_expressions(scaled, '', square, '')
        coordinates.append(square)

    summed = node(u.MaterialExpressionAdd, -200, -50)
    lib.connect_material_expressions(coordinates[0], '', summed, 'A')
    lib.connect_material_expressions(coordinates[1], '', summed, 'B')
    divisor = node(u.MaterialExpressionConstant, -200, 180)
    divisor.set_editor_property('r', 2.0)
    parity = node(u.MaterialExpressionFmod, 0, -50)
    lib.connect_material_expressions(summed, '', parity, 'A')
    lib.connect_material_expressions(divisor, '', parity, 'B')
    checker = node(u.MaterialExpressionAbs, 200, -50)
    lib.connect_material_expressions(parity, '', checker, '')

    dark = node(u.MaterialExpressionConstant3Vector, 0, -300)
    dark.set_editor_property('constant', u.LinearColor(0.075, 0.095, 0.115, 1))
    light = node(u.MaterialExpressionConstant3Vector, 0, -190)
    light.set_editor_property('constant', u.LinearColor(0.27, 0.30, 0.33, 1))
    color = node(u.MaterialExpressionLinearInterpolate, 430, -130)
    lib.connect_material_expressions(dark, '', color, 'A')
    lib.connect_material_expressions(light, '', color, 'B')
    lib.connect_material_expressions(checker, '', color, 'Alpha')
    lib.connect_material_property(color, '', u.MaterialProperty.MP_BASE_COLOR)

    roughness = node(u.MaterialExpressionConstant, 430, 130)
    roughness.set_editor_property('r', 0.9)
    lib.connect_material_property(roughness, '', u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(material)
    if not u.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError('Could not save arena checker material')
    return material


def apply_checker_to_floor(material=None):
    material = material or create_checker_material()
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0] != MAP_PATH:
        levels.load_level(MAP_PATH)
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    floors = [actor for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
              if actor.get_actor_label() == 'Combat_Floor']
    if len(floors) != 1:
        raise RuntimeError(f'Expected one Combat_Floor, found {len(floors)}')
    floors[0].static_mesh_component.set_material(0, material)
    if not u.EditorLoadingAndSavingUtils.save_map(world, MAP_PATH):
        raise RuntimeError('Could not save combat arena map')
    print('CHECKER_FLOOR_SAVED', material.get_path_name(), MAP_PATH)


if __name__ == '__main__':
    apply_checker_to_floor()
