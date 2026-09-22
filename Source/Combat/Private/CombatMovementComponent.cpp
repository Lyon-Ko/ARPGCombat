#include "CombatMovementComponent.h"
#include "CombatCharacter.h"
#include "CombatAnimInstance.h"
#include "CombatLocomotionSettings.h"

void UCombatMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    if(auto* Character = Cast<ACombatCharacter>(CharacterOwner); Character && !Character->bIsBoss)
    {
        const auto& S = UCombatLocomotionSubsystem::For(this);
        // Dash temporarily owns MaxAcceleration; leave that override intact.
        if(Character->GetActiveSkillTag().ToString() != TEXT("Combat.Skill.Dash")) MaxAcceleration = S.Acceleration;
        MaxWalkSpeed = S.ForwardSpeed;
        GroundFriction = S.GroundFriction;
        bUseSeparateBrakingFriction = true;
        BrakingFriction = S.BrakingFriction;
        BrakingFrictionFactor = S.BrakingFrictionFactor;
        BrakingDecelerationWalking = S.BrakingDeceleration;
        RotationRate = FRotator(0, S.TurnRate, 0);
        JumpZVelocity = S.JumpVelocity;
        GravityScale = S.GravityScale;
        AirControl = S.AirControl;
        BrakingDecelerationFalling = S.AirBrakingDeceleration;
        FallingLateralFriction = S.AirLateralFriction;
        Character->JumpMaxCount = FMath::RoundToInt(S.JumpCount);
    }
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    // Draw after movement so arrows use this frame's position and velocity.
    if(const auto* Character = Cast<ACombatCharacter>(CharacterOwner)) Character->DrawLocomotionDebug();
}

float UCombatMovementComponent::GetMaxSpeed() const
{
    const auto* Character = Cast<ACombatCharacter>(CharacterOwner);
    if(!Character || Character->bIsBoss || (!IsMovingOnGround() && !IsFalling())) return Super::GetMaxSpeed();
    const auto& S = UCombatLocomotionSubsystem::For(this);
    FVector Direction = Acceleration.IsNearlyZero() ? Velocity.GetSafeNormal2D() : Acceleration.GetSafeNormal2D();
    if(const auto* Anim = Cast<UCombatAnimInstance>(Character->GetMesh()->GetAnimInstance()); Anim && Anim->IsPivoting()) Direction = Anim->GetPivotDirection();
    if(Direction.IsNearlyZero()) return S.ForwardSpeed;
    const FVector Local = Character->GetActorTransform().InverseTransformVectorNoScale(Direction);
    const float XSpeed = Local.X >= 0.f ? S.ForwardSpeed : S.BackwardSpeed;
    const float YSpeed = Local.Y >= 0.f ? S.RightSpeed : S.LeftSpeed;
    // An ellipse preserves cardinal limits without boosting diagonal speed.
    return 1.f / FMath::Sqrt(FMath::Square(Local.X / XSpeed) + FMath::Square(Local.Y / YSpeed));
}

float UCombatMovementComponent::GetMaxAcceleration() const
{
    if(const auto* Character = Cast<ACombatCharacter>(CharacterOwner); Character && !Character->bIsBoss)
        if(const auto* Anim = Cast<UCombatAnimInstance>(Character->GetMesh()->GetAnimInstance()); Anim && Anim->IsPivoting())
            return UCombatLocomotionSubsystem::For(this).PivotReverseAcceleration;
    return Super::GetMaxAcceleration();
}

void UCombatMovementComponent::CalcVelocity(float DeltaTime, float Friction, bool bFluid, float BrakingDeceleration)
{
    const auto* Character = Cast<ACombatCharacter>(CharacterOwner);
    auto* Anim = Character ? Cast<UCombatAnimInstance>(Character->GetMesh()->GetAnimInstance()) : nullptr;
    if(!Character || Character->bIsBoss || !Anim || !Anim->IsPivoting() || !IsMovingOnGround())
    {
        Super::CalcVelocity(DeltaTime, Friction, bFluid, BrakingDeceleration);
        return;
    }
    const auto& S = UCombatLocomotionSubsystem::For(this);
    // Only friction policy is scoped; velocity remains UE's swept movement.
    const bool bSavedSeparateFriction = bUseSeparateBrakingFriction;
    bUseSeparateBrakingFriction = false;
    TGuardValue<float> FrictionFactorGuard(BrakingFrictionFactor, 1.f);
    if(Anim->IsPivotAccelerating())
    {
        Acceleration = Anim->GetPivotDirection() * S.PivotReverseAcceleration;
        Super::CalcVelocity(DeltaTime, S.PivotReverseFriction, bFluid, S.PivotBrakingDeceleration);
    }
    else
    {
        Acceleration = FVector::ZeroVector;
        Super::CalcVelocity(DeltaTime, S.PivotBrakingFriction, bFluid, S.PivotBrakingDeceleration);
    }
    bUseSeparateBrakingFriction = bSavedSeparateFriction;
}
