#include "CombatAnimNotify.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "Components/SkeletalMeshComponent.h"
void UCombatAnimNotify_Event::Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation, const FAnimNotifyEventReference& EventReference)
{
    Super::Notify(MeshComp, Animation, EventReference);
    if(MeshComp && MeshComp->GetOwner() && EventTag.IsValid())
    {
        FGameplayEventData Payload;
        Payload.EventTag = EventTag;
        Payload.Instigator = MeshComp->GetOwner();
        UAbilitySystemBlueprintLibrary::SendGameplayEventToActor(MeshComp->GetOwner(), EventTag, Payload);
    }
}
