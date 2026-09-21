#include "CombatAIController.h"
#include "CombatCharacter.h"
#include "Components/StateTreeAIComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
ACombatAIController::ACombatAIController()
{
    StateTreeComponent = CreateDefaultSubobject<UStateTreeAIComponent>(TEXT("CombatStateTree"));
    StateTreeComponent->SetStartLogicAutomatically(false);
    bStartAILogicOnPossess = false;
}
void ACombatAIController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    Random.Initialize(RandomSeed);
    if(CombatStateTree) { StateTreeComponent->SetStateTree(CombatStateTree); StateTreeComponent->StartLogic(); }
}
ACombatCharacter* ACombatAIController::GetCombatPawn() const { return Cast<ACombatCharacter>(GetPawn()); }
void ACombatAIController::ResetBrain()
{
    StateTreeComponent->StopLogic(TEXT("Encounter reset")); StopMovement(); ClearFocus(EAIFocusPriority::Gameplay);
    Random.Initialize(RandomSeed); SelectedSkill = PreviousSkill = FGameplayTag(); ActionsExecuted = 0;
    if(CombatStateTree) { StateTreeComponent->SetStateTree(CombatStateTree); StateTreeComponent->StartLogic(); }
}
bool ACombatAIController::ObserveTarget()
{
    auto* CombatPawn = GetCombatPawn();
    auto* Target = Cast<ACombatCharacter>(UGameplayStatics::GetPlayerPawn(GetWorld(), 0));
    if(!CombatPawn || !Target || !CombatPawn->IsAlive() || !Target->IsAlive()) return false;
    CombatPawn->SetCombatTarget(Target);
    ObservedTargetLocation = Target->GetActorLocation(); ObservedTargetSkill = Target->GetActiveSkillTag();
    SetFocus(Target);
    return true;
}
bool ACombatAIController::SelectAction()
{
    auto* CombatPawn = GetCombatPawn();
    if(!CombatPawn || !CombatPawn->IsAlive()) return false;
    const float Distance = FVector::Dist2D(CombatPawn->GetActorLocation(), ObservedTargetLocation);
    struct FChoice { FGameplayTag Tag; float Weight; };
    TArray<FChoice> Choices; float Total = 0.f;
    for(UCombatSkillDefinition* Skill : CombatPawn->SkillDefinitions)
    {
        if(!Skill || !Skill->SkillTag.ToString().StartsWith(TEXT("Combat.Skill.Boss.")) || Skill->SelectionWeight <= 0 || CombatPawn->GetSkillCooldownRemaining(Skill->SkillTag) > 0) continue;
        if(Distance < Skill->MinAIRange || Distance > Skill->MaxAIRange) continue;
        if(Skill->MovementDistance > 150.f)
        {
            FHitResult Wall;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(CombatAIRetreat), false, CombatPawn);
            const FVector Desired = CombatPawn->GetActorLocation() + CombatPawn->GetActorTransform().TransformVectorNoScale(Skill->MovementDirectionLocal).GetSafeNormal() * Skill->MovementDistance;
            GetWorld()->SweepSingleByChannel(Wall, CombatPawn->GetActorLocation(), Desired, FQuat::Identity, ECC_WorldStatic, FCollisionShape::MakeCapsule(CombatPawn->GetCapsuleComponent()->GetScaledCapsuleRadius(), CombatPawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Params);
            if(Wall.bBlockingHit && Wall.Time < .65f) continue;
        }
        float Weight = Skill->SelectionWeight;
        if(Skill->SkillTag == PreviousSkill) Weight *= .18f;
        const FString Name = Skill->SkillTag.ToString();
        if(ObservedTargetSkill.ToString().Contains(TEXT("Parry")) && (Name.Contains(TEXT("AOE")) || Name.Contains(TEXT("Leap")))) Weight *= 2.2f;
        if(ObservedTargetSkill.ToString().Contains(TEXT("Attack")) && Name.Contains(TEXT("LeapBack"))) Weight *= 1.8f;
        if(CombatPawn->bPhaseTwo && (Name.Contains(TEXT("AOE")) || Name.Contains(TEXT("Dash")))) Weight *= 1.4f;
        Choices.Add({Skill->SkillTag, Weight}); Total += Weight;
    }
    if(Choices.IsEmpty()) return false;
    float Pick = Random.FRandRange(0.f, Total);
    for(const FChoice& Choice : Choices) { Pick -= Choice.Weight; if(Pick <= 0.f) { SelectedSkill = Choice.Tag; return true; } }
    SelectedSkill = Choices.Last().Tag; return true;
}

