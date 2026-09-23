#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CombatTypes.h"
#include "CombatProjectile.generated.h"
class UBoxComponent;
class UStaticMeshComponent;
class UProjectileMovementComponent;
class UNiagaraComponent;
UCLASS(Blueprintable)
class COMBAT_API ACombatProjectile : public AActor
{
    GENERATED_BODY()
public:
    ACombatProjectile();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Collision;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> WaveMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UProjectileMovementComponent> Movement;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraComponent> Visual;
    UFUNCTION(BlueprintCallable) void InitializeProjectile(const FCombatHit& InHit, float Speed, FVector Direction, UNiagaraSystem* Effect, UStaticMesh* Mesh, UMaterialInterface* Material, FVector CollisionHalfExtent);
    virtual void Tick(float DeltaSeconds) override;
    void InitializeDefinition(UCombatProjectileDefinition* Definition, ACombatCharacter* Source, ACombatCharacter* Target, FVector Direction, uint64 Serial);
    void ActivateDefinition();
    void CancelForSkill(uint64 Serial);
    UFUNCTION(BlueprintPure, Category="Combat|Projectile") UCombatProjectileDefinition* GetDefinition() const { return Data; }
private:
    UPROPERTY() TObjectPtr<UCombatProjectileDefinition> Data;
    UPROPERTY() TWeakObjectPtr<ACombatCharacter> HomingTarget;
    uint64 OwnerSerial = 0;
    FVector DataVelocity = FVector::ZeroVector;
    float Age = 0.f;
    float Travel = 0.f;
    float NextAcquire = 0.f;
    int32 Pierced = 0;
    int32 Bounced = 0;
    bool bDataActive = false;
    TSet<TWeakObjectPtr<ACombatCharacter>> HitTargets;
    void AdvanceDefinition(float DeltaSeconds);
    void AcquireTarget();
    void Impact(ACombatCharacter* Target, FVector Location);
    void ApplyPayload(ACombatCharacter* Target, FVector Location, float Scale, int32 Instance);
    UPROPERTY() FCombatHit CombatHit;
    bool bConsumed = false;
    UFUNCTION() void OnOverlap(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 BodyIndex, bool bFromSweep, const FHitResult& Hit);
    UFUNCTION() void OnBlocked(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit);
};
