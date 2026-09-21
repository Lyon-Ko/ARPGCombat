#include "CombatAnimInstance.h"
#include "CombatCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
void UCombatAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if(const auto* Character = Cast<ACombatCharacter>(TryGetPawnOwner()))
    {
        const FVector Velocity = Character->GetVelocity();
        Speed = Velocity.Size2D();
        const FVector Local = Character->GetActorTransform().InverseTransformVectorNoScale(Velocity);
        Direction = FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X));
        bInAir = Character->GetCharacterMovement()->IsFalling();
        bIsBoss = Character->bIsBoss;
    }
}
