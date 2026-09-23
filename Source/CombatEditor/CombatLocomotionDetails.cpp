#include "CombatLocomotionDetails.h"
#include "CombatLocomotionConfig.h"
#include "CombatLocomotionSettings.h"
#include "CombatCharacter.h"
#include "CombatAnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "DetailLayoutBuilder.h"
#include "DetailCategoryBuilder.h"
#include "DetailWidgetRow.h"
#include "IDetailPropertyRow.h"
#include "PropertyHandle.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
struct FLiveLocomotionView
{
    TWeakObjectPtr<UCombatLocomotionConfig> Asset;
    TWeakObjectPtr<ACombatCharacter> PreviousPlayer;
    double NextRead = 0., PreviousTime = 0.;
    float PreviousYaw = 0.f, PreviousSpeed = 0.f;
    float LastTurnRate = 0.f, LastDeceleration = 0.f;
    bool HasRateSample = false;
    TMap<FName, FText> Values;
    FText Status, Missing;

    void Refresh()
    {
        const double Now = FPlatformTime::Seconds();
        if(Now < NextRead) return;
        NextRead = Now + .1;
        Values.Reset();
        Status = FText::FromString(TEXT("未运行：启动 PIE 后显示实际状态；右列只读，每 0.1 秒刷新。"));
        Missing = FText::FromString(TEXT("— 未运行"));
        UCombatLocomotionSubsystem* Selected = nullptr;
        int32 Matches = 0;
        if(GEngine && Asset.IsValid()) for(const auto& Context : GEngine->GetWorldContexts())
        {
            UWorld* World = Context.World();
            if(!World || (World->WorldType != EWorldType::PIE && World->WorldType != EWorldType::Game)) continue;
            auto* Config = World->GetSubsystem<UCombatLocomotionSubsystem>();
            if(Config && Config->GetConfiguration() == Asset.Get()) { Selected = Config; ++Matches; }
        }
        if(Matches != 1)
        {
            PreviousPlayer.Reset();
            HasRateSample = false;
            if(Matches > 1)
            {
                Missing = FText::FromString(TEXT("— 多个运行世界"));
                Status = FText::FromString(TEXT("多个运行世界使用此资产：请仅保留一个 PIE 世界，避免混读玩家数据。"));
            }
            return;
        }
        UWorld* World = Selected->GetWorld();
        auto* PC = World->GetFirstPlayerController();
        auto* Player = PC ? Cast<ACombatCharacter>(PC->GetPawn()) : nullptr;
        if(!Player)
        {
            Missing = FText::FromString(TEXT("— 无玩家"));
            Status = FText::FromString(TEXT("已运行，等待玩家角色生成。"));
            PreviousPlayer.Reset();
            return;
        }
        auto* Move = Player->GetCharacterMovement();
        auto* Anim = Cast<UCombatAnimInstance>(Player->GetMesh()->GetAnimInstance());
        const bool Pivot = Anim && Anim->IsPivoting();
        const FVector Input = Player->GetLocomotionDebugInput();
        const float Speed = Player->GetVelocity().Size2D();
        const FVector LocalVelocity = Player->GetActorTransform().InverseTransformVectorNoScale(Player->GetVelocity());
        const auto Number = [&](FName Name, const TCHAR* Label, float Value, const TCHAR* Unit)
        { Values.Add(Name, FText::FromString(FString::Printf(TEXT("%s %.2f %s"), Label, FMath::Abs(Value) < .005f ? 0.f : Value, Unit))); };
        const auto Text = [&](FName Name, const TCHAR* Value) { Values.Add(Name, FText::FromString(Value)); };
        const auto Angle = [](const FVector& A, const FVector& B)
        { return FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(A.GetSafeNormal2D(), B.GetSafeNormal2D()), -1., 1.))); };
        const TCHAR* Phase = Pivot ? (Anim->IsPivotAccelerating() ? TEXT("反向加速") : TEXT("折返刹车")) : TEXT("普通移动");
        Status = FText::FromString(FString::Printf(TEXT("%s | %s | 配置 r%d | %s%s%s"), *World->GetName(), *Player->GetName(),
            Selected->GetRevision(), Phase, UGameplayStatics::IsGamePaused(World) ? TEXT(" | 已暂停，速率保留最后采样") : TEXT(""),
            Selected->GetLastError().IsEmpty() ? TEXT("") : TEXT(" | 配置无效，仍使用上次有效配置")));
        Missing = FText::FromString(TEXT("— 无对应瞬时量"));
        Number(TEXT("ForwardSpeed"), TEXT("前向速度"), FMath::Max(0., LocalVelocity.X), TEXT("cm/s"));
        Number(TEXT("BackwardSpeed"), TEXT("后向速度"), FMath::Max(0., -LocalVelocity.X), TEXT("cm/s"));
        Number(TEXT("LeftSpeed"), TEXT("左向速度"), FMath::Max(0., -LocalVelocity.Y), TEXT("cm/s"));
        Number(TEXT("RightSpeed"), TEXT("右向速度"), FMath::Max(0., LocalVelocity.Y), TEXT("cm/s"));
        Number(TEXT("Acceleration"), TEXT("输入加速度"), Move->GetCurrentAcceleration().Size2D(), TEXT("cm/s²"));
        Number(TEXT("InputDeadZone"), TEXT("输入方向长度"), Input.Size2D(), TEXT(""));
        const double GameTime = World->GetTimeSeconds();
        const double DT = GameTime - PreviousTime;
        if(PreviousPlayer.Get() != Player || DT < 0.) HasRateSample = false;
        if(PreviousPlayer.Get() == Player && DT > SMALL_NUMBER)
        {
            LastTurnRate = FMath::Abs(FMath::FindDeltaAngleDegrees(PreviousYaw, Player->GetActorRotation().Yaw)) / DT;
            LastDeceleration = FMath::Max(0.f, (PreviousSpeed - Speed) / static_cast<float>(DT));
            HasRateSample = true;
        }
        if(HasRateSample)
        {
            Number(TEXT("TurnRate"), TEXT("实测角速度"), LastTurnRate, TEXT("°/s"));
            if(Pivot) Number(TEXT("PivotTurnRate"), Anim->IsAuthoredFreePivot() ? TEXT("曲线驱动") : TEXT("实测角速度"), LastTurnRate, TEXT("°/s"));
            if(Pivot && !Anim->IsPivotAccelerating())
            {
                Number(TEXT("PivotBrakingDeceleration"), TEXT("实测总减速"), LastDeceleration, TEXT("cm/s²"));
                Number(TEXT("PivotBrakingFriction"), TEXT("实测总减速"), LastDeceleration, TEXT("cm/s²"));
            }
            else if(!Pivot && Move->IsMovingOnGround() && Input.IsNearlyZero())
            {
                Number(TEXT("BrakingDeceleration"), TEXT("实测总减速"), LastDeceleration, TEXT("cm/s²"));
                Number(TEXT("BrakingFriction"), TEXT("实测总减速"), LastDeceleration, TEXT("cm/s²"));
            }
        }
        PreviousPlayer = Player; PreviousTime = GameTime; PreviousYaw = Player->GetActorRotation().Yaw; PreviousSpeed = Speed;
        for(const FName Name : {TEXT("PivotMinSpeed"), TEXT("PivotStopSpeed"), TEXT("AnimationJogSpeed"), TEXT("AnimationFastSpeed"), TEXT("AnimationIdleDirectionSpeed")})
            Number(Name, TEXT("水平速度"), Speed, TEXT("cm/s"));
        Text(TEXT("PivotEnabled"), Pivot ? TEXT("正在折返") : TEXT("未折返"));
        if(!Input.IsNearlyZero() && Speed > KINDA_SMALL_NUMBER)
            Number(TEXT("PivotMinAngle"), TEXT("速度/输入夹角"), Angle(Player->GetVelocity(), Input), TEXT("°"));
        else Text(TEXT("PivotMinAngle"), TEXT("— 无输入或速度为零"));
        if(Anim)
        {
            Number(TEXT("PivotCooldown"), TEXT("剩余冷却"), Anim->GetPivotCooldownRemaining(), TEXT("s"));
            Number(TEXT("AnimationSpeedInterp"), TEXT("BS Speed"), Anim->Speed, TEXT(""));
            Number(TEXT("AnimationDirectionInterp"), TEXT("BS Direction"), Anim->Direction, TEXT("°"));
            if(Pivot)
            {
                for(const FName Name : {TEXT("PivotReverseDelay"), TEXT("PivotTurnDelay")})
                    Number(Name, TEXT("折返已过"), Anim->PivotElapsed, TEXT("s"));
                for(const FName Name : {TEXT("PivotReverseMinProgress"), TEXT("PivotExitMinProgress")})
                    Number(Name, TEXT("动画进度"), Anim->PivotProgress, TEXT(""));
                Number(TEXT("PivotReverseMaxFacingAngle"), TEXT("朝向误差"), FMath::Abs(FMath::FindDeltaAngleDegrees(Player->GetActorRotation().Yaw, Anim->GetPivotDirection().Rotation().Yaw)), TEXT("°"));
                Number(TEXT("PivotExitMinSpeed"), TEXT("目标方向速度"), FVector::DotProduct(Player->GetVelocity(), Anim->GetPivotDirection()), TEXT("cm/s"));
                Number(TEXT("PivotReverseAcceleration"), TEXT("输入加速度"), Move->GetCurrentAcceleration().Size2D(), TEXT("cm/s²"));
                if(!Input.IsNearlyZero()) Number(TEXT("PivotCancelAngle"), TEXT("输入偏离"), Angle(Input, Anim->GetPivotDirection()), TEXT("°"));
                Text(TEXT("PivotCancelOnRelease"), Input.IsNearlyZero() ? TEXT("已松开方向键") : TEXT("仍有方向输入"));
                Text(TEXT("PivotEarlyExit"), Anim->IsPivotAccelerating() ? TEXT("已进入反向加速") : TEXT("仍在刹车"));
                if(auto* Instance = Anim->GetPivotDebugInstance())
                {
                    Number(TEXT("PivotPlayRate"), TEXT("实际播放倍率"), Instance->GetPlayRate(), TEXT("×"));
                    for(const FName Name : {TEXT("PivotBlendIn"), TEXT("PivotBlendOut"), TEXT("PivotInterruptBlendOut")})
                        Number(Name, TEXT("蒙太奇权重"), Instance->GetWeight(), TEXT(""));
                    Number(TEXT("PivotBlendOutTriggerTime"), TEXT("片段剩余"), FMath::Max(0.f, Instance->Montage->GetPlayLength() - Instance->GetPosition()), TEXT("s"));
                }
            }
            else for(const FName Name : {TEXT("PivotReverseDelay"), TEXT("PivotTurnDelay"), TEXT("PivotReverseMinProgress"), TEXT("PivotExitMinProgress"), TEXT("PivotReverseMaxFacingAngle"), TEXT("PivotExitMinSpeed"), TEXT("PivotReverseAcceleration"), TEXT("PivotCancelAngle"), TEXT("PivotPlayRate"), TEXT("PivotBlendIn"), TEXT("PivotBlendOut"), TEXT("PivotInterruptBlendOut"), TEXT("PivotBlendOutTriggerTime")})
                Text(Name, TEXT("— 未折返"));
        }
        Number(TEXT("JumpVelocity"), TEXT("垂直速度"), Move->Velocity.Z, TEXT("cm/s"));
        Number(TEXT("JumpCount"), TEXT("已跳次数"), Player->JumpCurrentCount, TEXT(""));
        Number(TEXT("GravityScale"), TEXT("实际重力"), Move->GetGravityZ(), TEXT("cm/s²"));
        if(Player->Camera && Player->CameraBoom)
        {
            Number(TEXT("CameraFOV"), TEXT("当前 FOV"), Player->Camera->FieldOfView, TEXT("°"));
            const float Distance = FVector::Distance(Player->Camera->GetComponentLocation(), Player->GetActorLocation());
            for(const FName Name : {TEXT("CameraDistance"), TEXT("CameraLockedMinDistance"), TEXT("CameraLockedMaxDistance")})
                Number(Name, TEXT("当前臂长"), Player->CameraBoom->TargetArmLength, TEXT("cm"));
            for(const FName Name : {TEXT("CameraHideDistance"), TEXT("CameraRevealDistance")}) Number(Name, TEXT("镜头距角色"), Distance, TEXT("cm"));
            for(const FName Name : {TEXT("CameraPitchMin"), TEXT("CameraPitchMax")}) Number(Name, TEXT("镜头俯仰"), PC->GetControlRotation().Pitch, TEXT("°"));
        }
    }
    FText Read(FName Name) { Refresh(); if(const FText* Found = Values.Find(Name)) return *Found; return Missing; }
};
}

