#pragma once
#include "CoreMinimal.h"
#include "Tasks/StateTreeAITask.h"
#include "GameplayTagContainer.h"
#include "CombatStateTree.generated.h"
USTRUCT()
struct COMBAT_API FCombatStateTreeTaskData
{
    GENERATED_BODY()
    UPROPERTY() float Elapsed = 0.f;
    UPROPERTY() double EnteredAt = 0.0;
    UPROPERTY() float Deadline = 0.f;
    UPROPERTY() bool bStarted = false;
    UPROPERTY() FGameplayTag NextSkill;
    UPROPERTY() int32 ChainCount = 0;
};
USTRUCT(meta=(DisplayName="Combat Observe And Select", Category="Combat"))
struct COMBAT_API FCombatStateTreeSelectTask : public FStateTreeAITaskBase
{
    GENERATED_BODY()
    using FInstanceDataType = FCombatStateTreeTaskData;
    FCombatStateTreeSelectTask() { bShouldCallTick = true; }
    virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
    virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
    virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, float DeltaTime) const override;
};
USTRUCT(meta=(DisplayName="Combat Execute Skill", Category="Combat"))
struct COMBAT_API FCombatStateTreeExecuteTask : public FStateTreeAITaskBase
{
    GENERATED_BODY()
    using FInstanceDataType = FCombatStateTreeTaskData;
    FCombatStateTreeExecuteTask() { bShouldCallTick = true; }
    virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
    virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
    virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, float DeltaTime) const override;
    virtual void ExitState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
};
USTRUCT(meta=(DisplayName="Combat Guaranteed Recovery", Category="Combat"))
struct COMBAT_API FCombatStateTreeRecoverTask : public FStateTreeAITaskBase
{
    GENERATED_BODY()
    using FInstanceDataType = FCombatStateTreeTaskData;
    FCombatStateTreeRecoverTask() { bShouldCallTick = true; }
    virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
    virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
    virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, float DeltaTime) const override;
};
