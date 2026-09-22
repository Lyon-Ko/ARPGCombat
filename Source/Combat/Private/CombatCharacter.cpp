#include "CombatCharacter.h"
#include "CombatAnimInstance.h"
#include "CombatMovementComponent.h"
#include "CombatLocomotionSettings.h"
#include "CombatLocomotionConfig.h"
#include "Engine/Engine.h"
#include "DrawDebugHelpers.h"
#include "CombatGameMode.h"
#include "CombatAttributeSet.h"
#include "CombatGameplayAbility.h"
#include "CombatTags.h"
#include "CombatEffects.h"
#include "CombatAIController.h"
#include "CombatProjectile.h"
#include "CombatFeedback.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "MotionWarpingComponent.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "GameplayEffect.h"
#include "GameFramework/PlayerController.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/AudioComponent.h"

static FGameplayTag CT(const TCHAR* Name) { return FGameplayTag::RequestGameplayTag(FName(Name)); }
ACombatCharacter::ACombatCharacter(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UCombatMovementComponent>(ACharacter::CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    AbilitySystem = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("AbilitySystem"));
    Attributes = CreateDefaultSubobject<UCombatAttributeSet>(TEXT("Attributes"));
    MotionWarping = CreateDefaultSubobject<UMotionWarpingComponent>(TEXT("MotionWarping"));
    FeedbackComponent = CreateDefaultSubobject<UCombatFeedbackComponent>(TEXT("Feedback"));
    ProjectileClass = ACombatProjectile::StaticClass();
    WeaponMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Weapon"));
    WeaponMesh->SetupAttachment(GetMesh(), WeaponAttachSocket);
    WeaponMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 560.f;
    CameraBoom->SocketOffset = FVector(0, 45, 85);
    CameraBoom->bUsePawnControlRotation = true;
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(CameraBoom);
    GetCapsuleComponent()->InitCapsuleSize(38.f, 92.f);
    GetMesh()->SetRelativeLocationAndRotation(FVector(0,0,-92), FRotator(0,-90,0));
    GetCharacterMovement()->MaxWalkSpeed = 560.f;
    GetCharacterMovement()->JumpZVelocity = 650.f;
    GetCharacterMovement()->GravityScale = 1.8f;
    GetCharacterMovement()->AirControl = .7f;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0,900,0);
    JumpMaxCount = 2;
    bUseControllerRotationYaw = false;
}
void ACombatCharacter::BeginPlay()
{
    Super::BeginPlay();
    ApplyLocomotionSettings();
    InitialTransform = GetActorTransform();
    InitialMeshTransform = GetMesh()->GetRelativeTransform();
    InitialMeshCollisionProfile = GetMesh()->GetCollisionProfileName();
    PreviousStepLocation = GetActorLocation();
    CameraBoom->TargetArmLength = DefaultCameraDistance;
    AbilitySystem->InitAbilityActorInfo(this, this);
    Attributes->InitMaxHealth(InitialHealth); Attributes->InitHealth(InitialHealth);
    Attributes->InitMaxPoise(InitialPoise); Attributes->InitPoise(InitialPoise);
    WeaponMesh->AttachToComponent(GetMesh(), FAttachmentTransformRules::KeepRelativeTransform, WeaponAttachSocket);
    for(UCombatSkillDefinition* Definition : SkillDefinitions)
        if(Definition && Definition->AbilityClass && Definition->SkillTag.IsValid())
        {
            FGameplayAbilitySpec Spec(Definition->AbilityClass, 1, INDEX_NONE, Definition);
            SkillHandles.Add(Definition->SkillTag, AbilitySystem->GiveAbility(Spec));
        }
    for(auto Class : AbilitySet) if(Class) AbilitySystem->GiveAbility(FGameplayAbilitySpec(Class, 1));
    if(bIsBoss) { Camera->Deactivate(); CameraBoom->Deactivate(); }
}
const FCombatLocomotionSettings& ACombatCharacter::GetLocomotionSettings() const
{
    static const FCombatLocomotionSettings BossDefaults;
    return bIsBoss ? BossDefaults : UCombatLocomotionSubsystem::For(this);
}
void ACombatCharacter::ApplyLocomotionSettings()
{
    if(bIsBoss) return;
    if(LocomotionConfig)
        if(auto* Config = GetWorld()->GetSubsystem<UCombatLocomotionSubsystem>()) Config->SetConfiguration(LocomotionConfig);
    const auto& S = GetLocomotionSettings();
    DefaultCameraDistance = S.CameraDistance;
    CameraSensitivity = S.CameraSensitivity;
    CameraHideDistance = S.CameraHideDistance;
    CameraRevealDistance = S.CameraRevealDistance;
    SoftLockRange = S.SoftLockRange;
    SoftLockViewDot = S.SoftLockViewDot;
    MaxAirHangBudget = S.MaxAirHangBudget;
    CameraBoom->SocketOffset = FVector(S.CameraOffsetX, S.CameraOffsetY, S.CameraOffsetZ);
    CameraBoom->bDoCollisionTest = S.CameraCollision;
    CameraBoom->ProbeSize = S.CameraProbeSize;
    CameraBoom->bEnableCameraLag = S.CameraLag;
    CameraBoom->CameraLagSpeed = S.CameraLagSpeed;
    CameraBoom->bEnableCameraRotationLag = S.CameraRotationLag;
    CameraBoom->CameraRotationLagSpeed = S.CameraRotationLagSpeed;
    Camera->SetFieldOfView(S.CameraFOV);
}
bool ACombatCharacter::IsAlive() const { return Attributes && GetHealth() > 0.f; }
bool ACombatCharacter::IsBusy() const { return ActiveSkill != nullptr || AbilitySystem->HasMatchingGameplayTag(CombatTags::State_Stunned); }
float ACombatCharacter::GetHealth() const { return Attributes->GetHealth(); }
float ACombatCharacter::GetMaxHealth() const { return Attributes->GetMaxHealth(); }
float ACombatCharacter::GetPoise() const { return Attributes->GetPoise(); }
float ACombatCharacter::GetMaxPoise() const { return Attributes->GetMaxPoise(); }
FGameplayTag ACombatCharacter::GetActiveSkillTag() const { return ActiveSkill ? ActiveSkill->SkillTag : FGameplayTag(); }
bool ACombatCharacter::IsParryWindowActive() const { return AbilitySystem->HasMatchingGameplayTag(CombatTags::State_Parry); }
float ACombatCharacter::GetSkillElapsedTime() const { return ActiveSkill ? GetWorld()->GetTimeSeconds() - SkillStartedAt : 0.f; }
float ACombatCharacter::GetSkillCooldownRemaining(FGameplayTag SkillTag) const
{
    float Remaining = 0.f;
    for(float Time : AbilitySystem->GetActiveEffectsTimeRemaining(FGameplayEffectQuery::MakeQuery_MatchAnyEffectTags(FGameplayTagContainer(SkillTag)))) Remaining = FMath::Max(Remaining, Time);
    return Remaining;
}

