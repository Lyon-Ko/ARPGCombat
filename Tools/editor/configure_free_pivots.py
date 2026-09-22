"""Bind the baked free-facing turns without altering locked pivots or tuning."""
import unreal as u

root = '/Game/Combat/Animations/Native/Kwang'
blueprint = u.load_asset(root + '/ABP_CombatKwang2D')
defaults = u.get_default_object(blueprint.generated_class())
for direction in ('Left', 'Right'):
    sequence = u.load_asset(root + '/A_FreePivot_' + direction)
    assert sequence and not sequence.get_editor_property('enable_root_motion')
    factory = u.AnimMontageFactory()
    factory.source_animation = sequence
    factory.target_skeleton = sequence.get_editor_property('skeleton')
    name = 'AM_FreePivot_' + direction
    montage = u.load_asset(root + '/' + name)
    if not montage:
        montage = u.AssetToolsHelpers.get_asset_tools().create_asset(name, root, u.AnimMontage, factory)
    tracks = list(montage.get_editor_property('slot_anim_tracks'))
    tracks[0].set_editor_property('slot_name', 'DefaultSlot')
    track = tracks[0].get_editor_property('anim_track')
    segments = list(track.get_editor_property('anim_segments'))
    for prop, value in dict(anim_reference=sequence, anim_start_time=0.,
                            anim_end_time=sequence.get_play_length(),
                            anim_play_rate=1., looping_count=1).items():
        segments[0].set_editor_property(prop, value)
    track.set_editor_property('anim_segments', segments)
    tracks[0].set_editor_property('anim_track', track)
    montage.set_editor_property('slot_anim_tracks', tracks)
    montage.set_editor_property('rate_scale', 1.)
    montage.set_editor_property('blend_out_trigger_time', 0.)
    for prop, duration in [('blend_in', .07), ('blend_out', .14)]:
        blend = montage.get_editor_property(prop)
        blend.set_editor_property('blend_time', duration)
        montage.set_editor_property(prop, blend)
    assert u.CombatEditorLibrary.rebuild_montage(montage)
    defaults.set_editor_property('free_pivot_' + direction.lower(), montage)
assert u.CombatEditorLibrary.compile_and_save(blueprint)
print('FREE_PIVOTS_CONFIGURED: locked clips and locomotion tuning preserved')
