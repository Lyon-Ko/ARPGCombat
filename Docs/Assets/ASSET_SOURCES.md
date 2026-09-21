# Combat asset provenance

Acquired / authored 2026-09-22. Original downloads are preserved in `SourceAssets/Audio/Downloads`; game-ready PCM16 WAVs are in `SourceAssets/Audio/Ready`.

## Acquired audio

| Collection | Creator | Source | License | Used output |
| --- | --- | --- | --- | --- |
| Fantasy Weapons and Apparel SFX Library | Vehicle / Jan Schupke | https://opengameart.org/content/fantasy-weapons-and-apparel-sfx-library | CC0 1.0 | MetalClash 01–04, Parry, Footstep |
| Swishes Sound Pack | artisticdude | https://opengameart.org/content/swishes-sound-pack | CC0 1.0 | SwordSwing 01–04, Dash, Burst layer |
| Impact Sounds | Kenney | https://kenney.nl/assets/impact-sounds | CC0 1.0 | Burst metal layer |
| The Final Battle | skrjablin | https://opengameart.org/content/the-final-battle | CC0 1.0 | BattleMusic |

CC0 legal text: https://creativecommons.org/publicdomain/zero/1.0/

Final latency pass: all original game-ready WAVs were retained byte-for-byte in `SourceAssets/Audio/OriginalReady`. Sword swings, metal clashes, Parry and Dash were trimmed to retain 2 ms before the first sample exceeding -60 dBFS, with a 0.5 ms fade inside that retained lead to avoid a hard discontinuity. No gain was raised and no normalization was applied. Burst required no trim; Footstep and BattleMusic were unchanged. `Docs/Assets/AudioTrimReport.json` records exact frame/time removals and original/final SHA256; `AudioValidation.json` records the final analysis. Rebuild order is `prepare_audio.py`, `trim_combat_audio.py`, then `validate_audio.py`.

Vehicle's original `readme.txt` and Kenney's `License.txt` are included with the extracted packages. Attribution is not required by CC0; the above credits are retained voluntarily. `prepare_audio.py` resamples to 48 kHz mono for SFX, adjusts speed/level, and layers metal, swish, and an original synthesized low-frequency transient for Burst. Music remains 44.1 kHz stereo PCM16 at reduced gain. The source music contains an audible pause at its loop boundary; use a crossfade if a seamless battle loop is required.

Direct downloads:

- https://opengameart.org/sites/default/files/weapons-apparel.zip
- https://opengameart.org/sites/default/files/swishes.zip
- https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip
- https://opengameart.org/sites/default/files/the_final_battle.ogg

## Character / animation source and authorship

- Base skeleton and body: local Epic Manny export from `D:/UEproject/UE-ANIMATION/Exchange/SKM_Manny_Simple.fbx`. Original source asset is `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple`; skeleton `/Game/Characters/Mannequins/Meshes/SK_Mannequin`. Epic asset terms apply; no ownership of the Manny base is claimed.
- Original mesh work: Player / Boss plate armor, helmet, tabard, cape and two swords authored procedurally for this project in `build_armored_characters.py`. These are backup art assets; the final character direction is the user-acquired Epic Paragon packs below.
- Original animation work: 19 purpose-authored sword animation FBXs at 60 fps. `build_sword_animations.py` uses hand/blade targets with geometric limb solving, spine twist, pelvis weight transfer, stance changes and finger curl. No boxing animations were repurposed. Per-clip JSON includes damage windows and gameplay events.
- Sword geometry origin: grip center, local +X toward blade tip, centimeters, blade starts at X=12 cm. Player blade tip X=106 cm; Boss X=137 cm. Final grip socket: attach to `hand_r`, location (-9,-2.5,0) cm in the bone's local coordinates. Socket rotation maps Sword X to Hand Z, Sword Y to Hand X, Sword Z to Hand Y; matrix rows are [[0,1,0],[0,0,1],[1,0,0]]. This accounts for Manny's palm extending along hand-local -X and fingers arranged along local Z. All three joints on each right finger and thumb are posed around the handle. Per-clip JSON stores the exact socket matrix.
- Animations are in-place; gameplay code supplies dash/jump movement. Air poses must be played while the actor is airborne. Cloth pieces have skin weights and do not include a cloth simulation asset.

