#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CombatAnimInstance.generated.h"
class UAnimMontage;
class UBlendSpace;
struct FAnimNode_BlendSpacePlayer;
UCLASS(Blueprintable)
class COMBAT_API UCombatAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly, Category="Combat") float Speed = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") float Direction = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bInAir = false;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bIsBoss = false;
    // Incoming travel direction, relative to the actor, selects the reversal clip.
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion|Pivot") TObjectPtr<UAnimMontage> PivotForward;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion|Pivot") TObjectPtr<UAnimMontage> PivotBackward;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion|Pivot") TObjectPtr<UAnimMontage> PivotLeft;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion|Pivot") TObjectPtr<UAnimMontage> PivotRight;
    // Baked sword poses for free-facing reversals; PivotYaw drives yaw only.
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion|Pivot") TObjectPtr<UAnimMontage> FreePivotLeft;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion|Pivot") TObjectPtr<UAnimMontage> FreePivotRight;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion") TObjectPtr<UBlendSpace> GroundBlendSpace;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion") float AnimationPlayRate = 1.f;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion") float GroundAnimationPhase = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion|Pivot") float PivotExpectedRunPhase = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion|Pivot") bool bPivotPhaseAligned = false;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion|Pivot") float PivotProgress = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion|Pivot") float PivotElapsed = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Locomotion|Pivot") bool bPivotAccelerating = false;
    UFUNCTION(BlueprintPure, Category="Locomotion") bool IsPivoting() const { return ActivePivot != nullptr; }
    UFUNCTION(BlueprintPure, Category="Locomotion") bool IsPivotAccelerating() const { return IsPivoting() && bPivotAccelerating; }
    FVector GetPivotDirection() const { return PivotDesiredDirection; }
    float GetPivotCooldownRemaining() const { return PivotCooldownRemaining; }
    bool IsAuthoredFreePivot() const { return IsPivoting() && bAuthoredFreePivot; }
    FAnimMontageInstance* GetPivotDebugInstance() { return GetMontageInstanceForID(PivotInstanceID); }
    UFUNCTION(BlueprintCallable, Category="Locomotion") void StopGroundPivot();
    void UpdateGroundLocomotion(float DeltaSeconds, const FVector& DesiredDirection);
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    virtual void NativePostEvaluateAnimation() override;
private:
    FAnimNode_BlendSpacePlayer* FindGroundPlayer();
    void AlignHiddenGroundPhase(float DeltaSeconds);
    UPROPERTY(Transient) TObjectPtr<UAnimMontage> ActivePivot;
    float PivotCooldownRemaining = 0.f;
    int32 PivotInstanceID = INDEX_NONE;
    UPROPERTY(Transient) TMap<TObjectPtr<UAnimMontage>, TObjectPtr<UAnimMontage>> RuntimePivots;
    bool bPivotWasLocked = false;
    bool bWasGroundEligible = false;
    FVector PivotDesiredDirection = FVector::ZeroVector;
    float PivotStartYaw = 0.f;
    float PivotTurnAngle = 0.f;
    bool bAuthoredFreePivot = false;
    void OnPivotBlendingOut(UAnimMontage* Montage, bool bInterrupted);
    void OnPivotEnded(UAnimMontage* Montage, bool bInterrupted);
};
