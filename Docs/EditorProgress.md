# Editor asset generation progress

**FINAL PLAYABLE HANDOFF 02:00 — REMOTE RELEASED TO COORDINATOR/REGRESSION. No further editor calls from this worker.** Floating in-process PIE is running, encounter RESET then PAUSED; press P or SetGamePaused(false) to resume. No editor callbacks remain. All /Game/Combat assets and arena saved before PIE. Source frozen. Root/assigned regression worker now owns sole remote and UI.

Final asset verification: **33 Blueprints compile/save/reload PASS;39 notified montage packages reload PASS;208 assets under /Game/Combat.** This includes editable GAS task/9event-branch graphs, both real 2D15sample native AnimBPs, designer Chinese HUD, StateTree, unique-tag extension, camera shake BP. Camera feedback script executed successfully (.12s, pitch.25deg, Z1cm), bound bothcharacters; Parry.hit_effect=NS_ParryFlash. Included in run_pipeline.py. Its long docstring trips native remote auto-file detection when supplied via -File; I executed `exec(compile(Path(...).read_text(),"generate_camera_feedback","exec"),globals())`; run_pipeline's runpy is unaffected. No environment script changed.

**Actual autonomous AI evidence:** final high-scalability floating PIE observed ST_CombatBoss executing4actions in8seconds; player300→232HP, ABP_CombatKwang2D_C and ABP_CombatGreystone2D_C active. Saved/Acceptance/PlayableHandoff.json. Request was1920x1080 and engine CSV reports1920x1080, but `PlayerController.get_viewport_size()` returns **1920x1082** (floating client sizing discrepancy). Do not label this exact1080p performance acceptance without correcting/recording dimensions. Recorded Slate deltas are warmup diagnostics only, not GPU performance proof.

**Remaining coordinator acceptance:** 30/60fps timing+20real fight/reset bouts, native keyboard/mouse/camera/pause/settings review, final wave/ribbon/AOE/death visual quality and exact1080p performance. Initial milestone real graph invocation+reload and fixture montage NotifyState/WBP/Niagara PASS. All19authored abilities and all damaging skills have actual corrected-pose PIE activation/montage/damage/cleanup evidence; final standalone newtag normal-input chain Attack1→2→3→Example.CrescentBurst produced130damage and restored defaults (Saved/Acceptance/SkillExtensionNewTagPIE.json). No claim that outstanding formal regression/visual acceptance has passed.

**CURRENT 01:57: Final unique-tag extension actual normal-input PIE PASS.** InjectPlayerKey LMB produced Attack1→Attack2→Attack3→Combat.Skill.Example.CrescentBurst; total130damage, cleanfinish, original playerdefinitions and Attack3.NextSkillTag restored and saved. Evidence Saved/Acceptance/SkillExtensionNewTagPIE.json. Temporary append required BP compile/save to propagate new array entry into PIE spawn (first unsavedCDO attempt onlyran3hits; resolved). Both 2D15sample native BlendSpaces/AnimBPs generated/compiled; LocationBasedRibbon systems created by stock Niagara factory and bound width4/5.5; wave mesh/material/box props all3leaps assigned; grounded warningring assigned. Final packagevalidation running; awaiting coordinator-owned generate_camera_feedback.py then run it, save and1920x1080hand off.

**CURRENT: InputFX_07 BUILD READY acknowledged; resuming sole remote for final2Dlocomotion, Ribbon/wave binding, unique-tag extension, reload and1920x1080 playable handoff. Source frozen; no additional assets outside required final stages.**

**Requested Direction/2D locomotion helper patch added 01:53; source READY FOR BUILD again.** CreateLocomotion connects existing CombatAnimInstance.Direction to BlendSpacePlayer Y for non-BlendSpace1D assets, retains XSpeed and1D fallback. Postbuild native authoring will create 2D Speed/Direction with Jog_Fwd/Left/Right/Bwd and new AnimBP paths to avoid reusing old1D graphs. Remote remains idle, allassets already saved; coordinator may build now.

