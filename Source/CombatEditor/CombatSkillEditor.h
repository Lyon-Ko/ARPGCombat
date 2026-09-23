#pragma once
#include "CoreMinimal.h"
#include "Toolkits/AssetEditorToolkit.h"
#include "EditorUndoClient.h"
#include "UObject/GCObject.h"
#include "TickableEditorObject.h"

class UCombatSkillDefinition;
class UCombatSkillSet;
class UCombatSkillEventSelection;
class UEdGraph;
class IDetailsView;
class SGraphEditor;
class SCombatSkillTimeline;
class SCombatSkillPreview;
class STextBlock;
class SVerticalBox;
struct FPropertyChangedEvent;

class FCombatSkillEditor : public FAssetEditorToolkit, public FEditorUndoClient, public FGCObject, public FTickableEditorObject
{
public:
    static void Open(UObject* Asset);
    virtual ~FCombatSkillEditor() override;
    virtual FName GetToolkitFName() const override { return TEXT("CombatSkillEditor"); }
    virtual FText GetBaseToolkitName() const override { return FText::FromString(TEXT("战斗技能工作台")); }
    virtual FText GetToolkitName() const override;
    virtual FText GetToolkitToolTipText() const override;
    virtual FString GetWorldCentricTabPrefix() const override { return TEXT("技能"); }
    virtual FLinearColor GetWorldCentricTabColorScale() const override { return FLinearColor(.05f,.35f,.55f); }
    virtual void RegisterTabSpawners(const TSharedRef<FTabManager>& Manager) override;
    virtual void UnregisterTabSpawners(const TSharedRef<FTabManager>& Manager) override;
    virtual void PostUndo(bool bSuccess) override;
    virtual void PostRedo(bool bSuccess) override { PostUndo(bSuccess); }
    virtual void AddReferencedObjects(FReferenceCollector& Collector) override;
    virtual FString GetReferencerName() const override { return TEXT("FCombatSkillEditor"); }
    virtual void Tick(float DeltaSeconds) override;
    virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(FCombatSkillEditor,STATGROUP_Tickables); }
private:
    TObjectPtr<UObject> RootAsset=nullptr;
    TObjectPtr<UObject> CurrentAsset=nullptr;
    TObjectPtr<UCombatSkillDefinition> Skill=nullptr;
    TObjectPtr<UCombatSkillEventSelection> Selection=nullptr;
    TObjectPtr<UEdGraph> Graph=nullptr;
    TArray<TObjectPtr<UCombatSkillDefinition>> GraphSkills;
    TSharedPtr<IDetailsView> Details;
    TSharedPtr<SGraphEditor> GraphView;
    TSharedPtr<SCombatSkillTimeline> Timeline;
    TSharedPtr<SCombatSkillPreview> Preview;
    TSharedPtr<STextBlock> Messages;
    TSharedPtr<SVerticalBox> GraphContainer;
    FGuid SelectedEvent;
    FGuid SelectedRule;
    bool bPreviewPlaying=false;
    bool bMovingTarget=false;
    float Playhead=0;
    FString ValidationText;
    void Init(UObject* Asset);
    TSharedRef<SDockTab> SpawnWorkspace(const FSpawnTabArgs& Args);
    void Select(UObject* Asset);
    void SelectEvent(FGuid Id);
    void Changed(const FPropertyChangedEvent& Event);
    void RebuildGraph();
    FReply Validate();
    FReply Play();
    FReply AddEvent();
    FReply CopySkill();
    FReply NewAsset(UClass* Class);
    FReply Equip();
    void GraphSelection(const TSet<UObject*>& Nodes);
    FText StatusText() const;
};
