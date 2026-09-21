using UnrealBuildTool;
public class Combat : ModuleRules
{
    public Combat(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new [] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "GameplayAbilities", "GameplayTags", "GameplayTasks", "MotionWarping", "AIModule", "GameplayStateTreeModule", "StateTreeModule", "Niagara", "UMG", "Slate", "SlateCore" });
    }
}

