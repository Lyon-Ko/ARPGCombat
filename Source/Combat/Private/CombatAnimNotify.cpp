#include "CombatAnimNotify.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/ActiveMontageInstanceScope.h"
#include "CombatCharacter.h"
#include "CombatSkillRuntime.h"
#include "Engine/World.h"
void UCombatAnimNotify_Event::Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation, const FAnimNotifyEventReference& EventReference)
{
    Super::Notify(MeshComp, Animation, EventReference);
    if(MeshComp && MeshComp->GetOwner() && EventTag.IsValid())
    {
        FGameplayEventData Payload;
        Payload.EventTag = EventTag;
        Payload.Instigator = MeshComp->GetOwner();
        Payload.OptionalObject = Animation;
        if(const auto* Context = EventReference.GetContextData<UE::Anim::FAnimNotifyMontageInstanceContext>())
        {
            auto* Anim = MeshComp->GetAnimInstance();
            auto* Instance = Anim ? Anim->GetMontageInstanceForID(Context->MontageInstanceID) : nullptr;
            // Asset identity alone is insufficient when the same attack is replayed.
            if(!Instance || Anim->GetActiveInstanceForMontage(Instance->Montage) != Instance) return;
            Payload.OptionalObject = Instance->Montage;
        }
        UAbilitySystemBlueprintLibrary::SendGameplayEventToActor(MeshComp->GetOwner(), EventTag, Payload);
    }
}

static UCombatSkillRuntime* SkillNotifyRuntime(USkeletalMeshComponent* Mesh,UAnimSequenceBase* Animation,const FAnimNotifyEventReference& Ref)
{
    if(!Mesh || !Mesh->GetWorld() || !Mesh->GetWorld()->IsGameWorld()) return nullptr;
    auto* C=Cast<ACombatCharacter>(Mesh->GetOwner());
    const auto* Context=Ref.GetContextData<UE::Anim::FAnimNotifyMontageInstanceContext>();
    if(!C || Mesh!=C->GetMesh() || !C->IsAlive() || !Context) return nullptr;
    return C->SkillRuntime->AcceptMontageNotify(Cast<UAnimMontage>(Animation),Context->MontageInstanceID)?C->SkillRuntime.Get():nullptr;
}
UCombatAnimNotify_SkillAction::UCombatAnimNotify_SkillAction()
{
    Action.Type=ECombatSkillEventType::Projectile;
#if WITH_EDITORONLY_DATA
    NotifyColor=FColor(40,170,230);
#endif
}
void UCombatAnimNotify_SkillAction::Notify(USkeletalMeshComponent* Mesh,UAnimSequenceBase* Animation,const FAnimNotifyEventReference& Ref)
{ if(auto* Runtime=SkillNotifyRuntime(Mesh,Animation,Ref)) Runtime->ExecuteMontageAction(Action); }
void UCombatAnimNotify_SkillAction::BranchingPointNotify(FBranchingPointNotifyPayload& P)
{ FAnimNotifyEventReference Ref(P.NotifyEvent,P.SequenceAsset); Ref.AddContextData<UE::Anim::FAnimNotifyMontageInstanceContext>(P.MontageInstanceID); Notify(P.SkelMeshComponent,P.SequenceAsset,Ref); }
FString UCombatAnimNotify_SkillAction::GetNotifyName_Implementation() const
{ return Action.Label.IsEmpty()?TEXT("技能 · ")+StaticEnum<ECombatSkillEventType>()->GetDisplayNameTextByValue(int64(Action.Type)).ToString():Action.Label; }
void UCombatAnimNotifyState_SkillWindow::NotifyBegin(USkeletalMeshComponent* Mesh,UAnimSequenceBase* Animation,float Duration,const FAnimNotifyEventReference& Ref)
{ if(auto* Runtime=SkillNotifyRuntime(Mesh,Animation,Ref)) Runtime->BeginMontageWindow(this,WindowType,WindowName); }
void UCombatAnimNotifyState_SkillWindow::NotifyEnd(USkeletalMeshComponent* Mesh,UAnimSequenceBase* Animation,const FAnimNotifyEventReference& Ref)
{ if(auto* Runtime=SkillNotifyRuntime(Mesh,Animation,Ref)) Runtime->EndMontageWindow(this); }
void UCombatAnimNotifyState_SkillWindow::BranchingPointNotifyBegin(FBranchingPointNotifyPayload& P)
{ FAnimNotifyEventReference Ref(P.NotifyEvent,P.SequenceAsset); Ref.AddContextData<UE::Anim::FAnimNotifyMontageInstanceContext>(P.MontageInstanceID); NotifyBegin(P.SkelMeshComponent,P.SequenceAsset,P.NotifyEvent?P.NotifyEvent->GetDuration():0.f,Ref); }
void UCombatAnimNotifyState_SkillWindow::BranchingPointNotifyEnd(FBranchingPointNotifyPayload& P)
{ FAnimNotifyEventReference Ref(P.NotifyEvent,P.SequenceAsset); Ref.AddContextData<UE::Anim::FAnimNotifyMontageInstanceContext>(P.MontageInstanceID); NotifyEnd(P.SkelMeshComponent,P.SequenceAsset,Ref); }
FString UCombatAnimNotifyState_SkillWindow::GetNotifyName_Implementation() const
{ return FString(WindowType==ECombatSkillWindowType::Hit?TEXT("命中窗口 · "):WindowType==ECombatSkillWindowType::Cancel?TEXT("取消窗口 · "):TEXT("派生窗口 · "))+WindowName.ToString(); }
#if WITH_EDITOR
bool UCombatAnimNotify_SkillAction::CanBePlaced(UAnimSequenceBase* Animation) const { return Animation && Animation->IsA<UAnimMontage>(); }
bool UCombatAnimNotifyState_SkillWindow::CanBePlaced(UAnimSequenceBase* Animation) const { return Animation && Animation->IsA<UAnimMontage>(); }
#endif
