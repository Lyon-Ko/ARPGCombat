#include "CombatAnimNotify.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/ActiveMontageInstanceScope.h"
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
