#pragma once
#include "CoreMinimal.h"
#include "Abilities/GameplayAbility.h"
#include "CombatGameplayAbility.generated.h"
class ACombatCharacter;
class UCombatSkillDefinition;
class UCombatAbilityTask_PlayMontageAndEvents;
UCLASS(Blueprintable)
class COMBAT_API UCombatGameplayAbility : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UPROPERTY() TObjectPtr<UCombatAbilityTask_PlayMontageAndEvents> DataMontageTask;
    UFUNCTION() void DataCompleted(FGameplayTag Tag, FGameplayEventData Data);
    UFUNCTION() void DataInterrupted(FGameplayTag Tag, FGameplayEventData Data);
    UCombatGameplayAbility();
    UFUNCTION(BlueprintPure) ACombatCharacter* GetCombatCharacter() const;
    UFUNCTION(BlueprintPure) UCombatSkillDefinition* GetSkillDefinition() const;
    UFUNCTION(BlueprintCallable) void CompleteSkill(bool bInterrupted = false);
    virtual void ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData) override;
    virtual void EndAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled) override;
};

