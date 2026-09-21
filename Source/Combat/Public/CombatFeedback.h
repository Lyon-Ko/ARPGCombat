#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "CombatTypes.h"
#include "CombatFeedback.generated.h"
class UNiagaraComponent;
class UStaticMeshComponent;
class ACombatCharacter;
UCLASS(ClassGroup=(Combat), meta=(BlueprintSpawnableComponent))
class COMBAT_API UCombatFeedbackComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UCombatFeedbackComponent();
    UFUNCTION(BlueprintCallable) void BeginSkillFeedback(UCombatSkillDefinition* Skill);
    UFUNCTION(BlueprintCallable) void EndSkillFeedback();
    UFUNCTION(BlueprintCallable) void BeginTrail();
    UFUNCTION(BlueprintCallable) void EndTrail();
    UFUNCTION(BlueprintCallable) void ShowWarning(FVector Center);
    UFUNCTION(BlueprintCallable) void ReleaseArea();
    UFUNCTION(BlueprintCallable) void PlayReleaseSound();
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY() TObjectPtr<ACombatCharacter> Character;
    UPROPERTY() TObjectPtr<UCombatSkillDefinition> Definition;
    UPROPERTY() TObjectPtr<UNiagaraComponent> Trail;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WarningMesh;
    bool bReleaseSoundPlayed = false;
    UFUNCTION() void Feedback(ACombatCharacter* Source, ACombatCharacter* Target, FGameplayTag CueTag, FVector Location, float Intensity);
};
