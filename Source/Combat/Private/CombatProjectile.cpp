#include "CombatProjectile.h"
#include "CombatCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "NiagaraComponent.h"
ACombatProjectile::ACombatProjectile()
{
    PrimaryActorTick.bCanEverTick = true;
    Collision = CreateDefaultSubobject<UBoxComponent>(TEXT("Collision")); RootComponent = Collision;
    Collision->SetBoxExtent(FVector(24.f,85.f,20.f)); Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Collision->SetCollisionObjectType(ECC_WorldDynamic); Collision->SetCollisionResponseToAllChannels(ECR_Block); Collision->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    Collision->OnComponentBeginOverlap.AddDynamic(this, &ThisClass::OnOverlap); Collision->OnComponentHit.AddDynamic(this, &ThisClass::OnBlocked);
    Movement = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Movement")); Movement->UpdatedComponent = Collision;
    Movement->ProjectileGravityScale = 0.f; Movement->bRotationFollowsVelocity = true; Movement->bForceSubStepping = true;
    Visual = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Visual")); Visual->SetupAttachment(RootComponent); Visual->SetAutoActivate(false);
    WaveMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WaveMesh")); WaveMesh->SetupAttachment(RootComponent);
    WaveMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); WaveMesh->SetGenerateOverlapEvents(false); WaveMesh->SetCastShadow(false);
    InitialLifeSpan = 4.f;
}
void ACombatProjectile::InitializeProjectile(const FCombatHit& InHit, float Speed, FVector Direction, UNiagaraSystem* Effect, UStaticMesh* Mesh, UMaterialInterface* Material, FVector CollisionHalfExtent)
{
    CombatHit = InHit; Collision->IgnoreActorWhenMoving(InHit.Attacker, true);
    SetActorRotation(Direction.Rotation());
    Collision->SetBoxExtent(CollisionHalfExtent.GetAbs().ComponentMax(FVector(1.f)), false);
    WaveMesh->SetStaticMesh(Mesh);
    if(Material) WaveMesh->SetMaterial(0, Material);
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
    if(auto* Target = Cast<ACombatCharacter>(OtherActor); !bConsumed && Target && CombatHit.Attacker && Target->bIsBoss != CombatHit.Attacker->bIsBoss)
    {
        bConsumed = true;
        Collision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        CombatHit.Location = GetActorLocation(); CombatHit.Direction = Movement->Velocity.GetSafeNormal();
        Target->ReceiveCombatHit(CombatHit); Destroy();
    }
}
void ACombatProjectile::OnBlocked(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit) { bConsumed = true; Destroy(); }
