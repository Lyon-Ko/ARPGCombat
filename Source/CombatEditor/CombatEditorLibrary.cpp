#include "CombatEditorLibrary.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "InputKeyEventArgs.h"

bool UCombatEditorLibrary::InjectPlayerKey(APlayerController* Controller, FName Key, bool bPressed)
{
    if (!IsValid(Controller) || !Controller->GetWorld() || Controller->GetWorld()->WorldType != EWorldType::PIE)
        return false;
    const FKey InputKey(Key);
    if (!InputKey.IsValid()) return false;
    return Controller->InputKey(FInputKeyEventArgs::CreateSimulated(InputKey, bPressed ? IE_Pressed : IE_Released, bPressed ? 1.f : 0.f));
}
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Engine/Font.h"
#include "UObject/SavePackage.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "KismetCompiler.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_VariableGet.h"
#include "K2Node_CallFunction.h"
#include "Kismet/KismetMathLibrary.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSequence.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_StateMachine.h"
#include "AnimGraphNode_StateResult.h"
#include "AnimGraphNode_TransitionResult.h"
#include "AnimGraphNode_BlendSpacePlayer.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_Slot.h"
#include "AnimationStateMachineGraph.h"
#include "AnimationTransitionGraph.h"
#include "AnimStateEntryNode.h"
#include "AnimStateNode.h"
#include "AnimStateTransitionNode.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/UserWidget.h"
#include "WidgetBlueprint.h"
#include "Blueprint/WidgetBlueprintGeneratedClass.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Components/Border.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationSystem.h"
#include "Builders/CubeBuilder.h"
#include "StateTree.h"
#include "StateTreeEditorData.h"
#include "StateTreeState.h"
#include "StateTreeTaskBase.h"
#include "StateTreeCompiler.h"
#include "StateTreeCompilerLog.h"
#include "Components/StateTreeAIComponentSchema.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraSpriteRendererProperties.h"
#include "NiagaraRibbonRendererProperties.h"

namespace CombatAuthoring
{
    bool Save(UObject* Asset)
    {
        if (!Asset) return false;
        Asset->MarkPackageDirty();
        FSavePackageArgs Args;
        Args.TopLevelFlags = RF_Public | RF_Standalone;
        Args.SaveFlags = SAVE_NoError;
        return UPackage::SavePackage(Asset->GetPackage(), Asset,
            *FPackageName::LongPackageNameToFilename(Asset->GetPackage()->GetName(), FPackageName::GetAssetPackageExtension()), Args);
    }
    template<class T> T* Node(UEdGraph* Graph, int X, int Y)
    {
        T* Result = NewObject<T>(Graph);
        Graph->AddNode(Result, false, false);
        Result->CreateNewGuid();
        Result->PostPlacedNewNode();
        Result->AllocateDefaultPins();
        Result->NodePosX = X; Result->NodePosY = Y;
        return Result;
    }
    bool Link(UEdGraphPin* A, UEdGraphPin* B)
    {
        return A && B && A->GetOwningNode()->GetGraph()->GetSchema()->TryCreateConnection(A,B);
    }
    UK2Node_VariableGet* Variable(UEdGraph* Graph, FName Name, int X, int Y)
    {
        auto* N = NewObject<UK2Node_VariableGet>(Graph);
        N->VariableReference.SetSelfMember(Name);
        Graph->AddNode(N,false,false); N->CreateNewGuid(); N->PostPlacedNewNode(); N->AllocateDefaultPins();
        N->NodePosX=X; N->NodePosY=Y;
        return N;
    }
}

bool UCombatEditorLibrary::CompileAndSave(UBlueprint* Blueprint)
{
    if (!Blueprint) return false;
    FCompilerResultsLog Results;
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
    FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Results);
    return Results.NumErrors == 0 && Blueprint->Status != BS_Error && CombatAuthoring::Save(Blueprint);
}

bool UCombatEditorLibrary::RebuildBlendSpace(UBlendSpace* BlendSpace)
{
    if (!BlendSpace || !BlendSpace->GetPathName().StartsWith(TEXT("/Game/Combat/"))) return false;
    BlendSpace->ValidateSampleData();
    BlendSpace->ResampleData();
    return CombatAuthoring::Save(BlendSpace);
}

