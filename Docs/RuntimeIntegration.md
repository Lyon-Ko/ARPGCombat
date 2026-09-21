# Runtime integration contract (2026-09-22)

## Native classes
- `CombatCharacter`: player or boss, ASC + AttributeSet, camera/spring arm, editable weapon and feedback components. Set `bIsBoss`, health/poise, `SkillDefinitions`, skeletal mesh/AnimClass and `AIControllerClass` on character Blueprints.
- `CombatGameplayAbility`: Blueprint parent. Native activation commits GAS and begins the selected definition; Blueprint `ActivateAbility` must start `CombatAbilityTask_PlayMontageAndEvents.PlayMontageAndEvents(GetSkillDefinition().Montage)`. Route `OnEvent.EventTag` through real visible tag branches to character blocks. Route Completed to `CompleteSkill(false)` and Interrupted to `CompleteSkill(true)`.
- `CombatAnimNotify_Event.EventTag`: montage notify payload; no actor-owned live state lives on notify assets.
- `CombatAnimInstance`: Speed, Direction, bInAir, bIsBoss. Locomotion graph must include `DefaultSlot`.
- `CombatAIController.CombatStateTree`: assign actual StateTree on BP controller. Character/GameMode preserves this BP class.
- StateTree ordered native tasks: `/Script/Combat.CombatStateTreeSelectTask`, `/Script/Combat.CombatStateTreeExecuteTask`, `/Script/Combat.CombatStateTreeRecoverTask`. Context owner must be CombatAIController under AI schema; there are no explicit external-data bindings. Select observes snapshot then waits 0.2–0.35 sec. Execute requests GAS ability and awaits real completion. Recovery is mandatory. There is no timer-based shadow decision loop.
- `CombatHUDWidget`: editable WBP parent. Finds HealthBar, HealthText, BossHealthBar, BossPoiseBar, PhaseText, LockText, ParryText, ResultText, PauseText. Native fallback builds real UMG controls if names are absent. Pause settings are real sliders/checkbox. `CombatGameMode.HUDWidgetClass` selects WBP.
- `CombatGameMode.BossClass` spawns configured BP only when the level contains no boss. Its BP AIControllerClass remains untouched.

## Skill data
`CombatSkillDefinition`: SkillTag, InputTag, NextSkillTag, ActivationQuery, Priority, AbilityClass, Montage, Damage, PoiseDamage, Cooldown, Duration, MovementDistance, MovementDuration, MovementDirectionLocal, LaunchVelocityZ, TraceRadius, TraceReach, AreaRadius, AreaHeight, AreaDelay, ProjectileSpeed, bAirOnly, bParryable, bCanInterrupt. Presentation: HitEffect, TrailEffect, CastEffect, CastSound, HitSound, ParrySound, AreaMesh, AreaMaterial, CueColor. AI: SelectionWeight, MinAIRange, MaxAIRange. AirAttackIndex 1 or 2 + AirHangTime uses shared character MaxAirHangBudget=0.25sec; 0 means not one of the two budgeted air light attacks.

Input chooses valid candidates in descending Priority with query/cooldown/air checks. Direct ByTag also checks query and budgets before cancelling the current skill. NextSkillTag chains data, never hardcoded four-hit logic. Boss continuation skills normally have SelectionWeight=0 so only the entry move is chosen; NextSkillTag drives continuation. A Blueprint/data-only extra skill needs no C++ edit.

Input tags: `Combat.Input.Attack`, `Combat.Input.Parry`, `Combat.Input.Dash`. Native state query tags: `Combat.State.Air`, `Combat.State.Dashing`, `Combat.State.RiposteReady`, `Combat.State.Busy`, `Combat.State.Dead`, `Combat.State.Parry`, `Combat.State.Stunned`, `Combat.State.Invulnerable`. Cooldowns are real duration GE specs queried by skill asset tag; RiposteReady is a separate 0.8sec duration GE and survives the parry ability end.

