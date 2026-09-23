#include "CombatStateTree.h"
#include "CombatAIController.h"
#include "CombatCharacter.h"
#include "CombatSkillRuntime.h"
#include "StateTreeExecutionContext.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
static ACombatAIController* GetCombatAI(FStateTreeExecutionContext& Context) { return Cast<ACombatAIController>(Context.GetOwner()); }
EStateTreeRunStatus FCombatStateTreeSelectTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
    auto& Data = Context.GetInstanceData(*this); Data = FInstanceDataType();
    if(auto* AI = GetCombatAI(Context)) { Data.EnteredAt = AI->GetWorld()->GetTimeSeconds(); Data.Deadline = AI->RandomRange(AI->ReactionMin, AI->ReactionMax); AI->ObserveTarget(); return EStateTreeRunStatus::Running; }
    return EStateTreeRunStatus::Failed;
}
EStateTreeRunStatus FCombatStateTreeSelectTask::Tick(FStateTreeExecutionContext& Context, float DeltaTime) const
{
    auto* AI = GetCombatAI(Context); auto* Pawn = AI ? AI->GetCombatPawn() : nullptr;
    if(!Pawn) return EStateTreeRunStatus::Failed;
    if(!Pawn->IsAlive()) return EStateTreeRunStatus::Running;
    if(!Pawn->CombatTarget || !Pawn->CombatTarget->IsAlive())
    {
        if(!AI->ObserveTarget()) return EStateTreeRunStatus::Running;
        auto& RetryData = Context.GetInstanceData(*this); RetryData.Elapsed = 0.f; RetryData.EnteredAt = AI->GetWorld()->GetTimeSeconds();
    }
    // A tree restarted during this frame must not inherit time before EnterState.
    auto& Data = Context.GetInstanceData(*this); Data.Elapsed = static_cast<float>(FMath::Max(0.0, AI->GetWorld()->GetTimeSeconds() - Data.EnteredAt));
    if(Data.Elapsed < Data.Deadline || Pawn->IsBusy()) return EStateTreeRunStatus::Running;
    // Decisions use the delayed observed snapshot, never the player's button state.
    if(AI->SelectAction()) return EStateTreeRunStatus::Succeeded;
    if(Data.Elapsed < 2.2f)
    {
        FVector Direction = AI->ObservedTargetLocation - Pawn->GetActorLocation(); Direction.Z = 0;
        Pawn->AddMovementInput(Direction.GetSafeNormal());
        return EStateTreeRunStatus::Running;
    }
    AI->SelectedSkill = FGameplayTag();
    return EStateTreeRunStatus::Succeeded; // bounded failed chase must still pay recovery
}
EStateTreeRunStatus FCombatStateTreeExecuteTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
    auto& Data = Context.GetInstanceData(*this); Data = FInstanceDataType();
    auto* AI = GetCombatAI(Context); auto* Pawn = AI ? AI->GetCombatPawn() : nullptr;
    if(!Pawn || !Pawn->IsAlive()) return EStateTreeRunStatus::Succeeded;
    Data.EnteredAt = AI->GetWorld()->GetTimeSeconds();
    Pawn->GetCharacterMovement()->StopMovementImmediately();
    Data.bStarted = Pawn->RequestSkillByTag(AI->SelectedSkill);
    if(Data.bStarted) { AI->PreviousSkill = AI->SelectedSkill; ++AI->ActionsExecuted; if(auto* Skill = Pawn->GetActiveSkillDefinition()) Data.NextSkill = Skill->bDataDriven ? FGameplayTag() : Skill->NextSkillTag; }
    return Data.bStarted ? EStateTreeRunStatus::Running : EStateTreeRunStatus::Succeeded;
}
EStateTreeRunStatus FCombatStateTreeExecuteTask::Tick(FStateTreeExecutionContext& Context, float DeltaTime) const
{
    auto* AI = GetCombatAI(Context); auto* Pawn = AI ? AI->GetCombatPawn() : nullptr;
    if(!Pawn || !Pawn->IsAlive()) return EStateTreeRunStatus::Succeeded;
    auto& Data = Context.GetInstanceData(*this); Data.Elapsed = static_cast<float>(FMath::Max(0.0, AI->GetWorld()->GetTimeSeconds() - Data.EnteredAt));
    if(Data.Elapsed > 6.f) { Pawn->CancelCurrentSkill(); return EStateTreeRunStatus::Succeeded; }
    if(Pawn->IsBusy() || Pawn->SkillRuntime->HasPendingDerivation()) return EStateTreeRunStatus::Running;
    if(Pawn->bLastSkillInterrupted) return EStateTreeRunStatus::Succeeded;
    if(Data.NextSkill.IsValid() && Data.ChainCount < 4)
    {
        const FGameplayTag Next = Data.NextSkill; Data.NextSkill = FGameplayTag();
        if(Pawn->RequestSkillByTag(Next)) { ++Data.ChainCount; if(auto* Skill = Pawn->GetActiveSkillDefinition()) Data.NextSkill = Skill->bDataDriven ? FGameplayTag() : Skill->NextSkillTag; return EStateTreeRunStatus::Running; }
    }
    return EStateTreeRunStatus::Succeeded;
}
void FCombatStateTreeExecuteTask::ExitState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
    if(auto* AI = GetCombatAI(Context)) if(auto* Pawn = AI->GetCombatPawn(); Pawn && Pawn->IsBusy()) Pawn->CancelCurrentSkill();
}
EStateTreeRunStatus FCombatStateTreeRecoverTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
    auto& Data = Context.GetInstanceData(*this); Data = FInstanceDataType();
    if(auto* AI = GetCombatAI(Context)) { Data.EnteredAt = AI->GetWorld()->GetTimeSeconds(); Data.Deadline = AI->RandomRange(AI->RecoveryMin, AI->RecoveryMax); if(auto* Pawn = AI->GetCombatPawn(); Pawn && Pawn->bPhaseTwo) Data.Deadline *= .8f; AI->StopMovement(); }
    return EStateTreeRunStatus::Running;
}
EStateTreeRunStatus FCombatStateTreeRecoverTask::Tick(FStateTreeExecutionContext& Context, float DeltaTime) const
{
    auto* AI = GetCombatAI(Context); auto* Pawn = AI ? AI->GetCombatPawn() : nullptr;
    if(!Pawn) return EStateTreeRunStatus::Failed;
    if(!Pawn->IsAlive()) return EStateTreeRunStatus::Running;
    auto& Data = Context.GetInstanceData(*this); Data.Elapsed = static_cast<float>(FMath::Max(0.0, AI->GetWorld()->GetTimeSeconds() - Data.EnteredAt));
    return Data.Elapsed >= Data.Deadline ? EStateTreeRunStatus::Succeeded : EStateTreeRunStatus::Running;
}
