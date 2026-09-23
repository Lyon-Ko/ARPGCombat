#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "AttributeSet.h"
#include "CombatSkillAuthoring.generated.h"

class UCombatSkillDefinition;
class UCombatProjectileDefinition;
class UCombatBuffDefinition;
class UStaticMesh;
class UMaterialInterface;
class UNiagaraSystem;
class USoundBase;

UENUM(BlueprintType)
enum class ECombatSkillEventType : uint8 { HitWindow, Movement, Projectile, AreaWarning, AreaRelease, ApplyBuff, RemoveBuff, CancelWindow, ComboWindow, Effect, Finish };
UENUM(BlueprintType)
enum class ECombatDerivationTrigger : uint8 { Input, Hit, Completed };
UENUM(BlueprintType)
enum class ECombatSkillWindowType : uint8 { Hit, Derivation, Cancel };
UENUM(BlueprintType)
enum class ECombatProjectileMotion : uint8 { Straight, Ballistic, Guided };
UENUM(BlueprintType)
enum class ECombatLostTarget : uint8 { Continue, Destroy, Reacquire };
UENUM(BlueprintType)
enum class ECombatFirePattern : uint8 { Single, Fan, Ring, Scatter };
UENUM(BlueprintType)
enum class ECombatBuffLifetime : uint8 { Instant, Timed, Infinite };
UENUM(BlueprintType)
enum class ECombatBuffTarget : uint8 { Self, Target, Area };
UENUM(BlueprintType)
enum class ECombatInterruptReason : uint8 { Skill, Hit, Parry, PoiseBreak, Control, Death, Reset };
UENUM(BlueprintType)
enum class ECombatSkillRequestResult : uint8 { Activated, Buffered, MissingSkill, Dead, Cooldown, Conditions, Blocked, Uninterruptible, ActivationFailed };

USTRUCT(BlueprintType)
struct COMBAT_API FCombatSkillEvent
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, Category="事件", meta=(IgnoreForMemberInitializationTest)) FGuid Id = FGuid::NewGuid();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="事件") FString Label;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="事件", meta=(ClampMin="0", Units="s")) float Time = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="事件", meta=(ClampMin="0", Units="s")) float Duration = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="事件") ECombatSkillEventType Type = ECombatSkillEventType::HitWindow;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射") TObjectPtr<UCombatProjectileDefinition> Projectile;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射") ECombatFirePattern Pattern = ECombatFirePattern::Single;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射", meta=(ClampMin="1", ClampMax="128")) int32 Count = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射", meta=(ClampMin="1", ClampMax="64")) int32 Bursts = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射", meta=(ClampMin="0.01", Units="s")) float BurstInterval = .1f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射", meta=(ClampMin="0", ClampMax="360")) float SpreadDegrees = 30.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射") int32 Seed = 12345;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射") FName Socket;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射") FVector Offset = FVector(90,0,35);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="发射") bool bAimAtTarget = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff") TObjectPtr<UCombatBuffDefinition> Buff;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff") ECombatBuffTarget BuffTarget = ECombatBuffTarget::Self;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff") bool bSkillScoped = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff", meta=(ClampMin="0")) float Radius = 400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="位移") float Distance = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="位移") FVector Direction = FVector::ForwardVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<UNiagaraSystem> Effect;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<USoundBase> Sound;
};

USTRUCT(BlueprintType)
struct COMBAT_API FCombatSkillDerivation
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, Category="派生", meta=(IgnoreForMemberInitializationTest)) FGuid Id = FGuid::NewGuid();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") FGameplayTag TargetSkill;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") ECombatDerivationTrigger Trigger = ECombatDerivationTrigger::Input;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") FGameplayTag InputTag;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") FGameplayTagQuery Conditions;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") int32 Priority = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生", meta=(ToolTip="原生 Montage 模式：引用 Combat Skill Window 的名字；空值表示不限制窗口。Completed 使用结束触发，不依赖已关闭的窗口。")) FName WindowName;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="数据时序", meta=(ClampMin="0", Units="s", ToolTip="仅无动画/未迁移的数据时间轴使用；原生 Montage 模式忽略。")) float WindowStart = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="数据时序", meta=(ClampMin="0", Units="s")) float WindowEnd = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") bool bRequireHit = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") bool bGroundOnly = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="派生") bool bAirOnly = false;
};

