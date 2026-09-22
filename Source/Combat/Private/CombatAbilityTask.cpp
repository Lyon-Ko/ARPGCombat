#include "CombatAbilityTask.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimInstance.h"
#include "CombatTags.h"
#include "CombatCharacter.h"
#include "CombatGameplayAbility.h"
#include "CombatLocomotionSettings.h"
#include "Animation/AnimMontage.h"
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
    if(const auto* CombatAbility = Cast<UCombatGameplayAbility>(Ability))
        if(const auto* Definition = CombatAbility->GetSkillDefinition())
        {
            LocomotionBlendOut = Definition->LocomotionBlendOut;
            InterruptBlendOut = Definition->InterruptBlendOut;
        }
    EventHandle = ASC->AddGameplayEventTagContainerDelegate(FGameplayTagContainer(CombatTags::Event_Root), FGameplayEventTagMulticastDelegate::FDelegate::CreateUObject(this, &ThisClass::OnGameplayEvent));
    CancelHandle = Ability->OnGameplayAbilityCancelled.AddUObject(this, &ThisClass::OnCancelled);
    if(ASC->PlayMontage(Ability, Ability->GetCurrentActivationInfo(), MontageToPlay, PlayRate) <= 0.f) { OnCancelled(); return; }
    FOnMontageEnded EndDelegate;
    EndDelegate.BindUObject(this, &ThisClass::OnMontageEnded);
    Anim->Montage_SetEndDelegate(EndDelegate, MontageToPlay);
    FOnMontageBlendingOutStarted BlendDelegate;
    BlendDelegate.BindUObject(this, &ThisClass::OnMontageBlendingOut);
    Anim->Montage_SetBlendingOutDelegate(BlendDelegate, MontageToPlay);
    SetWaitingOnAvatar();
}
void UCombatAbilityTask_PlayMontageAndEvents::OnGameplayEvent(FGameplayTag Tag, const FGameplayEventData* Data)
{
    // An outgoing montage can still emit notifies while blending. Its events
    // must never open hit windows or finish the newly started ability.
    if(Data && Data->OptionalObject && Data->OptionalObject != MontageToPlay) return;
    if(!bFinishing && ShouldBroadcastAbilityTaskDelegates()) OnEvent.Broadcast(Tag, Data ? *Data : FGameplayEventData());
}
void UCombatAbilityTask_PlayMontageAndEvents::OnMontageBlendingOut(UAnimMontage* Montage, bool bInterrupted)
{
    // Release gameplay ownership at interruption, not after the visual fade.
    if(bInterrupted) OnMontageEnded(Montage, true);
}
void UCombatAbilityTask_PlayMontageAndEvents::OnMontageEnded(UAnimMontage* Montage, bool bInterrupted)
{
    if(bFinishing || Montage != MontageToPlay) return;
    bFinishing = true;
    if(ShouldBroadcastAbilityTaskDelegates())
    {
        if(bInterrupted) OnInterrupted.Broadcast(FGameplayTag(), FGameplayEventData());
        else OnCompleted.Broadcast(FGameplayTag(), FGameplayEventData());
    }
    EndTask();
}
void UCombatAbilityTask_PlayMontageAndEvents::OnCancelled()
{
    if(bFinishing) return;
    bFinishing = true;
    if(ShouldBroadcastAbilityTaskDelegates()) OnInterrupted.Broadcast(FGameplayTag(), FGameplayEventData());
    EndTask();
}
void UCombatAbilityTask_PlayMontageAndEvents::OnDestroy(bool bAbilityEnded)
{
    bFinishing = true;
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
                FOnMontageBlendingOutStarted EmptyBlendDelegate;
                Anim->Montage_SetBlendingOutDelegate(EmptyBlendDelegate, MontageToPlay);
            }
            const auto* Character = Cast<ACombatCharacter>(Ability->GetAvatarActorFromActorInfo());
            if(Character && !Character->bIsBoss)
            {
                const auto& S = Character->GetLocomotionSettings();
                if(S.OverrideSkillBlendOut) { LocomotionBlendOut = S.SkillLocomotionBlendOut; InterruptBlendOut = S.SkillInterruptBlendOut; }
            }
            ASC->CurrentMontageStop(Character && Character->bLastSkillInterrupted ? InterruptBlendOut : LocomotionBlendOut);
        }
    }
    Super::OnDestroy(bAbilityEnded);
}
