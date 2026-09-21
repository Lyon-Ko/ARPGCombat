using UnrealBuildTool;
public class CombatEditorTarget : TargetRules
{
    public CombatEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.AddRange(new [] { "Combat", "CombatEditor" });
    }
}
