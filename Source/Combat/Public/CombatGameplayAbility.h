#pragma once
#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "CombatGameplayAbility.generated.h"
class ACombatCharacter;
class UCombatSkillDefinition;
UCLASS(Blueprintable)
class COMBAT_API UCombatGameplayAbility : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UCombatGameplayAbility();
    UFUNCTION(BlueprintPure) ACombatCharacter* GetCombatCharacter() const;
    UFUNCTION(BlueprintPure) UCombatSkillDefinition* GetSkillDefinition() const;
    UFUNCTION(BlueprintCallable) void CompleteSkill(bool bInterrupted = false);
    virtual void ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
    virtual void EndAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;
};

