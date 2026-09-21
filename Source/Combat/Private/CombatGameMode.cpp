#include "CombatGameMode.h"
#include "CombatCharacter.h"
#include "CombatHUD.h"
#include "CombatAIController.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"
#include "Components/AudioComponent.h"
ACombatGameMode::ACombatGameMode()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    MusicComponent = CreateDefaultSubobject<UAudioComponent>(TEXT("BattleMusic"));
    MusicComponent->bAutoActivate = false;
    MusicComponent->bIsUISound = true;
    DefaultPawnClass = ACombatCharacter::StaticClass();
    HUDWidgetClass = UCombatHUDWidget::StaticClass();
}
void ACombatGameMode::BeginPlay()
{
    Super::BeginPlay();
    MusicComponent->OnAudioFinished.AddDynamic(this, &ThisClass::ReplayMusic);
    if(BattleMusic) { MusicComponent->SetSound(BattleMusic); MusicComponent->SetVolumeMultiplier(MusicVolume); MusicComponent->Play(); }
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



void ACombatGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(auto* Player = Cast<ACombatCharacter>(UGameplayStatics::GetPlayerPawn(this, 0))) MusicComponent->SetVolumeMultiplier(MusicVolume * Player->MasterVolume);
}
void ACombatGameMode::ReplayMusic()
{
    if(BattleMusic && !IsActorBeingDestroyed()) MusicComponent->Play();
}
