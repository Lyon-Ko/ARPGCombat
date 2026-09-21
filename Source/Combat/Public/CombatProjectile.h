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
private:
    UPROPERTY() FCombatHit CombatHit;
    bool bConsumed = false;
    UFUNCTION() void OnOverlap(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 BodyIndex, bool bFromSweep, const FHitResult& Hit);
    UFUNCTION() void OnBlocked(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit);
};