UCLASS(BlueprintType)
class COMBAT_API UCombatProjectileDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="运动") ECombatProjectileMotion Motion = ECombatProjectileMotion::Straight;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="运动", meta=(ClampMin="1", Units="cm/s")) float Speed = 1400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="运动", meta=(ClampMin="1", Units="cm/s")) float MaxSpeed = 2400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="运动") float Acceleration = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="运动") float GravityScale = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="生命周期", meta=(ClampMin="0.01", Units="s")) float Lifetime = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="生命周期", meta=(ClampMin="1", Units="cm")) float MaxDistance = 10000.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="生命周期") bool bDestroyOnInterrupt = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="碰撞") bool bSphereCollision = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="碰撞", meta=(ClampMin="1")) float Radius = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="碰撞") FVector HalfExtent = FVector(24,85,20);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="碰撞", meta=(ClampMin="0", ClampMax="128")) int32 Penetrations = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="碰撞", meta=(ClampMin="0", ClampMax="32")) int32 Bounces = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害", meta=(ClampMin="0")) float Damage = 20.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害", meta=(ClampMin="0")) float PoiseDamage = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害") bool bParryable = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害", meta=(ClampMin="0")) float ExplosionRadius = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害", meta=(ClampMin="0", ClampMax="1")) float EdgeDamageFraction = .25f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害") bool bStackDirectAndExplosion = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="伤害") TObjectPtr<UCombatBuffDefinition> HitBuff;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0")) float GuidanceDelay = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0")) float TurnDegreesPerSecond = 180.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0")) float AcquireRange = 3000.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0", ClampMax="180")) float AcquireHalfAngle = 70.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0")) float PredictionSeconds = .3f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0")) float ProximityRadius = 30.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导") ECombatLostTarget LostTarget = ECombatLostTarget::Continue;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="制导", meta=(ClampMin="0.05")) float ReacquireInterval = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<UMaterialInterface> Material;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<UNiagaraSystem> FlightEffect;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<UNiagaraSystem> ImpactEffect;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="表现") TObjectPtr<USoundBase> ImpactSound;
};

USTRUCT(BlueprintType)
struct COMBAT_API FCombatBuffAttributeModifier
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="属性") FGameplayAttribute Attribute;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="属性") float Additive = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="属性", meta=(ClampMin="0.01")) float Multiplier = 1.f;
};

UCLASS(BlueprintType)
class COMBAT_API UCombatBuffDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff") FGameplayTag BuffTag;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff") ECombatBuffLifetime Lifetime = ECombatBuffLifetime::Timed;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Buff", meta=(ClampMin="0.01", Units="s")) float Duration = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="叠层", meta=(ClampMin="1", ClampMax="100")) int32 MaxStacks = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="叠层") bool bSeparateSources = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="叠层") bool bRefreshDuration = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="叠层") bool bResetPeriod = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果") FGameplayTagContainer GrantedTags;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果", meta=(ClampMin="0.01")) float DamageMultiplier = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果", meta=(ClampMin="0.01")) float MoveSpeedMultiplier = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果") float MaxHealthAdd = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果") float MaxPoiseAdd = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果") bool bSuperArmor = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果") TArray<FCombatBuffAttributeModifier> AttributeModifiers;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="效果", meta=(ToolTip="应用成功时请求 Control 原因打断；免疫该原因的目标拒绝此 Buff")) bool bInterruptOnApply = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="周期", meta=(ClampMin="0.01", Units="s")) float Period = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="周期", meta=(ToolTip="正数治疗，负数伤害；每层每周期生效")) float HealthPerPeriod = 0.f;
};

UCLASS(BlueprintType)
class COMBAT_API UCombatSkillSet : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="技能集合") TArray<TObjectPtr<UCombatSkillDefinition>> Skills;
};
