#pragma once
#include "CoreMinimal.h"
#include "GameplayEffect.h"
#include "CombatEffects.generated.h"
UCLASS()
class COMBAT_API UCombatCooldownEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UCombatCooldownEffect();
};
UCLASS()
class COMBAT_API UCombatRiposteEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UCombatRiposteEffect();
};