bool UCombatEditorLibrary::BuildNavBounds(ANavMeshBoundsVolume* Volume, FVector Size)
{
    if (!Volume || Size.GetMin()<=0) return false;
    Volume->Modify();
    auto* Builder=NewObject<UCubeBuilder>(Volume);
    Builder->X=Size.X; Builder->Y=Size.Y; Builder->Z=Size.Z;
    UBrushBuilder* Base=Builder;
    if (!Base->Build(Volume->GetWorld(),Volume)) return false;
    Volume->PostEditChange();
    if (auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(Volume->GetWorld())) Nav->OnNavigationBoundsUpdated(Volume);
    return true;
}

UWidgetBlueprint* UCombatEditorLibrary::CreateHUD(const FString& AssetPath, TSubclassOf<UUserWidget> ParentClass)
{
    using namespace CombatAuthoring;
    if (!ParentClass || !AssetPath.StartsWith(TEXT("/Game/Combat/"))) return nullptr;
    auto* BP=LoadObject<UWidgetBlueprint>(nullptr,*AssetPath);
    if (!BP)
    {
        BP=Cast<UWidgetBlueprint>(FKismetEditorUtilities::CreateBlueprint(ParentClass,CreatePackage(*AssetPath),*FPackageName::GetLongPackageAssetName(AssetPath),BPTYPE_Normal,UWidgetBlueprint::StaticClass(),UWidgetBlueprintGeneratedClass::StaticClass()));
        FAssetRegistryModule::AssetCreated(BP);
    }
    if (!BP || BP->ParentClass!=ParentClass) return nullptr;
    // Rebuild only this generated designer tree; callers never pass template assets.
    BP->WidgetTree=NewObject<UWidgetTree>(BP,MakeUniqueObjectName(BP,UWidgetTree::StaticClass(),TEXT("WidgetTree")),RF_Transactional);
    auto* Tree=BP->WidgetTree.Get();
    UFont* CJKFont=LoadObject<UFont>(nullptr,TEXT("/Game/Combat/UI/F_CombatCJK"));
    if (!CJKFont)
    {
        CJKFont=NewObject<UFont>(CreatePackage(TEXT("/Game/Combat/UI/F_CombatCJK")),TEXT("F_CombatCJK"),RF_Public|RF_Standalone);
        CJKFont->FontCacheType=EFontCacheType::Runtime;
        CJKFont->GetMutableInternalCompositeFont().DefaultTypeface.Fonts.Add(FTypefaceEntry(TEXT("Regular"),FPaths::EngineContentDir()/TEXT("Slate/Fonts/DroidSansFallback.ttf"),EFontHinting::Default,EFontLoadingPolicy::LazyLoad));
        FAssetRegistryModule::AssetCreated(CJKFont); Save(CJKFont);
    }
    auto* Canvas=Tree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(),TEXT("CombatCanvas"));
    Tree->RootWidget=Canvas;
    auto Place=[Canvas](UWidget* W,FVector2D Pos,FVector2D Size,FVector2D Anchor=FVector2D(0,0),FVector2D Align=FVector2D(0,0))
    {
        auto* Slot=Canvas->AddChildToCanvas(W); Slot->SetAnchors(FAnchors(Anchor.X,Anchor.Y)); Slot->SetAlignment(Align); Slot->SetPosition(Pos); Slot->SetSize(Size);
    };
    auto Text=[&](FName Name,const TCHAR* Value,FVector2D Pos,FVector2D Size,int FontSize,FLinearColor Color,FVector2D Anchor=FVector2D(0,0),FVector2D Align=FVector2D(0,0))
    {
        auto* T=Tree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(),Name); T->SetText(FText::FromString(Value));
        auto Font=T->GetFont(); Font.Size=FontSize; Font.FontObject=CJKFont; Font.TypefaceFontName=TEXT("Regular"); T->SetFont(Font); T->SetColorAndOpacity(FSlateColor(Color));
        T->SetShadowOffset(FVector2D(1,2)); T->SetShadowColorAndOpacity(FLinearColor(0,0,0,.8f)); Place(T,Pos,Size,Anchor,Align); return T;
    };
    auto Bar=[&](FName Name,FVector2D Pos,FVector2D Size,FLinearColor Color,FVector2D Anchor=FVector2D(0,0),FVector2D Align=FVector2D(0,0))
    {
        auto* B=Tree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(),Name); B->SetPercent(1); B->SetFillColorAndOpacity(Color);
        B->bIsVariable=false; // Runtime resolves by name; do not shadow its private cached UPROPERTY.
        FProgressBarStyle Style=B->GetWidgetStyle(); Style.BackgroundImage.TintColor=FSlateColor(FLinearColor(.015f,.02f,.027f,.93f));
        Style.FillImage.TintColor=FSlateColor(FLinearColor::White); B->SetWidgetStyle(Style); Place(B,Pos,Size,Anchor,Align); return B;
    };
    const FLinearColor Pale(.86f,.9f,.93f), Gold(.96f,.65f,.24f), Teal(.12f,.75f,.69f), Red(.76f,.14f,.13f);
    Text(TEXT("PlayerLabel"),TEXT("霜刃 · 生命"),{40,-185},{360,30},20,Pale,{0,1},{0,1});
    Bar(TEXT("HealthBar"),{40,-143},{330,18},Teal,{0,1},{0,1});
    Text(TEXT("HealthText"),TEXT("300 / 300"),{40,-112},{330,24},15,Pale,{0,1},{0,1});
    Text(TEXT("BossTitle"),TEXT("烬锋 · 铁卫"),{0,32},{600,35},24,Pale,{.5,0},{.5,0})->SetJustification(ETextJustify::Center);
    Bar(TEXT("BossHealthBar"),{0,76},{620,18},Red,{.5,0},{.5,0});
    Bar(TEXT("BossPoiseBar"),{0,99},{620,6},Gold,{.5,0},{.5,0});
    Text(TEXT("PhaseText"),TEXT("第一阶段"),{0,116},{600,26},16,Gold,{.5,0},{.5,0})->SetJustification(ETextJustify::Center);
    Text(TEXT("LockText"),TEXT("Q  锁定目标"),{-40,-110},{250,28},18,Pale,{1,1},{1,1})->SetJustification(ETextJustify::Right);
    Text(TEXT("ParryText"),TEXT("精准格挡 · 左键反击"),{0,-120},{650,40},22,Gold,{.5,1},{.5,1})->SetJustification(ETextJustify::Center);
    Text(TEXT("ControlsText"),TEXT("WASD 移动    左键 连击 / 空中长按下劈    右键 弹反\nShift 闪避    空格 二段跳    Q 锁定    P 暂停"),{40,-36},{1100,62},16,Pale,{0,1},{0,1});
    Text(TEXT("ResultText"),TEXT(""),{0,-20},{800,90},42,Gold,{.5,.5},{.5,.5})->SetJustification(ETextJustify::Center);
    Text(TEXT("PauseText"),TEXT(""),{0,65},{800,55},26,Pale,{.5,.5},{.5,.5})->SetJustification(ETextJustify::Center);
    return CompileAndSave(BP)?BP:nullptr;
}