**CURRENT HANDOFF 01:52: READY FOR BUILD. PIE stopped, /Game/Combat and arena map saved. Source/CombatEditor frozen with StartPIEWindow + CreateNiagaraFromEmitter; final isolated CPP compile PASS (added NiagaraEditor public/UHT paths and DLLIMPORT defines to old rsp invocation only; Build.cs has actual dependency). Coordinator may close/build/restart. No further remote calls until BUILD READY.**

Latest actual checks: all19skills activated/real native montage/ended cleanly; every damaging skill has now produced its expected damage in corrected-pose PIE (BossCombo2 latest27; Air1/2 22/30 at250cm testheight). Dash250cm. 30BP compile/save/reload PASS; 39montages with notifications reload PASS;195Combatassets at that check. Native sourceRootLock offmotion/rootlocked, original packs unchanged. Extension64damage clean finish, samplegraph/data/native montage editable and defaults restored. Final close-range data: BossCombo1/2/3 pressure steps30/35/55, C-sweep for middle strike. Native ground bounds read: Kwang Zmin-.095/Zmax194.87; Greystone Zmin-.508/Zmax205.04. Aligned meshoffset to actual capsule: Player-92, Boss-104 (radius43, halfheight104 proportional to1.13scale), spawned Boss atZ110. This final capsule/foot alignment awaits postbuild visual rerun; prior damage evidence predates only this small fit change.

After BUILD READY: run generate_fx_meshes.py to bind new projectile fields; create LocationBasedRibbon systems via new helper + ConfigureNiagara, assign trail_effect allskills; validate and use StartPIEWindow for root/20bout regression handoff. Remaining acceptance is actual StateTree autonomous bouts, 30/60fps/1080p performance, native UI review, thin-ribbon/wave/grounded-ring visual tuning. Current allskill matrix stops AI deliberately, so it does not establish AI acceptance.

**Source final tiny addition before handoff: CreateNiagaraFromEmitter for real LocationBasedRibbon template.** Existing AttributeReaderTrails is a demonstration system with unrelated moving particles, unsuitable final blade trail. Python cannot add emitter to NiagaraSystem (actual stub verified). Added editor-only NiagaraEditor dependency and stock factory InitializeSystem + AddEmitterToSystem(copy=true), confined /Game/Combat. Next build includes this plus StartPIEWindow. All recent melee checks now pass including BossCombo2=27 after native C waist sweep. Finishing save/assetvalidation, then remote handoff.

**CURRENT 01:47: Source/CombatEditor READY for next build: StartPIEWindow(1920,1080) added per request, isolated cl compile PASS. Finishing one short BossCombo2 retest then save/handoff below.** Native corrected Air1/Air2 damage22/30 at250cm startheight. BossCombo1 close miss was genuine over-lunge: hand/bladebase overshot target capsule; pressure step now30cm (was170), observed24damage. Combo3 step55 observed38damage. Combo2 replaced high native B stroke with distinct native C waist sweep, notify .13.. .23, testing now. No trace broadening. Extension actual PIE PASS: GA_CrescentBurst + native AM + data installed temporarily at existing Attack4 slot, total64damage (32melee+32AOE), clean finish; saved timeline Saved/Acceptance/SkillExtensionPIE.json. Player defaults immediately restored, no runtime C++ changed for extension.

Original FX imported: /Game/Combat/VFX/SM_SwordWave actual halfbounds22.625,90,3.5; SM_WarningRing halfbounds51,51,.125. Editable M_SwordWave additive ember and plain uniform M_WarningRing translucent emissive authored. Ring assigned AOE/extension. generate_fx_meshes.py gates new projectile props until next build; rerun it after build to bind all3leap mesh/material/halfextent24,85,20. Pipeline includes FX stage after native/extension. Runtime must retain warning ring on floor at release per coordinator contract; current DLL still expands/moves it until next build.

