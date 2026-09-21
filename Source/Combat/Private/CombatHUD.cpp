#include "CombatHUD.h"
#include "CombatCharacter.h"
#include "CombatTags.h"
#include "AbilitySystemComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/Border.h"
#include "Components/Slider.h"
#include "Components/CheckBox.h"
#include "Components/Button.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"

void UCombatHUDWidget::NativeConstruct()
{
    Super::NativeConstruct();
    if(!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this);
    auto* Canvas = Cast<UCanvasPanel>(WidgetTree->RootWidget);
    if(!Canvas && !WidgetTree->RootWidget) { Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(); WidgetTree->RootWidget = Canvas; }
    auto MakeText = [&](FName Name, FVector2D Position, FVector2D Size, const FString& Text) -> UTextBlock*
    {
        if(auto* Existing = Cast<UTextBlock>(GetWidgetFromName(Name))) return Existing;
        if(!Canvas) return nullptr;
        auto* Widget = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
        Widget->SetText(FText::FromString(Text)); Widget->SetColorAndOpacity(FSlateColor(FLinearColor(.93f,.93f,.90f)));
        FSlateFontInfo Font = Widget->GetFont(); Font.Size = 19; Widget->SetFont(Font);
        auto* LayoutSlot = Canvas->AddChildToCanvas(Widget); LayoutSlot->SetPosition(Position); LayoutSlot->SetSize(Size); return Widget;
    };
    auto MakeBar = [&](FName Name, FVector2D Position, FVector2D Size, FLinearColor Color) -> UProgressBar*
    {
        if(auto* Existing = Cast<UProgressBar>(GetWidgetFromName(Name))) return Existing;
        if(!Canvas) return nullptr;
        auto* Widget = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), Name); Widget->SetFillColorAndOpacity(Color);
        auto* LayoutSlot = Canvas->AddChildToCanvas(Widget); LayoutSlot->SetPosition(Position); LayoutSlot->SetSize(Size); return Widget;
    };
    HealthBar = MakeBar(TEXT("HealthBar"), FVector2D(45,920), FVector2D(350,22), FLinearColor(.15f,.64f,.7f));
    BossHealthBar = MakeBar(TEXT("BossHealthBar"), FVector2D(432,60), FVector2D(1056,24), FLinearColor(.65f,.16f,.10f));
    BossPoiseBar = MakeBar(TEXT("BossPoiseBar"), FVector2D(432,91), FVector2D(1056,7), FLinearColor(.85f,.63f,.24f));
    HealthText = MakeText(TEXT("HealthText"), FVector2D(45,885), FVector2D(460,30), TEXT("霜刃"));
    PhaseText = MakeText(TEXT("PhaseText"), FVector2D(700,22), FVector2D(700,30), TEXT("烬锋·铁卫"));
    LockText = MakeText(TEXT("LockText"), FVector2D(1350,930), FVector2D(550,40), TEXT("Q · 自由镜头"));
    ParryText = MakeText(TEXT("ParryText"), FVector2D(45,955), FVector2D(550,50), TEXT(""));
    ResultText = MakeText(TEXT("ResultText"), FVector2D(690,430), FVector2D(700,100), TEXT(""));
    PauseText = MakeText(TEXT("PauseText"), FVector2D(780,255), FVector2D(500,55), TEXT(""));
    if(Canvas)
    {
        SettingsPanel = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("CombatSettingsPanel"));
        SettingsBackdrop = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("CombatSettingsBackdrop"));
        SettingsBackdrop->SetBrushColor(FLinearColor(.015f,.022f,.032f,.94f));
        SettingsBackdrop->SetPadding(FMargin(30.f,24.f));
        SettingsBackdrop->SetContent(SettingsPanel);
        auto* LayoutSlot = Canvas->AddChildToCanvas(SettingsBackdrop); LayoutSlot->SetAnchors(FAnchors(.5f,.5f)); LayoutSlot->SetAlignment(FVector2D(.5f,.5f)); LayoutSlot->SetPosition(FVector2D(0,0)); LayoutSlot->SetSize(FVector2D(460,390)); LayoutSlot->SetZOrder(20);
        auto AddRow = [&](UWidget* Widget, float BottomPadding) { auto* Row = SettingsPanel->AddChildToVerticalBox(Widget); Row->SetPadding(FMargin(0,0,0,BottomPadding)); };
        auto StyleText = [](UTextBlock* Label, int32 Size) { FSlateFontInfo Font = Label->GetFont(); Font.Size = Size; Label->SetFont(Font); Label->SetColorAndOpacity(FSlateColor(FLinearColor(.96f,.96f,.94f))); };
        if(PauseText) { PauseText->RemoveFromParent(); StyleText(PauseText,22); PauseText->SetJustification(ETextJustify::Center); AddRow(PauseText,20.f); }
        auto AddLabel = [&](const TCHAR* Text) { auto* Label = WidgetTree->ConstructWidget<UTextBlock>(); Label->SetText(FText::FromString(Text)); StyleText(Label,18); AddRow(Label,8.f); };
        AddLabel(TEXT("主音量"));
        auto* Volume = WidgetTree->ConstructWidget<USlider>(); Volume->SetValue(1.f); Volume->OnValueChanged.AddDynamic(this, &ThisClass::SetMasterVolume); AddRow(Volume,18.f);
        AddLabel(TEXT("镜头灵敏度"));
        auto* Sensitivity = WidgetTree->ConstructWidget<USlider>(); Sensitivity->SetMinValue(.2f); Sensitivity->SetMaxValue(3.f); Sensitivity->SetValue(1.f); Sensitivity->OnValueChanged.AddDynamic(this, &ThisClass::SetSensitivity); AddRow(Sensitivity,20.f);
        auto* Shake = WidgetTree->ConstructWidget<UCheckBox>(); Shake->SetIsChecked(true); Shake->OnCheckStateChanged.AddDynamic(this, &ThisClass::SetCameraShakeEnabled);
        auto* ShakeLabel = WidgetTree->ConstructWidget<UTextBlock>(); ShakeLabel->SetText(FText::FromString(TEXT("  镜头震动"))); StyleText(ShakeLabel,18); Shake->AddChild(ShakeLabel); AddRow(Shake,24.f);
        auto* Resume = WidgetTree->ConstructWidget<UButton>(); auto* ResumeLabel = WidgetTree->ConstructWidget<UTextBlock>(); ResumeLabel->SetText(FText::FromString(TEXT("继续战斗 · P"))); StyleText(ResumeLabel,20); ResumeLabel->SetColorAndOpacity(FSlateColor(FLinearColor(.03f,.04f,.05f))); Resume->AddChild(ResumeLabel); Resume->OnClicked.AddDynamic(this, &ThisClass::ResumeGame); AddRow(Resume,0.f);
        SettingsBackdrop->SetVisibility(ESlateVisibility::Collapsed);
    }
    BindCharacters();
}
void UCombatHUDWidget::BindCharacters()
{
    Player = Cast<ACombatCharacter>(GetOwningPlayerPawn()); Boss = nullptr;
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
    {
        It->OnCombatFeedback.RemoveDynamic(this, &ThisClass::HandleFeedback);
        It->OnCombatFeedback.AddDynamic(this, &ThisClass::HandleFeedback);
        if(It->bIsBoss) Boss = *It;
    }
    if(Player && Boss) { Player->SetCombatTarget(Boss); Boss->SetCombatTarget(Player); }
}
void UCombatHUDWidget::NativeTick(const FGeometry& Geometry, float DeltaSeconds)
{
    Super::NativeTick(Geometry, DeltaSeconds);
    if(!Player || !Boss) BindCharacters();
    if(!Player) return;
    if(LockText) LockText->SetText(FText::FromString(Player->IsTargetLocked() ? TEXT("Q · 已锁定目标") : TEXT("Q · 自由镜头")));
    if(HealthBar) HealthBar->SetPercent(Player->GetHealth() / FMath::Max(1.f, Player->GetMaxHealth()));
    if(HealthText) HealthText->SetText(FText::FromString(FString::Printf(TEXT("%s  %.0f / %.0f"), *PlayerName.ToString(), Player->GetHealth(), Player->GetMaxHealth())));
    if(Boss)
    {
        if(BossHealthBar) BossHealthBar->SetPercent(Boss->GetHealth() / FMath::Max(1.f, Boss->GetMaxHealth()));
        if(BossPoiseBar) BossPoiseBar->SetPercent(Boss->GetPoise() / FMath::Max(1.f, Boss->GetMaxPoise()));
        if(PhaseText) PhaseText->SetText(FText::FromString(Boss->bPhaseTwo ? TEXT("破阵") : TEXT("第一阶段")));
    }
    const bool bRiposte = Player->GetAbilitySystemComponent()->HasMatchingGameplayTag(CombatTags::State_RiposteReady);
    if(ParryText)
    {
        const bool bDashReady = Player->GetSkillCooldownRemaining(FGameplayTag::RequestGameplayTag(TEXT("Combat.Skill.Dash"))) <= 0;
        const bool bParryReady = Player->GetSkillCooldownRemaining(FGameplayTag::RequestGameplayTag(TEXT("Combat.Skill.Parry"))) <= 0;
        ParryText->SetText(FText::FromString(bRiposte ? TEXT("反击就绪 · 左键") : FString::Printf(TEXT("短冲 %s   精准格挡 %s"), bDashReady ? TEXT("就绪") : TEXT("恢复中"), bParryReady ? TEXT("就绪") : TEXT("恢复中"))));
    }
    CueRemaining = FMath::Max(0.f, CueRemaining - DeltaSeconds);
    const bool bResult = !Player->IsAlive() || (Boss && !Boss->IsAlive());
    if(ResultText) ResultText->SetText(bResult ? FText::FromString(Player->IsAlive() ? TEXT("战斗胜利\nR 再战") : TEXT("战斗失败\nR 再战")) : (bRiposte ? FText::FromString(TEXT("反击！")) : (CueRemaining > 0 ? CenterCue : FText::GetEmpty())));
    const bool bPaused = UGameplayStatics::IsGamePaused(this);
    if(PauseText) PauseText->SetText(bPaused ? FText::FromString(TEXT("已暂停")) : FText::GetEmpty());
    if(SettingsBackdrop) SettingsBackdrop->SetVisibility(bPaused ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    if(auto* PC = GetOwningPlayer(); PC && bLastShowCursor != bPaused)
    {
        bLastShowCursor = bPaused; PC->bShowMouseCursor = bPaused;
        if(bPaused) PC->SetInputMode(FInputModeGameAndUI()); else PC->SetInputMode(FInputModeGameOnly());
    }
}
void UCombatHUDWidget::NativeDestruct()
{
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) It->OnCombatFeedback.RemoveDynamic(this, &ThisClass::HandleFeedback);
    Super::NativeDestruct();
}
void UCombatHUDWidget::HandleFeedback(ACombatCharacter* Source, ACombatCharacter* Target, FGameplayTag CueTag, FVector Location, float Intensity)
{
    if(CueTag == CombatTags::Cue_PoiseBreak) { CenterCue = FText::FromString(TEXT("破韧")); CueRemaining = .75f; }
    else if(CueTag == CombatTags::Cue_Parry) { CenterCue = FText::FromString(TEXT("精准格挡")); CueRemaining = .5f; }
}
void UCombatHUDWidget::SetMasterVolume(float Volume) { for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) It->MasterVolume = FMath::Clamp(Volume, 0.f, 1.f); }
void UCombatHUDWidget::SetSensitivity(float Sensitivity) { if(Player) Player->CameraSensitivity = FMath::Clamp(Sensitivity, .2f, 3.f); }
void UCombatHUDWidget::SetCameraShakeEnabled(bool bEnabled) { for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) It->bCameraShakeEnabled = bEnabled; }
void UCombatHUDWidget::ResumeGame() { UGameplayStatics::SetGamePaused(this, false); }
void UCombatHUDWidget::RetryGame() { if(Player) Player->RetryEncounter(); }

