#include "CombatGameplayAbility.h"
#include "CombatCharacter.h"
#include "CombatTypes.h"
#include "CombatAbilityTask.h"
#include "CombatSkillRuntime.h"
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
    const uint64 ExpectedSerial=Character->SkillRuntime->GetSerial()+1;
    Character->BeginSkill(Definition, this);
    if(!Character->IsActiveAbility(this) || Character->SkillRuntime->GetSerial()!=ExpectedSerial) return;
    if(Definition->bDataDriven)
    {
        if(Definition->Montage)
        {
            DataMontageTask = UCombatAbilityTask_PlayMontageAndEvents::PlayMontageAndEvents(this,Definition->Montage);
            DataMontageTask->OnCompleted.AddDynamic(this,&ThisClass::DataCompleted);
            DataMontageTask->OnInterrupted.AddDynamic(this,&ThisClass::DataInterrupted);
            DataMontageTask->ReadyForActivation();
        }
        return;
    }
    Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData);
}
void UCombatGameplayAbility::CompleteSkill(bool bInterrupted) { EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, bInterrupted); }
void UCombatGameplayAbility::EndAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo, bool bReplicateEndAbility, bool bWasCancelled)
{
    ACombatCharacter* Character = GetCombatCharacter();
    const bool bOwnsExecution = Character && Character->IsActiveAbility(this);
    if(bOwnsExecution) Character->bLastSkillInterrupted = bWasCancelled;
    Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
    if(bOwnsExecution && Character->IsActiveAbility(this)) Character->EndSkill(bWasCancelled);
}
void UCombatGameplayAbility::DataCompleted(FGameplayTag Tag, FGameplayEventData Data)
{
    auto* C=GetCombatCharacter(); if(!C || !C->IsActiveAbility(this)) return;
    const uint64 Serial=C->SkillRuntime->GetSerial(); C->SkillRuntime->CompleteAnimation();
    if(C->SkillRuntime->GetSerial()==Serial && C->IsActiveAbility(this)) CompleteSkill(false);
}
void UCombatGameplayAbility::DataInterrupted(FGameplayTag Tag, FGameplayEventData Data) { CompleteSkill(true); }