**CURRENT 01:43: Rotator repair actual PIE rerun: all19 activate/observe montage/end cleanly. Player Attack1/2/3/4 now damage18/22/26/38, DashStrike32, Riposte85, Plunge50; Dash250cm. BossCombo3=38, DashSlash40, AOE65, all3wave28. BossCombo1/2 still close140cm misses; Air1/2 from deliberately450cm setup miss standing target but activate, need appropriate aerial-height test. Fresh endpoint tracing underway, remaining close-range findings will be documented before playable handoff.** No more GDI screenshots per coordinator; UE capture only, root owns UI capture. Both native mesh rotations now verified named yaw=-90, boss actor yaw180, sun pitch=-48/yaw=-32. Pipeline includes native stage before extension/validation, plus sky atmosphere.

**CURRENT IMPORTANT ROOT CAUSE 01:41: Native PIE endpoint capture exposed all character mesh rotations wrong: UE Python Rotator positional args are roll,pitch,yaw, so `Rotator(0,-90,0)` set PITCH=-90, not YAW. Sword bases were below ground, explaining misses and elevated/sideways render. All Tools/editor constructors now use named yaw/pitch fields. Regenerating character defaults/placed boss and rerunning real PIE; earlier damage/render evidence is diagnostic only. No runtime repair needed for this issue.** SkyAtmosphere background added/saved; Chinese WBP visually readable in actual screenshot Saved/Acceptance/EditorNativePIE.png (prior to rotation repair).

**CURRENT 01:38: Native Kwang player/Greystone boss generated and arena saved; styled WBP now compile-valid. 30 Blueprints compile/save/reload PASS; 20 original/extension montages notify/save/reload PASS (native montage reload separately next). Running actual native-character 19-skill PIE matrix now.** Both meshes are /Game/Combat copies with mesh-only BladeBase/BladeTip sockets, no double weapon. Both native AnimBPs inherit CombatAnimInstance, real Speed BlendSpace/air state/DefaultSlot. All19 skill data now native matching-skeleton montages; source notifies stripped only on copies, rootmotion off/rootlocked. Socket geometry measured from skin weights: Kwang localY -18..-147; Greystone bottom localZ14 to top localZ78. Native blade sample report Saved/Acceptance/NativeBladeMotion.json; no widened trace radii (12cm). Death/hitreact native montages, real footsteps and battle music assigned. New WBP successful helper compile proves prior property conflict resolved.

**CURRENT: Presentation_06 BUILD READY acknowledged. Resuming sole remote ownership: regenerate styled HUD and third-batch audio/data properties, inspect native Kwang/Greystone weapon bones/animations, adapt under /Game/Combat. Previous READY FOR BUILD messages below are historical.**

**Requested tiny input seam added; READY FOR BUILD again.** `InjectPlayerKey(Controller, Key, bPressed)` validates controller/key and PIE world, then uses UE5.8 `FInputKeyEventArgs::CreateSimulated` through real `PlayerController::InputKey`. Added InputCore editor dependency. Source frozen; remote remains paused. Existing RebuildBlendSpace and UMG fixes included. Coordinator can proceed with full UHT/build.

Isolated editor C++ compile including requested InputKey seam PASS (exit0). Native Paragon read-only inventory script prepared: component-space reference/animation weapon bone transforms, sockets, rootmotion flags and original notifies. Awaiting BUILD READY to run it; no remote requests during handoff.

**CURRENT HANDOFF: READY FOR BUILD. PIE matrix finished, PIE stopped, /Game/Combat and current map saved (01:25). Editor source frozen with WBP progressbar fix and tiny RebuildBlendSpace helper (resamples/validates native blendspace data, unreflected in Python). Coordinator may close/build/restart now. Remote calls paused until BUILD READY.**

01:21: ABP_Combat creation/compile/save PASS (grounded/airborne state machine, DefaultSlot); ST_CombatBoss creation/compile/save PASS (AI schema, 3 real task states). Styled WBP compile caught native private UPROPERTY name collisions on the three ProgressBars. Exact fix now in helper: `B->bIsVariable=false` because runtime finds controls by name. **Please include this one-line editor repair in next coordinated build, after I finish independent combat PIE.** Using native HUD fallback temporarily; styled WBP is NOT accepted yet. Ability override issue resolved via available-node action in actual Gameplay Ability Graph; all19 compiled.

