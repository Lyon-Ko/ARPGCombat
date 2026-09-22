#pragma once
#include "CoreMinimal.h"

struct COMBAT_API FCombatLocomotionSettings
{
#define LOCO_FLOAT(Member, Section, Key, Default, Min, Max, Description) float Member = static_cast<float>(Default);
#define LOCO_BOOL(Member, Section, Key, Default, Description) bool Member = Default;
#include "CombatLocomotionParameters.inl"
#undef LOCO_FLOAT
#undef LOCO_BOOL
};
