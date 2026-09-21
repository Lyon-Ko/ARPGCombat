#pragma once
#include "CoreMinimal.h"
#include "Abilities/Tasks/AbilityTask.h"
#include "Abilities/GameplayAbilityTypes.h"
#include "CombatAbilityTask.generated.h"
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FCombatMontageEvent, FGameplayTag, EventTag, FGameplayEventData, EventData);
UCLASS()
class COMBAT_API UCombatAbilityTask_PlayMontageAndEvents : public UAbilityTask
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintAssignable) FCombatMontageEvent OnEvent;
    UPROPERTY(BlueprintAssignable) FCombatMontageEvent OnCompleted;
    UPROPERTY(BlueprintAssignable) FCombatMontageEvent OnInterrupted;
    UFUNCTION(BlueprintCallable, Category="Combat|Ability", meta=(DisplayName="Combat Play Montage And Events", HidePin="OwningAbility", DefaultToSelf="OwningAbility", BlueprintInternalUseOnly="true"))
    static UCombatAbilityTask_PlayMontageAndEvents* PlayMontageAndEvents(UGameplayAbility* OwningAbility, UAnimMontage* Montage, float Rate = 1.f);
    virtual void Activate() override;
protected:
    virtual void OnDestroy(bool bAbilityEnded) override;
private:
    UPROPERTY() TObjectPtr<UAnimMontage> MontageToPlay;
    float PlayRate = 1.f;
    FDelegateHandle EventHandle;
    FDelegateHandle CancelHandle;
    void OnGameplayEvent(FGameplayTag Tag, const FGameplayEventData* Data);
    void OnMontageEnded(UAnimMontage* Montage, bool bInterrupted);
    void OnCancelled();
};
