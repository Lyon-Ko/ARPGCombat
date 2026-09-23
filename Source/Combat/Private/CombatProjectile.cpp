#include "CombatProjectile.h"
#include "CombatCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "NiagaraComponent.h"
#include "CombatSkillRuntime.h"
#include "CombatAttributeSet.h"
#include "EngineUtils.h"
#include "NiagaraFunctionLibrary.h"
#include "Kismet/GameplayStatics.h"
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
    else if(Data && bDataActive) AdvanceDefinition(DeltaSeconds);
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

void ACombatProjectile::InitializeDefinition(UCombatProjectileDefinition* Definition, ACombatCharacter* Source, ACombatCharacter* Target, FVector Direction, uint64 Serial)
{
    Data = DuplicateObject<UCombatProjectileDefinition>(Definition,this); OwnerSerial = Serial; HomingTarget = Target;
    CombatHit.ExecutionSerial = Serial;
    CombatHit.Attacker = Source; CombatHit.Damage = Data->Damage * Source->Attributes->GetDamageMultiplier();
    CombatHit.PoiseDamage = Data->PoiseDamage; CombatHit.bParryable = Data->bParryable; CombatHit.AttackInstance = Source->AllocateAttackInstance();
    Collision->SetCollisionEnabled(ECollisionEnabled::NoCollision); Movement->Deactivate();
    DataVelocity = Direction.GetSafeNormal() * FMath::Max(1.f,Data->Speed);
    WaveMesh->SetStaticMesh(Data->Mesh); if(Data->Material) WaveMesh->SetMaterial(0,Data->Material);
    if(Data->FlightEffect) { Visual->SetAsset(Data->FlightEffect); Visual->Activate(); }
    InitialLifeSpan = 0;
}
void ACombatProjectile::ActivateDefinition()
{
    if(!Data || IsActorBeingDestroyed()) return;
    SetLifeSpan(0); bDataActive = true;
    if(Data->Motion == ECombatProjectileMotion::Guided)
    {
        if(HomingTarget.IsValid())
        {
            FVector To = HomingTarget->GetActorLocation() - GetActorLocation();
            if(To.Size() > Data->AcquireRange || FVector::DotProduct(To.GetSafeNormal(),DataVelocity.GetSafeNormal()) < FMath::Cos(FMath::DegreesToRadians(Data->AcquireHalfAngle))) HomingTarget.Reset();
        }
        if(!HomingTarget.IsValid()) AcquireTarget();
    }
    AdvanceDefinition(0.f); // Resolve an initial overlap before the first movement tick.
}
void ACombatProjectile::CancelForSkill(uint64 Serial)
{ if(Data && OwnerSerial == Serial && Data->bDestroyOnInterrupt) Destroy(); }
void ACombatProjectile::AcquireTarget()
{
    HomingTarget.Reset();
    float Best = FMath::Square(Data->AcquireRange);
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
    {
        if(!It->IsAlive() || It->bIsBoss == CombatHit.Attacker->bIsBoss) continue;
        const FVector To = It->GetActorLocation() - GetActorLocation();
        if(To.SizeSquared() >= Best || FVector::DotProduct(To.GetSafeNormal(),DataVelocity.GetSafeNormal()) < FMath::Cos(FMath::DegreesToRadians(Data->AcquireHalfAngle))) continue;
        FHitResult Block; FCollisionQueryParams Q(SCENE_QUERY_STAT(MissileAcquire),false,this); Q.AddIgnoredActor(CombatHit.Attacker);
        if(GetWorld()->LineTraceSingleByChannel(Block,GetActorLocation(),It->GetActorLocation(),ECC_Visibility,Q) && Block.GetActor() != *It) continue;
        Best = To.SizeSquared(); HomingTarget = *It;
    }
    NextAcquire = Age + FMath::Max(.05f,Data->ReacquireInterval);
}
void ACombatProjectile::AdvanceDefinition(float DeltaSeconds)
{
    const int32 Steps = FMath::Clamp(FMath::CeilToInt(DeltaSeconds * 120.f),1,128);
    const float Step = DeltaSeconds / Steps;
    for(int32 Index=0; Index<Steps && !bConsumed && !IsActorBeingDestroyed(); ++Index)
    {
        Age += Step;
        if(Age >= Data->Lifetime || Travel >= Data->MaxDistance) { Destroy(); return; }
        if(Data->Motion == ECombatProjectileMotion::Guided && Age >= Data->GuidanceDelay)
        {
            if(HomingTarget.IsValid() && (!HomingTarget->IsAlive() || FVector::DistSquared(HomingTarget->GetActorLocation(),GetActorLocation()) > FMath::Square(Data->AcquireRange))) HomingTarget.Reset();
            if(!HomingTarget.IsValid())
            {
                if(Data->LostTarget == ECombatLostTarget::Destroy) { Destroy(); return; }
                if(Data->LostTarget == ECombatLostTarget::Reacquire && Age >= NextAcquire) AcquireTarget();
            }
            if(HomingTarget.IsValid())
            {
                const FVector Aim = HomingTarget->GetActorLocation() + HomingTarget->GetVelocity() * Data->PredictionSeconds;
                const FVector Current = DataVelocity.GetSafeNormal(), Desired = (Aim-GetActorLocation()).GetSafeNormal();
                const float Angle = FMath::Acos(FMath::Clamp(FVector::DotProduct(Current,Desired),-1.f,1.f));
                const float Fraction = Angle > SMALL_NUMBER ? FMath::Min(1.f,FMath::DegreesToRadians(Data->TurnDegreesPerSecond)*Step/Angle) : 1.f;
                DataVelocity = FQuat::Slerp(FQuat::Identity,FQuat::FindBetweenNormals(Current,Desired),Fraction).RotateVector(Current) * DataVelocity.Size();
                if(FVector::DistSquared(HomingTarget->GetActorLocation(),GetActorLocation()) <= FMath::Square(Data->ProximityRadius)) { Impact(HomingTarget.Get(),GetActorLocation()); return; }
            }
        }
        const float Speed = FMath::Clamp(DataVelocity.Size() + Data->Acceleration*Step,1.f,FMath::Max(1.f,Data->MaxSpeed));
        DataVelocity = DataVelocity.GetSafeNormal() * Speed;
        if(Data->Motion == ECombatProjectileMotion::Ballistic) DataVelocity.Z += GetWorld()->GetGravityZ()*Data->GravityScale*Step;
        const FVector Start = GetActorLocation();
        const FVector End = Start + DataVelocity*Step;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(CombatProjectileSweep),false,this); Params.AddIgnoredActor(CombatHit.Attacker);
        for(const auto& T : HitTargets) if(T.IsValid()) Params.AddIgnoredActor(T.Get());
        FCollisionObjectQueryParams Objects; Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic); Objects.AddObjectTypesToQuery(ECC_Pawn);
        const FCollisionShape Shape = Data->bSphereCollision ? FCollisionShape::MakeSphere(FMath::Max(1.f,Data->Radius)) : FCollisionShape::MakeBox(Data->HalfExtent.GetAbs().ComponentMax(FVector(1)));
        TArray<FHitResult> Hits; GetWorld()->SweepMultiByObjectType(Hits,Start,End,DataVelocity.Rotation().Quaternion(),Objects,Shape,Params);
        Hits.StableSort([](const auto& A,const auto& B) { return A.Time < B.Time; });
        bool Reflected = false;
        for(const auto& H : Hits)
        {
            if(H.GetActor() == this || Cast<ACombatProjectile>(H.GetActor())) continue;
            if(auto* Target = Cast<ACombatCharacter>(H.GetActor()))
            {
                if(!Target->IsAlive() || Target->bIsBoss == CombatHit.Attacker->bIsBoss || HitTargets.Contains(Target)) continue;
                HitTargets.Add(Target);
                if(Pierced++ < Data->Penetrations)
                { ApplyPayload(Target,H.ImpactPoint,1.f,CombatHit.AttackInstance); if(IsActorBeingDestroyed()) return; continue; }
                SetActorLocation(H.Location); Impact(Target,H.ImpactPoint); return;
            }
            if(!H.bBlockingHit) continue;
            if(Bounced++ < Data->Bounces && !H.bStartPenetrating)
            {
                Travel += FVector::Dist(Start,H.Location); SetActorLocation(H.Location + H.ImpactNormal * .5f);
                DataVelocity = FMath::GetReflectionVector(DataVelocity,H.ImpactNormal); Reflected = true; break;
            }
            SetActorLocation(H.Location); Impact(nullptr,H.ImpactPoint); return;
        }
        if(!Reflected) { SetActorLocation(End); Travel += FVector::Dist(Start,End); }
        SetActorRotation(DataVelocity.Rotation());
    }
}
void ACombatProjectile::ApplyPayload(ACombatCharacter* Target, FVector Location, float Scale, int32 Instance)
{
    FCombatHit Hit = CombatHit; Hit.AttackInstance = Instance; Hit.Location = Location; Hit.Direction = DataVelocity.GetSafeNormal(); Hit.Damage *= Scale; Hit.PoiseDamage *= Scale;
    const auto Result = Target->ReceiveCombatHit(Hit);
    if(!IsActorBeingDestroyed() && Data->HitBuff && Result == ECombatHitResult::Damaged) Target->SkillRuntime->AddBuff(Data->HitBuff,CombatHit.Attacker);
}
void ACombatProjectile::Impact(ACombatCharacter* Target, FVector Location)
{
    if(bConsumed) return; bConsumed = true;
    if(Data->ImpactEffect) UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),Data->ImpactEffect,Location);
    if(Data->ImpactSound) UGameplayStatics::PlaySoundAtLocation(this,Data->ImpactSound,Location);
    if(Target && (Data->ExplosionRadius <= 0.f || Data->bStackDirectAndExplosion)) ApplyPayload(Target,Location,1.f,CombatHit.AttackInstance);
    if(IsActorBeingDestroyed()) return;
    if(Data->ExplosionRadius > 0.f && CombatHit.Attacker && CombatHit.Attacker->IsAlive())
    {
        const int32 Id = CombatHit.Attacker->AllocateAttackInstance();
        for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
        {
            if(!It->IsAlive() || It->bIsBoss == CombatHit.Attacker->bIsBoss) continue;
            const float Distance = FVector::Dist(It->GetActorLocation(),Location); if(Distance > Data->ExplosionRadius) continue;
            FHitResult Block; FCollisionQueryParams Q(SCENE_QUERY_STAT(ProjectileExplosion),false,this); Q.AddIgnoredActor(CombatHit.Attacker);
            if(GetWorld()->LineTraceSingleByChannel(Block,Location,It->GetActorLocation(),ECC_Visibility,Q) && Block.GetActor() != *It) continue;
            ApplyPayload(*It,Location,FMath::Lerp(1.f,Data->EdgeDamageFraction,Distance/Data->ExplosionRadius),Id);
            if(IsActorBeingDestroyed() || !CombatHit.Attacker->IsAlive()) return;
        }
    }
    Destroy();
}