UAnimBlueprint* UCombatEditorLibrary::CreateLocomotion(const FString& AssetPath,TSubclassOf<UAnimInstance> ParentClass,USkeleton* Skeleton,UBlendSpace* BlendSpace,UAnimSequence* AirSequence)
{
    using namespace CombatAuthoring;
    if (!ParentClass || !Skeleton || !BlendSpace || !AirSequence || !AssetPath.StartsWith(TEXT("/Game/Combat/"))) return nullptr;
    auto* BP=LoadObject<UAnimBlueprint>(nullptr,*AssetPath);
    if (BP) return CompileAndSave(BP)?BP:nullptr;
    BP=Cast<UAnimBlueprint>(FKismetEditorUtilities::CreateBlueprint(ParentClass,CreatePackage(*AssetPath),*FPackageName::GetLongPackageAssetName(AssetPath),BPTYPE_Normal,UAnimBlueprint::StaticClass(),UAnimBlueprintGeneratedClass::StaticClass()));
    if (!BP) return nullptr;
    BP->TargetSkeleton=Skeleton;
    FAssetRegistryModule::AssetCreated(BP);
    UEdGraph* Graph=FBlueprintEditorUtils::FindEventGraph(BP);
    for (UEdGraph* G:BP->FunctionGraphs) if (G->GetFName()==TEXT("AnimGraph")) Graph=G;
    TArray<UAnimGraphNode_Root*> Roots; Graph->GetNodesOfClass(Roots);
    if (Roots.IsEmpty()) return nullptr;
    auto* Machine=Node<UAnimGraphNode_StateMachine>(Graph,-600,0);
    Machine->OnRenameNode(TEXT("Locomotion"));
    auto* Slot=Node<UAnimGraphNode_Slot>(Graph,-240,0); Slot->Node.SlotName=TEXT("DefaultSlot");
    if (!Link(Machine->FindPin(TEXT("Pose")),Slot->FindPin(TEXT("Source"))) || !Link(Slot->FindPin(TEXT("Pose")),Roots[0]->FindPin(TEXT("Result")))) return nullptr;
    auto* SM=Machine->EditorStateMachineGraph.Get();
    auto* Ground=Node<UAnimStateNode>(SM,180,0); Ground->OnRenameNode(TEXT("Grounded"));
    auto* Air=Node<UAnimStateNode>(SM,500,0); Air->OnRenameNode(TEXT("Airborne"));
    TArray<UAnimStateEntryNode*> Entries; SM->GetNodesOfClass(Entries);
    if (Entries.IsEmpty() || !Link(Entries[0]->GetOutputPin(),Ground->GetInputPin())) return nullptr;
    auto* Player=Node<UAnimGraphNode_BlendSpacePlayer>(Ground->BoundGraph,-150,0);
    Player->Node.SetBlendSpace(BlendSpace); Player->ReconstructNode();
    auto* Speed=Variable(Ground->BoundGraph,TEXT("Speed"),-430,60);
    Link(Speed->GetValuePin(),Player->FindPin(TEXT("X")));
    Link(Player->FindPin(TEXT("Pose")),Ground->GetPoseSinkPinInsideState());
    auto* Fall=Node<UAnimGraphNode_SequencePlayer>(Air->BoundGraph,-150,0); Fall->Node.SetSequence(AirSequence); Fall->Node.SetLoopAnimation(true); Fall->ReconstructNode();
    Link(Fall->FindPin(TEXT("Pose")),Air->GetPoseSinkPinInsideState());
    for (int I=0;I<2;++I)
    {
        auto* T=Node<UAnimStateTransitionNode>(SM,350,I?130:-130); T->CreateConnections(I?Air:Ground,I?Ground:Air); T->CrossfadeDuration=.12f;
        auto* TG=CastChecked<UAnimationTransitionGraph>(T->BoundGraph);
        auto* InAir=Variable(TG,TEXT("bInAir"),-400,0);
        UEdGraphPin* Value=InAir->GetValuePin();
        if (I)
        {
            auto* Not=NewObject<UK2Node_CallFunction>(TG);
            Not->SetFromFunction(UKismetMathLibrary::StaticClass()->FindFunctionByName(TEXT("Not_PreBool")));
            TG->AddNode(Not,false,false); Not->CreateNewGuid(); Not->AllocateDefaultPins(); Not->NodePosX=-200;
            Link(Value,Not->FindPin(TEXT("A"))); Value=Not->GetReturnValuePin();
        }
        Link(Value,TG->GetResultNode()->FindPin(TEXT("bCanEnterTransition")));
    }
    return CompileAndSave(BP)?BP:nullptr;
}

