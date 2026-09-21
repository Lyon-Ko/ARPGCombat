#include "CombatProjectile.h"
#include "CombatCharacter.h"
#include "Components/SphereComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "NiagaraComponent.h"
ACombatProjectile::ACombatProjectile()
{
    PrimaryActorTick.bCanEverTick = true;
    Collision = CreateDefaultSubobject<USphereComponent>(TEXT("Collision")); RootComponent = Collision;
    Collision->SetSphereRadius(28.f); Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Collision->SetCollisionObjectType(ECC_WorldDynamic); Collision->SetCollisionResponseToAllChannels(ECR_Block); Collision->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    Collision->OnComponentBeginOverlap.AddDynamic(this, &ThisClass::OnOverlap); Collision->OnComponentHit.AddDynamic(this, &ThisClass::OnBlocked);
    Movement = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Movement")); Movement->UpdatedComponent = Collision;
    Movement->ProjectileGravityScale = 0.f; Movement->bRotationFollowsVelocity = true; Movement->bForceSubStepping = true;
    Visual = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Visual")); Visual->SetupAttachment(RootComponent); Visual->SetAutoActivate(false);
    InitialLifeSpan = 4.f;
}
void ACombatProjectile::InitializeProjectile(const FCombatHit& InHit, float Speed, FVector Direction, UNiagaraSystem* Effect)
{
    CombatHit = InHit; Collision->IgnoreActorWhenMoving(InHit.Attacker, true);
    Movement->Velocity = Direction.GetSafeNormal() * Speed; Movement->InitialSpeed = Movement->MaxSpeed = Speed;
    if(Effect) { Visual->SetAsset(Effect); Visual->Activate(true); }
}
void ACombatProjectile::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!CombatHit.Attacker || !CombatHit.Attacker->IsAlive()) Destroy();
}
void ACombatProjectile::OnOverlap(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 BodyIndex, bool bFromSweep, const FHitResult& Hit)
{
    if(auto* Target = Cast<ACombatCharacter>(OtherActor); Target && CombatHit.Attacker && Target->bIsBoss != CombatHit.Attacker->bIsBoss)
    {
        CombatHit.Location = GetActorLocation(); CombatHit.Direction = Movement->Velocity.GetSafeNormal();
        Target->ReceiveCombatHit(CombatHit); Destroy();
    }
}
void ACombatProjectile::OnBlocked(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit) { Destroy(); }