void FCombatLocomotionDetails::CustomizeDetails(IDetailLayoutBuilder& Builder)
{
    TArray<TWeakObjectPtr<UObject>> Objects;
    Builder.GetObjectsBeingCustomized(Objects);
    if(Objects.Num() != 1) return;
    auto View = MakeShared<FLiveLocomotionView>();
    View->Asset = Cast<UCombatLocomotionConfig>(Objects[0].Get());
    auto& Debug = Builder.EditCategory(TEXT("00 Runtime 运行时调试"));
    Debug.AddCustomRow(FText::FromString(TEXT("运行时调试"))).WholeRowContent()
        [SNew(STextBlock).AutoWrapText(true).Text_Lambda([View] { View->Refresh(); return View->Status; })];
    TSet<FName> Headers;
    for(TFieldIterator<FProperty> It(UCombatLocomotionConfig::StaticClass(), EFieldIteratorFlags::ExcludeSuper); It; ++It)
    {
        auto Property = Builder.GetProperty(It->GetFName());
        auto* Row = Builder.EditDefaultProperty(Property);
        if(!Row) continue;
        const FName Name = It->GetFName();
        const FName Category(*It->GetMetaData(TEXT("Category")));
        if(!Headers.Contains(Category))
        {
            Headers.Add(Category);
            Builder.EditCategory(Category).AddCustomRow(FText::FromString(TEXT("配置值 运行时调试值")))
                .ValueContent().MinDesiredWidth(420)
                [SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(TEXT("配置值")))]
                    + SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(220)[SNew(STextBlock).Text(FText::FromString(TEXT("运行时调试值")))]]];
        }
        TSharedPtr<SWidget> NameWidget, ValueWidget;
        Row->GetDefaultWidgets(NameWidget, ValueWidget);
        Row->CustomWidget().NameContent()[NameWidget.ToSharedRef()]
            .ValueContent().MinDesiredWidth(420).MaxDesiredWidth(800)
            [SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[ValueWidget.ToSharedRef()]
                + SHorizontalBox::Slot().AutoWidth().Padding(12, 0, 0, 0)
                [SNew(SBox).WidthOverride(220).VAlign(VAlign_Center)
                    [SNew(STextBlock).ColorAndOpacity(FLinearColor(.2f,.75f,.9f))
                        .ToolTipText(FText::FromString(TEXT("当前玩家实际测量值，不是配置副本。角速度和总减速度按约 0.1 秒采样；总减速包含摩擦、碰撞等影响。— 表示未运行、阶段不适用或没有对应瞬时量。")))
                        .Text_Lambda([View, Name] { return View->Read(Name); })]]];
    }
}
