#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CombatTypes.h"
#include "CombatProjectile.generated.h"
class USphereComponent;
class UProjectileMovementComponent;
class UNiagaraComponent;
UCLASS(Blueprintable)
class COMBAT_API ACombatProjectile : public AActor
{
    GENERATED_BODY()
public:
    ACombatProjectile();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USphereComponent> Collision;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UProjectileMovementComponent> Movement;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraComponent> Visual;
    UFUNCTION(BlueprintCallable) void InitializeProjectile(const FCombatHit& InHit, float Speed, FVector Direction, UNiagaraSystem* Effect);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() FCombatHit CombatHit;
    UFUNCTION() void OnOverlap(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 BodyIndex, bool bFromSweep, const FHitResult& Hit);
    UFUNCTION() void OnBlocked(UPrimitiveComponent* Component, AActor* OtherActor, UPrimitiveComponent* OtherComponent, FVector NormalImpulse, const FHitResult& Hit);
};
