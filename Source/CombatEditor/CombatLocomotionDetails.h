#pragma once
#include "IDetailCustomization.h"

/** Read-only live measurements alongside the normal editable asset properties. */
class FCombatLocomotionDetails : public IDetailCustomization
{
public:
    virtual void CustomizeDetails(IDetailLayoutBuilder& Builder) override;
};
