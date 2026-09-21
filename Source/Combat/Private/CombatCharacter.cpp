#include "CombatCharacter.h"
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

static FGameplayTag CT(const TCHAR* Name) { return FGameplayTag::RequestGameplayTag(FName(Name)); }
ACombatCharacter::ACombatCharacter()
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
    InitialTransform = GetActorTransform();
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
        if(Definition && Definition->InputTag == InputTag && GetSkillCooldownRemaining(Definition->SkillTag) <= 0.f && (Definition->ActivationQuery.IsEmpty() || Definition->ActivationQuery.Matches(OwnedTags)) && (!Definition->bAirOnly || GetCharacterMovement()->IsFalling()) && (Definition->AirAttackIndex == 0 || Definition->AirAttackIndex == AirComboIndex + 1)) Candidates.Add(Definition);
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
    FGameplayTagContainer OwnedTags; AbilitySystem->GetOwnedGameplayTags(OwnedTags);
    if(!Definition->ActivationQuery.IsEmpty() && !Definition->ActivationQuery.Matches(OwnedTags)) return false;
    if(ActiveSkill)
    {
        if(!bCancelable && !bComboWindow && !Definition->bCanInterrupt)
        { BufferedSkill = SkillTag; BufferedUntil = Now + .18f; return false; }
        CancelCurrentSkill();
    }
    return AbilitySystem->TryActivateAbility(*Handle);
}
void ACombatCharacter::BeginSkill(UCombatSkillDefinition* Definition, UCombatGameplayAbility* Ability)
{
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
    if(CombatTarget && CombatTarget->IsAlive())
    {
        FVector ToTarget = CombatTarget->GetActorLocation() - GetActorLocation(); ToTarget.Z = 0;
        if(!ToTarget.IsNearlyZero()) SetActorRotation(ToTarget.Rotation());
        MotionWarping->AddOrUpdateWarpTargetFromLocationAndRotation(TEXT("CombatTarget"), CombatTarget->GetActorLocation() - ToTarget.GetSafeNormal() * 130.f, ToTarget.Rotation());
    }
    const FString Name = Definition->SkillTag.ToString();
    if(Name == TEXT("Combat.Skill.Dash"))
    {
        AbilitySystem->SetLooseGameplayTagCount(CT(TEXT("Combat.State.Dashing")), 1);
        FVector Direction = SampleMovementDirection();
        if(Direction.IsNearlyZero()) Direction = -GetActorForwardVector();
        StartSkillMovement(250.f, .23f, Direction);
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
    if(ActiveAbility) AbilitySystem->CancelAbility(ActiveAbility);
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
    const FGameplayTag OldTag = GetActiveSkillTag();
    GetWorldTimerManager().ClearTimer(SkillTimeout);
    GetWorldTimerManager().ClearTimer(AreaTimer);
    CloseHitWindow(); MovementRemaining = 0; AirHangRemaining = 0;
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
    bHitWindow = true; HitActors.Reset(); ++AttackInstance;
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
FCombatHit ACombatCharacter::MakeHit() const
{
    FCombatHit Hit; Hit.Attacker = const_cast<ACombatCharacter*>(this); Hit.AttackInstance = AttackInstance;
    Hit.Direction = GetActorForwardVector(); Hit.Location = GetActorLocation();
    if(ActiveSkill) { Hit.Damage = ActiveSkill->Damage * (bPhaseTwo ? 1.15f : 1.f); Hit.PoiseDamage = ActiveSkill->PoiseDamage; Hit.bParryable = ActiveSkill->bParryable; }
    return Hit;
}
void ACombatCharacter::TraceHitWindow()
{
    if(!bHitWindow || !ActiveSkill) return;
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
                HitActors.Add(Target); auto Hit = MakeHit(); Hit.Location = Result.ImpactPoint; Hit.Direction = (Target->GetActorLocation() - GetActorLocation()).GetSafeNormal(); Target->ReceiveCombatHit(Hit);
                if(!bHitWindow || !ActiveSkill) return;
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
    if(const int32* Previous = ReceivedAttackIds.Find(Hit.Attacker); Previous && *Previous == Hit.AttackInstance) return ECombatHitResult::Miss;
    ReceivedAttackIds.Add(Hit.Attacker, Hit.AttackInstance);
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
        BroadcastCue(CombatTags::Cue_Parry, Hit.Attacker, Hit.Location, 1.4f);
        return ECombatHitResult::Parried;
    }
    ApplyAttributeDelta(UCombatAttributeSet::GetHealthAttribute(), -FMath::Max(0.f, Hit.Damage));
    if(Now >= PoiseImmuneUntil) ApplyAttributeDelta(UCombatAttributeSet::GetPoiseAttribute(), -FMath::Max(0.f, Hit.PoiseDamage));
    LastDamageAt = Now;
    Hit.Attacker->BroadcastCue(CombatTags::Cue_Hit, this, Hit.Location, Hit.Damage / 20.f);
    if(!IsAlive()) { Die(); return ECombatHitResult::Killed; }
    CheckPoiseBreak(Now);
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
    if(!ActiveSkill) return;
    ++AttackInstance;
    OnProjectileRequested(MakeHit(), ActiveSkill->ProjectileSpeed);
    const FVector Origin = GetActorLocation() + GetActorForwardVector() * 90.f + FVector(0,0,35.f);
    const FVector Direction = CombatTarget && CombatTarget->IsAlive() ? (CombatTarget->GetActorLocation() - Origin).GetSafeNormal() : GetActorForwardVector();
    FActorSpawnParameters Params; Params.Owner = this; Params.Instigator = this; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Projectile = GetWorld()->SpawnActor<ACombatProjectile>(ProjectileClass, Origin, Direction.Rotation(), Params))
    { Projectile->InitializeProjectile(MakeHit(), ActiveSkill->ProjectileSpeed, Direction, ActiveSkill->CastEffect); SkillProjectiles.Add(Projectile); }
}
void ACombatCharacter::ShowAreaWarning()
{
    if(!ActiveSkill) return;
    AreaCenter = GetActorLocation();
    FeedbackComponent->ShowWarning(AreaCenter);
    OnAreaWarningRequested(AreaCenter, ActiveSkill->AreaRadius, ActiveSkill->AreaHeight, ActiveSkill->AreaDelay);
    BroadcastCue(CombatTags::Cue_AreaWarning, this, AreaCenter);
}
void ACombatCharacter::DetonateArea()
{
    if(!ActiveSkill) return;
    BroadcastCue(CombatTags::Cue_AreaRelease, this, AreaCenter, ActiveSkill->AreaRadius);
    FeedbackComponent->ReleaseArea();
    GetWorldTimerManager().SetTimer(AreaTimer, this, &ThisClass::DoAreaDamage, FMath::Max(.001f, ActiveSkill->AreaDelay), false);
}
void ACombatCharacter::DoAreaDamage()
{
    if(!ActiveSkill || !IsAlive()) return;
    ++AttackInstance;
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
    {
        auto* Target = *It;
        const FVector Delta = Target->GetActorLocation() - AreaCenter;
        if(Target != this && Target->bIsBoss != bIsBoss && Delta.Size2D() <= ActiveSkill->AreaRadius + Target->GetCapsuleComponent()->GetScaledCapsuleRadius() && FMath::Abs(Delta.Z) <= ActiveSkill->AreaHeight * .5f + Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())
        { auto Hit = MakeHit(); Hit.Location = Target->GetActorLocation(); Hit.Direction = Delta.GetSafeNormal(); Target->ReceiveCombatHit(Hit); }
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
    CancelCurrentSkill(); AbilitySystem->CancelAllAbilities();
    AbilitySystem->RemoveActiveGameplayEffect(RiposteEffectHandle);
    for(auto Projectile : SkillProjectiles) if(Projectile.IsValid()) Projectile->Destroy();
    SkillProjectiles.Reset();
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_Dead, 1);
    AbilitySystem->SetLooseGameplayTagCount(CombatTags::State_RiposteReady, 0);
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    BroadcastCue(CombatTags::Cue_Death, this, GetActorLocation(), 2.f); OnCombatDeath.Broadcast(this);
}
void ACombatCharacter::ResetCombatState()
{
    CancelCurrentSkill(); AbilitySystem->CancelAllAbilities();
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
    if(auto* AI = Cast<ACombatAIController>(Controller)) AI->ResetBrain();
}
void ACombatCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!IsAlive()) return;
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
        const float Step = FMath::Min(DeltaSeconds, MovementRemaining);
        FHitResult Hit; AddActorWorldOffset(MovementDirection * MovementSpeed * Step, true, &Hit);
        MovementRemaining -= Step;
        if(Hit.bBlockingHit) MovementRemaining = 0;
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
            MoveForward((PC->IsInputKeyDown(EKeys::W) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::S) ? 1.f : 0.f));
            MoveRight((PC->IsInputKeyDown(EKeys::D) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::A) ? 1.f : 0.f));
            if(bTargetLocked && CombatTarget && CombatTarget->IsAlive())
            {
                const FVector Midpoint = FMath::Lerp(GetActorLocation(), CombatTarget->GetActorLocation(), .4f);
                FRotator Desired = (Midpoint - Camera->GetComponentLocation()).Rotation(); Desired.Pitch = FMath::Clamp(Desired.Pitch, -35.f, -8.f);
                PC->SetControlRotation(FMath::RInterpTo(PC->GetControlRotation(), Desired, DeltaSeconds, 4.f));
                CameraBoom->TargetArmLength = FMath::FInterpTo(CameraBoom->TargetArmLength, FMath::Clamp(FVector::Dist2D(GetActorLocation(), CombatTarget->GetActorLocation()) * .65f + 400.f, 550.f, 1000.f), DeltaSeconds, 3.f);
            }
            if(bAttackHeld && bAir && Now - AttackPressedAt > .28f) { bAttackHeld = false; RequestSkillByTag(CT(TEXT("Combat.Skill.Plunge"))); }
        }
    }
}
void ACombatCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxisKey(EKeys::MouseX, this, &ThisClass::LookYaw);
    Input->BindAxisKey(EKeys::MouseY, this, &ThisClass::LookPitch);
    Input->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &ThisClass::AttackPressed);
    Input->BindKey(EKeys::LeftMouseButton, IE_Released, this, &ThisClass::AttackReleased);
    Input->BindKey(EKeys::RightMouseButton, IE_Pressed, this, &ThisClass::ParryPressed);
    Input->BindKey(EKeys::LeftShift, IE_Pressed, this, &ThisClass::DashPressed);
    Input->BindKey(EKeys::SpaceBar, IE_Pressed, this, &ThisClass::JumpPressed);
    Input->BindKey(EKeys::SpaceBar, IE_Released, this, &ACharacter::StopJumping);
    Input->BindKey(EKeys::Q, IE_Pressed, this, &ThisClass::ToggleTargetLock);
    Input->BindKey(EKeys::P, IE_Pressed, this, &ThisClass::PausePressed).bExecuteWhenPaused = true;
    Input->BindKey(EKeys::R, IE_Pressed, this, &ThisClass::RetryEncounter).bExecuteWhenPaused = true;
}
void ACombatCharacter::MoveForward(float Value)
{
    if(!Controller || IsBusy() || Value == 0.f) return;
    const FRotator Rotation(0, bTargetLocked && CombatTarget ? (CombatTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw : Controller->GetControlRotation().Yaw, 0);
    AddMovementInput(Rotation.Vector(), Value);
}
void ACombatCharacter::MoveRight(float Value)
{
    if(!Controller || IsBusy() || Value == 0.f) return;
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
void ACombatCharacter::PausePressed() { UGameplayStatics::SetGamePaused(GetWorld(), !UGameplayStatics::IsGamePaused(GetWorld())); }
void ACombatCharacter::RetryEncounter()
{
    if(IsAlive() && (!CombatTarget || CombatTarget->IsAlive())) return;
    UGameplayStatics::SetGamePaused(GetWorld(), false);
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It) It->ResetCombatState();
}


FVector ACombatCharacter::SampleMovementDirection() const
{
    const auto* PC = Cast<APlayerController>(Controller);
    if(!PC) return GetLastMovementInputVector();
    const float Forward = (PC->IsInputKeyDown(EKeys::W) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::S) ? 1.f : 0.f);
    const float Right = (PC->IsInputKeyDown(EKeys::D) ? 1.f : 0.f) - (PC->IsInputKeyDown(EKeys::A) ? 1.f : 0.f);
    if(FMath::IsNearlyZero(Forward) && FMath::IsNearlyZero(Right)) return FVector::ZeroVector;
    float BaseYaw = PC->GetControlRotation().Yaw;
    if(bTargetLocked && CombatTarget) BaseYaw = (CombatTarget->GetActorLocation() - GetActorLocation()).Rotation().Yaw;
    const float InputYaw = FMath::RoundToFloat(FMath::RadiansToDegrees(FMath::Atan2(Right, Forward)) / 45.f) * 45.f;
    return FRotator(0, BaseYaw + InputYaw, 0).Vector();
}
