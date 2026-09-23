#pragma once
#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "CombatSkillAuthoring.h"
#include "CombatTypes.generated.h"
class UGameplayAbility;
class UAnimMontage;
class ACombatCharacter;
class UNiagaraSystem;
class USoundBase;
class UStaticMesh;
class UMaterialInterface;

UENUM(BlueprintType)
enum class ECombatHitResult : uint8 { Miss, Damaged, Parried, Evaded, Killed };

USTRUCT(BlueprintType)
struct COMBAT_API FCombatHit
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<ACombatCharacter> Attacker = nullptr;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Damage = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float PoiseDamage = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Location = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Direction = FVector::ForwardVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bParryable = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 AttackInstance = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int64 ExecutionSerial = 0;
};

UCLASS(BlueprintType)
class COMBAT_API UCombatSkillDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(VisibleAnywhere, Category="编辑器") int32 SchemaVersion = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="编辑器") bool bDataDriven = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="编辑器", meta=(ToolTip="动画技能由原生 Montage 的 Combat Skill Action / Window 通知驱动；转换后旧事件数组不执行。")) bool bUseMontageNotifies = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="时间轴", meta=(EditCondition="!bUseMontageNotifies || Montage == nullptr", EditConditionHides)) TArray<FCombatSkillEvent> Events;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="派生") TArray<FCombatSkillDerivation> Derivations;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="互斥") FGameplayTagContainer ExclusiveTags;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="互斥") FGameplayTagContainer BlockedByTags;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="打断") int32 InterruptPriority = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="打断") int32 InterruptResistance = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="打断") bool bForceInterrupt = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="打断") TArray<ECombatInterruptReason> AllowedInterrupts = { ECombatInterruptReason::Skill, ECombatInterruptReason::Hit, ECombatInterruptReason::Parry, ECombatInterruptReason::PoiseBreak, ECombatInterruptReason::Control };
#if WITH_EDITORONLY_DATA
    UPROPERTY() FVector2D GraphPosition = FVector2D::ZeroVector;
#endif
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FGameplayTag SkillTag;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FGameplayTag InputTag;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FGameplayTag NextSkillTag;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FGameplayTagQuery ActivationQuery;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 Priority = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSubclassOf<UGameplayAbility> AbilityClass;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UAnimMontage> Montage;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Animation", meta=(ClampMin="0")) float LocomotionBlendOut = .14f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Animation", meta=(ClampMin="0")) float InterruptBlendOut = .08f;
    // Movement may cancel recovery only after the existing Cancelable notify.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Animation") bool bAllowMovementCancel = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Damage = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float PoiseDamage = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Cooldown = .1f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Duration = .7f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MovementDistance = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MovementDuration = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float TraceRadius = 24.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float TraceReach = 170.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float AreaRadius = 460.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float AreaHeight = 700.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float AreaDelay = .18f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ProjectileSpeed = 1400.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> ProjectileMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> ProjectileMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FVector ProjectileCollisionHalfExtent = FVector(24.f,85.f,20.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bAirOnly = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bGroundOnly = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bFaceTarget = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bPlayCastSoundAtActivation = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bParryable = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bCanInterrupt = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> AreaMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> AreaMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FVector MovementDirectionLocal = FVector::ForwardVector;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float LaunchVelocityZ = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraSystem> HitEffect;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraSystem> TrailEffect;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraSystem> CastEffect;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraSystem> AreaReleaseEffect;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> CastSound;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> ParrySound;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float SelectionWeight = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MinAIRange = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MaxAIRange = 650.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 AirAttackIndex = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float AirHangTime = .10f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FLinearColor CueColor = FLinearColor(.15f,.65f,1.f);
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_FiveParams(FCombatFeedbackDelegate, ACombatCharacter*, Source, ACombatCharacter*, Target, FGameplayTag, CueTag, FVector, Location, float, Intensity);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FCombatDeathDelegate, ACombatCharacter*, Character);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FCombatSkillDelegate, ACombatCharacter*, Character, FGameplayTag, SkillTag);