Events: `Combat.Event.HitOpen`, `HitClose`, `Move`, `Projectile`, `AreaWarning`, `AreaRelease`, `ComboOpen`, `Cancelable`, `Finish`. Native composable blocks share those names via OpenHitWindow, CloseHitWindow, StartSkillMovement, EmitSkillProjectile, ShowAreaWarning, DetonateArea, OpenComboWindow, SetCancelable, FinishSkill. `HandleMontageEvent` is a convenience router but production BP should expose the event branches and blocks.

## Weapon/movement/feedback
- Independent static sword: WeaponMesh attaches to configurable WeaponAttachSocket, preserving its relative component transform. TraceStartSocket/TraceEndSocket default BladeBase/BladeTip; fallback WeaponBladeAxis is local +X and WeaponBladeLength=130cm. Six swept samples span previous/current sword blade endpoints every frame. One new AttackInstance per hit window and one hit per target per window.
- Embedded Paragon sword: `bTraceFromCharacterMesh=true`; set TraceStartSocket/TraceEndSocket to actual skeletal sockets/bones; hide independent WeaponMesh. No Manny bone other than the editable default attachment is required by combat logic.
- Dash uses independently sampled current keys with eight-way quantization, camera-relative or target-relative when locked, backward if no movement, swept capsule displacement. Only one air dash per landing.
- Leap variants can set MovementDirectionLocal Y +/-1 or X -1 and LaunchVelocityZ. Select checks wall sweep clearance before choosing long movement. Phase 2 raises move weights and reduces mandatory recovery to 80%.
- AreaMesh should be an editable 100cm-diameter/height cylinder; warning scale uses thin disc at floor and release expands to the authored radius/height. AreaMaterial can expose `Tint`. Warning/flash/hit use the same Center and AreaDelay.
- CastEffect doubles as projectile visual until separate projectile visual assets are configured. CastSound/HitSound/ParrySound honor character MasterVolume. Character HitCameraShake optional, settings allow disabling shake.

## Validation hooks
Public: RequestSkillByTag, RequestSkillByInputTag, ReceiveCombatHit(FCombatHit), ResetCombatState, IsAlive, IsBusy, GetHealth/MaxHealth/Poise/MaxPoise, GetActiveSkillTag, GetSkillElapsedTime, GetSkillCooldownRemaining, IsParryWindowActive. Delegate OnCombatFeedback(source,target,tag,location,intensity), OnCombatDeath, OnSkillStarted/Ended. AI ActionsExecuted, SelectedSkill, PreviousSkill, ObservedTargetLocation/Skill and deterministic RandomSeed support repeatable scenario logs.

FCombatHit.AttackInstance must be unique for a new manual test hit from the same attacker. Reusing it intentionally tests deduplication. Exact-time defense checks use world elapsed time at hit receipt, so they do not rely only on tick-updated loose-tag state.

This document records the implemented interfaces. Actual build, gameplay, audio, visual and cold-start evidence is tracked in [DeliveryVerification](DeliveryVerification.md); later sections describe successive implementation batches rather than separate pending deliverables.

## Third runtime batch: presentation and lifecycle

New Character properties:
- `HitStopDuration` (0.045sec default): confirmed damage/parry applies CustomTimeDilation to involved characters only. Restore reads real time every tick, with an 85ms maximum continuous window; global/gameplay time is never slowed, preserving authored AOE .18sec scheduling.
- `DeathMontage`, `HitReactMontage`, `DeathSound`, `FootstepSounds`, `FootstepDistance` (160cm). Death uses a transient montage copy with auto blend-out disabled and freezes its final pose; without a montage but with PhysicsAsset it ragdolls. Retry unpauses animation, removes simulation, restores mesh transform/collision, stops montages and restores capsule/movement. Footsteps follow grounded travelled distance and don't fire during skills.
- `DefaultCameraDistance` (560), `SoftLockRange` (650), `SoftLockViewDot` (.4). Unlocked assistance requires range, view direction and unobstructed LOS. Unlock/dead target returns arm distance and free look.

