#include "CombatSkillEditor.h"
#include "CombatSkillEditorTypes.h"
#include "CombatSkillRuntime.h"
#include "CombatCharacter.h"
#include "CombatEditorLibrary.h"
#include "CombatTypes.h"
#include "Editor.h"
#include "Editor/EditorEngine.h"
#include "AssetToolsModule.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "ContentBrowserModule.h"
#include "IContentBrowserSingleton.h"
#include "PropertyEditorModule.h"
#include "IDetailsView.h"
#include "GraphEditor.h"
#include "ScopedTransaction.h"
#include "Framework/Commands/GenericCommands.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/SBoxPanel.h"
#include "SEditorViewport.h"
#include "EditorViewportClient.h"
#include "PreviewScene.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Serialization/JsonSerializer.h"
#include "JsonObjectConverter.h"
#include "EngineUtils.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "Kismet/GameplayStatics.h"
#include "CombatProjectile.h"
#include "DrawDebugHelpers.h"
#include "SceneManagement.h"

class FCombatPreviewClient : public FEditorViewportClient
{
public:
    FCombatPreviewClient(FPreviewScene* Scene,const TWeakPtr<SEditorViewport>& Viewport) : FEditorViewportClient(nullptr,Scene,Viewport) {}
    TWeakObjectPtr<UCombatSkillDefinition> Skill;
    virtual void Draw(const FSceneView* View,FPrimitiveDrawInterface* PDI) override
    {
        FEditorViewportClient::Draw(View,PDI);
        if(!Skill.IsValid()) return;
        for(const auto& E:Skill->Events)
        {
            if(E.Type==ECombatSkillEventType::Projectile && E.Projectile)
            {
                if(E.Projectile->bSphereCollision) DrawWireSphere(PDI,E.Offset,FLinearColor(.1f,.7f,1.f),E.Projectile->Radius,24,SDPG_World);
                else DrawWireBox(PDI,FBox(E.Offset-E.Projectile->HalfExtent,E.Offset+E.Projectile->HalfExtent),FLinearColor(.1f,.7f,1.f),SDPG_World);
            }
            if(E.Type==ECombatSkillEventType::AreaRelease) DrawWireSphere(PDI,FVector::ZeroVector,FLinearColor(1,.4f,.1f),Skill->AreaRadius,32,SDPG_World);
        }
    }
};

static FText CTxt(const TCHAR* Text) { return FText::FromString(Text); }
static const TCHAR* EventName(ECombatSkillEventType Type)
{
    switch(Type) {
    case ECombatSkillEventType::HitWindow:return TEXT("近战命中"); case ECombatSkillEventType::Movement:return TEXT("位移");
    case ECombatSkillEventType::Projectile:return TEXT("发射子弹"); case ECombatSkillEventType::AreaWarning:return TEXT("范围预警");
    case ECombatSkillEventType::AreaRelease:return TEXT("范围释放"); case ECombatSkillEventType::ApplyBuff:return TEXT("添加 Buff");
    case ECombatSkillEventType::RemoveBuff:return TEXT("移除 Buff"); case ECombatSkillEventType::CancelWindow:return TEXT("打断窗口");
    case ECombatSkillEventType::ComboWindow:return TEXT("连招窗口"); case ECombatSkillEventType::Effect:return TEXT("表现");
    default:return TEXT("结束"); }
}

