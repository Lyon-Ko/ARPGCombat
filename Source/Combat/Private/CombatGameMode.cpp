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
void ACombatGameMode::StartPlay()
{
    // A placed boss may be restored by editor undo or Keep Simulation Changes.
    // Clear the play-world copy before BeginPlay starts AI and binds the HUD.
    // Every new play session must wait for R, even if the map contains a boss.
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
    {
        if(!It->bIsBoss) continue;
        if(auto* Controller = It->GetController()) Controller->Destroy();
        It->Destroy();
    }
    Super::StartPlay();
}

void ACombatGameMode::BeginPlay()
{
    Super::BeginPlay();
    MusicComponent->OnAudioFinished.AddDynamic(this, &ThisClass::ReplayMusic);
    if(BattleMusic) { MusicComponent->SetSound(BattleMusic); MusicComponent->SetVolumeMultiplier(MusicVolume); MusicComponent->Play(); }
    if(auto* PC = UGameplayStatics::GetPlayerController(this, 0); PC && HUDWidgetClass)
    {
        HUDWidget = CreateWidget<UCombatHUDWidget>(PC, HUDWidgetClass); if(HUDWidget) HUDWidget->AddToViewport();
        PC->SetInputMode(FInputModeGameOnly()); PC->bShowMouseCursor = false;
    }
}

void ACombatGameMode::SpawnBoss()
{
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) if(It->bIsBoss) return;
    if(BossClass)
    {
        if(auto* Boss = GetWorld()->SpawnActorDeferred<ACombatCharacter>(BossClass, BossSpawnTransform))
        {
            Boss->bIsBoss = true;
            Boss->AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
            UGameplayStatics::FinishSpawningActor(Boss, BossSpawnTransform);
            if(auto* Player = Cast<ACombatCharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
            {
                Player->SetCombatTarget(Boss);
                Boss->SetCombatTarget(Player);
                Boss->MasterVolume = Player->MasterVolume;
                Boss->bCameraShakeEnabled = Player->bCameraShakeEnabled;
            }
        }
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