bool ACombatCharacter::RequestSkillByInputTag(FGameplayTag InputTag)
{
    FGameplayTagContainer OwnedTags; AbilitySystem->GetOwnedGameplayTags(OwnedTags);
    TArray<UCombatSkillDefinition*> Candidates;
    for(UCombatSkillDefinition* Definition : SkillDefinitions)
        if(Definition && Definition->InputTag == InputTag && GetSkillCooldownRemaining(Definition->SkillTag) <= 0.f && (Definition->ActivationQuery.IsEmpty() || Definition->ActivationQuery.Matches(OwnedTags)) && (!Definition->bAirOnly || GetCharacterMovement()->IsFalling()) && (!Definition->bGroundOnly || !GetCharacterMovement()->IsFalling()) && (Definition->AirAttackIndex == 0 || Definition->AirAttackIndex == AirComboIndex + 1)) Candidates.Add(Definition);
    Candidates.Sort([](const UCombatSkillDefinition& A, const UCombatSkillDefinition& B) { return A.Priority > B.Priority; });
    for(auto* Definition : Candidates)
    {
        if(RequestSkillByTag(Definition->SkillTag)) return true;
        if(BufferedSkill == Definition->SkillTag && BufferedUntil >= GetWorld()->GetTimeSeconds()) return false;
    }
    return false;
}
bool ACombatCharacter::RequestSkillByTag(FGameplayTag SkillTag)
{
    if(!IsAlive() || AbilitySystem->HasMatchingGameplayTag(CombatTags::State_Stunned)) return false;
    const auto* Handle = SkillHandles.Find(SkillTag);
    if(!Handle) return false;
    UCombatSkillDefinition* Definition = nullptr;
    for(UCombatSkillDefinition* Item : SkillDefinitions) if(Item && Item->SkillTag == SkillTag) { Definition = Item; break; }
    const float Now = GetWorld()->GetTimeSeconds();
    if(!Definition || GetSkillCooldownRemaining(SkillTag) > 0.f || (Definition->bAirOnly && !GetCharacterMovement()->IsFalling()) || (Definition->AirAttackIndex > 0 && (Definition->AirAttackIndex != AirComboIndex + 1 || AirComboIndex >= 2))) return false;
    if(Definition->bGroundOnly && GetCharacterMovement()->IsFalling()) return false;
    FGameplayTagContainer OwnedTags; AbilitySystem->GetOwnedGameplayTags(OwnedTags);
    if(!Definition->ActivationQuery.IsEmpty() && !Definition->ActivationQuery.Matches(OwnedTags)) return false;
    if(ActiveSkill)
    {
        if(!bCancelable && !bComboWindow && !Definition->bCanInterrupt)
        { BufferedSkill = SkillTag; BufferedUntil = Now + GetLocomotionSettings().InputBufferTime; return false; }
        CancelCurrentSkill();
    }
    return AbilitySystem->TryActivateAbility(*Handle);
}
void ACombatCharacter::BeginSkill(UCombatSkillDefinition* Definition, UCombatGameplayAbility* Ability)
{
    if(auto* Anim = Cast<UCombatAnimInstance>(GetMesh()->GetAnimInstance())) Anim->StopGroundPivot();
    if(!bIsBoss) GetCharacterMovement()->bOrientRotationToMovement = false;
    ConsumeMovementInputVector();
    // Ground skills own horizontal displacement; discard the run-in velocity.
    if(GetCharacterMovement()->IsMovingOnGround() && (bIsBoss || GetLocomotionSettings().StopOnGroundSkill)) GetCharacterMovement()->StopMovementImmediately();
    ++SkillExecutionSerial;
    ActiveSkill = Definition; ActiveAbility = Ability;
    bLastSkillInterrupted = false;
    SkillStartedAt = GetWorld()->GetTimeSeconds();
    if(Definition->Cooldown > 0.f)
    {
        FGameplayEffectSpec Spec(GetDefault<UCombatCooldownEffect>(), AbilitySystem->MakeEffectContext(), 1.f);
        Spec.SetDuration(Definition->Cooldown, true); Spec.AddDynamicAssetTag(Definition->SkillTag); Spec.AddDynamicAssetTag(CT(TEXT("Combat.State.Cooldown")));
        AbilitySystem->ApplyGameplayEffectSpecToSelf(Spec);
    }
    if(Definition->AirAttackIndex > 0)
    {
        AirComboIndex = Definition->AirAttackIndex;
        AirHangRemaining = FMath::Min(Definition->AirHangTime, FMath::Max(0.f, MaxAirHangBudget - AirHangBudgetUsed));
        AirHangBudgetUsed += AirHangRemaining;
    }
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Busy, 1);
    AbilitySystem->SetLooseGameplayTagCount(Definition->SkillTag, 1);
    bCancelable = bComboWindow = false;
    if(Definition->bFaceTarget && CanAssistFacing())
    {
        FVector ToTarget = CombatTarget->GetActorLocation() - GetActorLocation(); ToTarget.Z = 0;
        if(!ToTarget.IsNearlyZero()) SetActorRotation(ToTarget.Rotation());
        MotionWarping->AddOrUpdateWarpTargetFromLocationAndRotation(TEXT("CombatTarget"), CombatTarget->GetActorLocation() - ToTarget.GetSafeNormal() * 130.f, ToTarget.Rotation());
    }
    const FString Name = Definition->SkillTag.ToString();
    if(Name == TEXT("Combat.Skill.Dash"))
    {
        AbilitySystem->SetLooseGameplayTagCount(CT(TEXT("Combat.State.Dashing")), 1);
        FVector Direction = SampleMovementDirection(true);
        if(Direction.IsNearlyZero()) Direction = -GetActorForwardVector();
        auto* Move = GetCharacterMovement();
        SavedDashMaxAcceleration = Move->MaxAcceleration;
        bDashHorizontalOverride = true;
        Move->MaxAcceleration = 0.f;
        Move->Velocity.X = Move->Velocity.Y = 0.f;
        ConsumeMovementInputVector();
        StartSkillMovement(GetLocomotionSettings().DashDistance, GetLocomotionSettings().DashDuration, Direction);
        if(GetCharacterMovement()->IsFalling()) bAirDashUsed = true;
    }
    if(Name == TEXT("Combat.Skill.Parry")) SetParryWindow(true);
    if(Name == TEXT("Combat.Skill.Riposte")) { RiposteUntil = 0; AbilitySystem->RemoveActiveGameplayEffect(RiposteEffectHandle); }
    GetWorldTimerManager().SetTimer(SkillTimeout, this, &ThisClass::FinishSkill, FMath::Max(.1f, Definition->Duration + .3f), false);
    FeedbackComponent->BeginSkillFeedback(Definition);
    OnSkillStarted.Broadcast(this, Definition->SkillTag);
}
void ACombatCharacter::CancelCurrentSkill()
{
    // CancelAbility compares the granted CDO, not an InstancedPerActor instance.
    // The spec handle routes cancellation to the active instance and its tasks.
    if(ActiveAbility) AbilitySystem->CancelAbilityHandle(ActiveAbility->GetCurrentAbilitySpecHandle());
    else EndSkill(true);
}
void ACombatCharacter::FinishSkill()
{
    if(ActiveAbility) ActiveAbility->CompleteSkill();
    else EndSkill(false);
}
void ACombatCharacter::EndSkill(bool bInterrupted)
{
    bLastSkillInterrupted = bInterrupted;
    if(bInterrupted) { BufferedSkill = FGameplayTag(); BufferedUntil = 0.f; }
    const FGameplayTag OldTag = GetActiveSkillTag();
    GetWorldTimerManager().ClearTimer(SkillTimeout);
    GetWorldTimerManager().ClearTimer(AreaTimer);
    CloseHitWindow(); MovementRemaining = 0; AirHangRemaining = 0;
    EndDashHorizontalOverride();
    FeedbackComponent->EndSkillFeedback();
    if(bInterrupted) for(auto Projectile : SkillProjectiles) if(Projectile.IsValid()) Projectile->Destroy();
    if(bInterrupted) SkillProjectiles.Reset();
    SetParryWindow(false); SetInvulnerable(false);
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Busy, 0);
    AbilitySystem->SetLooseGameplayTagCount(CT(TEXT("Combat.State.Dashing")), 0);
    if(OldTag.IsValid()) AbilitySystem->SetLooseGameplayTagCount(OldTag, 0);
    for(auto Handle : TemporaryEffects) AbilitySystem->RemoveActiveGameplayEffect(Handle);
    TemporaryEffects.Reset();
    MotionWarping->RemoveWarpTarget(TEXT("CombatTarget"));
    ActiveSkill = nullptr; ActiveAbility = nullptr; bCancelable = bComboWindow = false;
    if(OldTag.IsValid()) OnSkillEnded.Broadcast(this, OldTag);
    // RiposteReady belongs to the character reward window, never this skill's cleanup.
    if(bIsBoss && GetHealth() <= GetMaxHealth() * .5f && IsAlive()) bPhaseTwo = true;
}
void ACombatCharacter::OpenHitWindow()
{
    if(!ActiveSkill) return;
    bHitWindow = true; HitActors.Reset(); HitWindowAttackInstance = ++AttackInstance;
    GetBladeEndpoints(LastTraceStart, LastTraceEnd);
    FeedbackComponent->BeginTrail();
}
void ACombatCharacter::CloseHitWindow() { bHitWindow = false; HitActors.Reset(); FeedbackComponent->EndTrail(); }
void ACombatCharacter::GetBladeEndpoints(FVector& Start, FVector& End) const
{
    const USceneComponent* Source = bTraceFromCharacterMesh ? static_cast<const USceneComponent*>(GetMesh()) : static_cast<const USceneComponent*>(WeaponMesh.Get());
    Start = Source->DoesSocketExist(TraceStartSocket) ? Source->GetSocketLocation(TraceStartSocket) : Source->GetComponentLocation();
    End = Source->DoesSocketExist(TraceEndSocket) ? Source->GetSocketLocation(TraceEndSocket) : Start + Source->GetComponentTransform().TransformVectorNoScale(WeaponBladeAxis.GetSafeNormal()) * WeaponBladeLength;
}
FCombatHit ACombatCharacter::MakeHit(int32 HitInstance) const
{
    FCombatHit Hit; Hit.Attacker = const_cast<ACombatCharacter*>(this); Hit.AttackInstance = HitInstance;
    Hit.Direction = GetActorForwardVector(); Hit.Location = GetActorLocation();
    if(ActiveSkill) { Hit.Damage = ActiveSkill->Damage * (bPhaseTwo ? 1.15f : 1.f); Hit.PoiseDamage = ActiveSkill->PoiseDamage; Hit.bParryable = ActiveSkill->bParryable; }
    return Hit;
}
void ACombatCharacter::TraceHitWindow()
{
    if(!bHitWindow || !ActiveSkill) return;
    const uint64 ExecutionSerial = SkillExecutionSerial;
    FVector Start, End; GetBladeEndpoints(Start, End);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(CombatBlade), false, this);
    FCollisionObjectQueryParams Objects; Objects.AddObjectTypesToQuery(ECC_Pawn);
    const float Radius = ActiveSkill->TraceRadius;
    // Sweep samples along the blade between frames, then the current blade itself.
    for(int32 I=0; I<=6; ++I)
    {
        const float Alpha = I / 6.f;
        TArray<FHitResult> Hits;
        GetWorld()->SweepMultiByObjectType(Hits, FMath::Lerp(LastTraceStart, LastTraceEnd, Alpha), FMath::Lerp(Start, End, Alpha), FQuat::Identity, Objects, FCollisionShape::MakeSphere(Radius), Params);
        for(const auto& Result : Hits)
            if(auto* Target = Cast<ACombatCharacter>(Result.GetActor()); Target && Target->bIsBoss != bIsBoss && !HitActors.Contains(Target))
            {
                HitActors.Add(Target); auto Hit = MakeHit(HitWindowAttackInstance); Hit.Location = Result.ImpactPoint; Hit.Direction = (Target->GetActorLocation() - GetActorLocation()).GetSafeNormal(); Target->ReceiveCombatHit(Hit);
                if(!bHitWindow || !ActiveSkill || SkillExecutionSerial != ExecutionSerial) return;
            }
    }
    LastTraceStart = Start; LastTraceEnd = End;
}
void ACombatCharacter::ApplyAttributeDelta(const FGameplayAttribute& Attribute, float Delta)
{
    UGameplayEffect* Effect = NewObject<UGameplayEffect>(GetTransientPackage());
    Effect->DurationPolicy = EGameplayEffectDurationType::Instant;
    FGameplayModifierInfo& Modifier = Effect->Modifiers.AddDefaulted_GetRef();
    Modifier.Attribute = Attribute; Modifier.ModifierOp = EGameplayModOp::Additive; Modifier.ModifierMagnitude = FScalableFloat(Delta);
    FGameplayEffectSpec Spec(Effect, AbilitySystem->MakeEffectContext(), 1.f);
    AbilitySystem->ApplyGameplayEffectSpecToSelf(Spec);
}
ECombatHitResult ACombatCharacter::ReceiveCombatHit(const FCombatHit& Hit)
{
    if(!IsAlive() || !Hit.Attacker || Hit.Attacker == this || Hit.Attacker->bIsBoss == bIsBoss) return ECombatHitResult::Miss;
    TArray<int32>& RecentHits = ReceivedAttackIds.FindOrAdd(Hit.Attacker);
    if(RecentHits.Contains(Hit.AttackInstance)) return ECombatHitResult::Miss;
    RecentHits.Add(Hit.AttackInstance);
    if(RecentHits.Num() > 64) RecentHits.RemoveAt(0, RecentHits.Num() - 64);
    const float Now = GetWorld()->GetTimeSeconds();
    const bool bTimedDashInvulnerable = ActiveSkill && ActiveSkill->SkillTag == CT(TEXT("Combat.Skill.Dash")) && GetSkillElapsedTime() >= .04f && GetSkillElapsedTime() <= .18f;
    if(bTimedDashInvulnerable || (AbilitySystem->HasMatchingGameplayTag(CombatTags::State_Invulnerable) && GetActiveSkillTag() != CT(TEXT("Combat.Skill.Dash")))) { BroadcastCue(CombatTags::Cue_Evade, this, GetActorLocation()); return ECombatHitResult::Evaded; }
    const FVector ToAttacker = (Hit.Attacker->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    if(Hit.bParryable && IsParryWindowActive() && GetSkillElapsedTime() <= .2f && FVector::DotProduct(GetActorForwardVector(), ToAttacker) >= FMath::Cos(FMath::DegreesToRadians(70.f)))
    {
        RiposteUntil = Now + .8f;
        AbilitySystem->RemoveActiveGameplayEffect(RiposteEffectHandle);
        RiposteEffectHandle = AbilitySystem->ApplyGameplayEffectToSelf(GetDefault<UCombatRiposteEffect>(), 1.f, AbilitySystem->MakeEffectContext());
        for(auto Handle : AbilitySystem->GetActiveEffects(FGameplayEffectQuery::MakeQuery_MatchAnyEffectTags(FGameplayTagContainer(CT(TEXT("Combat.Skill.Parry")))))) AbilitySystem->RemoveActiveGameplayEffect(Handle);
        Hit.Attacker->CancelCurrentSkill();
        if(Now >= Hit.Attacker->PoiseImmuneUntil) Hit.Attacker->ApplyAttributeDelta(UCombatAttributeSet::GetPoiseAttribute(), -Hit.PoiseDamage * 1.6f);
        Hit.Attacker->CheckPoiseBreak(Now);
        Hit.Attacker->StunnedUntil = FMath::Max(Hit.Attacker->StunnedUntil, Now + .3f);
        Hit.Attacker->AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Stunned, 1);
        ApplyHitStop(HitStopDuration * 1.3f); Hit.Attacker->ApplyHitStop(HitStopDuration * 1.3f);
        BroadcastCue(CombatTags::Cue_Parry, Hit.Attacker, Hit.Location, 1.4f);
        return ECombatHitResult::Parried;
    }
    ApplyAttributeDelta(UCombatAttributeSet::GetHealthAttribute(), -FMath::Max(0.f, Hit.Damage));
    if(Now >= PoiseImmuneUntil) ApplyAttributeDelta(UCombatAttributeSet::GetPoiseAttribute(), -FMath::Max(0.f, Hit.PoiseDamage));
    LastDamageAt = Now;
    ApplyHitStop(HitStopDuration); Hit.Attacker->ApplyHitStop(HitStopDuration);
    Hit.Attacker->BroadcastCue(CombatTags::Cue_Hit, this, Hit.Location, Hit.Damage / 20.f);
    if(!IsAlive()) { Die(); return ECombatHitResult::Killed; }
    CheckPoiseBreak(Now);
    if(HitReactMontage && (!bIsBoss || !IsBusy()))
    {
        if(auto* Anim = Cast<UCombatAnimInstance>(GetMesh()->GetAnimInstance())) Anim->StopGroundPivot();
        if(!bIsBoss) CancelCurrentSkill();
        PlayAnimMontage(HitReactMontage);
    }
    return ECombatHitResult::Damaged;
}
void ACombatCharacter::CheckPoiseBreak(float Now)
{
    if(GetPoise() <= 0.f && Now >= PoiseImmuneUntil)
    {
        CancelCurrentSkill(); StunnedUntil = Now + (bIsBoss ? .9f : .5f); PoiseImmuneUntil = Now + 3.f;
        AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Stunned, 1);
        ApplyAttributeDelta(UCombatAttributeSet::GetPoiseAttribute(), GetMaxPoise());
        BroadcastCue(CombatTags::Cue_PoiseBreak, this, GetActorLocation(), 1.5f);
    }
}
void ACombatCharacter::SetParryWindow(bool bEnabled) { AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Parry, bEnabled ? 1 : 0); }
void ACombatCharacter::SetInvulnerable(bool bEnabled) { AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Invulnerable, bEnabled ? 1 : 0); }
void ACombatCharacter::ApplyCombatEffect(TSubclassOf<UGameplayEffect> EffectClass, float Level)
{
    if(EffectClass) TemporaryEffects.Add(AbilitySystem->ApplyGameplayEffectToSelf(EffectClass->GetDefaultObject<UGameplayEffect>(), Level, AbilitySystem->MakeEffectContext()));
}
void ACombatCharacter::StartSkillMovement(float Distance, float Duration, FVector Direction)
{
    if(!ActiveSkill) return;
    if(Distance < 0) Distance = ActiveSkill->MovementDistance;
    if(Duration < 0) Duration = ActiveSkill->MovementDuration;
    MovementRemaining = FMath::Max(.01f, Duration); MovementSpeed = Distance / MovementRemaining;
    MovementDirection = Direction.IsNearlyZero() ? GetActorTransform().TransformVectorNoScale(ActiveSkill->MovementDirectionLocal).GetSafeNormal() : Direction.GetSafeNormal();
    if(ActiveSkill->LaunchVelocityZ > 0.f) LaunchCharacter(FVector(0,0,ActiveSkill->LaunchVelocityZ), false, true);
}
void ACombatCharacter::EmitSkillProjectile()
{
    if(!ActiveSkill || !IsAlive()) return;
    const uint64 ExecutionSerial = SkillExecutionSerial;
    const UCombatSkillDefinition* Definition = ActiveSkill;
    const UCombatGameplayAbility* Ability = ActiveAbility;
    const FCombatHit Hit = MakeHit(++AttackInstance);
    const float Speed = Definition->ProjectileSpeed;
    FeedbackComponent->PlayReleaseSound();
    OnProjectileRequested(Hit, Speed);
    if(!IsAlive() || bLastSkillInterrupted || ActiveSkill != Definition || ActiveAbility != Ability || SkillExecutionSerial != ExecutionSerial) return;
    const FVector Origin = GetActorLocation() + GetActorForwardVector() * 90.f + FVector(0,0,35.f);
    const FVector Direction = CombatTarget && CombatTarget->IsAlive() ? (CombatTarget->GetActorLocation() - Origin).GetSafeNormal() : GetActorForwardVector();
    FActorSpawnParameters Params; Params.Owner = this; Params.Instigator = this; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Projectile = GetWorld()->SpawnActor<ACombatProjectile>(ProjectileClass, Origin, Direction.Rotation(), Params))
    {
        // A Blueprint projectile's BeginPlay may also end the owning skill.
        if(!IsAlive() || bLastSkillInterrupted || ActiveSkill != Definition || ActiveAbility != Ability || SkillExecutionSerial != ExecutionSerial) { Projectile->Destroy(); return; }
        Projectile->InitializeProjectile(Hit, Speed, Direction, Definition->CastEffect, Definition->ProjectileMesh, Definition->ProjectileMaterial, Definition->ProjectileCollisionHalfExtent);
        SkillProjectiles.Add(Projectile);
    }
}
void ACombatCharacter::ShowAreaWarning()
{
    if(!ActiveSkill || !IsAlive()) return;
    const UCombatSkillDefinition* Definition = ActiveSkill;
    const uint64 ExecutionSerial = SkillExecutionSerial;
    const FVector Center = GetActorLocation();
    const float Radius = Definition->AreaRadius, Height = Definition->AreaHeight, Delay = Definition->AreaDelay;
    const auto IsCurrentExecution = [&]() { return IsAlive() && ActiveSkill == Definition && SkillExecutionSerial == ExecutionSerial; };
    AreaCenter = Center;
    FeedbackComponent->ShowWarning(Center);
    if(!IsCurrentExecution()) return;
    OnAreaWarningRequested(Center, Radius, Height, Delay);
    if(!IsCurrentExecution()) return;
    BroadcastCue(CombatTags::Cue_AreaWarning, this, Center);
}
void ACombatCharacter::DetonateArea()
{
    if(!ActiveSkill || !IsAlive()) return;
    const UCombatSkillDefinition* Definition = ActiveSkill;
    const uint64 ExecutionSerial = SkillExecutionSerial;
    const FVector Center = AreaCenter;
    const float Radius = Definition->AreaRadius, Delay = Definition->AreaDelay;
    const auto IsCurrentExecution = [&]() { return IsAlive() && ActiveSkill == Definition && SkillExecutionSerial == ExecutionSerial; };
    BroadcastCue(CombatTags::Cue_AreaRelease, this, Center, Radius);
    if(!IsCurrentExecution()) return;
    FeedbackComponent->ReleaseArea();
    if(!IsCurrentExecution()) return;
    FeedbackComponent->PlayReleaseSound();
    if(!IsCurrentExecution()) return;
    GetWorldTimerManager().SetTimer(AreaTimer, this, &ThisClass::DoAreaDamage, FMath::Max(.001f, Delay), false);
}
void ACombatCharacter::DoAreaDamage()
{
    if(!ActiveSkill || !IsAlive()) return;
    const uint64 ExecutionSerial = SkillExecutionSerial;
    const UCombatSkillDefinition* Definition = ActiveSkill;
    const UCombatGameplayAbility* Ability = ActiveAbility;
    const float Radius = Definition->AreaRadius;
    const float Height = Definition->AreaHeight;
    const FVector Center = AreaCenter;
    const FCombatHit BaseHit = MakeHit(++AttackInstance);
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
    {
        auto* Target = *It;
        const FVector Delta = Target->GetActorLocation() - Center;
        if(Target != this && Target->bIsBoss != bIsBoss && Delta.Size2D() <= Radius + Target->GetCapsuleComponent()->GetScaledCapsuleRadius() && FMath::Abs(Delta.Z) <= Height * .5f + Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())
        {
            FCombatHit Hit = BaseHit; Hit.Location = Target->GetActorLocation(); Hit.Direction = Delta.GetSafeNormal(); Target->ReceiveCombatHit(Hit);
            if(!IsAlive() || bLastSkillInterrupted || ActiveSkill != Definition || ActiveAbility != Ability || SkillExecutionSerial != ExecutionSerial) return;
        }
    }
}
void ACombatCharacter::OpenComboWindow() { bComboWindow = true; }
void ACombatCharacter::HandleMontageEvent(FGameplayTag EventTag)
{
    const FString Event = EventTag.ToString();
    if(Event == TEXT("Combat.Event.HitOpen")) OpenHitWindow();
    else if(Event == TEXT("Combat.Event.HitClose")) CloseHitWindow();
    else if(Event == TEXT("Combat.Event.Move")) StartSkillMovement();
    else if(Event == TEXT("Combat.Event.Projectile")) EmitSkillProjectile();
    else if(Event == TEXT("Combat.Event.AreaWarning")) ShowAreaWarning();
    else if(Event == TEXT("Combat.Event.AreaRelease")) DetonateArea();
    else if(Event == TEXT("Combat.Event.ComboOpen")) OpenComboWindow();
    else if(Event == TEXT("Combat.Event.Cancelable")) SetCancelable();
    else if(Event == TEXT("Combat.Event.Finish")) FinishSkill();
}
void ACombatCharacter::BroadcastCue(FGameplayTag Tag, ACombatCharacter* Target, FVector Location, float Intensity) { OnCombatFeedback.Broadcast(this, Target, Tag, Location, Intensity); }
void ACombatCharacter::Die()
{
    if(auto* Anim = Cast<UCombatAnimInstance>(GetMesh()->GetAnimInstance())) Anim->StopGroundPivot();
    SetHiddenForCloseCamera(false);
    CancelCurrentSkill(); AbilitySystem->CancelAllAbilities();
    AbilitySystem->RemoveActiveGameplayEffect(RiposteEffectHandle);
    for(auto Projectile : SkillProjectiles) if(Projectile.IsValid()) Projectile->Destroy();
    SkillProjectiles.Reset();
    DestroyOwnedProjectiles();
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Dead, 1);
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_RiposteReady, 0);
    GetCharacterMovement()->ClearAccumulatedForces();
    ConsumeMovementInputVector();
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    if(DeathSound) UGameplayStatics::PlaySoundAtLocation(this, DeathSound, GetActorLocation(), MasterVolume);
    if(DeathMontage)
    {
        ActiveDeathMontage = DuplicateObject<UAnimMontage>(DeathMontage, this);
        ActiveDeathMontage->bEnableAutoBlendOut = false;
        PlayAnimMontage(ActiveDeathMontage);
    }
    else if(GetMesh()->GetPhysicsAsset())
    {
        GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
        GetMesh()->SetAllBodiesSimulatePhysics(true); GetMesh()->SetSimulatePhysics(true);
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
    BroadcastCue(CombatTags::Cue_Death, this, GetActorLocation(), 2.f); OnCombatDeath.Broadcast(this);
}
void ACombatCharacter::ResetCombatState()
{
    if(auto* Anim = Cast<UCombatAnimInstance>(GetMesh()->GetAnimInstance())) Anim->StopGroundPivot();
    SetHiddenForCloseCamera(false);
    CancelCurrentSkill(); AbilitySystem->CancelAllAbilities();
    DestroyOwnedProjectiles();
    CustomTimeDilation = SavedTimeDilation; HitStopUntilReal = 0.f;
    GetMesh()->bPauseAnims = false;
    GetMesh()->SetSimulatePhysics(false); GetMesh()->SetAllBodiesSimulatePhysics(false);
    GetMesh()->AttachToComponent(GetCapsuleComponent(), FAttachmentTransformRules::KeepRelativeTransform);
    GetMesh()->SetRelativeTransform(InitialMeshTransform); GetMesh()->SetCollisionProfileName(InitialMeshCollisionProfile);
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    if(auto* Anim = GetMesh()->GetAnimInstance()) Anim->StopAllMontages(0.f);
    ActiveDeathMontage = nullptr;
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Dead, 0);
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Stunned, 0);
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_RiposteReady, 0);
    Attributes->SetHealth(GetMaxHealth()); Attributes->SetPoise(GetMaxPoise());
    for(auto Handle : AbilitySystem->GetActiveEffects(FGameplayEffectQuery::MakeQuery_MatchAnyEffectTags(FGameplayTagContainer(CT(TEXT("Combat.State.Cooldown")))))) AbilitySystem->RemoveActiveGameplayEffect(Handle);
    AbilitySystem->RemoveActiveGameplayEffect(RiposteEffectHandle);
    ReceivedAttackIds.Reset(); BufferedSkill = FGameplayTag();
    RiposteUntil = StunnedUntil = MovementRemaining = PoiseImmuneUntil = LastDamageAt = 0; bPhaseTwo = bAirDashUsed = bAttackHeld = false;
    ComboIndex = AirComboIndex = 0; AirHangBudgetUsed = AirHangRemaining = 0; SetActorTransform(InitialTransform, false, nullptr, ETeleportType::TeleportPhysics);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking); GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->ClearAccumulatedForces();
    ConsumeMovementInputVector();
    PreviousStepLocation = GetActorLocation(); StepDistanceAccumulator = 0; StepIndex = 0;
    if(auto* AI = Cast<ACombatAIController>(Controller)) AI->ResetBrain();
}
void ACombatCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ApplyLocomotionSettings();
    UpdateCloseCameraVisibility();
    if(HitStopUntilReal > 0 && GetWorld()->GetRealTimeSeconds() >= HitStopUntilReal) { CustomTimeDilation = SavedTimeDilation; HitStopUntilReal = 0; }
    if(!IsAlive())
    {
        if(ActiveDeathMontage) if(auto* Anim = GetMesh()->GetAnimInstance(); Anim && Anim->Montage_GetPosition(ActiveDeathMontage) >= ActiveDeathMontage->GetPlayLength() - .02f) GetMesh()->bPauseAnims = true;
        return;
    }
    UpdateFootsteps();
    const float Now = GetWorld()->GetTimeSeconds();
    const bool bAir = GetCharacterMovement()->IsFalling();
    if(bAir && AirHangRemaining > 0.f) { GetCharacterMovement()->Velocity.Z = FMath::Max(0.f, GetCharacterMovement()->Velocity.Z); AirHangRemaining -= DeltaSeconds; }
    AbilitySystem->SetLooseGameplayTagCount(CT(TEXT("Combat.State.Air")), bAir ? 1 : 0);
    if(RiposteUntil > 0 && Now >= RiposteUntil) { RiposteUntil = 0; AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_RiposteReady, 0); }
    if(StunnedUntil > 0 && Now >= StunnedUntil) { StunnedUntil = 0; AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Stunned, 0); }
    if(GetPoise() < GetMaxPoise() && Now - LastDamageAt > 3.f) ApplyAttributeDelta(UCombatAttributeSet::GetPoiseAttribute(), DeltaSeconds * 12.f);
    if(ActiveSkill)
    {
        const FString SkillName = ActiveSkill->SkillTag.ToString();
        const float Elapsed = GetSkillElapsedTime();
        if(SkillName == TEXT("Combat.Skill.Dash")) SetInvulnerable(Elapsed >= .04f && Elapsed <= .18f);
        if(SkillName == TEXT("Combat.Skill.Parry") && Elapsed >= .2f) SetParryWindow(false);
    }
    if(MovementRemaining > 0.f)
    {
        if(bDashHorizontalOverride)
        {
            GetCharacterMovement()->Velocity.X = GetCharacterMovement()->Velocity.Y = 0.f;
            ConsumeMovementInputVector();
        }
        const float Step = FMath::Min(DeltaSeconds, MovementRemaining);
        FHitResult Hit; AddActorWorldOffset(MovementDirection * MovementSpeed * Step, true, &Hit);
        MovementRemaining -= Step;
        if(Hit.bBlockingHit) MovementRemaining = 0;
        if(MovementRemaining <= 0.f) EndDashHorizontalOverride();
    }
    TraceHitWindow();
    if(BufferedSkill.IsValid())
    {
        const FGameplayTag Tag = BufferedSkill;
        if(Now > BufferedUntil) BufferedSkill = FGameplayTag();
        else if(!IsBusy() || bComboWindow || bCancelable) { BufferedSkill = FGameplayTag(); RequestSkillByTag(Tag); }
    }
    if(!bIsBoss && IsPlayerControlled())
    {
        auto* PC = Cast<APlayerController>(Controller);
        if(PC)
        {
            if(bTargetLocked && (!CombatTarget || !CombatTarget->IsAlive())) bTargetLocked = false;
            const FVector DesiredMovement = SampleMovementDirection();
            // Buffered combos win above; held movement only releases permitted recovery.
            const auto& Tuning = GetLocomotionSettings();
            if(Tuning.AllowMovementRecovery && ActiveSkill && ActiveSkill->bAllowMovementCancel && bCancelable && !bHitWindow &&
                GetCharacterMovement()->IsMovingOnGround() && !DesiredMovement.IsNearlyZero()) CancelCurrentSkill();
            auto* Locomotion = Cast<UCombatAnimInstance>(GetMesh()->GetAnimInstance());
            if(Locomotion) Locomotion->UpdateGroundLocomotion(DeltaSeconds, DesiredMovement);
            GetCharacterMovement()->bOrientRotationToMovement = !bTargetLocked && !IsBusy() && !(Locomotion && Locomotion->IsPivoting());
            if(bTargetLocked && CombatTarget && !IsBusy())
            {
                FVector Facing = CombatTarget->GetActorLocation() - GetActorLocation(); Facing.Z = 0.f;
                if(!Facing.IsNearlyZero()) SetActorRotation(FMath::RInterpTo(GetActorRotation(), Facing.Rotation(), DeltaSeconds, Tuning.LockedTurnInterpSpeed));
            }
            MoveForward((PC->IsInputKeyDown(EKeys::W) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::S) ? 1.f : 0.f));
            MoveRight((PC->IsInputKeyDown(EKeys::D) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::A) ? 1.f : 0.f));
            if(bTargetLocked && CombatTarget && CombatTarget->IsAlive())
            {
                const FVector Midpoint = FMath::Lerp(GetActorLocation(), CombatTarget->GetActorLocation(), Tuning.CameraLockedTargetWeight);
                FRotator Desired = (Midpoint - Camera->GetComponentLocation()).Rotation(); Desired.Pitch = FMath::Clamp(Desired.Pitch, Tuning.CameraPitchMin, Tuning.CameraPitchMax);
                PC->SetControlRotation(FMath::RInterpTo(PC->GetControlRotation(), Desired, DeltaSeconds, Tuning.CameraLockedRotationInterp));
                CameraBoom->TargetArmLength = FMath::FInterpTo(CameraBoom->TargetArmLength, FMath::Clamp(FVector::Dist2D(GetActorLocation(), CombatTarget->GetActorLocation()) * Tuning.CameraDistanceScale + Tuning.CameraDistanceBias, Tuning.CameraLockedMinDistance, Tuning.CameraLockedMaxDistance), DeltaSeconds, Tuning.CameraLockedDistanceInterp);
            }
            else CameraBoom->TargetArmLength = FMath::FInterpTo(CameraBoom->TargetArmLength, DefaultCameraDistance, DeltaSeconds, Tuning.CameraFreeDistanceInterp);
            if(bAttackHeld && bAir && Now - AttackPressedAt > Tuning.PlungeHoldTime) { bAttackHeld = false; RequestSkillByTag(CT(TEXT("Combat.Skill.Plunge"))); }
            if(GEngine && Tuning.DebugOverlay)
            {
                const auto* Config = GetWorld()->GetSubsystem<UCombatLocomotionSubsystem>();
                const TCHAR* Phase = Locomotion && Locomotion->IsPivoting() ? (Locomotion->IsPivotAccelerating() ? TEXT("Reverse") : TEXT("Brake")) : TEXT("Move");
                const float Brake = Locomotion && Locomotion->IsPivoting() && !Locomotion->IsPivotAccelerating() ? Tuning.PivotBrakingDeceleration : 0.f;
                GEngine->AddOnScreenDebugMessage(72103, .3f, FColor::Cyan, FString::Printf(TEXT("Locomotion r%d | Speed %.0f | InputA %.0f | BrakeA %.0f | %s | Pivot %.2f"),
                    Config ? Config->GetRevision() : 0, GetVelocity().Size2D(), GetCharacterMovement()->GetCurrentAcceleration().Size2D(), Brake, Phase, Locomotion ? Locomotion->PivotProgress : 0.f));
            }
            else if(GEngine) GEngine->RemoveOnScreenDebugMessage(72103);
        }
    }
}
void ACombatCharacter::DrawLocomotionDebug() const
{
#if ENABLE_DRAW_DEBUG
    if(bIsBoss || !IsPlayerControlled() || !IsLocallyControlled() || !IsAlive()) return;
    const auto& S = GetLocomotionSettings();
    if(!S.DebugMovementVectors) return;

    FVector LogicalDirection = FVector::ZeroVector;
    FColor LogicalColor = FColor::Green;
    if(MovementRemaining > 0.f)
    {
        LogicalDirection = MovementDirection;
        LogicalColor = FColor::Orange;
    }
    else if(!IsBusy())
    {
        if(const auto* Anim = Cast<UCombatAnimInstance>(GetMesh()->GetAnimInstance()); Anim && Anim->IsPivoting())
        {
            // The desired reversal remains visible while velocity still points
            // in the incoming direction during braking. This is intent, not yaw.
            LogicalDirection = Anim->GetPivotDirection();
            LogicalColor = Anim->IsPivotAccelerating() ? FColor::Magenta : FColor::Yellow;
        }
        else LogicalDirection = GetLastMovementInputVector();
    }
    const FVector Start = GetActorLocation() + FVector(0, 0, S.DebugMovementVectorHeight - GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Direction = LogicalDirection.GetSafeNormal2D();
    // Single-frame, foreground lines: no history trails or global debug flush.
    if(!Direction.IsNearlyZero())
        DrawDebugDirectionalArrow(GetWorld(), Start, Start + Direction * S.DebugMovementVectorLength,
            20.f, LogicalColor, false, 0.f, SDPG_Foreground, 3.f);
    const FVector Velocity = GetVelocity();
    const float SpeedRatio = FMath::Clamp(Velocity.Size2D() / FMath::Max(1.f, GetCharacterMovement()->GetMaxSpeed()), 0.f, 1.f);
    if(!Velocity.IsNearlyZero() && SpeedRatio > UE_KINDA_SMALL_NUMBER)
    {
        const FVector VelocityStart = Start + FVector(0, 0, 8.f);
        const float VelocityLength = S.DebugMovementVectorLength * SpeedRatio;
        DrawDebugDirectionalArrow(GetWorld(), VelocityStart, VelocityStart + Velocity.GetSafeNormal2D() * VelocityLength,
            FMath::Min(16.f, VelocityLength * .3f), FColor::Blue, false, 0.f, SDPG_Foreground, 2.f);
    }
#endif
}

void ACombatCharacter::SetHiddenForCloseCamera(bool bHide)
{
    if(bHiddenForCloseCamera == bHide) return;
    if(bHide)
    {
        bSavedMeshOwnerNoSee = GetMesh()->bOwnerNoSee;
        bSavedMeshHiddenShadow = GetMesh()->bCastHiddenShadow;
        if(WeaponMesh)
        {
            bSavedWeaponOwnerNoSee = WeaponMesh->bOwnerNoSee;
            bSavedWeaponHiddenShadow = WeaponMesh->bCastHiddenShadow;
        }
    }
    GetMesh()->SetOwnerNoSee(bHide || bSavedMeshOwnerNoSee);
    GetMesh()->SetCastHiddenShadow(bHide || bSavedMeshHiddenShadow);
    if(WeaponMesh)
    {
        WeaponMesh->SetOwnerNoSee(bHide || bSavedWeaponOwnerNoSee);
        WeaponMesh->SetCastHiddenShadow(bHide || bSavedWeaponHiddenShadow);
    }
    bHiddenForCloseCamera = bHide;
}
void ACombatCharacter::UpdateCloseCameraVisibility()
{
    if(bIsBoss || !IsPlayerControlled() || !IsLocallyControlled() || !IsAlive() || !Camera)
    {
        SetHiddenForCloseCamera(false);
        return;
    }
    const float Distance = FVector::Distance(Camera->GetComponentLocation(), GetActorLocation());
    const float RevealDistance = FMath::Max(CameraHideDistance + 1.f, CameraRevealDistance);
    if(!bHiddenForCloseCamera && Distance < CameraHideDistance) SetHiddenForCloseCamera(true);
    else if(bHiddenForCloseCamera && Distance > RevealDistance) SetHiddenForCloseCamera(false);
}
void ACombatCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxisKey(EKeys::MouseX, this, &ThisClass::LookYaw);
    Input->BindAxisKey(EKeys::MouseY, this, &ThisClass::LookPitch);
    Input->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &ThisClass::AttackPressed);
    Input->BindKey(EKeys::LeftMouseButton, IE_Released, this, &ThisClass::AttackReleased).bExecuteWhenPaused = true;
    Input->BindKey(EKeys::RightMouseButton, IE_Pressed, this, &ThisClass::ParryPressed);
    Input->BindKey(EKeys::LeftShift, IE_Pressed, this, &ThisClass::DashPressed);
    Input->BindKey(EKeys::SpaceBar, IE_Pressed, this, &ThisClass::JumpPressed);
    Input->BindKey(EKeys::SpaceBar, IE_Released, this, &ACharacter::StopJumping).bExecuteWhenPaused = true;
    Input->BindKey(EKeys::Q, IE_Pressed, this, &ThisClass::ToggleTargetLock);
    Input->BindKey(EKeys::P, IE_Pressed, this, &ThisClass::PausePressed).bExecuteWhenPaused = true;
    Input->BindKey(EKeys::R, IE_Pressed, this, &ThisClass::RetryEncounter).bExecuteWhenPaused = true;
}
void ACombatCharacter::MoveForward(float Value)
{
    if(!Controller || IsBusy() || FMath::Abs(Value) <= GetLocomotionSettings().InputDeadZone) return;
    const FRotator Rotation(0, bTargetLocked && CombatTarget ? (CombatTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw : Controller->GetControlRotation().Yaw, 0);
    AddMovementInput(Rotation.Vector(), Value);
}
void ACombatCharacter::MoveRight(float Value)
{
    if(!Controller || IsBusy() || FMath::Abs(Value) <= GetLocomotionSettings().InputDeadZone) return;
    const FRotator Rotation(0, bTargetLocked && CombatTarget ? (CombatTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw : Controller->GetControlRotation().Yaw, 0);
    AddMovementInput(FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y), Value);
}
void ACombatCharacter::LookYaw(float Value) { if(!bTargetLocked) AddControllerYawInput(Value * CameraSensitivity); }
void ACombatCharacter::LookPitch(float Value) { if(!bTargetLocked) AddControllerPitchInput(-Value * CameraSensitivity); }
void ACombatCharacter::JumpPressed() { if(IsAlive() && !IsBusy()) Jump(); }
void ACombatCharacter::Landed(const FHitResult& Hit) { Super::Landed(Hit); bAirDashUsed = false; AirComboIndex = 0; AirHangBudgetUsed = AirHangRemaining = 0; }
void ACombatCharacter::AttackPressed()
{
    bAttackHeld = true; AttackPressedAt = GetWorld()->GetTimeSeconds();
    if(ActiveSkill && ActiveSkill->NextSkillTag.IsValid()) { RequestSkillByTag(ActiveSkill->NextSkillTag); return; }
    RequestSkillByInputTag(CT(TEXT("Combat.Input.Attack")));
}
void ACombatCharacter::AttackReleased() { bAttackHeld = false; }
void ACombatCharacter::ParryPressed() { RequestSkillByInputTag(CT(TEXT("Combat.Input.Parry"))); }
void ACombatCharacter::DashPressed() { if(!(GetCharacterMovement()->IsFalling() && bAirDashUsed)) RequestSkillByInputTag(CT(TEXT("Combat.Input.Dash"))); }
void ACombatCharacter::ToggleTargetLock()
{
    bTargetLocked = !bTargetLocked;
    if(bTargetLocked && (!CombatTarget || !CombatTarget->IsAlive()))
    {
        float Best = TNumericLimits<float>::Max();
        for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
            if(It->bIsBoss != bIsBoss && It->IsAlive()) { float Distance = FVector::DistSquared(It->GetActorLocation(), GetActorLocation()); if(Distance < Best) { Best = Distance; CombatTarget = *It; } }
    }
    if(!CombatTarget) bTargetLocked = false;
}
void ACombatCharacter::PausePressed()
{
    const bool bPause = !UGameplayStatics::IsGamePaused(GetWorld());
    if(bPause) { AttackReleased(); StopJumping(); }
    UGameplayStatics::SetGamePaused(GetWorld(), bPause);
}
void ACombatCharacter::EndDashHorizontalOverride()
{
    if(!bDashHorizontalOverride) return;
    auto* Move = GetCharacterMovement();
    Move->Velocity.X = Move->Velocity.Y = 0.f;
    Move->MaxAcceleration = SavedDashMaxAcceleration;
    ConsumeMovementInputVector();
    bDashHorizontalOverride = false;
}
void ACombatCharacter::RetryEncounter()
{
    if(IsAlive() && (!CombatTarget || CombatTarget->IsAlive()))
    {
        if(!UGameplayStatics::IsGamePaused(this))
            if(auto* GameMode = Cast<ACombatGameMode>(UGameplayStatics::GetGameMode(this))) GameMode->SpawnBoss();
        return;
    }
    UGameplayStatics::SetGamePaused(GetWorld(), false);
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) It->ResetCombatState();
}


