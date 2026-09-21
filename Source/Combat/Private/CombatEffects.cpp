#include "CombatEffects.h"
#include "CombatTags.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"
UCombatCooldownEffect::UCombatCooldownEffect() { DurationPolicy = EGameplayEffectDurationType::HasDuration; DurationMagnitude = FScalableFloat(.35f); }
UCombatRiposteEffect::UCombatRiposteEffect()
{
    DurationPolicy = EGameplayEffectDurationType::HasDuration;
    DurationMagnitude = FScalableFloat(.8f);
    FInheritedTagContainer Tags; Tags.AddTag(CombatTags::State_RiposteReady);
    FindOrAddComponent<UTargetTagsGameplayEffectComponent>().SetAndApplyTargetTagChanges(Tags);
}
