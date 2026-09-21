using UnrealBuildTool;
public class CombatEditor : ModuleRules
{
    public CombatEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new [] { "Core", "CoreUObject", "Engine", "UnrealEd", "Combat",
            "AssetRegistry", "Kismet", "KismetCompiler", "BlueprintGraph", "AnimGraph", "AnimGraphRuntime",
            "UMG", "UMGEditor", "Slate", "SlateCore", "InputCore", "NavigationSystem", "AIModule",
            "StateTreeModule", "StateTreeEditorModule", "GameplayStateTreeModule", "PropertyBindingUtils", "Niagara" });
    }
}
