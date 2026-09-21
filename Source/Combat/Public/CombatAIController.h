#pragma once
#include "CoreMinimal.h"
#include "AIController.h"
#include "GameplayTagContainer.h"
#include "CombatAIController.generated.h"
class UStateTree;
class UStateTreeAIComponent;
class ACombatCharacter;
UCLASS(Blueprintable)
class COMBAT_API ACombatAIController : public AAIController
{
    GENERATED_BODY()
public:
    ACombatAIController();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UStateTreeAIComponent> StateTreeComponent;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TObjectPtr<UStateTree> CombatStateTree;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") int32 RandomSeed = 731;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float ReactionMin = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float ReactionMax = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float RecoveryMin = .45f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float RecoveryMax = .8f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") FGameplayTag SelectedSkill;
    UPROPERTY(BlueprintReadOnly, Category="Combat") FGameplayTag PreviousSkill;
    UPROPERTY(BlueprintReadOnly, Category="Combat") FVector ObservedTargetLocation;
    UPROPERTY(BlueprintReadOnly, Category="Combat") FGameplayTag ObservedTargetSkill;
    UPROPERTY(BlueprintReadOnly, Category="Combat") int32 ActionsExecuted = 0;
    UFUNCTION(BlueprintCallable) void ResetBrain();
    UFUNCTION(BlueprintPure) ACombatCharacter* GetCombatPawn() const;
    bool ObserveTarget();
    bool SelectAction();
    float RandomRange(float Minimum, float Maximum) { return Random.FRandRange(Minimum, Maximum); }
protected:
    virtual void OnPossess(APawn* InPawn) override;
private:
    FRandomStream Random;
};
