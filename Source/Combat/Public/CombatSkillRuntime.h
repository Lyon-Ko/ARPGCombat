#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayEffect.h"
#include "CombatTypes.h"
#include "CombatSkillRuntime.generated.h"
class ACombatCharacter;

USTRUCT()
struct FCombatBuffInstance
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UCombatBuffDefinition> Definition;
    UPROPERTY() TObjectPtr<UGameplayEffect> Effect;
    UPROPERTY() TWeakObjectPtr<ACombatCharacter> Source;
    UPROPERTY() int32 Stacks = 1;
    FActiveGameplayEffectHandle Handle;
    uint64 Scope = 0;
    float Expires = 0;
    float NextPeriod = 0;
};

/** Local-only authoring runtime; all callbacks are bound to an execution serial. */
UCLASS(ClassGroup=Combat, meta=(BlueprintSpawnableComponent))
class COMBAT_API UCombatSkillRuntime : public UActorComponent
{
    GENERATED_BODY()
public:
    UCombatSkillRuntime();
    void Start(UCombatSkillDefinition* Definition);
    void Stop(bool bInterrupted);
    void Advance(float DeltaSeconds);
    void CompleteAnimation();
    bool UsesMontageNotifies() const;
    bool AcceptMontageNotify(UAnimMontage* Montage,int32 InstanceId) const;
    void BindMontageInstance(int32 InstanceId) { MontageInstanceId=InstanceId; }
    void ExecuteMontageAction(const FCombatSkillEvent& Action);
    void BeginMontageWindow(const UObject* Key,ECombatSkillWindowType Type,FName Name);
    void EndMontageWindow(const UObject* Key);
    UFUNCTION(BlueprintPure, Category="Combat|Montage") bool IsMontageWindowOpen(FName Name) const;
    void NotifyHit(uint64 ExpectedSerial);
    bool TryDerive(ECombatDerivationTrigger Trigger, FGameplayTag Input = FGameplayTag());
    bool CanInterrupt(ECombatInterruptReason Reason, const UCombatSkillDefinition* Incoming = nullptr) const;
    UFUNCTION(BlueprintCallable, Category="Combat|Buff") void AddBuff(UCombatBuffDefinition* Definition, ACombatCharacter* Source, bool bSkillScoped = false);
    UFUNCTION(BlueprintCallable, Category="Combat|Buff") void RemoveBuff(UCombatBuffDefinition* Definition);
    UFUNCTION(BlueprintCallable, Category="Combat|Buff") void ClearBuffs();
    UFUNCTION(BlueprintPure, Category="Combat|Buff") int32 GetBuffStacks(UCombatBuffDefinition* Definition) const;
    bool HasSuperArmor() const;
    UFUNCTION(BlueprintPure, Category="Combat|Editor") TArray<FString> GetDebugLog() const { return DebugLog; }
    void Log(const FString& Message);
    uint64 GetSerial() const { return Serial; }
    float GetTime() const { return Time; }
    bool IsRunning() const { return Running != nullptr; }
    bool HasPendingDerivation() const { return PendingCompletion != nullptr; }
    bool IsDeriving() const { return bDeriving; }
    UPROPERTY(BlueprintReadOnly, Category="Combat") ECombatSkillRequestResult LastRequest = ECombatSkillRequestResult::MissingSkill;
private:
    UPROPERTY() TObjectPtr<UCombatSkillDefinition> Running;
    UPROPERTY() TObjectPtr<UCombatSkillDefinition> PendingCompletion;
    UPROPERTY() TArray<FCombatBuffInstance> Buffs;
    UPROPERTY() TArray<FString> DebugLog;
    TSet<FGuid> Fired;
    TMap<FGuid, int32> BurstCounts;
    struct FWindow { ECombatSkillWindowType Type; FName Name; };
    TMap<const UObject*,FWindow> MontageWindows;
    struct FBurst { FCombatSkillEvent Event; float Started; int32 Fired=0; };
    TArray<FBurst> MontageBursts;
    float MontageClock=0;
    int32 MontageInstanceId=INDEX_NONE;
    void UpdateMontageWindows();
    void PollBufferedDerivation();
    uint64 Serial = 0;
    float Time = 0.f;
    bool bHitConfirmed = false;
    bool bDeriving = false;
    bool bPollingBufferedInput = false;
    int32 AutomaticChain = 0;
    FGameplayTag BufferedInput;
    float BufferedInputUntil = 0;
    void Execute(const FCombatSkillEvent& Event);
    void Fire(const FCombatSkillEvent& Event, int32 Burst);
    void RefreshEffect(FCombatBuffInstance& Instance);
    void TickBuffs();
    void TickHealth(const FCombatBuffInstance& Instance);
    ACombatCharacter* Character() const;
};