Initial forced-skill PIE diagnostic completed, full data table appended below. 18/19 requested skills activated; all active cases observed ABP_Combat_C + real montage, ended cleanly. Actual damage observed on Attack2(22), DashStrike(32), Plunge(50), BossCombo2(27), AOE(65), all3projectiles(28 each). Other sword trajectories missed fixed140cm target; not claimed as combat acceptance. Air2 immediate cancel/setup rejected (test needs next-frame chain). Dash exposed copied template root motion causing942cm movement; asset root motion now disabled/root locked, pending retest. These are concrete findings for next validation, not passes. Native Paragon meshes now available; after build will adapt native clips/locomotion and tune blade endpoints. No extra skeleton socket helper needed: UE5.8 SkeletalMesh.add_socket is actually reflected.

2026-09-22: Editor worker owns Source/CombatEditor, Tools/editor/*.py and Content/Combat only. Architecture and remote scripts read. No builds, restarts, config changes or commits performed.

Current live engine exposes the expanded BlueprintGraphEditor API, AnimMontageFactory source_animation and AnimationLibrary notify-state authoring. Running real create/connect/compile/invoke/save/reload fixtures now. Runtime headers and produced model/animation directories were absent on initial inspection; audio Ready exists. Native helper design will follow actual runtime headers when supplied.

## Milestone 1 PASS (00:49 local)
- `Tools/editor/probe_milestone.py` executed successfully. BP_GraphProbe has a real HelloWorld function entry connected to PrintString. Native function invoked before and after package reload. LogBlueprintUserMessages records COMBAT_NATIVE_GRAPH_EXECUTED twice in Saved/Logs/CombatEditorSession.log at 16:49:17/18 UTC.
- AM_NotifyProbe made from Manny idle via AnimMontageFactory; real TimedNiagaraEffect NotifyState at 0.1..0.3 sec; exactly one notify after reload.
- WBP_WidgetProbe compiled; NS_TemplateProbe duplicated DirectionalBurst template. All four saved; reload_packages returned `(True, Text(""))`.
- WidgetBlueprint widget_tree is not reflected to Python (actual get_editor_property fails). Editor helper required for editable designer tree. Full AnimBP/StateTree helper forthcoming. No build requested yet.

## Build request / coordination (00:55 local)
`Source/CombatEditor/CombatEditorLibrary.{h,cpp}` and editor Build.cs ready for coordinator's next build. **Please build at your agreed runtime milestone and restart editor, then record result here or integration progress.** I will not build/restart. Helper only adds editor code: editable UMG designer tree, real grounded/airborne AnimGraph with speed blendspace and DefaultSlot, StateTree AI-schema creation from supplied native task struct paths, nav brush construction, compile/save validation.

Current generated foundation: `/Game/Combat/Maps/L_CombatArena` (10 actors, 50 m floor, 4 m walls), subtle rough concrete material, 13 WAV imports, 6 Niagara copies. Nav actor factory confirmed real 200 cm brush; scaling to full bounds on next idempotent run. Niagara copies are templates pending tuning/parameter binding and runtime integration, not yet final VFX.

Runtime requests based on actual headers:
- SkillDefinition currently lacks next-skill links and FX asset fields. Please expose these to meet BP/data-only extension requirement.
- Need gameplay montage event stream reaching ability BP so visible tag branches execute blocks. Current ability Activate calls BeginSkill then Super; will use actual task API once compiled.
- HUD generated designer widget names: HealthBar, HealthText, BossHealthBar, BossPoiseBar, PhaseText, LockText, ParryText, ResultText, PauseText; please bind/update these from your UCombatHUDWidget if supplied. Parent passed to helper is runtime subclass.
- StateTree helper accepts ordered native task struct paths (selection/execution/recovery), creates completion transitions including loop to selection. Please provide task class names and confirm external context bindings expected.

## Handoff acknowledged (00:58 local)
Read BUILD HANDOFF ACTIVE; no further remote calls until BUILD READY. Montage generation request overlapped shutdown discovery and returned no remote editor (no script executed). Source prep continues. Full source import completed successfully: 2 armored meshes, 2 weapons, 19 AnimSequences, copied SK_CombatSkeleton (original untouched). Imported sword1 actual length 0.6166667 sec, all clip times read; armored mesh heights ~185/187 cm. Updated StateTree task path/HUD contract received.

Build_Core_01 editor error fixed: include is Blueprint/WidgetBlueprintGeneratedClass.h (01:00). Ready for coordinator retry.

Animation bind-pose correction notice received; previous import lengths are verified but **visual animation acceptance is revoked pending corrected FBX reimport**. Import pipeline now hashes each source FBX and automatically reimports changed source while preserving asset paths. Await corrected-source notice and BUILD READY before executing it.

Read Build_Editor_Check.log: fixed the two TObjectPtr deduction roots with `.Get()` (WidgetTree and EditorStateMachineGraph). Added editor-only ConfigureNiagara: real renderer bindings for User.Tint/User.SpriteSize/User.RibbonWidth, not unused decorative parameters. Ready for next coordinator compile (01:03).

Coordinator authorized isolated `cl.exe @CombatEditorLibrary.cpp.obj.rsp` compile in EditorCoordinator.md. Running that exact check now; no UBT/UHT/runtime build/restart. Seven Python scripts pass AST syntax validation. Skill pipeline authors actual async MontageAndEvents task plus nine visible tag comparisons/branches calling native blocks, with DataAsset-driven montage and next links.

Isolated editor helper compile PASS (exit 0, 01:06). Subsequent small update uses new FVersionedNiagaraEmitterBase binding overload to remove deprecation warnings. Header adds ConfigureNiagara UFUNCTION, so next full coordinator build must run UHT normally. Source ready; remote remains idle during handoff.

ArtDirection read. HUD helper now places player health bottom-left, names 霜刃 / 烬锋·铁卫, uses explicit engine DroidSansFallback CJK composite font asset, and removes execution wording. Original armored models remain integration diagnostics pending pack download. **Runtime integration issue:** GameMode BeginPlay currently overwrites spawned Boss AIControllerClass with native ACombatAIController, losing BP_CombatAI's configured StateTree. Please preserve BossClass CDO controller; editor will also place a configured BP boss in arena to avoid this during testing. HUD runtime dynamically constructs pause settings; for fully editable styled layout please let it reuse designer settings children or coordinator can schedule helper expansion. All seven generated asset stages plus validation/PIE probe scripts prepared.

FULL BUILD freeze acknowledged (01:11). No further Source/CombatEditor changes until build result. Final isolated compile including CJK font/layout PASS exit 0 before freeze. Ability graph version bumped to 4; OnInterrupted CompleteSkill sets bInterrupted=true, normal OnCompleted false. Ten Python files syntax checked successfully. Actual PIE remains pending full build.

Build_Integrated_03 finished failed at editor DLL link only: unresolved FPropertyBindingBindableStructDescriptor destructor. Adding direct `PropertyBindingUtils` editor dependency now (required by UE5.8 StateTree headers), then refreezing for coordinator rebuild. No runtime files touched.


## Actual PIE skill matrix
```json
[
  {
    "skill": "Attack1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.7,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Attack2",
    "activated": true,
    "montage_observed": true,
    "damage": 22.0,
    "movement_cm": 63.6,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Attack3",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Attack4",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "DashStrike",
    "activated": true,
    "montage_observed": true,
    "damage": 32.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Air1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 349.9,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Air2",
    "activated": false,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 348.6,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Plunge",
    "activated": true,
    "montage_observed": true,
    "damage": 50.0,
    "movement_cm": 348.4,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Parry",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 0.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Riposte",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.4,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Dash",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 942.4,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.Combo1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.2,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.Combo2",
    "activated": true,
    "montage_observed": true,
    "damage": 27.0,
    "movement_cm": 63.2,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.Combo3",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.AOE",
    "activated": true,
    "montage_observed": true,
    "damage": 65.0,
    "movement_cm": 0.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.DashSlash",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.LeapLeft",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 450.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.LeapRight",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 450.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  },
  {
    "skill": "Boss.LeapBack",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 500.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_Combat_C"
  }
]
```


## Actual PIE skill matrix
```json
[
  {
    "skill": "Attack1",
    "activated": true,
    "montage_observed": true,
    "damage": 18.0,
    "movement_cm": 63.7,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Attack2",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Attack3",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Attack4",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "DashStrike",
    "activated": true,
    "montage_observed": true,
    "damage": 32.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Air1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 350.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Air2",
    "activated": true,
    "montage_observed": true,
    "damage": 30.0,
    "movement_cm": 285.1,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Plunge",
    "activated": true,
    "montage_observed": true,
    "damage": 50.0,
    "movement_cm": 349.6,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Parry",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 0.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Riposte",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.4,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Dash",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 250.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Boss.Combo1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.2,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.Combo2",
    "activated": true,
    "montage_observed": true,
    "damage": 27.0,
    "movement_cm": 63.2,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.Combo3",
    "activated": true,
    "montage_observed": true,
    "damage": 38.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.AOE",
    "activated": true,
    "montage_observed": true,
    "damage": 65.0,
    "movement_cm": 0.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.DashSlash",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.LeapLeft",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 450.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.LeapRight",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 450.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.LeapBack",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 500.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  }
]
```


## Actual PIE skill matrix
```json
[
  {
    "skill": "Attack1",
    "activated": true,
    "montage_observed": true,
    "damage": 18.0,
    "movement_cm": 63.7,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Attack2",
    "activated": true,
    "montage_observed": true,
    "damage": 22.0,
    "movement_cm": 63.8,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Attack3",
    "activated": true,
    "montage_observed": true,
    "damage": 26.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Attack4",
    "activated": true,
    "montage_observed": true,
    "damage": 38.0,
    "movement_cm": 63.5,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "DashStrike",
    "activated": true,
    "montage_observed": true,
    "damage": 32.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Air1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 349.9,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Air2",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 291.4,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Plunge",
    "activated": true,
    "montage_observed": true,
    "damage": 50.0,
    "movement_cm": 349.7,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Parry",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 0.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Riposte",
    "activated": true,
    "montage_observed": true,
    "damage": 85.0,
    "movement_cm": 63.4,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Dash",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 250.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Boss.Combo1",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.2,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.Combo2",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 63.2,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.Combo3",
    "activated": true,
    "montage_observed": true,
    "damage": 38.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.AOE",
    "activated": true,
    "montage_observed": true,
    "damage": 65.0,
    "movement_cm": 0.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.DashSlash",
    "activated": true,
    "montage_observed": true,
    "damage": 40.0,
    "movement_cm": 63.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.LeapLeft",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 450.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.LeapRight",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 450.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.LeapBack",
    "activated": true,
    "montage_observed": true,
    "damage": 28.0,
    "movement_cm": 500.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  }
]
```


## Actual PIE skill matrix
```json
[
  {
    "skill": "Air1",
    "activated": true,
    "montage_observed": true,
    "damage": 22.0,
    "movement_cm": 144.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Air2",
    "activated": true,
    "montage_observed": true,
    "damage": 30.0,
    "movement_cm": 100.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatKwang_C"
  },
  {
    "skill": "Boss.Combo1",
    "activated": true,
    "montage_observed": true,
    "damage": 24.0,
    "movement_cm": 30.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.Combo2",
    "activated": true,
    "montage_observed": true,
    "damage": 0.0,
    "movement_cm": 35.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  },
  {
    "skill": "Boss.Combo3",
    "activated": true,
    "montage_observed": true,
    "damage": 38.0,
    "movement_cm": 55.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  }
]
```


## Actual PIE skill matrix
```json
[
  {
    "skill": "Boss.Combo2",
    "activated": true,
    "montage_observed": true,
    "damage": 27.0,
    "movement_cm": 35.0,
    "ended_cleanly": true,
    "anim_instance": "ABP_CombatGreystone_C"
  }
]
```