/** Direct asset editing, with one undo transaction per drag. */
class SCombatSkillTimeline : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SCombatSkillTimeline) {} SLATE_END_ARGS()
    void Construct(const FArguments&) { SetCanTick(false); }
    TWeakObjectPtr<UCombatSkillDefinition> Skill;
    TFunction<void(FGuid)> OnSelect;
    TFunction<void(float)> OnScrub;
    FGuid Selected;
    float Playhead=0, Zoom=1;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(650,340); }
    float Scale(const FGeometry& G) const { return FMath::Max(1.f,G.GetLocalSize().X-135.f)/FMath::Max(.1f,Skill.IsValid()?Skill->Duration:1.f)*Zoom; }
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle&,bool) const override
    {
        const auto* Brush=FAppStyle::GetBrush(TEXT("WhiteBrush"));
        FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(),Brush,ESlateDrawEffect::None,FLinearColor(.025f,.033f,.047f));
        if(!Skill.IsValid()) return Layer+1;
        const float S=Scale(G), Width=G.GetLocalSize().X;
        for(int32 Row=0;Row<11;++Row)
        {
            float Y=32+Row*27;
            FSlateDrawElement::MakeText(Out,Layer+1,G.ToPaintGeometry(FVector2D(120,24),FSlateLayoutTransform(FVector2D(6,Y+3))),CTxt(EventName(ECombatSkillEventType(Row))),FAppStyle::GetFontStyle(TEXT("SmallFont")),ESlateDrawEffect::None,FLinearColor(.65f,.72f,.8f));
            FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),{FVector2D(128,Y+26),FVector2D(Width,Y+26)},ESlateDrawEffect::None,FLinearColor(.1f,.14f,.2f));
        }
        const float Step=.1f;
        for(float T=0;T<=Skill->Duration && 130+T*S<Width;T+=Step)
        {
            const float X=130+T*S;
            FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),{FVector2D(X,24),FVector2D(X,330)},ESlateDrawEffect::None,FLinearColor(.09f,.12f,.17f));
            FSlateDrawElement::MakeText(Out,Layer+2,G.ToPaintGeometry(FVector2D(40,20),FSlateLayoutTransform(FVector2D(X,2))),FText::FromString(FString::Printf(TEXT("%.1f"),T)),FAppStyle::GetFontStyle(TEXT("SmallFont")));
        }
        for(const auto& E:Skill->Events)
        {
            const float X=130+E.Time*S,Y=34+int32(E.Type)*27;
            const bool Window=E.Type==ECombatSkillEventType::HitWindow || E.Type==ECombatSkillEventType::CancelWindow || E.Type==ECombatSkillEventType::ComboWindow;
            const float W=Window?FMath::Max(12.f,E.Duration*S):14.f;
            const FLinearColor Color=E.Id==Selected?FLinearColor(1,.6f,.16f):FLinearColor(.08f,.5f,.7f);
            FSlateDrawElement::MakeBox(Out,Layer+3,G.ToPaintGeometry(FVector2D(W,22),FSlateLayoutTransform(FVector2D(X,Y))),Brush,ESlateDrawEffect::None,Color);
            if(W>45) FSlateDrawElement::MakeText(Out,Layer+4,G.ToPaintGeometry(FVector2D(W,22),FSlateLayoutTransform(FVector2D(X+3,Y+2))),FText::FromString(E.Label),FAppStyle::GetFontStyle(TEXT("SmallFont")));
        }
        const float X=130+Playhead*S;
        FSlateDrawElement::MakeLines(Out,Layer+5,G.ToPaintGeometry(),{FVector2D(X,0),FVector2D(X,330)},ESlateDrawEffect::None,FLinearColor(1,.85f,.35f),true,2);
        return Layer+5;
    }
    virtual FReply OnMouseButtonDown(const FGeometry& G,const FPointerEvent& E) override
    {
        if(!Skill.IsValid() || E.GetEffectingButton()!=EKeys::LeftMouseButton) return FReply::Unhandled();
        const FVector2D P=G.AbsoluteToLocal(E.GetScreenSpacePosition());
        if(P.Y<30) { Scrub(G,P.X); return FReply::Handled().SetUserFocus(SharedThis(this)); }
        for(auto& Event:Skill->Events)
        {
            const float X=130+Event.Time*Scale(G),Y=34+int32(Event.Type)*27;
            const bool Window=Event.Type==ECombatSkillEventType::HitWindow || Event.Type==ECombatSkillEventType::CancelWindow || Event.Type==ECombatSkillEventType::ComboWindow;
            const float W=Window?FMath::Max(12.f,Event.Duration*Scale(G)):14;
            if(P.X>=X && P.X<=X+W && P.Y>=Y && P.Y<=Y+22)
            {
                Selected=Event.Id; if(OnSelect) OnSelect(Selected);
                Transaction=MakeUnique<FScopedTransaction>(CTxt(TEXT("调整时间轴事件"))); Skill->Modify();
                StartX=P.X; StartTime=Event.Time; StartDuration=Event.Duration; bResize=Window && (E.IsShiftDown() || P.X>X+W-6);
                return FReply::Handled().CaptureMouse(SharedThis(this)).SetUserFocus(SharedThis(this));
            }
        }
        Scrub(G,P.X); return FReply::Handled().SetUserFocus(SharedThis(this));
    }
    virtual FReply OnMouseMove(const FGeometry& G,const FPointerEvent& E) override
    {
        if(!HasMouseCapture() || !Skill.IsValid()) return FReply::Unhandled();
        if(auto* Event=Skill->Events.FindByPredicate([&](const auto& V){return V.Id==Selected;}))
        {
            const float Delta=(G.AbsoluteToLocal(E.GetScreenSpacePosition()).X-StartX)/Scale(G);
            auto Snap=[&](float T){return E.IsAltDown()?T:FMath::GridSnap(T,1.f/30.f);};
            if(bResize) Event->Duration=FMath::Clamp(Snap(StartDuration+Delta),0.f,Skill->Duration-Event->Time);
            else Event->Time=FMath::Clamp(Snap(StartTime+Delta),0.f,Skill->Duration);
            Skill->MarkPackageDirty();
        }
        return FReply::Handled();
    }
    virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent&) override
    {
        if(!HasMouseCapture()) return FReply::Unhandled(); Transaction.Reset(); if(OnSelect) OnSelect(Selected); return FReply::Handled().ReleaseMouseCapture();
    }
    virtual FReply OnMouseWheel(const FGeometry&,const FPointerEvent& E) override { Zoom=FMath::Clamp(Zoom+E.GetWheelDelta()*.15f,.25f,4.f); return FReply::Handled(); }
    virtual FReply OnKeyDown(const FGeometry&,const FKeyEvent& E) override
    {
        if(!Skill.IsValid()) return FReply::Unhandled();
        auto* Event=Skill->Events.FindByPredicate([&](const auto& V){return V.Id==Selected;});
        if(E.IsControlDown() && E.GetKey()==EKeys::C && Event)
        { FString Json; FJsonObjectConverter::UStructToJsonObjectString(*Event,Json); FPlatformApplicationMisc::ClipboardCopy(*Json); return FReply::Handled(); }
        if(E.IsControlDown() && E.GetKey()==EKeys::V)
        {
            FString Json; FPlatformApplicationMisc::ClipboardPaste(Json); FCombatSkillEvent Copy;
            if(FJsonObjectConverter::JsonObjectStringToUStruct(Json,&Copy))
            { const FScopedTransaction T(CTxt(TEXT("粘贴事件"))); Skill->Modify(); Copy.Id=FGuid::NewGuid(); Copy.Time=Playhead; Skill->Events.Add(Copy); Skill->MarkPackageDirty(); if(OnSelect) OnSelect(Copy.Id); }
            return FReply::Handled();
        }
        if(E.GetKey()==EKeys::Delete && Event)
        { const FScopedTransaction T(CTxt(TEXT("删除事件"))); Skill->Modify(); Skill->Events.RemoveAll([&](const auto& V){return V.Id==Selected;}); Skill->MarkPackageDirty(); if(OnSelect) OnSelect(FGuid()); return FReply::Handled(); }
        return FReply::Unhandled();
    }
