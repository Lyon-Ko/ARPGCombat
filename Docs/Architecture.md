# Combat demo implementation contract

## Fixed scope
UE 5.8.2, local single player PIE, keyboard/mouse, Chinese HUD, 50 m flat walled arena. Fast sword combat, no stamina or held guard. Ground four-hit chain; dash strike, two air strikes, held-air plunge, parry riposte. Double jump and one air dash. Boss three-hit combo, charge flash AOE, forward dash slash, left/right leap projectile, backward leap projectile. Half-health second phase.

## Ownership
- Astra Ultra: architecture, integration decisions, review and acceptance.
- Astra Medium environment: module scaffolding, Tools, build/MCP baseline.
- Astra Medium assets: SourceAssets and Docs/Assets, original armor/weapons/animations/audio.
- Runtime implementation worker: Source/Combat/Public and Private files prefixed CombatCharacter, CombatTypes, CombatAttributeSet, CombatGameplayAbility, CombatAbilityTask, CombatAnimInstance, CombatAnimNotify.
- AI/presentation implementation worker (after core contract): files prefixed CombatAI, CombatStateTree, CombatGameMode, CombatHUD, CombatFeedback, CombatProjectile.
- Editor generation worker: Source/CombatEditor and Tools/editor scripts; sole writer of Content/Combat.
Never overwrite another worker's in-progress files. Build.cs changes go through the environment/editor owner. Only one live editor and one build at a time.

## Runtime conventions
Use centimeters, seconds, Z-up, UE forward +X. Final actors use the acquired Kwang and Greystone native skeletons, meshes and sword animation copies; the original Manny-based art is retained as backup source material. Each actor has capsule movement and a skeleton-specific AnimInstance with locomotion and a DefaultSlot montage. Attacks do not switch the mesh into SingleNode mode.

GAS is authoritative for skill activation, tags, cooldown/buffs and attributes. UCombatGameplayAbility is Blueprintable. Skill definition data assets carry montage, skill tag, ability class, damage/poise, movement and cue configuration. Actual blueprint graphs call composable native blocks and handle tagged montage events; don't reduce the blueprint to a single opaque full-skill function.

Public contract to implement (notify coordinator before changes):
- ACombatCharacter : ACharacter, IAbilitySystemInterface. bIsBoss; InitialHealth/InitialPoise; AbilitySet/SkillDefinitions; CombatTarget.
- Blueprint methods RequestSkillByTag(FGameplayTag), CancelCurrentSkill(), SetCombatTarget(ACombatCharacter*), GetCombatTarget(), IsAlive(), IsBusy(), GetHealth(), GetMaxHealth(), GetPoise(), GetMaxPoise(), GetActiveSkillTag(), IsParryWindowActive(), GetSkillElapsedTime(), ResetCombatState().
- ReceiveCombatHit structured attacker/damage/poise/location/direction/parryable attack instance; returns damage/parry/evade result. Per-target per-window hit deduplication.
- Blueprint-callable blocks OpenHitWindow, CloseHitWindow, StartSkillMovement, EmitSkillProjectile, ShowAreaWarning, DetonateArea, OpenComboWindow, SetCancelable, ApplyCombatEffect, FinishSkill. Projectile/feedback events can be implemented by delegates or explicit classes supplied by presentation worker.
- OnCombatFeedback source,target,tag,world location,intensity; OnCombatDeath; OnSkillStarted/Ended delegates. HUD obtains current player/boss state through methods, not duplicate health variables.
- UCombatAnimInstance exposes Speed, Direction, bInAir, bIsBoss for generated locomotion graph.
- Native tag namespace Combat.Skill.*, Combat.State.*, Combat.Event.*, Combat.Cue.*; register C++ native tags or startup config, never silently request missing tags.

Skill instances own hit lists, montage event listeners and movement; cancel/death removes all temporary tags/GE, traces, cues and listeners. AnimNotify objects store authored parameters only, never live actor state.

## Movement and defense
Dash 250cm/0.23s, cooldown0.35s, invulnerable0.04..0.18s. Camera-relative eight ways, target-relative while locked, backwards if no movement. World/capsule swept movement. Parry frontal140deg duration0.20s, no hold/repeat autoactivation, successful parry opens0.8s riposte. Input buffer0.18s. Final values are tunable data.

Montage events coordinate trace open/close, release, movement, cue, combo, cancellation. Flash begins the AOE release; hit follows0.18s later. AOE volume covers normal jump height and visible blast matches it. Parry/iframe/escape are valid counters. Parry has finite retry interval; success can reset it for the next incoming blow.

## AI/presentation
StateTree asset with native tasks controls engagement/decision/execution/recovery/death; don't install a dummy StateTree while actually driving all AI from a separate timer. Observe performed actions and positions (not raw input), delayed reaction0.2..0.35s, weighted actions, repeat penalty, finite chase/retreat and guaranteed recovery. Phase2 below50% activates after current move. Boss can be poise-broken but not infinitely interrupted by normal hits.

Camera free/soft/hard lock with collision and both actors framed. Chinese HUD: HP, boss HP/poise, phase, riposte cue, controls, pause/result/retry. Keys WASD, Mouse, LMB attack, RMB parry, Shift dash, Space jump, Q lock, P pause, R retry on result.

## Acceptance
Complete C++ build and all blueprint compile, cold reload, actual PIE interaction, all moves reviewed. 30/60fps hit/parry consistency, front/back parry, cancellation/death cleanup, walls/blocked retreat/air reset, at least20 automated fight/retry cycles. No pass based solely on compilation or mannequin placeholders. Documentation and screenshot/video proof. Assets generated with scripts remain editable. Add a new skill solely by BP/montage/data as extension proof.