UStateTree* UCombatEditorLibrary::CreateCombatStateTree(const FString& AssetPath,const TArray<FString>& TaskStructPaths)
{
    using namespace CombatAuthoring;
    if (TaskStructPaths.IsEmpty() || !AssetPath.StartsWith(TEXT("/Game/Combat/"))) return nullptr;
    TArray<UScriptStruct*> Types;
    for (const FString& Path:TaskStructPaths)
    {
        auto* S=LoadObject<UScriptStruct>(nullptr,*Path);
        if (!S || !S->IsChildOf(FStateTreeTaskBase::StaticStruct())) return nullptr;
        Types.Add(S);
    }
    auto* Tree=LoadObject<UStateTree>(nullptr,*AssetPath);
    if (!Tree) { Tree=NewObject<UStateTree>(CreatePackage(*AssetPath),*FPackageName::GetLongPackageAssetName(AssetPath),RF_Public|RF_Standalone|RF_Transactional); FAssetRegistryModule::AssetCreated(Tree); }
    auto* Data=NewObject<UStateTreeEditorData>(Tree,NAME_None,RF_Transactional);
    Tree->EditorData=Data; Data->Schema=NewObject<UStateTreeAIComponentSchema>(Data);
    auto& Root=Data->AddSubTree(TEXT("Combat"));
    TArray<UStateTreeState*> States;
    for (int I=0;I<Types.Num();++I)
    {
        auto& State=Root.AddChildState(*Types[I]->GetName()); States.Add(&State);
        State.Tasks.AddDefaulted_GetRef().InitializeAs(&State,Types[I]);
    }
    for (int I=0;I<States.Num();++I) States[I]->AddTransition(EStateTreeTransitionTrigger::OnStateCompleted,EStateTreeTransitionType::GotoState,States[(I+1)%States.Num()]);
    FStateTreeCompilerLog Log; FStateTreeCompiler Compiler(Log);
    if (!Compiler.Compile(*Tree)) { Log.DumpToLog(LogTemp); return nullptr; }
    return Save(Tree)?Tree:nullptr;
}

