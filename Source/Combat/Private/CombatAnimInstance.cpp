#include "CombatAnimInstance.h"
#include "CombatCharacter.h"
#include "Animation/AnimMontage.h"
#include "Animation/BlendSpace.h"
#include "CombatLocomotionSettings.h"
#include "GameFramework/CharacterMovementComponent.h"
void UCombatAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if(const auto* Character = Cast<ACombatCharacter>(TryGetPawnOwner()))
    {
        const FVector Velocity = Character->GetVelocity();
        const auto& S = Character->GetLocomotionSettings();
        const float RealSpeed = Velocity.Size2D();
        float TargetSpeed = RealSpeed;
        if(!Character->bIsBoss && GroundBlendSpace)
        {
            // Remap configurable physical thresholds onto the authored sample grid.
            float JogCoordinate = GroundBlendSpace->GetBlendParameter(0).Max;
            for(const auto& Sample : GroundBlendSpace->GetBlendSamples())
                if(Sample.SampleValue.X > UE_KINDA_SMALL_NUMBER) JogCoordinate = FMath::Min(JogCoordinate, static_cast<float>(Sample.SampleValue.X));
            const float MaxCoordinate = GroundBlendSpace->GetBlendParameter(0).Max;
            TargetSpeed = RealSpeed <= S.AnimationJogSpeed ? RealSpeed / S.AnimationJogSpeed * JogCoordinate :
                FMath::Lerp(JogCoordinate, MaxCoordinate, FMath::Clamp((RealSpeed - S.AnimationJogSpeed) / (S.AnimationFastSpeed - S.AnimationJogSpeed), 0.f, 1.f));
        }
        Speed = !Character->bIsBoss && S.AnimationSpeedInterp > 0.f ? FMath::FInterpTo(Speed, TargetSpeed, DeltaSeconds, S.AnimationSpeedInterp) : TargetSpeed;
        const FVector Local = Character->GetActorTransform().InverseTransformVectorNoScale(Velocity);
        if(RealSpeed > S.AnimationIdleDirectionSpeed)
        {
            const float TargetDirection = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
            Direction = !Character->bIsBoss && S.AnimationDirectionInterp > 0.f ?
                FMath::RInterpTo(FRotator(0, Direction, 0), FRotator(0, TargetDirection, 0), DeltaSeconds, S.AnimationDirectionInterp).Yaw : TargetDirection;
        }
        AnimationPlayRate = Character->bIsBoss ? 1.f : S.AnimationPlayRate;
        bInAir = Character->GetCharacterMovement()->IsFalling();
        bIsBoss = Character->bIsBoss;
    }
}

void UCombatAnimInstance::StopGroundPivot()
{
    // Never stop a skill/hit/death montage which has taken over the shared slot.
    UAnimMontage* PreviousPivot = ActivePivot;
    ActivePivot = nullptr;
    if(auto* Instance = GetMontageInstanceForID(PivotInstanceID))
    {
        Instance->OnMontageBlendingOutStarted.Unbind();
        Instance->OnMontageEnded.Unbind();
    }
    PivotInstanceID = INDEX_NONE;
    PivotProgress = 0.f;
    PivotElapsed = 0.f;
    bPivotAccelerating = false;
    bAuthoredFreePivot = false;
    const auto& S = UCombatLocomotionSubsystem::For(this);
    if(PreviousPivot) Montage_Stop(S.PivotInterruptBlendOut, PreviousPivot);
    PivotCooldownRemaining = S.PivotCooldown;
    bWasGroundEligible = false;
}

void UCombatAnimInstance::OnPivotBlendingOut(UAnimMontage* Montage, bool bInterrupted)
{
    // Keep the movement policy during natural fading; interruption releases it.
    if(Montage == ActivePivot && bInterrupted) StopGroundPivot();
}

void UCombatAnimInstance::OnPivotEnded(UAnimMontage* Montage, bool bInterrupted)
{
    if(Montage == ActivePivot) StopGroundPivot();
}