FVector ACombatCharacter::SampleMovementDirection(bool bForDash) const
{
    const auto* PC = Cast<APlayerController>(Controller);
    if(!PC) return GetLastMovementInputVector();
    const float Forward = (PC->IsInputKeyDown(EKeys::W) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::S) ? 1.f : 0.f);
    const float Right = (PC->IsInputKeyDown(EKeys::D) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::A) ? 1.f : 0.f);
    if(FMath::IsNearlyZero(Forward) && FMath::IsNearlyZero(Right)) return FVector::ZeroVector;
    float BaseYaw = PC->GetControlRotation().Yaw;
    if(bTargetLocked && CombatTarget) BaseYaw = (CombatTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw;
    const float Step = GetLocomotionSettings().DashDirectionStep;
    const float RawYaw = FMath::RadiansToDegrees(FMath::Atan2(Right, Forward));
    const float InputYaw = bForDash ? FMath::RoundToFloat(RawYaw / Step) * Step : RawYaw;
    return FRotator(0, BaseYaw + InputYaw, 0).Vector();
}

void ACombatCharacter::ApplyHitStop(float Duration)
{
    if(Duration <= 0.f) return;
    const float Now = GetWorld()->GetRealTimeSeconds();
    if(HitStopUntilReal <= 0.f) { SavedTimeDilation = CustomTimeDilation; HitStopStartedReal = Now; }
    HitStopUntilReal = FMath::Min(HitStopStartedReal + .085f, FMath::Max(HitStopUntilReal, Now + FMath::Clamp(Duration, .01f, .085f)));
    CustomTimeDilation = FMath::Min(SavedTimeDilation, .035f);
}
void ACombatCharacter::DestroyOwnedProjectiles()
{
    for(TActorIterator<ACombatProjectile> It(GetWorld()); It; ++It) if(It->GetOwner() == this) It->Destroy();
    SkillProjectiles.Reset();
}
void ACombatCharacter::UpdateFootsteps()
{
    const FVector Location = GetActorLocation();
    const float Distance = FVector::Dist2D(Location, PreviousStepLocation); PreviousStepLocation = Location;
    if(GetCharacterMovement()->IsFalling() || IsBusy() || GetVelocity().Size2D() < 100.f) { StepDistanceAccumulator = 0.f; return; }
    StepDistanceAccumulator += FMath::Min(Distance, 100.f);
    if(StepDistanceAccumulator >= FMath::Max(30.f, FootstepDistance) && !FootstepSounds.IsEmpty())
    {
        StepDistanceAccumulator = 0.f;
        if(USoundBase* Sound = FootstepSounds[StepIndex++ % FootstepSounds.Num()]) UGameplayStatics::PlaySoundAtLocation(this, Sound, Location, MasterVolume * .65f);
    }
}
bool ACombatCharacter::CanAssistFacing() const
{
    if(!CombatTarget || !CombatTarget->IsAlive()) return false;
    if(bIsBoss || bTargetLocked) return true;
    const FVector Delta = CombatTarget->GetActorLocation() - GetActorLocation();
    if(Delta.Size2D() > SoftLockRange) return false;
    const FVector ViewForward = Controller ? Controller->GetControlRotation().Vector().GetSafeNormal2D() : GetActorForwardVector();
    if(FVector::DotProduct(ViewForward, Delta.GetSafeNormal2D()) < SoftLockViewDot) return false;
    FHitResult Obstruction; FCollisionQueryParams Params(SCENE_QUERY_STAT(CombatSoftLock), false, this); Params.AddIgnoredActor(CombatTarget);
    return !GetWorld()->LineTraceSingleByChannel(Obstruction, GetActorLocation() + FVector(0,0,30), CombatTarget->GetActorLocation() + FVector(0,0,30), ECC_Visibility, Params);
}
