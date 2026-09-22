"""Run in a fresh arena PIE session; exercises the handler bound to R.

For repeated-Play coverage, leave a placed boss in the editor map and run
this script in two successive PIE sessions. Neither may inherit that boss.
"""
import unreal as u

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
assert world, 'Start a fresh PIE session first'

def bosses():
    return [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.CombatCharacter) if a.is_boss]

player = u.GameplayStatics.get_player_pawn(world, 0)
assert not bosses(), 'Boss must not appear at startup'
assert not u.GameplayStatics.get_all_actors_of_class(world, u.CombatAIController), 'No orphan boss AI at startup'
u.GameplayStatics.set_game_paused(world, True)
player.retry_encounter()
assert not bosses(), 'Pause must not summon the boss'
u.GameplayStatics.set_game_paused(world, False)
player.retry_encounter()
assert len(bosses()) == 1, 'First R must spawn exactly one boss'
boss = bosses()[0]
assert player.get_combat_target() == boss and boss.get_combat_target() == player
boss.get_controller().get_editor_property('state_tree_component').stop_logic('Spawn regression')
player.reset_combat_state()
player_start = player.get_actor_location()
boss_start = boss.get_actor_location()

def hit(receiver, attacker, damage, instance):
    return receiver.receive_combat_hit(u.CombatHit(
        attacker=attacker, damage=float(damage), poise_damage=0.0,
        location=receiver.get_actor_location(), direction=u.Vector(-1, 0, 0),
        parryable=False, attack_instance=instance))

hit(player, boss, 5, 90001)
health = player.get_health()
for _ in range(3):
    player.retry_encounter()
assert bosses() == [boss] and player.get_health() == health, 'R during combat must not reset or duplicate'

for receiver, attacker, instance in [(player, boss, 90002), (boss, player, 90003)]:
    assert hit(receiver, attacker, receiver.get_max_health() * 2, instance) == u.CombatHitResult.KILLED
    assert not receiver.is_alive()
    u.GameplayStatics.set_game_paused(world, True)
    player.retry_encounter()
    assert not u.GameplayStatics.is_game_paused(world)
    assert bosses() == [boss], 'Retry must reuse the existing boss'
    for actor in (player, boss):
        assert actor.is_alive() and actor.get_health() == actor.get_max_health()
    assert (player.get_actor_location() - player_start).length() < 0.1
    assert (boss.get_actor_location() - boss_start).length() < 0.1
    boss.get_controller().get_editor_property('state_tree_component').stop_logic('Spawn regression')

print('BOSS_SPAWN_REGRESSION_PASS: empty startup, pause, first R, repeated R, defeat retry, victory retry')
