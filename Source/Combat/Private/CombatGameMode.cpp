#include "CombatGameMode.h"
#include "CombatCharacter.h"
#include "CombatHUD.h"
#include "CombatAIController.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"
ACombatGameMode::ACombatGameMode()
{
    DefaultPawnClass = ACombatCharacter::StaticClass();
    HUDWidgetClass = UCombatHUDWidget::StaticClass();
}
void ACombatGameMode::BeginPlay()
{
    Super::BeginPlay();
    bool bHasBoss = false;
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) if(It->bIsBoss) bHasBoss = true;
    if(!bHasBoss && BossClass)
    {
        if(auto* Boss = GetWorld()->SpawnActorDeferred<ACombatCharacter>(BossClass, BossSpawnTransform))
        {
            Boss->bIsBoss = true;
            Boss->AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
            UGameplayStatics::FinishSpawningActor(Boss, BossSpawnTransform);
        }
    }
    if(auto* PC = UGameplayStatics::GetPlayerController(this, 0); PC && HUDWidgetClass)
    {
        HUDWidget = CreateWidget<UCombatHUDWidget>(PC, HUDWidgetClass); if(HUDWidget) HUDWidget->AddToViewport();
        PC->SetInputMode(FInputModeGameOnly()); PC->bShowMouseCursor = false;
    }
}


