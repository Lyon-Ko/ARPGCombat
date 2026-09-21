#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "CombatAnimInstance.generated.h"
UCLASS(Blueprintable)
class COMBAT_API UCombatAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly, Category="Combat") float Speed = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") float Direction = 0.f;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bInAir = false;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bIsBoss = false;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
};