bool UCombatEditorLibrary::ConfigureNiagara(UNiagaraSystem* System,FLinearColor Color,float SpriteSize,float RibbonWidth)
{
    if (!System || !System->GetPathName().StartsWith(TEXT("/Game/Combat/"))) return false;
    System->Modify();
    auto& Params=System->GetExposedParameters();
    Params.SetParameterValue(Color,FNiagaraVariable(FNiagaraTypeDefinition::GetColorDef(),TEXT("User.Tint")),true);
    Params.SetParameterValue(FVector2f(SpriteSize,SpriteSize),FNiagaraVariable(FNiagaraTypeDefinition::GetVec2Def(),TEXT("User.SpriteSize")),true);
    Params.SetParameterValue(RibbonWidth,FNiagaraVariable(FNiagaraTypeDefinition::GetFloatDef(),TEXT("User.RibbonWidth")),true);
    int32 BoundRenderers=0;
    for (auto& Handle:System->GetEmitterHandles())
    {
        const FVersionedNiagaraEmitterBase Emitter(Handle.GetEmitterBase(),Handle.GetInstance().Version);
        if (auto* Data=Handle.GetEmitterData())
        {
            for (auto* Renderer:Data->GetRenderers())
            {
                if (auto* Sprite=Cast<UNiagaraSpriteRendererProperties>(Renderer))
                {
                    Sprite->ColorBinding.SetValue(TEXT("User.Tint"),Emitter,Sprite->GetCurrentSourceMode());
                    Sprite->SpriteSizeBinding.SetValue(TEXT("User.SpriteSize"),Emitter,Sprite->GetCurrentSourceMode());
                    ++BoundRenderers;
                }
                if (auto* Ribbon=Cast<UNiagaraRibbonRendererProperties>(Renderer))
                {
                    Ribbon->ColorBinding.SetValue(TEXT("User.Tint"),Emitter,Ribbon->GetCurrentSourceMode());
                    Ribbon->RibbonWidthBinding.SetValue(TEXT("User.RibbonWidth"),Emitter,Ribbon->GetCurrentSourceMode());
                    ++BoundRenderers;
                }
            }
        }
    }
    System->RequestCompile(false);
    return BoundRenderers>0 && CombatAuthoring::Save(System);
}
