#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "CombatLocomotionValues.h"
#include "CombatLocomotionSettings.generated.h"
class UCombatLocomotionConfig;

/** One validated Data Asset snapshot per world; Details edits apply during PIE. */
UCLASS()
class COMBAT_API UCombatLocomotionSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;
    UFUNCTION(BlueprintCallable, Category="Locomotion") bool ReloadConfiguration();
    UFUNCTION(BlueprintCallable, Category="Locomotion") void SetConfiguration(UCombatLocomotionConfig* Asset);
    UFUNCTION(BlueprintPure, Category="Locomotion") UCombatLocomotionConfig* GetConfiguration() const { return Configuration; }
    UFUNCTION(BlueprintPure, Category="Locomotion") int32 GetRevision() const { return Revision; }
    UFUNCTION(BlueprintPure, Category="Locomotion") FString GetLastError() const { return LastError; }
    UFUNCTION(BlueprintPure, Category="Locomotion") FString GetConfigurationPath() const;
    UFUNCTION(BlueprintPure, Category="Locomotion") float GetParameter(FName Section, FName Key) const;
    UFUNCTION(BlueprintPure, Category="Locomotion", meta=(WorldContext="Context")) static UCombatLocomotionSubsystem* GetForWorld(const UObject* Context);
    const FCombatLocomotionSettings& GetSettings() const { return Settings; }
    static const FCombatLocomotionSettings& For(const UObject* Context);
private:
    FCombatLocomotionSettings Settings;
    UPROPERTY(Transient) TObjectPtr<UCombatLocomotionConfig> Configuration;
    FCombatLocomotionSettings LastAttempt;
    bool bHasLastAttempt = false;
    FString LastError;
    int32 Revision = 0;
    double NextPollTime = 0;
    bool Load(bool bForce);
    bool Reject(const FString& Error);
};