private:
    float StartX=0,StartTime=0,StartDuration=0; bool bResize=false; TUniquePtr<FScopedTransaction> Transaction;
    void Scrub(const FGeometry& G,float X) { Playhead=FMath::Clamp((X-130)/Scale(G),0.f,Skill->Duration); if(OnScrub) OnScrub(Playhead); }
};

class SCombatSkillPreview : public SEditorViewport
{
public:
    SLATE_BEGIN_ARGS(SCombatSkillPreview) {} SLATE_END_ARGS()
    void Construct(const FArguments&) { Scene=MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues()); SEditorViewport::Construct(SEditorViewport::FArguments()); }
    void SetSkill(UCombatSkillDefinition* InSkill)
    {
        Skill=InSkill;
        if(Client) StaticCastSharedPtr<FCombatPreviewClient>(Client)->Skill=InSkill;
        if(!Mesh)
        { Mesh=NewObject<USkeletalMeshComponent>(); Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode); Scene->AddComponent(Mesh,FTransform::Identity); }
        USkeletalMesh* Skeletal=InSkill && InSkill->Montage && InSkill->Montage->GetSkeleton()?InSkill->Montage->GetSkeleton()->GetPreviewMesh(true):nullptr;
        if(!Skeletal)
        {
            if(auto* Class=LoadClass<ACombatCharacter>(nullptr,TEXT("/Game/Combat/Characters/BP_CombatPlayer.BP_CombatPlayer_C"))) Skeletal=Class->GetDefaultObject<ACombatCharacter>()->GetMesh()->GetSkeletalMeshAsset();
        }
        Mesh->SetSkeletalMeshAsset(Skeletal); Scrub(0);
    }
    void Scrub(float Time)
    {
        if(Mesh && Skill.IsValid() && Skill->Montage && Skill->Montage->SlotAnimTracks.Num())
        {
            for(const auto& Segment:Skill->Montage->SlotAnimTracks[0].AnimTrack.AnimSegments)
                if(Time>=Segment.StartPos && Time<=Segment.GetEndPos())
                    if(auto* Sequence=Cast<UAnimSequence>(Segment.GetAnimReference()))
                        UCombatEditorLibrary::SampleAnimationPreview(Mesh,Sequence,Segment.AnimStartTime+(Time-Segment.StartPos)*Segment.AnimPlayRate);
        }
        if(Client.IsValid()) Client->Invalidate();
    }
    virtual TSharedRef<FEditorViewportClient> MakeEditorViewportClient() override
    {
        Client=MakeShared<FCombatPreviewClient>(Scene.Get(),SharedThis(this)); Client->SetViewLocation(FVector(260,-330,150)); Client->SetViewRotation(FRotator(-10,125,0)); Client->SetViewMode(VMI_Lit); Client->SetRealtime(true); return Client.ToSharedRef();
    }
