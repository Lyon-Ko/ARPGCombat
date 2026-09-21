#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "CombatGameMode.generated.h"
class UCombatHUDWidget;
class ACombatCharacter;
class USoundBase;
class UAudioComponent;
UCLASS(Blueprintable)
class COMBAT_API ACombatGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ACombatGameMode();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TSubclassOf<UCombatHUDWidget> HUDWidgetClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TSubclassOf<ACombatCharacter> BossClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FTransform BossSpawnTransform = FTransform(FRotator(0,180,0), FVector(900,0,100));
    UPROPERTY(BlueprintReadOnly, Category="Combat") TObjectPtr<UCombatHUDWidget> HUDWidget;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Audio") TObjectPtr<USoundBase> BattleMusic;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Audio") float MusicVolume = .35f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Audio") TObjectPtr<UAudioComponent> MusicComponent;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION() void ReplayMusic();
};
