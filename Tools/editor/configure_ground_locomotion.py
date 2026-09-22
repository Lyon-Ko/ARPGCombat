"""Configure ground reversals without rebuilding existing animation graphs.

Original Paragon assets remain read-only. Run after generate_native_characters.
"""
import unreal as u

ROOT = '/Game/Combat/Animations/Native'
tools = u.AssetToolsHelpers.get_asset_tools()


def configure():
    for hero in ('Kwang', 'Greystone'):
        abp = u.load_asset(f'{ROOT}/{hero}/ABP_Combat{hero}2D')
        assert abp
        assert u.CombatEditorLibrary.configure_locomotion_blending(abp)
        defaults = u.get_default_object(abp.generated_class())
        # Preserve authored positions/clips, removing only the speed-up factors.
        blend_space = u.load_asset(f'{ROOT}/{hero}/BS_Locomotion2D')
        defaults.set_editor_property('ground_blend_space', blend_space)
        samples = list(blend_space.get_editor_property('sample_data'))
        for sample in samples:
            sample.set_editor_property('rate_scale', 1.0)
            clip = sample.get_editor_property('animation')
            if clip.get_path_name().startswith(ROOT + '/'):
                clip.set_editor_property('rate_scale', 1.0)
                assert u.EditorAssetLibrary.save_loaded_asset(clip)
        blend_space.set_editor_property('sample_data', samples)
        blend_space.set_editor_property('axis_to_scale_animation', u.BlendSpaceAxis.BSA_NONE)
        assert u.CombatEditorLibrary.rebuild_blend_space(blend_space)
        for direction, prop in [('Fwd', 'pivot_forward'), ('Bwd', 'pivot_backward'),
                                ('Left', 'pivot_left'), ('Right', 'pivot_right')]:
            source = f'/Game/Paragon{hero}/Characters/Heroes/{hero}/Animations/Jog_{direction}_Pivot180'
            path = f'{ROOT}/{hero}/A_Jog_{direction}_Pivot180'
            sequence = u.load_asset(path) or u.EditorAssetLibrary.duplicate_asset(source, path)
            assert sequence
            u.AnimationLibrary.remove_all_animation_notify_tracks(sequence)
            sequence.set_editor_property('enable_root_motion', False)
            sequence.set_editor_property('force_root_lock', True)
            sequence.set_editor_property('rate_scale', 1.0)
            factory = u.AnimMontageFactory()
            factory.source_animation = sequence
            factory.target_skeleton = sequence.get_editor_property('skeleton')
            name = f'AM_Pivot_{direction}'
            montage = u.load_asset(f'{ROOT}/{hero}/{name}') or tools.create_asset(
                name, f'{ROOT}/{hero}', u.AnimMontage, factory)
            tracks = list(montage.get_editor_property('slot_anim_tracks'))
            tracks[0].set_editor_property('slot_name', 'DefaultSlot')
            track = tracks[0].get_editor_property('anim_track')
            segments = list(track.get_editor_property('anim_segments'))
            segments[0].set_editor_property('anim_reference', sequence)
            segments[0].set_editor_property('anim_start_time', 0.0)
            # Keep the complete source: neither the turn nor its recovery is trimmed.
            segments[0].set_editor_property('anim_end_time', sequence.get_play_length())
            segments[0].set_editor_property('anim_play_rate', 1.0)
            segments[0].set_editor_property('looping_count', 1)
            track.set_editor_property('anim_segments', segments)
            tracks[0].set_editor_property('anim_track', track)
            montage.set_editor_property('slot_anim_tracks', tracks)
            montage.set_editor_property('rate_scale', 1.0)
            montage.set_editor_property('enable_auto_blend_out', True)
            # Start fading only after the full clip, not before its final frames.
            montage.set_editor_property('blend_out_trigger_time', 0.0)
            for prop_name, seconds in [('blend_in', .07), ('blend_out', .14)]:
                blend = montage.get_editor_property(prop_name)
                blend.set_editor_property('blend_time', seconds)
                montage.set_editor_property(prop_name, blend)
            u.AnimationLibrary.remove_all_animation_notify_tracks(montage)
            defaults.set_editor_property(prop, montage)
            assert u.EditorAssetLibrary.save_loaded_asset(sequence)
            assert u.CombatEditorLibrary.rebuild_montage(montage)
            assert abs(montage.get_play_length() - sequence.get_play_length()) < .001
        assert u.CombatEditorLibrary.compile_and_save(abp)

    # Only basic ground attacks opt into movement recovery cancellation.
    # Dash/parry/air/area timings retain their existing gameplay contract.
    for number in range(1, 5):
        skill = u.load_asset(f'/Game/Combat/Skills/DA_Attack{number}')
        skill.set_editor_property('allow_movement_cancel', True)
        skill.set_editor_property('locomotion_blend_out', .14)
        skill.set_editor_property('interrupt_blend_out', .08)
        assert u.EditorAssetLibrary.save_loaded_asset(skill)
    print('GROUND_LOCOMOTION_CONFIGURED: full-length pivots, original playback rates, live slot source, ground attack recovery')


configure()