New Skill properties:
- `bGroundOnly`: set true on Attack1..4 (and other ground-only skills), false on Dash/Parry and air skills. Both direct and input activation enforce it, preventing ground attacks from bypassing the two-air-light budget.
- `bFaceTarget`: set false for Dash and Parry; ordinary offensive skills may use conditional facing assistance.
- `bPlayCastSoundAtActivation`: default false. Set true for Dash. Other sounds play once at actual HitOpen / Projectile / AreaRelease, rather than all at activation. Successful parry sound stays contact-triggered.
- `AreaReleaseEffect`: bind the intended NS_AOEFlash for the release impact. The radius-50 cm thin XY warning ring keeps its ground position and thin Z scale from ShowWarning; opacity rises from .2 to .65 on release, then EndSkillFeedback removes it. `AreaHeight` controls actual damage height and does not stretch or lift the ring. Existing CastSound should be the appropriate AOE burst sound for that skill.

GameMode adds `BattleMusic` (USoundBase), `MusicVolume` (.35), `MusicComponent` (UAudioComponent). Set BattleMusic to SW_BattleMusic. It plays and loops in the actual game, and tracks MasterVolume even while pause settings are open. Footstep/swing/impact/parry/death sound routes also use MasterVolume.

Lifecycle: deduplication remembers the most recent64attack IDs per source actor, so interleaved old projectiles and new melee windows cannot reapply the same recent hit. Death and Reset destroy *all* world projectiles whose Owner is that character, including those released by previously completed skills. PhaseText now displays only phase, allowing the WBP's separate BossName label.

The matching assets have been assigned and checked in the later integration passes. See the delivery record for each check's actual build and scope.

## Sword wave and input correction batch

- SkillDefinition exposes `ProjectileMesh`, `ProjectileMaterial`, and `ProjectileCollisionHalfExtent` (default half size `(24, 85, 20)` cm). The assigned sword wave mesh uses local +X propagation and Y width 180 cm; `WaveMesh` follows the projectile root and has no collision. The root `Collision` is a box, with full default dimensions 48 x 170 x 40 cm. It blocks walls, overlaps opposing characters, ignores the owner during movement, and consumes one hit before calling the receiver. Existing `CastEffect` remains the accompanying Niagara effect. Contact and wall checks are included in the arena regression suite.
- `InitializeProjectile` now accepts Mesh, Material, and CollisionHalfExtent after Effect. The native character emitter supplies these from its skill definition; existing Blueprint calls to this function need those inputs reviewed after recompilation.
- Dash clears existing horizontal velocity and temporarily suppresses normal horizontal acceleration while its controlled movement runs. Vertical velocity and falling physics continue. Completion, blocking, interruption, death and reset restore normal acceleration through skill cleanup.
- `IsTargetLocked()` is BlueprintPure. The existing HUD controls line displays either `Q 已锁定` or `Q 自由镜头`.
- Pause entry clears held attack/jump state, and their release bindings execute while paused. Required regression cases: running airborne forward/reverse Dash (about 250 cm horizontal displacement), hold LMB/Space then pause/release/resume (no stale plunge/jump hold), and visible Q state transitions.
- Default startup/game map is `/Game/Combat/Maps/L_CombatArena.L_CombatArena`, default mode is `/Game/Combat/Blueprints/BP_CombatGameMode.BP_CombatGameMode_C`, and split screen is disabled.

These corrections are included in the current built runtime and arena regression checks.

AI reaction: when the delayed observation snapshot contains the player's executed `Combat.Skill.Dash`, eligible `Combat.Skill.Boss.DashSlash` choices receive a 1.7 weight multiplier. Range, cooldown and movement-space filters still apply before weighting; prior-action repetition penalty and phase-two weighting remain multiplicative. This reads the observed active skill, never raw input, and does not force a chase action. Independent AI scenario and near-range paired-sample results are linked in the delivery record.
