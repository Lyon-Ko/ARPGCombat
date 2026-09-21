#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "CombatTypes.h"
#include "CombatHUD.generated.h"
class UProgressBar;
class UTextBlock;
class UVerticalBox;
class USlider;
class UCheckBox;
class ACombatCharacter;
UCLASS(Blueprintable)
class COMBAT_API UCombatHUDWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FText PlayerName = FText::FromString(TEXT("霜刃"));
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FText BossName = FText::FromString(TEXT("烬锋·铁卫"));
    UFUNCTION(BlueprintCallable) void SetMasterVolume(float Volume);
    UFUNCTION(BlueprintCallable) void SetSensitivity(float Sensitivity);
    UFUNCTION(BlueprintCallable) void SetCameraShakeEnabled(bool bEnabled);
    UFUNCTION(BlueprintCallable) void ResumeGame();
    UFUNCTION(BlueprintCallable) void RetryGame();
protected:
    virtual void NativeConstruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaSeconds) override;
    virtual void NativeDestruct() override;
private:
    UPROPERTY() TObjectPtr<ACombatCharacter> Player;
    UPROPERTY() TObjectPtr<ACombatCharacter> Boss;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UProgressBar> HealthBar;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UProgressBar> BossHealthBar;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UProgressBar> BossPoiseBar;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> HealthText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> PhaseText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> LockText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> ParryText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> ResultText;
    UPROPERTY(meta=(BindWidgetOptional)) TObjectPtr<UTextBlock> PauseText;
    UPROPERTY() TObjectPtr<UVerticalBox> SettingsPanel;
    float CueRemaining = 0.f;
    FText CenterCue;
    bool bLastShowCursor = false;
    void BindCharacters();
    UFUNCTION() void HandleFeedback(ACombatCharacter* Source, ACombatCharacter* Target, FGameplayTag CueTag, FVector Location, float Intensity);
};

