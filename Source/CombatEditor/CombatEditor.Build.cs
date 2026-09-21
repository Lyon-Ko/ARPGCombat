using UnrealBuildTool;
public class CombatEditor : ModuleRules
{
    public CombatEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new [] { "Core", "CoreUObject", "Engine", "UnrealEd", "Combat" });
    }
}
