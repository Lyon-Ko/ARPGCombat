# Integration review queue

These are concrete remaining quality/acceptance checks, not additional user approval gates. Root coordinates batches so editor work can continue between builds.

## After first successful PIE
- Verify all regular and derived player inputs, boss StateTree startup and actual montage event flow. No permanent Busy, idle AI, double weapon or skeleton mismatch.
- Real Kwang/Greystone meshes/native locomotion, distinct four player attacks, three Boss hits ending heavy, genuine left/right/back jumps. Inspect source clips before assuming Ultimate is a charge attack (Greystone's Paragon ultimate may be resurrection).
- Charged AOE requires a visible release flash, precise .18 sec flash-to-damage delay, and a low-opacity readable radial telegraph. Opaque cylinder growth is not accepted final presentation.
- Bind/tune real ribbon/hit/wave effects and cue sounds. Native game currently has configured hooks but data binding and appearance need verification.
- Confirm hitstop is implemented and bounded (it was absent in the first Feedback source review). It should affect confirmed impacts, not every generic cue. Ensure it does not accidentally shorten the AOE reaction window.
- Add/verify footstep cadence, battle music, defeat sound and actual death animation or ragdoll. Standing idle characters with only result text are insufficient final defeat presentation.
- Verify cast/swing sound timing: a sword swish should coincide with visible swing, not always start at skill activation. Parry sound should play on successful contact. AudioValidation.json reports some leading silence up to76ms; trim source or schedule appropriately when revisiting audio assets.
- Review camera pitch/framing after lock/unlock; unlocked distance should restore; soft target assistance should respect proximity/view and not snap actor toward distant boss on every ability (including parry/backdash).
- Ensure ground Attack1 cannot bypass two-air-attack budget, direct skill API respects activation conditions, jump/cancel permits intended short aerial strings.
- Do not leak previously released projectiles through reset after the skill has completed; assert actual world actor/component counts after20cycles.
- Verify CJK typography and editable UMG layout. PhaseText should show stage, not duplicate the BossName label. Paused settings should be styled and preferably designer-editable; master sound controls actual music/effects route.

## Required final evidence
Docs/Acceptance.md defines timing/death/cancel tests, 30/60fps,20actual fight/reset bouts, default map cold launch, 1080p high render performance, native input and visual inspection, and a BP/Montage/data-only extension example. Save actual evidence; do not replace it with inferred passes.
