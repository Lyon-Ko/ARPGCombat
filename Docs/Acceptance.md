# Acceptance evidence and autonomous recovery

## Required automated coverage
Use the real world actors and the same public skill/hit interfaces as normal play. A test that only mirrors a private helper is insufficient.

1. Parry before/inside/after its window; frontal vs rear attack; held input cannot retrigger. Success grants the riposte GE/tag and consumes no HP; failed attempts take damage. Test damage frame and cue deadline at 30fps and60fps.
2. Each weapon window damages a target at most once; a distinct combo window may damage it again. Crossing target at low frame rate must be swept.
3. Cancel skills before/after hit opening, interrupt Montage, and kill actor while dashing/parrying/projectile/area is active. No hitboxes, listeners, invulnerability or Busy remain beyond intended lifetime.
4. Double jump + one air dash + air attacks don't permit infinite jumps or hover. Landing resets air budget. Sweep prevents arena wall penetration.
5. Force every Boss skill for visual recording and deterministic validity checks. Left/right/back variants respect available space; projectile aim locks on release. AOE warning/flash/hit share the authored timeline and correct volume.
6. Compare action counts for near aggressive, distant evasive and frequent-parry player scenarios with a fixed RNG seed. Decision changes must correspond to observed actions, not raw input. Verify half-health phase activates after the current skill and only once.
7. Run20 sequential fight/reset cycles using a test controller that issues real move/attack/parry commands. Log match number, elapsed time, attacks/hits/parries, phase transition, outcome and reset cleanup. Accelerated/forced scenarios are labelled separately from normal-speed balance play. A simulation is not evidence of rendered visual quality.
8. All authored Blueprint/Montage/StateTree assets validate, save, reload and still reference the intended skeleton. Record missing references/errors as failures.
9. Demonstrate a new ability added with BP/montage/data only, using the same logical blocks and no C++ special case.

## Manual/visual acceptance by agent
Cold editor launch, default arena, actual keyboard/mouse movement, dodge/jump/attack/parry/lock/pause/result/retry. Inspect both characters' armor, sword attachment, four distinct strike poses, feet, trail, hit sparks, telegraph edges, UI readability at1080p, camera walls and obstruction. Verify audio files are attached and audible in the actual runtime route.

Performance: after shader warmup, collect1080p high-quality rendered frame samples on the actual local machine. Target60fps, report measured averages and low-frame behavior rather than inferring from hardware. Keep recording/testing cheats out of ordinary default play.

## Recovery
Persist the failing command/log and relevant source state, identify cause, repair or replace path, re-run the failed check. Free resource download failures switch to originals. MCP failures use native commandlet/CLI paths. Changes remain local; don't upload or purchase. Keep baseline backup and stage commits. Only mark whole demo complete when functional and visual acceptance both pass.
