#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AbilitySystemInterface.h"
#include "AbilitySystemComponent.h"
#include "Abilities/GameplayAbilityTypes.h"
#include "CombatTypes.h"
#include "CombatCharacter.generated.h"
class UCombatAttributeSet;
class UCombatGameplayAbility;
class USpringArmComponent;
class UCameraComponent;
class UGameplayEffect;
class UMotionWarpingComponent;
class UStaticMeshComponent;
class ACombatProjectile;
class UCombatFeedbackComponent;
class UCameraShakeBase;
class USoundBase;
class UAnimMontage;
struct FCombatLocomotionSettings;
class UCombatLocomotionConfig;
class UCombatSkillRuntime;

UCLASS(Blueprintable)
class COMBAT_API ACombatCharacter : public ACharacter, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UCombatSkillRuntime> SkillRuntime;
    UPROPERTY(BlueprintReadOnly, Category="Combat") TWeakObjectPtr<ACombatCharacter> LastDamageSource;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TObjectPtr<UCombatSkillSet> DesignerSkillSet;
    UFUNCTION(BlueprintCallable, Category="Combat") ECombatSkillRequestResult RequestSkillDetailed(FGameplayTag SkillTag);
    UFUNCTION(BlueprintCallable, Category="Combat") bool TryInterruptSkill(ECombatInterruptReason Reason);
    UFUNCTION(BlueprintCallable, Category="Combat") void SetComboWindow(bool bAllowed) { bComboWindow = bAllowed; }
    void ApplyPeriodicDamage(float Damage, ACombatCharacter* Source);
    int32 AllocateAttackInstance() { return ++AttackInstance; }
    void SampleSkillHit() { TraceHitWindow(); }
    UFUNCTION(BlueprintCallable, Category="Combat") void EquipRuntimeSkills(const TArray<UCombatSkillDefinition*>& Skills);
    ACombatCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    const FCombatLocomotionSettings& GetLocomotionSettings() const;
    void DrawLocomotionDebug() const;
    FVector GetLocomotionDebugInput() const { return SampleMovementDirection(); }
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override { return AbilitySystem; }
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void Landed(const FHitResult& Hit) override;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Locomotion", meta=(ToolTip="Edit this Data Asset in Details for live player locomotion tuning.")) TObjectPtr<UCombatLocomotionConfig> LocomotionConfig;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UAbilitySystemComponent> AbilitySystem;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UCombatAttributeSet> Attributes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UMotionWarpingComponent> MotionWarping;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UStaticMeshComponent> WeaponMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Combat") TObjectPtr<UCombatFeedbackComponent> FeedbackComponent;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") bool bTraceFromCharacterMesh = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TSubclassOf<ACombatProjectile> ProjectileClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Camera") TSubclassOf<UCameraShakeBase> HitCameraShake;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Settings") float MasterVolume = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Settings") float CameraSensitivity = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Settings") bool bCameraShakeEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Feedback") float HitStopDuration = .045f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Feedback") TObjectPtr<UAnimMontage> DeathMontage;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Feedback") TObjectPtr<UAnimMontage> HitReactMontage;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Feedback") TObjectPtr<USoundBase> DeathSound;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Feedback") TArray<TObjectPtr<USoundBase>> FootstepSounds;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Feedback") float FootstepDistance = 160.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Camera") float DefaultCameraDistance = 560.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Camera", meta=(ClampMin="0")) float CameraHideDistance = 220.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Camera", meta=(ClampMin="0")) float CameraRevealDistance = 270.f;
    UFUNCTION(BlueprintPure, Category="Camera") bool IsHiddenForCloseCamera() const { return bHiddenForCloseCamera; }
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Camera") float SoftLockRange = 650.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Camera") float SoftLockViewDot = .4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FName WeaponAttachSocket = "hand_r";
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FName TraceStartSocket = "BladeBase";
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FName TraceEndSocket = "BladeTip";
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float WeaponBladeLength = 130.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") FVector WeaponBladeAxis = FVector::ForwardVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float MaxAirHangBudget = .25f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera") TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera") TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") bool bIsBoss = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float InitialHealth = 300.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") float InitialPoise = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TArray<TSubclassOf<UGameplayAbility>> AbilitySet;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TArray<TObjectPtr<UCombatSkillDefinition>> SkillDefinitions;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Combat") TObjectPtr<ACombatCharacter> CombatTarget;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bPhaseTwo = false;
    UPROPERTY(BlueprintReadOnly, Category="Combat") bool bLastSkillInterrupted = false;
    UPROPERTY(BlueprintReadOnly, Category="Camera") bool bTargetLocked = false;
    UFUNCTION(BlueprintPure, Category="Camera") bool IsTargetLocked() const { return bTargetLocked; }
    UPROPERTY(BlueprintAssignable) FCombatFeedbackDelegate OnCombatFeedback;
    UPROPERTY(BlueprintAssignable) FCombatDeathDelegate OnCombatDeath;
    UPROPERTY(BlueprintAssignable) FCombatSkillDelegate OnSkillStarted;
    UPROPERTY(BlueprintAssignable) FCombatSkillDelegate OnSkillEnded;

    UFUNCTION(BlueprintCallable) bool RequestSkillByTag(FGameplayTag SkillTag);
    UFUNCTION(BlueprintCallable) bool RequestSkillByInputTag(FGameplayTag InputTag);
    UFUNCTION(BlueprintCallable) void CancelCurrentSkill();
    UFUNCTION(BlueprintCallable) void SetCombatTarget(ACombatCharacter* Target) { CombatTarget = Target; }
    UFUNCTION(BlueprintPure) ACombatCharacter* GetCombatTarget() const { return CombatTarget; }
    UFUNCTION(BlueprintPure) bool IsAlive() const;
    UFUNCTION(BlueprintPure) bool IsBusy() const;
    UFUNCTION(BlueprintPure) float GetHealth() const;
    UFUNCTION(BlueprintPure) float GetMaxHealth() const;
    UFUNCTION(BlueprintPure) float GetPoise() const;
    UFUNCTION(BlueprintPure) float GetMaxPoise() const;
    UFUNCTION(BlueprintPure) FGameplayTag GetActiveSkillTag() const;
    UFUNCTION(BlueprintPure) UCombatSkillDefinition* GetActiveSkillDefinition() const { return ActiveSkill; }
    bool IsActiveAbility(const UCombatGameplayAbility* Ability) const { return ActiveAbility == Ability; }
    UFUNCTION(BlueprintPure) bool IsParryWindowActive() const;
    UFUNCTION(BlueprintPure) float GetSkillElapsedTime() const;
    UFUNCTION(BlueprintPure) float GetSkillCooldownRemaining(FGameplayTag SkillTag) const;
    UFUNCTION(BlueprintCallable) void ResetCombatState();
    UFUNCTION(BlueprintCallable) ECombatHitResult ReceiveCombatHit(const FCombatHit& Hit);
    UFUNCTION(BlueprintCallable) void OpenHitWindow();
    UFUNCTION(BlueprintCallable) void CloseHitWindow();
    UFUNCTION(BlueprintCallable) void StartSkillMovement(float Distance = -1.f, float Duration = -1.f, FVector Direction = FVector::ZeroVector);
    UFUNCTION(BlueprintCallable) void EmitSkillProjectile();
    UFUNCTION(BlueprintCallable) void ShowAreaWarning();
    UFUNCTION(BlueprintCallable) void DetonateArea();
    UFUNCTION(BlueprintCallable) void OpenComboWindow();
    UFUNCTION(BlueprintCallable) void SetCancelable(bool bAllowed = true) { bCancelable = bAllowed; }
    UFUNCTION(BlueprintCallable) void ApplyCombatEffect(TSubclassOf<UGameplayEffect> EffectClass, float Level = 1.f);
    UFUNCTION(BlueprintCallable) void FinishSkill();
    UFUNCTION(BlueprintCallable) void SetParryWindow(bool bEnabled);
    UFUNCTION(BlueprintCallable) void SetInvulnerable(bool bEnabled);
    UFUNCTION(BlueprintCallable) void HandleMontageEvent(FGameplayTag EventTag);
    UFUNCTION(BlueprintCallable) void BeginSkill(UCombatSkillDefinition* Definition, UCombatGameplayAbility* Ability);
    UFUNCTION(BlueprintCallable) void EndSkill(bool bInterrupted);
    UFUNCTION(BlueprintImplementableEvent) void OnProjectileRequested(const FCombatHit& Hit, float Speed);
    UFUNCTION(BlueprintImplementableEvent) void OnAreaWarningRequested(FVector Center, float Radius, float Height, float Delay);
    UFUNCTION(BlueprintCallable) void AttackPressed();
    UFUNCTION(BlueprintCallable) void AttackReleased();
    UFUNCTION(BlueprintCallable) void ParryPressed();
    UFUNCTION(BlueprintCallable) void DashPressed();
    UFUNCTION(BlueprintCallable) void ToggleTargetLock();
    UFUNCTION(BlueprintCallable) void RetryEncounter();
    UFUNCTION(BlueprintCallable) void ApplyHitStop(float Duration);
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY() TObjectPtr<UCombatSkillDefinition> ActiveSkill;
    UPROPERTY() TObjectPtr<UCombatGameplayAbility> ActiveAbility;
    UPROPERTY() TObjectPtr<UAnimMontage> ActiveDeathMontage;
    TMap<FGameplayTag, FGameplayAbilitySpecHandle> SkillHandles;
    FActiveGameplayEffectHandle RiposteEffectHandle;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    TMap<TWeakObjectPtr<ACombatCharacter>, TArray<int32>> ReceivedAttackIds;
    TArray<FActiveGameplayEffectHandle> TemporaryEffects;
    TArray<TWeakObjectPtr<ACombatProjectile>> SkillProjectiles;
    bool bHitWindow = false;
    bool bComboWindow = false;
    bool bCancelable = false;
    bool bAirDashUsed = false;
    bool bAttackHeld = false;
    int32 ComboIndex = 0;
    int32 AirComboIndex = 0;
    int32 AttackInstance = 0;
    int32 HitWindowAttackInstance = 0;
    uint64 SkillExecutionSerial = 0;
    float SkillStartedAt = 0.f;
    float BufferedUntil = 0.f;
    float RiposteUntil = 0.f;
    float StunnedUntil = 0.f;
    float PoiseImmuneUntil = 0.f;
    float AttackPressedAt = 0.f;
    float MovementRemaining = 0.f;
    float MovementSpeed = 0.f;
    bool bDashHorizontalOverride = false;
    bool bHiddenForCloseCamera = false;
    bool bSavedMeshOwnerNoSee = false;
    bool bSavedWeaponOwnerNoSee = false;
    bool bSavedMeshHiddenShadow = false;
    bool bSavedWeaponHiddenShadow = false;
    float SavedDashMaxAcceleration = 0.f;
    float LastDamageAt = 0.f;
    float AirHangBudgetUsed = 0.f;
    float AirHangRemaining = 0.f;
    float HitStopUntilReal = 0.f;
    float HitStopStartedReal = 0.f;
    float SavedTimeDilation = 1.f;
    float StepDistanceAccumulator = 0.f;
    int32 StepIndex = 0;
    FVector PreviousStepLocation = FVector::ZeroVector;
    FTransform InitialMeshTransform;
    FName InitialMeshCollisionProfile;
    FVector MovementDirection = FVector::ZeroVector;
    FVector LastTraceStart = FVector::ZeroVector;
    FVector LastTraceEnd = FVector::ZeroVector;
    FVector AreaCenter = FVector::ZeroVector;
    FGameplayTag BufferedSkill;
    FTimerHandle AreaTimer;
    FTimerHandle SkillTimeout;
    FTransform InitialTransform;
    void MoveForward(float Value);
    void MoveRight(float Value);
    void LookYaw(float Value);
    void LookPitch(float Value);
    void JumpPressed();
    void PausePressed();
    void EndDashHorizontalOverride();
    void SetHiddenForCloseCamera(bool bHide);
    void UpdateCloseCameraVisibility();
    void TraceHitWindow();
    void GetBladeEndpoints(FVector& Start, FVector& End) const;
    void DestroyOwnedProjectiles();
    void UpdateFootsteps();
    bool CanAssistFacing() const;
    void DoAreaDamage();
    void Die();
    void CheckPoiseBreak(float Now);
    FVector SampleMovementDirection(bool bForDash = false) const;
    void ApplyLocomotionSettings();
    void ApplyAttributeDelta(const FGameplayAttribute& Attribute, float Delta);
    FCombatHit MakeHit(int32 HitInstance) const;
    void BroadcastCue(FGameplayTag Tag, ACombatCharacter* Target, FVector Location, float Intensity = 1.f);
};




