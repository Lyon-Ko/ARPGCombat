#include "CombatLocomotionConfig.h"

FCombatLocomotionSettings UCombatLocomotionConfig::MakeSnapshot() const
{
    FCombatLocomotionSettings Result;
#define LOCO_FLOAT(Member, Section, Key, Default, Min, Max, Description) Result.Member = Member;
#define LOCO_BOOL(Member, Section, Key, Default, Description) Result.Member = Member;
#include "CombatLocomotionParameters.inl"
#undef LOCO_FLOAT
#undef LOCO_BOOL
    return Result;
}
