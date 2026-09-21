"""Real montage clips; runtime notify metadata is filled once module reloads."""
import unreal as u
from pathlib import Path
import json

root=Path(u.Paths.project_dir())
assets=u.AssetToolsHelpers.get_asset_tools()
track='CombatEvents'
definitions={
 'Attack1':'A_Player_Sword_01','Attack2':'A_Player_Sword_02','Attack3':'A_Player_Sword_03','Attack4':'A_Player_Sword_04',
 'DashStrike':'A_Player_DashStrike','Air1':'A_Player_Air_01','Air2':'A_Player_Air_02','Plunge':'A_Player_Plunge',
 'Parry':'A_Player_Parry','Riposte':'A_Player_Riposte','Boss.Combo1':'A_Boss_Combo_01','Boss.Combo2':'A_Boss_Combo_02','Boss.Combo3':'A_Boss_Combo_03',
 'Boss.AOE':'A_Boss_ChargeAOE','Boss.DashSlash':'A_Boss_FrontDashSlash','Boss.LeapLeft':'A_Boss_JumpWave_L','Boss.LeapRight':'A_Boss_JumpWave_R','Boss.LeapBack':'A_Boss_JumpWave_Back','Dash':'MM_Dash'
}
notify_cls=getattr(u,'CombatAnimNotify_Event',None)
def gameplay_tag(name):
    value=u.GameplayTag()
    assert value.import_text('(TagName="'+name+'")')
    assert str(value.get_editor_property('tag_name'))==name
    return value
report=[]
for skill,clip in definitions.items():
    sequence=u.load_asset('/Game/Combat/Animations/Sequences/'+clip)
    if skill=='Dash' and not sequence:
        sequence=u.EditorAssetLibrary.duplicate_asset('/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Dash','/Game/Combat/Animations/Sequences/MM_Dash')
    if skill=='Dash':
        sequence.set_editor_property('enable_root_motion',False)
        sequence.set_editor_property('force_root_lock',True)
        u.EditorAssetLibrary.save_loaded_asset(sequence)
    if not sequence: continue
    name='AM_'+skill.replace('.','_')
    path='/Game/Combat/Animations/Montages/'+name
    factory=u.AnimMontageFactory()
    factory.source_animation=sequence
    factory.target_skeleton=sequence.get_editor_property('skeleton')
    montage=u.load_asset(path) or assets.create_asset(name,'/Game/Combat/Animations/Montages',u.AnimMontage,factory)
    montage.set_editor_property('rate_scale',4.2 if skill=='Dash' else 1.0)
    for property_name,blend_time in [('blend_in',.045),('blend_out',.065)]:
        blend=montage.get_editor_property(property_name)
        blend.set_editor_property('blend_time',blend_time)
        montage.set_editor_property(property_name,blend)
    meta=json.loads((root/'SourceAssets/Animations'/(clip+'.json')).read_text()) if skill!='Dash' else {'damage':None,'extra':{}}
    duration=sequence.get_editor_property('sequence_length')
    events=[]
    damage=meta.get('damage')
    extra=meta.get('extra',{})
    if damage and skill!='Boss.AOE': events += [(damage[0],'HitOpen'),(damage[1],'HitClose')]
    if skill=='Boss.AOE': events += [(extra.get('telegraph',.08),'AreaWarning'),(extra.get('flash',1.18),'AreaRelease')]
    if 'projectile' in extra: events += [(extra['projectile'],'Projectile')]
    if skill not in ('Parry','Boss.AOE','Dash'):
        events += [(extra.get('jump', max(.02,(damage or [.2])[0]-.12)),'Move')]
    if skill.startswith('Attack') or skill in ('Air1','Air2'):
        events += [(min(duration-.08,(damage or [0,.3])[1]+.03),'ComboOpen')]
    events += [(max(.1,duration-.15),'Cancelable'),(duration-.025,'Finish')]
    if not u.AnimationLibrary.is_valid_anim_notify_track_name(montage,track): u.AnimationLibrary.add_animation_notify_track(montage,track)
    if notify_cls:
        u.AnimationLibrary.remove_animation_notify_events_by_track(montage,track)
        for time,event in sorted(events):
            notify=u.AnimationLibrary.add_animation_notify_event(montage,track,min(time,duration-.01),notify_cls)
            # GameplayTag struct text import validates against loaded native tags.
            notify.set_editor_property('event_tag',gameplay_tag('Combat.Event.'+event))
    u.EditorAssetLibrary.save_loaded_asset(montage)
    report.append({'skill':skill,'montage':path,'duration':duration,'events':events,'runtime_notifies_authored':bool(notify_cls)})
print('MONTAGES',json.dumps(report))
