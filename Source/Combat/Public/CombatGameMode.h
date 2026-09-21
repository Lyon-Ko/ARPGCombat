#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "CombatGameMode.generated.h"
class UCombatHUDWidget;
class ACombatCharacter;
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
protected:
    virtual void BeginPlay() override;
};