void UCombatAnimInstance::UpdateGroundLocomotion(float DeltaSeconds, const FVector& DesiredDirection)
{
    auto* Character = Cast<ACombatCharacter>(TryGetPawnOwner());
    if(!Character) return;
    auto* Movement = Character->GetCharacterMovement();
    const auto& S = UCombatLocomotionSubsystem::For(this);
    PivotCooldownRemaining = FMath::Max(0.f, PivotCooldownRemaining - DeltaSeconds);
    const bool bEligible = S.PivotEnabled && Character->IsAlive() && !Character->IsBusy() && Movement->IsMovingOnGround();
    if(!bEligible)
    {
        if(ActivePivot) StopGroundPivot();
        bWasGroundEligible = false;
        return;
    }
    if(ActivePivot)
    {
        // Active-montage queries stop seeing a montage as soon as it blends out.
        // Keep ownership by instance ID until its full animation and fade finish.
        auto* Instance = GetMontageInstanceForID(PivotInstanceID);
        if(!Instance ||
            (S.PivotCancelOnRelease && DesiredDirection.IsNearlyZero()) ||
            (S.PivotCancelOnLockChange && Character->IsTargetLocked() != bPivotWasLocked) ||
            (!DesiredDirection.IsNearlyZero() && FVector::DotProduct(DesiredDirection, PivotDesiredDirection) < FMath::Cos(FMath::DegreesToRadians(S.PivotCancelAngle))))
        {
            StopGroundPivot();
            return;
        }
        PivotProgress = FMath::Clamp(Instance->GetPosition() / FMath::Max(ActivePivot->GetPlayLength(), UE_SMALL_NUMBER), 0.f, 1.f);
        PivotElapsed += DeltaSeconds;
        Instance->SetPlayRate(S.PivotPlayRate);
        ActivePivot->BlendOut.SetBlendTime(S.PivotBlendOut);
        ActivePivot->BlendOutTriggerTime = S.PivotBlendOutTriggerTime;
        if(bAuthoredFreePivot && !Character->IsTargetLocked() && ActivePivot->SlotAnimTracks.Num() > 0)
        {
            // Sample the sequence directly, independent of slot blend weight.
            // The baked pose has no root rotation, so apply the authored yaw once.
            float SequenceTime = 0.f;
            const auto* Segment = ActivePivot->SlotAnimTracks[0].AnimTrack.GetSegmentAtTime(Instance->GetPosition());
            if(const auto* Sequence = Segment ? Segment->GetAnimationData(Instance->GetPosition(), SequenceTime) : nullptr)
            {
                const float EndYaw = Sequence->EvaluateCurveData(TEXT("PivotYaw"), FAnimExtractContext(Sequence->GetPlayLength()));
                if(FMath::Abs(EndYaw) > 1.f)
                {
                    const float Yaw = Sequence->EvaluateCurveData(TEXT("PivotYaw"), FAnimExtractContext(SequenceTime));
                    Character->SetActorRotation(FRotator(0.f, PivotStartYaw + PivotTurnAngle * (Yaw / EndYaw), 0.f));
                }
            }
        }
        else if(!Character->IsTargetLocked() && PivotElapsed >= S.PivotTurnDelay)
            Character->SetActorRotation(FMath::RInterpConstantTo(Character->GetActorRotation(), PivotDesiredDirection.Rotation(), DeltaSeconds, S.PivotTurnRate));
        const float FacingAngle = FMath::Abs(FMath::FindDeltaAngleDegrees(Character->GetActorRotation().Yaw, PivotDesiredDirection.Rotation().Yaw));
        if(!bPivotAccelerating && !DesiredDirection.IsNearlyZero() && Movement->Velocity.Size2D() <= S.PivotStopSpeed &&
            PivotElapsed >= S.PivotReverseDelay && PivotProgress >= S.PivotReverseMinProgress &&
            (Character->IsTargetLocked() || FacingAngle <= S.PivotReverseMaxFacingAngle)) bPivotAccelerating = true;
        if(DesiredDirection.IsNearlyZero()) bPivotAccelerating = false;
        if(S.PivotEarlyExit && bPivotAccelerating && (!bAuthoredFreePivot || FacingAngle <= 5.f) && PivotProgress >= S.PivotExitMinProgress &&
            FVector::DotProduct(Movement->Velocity, PivotDesiredDirection) >= S.PivotExitMinSpeed) StopGroundPivot();
        return;
    }
    if(IsAnyMontagePlaying()) { bWasGroundEligible = false; return; }
    const bool bCanStart = bWasGroundEligible;
    bWasGroundEligible = true;
    const FVector Velocity = Character->GetVelocity().GetSafeNormal2D();
    if(!bCanStart || PivotCooldownRemaining > 0.f || DesiredDirection.IsNearlyZero() ||
        Character->GetVelocity().Size2D() < S.PivotMinSpeed ||
        FVector::DotProduct(Velocity, DesiredDirection) > FMath::Cos(FMath::DegreesToRadians(S.PivotMinAngle))) return;
    const FVector LocalVelocity = Character->GetActorTransform().InverseTransformVectorNoScale(Velocity);
    UAnimMontage* Montage = FMath::Abs(LocalVelocity.X) >= FMath::Abs(LocalVelocity.Y)
        ? (LocalVelocity.X >= 0.f ? PivotForward : PivotBackward)
        : (LocalVelocity.Y >= 0.f ? PivotRight : PivotLeft);
    const float TurnAngle = FMath::FindDeltaAngleDegrees(Character->GetActorRotation().Yaw, DesiredDirection.Rotation().Yaw);
    const bool bUseFreePivot = !Character->IsTargetLocked() && FreePivotLeft && FreePivotRight;
    if(bUseFreePivot) Montage = TurnAngle < 0.f ? FreePivotLeft : FreePivotRight;
    if(!Montage) return;
    auto& RuntimeMontage = RuntimePivots.FindOrAdd(Montage);
    if(!RuntimeMontage) RuntimeMontage = DuplicateObject<UAnimMontage>(Montage, this);
    Montage = RuntimeMontage;
    Montage->RateScale = 1.f;
    Montage->BlendIn.SetBlendTime(S.PivotBlendIn);
    Montage->BlendOut.SetBlendTime(S.PivotBlendOut);
    Montage->BlendOutTriggerTime = S.PivotBlendOutTriggerTime;
    if(Montage_Play(Montage, S.PivotPlayRate) > 0.f)
    {
        ActivePivot = Montage;
        bAuthoredFreePivot = bUseFreePivot;
        PivotStartYaw = Character->GetActorRotation().Yaw;
        PivotTurnAngle = TurnAngle;
        PivotDesiredDirection = DesiredDirection;
        PivotProgress = 0.f;
        PivotElapsed = 0.f;
        bPivotAccelerating = false;
        bPivotWasLocked = Character->IsTargetLocked();
        if(auto* Instance = GetActiveInstanceForMontage(Montage))
        {
            PivotInstanceID = Instance->GetInstanceID();
            Instance->OnMontageBlendingOutStarted.BindUObject(this, &ThisClass::OnPivotBlendingOut);
            Instance->OnMontageEnded.BindUObject(this, &ThisClass::OnPivotEnded);
        }
        else StopGroundPivot();
    }
}
