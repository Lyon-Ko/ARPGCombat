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

Not yet accepted: full compile after second batch, rendered skill/weapon/HUD inspection, all functional acceptance scenarios, twenty fight/reset cycles, audio/VFX tuning and cold reload. This document records implementation, not a passing visual/functional result.
