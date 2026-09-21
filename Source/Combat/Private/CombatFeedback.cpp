#include "CombatFeedback.h"
#include "CombatCharacter.h"
#include "CombatTags.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
UCombatFeedbackComponent::UCombatFeedbackComponent() { PrimaryComponentTick.bCanEverTick = false; }
void UCombatFeedbackComponent::BeginPlay()
{
    Super::BeginPlay(); Character = Cast<ACombatCharacter>(GetOwner());
    if(Character) Character->OnCombatFeedback.AddDynamic(this, &ThisClass::Feedback);
}
void UCombatFeedbackComponent::BeginSkillFeedback(UCombatSkillDefinition* Skill)
{
    Definition = Skill;
    if(!Definition || !Character) return;
    if(Definition->CastSound) UGameplayStatics::PlaySoundAtLocation(this, Definition->CastSound, Character->GetActorLocation(), Character->MasterVolume);
    if(Definition->CastEffect) UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, Definition->CastEffect, Character->GetActorLocation(), Character->GetActorRotation());
}
void UCombatFeedbackComponent::EndSkillFeedback()
{
    EndTrail();
    if(WarningMesh) { WarningMesh->DestroyComponent(); WarningMesh = nullptr; }
    Definition = nullptr;
}
void UCombatFeedbackComponent::BeginTrail()
{
    if(Definition && Definition->TrailEffect && Character)
    {
        EndTrail();
        USceneComponent* Parent = Character->bTraceFromCharacterMesh ? static_cast<USceneComponent*>(Character->GetMesh()) : static_cast<USceneComponent*>(Character->WeaponMesh.Get());
        Trail = UNiagaraFunctionLibrary::SpawnSystemAttached(Definition->TrailEffect, Parent, Character->TraceEndSocket, FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::SnapToTarget, true);
    }
}
void UCombatFeedbackComponent::EndTrail() { if(Trail) { Trail->DeactivateImmediate(); Trail->DestroyComponent(); Trail = nullptr; } }
void UCombatFeedbackComponent::ShowWarning(FVector Center)
{
    if(!Definition || !Definition->AreaMesh || !Character) return;
    if(WarningMesh) WarningMesh->DestroyComponent();
    WarningMesh = NewObject<UStaticMeshComponent>(Character); WarningMesh->RegisterComponent();
    WarningMesh->SetStaticMesh(Definition->AreaMesh); WarningMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    WarningMesh->SetWorldLocation(Center - FVector(0,0,Character->GetSimpleCollisionHalfHeight() - 3.f));
    WarningMesh->SetWorldScale3D(FVector(Definition->AreaRadius / 50.f, Definition->AreaRadius / 50.f, .035f));
    if(Definition->AreaMaterial) WarningMesh->SetMaterial(0, Definition->AreaMaterial);
    if(auto* Material = WarningMesh->CreateDynamicMaterialInstance(0)) Material->SetVectorParameterValue(TEXT("Tint"), Definition->CueColor);
}
void UCombatFeedbackComponent::ReleaseArea()
{
    if(!Definition || !WarningMesh) return;
    WarningMesh->SetWorldScale3D(FVector(Definition->AreaRadius / 50.f, Definition->AreaRadius / 50.f, Definition->AreaHeight / 100.f));
    WarningMesh->SetWorldLocation(Character->GetActorLocation());
}
void UCombatFeedbackComponent::Feedback(ACombatCharacter* Source, ACombatCharacter* Target, FGameplayTag CueTag, FVector Location, float Intensity)
{
    UCombatSkillDefinition* Skill = Definition;
    if(!Skill && Source) Skill = Source->GetActiveSkillDefinition();
    if(!Skill && Target) Skill = Target->GetActiveSkillDefinition();
    if(Skill)
    {
        if(Skill->HitEffect && (CueTag == CombatTags::Cue_Hit || CueTag == CombatTags::Cue_Parry || CueTag == CombatTags::Cue_PoiseBreak)) UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, Skill->HitEffect, Location);
        USoundBase* Sound = CueTag == CombatTags::Cue_Parry ? Skill->ParrySound.Get() : Skill->HitSound.Get();
        if(Sound && (CueTag == CombatTags::Cue_Hit || CueTag == CombatTags::Cue_Parry)) UGameplayStatics::PlaySoundAtLocation(this, Sound, Location, Character ? Character->MasterVolume : 1.f);
    }
    if(Character && Character->bCameraShakeEnabled && Character->HitCameraShake)
        if(auto* PC = UGameplayStatics::GetPlayerController(this, 0)) PC->ClientStartCameraShake(Character->HitCameraShake, FMath::Clamp(Intensity, .2f, 1.5f));
}
