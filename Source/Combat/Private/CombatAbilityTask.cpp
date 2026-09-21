#include "CombatAbilityTask.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "CombatTags.h"
UCombatAbilityTask_PlayMontageAndEvents* UCombatAbilityTask_PlayMontageAndEvents::PlayMontageAndEvents(UGameplayAbility* OwningAbility, UAnimMontage* Montage, float Rate)
{
    auto* Task = NewAbilityTask<UCombatAbilityTask_PlayMontageAndEvents>(OwningAbility);
    Task->MontageToPlay = Montage;
    Task->PlayRate = Rate;
    return Task;
}
void UCombatAbilityTask_PlayMontageAndEvents::Activate()
{
    auto* ASC = AbilitySystemComponent.Get();
    auto* Anim = Ability ? Ability->GetCurrentActorInfo()->GetAnimInstance() : nullptr;
    if(!ASC || !Anim || !MontageToPlay) { OnCancelled(); return; }
    EventHandle = ASC->AddGameplayEventTagContainerDelegate(FGameplayTagContainer(CombatTags::Event_Root), FGameplayEventTagMulticastDelegate::FDelegate::CreateUObject(this, &ThisClass::OnGameplayEvent));
    CancelHandle = Ability->OnGameplayAbilityCancelled.AddUObject(this, &ThisClass::OnCancelled);
    if(ASC->PlayMontage(Ability, Ability->GetCurrentActivationInfo(), MontageToPlay, PlayRate) <= 0.f) { OnCancelled(); return; }
    FOnMontageEnded EndDelegate;
    EndDelegate.BindUObject(this, &ThisClass::OnMontageEnded);
    Anim->Montage_SetEndDelegate(EndDelegate, MontageToPlay);
    SetWaitingOnAvatar();
}
void UCombatAbilityTask_PlayMontageAndEvents::OnGameplayEvent(FGameplayTag Tag, const FGameplayEventData* Data)
{
    if(ShouldBroadcastAbilityTaskDelegates()) OnEvent.Broadcast(Tag, Data ? *Data : FGameplayEventData());
}
void UCombatAbilityTask_PlayMontageAndEvents::OnMontageEnded(UAnimMontage* Montage, bool bInterrupted)
{
    if(Montage != MontageToPlay) return;
    if(ShouldBroadcastAbilityTaskDelegates())
    {
        if(bInterrupted) OnInterrupted.Broadcast(FGameplayTag(), FGameplayEventData());
        else OnCompleted.Broadcast(FGameplayTag(), FGameplayEventData());
    }
    EndTask();
}
void UCombatAbilityTask_PlayMontageAndEvents::OnCancelled()
{
    if(ShouldBroadcastAbilityTaskDelegates()) OnInterrupted.Broadcast(FGameplayTag(), FGameplayEventData());
    EndTask();
}
void UCombatAbilityTask_PlayMontageAndEvents::OnDestroy(bool bAbilityEnded)
{
    if(Ability) Ability->OnGameplayAbilityCancelled.Remove(CancelHandle);
    if(auto* ASC = AbilitySystemComponent.Get())
    {
        ASC->RemoveGameplayEventTagContainerDelegate(FGameplayTagContainer(CombatTags::Event_Root), EventHandle);
        if(Ability && ASC->GetAnimatingAbility() == Ability && ASC->GetCurrentMontage() == MontageToPlay)
        {
            if(auto* Anim = Ability->GetCurrentActorInfo()->GetAnimInstance())
            {
                FOnMontageEnded EmptyDelegate;
                Anim->Montage_SetEndDelegate(EmptyDelegate, MontageToPlay);
            }
            ASC->CurrentMontageStop(.08f);
        }
    }
    Super::OnDestroy(bAbilityEnded);
}
