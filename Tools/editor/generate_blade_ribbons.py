"""Use the engine's location-based emitter, not the moving-particle demo system."""
import unreal as u
ROOT='/Game/Combat'
emitter=u.load_asset('/Niagara/DefaultAssets/Templates/Emitters/LocationBasedRibbon')
assert emitter
systems={}
for boss,name,color,width in [(False,'NS_PlayerBladeRibbon',u.LinearColor(.08,.72,1,1),4.0),(True,'NS_BossBladeRibbon',u.LinearColor(1,.24,.035,1),5.5)]:
    system=u.CombatEditorLibrary.create_niagara_from_emitter(ROOT+'/VFX/'+name,emitter)
    assert system,name
    assert u.CombatEditorLibrary.configure_niagara(system,color,6,width),name
    systems[boss]=system
    print('LOCATION_RIBBON',name,system.get_path_name())
for path in u.EditorAssetLibrary.list_assets(ROOT+'/Skills',True):
    data=u.load_asset(path)
    if isinstance(data,u.CombatSkillDefinition):
        data.set_editor_property('trail_effect',systems['DA_Boss_' in path])
        u.EditorAssetLibrary.save_loaded_asset(data)
print('REAL_BLADE_RIBBONS_ASSIGNED')
