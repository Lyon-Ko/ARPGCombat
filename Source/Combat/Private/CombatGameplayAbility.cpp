#include "CombatGameplayAbility.h"
#include "CombatCharacter.h"
#include "CombatTypes.h"
UCombatGameplayAbility::UCombatGameplayAbility()
{
    InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalOnly;
}
ACombatCharacter* UCombatGameplayAbility::GetCombatCharacter() const { return Cast<ACombatCharacter>(GetAvatarActorFromActorInfo()); }
UCombatSkillDefinition* UCombatGameplayAbility::GetSkillDefinition() const { return Cast<UCombatSkillDefinition>(GetCurrentSourceObject()); }
void UCombatGameplayAbility::ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* TriggerEventData)
{
    ACombatCharacter* Character = GetCombatCharacter();
    UCombatSkillDefinition* Definition = GetSkillDefinition();
    if(!Character || !Definition || !CommitAbility(Handle, ActorInfo, ActivationInfo))
    {
        EndAbility(Handle, ActorInfo, ActivationInfo, true, true);
        return;
    }
    Character->BeginSkill(Definition, this);
    Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData);
}
void UCombatGameplayAbility::CompleteSkill(bool bInterrupted) { EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, bInterrupted); }
void UCombatGameplayAbility::EndAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
    if(ACombatCharacter* Character = GetCombatCharacter(); Character && Character->IsActiveAbility(this)) Character->EndSkill(bWasCancelled);
    Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}


