#pragma once
#include "CoreMinimal.h"
#include "AttributeSet.h"
#include "AbilitySystemComponent.h"
#include "CombatAttributeSet.generated.h"
#define COMBAT_ATTRIBUTE(Name) \
GAMEPLAYATTRIBUTE_PROPERTY_GETTER(UCombatAttributeSet, Name) \
GAMEPLAYATTRIBUTE_VALUE_GETTER(Name) \
GAMEPLAYATTRIBUTE_VALUE_SETTER(Name) \
GAMEPLAYATTRIBUTE_VALUE_INITTER(Name)
UCLASS()
class COMBAT_API UCombatAttributeSet : public UAttributeSet
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) FGameplayAttributeData DamageMultiplier = 1.f;
    COMBAT_ATTRIBUTE(DamageMultiplier)
    UPROPERTY(BlueprintReadOnly) FGameplayAttributeData MoveSpeedMultiplier = 1.f;
    COMBAT_ATTRIBUTE(MoveSpeedMultiplier)
    UPROPERTY(BlueprintReadOnly) FGameplayAttributeData Health;
    COMBAT_ATTRIBUTE(Health)
    UPROPERTY(BlueprintReadOnly) FGameplayAttributeData MaxHealth;
    COMBAT_ATTRIBUTE(MaxHealth)
    UPROPERTY(BlueprintReadOnly) FGameplayAttributeData Poise;
    COMBAT_ATTRIBUTE(Poise)
    UPROPERTY(BlueprintReadOnly) FGameplayAttributeData MaxPoise;
    COMBAT_ATTRIBUTE(MaxPoise)
    virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
    virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;
};
