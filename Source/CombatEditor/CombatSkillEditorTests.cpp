#include "CombatSkillEditorTypes.h"
#include "Misc/AutomationTest.h"
#include "Editor.h"
#include "CombatTypes.h"
#include "CombatAnimNotify.h"
#include "Animation/AnimMontage.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCombatMontageMigrationTest,"Combat.SkillEditor.MontageMigration",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FCombatMontageMigrationTest::RunTest(const FString&)
{
    auto* Source=LoadObject<UAnimMontage>(nullptr,TEXT("/Game/Combat/Animations/Native/Kwang/AM_Attack1.AM_Attack1"));
    if(!TestNotNull(TEXT("Source montage"),Source)) return false;
    const int32 OriginalCount=Source->Notifies.Num();
    auto* Skill=NewObject<UCombatSkillDefinition>(GetTransientPackage(),NAME_None,RF_Transactional);
    Skill->bDataDriven=true; Skill->Montage=Source; Skill->Duration=Source->GetPlayLength(); Skill->SkillTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Skill.Editor.Sample1"));
    FCombatSkillEvent E; E.Type=ECombatSkillEventType::Projectile; E.Time=.1f; E.Projectile=NewObject<UCombatProjectileDefinition>(); Skill->Events.Add(E);
    E.Id=FGuid::NewGuid(); E.Type=ECombatSkillEventType::HitWindow; E.Time=.2f; E.Duration=.1f; Skill->Events.Add(E);
    FCombatSkillDerivation R; R.TargetSkill=Skill->SkillTag; R.InputTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Input.Attack")); R.WindowStart=.3f; R.WindowEnd=.4f; Skill->Derivations.Add(R);
    const FString Path=TEXT("/Game/Combat/SkillEditorExamples/Tests/AM_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto* Copy=UCombatSkillEditorLibrary::ConvertToMontageNotifies(Skill,Path);
    if(!TestNotNull(TEXT("Conversion succeeded"),Copy)) return false;
    TestTrue(TEXT("Source not edited or reused"),Copy!=Source && Source->Notifies.Num()==OriginalCount);
    TestTrue(TEXT("Single native execution source"),Skill->bUseMontageNotifies && Skill->Events.IsEmpty());
    TestFalse(TEXT("Rule now uses a named window"),Skill->Derivations[0].WindowName.IsNone());
    int32 Actions=0,Windows=0;
    for(const auto& N:Copy->Notifies) { Actions+=Cast<UCombatAnimNotify_SkillAction>(N.Notify)!=nullptr; Windows+=Cast<UCombatAnimNotifyState_SkillWindow>(N.NotifyStateClass)!=nullptr; }
    TestEqual(TEXT("Point action retained"),Actions,1); TestEqual(TEXT("Hit and derivation state windows"),Windows,2);
    TestTrue(TEXT("Repeated conversion is idempotent"),UCombatSkillEditorLibrary::ConvertToMontageNotifies(Skill,Path)==Copy);
    Skill->Derivations[0].WindowStart=999; Skill->Derivations[0].WindowEnd=-999;
    TestTrue(TEXT("Native validation does not use old timing fields"),UCombatSkillEditorLibrary::ValidateSkillAssets({Skill}).IsEmpty());
    Skill->Derivations[0].WindowName=TEXT("Missing");
    TestFalse(TEXT("Broken window reference rejected"),UCombatSkillEditorLibrary::ValidateSkillAssets({Skill}).IsEmpty());
    GEditor->UndoTransaction();
    TestTrue(TEXT("Undo restores old execution mode and source"),!Skill->bUseMontageNotifies && Skill->Montage==Source && Skill->Events.Num()==2);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCombatSkillValidationTest,"Combat.SkillEditor.AssetValidation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FCombatSkillValidationTest::RunTest(const FString&)
{
    auto* A=NewObject<UCombatSkillDefinition>(); A->bDataDriven=true; A->SkillTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Skill.Editor.Sample1"));
    auto* B=NewObject<UCombatSkillDefinition>(); B->bDataDriven=true; B->SkillTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Skill.Editor.Sample2"));
    TestTrue(TEXT("Empty data skill is valid"),UCombatSkillEditorLibrary::ValidateSkillAssets({A}).IsEmpty());
    FCombatSkillEvent Event; Event.Type=ECombatSkillEventType::Projectile; A->Events.Add(Event);
    TestFalse(TEXT("Missing projectile rejected"),UCombatSkillEditorLibrary::ValidateSkillAssets({A}).IsEmpty());
    A->Events[0].Projectile=NewObject<UCombatProjectileDefinition>();
    TestTrue(TEXT("Assigned projectile accepted"),UCombatSkillEditorLibrary::ValidateSkillAssets({A}).IsEmpty());
    const FCombatSkillEvent Duplicate=A->Events[0]; A->Events.Add(Duplicate);
    TestFalse(TEXT("Duplicate event identity rejected"),UCombatSkillEditorLibrary::ValidateSkillAssets({A}).IsEmpty()); A->Events.Pop();
    B->SkillTag=A->SkillTag;
    TestFalse(TEXT("Duplicate skill tag rejected"),UCombatSkillEditorLibrary::ValidateSkillAssets({A,B}).IsEmpty());
    B->SkillTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Skill.Editor.Sample2"));
    FCombatSkillDerivation Rule; Rule.TargetSkill=B->SkillTag; Rule.Trigger=ECombatDerivationTrigger::Completed; Rule.WindowEnd=A->Duration; A->Derivations.Add(Rule);
    TestFalse(TEXT("Missing equipped target rejected"),UCombatSkillEditorLibrary::ValidateSkillAssets({A}).IsEmpty());
    TestTrue(TEXT("Equipped target accepted"),UCombatSkillEditorLibrary::ValidateSkillAssets({A,B}).IsEmpty());
    B->Derivations.Add(Rule); B->Derivations[0].TargetSkill=A->SkillTag;
    TestFalse(TEXT("Automatic cycle rejected"),UCombatSkillEditorLibrary::ValidateSkillAssets({A,B}).IsEmpty());
    A->Derivations[0].Trigger=B->Derivations[0].Trigger=ECombatDerivationTrigger::Input;
    A->Derivations[0].InputTag=B->Derivations[0].InputTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Input.Attack"));
    TestTrue(TEXT("Input-driven loop accepted"),UCombatSkillEditorLibrary::ValidateSkillAssets({A,B}).IsEmpty());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCombatSkillGraphTest,"Combat.SkillEditor.GraphTransactions",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FCombatSkillGraphTest::RunTest(const FString&)
{
    auto* Graph=NewObject<UCombatSkillGraph>(); Graph->Schema=UCombatSkillGraphSchema::StaticClass();
    auto MakeNode=[&](const TCHAR* Tag)
    {
        auto* Node=NewObject<UCombatSkillGraphNode>(Graph,NAME_None,RF_Transactional);
        Node->Skill=NewObject<UCombatSkillDefinition>(GetTransientPackage(),NAME_None,RF_Transactional); Node->Skill->bDataDriven=true; Node->Skill->SkillTag=FGameplayTag::RequestGameplayTag(Tag);
        Graph->AddNode(Node); Node->AllocateDefaultPins(); return Node;
    };
    auto* A=MakeNode(TEXT("Combat.Skill.Editor.Sample1")); auto* B=MakeNode(TEXT("Combat.Skill.Editor.Sample2"));
    auto* Schema=GetDefault<UCombatSkillGraphSchema>();
    TestTrue(TEXT("Connect creates a runtime rule"),Schema->TryCreateConnection(A->Pins[1],B->Pins[0]));
    TestEqual(TEXT("One derivation"),A->Skill->Derivations.Num(),1);
    TestTrue(TEXT("Target identity saved on the asset"),A->Skill->Derivations[0].TargetSkill==B->Skill->SkillTag);
    TestEqual(TEXT("New-rule output retained"),A->Pins.Num(),3);
    GEditor->UndoTransaction();
    TestEqual(TEXT("Undo restores asset rules"),A->Skill->Derivations.Num(),0);
    GEditor->RedoTransaction();
    TestEqual(TEXT("Redo restores asset rules"),A->Skill->Derivations.Num(),1);
    Schema->BreakPinLinks(*A->Pins[1],true);
    TestFalse(TEXT("Disconnect clears runtime target"),A->Skill->Derivations[0].TargetSkill.IsValid());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCombatSkillFactoryTest,"Combat.SkillEditor.Factories",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FCombatSkillFactoryTest::RunTest(const FString&)
{
    auto* Factory=NewObject<UCombatSkillAssetFactory>();
    auto* Skill=Cast<UCombatSkillDefinition>(Factory->FactoryCreateNew(UCombatSkillDefinition::StaticClass(),GetTransientPackage(),NAME_None,RF_Transient,nullptr,GWarn));
    TestNotNull(TEXT("Factory creates skill"),Skill);
    TestTrue(TEXT("New skills use the native data executor"),Skill && Skill->bDataDriven);
    TestFalse(TEXT("Legacy defaults retain blueprint execution"),GetDefault<UCombatSkillDefinition>()->bDataDriven);
    FCombatSkillEvent A,B;
    TestTrue(TEXT("Independent events receive different persistent IDs"),A.Id.IsValid() && B.Id.IsValid() && A.Id!=B.Id);
    return true;
}
#endif