## User-acquired Epic packs

- Kwang: https://www.fab.com/listings/f4c67e92-b976-4b5b-ab9f-4c25b010f6f3
- Greystone: https://www.fab.com/listings/122fd7bf-6f12-4304-a930-cccbbacdaebc

The user confirmed both free packs were acquired in their Epic account. The signed-in Epic Games Launcher showed both in My Library. On 2026-09-22 both were added to the existing `D:/UEproject/Combat/Combat.uproject` through the Launcher, selecting the verified compatible 5.8 project. These assets remain subject to the applicable Epic license accepted by the account. Their listings permit use in Unreal Engine projects and prohibit using the PARAGON trademark to name or advertise the game. Do not label the game with that trademark. No third-party mirrors were used.

Greystone installation completed and was independently verified on disk under `Content/ParagonGreystone`. A filesystem inventory is recorded in `Greystone_installed_manifest.json`. Main mesh `/Game/ParagonGreystone/Characters/Heroes/Greystone/Meshes/Greystone`, skeleton sibling `Greystone_Skeleton`. Native attacks include `Attack_PrimaryA/B/C` and their Montages, `Attack_A/B/C/D` Fast/Med/Slow variants, `Jump_Melee`, `Attack_RMB`, and `Ability_Ultimate`. Optional skin meshes include Dragonlord, Tough, Novaborn, and WhiteTiger. Use the supplied native sword animations where suitable.

Kwang installation also completed. The Launcher download manager showed both packs as **Installed**, with no active downloads. Kwang's files were independently verified under `Content/ParagonKwang`; the complete inventory is `Kwang_installed_manifest.json`.

Kwang main mesh: `/Game/ParagonKwang/Characters/Heroes/Kwang/Meshes/Kwang_GDC`. Skeleton: `/Game/ParagonKwang/Characters/Heroes/Kwang/Meshes/Kwang_Skeleton`. Mesh variations in the same folder: `KwangAlbino`, `KwangRosewood`, `KwangSunrise`.

Native animation root: `/Game/ParagonKwang/Characters/Heroes/Kwang/Animations/`. It contains `PrimaryAttack_A_Slow`, `PrimaryAttack_B_Slow`, `PrimaryAttack_C_Slow`, `PrimaryAttack_D_Slow` and their `_Montage` assets; `PrimaryAttack_Air`; `Ability_RMB` / `Ability_RMB_NoSword`; `Ability_R_Intro` / `Ability_R`; `Ability_Q_Throw` / `Ability_Q_Catch`; jump start/apex/land/recovery, sprint and jog locomotion; `Stun_Start`, `Stun_Loop`, `Death_Bwd`; and `Kwang_AnimBlueprint`. Names identify candidate source animations, not a claim that every native ability is already mapped to the demo's gameplay.

## Build tooling

- Existing local Blender: `D:/blender/blender.exe`, 5.1.1. No Blender installation was needed.
- Audio conversion runtime: Blender's bundled Python, plus PyPI SoundFile 0.14.0, cffi 2.1.1 and pycparser 3.0 installed only into `SourceAssets/Tools/python-libs`.
- Exclude runtime dependencies and redundant source download archives from Git: `SourceAssets/Tools/python-libs/`, `SourceAssets/Audio/Downloads/`, `SourceAssets/**/build.log`, `SourceAssets/**/*Build.log`, `SourceAssets/**/*.blend1`.

Game-ready files and deterministic build scripts should be retained. The audio manifest lists sample rate, duration, peak level and SHA256 for verification.
