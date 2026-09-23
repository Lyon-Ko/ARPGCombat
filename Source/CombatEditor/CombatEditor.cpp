#include "Modules/ModuleManager.h"
#include "AssetToolsModule.h"
#include "AssetTypeActions_Base.h"
#include "CombatSkillEditor.h"
#include "CombatSkillEditorTypes.h"
#include "CombatTypes.h"
#include "ToolMenus.h"
#include "AnimationToolMenuContext.h"
#include "IAnimationEditor.h"
#include "Animation/AnimMontage.h"
#include "CombatAnimNotify.h"
#include "IDetailCustomization.h"
#include "DetailLayoutBuilder.h"
#include "PropertyEditorModule.h"
#include "PropertyHandle.h"
#include "CombatLocomotionDetails.h"

class FCombatNotifyDetails : public IDetailCustomization
{
public:
    virtual void CustomizeDetails(IDetailLayoutBuilder& Builder) override
    {
        auto Action=Builder.GetProperty(GET_MEMBER_NAME_CHECKED(UCombatAnimNotify_SkillAction,Action));
        if(auto Time=Action->GetChildHandle(TEXT("Time"))) Builder.HideProperty(Time);
        if(auto Id=Action->GetChildHandle(TEXT("Id"))) Builder.HideProperty(Id);
    }
};

class FCombatSkillAssetActions : public FAssetTypeActions_Base
{
public:
    FCombatSkillAssetActions(UClass* InClass,const TCHAR* InName,EAssetTypeCategories::Type InCategory) : Class(InClass),Name(InName),Category(InCategory) {}
    virtual FText GetName() const override { return FText::FromString(Name); }
    virtual FColor GetTypeColor() const override { return FColor(30,165,215); }
    virtual UClass* GetSupportedClass() const override { return Class; }
    virtual uint32 GetCategories() override { return Category; }
    virtual void OpenAssetEditor(const TArray<UObject*>& Assets,TSharedPtr<IToolkitHost>) override { for(auto* A:Assets) FCombatSkillEditor::Open(A); }
private:
    UClass* Class; FString Name; EAssetTypeCategories::Type Category;
};
class FCombatEditorModule : public IModuleInterface
{
    TArray<TSharedPtr<IAssetTypeActions>> Actions;
public:
    virtual void StartupModule() override
    {
        auto& Tools=FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get();
        auto Category=Tools.RegisterAdvancedAssetCategory(TEXT("CombatSkills"),FText::FromString(TEXT("战斗技能")));
        auto Register=[&](UClass* Class,const TCHAR* Name) { auto Action=MakeShared<FCombatSkillAssetActions>(Class,Name,Category); Tools.RegisterAssetTypeActions(Action); Actions.Add(Action); };
        Register(UCombatSkillDefinition::StaticClass(),TEXT("技能")); Register(UCombatProjectileDefinition::StaticClass(),TEXT("子弹 / 导弹")); Register(UCombatBuffDefinition::StaticClass(),TEXT("Buff")); Register(UCombatSkillSet::StaticClass(),TEXT("技能集合"));
        FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor")).RegisterCustomClassLayout(TEXT("CombatAnimNotify_SkillAction"),FOnGetDetailCustomizationInstance::CreateLambda([]{return MakeShared<FCombatNotifyDetails>();}));
        UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this,&FCombatEditorModule::RegisterMenus));
        FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor")).RegisterCustomClassLayout(TEXT("CombatLocomotionConfig"), FOnGetDetailCustomizationInstance::CreateLambda([] { return MakeShared<FCombatLocomotionDetails>(); }));
    }
    void RegisterMenus()
    {
        FToolMenuOwnerScoped Owner(this);
        auto* Menu=UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Tools"));
        Menu->FindOrAddSection(TEXT("CombatSkills")).AddMenuEntry(TEXT("CombatSkillEditor"),FText::FromString(TEXT("战斗技能工作台")),FText::FromString(TEXT("打开技能编辑器；首次创建独立示例资产。")),FSlateIcon(),FUIAction(FExecuteAction::CreateLambda([]{FCombatSkillEditor::Open(UCombatSkillEditorLibrary::CreateExamples());})));
        auto* Toolbar=UToolMenus::Get()->ExtendMenu(TEXT("AssetEditor.AnimationEditor.ToolBar"));
        Toolbar->AddDynamicSection(TEXT("CombatMontage"),FNewToolMenuDelegate::CreateLambda([](UToolMenu* M)
        {
            auto* Context=M->FindContext<UAnimationToolMenuContext>();
            auto Editor=Context?Context->AnimationEditor.Pin():nullptr;
            UAnimMontage* Montage=nullptr;
            if(Editor) if(const auto* Objects=Editor->GetObjectsCurrentlyBeingEdited()) for(UObject* Object:*Objects) if(auto* Candidate=Cast<UAnimMontage>(Object)) { Montage=Candidate; break; }
            if(!Montage) return;
            auto& Section=M->FindOrAddSection(TEXT("CombatSkills"));
            Section.AddEntry(FToolMenuEntry::InitComboButton(TEXT("CombatDerivations"),FUIAction(),FNewToolMenuDelegate::CreateLambda([Weak=TWeakObjectPtr<UAnimMontage>(Montage)](UToolMenu* Sub)
            {
                auto& Items=Sub->AddSection(TEXT("Skills"),FText::FromString(TEXT("关联技能：派生图与参数")));
                const auto Skills=UCombatSkillEditorLibrary::FindMontageSkills(Weak.Get());
                for(auto* S:Skills) Items.AddMenuEntry(*S->GetPathName(),FText::FromString(S->GetName()),FText::FromString(TEXT("打开独立派生图；动画时序仍在此 Montage 编辑")),FSlateIcon(),FUIAction(FExecuteAction::CreateLambda([Skill=TWeakObjectPtr<UCombatSkillDefinition>(S)]{if(Skill.IsValid()) UCombatSkillEditorLibrary::OpenSkillEditor(Skill.Get());})));
                if(Skills.IsEmpty()) Items.AddMenuEntry(TEXT("NoSkill"),FText::FromString(TEXT("先在技能资产中引用此 Montage")),FText(),FSlateIcon(),FUIAction(FExecuteAction(),FCanExecuteAction::CreateLambda([]{return false;})));
            }),FText::FromString(TEXT("技能派生")),FText::FromString(TEXT("在原生通知轨道添加 Combat Skill Action / Window，技能关系单独配置。")),FSlateIcon()));
        }));
    }
    virtual void ShutdownModule() override
    {
        UToolMenus::UnRegisterStartupCallback(this); UToolMenus::UnregisterOwner(this);
        if(auto* Properties=FModuleManager::GetModulePtr<FPropertyEditorModule>(TEXT("PropertyEditor"))) Properties->UnregisterCustomClassLayout(TEXT("CombatLocomotionConfig"));
        if(auto* Properties=FModuleManager::GetModulePtr<FPropertyEditorModule>(TEXT("PropertyEditor"))) Properties->UnregisterCustomClassLayout(TEXT("CombatAnimNotify_SkillAction"));
        if(auto* Module=FModuleManager::GetModulePtr<FAssetToolsModule>(TEXT("AssetTools"))) for(auto Action:Actions) Module->Get().UnregisterAssetTypeActions(Action.ToSharedRef());
        Actions.Reset();
    }
};
IMPLEMENT_MODULE(FCombatEditorModule,CombatEditor);
