#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "GameplayTagContainer.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "CombatSkillAuthoring.h"
#include "CombatAnimNotify.generated.h"
UCLASS(meta=(DisplayName="Combat Gameplay Event"))
class COMBAT_API UCombatAnimNotify_Event : public UAnimNotify
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FGameplayTag EventTag;
    virtual void Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation, const FAnimNotifyEventReference& EventReference) override;
    virtual FString GetNotifyName_Implementation() const override { return EventTag.ToString(); }
};

/** Asset configuration only. All per-character execution state lives in SkillRuntime. */
UCLASS(meta=(DisplayName="Combat Skill Action · 技能事件"))
class COMBAT_API UCombatAnimNotify_SkillAction : public UAnimNotify
{
    GENERATED_BODY()
public:
    UCombatAnimNotify_SkillAction();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="技能事件", meta=(ShowOnlyInnerProperties)) FCombatSkillEvent Action;
    virtual void Notify(USkeletalMeshComponent* MeshComp,UAnimSequenceBase* Animation,const FAnimNotifyEventReference& Reference) override;
    virtual FString GetNotifyName_Implementation() const override;
    virtual void BranchingPointNotify(FBranchingPointNotifyPayload& Payload) override;
#if WITH_EDITOR
    virtual bool CanBePlaced(UAnimSequenceBase* Animation) const override;
    virtual bool ShouldFireInEditor() override { return false; }
#endif
};

UCLASS(meta=(DisplayName="Combat Skill Window · 技能窗口"))
class COMBAT_API UCombatAnimNotifyState_SkillWindow : public UAnimNotifyState
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="技能窗口") ECombatSkillWindowType WindowType = ECombatSkillWindowType::Derivation;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="技能窗口") FName WindowName = TEXT("Combo");
    virtual void NotifyBegin(USkeletalMeshComponent* MeshComp,UAnimSequenceBase* Animation,float TotalDuration,const FAnimNotifyEventReference& Reference) override;
    virtual void NotifyEnd(USkeletalMeshComponent* MeshComp,UAnimSequenceBase* Animation,const FAnimNotifyEventReference& Reference) override;
    virtual void BranchingPointNotifyBegin(FBranchingPointNotifyPayload& Payload) override;
    virtual void BranchingPointNotifyEnd(FBranchingPointNotifyPayload& Payload) override;
    virtual FString GetNotifyName_Implementation() const override;
#if WITH_EDITOR
    virtual bool CanBePlaced(UAnimSequenceBase* Animation) const override;
    virtual bool ShouldFireInEditor() override { return false; }
#endif
};
