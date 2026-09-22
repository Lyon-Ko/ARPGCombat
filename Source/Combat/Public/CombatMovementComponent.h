#pragma once
#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "CombatMovementComponent.generated.h"

/** Keeps UE collision/floor movement while giving pivot its own velocity policy. */
UCLASS()
class COMBAT_API UCombatMovementComponent : public UCharacterMovementComponent
{
    GENERATED_BODY()
public:
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual float GetMaxSpeed() const override;
    virtual float GetMaxAcceleration() const override;
    virtual void CalcVelocity(float DeltaTime, float Friction, bool bFluid, float BrakingDeceleration) override;
};