private:
    TUniquePtr<FPreviewScene> Scene; USkeletalMeshComponent* Mesh=nullptr; TWeakObjectPtr<UCombatSkillDefinition> Skill; TSharedPtr<FEditorViewportClient> Client;
};

void FCombatSkillEditor::Open(UObject* Asset) { MakeShared<FCombatSkillEditor>()->Init(Asset); }
FText FCombatSkillEditor::GetToolkitName() const
{
    return CurrentAsset ? GetLabelForObject(CurrentAsset) : GetBaseToolkitName();
}
FText FCombatSkillEditor::GetToolkitToolTipText() const
{
    return CurrentAsset ? GetToolTipTextForObject(CurrentAsset) : GetBaseToolkitName();
}
void FCombatSkillEditor::Init(UObject* Asset)
{
    RootAsset=Asset; CurrentAsset=Asset; Selection=NewObject<UCombatSkillEventSelection>();
    FDetailsViewArgs Args; Args.bHideSelectionTip=true; Args.bAllowSearch=true;
    Details=FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor")).CreateDetailView(Args);
    Details->SetIsPropertyVisibleDelegate(FIsPropertyVisible::CreateLambda([this](const FPropertyAndParent& P)
    {
        if(Skill && Skill->Montage && Skill->bUseMontageNotifies && P.Property.GetOwnerStruct()==FCombatSkillDerivation::StaticStruct() && (P.Property.GetFName()==TEXT("WindowStart") || P.Property.GetFName()==TEXT("WindowEnd"))) return false;
        if(P.Property.GetOwnerClass()==UCombatSkillEventSelection::StaticClass())
        { if(P.Property.GetFName()==TEXT("Event")) return SelectedEvent.IsValid(); if(P.Property.GetFName()==TEXT("Rule")) return SelectedRule.IsValid(); }
        return true;
    }));
    Details->OnFinishedChangingProperties().AddRaw(this,&FCombatSkillEditor::Changed);
    const auto Layout=FTabManager::NewLayout(TEXT("CombatSkillEditor_v1"))->AddArea(FTabManager::NewPrimaryArea()->SetOrientation(Orient_Vertical)->Split(FTabManager::NewStack()->AddTab(TEXT("CombatSkillWorkspace"),ETabState::OpenedTab)->SetHideTabWell(true)));
    InitAssetEditor(EToolkitMode::Standalone,TSharedPtr<IToolkitHost>(),TEXT("CombatSkillEditor"),Layout,true,true,Asset);
    GEditor->RegisterForUndo(this);
    Select(Asset);
}
FCombatSkillEditor::~FCombatSkillEditor() { if(GEditor) GEditor->UnregisterForUndo(this); if(Details) Details->OnFinishedChangingProperties().RemoveAll(this); }
void FCombatSkillEditor::RegisterTabSpawners(const TSharedRef<FTabManager>& Manager)
{ FAssetEditorToolkit::RegisterTabSpawners(Manager); Manager->RegisterTabSpawner(TEXT("CombatSkillWorkspace"),FOnSpawnTab::CreateSP(this,&FCombatSkillEditor::SpawnWorkspace)).SetDisplayName(CTxt(TEXT("技能工作台"))); }
void FCombatSkillEditor::UnregisterTabSpawners(const TSharedRef<FTabManager>& Manager)
{ Manager->UnregisterTabSpawner(TEXT("CombatSkillWorkspace")); FAssetEditorToolkit::UnregisterTabSpawners(Manager); }
void FCombatSkillEditor::AddReferencedObjects(FReferenceCollector& C) { C.AddReferencedObject(RootAsset); C.AddReferencedObject(CurrentAsset); C.AddReferencedObject(Skill); C.AddReferencedObject(Selection); C.AddReferencedObject(Graph); C.AddReferencedObjects(GraphSkills); }
TSharedRef<SDockTab> FCombatSkillEditor::SpawnWorkspace(const FSpawnTabArgs&)
{
    FAssetPickerConfig Picker;
    Picker.Filter.ClassPaths={UCombatSkillDefinition::StaticClass()->GetClassPathName(),UCombatProjectileDefinition::StaticClass()->GetClassPathName(),UCombatBuffDefinition::StaticClass()->GetClassPathName(),UCombatSkillSet::StaticClass()->GetClassPathName()};
    Picker.InitialAssetViewType=EAssetViewType::List; Picker.bAllowNullSelection=false;
    Picker.OnAssetSelected=FOnAssetSelected::CreateLambda([this](const FAssetData& A){Select(A.GetAsset());});
    auto Button=[&](const TCHAR* Name,TFunction<FReply()> Action) { return SNew(SButton).Text(CTxt(Name)).OnClicked_Lambda(MoveTemp(Action)); };
    return SNew(SDockTab)
    [SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(8)
        [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ 技能"),[this]{return NewAsset(UCombatSkillDefinition::StaticClass());})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ 子弹"),[this]{return NewAsset(UCombatProjectileDefinition::StaticClass());})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ Buff"),[this]{return NewAsset(UCombatBuffDefinition::StaticClass());})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ 集合"),[this]{return NewAsset(UCombatSkillSet::StaticClass());})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("复制为新版"),[this]{return CopySkill();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("原生 Montage"),[this]{UCombatSkillEditorLibrary::OpenSkillMontage(Skill);return FReply::Handled();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("迁移到 Montage"),[this]
            {
                if(Skill && Skill->Montage)
                {
                    FString Package,Name; FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get().CreateUniqueAssetName(TEXT("/Game/Combat/Animations/Custom/AM_")+Skill->GetName(),TEXT("_Skill"),Package,Name);
                    if(auto* M=UCombatSkillEditorLibrary::ConvertToMontageNotifies(Skill,Package)) { AddEditingObject(M); RebuildGraph(); Details->ForceRefresh(); UCombatSkillEditorLibrary::OpenSkillMontage(Skill); ValidationText=TEXT("已迁移到独立 Montage；旧事件数组已清空。保存技能和 Montage。派生图通过 WindowName 引用通知窗口。"); }
                    else ValidationText=TEXT("迁移未执行：请检查 Montage、事件/窗口范围、目标路径，且结束 PIE。已有原生技能通知的 Montage 不会重复导入。");
                }
                else ValidationText=TEXT("请先给技能指定 Montage；无动画技能继续使用数据时间轴。");
                return FReply::Handled();
            })]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("检查资产"),[this]{return Validate();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("PIE 试玩"),[this]{return Play();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("停止试玩"),[]{if(GEditor->PlayWorld)GEditor->RequestEndPlayMap();return FReply::Handled();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("移动靶开关"),[this]{bMovingTarget=!bMovingTarget;return FReply::Handled();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ 靶子"),[]{UCombatSkillEditorLibrary::SpawnPreviewTarget(FVector(900,200,100));return FReply::Handled();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ 障碍"),[]{UCombatSkillEditorLibrary::SpawnPreviewObstacle(FVector(450,0,150),FVector(20,150,300));return FReply::Handled();})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("装备集合"),[this]{return Equip();})]
        ]
        +SVerticalBox::Slot().FillHeight(1)
        [SNew(SSplitter)
            +SSplitter::Slot().Value(.18f)[FModuleManager::LoadModuleChecked<FContentBrowserModule>(TEXT("ContentBrowser")).Get().CreateAssetPicker(Picker)]
            +SSplitter::Slot().Value(.52f)
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Visibility_Lambda([this]{return Skill && Skill->Montage?EVisibility::Visible:EVisibility::Collapsed;}).Text(CTxt(TEXT("动画时序在原生 Montage 的通知轨道编辑。此处仅配置派生关系与技能参数；双击连线设置命名窗口。未迁移的旧时间轴请先点「迁移到 Montage」。")))]
                +SVerticalBox::Slot().FillHeight(TAttribute<float>::CreateLambda([this]{return Skill && Skill->Montage?0.f:.45f;}))[SAssignNew(Preview,SCombatSkillPreview).Visibility_Lambda([this]{return Skill && Skill->Montage?EVisibility::Collapsed:EVisibility::Visible;})]
                +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox).Visibility_Lambda([this]{return Skill && Skill->Montage?EVisibility::Collapsed:EVisibility::Visible;})
                    +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("＋ 时间轴事件"),[this]{return AddEvent();})]
                    +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("技能参数"),[this]{if(Skill) Details->SetObject(Skill);return FReply::Handled();})]
                    +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("播放 / 暂停"),[this]{bPreviewPlaying=!bPreviewPlaying;return FReply::Handled();})]
                    +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(CTxt(TEXT("拖动事件 · 边缘裁剪 · Alt 取消帧吸附 · 滚轮缩放 · Ctrl+C/V")))]
                ]
                +SVerticalBox::Slot().AutoHeight()[SAssignNew(Timeline,SCombatSkillTimeline).Visibility_Lambda([this]{return Skill && Skill->Montage?EVisibility::Collapsed:EVisibility::Visible;})]
                +SVerticalBox::Slot().FillHeight(TAttribute<float>::CreateLambda([this]{return Skill && Skill->Montage?1.f:.35f;}))[SAssignNew(GraphContainer,SVerticalBox)]
            ]
            +SSplitter::Slot().Value(.30f)[Details.ToSharedRef()]
        ]
        +SVerticalBox::Slot().AutoHeight().MaxHeight(130).Padding(6)[SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(Messages,STextBlock).Text(this,&FCombatSkillEditor::StatusText).AutoWrapText(true)]]
    ];
}
void FCombatSkillEditor::Select(UObject* Asset)
{
    if(!Asset) return;
    CurrentAsset=Asset; AddEditingObject(Asset); Details->SetObject(Asset);
    if(auto* S=Cast<UCombatSkillDefinition>(Asset)) Skill=S;
    else if(auto* Set=Cast<UCombatSkillSet>(Asset)) { RootAsset=Asset; Skill=Set->Skills.IsEmpty()?nullptr:Set->Skills[0].Get(); }
    if(Timeline) { Timeline->Skill=Skill; Timeline->OnSelect=[this](FGuid Id){SelectEvent(Id);}; Timeline->OnScrub=[this](float T){Playhead=T;if(Preview)Preview->Scrub(T);}; }
    if(Preview) Preview->SetSkill(Skill);
    RebuildGraph();
}
void FCombatSkillEditor::SelectEvent(FGuid Id)
{
    SelectedEvent=Id; SelectedRule.Invalidate(); if(Timeline) Timeline->Selected=Id;
    if(Skill) if(const auto* E=Skill->Events.FindByPredicate([&](const auto& V){return V.Id==Id;})) { Selection->Event=*E; Details->SetObject(Selection,true); return; }
    Details->SetObject(Skill);
}
void FCombatSkillEditor::Changed(const FPropertyChangedEvent&)
{
    if(Skill && SelectedEvent.IsValid() && Details->GetSelectedObjects().Contains(Selection))
        if(auto* E=Skill->Events.FindByPredicate([&](const auto& V){return V.Id==SelectedEvent;}))
        { const FScopedTransaction T(CTxt(TEXT("修改技能事件"))); Skill->Modify(); *E=Selection->Event; E->Id=SelectedEvent; Skill->MarkPackageDirty(); }
    if(Skill && SelectedRule.IsValid() && Details->GetSelectedObjects().Contains(Selection))
        if(auto* R=Skill->Derivations.FindByPredicate([&](const auto& V){return V.Id==SelectedRule;}))
        { const FScopedTransaction T(CTxt(TEXT("修改派生规则"))); Skill->Modify(); *R=Selection->Rule; R->Id=SelectedRule; Skill->MarkPackageDirty(); }
    RebuildGraph(); if(Preview) Preview->SetSkill(Skill);
}
void FCombatSkillEditor::PostUndo(bool) { if(Skill) SelectEvent(SelectedEvent); RebuildGraph(); }
void FCombatSkillEditor::RebuildGraph()
{
    if(!GraphContainer) return;
    GraphSkills.Reset();
    if(auto* Set=Cast<UCombatSkillSet>(RootAsset)) for(UCombatSkillDefinition* S:Set->Skills) if(S) GraphSkills.AddUnique(S);
    if(Skill) GraphSkills.AddUnique(Skill);
    // Include referenced assets to make individual skill editors useful as well.
    TArray<FAssetData> Assets; FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get().GetAssetsByClass(UCombatSkillDefinition::StaticClass()->GetClassPathName(),Assets);
    for(int32 I=0;I<GraphSkills.Num() && I<128;++I) for(const auto& R:GraphSkills[I]->Derivations)
        for(const auto& A:Assets) if(auto* Candidate=Cast<UCombatSkillDefinition>(A.GetAsset()); Candidate && Candidate->SkillTag==R.TargetSkill) GraphSkills.AddUnique(Candidate);
    auto* NewGraph=NewObject<UCombatSkillGraph>(); Graph=NewGraph; Graph->Schema=UCombatSkillGraphSchema::StaticClass(); Graph->SetFlags(RF_Transactional);
    NewGraph->OnSelectRule=[this](UCombatSkillDefinition* S,int32 Index)
    {
        if(!S || !S->Derivations.IsValidIndex(Index)) return;
        Skill=S; SelectedEvent.Invalidate(); SelectedRule=S->Derivations[Index].Id; Selection->Rule=S->Derivations[Index]; Details->SetObject(Selection,true);
    };
    TMap<FGameplayTag,UCombatSkillGraphNode*> Nodes;
    for(int32 I=0;I<GraphSkills.Num();++I)
    {
        auto* Node=NewObject<UCombatSkillGraphNode>(Graph); Node->Skill=GraphSkills[I]; Node->CreateNewGuid(); Node->SetFlags(RF_Transactional);
        const FVector2D P=Node->Skill->GraphPosition; Node->NodePosX=P.IsNearlyZero()?I*350:int32(P.X); Node->NodePosY=int32(P.Y);
        Graph->AddNode(Node); Node->AllocateDefaultPins(); Nodes.Add(Node->Skill->SkillTag,Node);
    }
    for(const auto& Pair:Nodes) for(int32 I=0;I<Pair.Value->Skill->Derivations.Num();++I)
        if(auto* const* Target=Nodes.Find(Pair.Value->Skill->Derivations[I].TargetSkill)) Pair.Value->Pins[I+1]->MakeLinkTo((*Target)->Pins[0]);
    SGraphEditor::FGraphEditorEvents Events; Events.OnSelectionChanged=SGraphEditor::FOnSelectionChanged::CreateRaw(this,&FCombatSkillEditor::GraphSelection);
    auto Commands=MakeShared<FUICommandList>();
    Commands->MapAction(FGenericCommands::Get().Delete,FExecuteAction::CreateLambda([this]
    {
        if(!GraphView) return; const auto Selected=GraphView->GetSelectedNodes();
        const FScopedTransaction T(CTxt(TEXT("从集合移除技能节点")));
        for(UObject* O:Selected) if(auto* N=Cast<UCombatSkillGraphNode>(O))
        {
            for(UCombatSkillDefinition* S:GraphSkills) { S->Modify(); S->Derivations.RemoveAll([&](const auto& R){return R.TargetSkill==N->Skill->SkillTag;}); }
            if(auto* Set=Cast<UCombatSkillSet>(RootAsset)) { Set->Modify(); Set->Skills.Remove(N->Skill); }
            if(Skill==N->Skill) { Skill=nullptr; Timeline->Skill=nullptr; Preview->SetSkill(nullptr); Details->SetObject(RootAsset); }
        }
        RebuildGraph();
    }));
    GraphContainer->ClearChildren(); GraphContainer->AddSlot()[SAssignNew(GraphView,SGraphEditor).GraphToEdit(Graph).AdditionalCommands(Commands).GraphEvents(Events)];
}
void FCombatSkillEditor::GraphSelection(const TSet<UObject*>& Nodes)
{
    for(UObject* O:Nodes) if(auto* N=Cast<UCombatSkillGraphNode>(O)) { Skill=N->Skill; CurrentAsset=Skill; AddEditingObject(Skill); Details->SetObject(Skill); Timeline->Skill=Skill; Preview->SetSkill(Skill); SelectedEvent.Invalidate(); break; }
}
FReply FCombatSkillEditor::Validate()
{
    TArray<UObject*> Assets{RootAsset}; for(UCombatSkillDefinition* S:GraphSkills) { Assets.AddUnique(S); for(const auto& E:S->Events) { if(E.Projectile) Assets.AddUnique(E.Projectile); if(E.Buff) Assets.AddUnique(E.Buff); } }
    const auto Errors=UCombatSkillEditorLibrary::ValidateSkillAssets(Assets);
    ValidationText=Errors.IsEmpty()?TEXT("检查通过。试玩将使用已保存的配置；未保存资源可通过工具栏保存。"):FString::Join(Errors,TEXT("\n")); return FReply::Handled();
}
FReply FCombatSkillEditor::AddEvent()
{
    if(Skill) { const FScopedTransaction T(CTxt(TEXT("添加技能事件"))); Skill->Modify(); auto& E=Skill->Events.AddDefaulted_GetRef(); E.Time=Playhead; E.Label=TEXT("新事件"); Skill->MarkPackageDirty(); SelectEvent(E.Id); }
    return FReply::Handled();
}
FReply FCombatSkillEditor::NewAsset(UClass* Class)
{
    UFactory* Factory=Class==UCombatSkillDefinition::StaticClass()?static_cast<UFactory*>(NewObject<UCombatSkillAssetFactory>()):Class==UCombatProjectileDefinition::StaticClass()?static_cast<UFactory*>(NewObject<UCombatProjectileAssetFactory>()):Class==UCombatBuffDefinition::StaticClass()?static_cast<UFactory*>(NewObject<UCombatBuffAssetFactory>()):NewObject<UCombatSkillSetAssetFactory>();
    if(auto* A=FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get().CreateAssetWithDialog(Class,Factory)) Select(A);
    return FReply::Handled();
}
FReply FCombatSkillEditor::CopySkill()
{
    if(Skill)
    {
        FString Package,Name; FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get().CreateUniqueAssetName(TEXT("/Game/Combat/Skills/Custom/")+Skill->GetName(),TEXT("_Data"),Package,Name);
        if(auto* Copy=UCombatSkillEditorLibrary::CopyAsDataSkill(Skill,Package)) Select(Copy);
        ValidationText=TEXT("已复制。请指定新的 SkillTag。旧蓝图自定义逻辑未转换；发射事件需指定子弹资产。");
    }
    return FReply::Handled();
}
FReply FCombatSkillEditor::Equip()
{
    auto* Set=Cast<UCombatSkillSet>(RootAsset);
    TArray<FAssetData> Selected; FModuleManager::LoadModuleChecked<FContentBrowserModule>(TEXT("ContentBrowser")).Get().GetSelectedAssets(Selected);
    bool Success=false; for(const auto& A:Selected) if(auto* B=Cast<UBlueprint>(A.GetAsset())) Success|=UCombatSkillEditorLibrary::EquipSkillSet(Set,B);
    ValidationText=Success?TEXT("技能集合已装备到选中的角色蓝图，请保存并重新开始 PIE。"):TEXT("请打开技能集合，并在主内容浏览器选中角色蓝图，再点击装备集合。"); return FReply::Handled();
}
FReply FCombatSkillEditor::Play()
{
    ValidationText=UCombatSkillEditorLibrary::StartSkillPreview(Skill,Cast<UCombatSkillSet>(RootAsset))?TEXT("启动真实 PIE 试玩。再次点击重置并重播，Esc 结束预览。"):TEXT("请选择数据驱动技能。");
    return FReply::Handled();
}
FText FCombatSkillEditor::StatusText() const
{
    FString Text=ValidationText;
    if(GEditor && GEditor->PlayWorld) for(TActorIterator<ACombatCharacter> It(GEditor->PlayWorld);It;++It) if(!It->bIsBoss)
    { auto Log=It->SkillRuntime->GetDebugLog(); const int32 Start=FMath::Max(0,Log.Num()-5); for(int32 I=Start;I<Log.Num();++I) Text+=TEXT("\n")+Log[I]; break; }
    return FText::FromString(Text.IsEmpty()?TEXT("选择技能开始编辑。新技能使用数据时间轴；旧技能保留 Montage Notify 执行方式。"):Text);
}
void FCombatSkillEditor::Tick(float DeltaSeconds)
{
    if(bPreviewPlaying && Skill && Timeline && Preview)
    { Playhead=FMath::Fmod(Playhead+DeltaSeconds,FMath::Max(.01f,Skill->Duration)); Timeline->Playhead=Playhead; Preview->Scrub(Playhead); }
    if(GEditor && GEditor->PlayWorld && bMovingTarget)
        for(TActorIterator<ACombatCharacter> It(GEditor->PlayWorld);It;++It) if(It->bIsBoss && It->IsAlive())
        {
            FVector P=It->GetActorLocation(); P.Y=FMath::Sin(GEditor->PlayWorld->GetTimeSeconds()*1.5f)*300.f;
            It->SetActorLocation(P,true);
        }
}
