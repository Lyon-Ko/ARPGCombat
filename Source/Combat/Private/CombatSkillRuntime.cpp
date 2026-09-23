#include "CombatSkillRuntime.h"
#include "CombatCharacter.h"
#include "CombatAttributeSet.h"
#include "CombatProjectile.h"
#include "CombatLocomotionSettings.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"
#include "EngineUtils.h"
#include "NiagaraFunctionLibrary.h"
#include "Kismet/GameplayStatics.h"

UCombatSkillRuntime::UCombatSkillRuntime() { PrimaryComponentTick.bCanEverTick = false; }
ACombatCharacter* UCombatSkillRuntime::Character() const { return Cast<ACombatCharacter>(GetOwner()); }
void UCombatSkillRuntime::Log(const FString& Message)
{
    DebugLog.Add(FString::Printf(TEXT("%.3f %s"), GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f, *Message));
    if(DebugLog.Num() > 200) DebugLog.RemoveAt(0, DebugLog.Num() - 200);
    UE_LOG(LogTemp, Verbose, TEXT("SkillRuntime %s: %s"), *GetNameSafe(GetOwner()), *Message);
}
void UCombatSkillRuntime::Start(UCombatSkillDefinition* Definition)
{
    ++Serial; Running = Definition; PendingCompletion = nullptr; Time = 0; bHitConfirmed = false; Fired.Reset(); BurstCounts.Reset(); BufferedInput = FGameplayTag();
    MontageWindows.Reset(); MontageBursts.Reset(); MontageClock=0; MontageInstanceId=INDEX_NONE;
    if(!bDeriving) AutomaticChain = 0;
    Log(TEXT("Start ") + Definition->SkillTag.ToString());
}
void UCombatSkillRuntime::Stop(bool bInterrupted)
{
    auto* C = Character();
    UCombatSkillDefinition* Previous = Running;
    const uint64 OldSerial = Serial;
    Running = nullptr; Fired.Reset(); BurstCounts.Reset(); BufferedInput = FGameplayTag();
    MontageWindows.Reset(); MontageBursts.Reset();
    // Scope belongs to the source execution, including effects placed on another actor.
    for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
    {
        auto* Runtime = It->SkillRuntime.Get();
        for(int32 Index = Runtime->Buffs.Num()-1; Index >= 0; --Index)
        {
            const auto& B = Runtime->Buffs[Index];
            if(B.Scope != 0 && B.Scope == OldSerial && B.Source == C)
            { It->AbilitySystem->RemoveActiveGameplayEffect(B.Handle); Runtime->Buffs.RemoveAt(Index); }
        }
    }
    Log(bInterrupted ? TEXT("Interrupted") : TEXT("Completed"));
    PendingCompletion = !bInterrupted && Previous && Previous->bDataDriven && C->IsAlive() ? Previous : nullptr;
    if(PendingCompletion) Time = FMath::Min(Time,PendingCompletion->Duration);
}
bool UCombatSkillRuntime::CanInterrupt(ECombatInterruptReason Reason, const UCombatSkillDefinition* Incoming) const
{
    if(Reason == ECombatInterruptReason::Death || Reason == ECombatInterruptReason::Reset) return true;
    if(Reason == ECombatInterruptReason::Hit && HasSuperArmor()) return false;
    const auto* Active = Character()->GetActiveSkillDefinition();
    if(!Active || !Active->bDataDriven) return true;
    if(!Active->AllowedInterrupts.Contains(Reason)) return false;
    return Reason != ECombatInterruptReason::Skill || !Incoming || Incoming->InterruptPriority >= Active->InterruptResistance;
}
bool UCombatSkillRuntime::TryDerive(ECombatDerivationTrigger Trigger, FGameplayTag Input)
{
    if(!Running || !Running->bDataDriven) return false;
    auto* C = Character();
    if(Trigger != ECombatDerivationTrigger::Input && AutomaticChain >= 16) { Log(TEXT("Automatic chain limit")); return false; }
    TArray<FCombatSkillDerivation> Candidates = Running->Derivations;
    Candidates.StableSort([](const auto& A, const auto& B) { return A.Priority > B.Priority; });
    FGameplayTagContainer Owned; C->AbilitySystem->GetOwnedGameplayTags(Owned);
    for(const auto& Rule : Candidates)
    {
        if(Rule.Trigger != Trigger || (Trigger == ECombatDerivationTrigger::Input && Rule.InputTag != Input)) continue;
        if((Rule.bRequireHit && !bHitConfirmed) || (!Rule.Conditions.IsEmpty() && !Rule.Conditions.Matches(Owned))) continue;
        const bool Air = C->GetCharacterMovement()->IsFalling();
        if((Rule.bGroundOnly && Air) || (Rule.bAirOnly && !Air)) continue;
        const bool Native=UsesMontageNotifies();
        const bool InWindow=Native ? (Rule.WindowName.IsNone() || IsMontageWindowOpen(Rule.WindowName)) : Time>=Rule.WindowStart && Time<=Rule.WindowEnd;
        if(!InWindow)
        {
            if(Trigger == ECombatDerivationTrigger::Input && (Native || Time < Rule.WindowStart) && !bPollingBufferedInput)
            { BufferedInput = Input; BufferedInputUntil = GetWorld()->GetTimeSeconds() + C->GetLocomotionSettings().InputBufferTime; }
            continue;
        }
        bDeriving = true;
        if(Trigger == ECombatDerivationTrigger::Input) AutomaticChain = 0; else ++AutomaticChain;
        const bool Activated = C->RequestSkillByTag(Rule.TargetSkill);
        bDeriving = false;
        if(Activated) { Log(TEXT("Derived -> ") + Rule.TargetSkill.ToString()); return true; }
    }
    return false;
}
void UCombatSkillRuntime::NotifyHit(uint64 ExpectedSerial) { if(ExpectedSerial != Serial || !Running) return; bHitConfirmed = true; TryDerive(ECombatDerivationTrigger::Hit); }
void UCombatSkillRuntime::CompleteAnimation()
{
    if(Running && Running->bDataDriven && Running->Montage && !UsesMontageNotifies()) { Time=Running->Montage->GetPlayLength(); Advance(0.f); }
}
bool UCombatSkillRuntime::UsesMontageNotifies() const { return Running && Running->bDataDriven && Running->bUseMontageNotifies && Running->Montage; }
bool UCombatSkillRuntime::AcceptMontageNotify(UAnimMontage* Montage,int32 InstanceId) const
{
    if(!UsesMontageNotifies() || Running->Montage!=Montage || !Character()->IsAlive()) return false;
    auto* Anim=Character()->GetMesh()->GetAnimInstance();
    const auto* Instance=Anim?Anim->GetMontageInstanceForID(InstanceId):nullptr;
    // UE clears Instance->Montage in Terminate before dispatching the last queued
    // notifies. The bound instance ID and payload asset still identify this execution.
    return Instance && InstanceId==MontageInstanceId && (!Instance->Montage || Instance->Montage==Montage);
}
void UCombatSkillRuntime::ExecuteMontageAction(const FCombatSkillEvent& Action)
{
    if(!UsesMontageNotifies()) return;
    // Window ownership belongs exclusively to AnimNotifyState, never a point action.
    if(Action.Type==ECombatSkillEventType::HitWindow || Action.Type==ECombatSkillEventType::ComboWindow || Action.Type==ECombatSkillEventType::CancelWindow) return;
    const uint64 Execution=Serial;
    Execute(Action);
    if(Serial!=Execution || !UsesMontageNotifies()) return;
    if(Action.Type==ECombatSkillEventType::Projectile)
    {
        if(Action.Bursts>1) { FBurst B; B.Event=Action; B.Started=MontageClock; B.Fired=1; MontageBursts.Add(B); }
        Fire(Action,0);
    }
}
bool UCombatSkillRuntime::IsMontageWindowOpen(FName Name) const
{
    for(const auto& Entry:MontageWindows) if(Entry.Value.Type==ECombatSkillWindowType::Derivation && Entry.Value.Name==Name) return true;
    return false;
}
void UCombatSkillRuntime::UpdateMontageWindows()
{
    bool Hit=false,Cancel=false;
    for(const auto& Entry:MontageWindows) { Hit|=Entry.Value.Type==ECombatSkillWindowType::Hit; Cancel|=Entry.Value.Type==ECombatSkillWindowType::Cancel; }
    if(!Hit) Character()->CloseHitWindow();
    Character()->SetCancelable(Cancel);
    // Only an actually selected graph rule may bypass the generic cancel gate.
    Character()->SetComboWindow(false);
}
void UCombatSkillRuntime::BeginMontageWindow(const UObject* Key,ECombatSkillWindowType Type,FName Name)
{
    if(!UsesMontageNotifies() || MontageWindows.Contains(Key)) return;
    const uint64 Execution=Serial;
    MontageWindows.Add(Key,FWindow{Type,Name});
    if(Type==ECombatSkillWindowType::Hit) { Character()->OpenHitWindow(); Character()->SampleSkillHit(); }
    if(Serial!=Execution || !UsesMontageNotifies()) return;
    UpdateMontageWindows(); PollBufferedDerivation();
}
void UCombatSkillRuntime::EndMontageWindow(const UObject* Key)
{
    if(!UsesMontageNotifies()) return;
    auto* Anim=Character()->GetMesh()->GetAnimInstance();
    const auto* Instance=Anim?Anim->GetMontageInstanceForID(MontageInstanceId):nullptr;
    if(Instance && Instance->Montage && !Instance->IsPlaying())
    {
        const float Position=Instance->GetPosition();
        for(const auto& N:Running->Montage->Notifies)
            if(N.NotifyStateClass==Key && Position>=N.GetTriggerTime() && Position<N.GetEndTriggerTime()) return;
    }
    const uint64 Execution=Serial;
    if(const auto* Window=MontageWindows.Find(Key); Window && Window->Type==ECombatSkillWindowType::Hit) Character()->SampleSkillHit();
    if(Serial!=Execution || !UsesMontageNotifies()) return;
    MontageWindows.Remove(Key); UpdateMontageWindows();
}
void UCombatSkillRuntime::PollBufferedDerivation()
{
    if(!BufferedInput.IsValid()) return;
    if(GetWorld()->GetTimeSeconds()>BufferedInputUntil) BufferedInput=FGameplayTag();
    else { TGuardValue<bool> Polling(bPollingBufferedInput,true); TryDerive(ECombatDerivationTrigger::Input,BufferedInput); }
}
void UCombatSkillRuntime::Advance(float DeltaSeconds)
{
    if(PendingCompletion)
    {
        const uint64 PreviousSerial = Serial;
        Running = PendingCompletion; PendingCompletion = nullptr;
        TryDerive(ECombatDerivationTrigger::Completed);
        if(Serial == PreviousSerial) Running = nullptr;
    }
    TickBuffs();
    auto* C = Character();
    if(!Running || !Running->bDataDriven || !C->IsAlive()) return;
    const uint64 ThisSerial = Serial;
    if(UsesMontageNotifies())
    {
        if(auto* Anim=C->GetMesh()->GetAnimInstance())
        {
            if(auto* Instance=Anim->GetMontageInstanceForID(MontageInstanceId))
            {
                Time=Instance->GetPosition();
                if(Instance->IsPlaying()) MontageClock+=DeltaSeconds*FMath::Abs(Instance->GetPlayRate()*Running->Montage->RateScale);
            }
            else if(MontageInstanceId!=INDEX_NONE) { C->CancelCurrentSkill(); return; }
        }
        // Pausing may end UE's queued state notifications; retain logical windows
        // at the paused pose, but close known windows after seeks out of their range.
        for(auto It=MontageWindows.CreateIterator();It;++It)
        {
            bool InRange=false;
            for(const auto& N:Running->Montage->Notifies) if(N.NotifyStateClass==It.Key() && Time>=N.GetTriggerTime() && Time<N.GetEndTriggerTime()) { InRange=true; break; }
            if(!InRange) It.RemoveCurrent();
        }
        UpdateMontageWindows();
        for(int32 I=0;I<MontageBursts.Num();++I)
        {
            while(MontageBursts[I].Fired<FMath::Clamp(MontageBursts[I].Event.Bursts,1,64) && MontageClock>=MontageBursts[I].Started+MontageBursts[I].Fired*FMath::Max(.01f,MontageBursts[I].Event.BurstInterval))
            {
                const FCombatSkillEvent Event=MontageBursts[I].Event;
                const int32 Burst=MontageBursts[I].Fired++;
                Fire(Event,Burst); if(Serial!=ThisSerial || !UsesMontageNotifies()) return;
            }
        }
        MontageBursts.RemoveAll([](const FBurst& B){return B.Fired>=FMath::Clamp(B.Event.Bursts,1,64);});
        PollBufferedDerivation(); return;
    }
    if(Running->Montage && C->GetMesh()->GetAnimInstance())
        Time = FMath::Max(Time, C->GetMesh()->GetAnimInstance()->Montage_GetPosition(Running->Montage));
    else Time += DeltaSeconds;
    TArray<FCombatSkillEvent> Events = Running->Events;
    Events.StableSort([](const auto& A, const auto& B) { return A.Time < B.Time; });
    bool HitWindow = false, CancelWindow = false, ComboWindow = false;
    for(const auto& E : Events)
    {
        const bool InWindow = Time >= E.Time && Time < E.Time + E.Duration;
        HitWindow |= InWindow && E.Type == ECombatSkillEventType::HitWindow;
        CancelWindow |= InWindow && E.Type == ECombatSkillEventType::CancelWindow;
        ComboWindow |= InWindow && E.Type == ECombatSkillEventType::ComboWindow;
        if(Time >= E.Time && !Fired.Contains(E.Id)) { Fired.Add(E.Id); Execute(E); }
        if(Serial != ThisSerial || !Running) return;
        if(E.Type == ECombatSkillEventType::Projectile && Time >= E.Time)
        {
            int32& Count = BurstCounts.FindOrAdd(E.Id);
            while(Count < FMath::Clamp(E.Bursts,1,64) && Time >= E.Time + Count * FMath::Max(.01f,E.BurstInterval))
            {
                const int32 Burst = Count++;
                Fire(E, Burst);
                if(Serial != ThisSerial || !Running) return;
            }
        }
    }
    if(!HitWindow) { C->SampleSkillHit(); if(Serial != ThisSerial || !Running) return; C->CloseHitWindow(); }
    C->SetCancelable(CancelWindow); C->SetComboWindow(ComboWindow);
    if(BufferedInput.IsValid())
    {
        if(GetWorld()->GetTimeSeconds() > BufferedInputUntil) BufferedInput = FGameplayTag();
        else { TGuardValue<bool> Polling(bPollingBufferedInput,true); if(TryDerive(ECombatDerivationTrigger::Input, BufferedInput)) return; }
    }
    if(!Running->Montage && Time >= Running->Duration) C->FinishSkill();
}
void UCombatSkillRuntime::Execute(const FCombatSkillEvent& E)
{
    auto* C = Character();
    Log(FString::Printf(TEXT("Event %s [%d]"), *E.Label, int32(E.Type)));
    switch(E.Type)
    {
    case ECombatSkillEventType::HitWindow:
    { const uint64 Execution=Serial; C->SampleSkillHit(); if(Serial==Execution && Running) { C->OpenHitWindow(); C->SampleSkillHit(); } break; }
    case ECombatSkillEventType::Movement: C->StartSkillMovement(E.Distance, E.Duration, C->GetActorTransform().TransformVectorNoScale(E.Direction)); break;
    case ECombatSkillEventType::AreaWarning: C->ShowAreaWarning(); break;
    case ECombatSkillEventType::AreaRelease: C->DetonateArea(); break;
    case ECombatSkillEventType::ApplyBuff:
    case ECombatSkillEventType::RemoveBuff:
        for(TActorIterator<ACombatCharacter> It(GetWorld()); It; ++It)
        {
            const bool Selected = E.BuffTarget == ECombatBuffTarget::Self ? *It == C : E.BuffTarget == ECombatBuffTarget::Target ? *It == C->CombatTarget : FVector::DistSquared(It->GetActorLocation(), C->GetActorLocation()) <= FMath::Square(E.Radius) && It->bIsBoss != C->bIsBoss;
            if(!Selected || !It->IsAlive()) continue;
            if(E.Type == ECombatSkillEventType::ApplyBuff) It->SkillRuntime->AddBuff(E.Buff, C, E.bSkillScoped);
            else It->SkillRuntime->RemoveBuff(E.Buff);
        }
        break;
    case ECombatSkillEventType::Effect:
        if(E.Effect) UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(), E.Effect, C->GetActorLocation());
        if(E.Sound) UGameplayStatics::PlaySoundAtLocation(C, E.Sound, C->GetActorLocation());
        break;
    case ECombatSkillEventType::Finish: C->FinishSkill(); break;
    default: break;
    }
}
void UCombatSkillRuntime::Fire(const FCombatSkillEvent& E, int32 Burst)
{
    auto* C = Character(); if(!E.Projectile) return;
    const uint64 ThisSerial = Serial;
    const FTransform Transform = E.Socket.IsNone() ? C->GetActorTransform() : C->GetMesh()->GetSocketTransform(E.Socket);
    const FVector Origin = Transform.TransformPosition(E.Offset);
    FVector Forward = C->GetActorForwardVector();
    if(E.bAimAtTarget && C->CombatTarget && C->CombatTarget->IsAlive()) Forward = (C->CombatTarget->GetActorLocation() - Origin).GetSafeNormal();
    FRandomStream Random(E.Seed + Burst);
    const int32 Count = E.Pattern == ECombatFirePattern::Single ? 1 : FMath::Clamp(E.Count,1,128);
    for(int32 Index = 0; Index < Count; ++Index)
    {
        FVector Direction = Forward;
        if(E.Pattern == ECombatFirePattern::Scatter) Direction = Random.VRandCone(Forward, FMath::DegreesToRadians(E.SpreadDegrees * .5f));
        else if(Count > 1) Direction = Forward.RotateAngleAxis(E.Pattern == ECombatFirePattern::Ring ? Index * 360.f / Count : -E.SpreadDegrees*.5f + Index * E.SpreadDegrees/(Count-1), FVector::UpVector);
        FTransform SpawnTransform(Direction.Rotation(), Origin);
        auto* P = GetWorld()->SpawnActorDeferred<ACombatProjectile>(C->ProjectileClass, SpawnTransform, C, C, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!P) continue;
        P->InitializeDefinition(E.Projectile, C, C->CombatTarget, Direction, ThisSerial);
        P->FinishSpawning(SpawnTransform);
        if(Serial != ThisSerial || !Running) { P->Destroy(); return; }
        P->ActivateDefinition();
    }
}
void UCombatSkillRuntime::RefreshEffect(FCombatBuffInstance& B)
{
    auto* ASC = Character()->AbilitySystem.Get();
    ASC->RemoveActiveGameplayEffect(B.Handle);
    B.Effect = NewObject<UGameplayEffect>(this);
    B.Effect->DurationPolicy = EGameplayEffectDurationType::Infinite;
    auto Add = [&](FGameplayAttribute Attribute, float Value, EGameplayModOp::Type Op)
    { auto& M = B.Effect->Modifiers.AddDefaulted_GetRef(); M.Attribute = Attribute; M.ModifierOp = Op; M.ModifierMagnitude = FScalableFloat(Value); };
    Add(UCombatAttributeSet::GetDamageMultiplierAttribute(), FMath::Pow(B.Definition->DamageMultiplier,B.Stacks), EGameplayModOp::Multiplicitive);
    Add(UCombatAttributeSet::GetMoveSpeedMultiplierAttribute(), FMath::Pow(B.Definition->MoveSpeedMultiplier,B.Stacks), EGameplayModOp::Multiplicitive);
    Add(UCombatAttributeSet::GetMaxHealthAttribute(), B.Definition->MaxHealthAdd * B.Stacks, EGameplayModOp::Additive);
    Add(UCombatAttributeSet::GetMaxPoiseAttribute(), B.Definition->MaxPoiseAdd * B.Stacks, EGameplayModOp::Additive);
    for(const auto& Modifier:B.Definition->AttributeModifiers) if(Modifier.Attribute.IsValid())
    { Add(Modifier.Attribute,Modifier.Additive*B.Stacks,EGameplayModOp::Additive); Add(Modifier.Attribute,FMath::Pow(Modifier.Multiplier,B.Stacks),EGameplayModOp::Multiplicitive); }
    FInheritedTagContainer Tags;
    for(const auto& Tag : B.Definition->GrantedTags) Tags.AddTag(Tag);
    if(B.Definition->BuffTag.IsValid()) Tags.AddTag(B.Definition->BuffTag);
    B.Effect->FindOrAddComponent<UTargetTagsGameplayEffectComponent>().SetAndApplyTargetTagChanges(Tags);
    auto Context = ASC->MakeEffectContext(); Context.AddInstigator(B.Source.Get(), B.Source.Get());
    B.Handle = ASC->ApplyGameplayEffectToSelf(B.Effect, 1.f, Context);
}
void UCombatSkillRuntime::AddBuff(UCombatBuffDefinition* D, ACombatCharacter* Source, bool bSkillScoped)
{
    if(!D || !Character()->IsAlive()) return;
    if(!Source) Source = Character();
    if(bSkillScoped && !Source->SkillRuntime->IsRunning()) return;
    if(D->bInterruptOnApply && !Character()->TryInterruptSkill(ECombatInterruptReason::Control)) return;
    if(bSkillScoped && !Source->SkillRuntime->IsRunning()) return;
    if(D->Lifetime == ECombatBuffLifetime::Instant)
    {
        auto* Effect=NewObject<UGameplayEffect>(this); Effect->DurationPolicy=EGameplayEffectDurationType::Instant;
        for(const auto& Modifier:D->AttributeModifiers) if(Modifier.Attribute.IsValid())
        {
            auto& Add=Effect->Modifiers.AddDefaulted_GetRef(); Add.Attribute=Modifier.Attribute; Add.ModifierOp=EGameplayModOp::Additive; Add.ModifierMagnitude=FScalableFloat(Modifier.Additive);
            auto& Multiply=Effect->Modifiers.AddDefaulted_GetRef(); Multiply.Attribute=Modifier.Attribute; Multiply.ModifierOp=EGameplayModOp::Multiplicitive; Multiply.ModifierMagnitude=FScalableFloat(Modifier.Multiplier);
        }
        auto Context=Character()->AbilitySystem->MakeEffectContext(); Context.AddInstigator(Source,Source);
        Character()->AbilitySystem->ApplyGameplayEffectToSelf(Effect,1.f,Context);
        FCombatBuffInstance B; B.Definition = D; B.Source = Source; TickHealth(B); return;
    }
    const uint64 Scope = bSkillScoped ? Source->SkillRuntime->Serial : 0;
    FCombatBuffInstance* B = Buffs.FindByPredicate([&](const auto& I) { return I.Definition == D && I.Scope == Scope && (!D->bSeparateSources || I.Source == Source) && (!Scope || I.Source == Source); });
    const float Now = GetWorld()->GetTimeSeconds();
    if(!B) { B = &Buffs.AddDefaulted_GetRef(); B->Definition = D; B->Source = Source; B->Scope = Scope; B->Expires = Now + D->Duration; B->NextPeriod = Now + FMath::Max(.01f,D->Period); }
    else { B->Stacks = FMath::Min(B->Stacks+1,FMath::Max(1,D->MaxStacks)); if(D->bRefreshDuration) B->Expires = Now + D->Duration; if(D->bResetPeriod) B->NextPeriod = Now + FMath::Max(.01f,D->Period); }
    RefreshEffect(*B); Log(TEXT("Buff + ") + D->GetName());
}
void UCombatSkillRuntime::RemoveBuff(UCombatBuffDefinition* D)
{
    for(int32 I=Buffs.Num()-1; I>=0; --I) if(Buffs[I].Definition == D)
    { Character()->AbilitySystem->RemoveActiveGameplayEffect(Buffs[I].Handle); Buffs.RemoveAt(I); }
}
void UCombatSkillRuntime::ClearBuffs()
{
    for(auto& B : Buffs) Character()->AbilitySystem->RemoveActiveGameplayEffect(B.Handle);
    Buffs.Reset();
}
int32 UCombatSkillRuntime::GetBuffStacks(UCombatBuffDefinition* D) const
{ int32 Count = 0; for(const auto& B : Buffs) if(B.Definition == D) Count += B.Stacks; return Count; }
bool UCombatSkillRuntime::HasSuperArmor() const
{ for(const auto& B : Buffs) if(B.Definition->bSuperArmor) return true; return false; }
void UCombatSkillRuntime::TickHealth(const FCombatBuffInstance& B)
{
    auto* C = Character(); const float Value = B.Definition->HealthPerPeriod * B.Stacks;
    if(Value < 0) C->ApplyPeriodicDamage(-Value, B.Source.Get());
    else if(Value > 0)
    {
        auto* Effect = NewObject<UGameplayEffect>(this); Effect->DurationPolicy = EGameplayEffectDurationType::Instant;
        auto& M = Effect->Modifiers.AddDefaulted_GetRef(); M.Attribute = UCombatAttributeSet::GetHealthAttribute(); M.ModifierOp = EGameplayModOp::Additive; M.ModifierMagnitude = FScalableFloat(Value);
        C->AbilitySystem->ApplyGameplayEffectToSelf(Effect, 1.f, C->AbilitySystem->MakeEffectContext());
    }
}
void UCombatSkillRuntime::TickBuffs()
{
    const float Now = GetWorld()->GetTimeSeconds();
    // Copy work items: a periodic death clears the live array synchronously.
    TArray<FCombatBuffInstance> Ticks;
    for(int32 I = Buffs.Num()-1; I >= 0; --I)
    {
        auto& B = Buffs[I];
        const float End = B.Definition->Lifetime == ECombatBuffLifetime::Timed ? FMath::Min(Now,B.Expires) : Now;
        int32 Safety = 0;
        while(B.NextPeriod <= End && Safety++ < 128)
        { Ticks.Add(B); B.NextPeriod += FMath::Max(.01f,B.Definition->Period); }
        if(B.Definition->Lifetime == ECombatBuffLifetime::Timed && Now >= B.Expires)
        { Character()->AbilitySystem->RemoveActiveGameplayEffect(B.Handle); Buffs.RemoveAt(I); }
    }
    for(const auto& B : Ticks) { if(!Character()->IsAlive()) break; TickHealth(B); }
}
