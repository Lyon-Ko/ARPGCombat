#include "CombatSkillEditorTypes.h"
#include "CombatSkillEditor.h"
#include "CombatCharacter.h"
#include "CombatGameMode.h"
#include "CombatAnimNotify.h"
#include "Animation/AnimMontage.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "ScopedTransaction.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "GameplayTagsManager.h"
#include "Editor.h"
#include "PlayInEditorDataTypes.h"
#include "EngineUtils.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "SGraphNodeDefault.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameViewportClient.h"
#include "Slate/SceneViewport.h"

class SCombatGraphNode : public SGraphNodeDefault
{
public:
    SLATE_BEGIN_ARGS(SCombatGraphNode) {} SLATE_END_ARGS()
    void Construct(const FArguments&,UEdGraphNode* Node) { SGraphNodeDefault::Construct(SGraphNodeDefault::FArguments().GraphNodeObj(Node)); }
    virtual void MoveTo(const FVector2f& Position,FNodeSet& Filter,bool bDirty=true) override
    {
        if(auto* Node=Cast<UCombatSkillGraphNode>(GraphNode); Node && Node->Skill)
        { Node->Skill->Modify(); Node->Skill->GraphPosition=FVector2D(Position); Node->Skill->MarkPackageDirty(); }
        SGraphNodeDefault::MoveTo(Position,Filter,bDirty);
    }
};
TSharedPtr<SGraphNode> UCombatSkillGraphNode::CreateVisualWidget() { return SNew(SCombatGraphNode,this); }

UCombatSkillAssetFactory::UCombatSkillAssetFactory() { SupportedClass = UCombatSkillDefinition::StaticClass(); bCreateNew = bEditAfterNew = true; }
UObject* UCombatSkillAssetFactory::FactoryCreateNew(UClass* Class,UObject* Parent,FName Name,EObjectFlags Flags,UObject*,FFeedbackContext*)
{ auto* D=NewObject<UCombatSkillDefinition>(Parent,Class,Name,Flags|RF_Transactional); D->bDataDriven=true; D->bUseMontageNotifies=true; D->SchemaVersion=2; return D; }
#define COMBAT_FACTORY(Factory,Asset) \
Factory::Factory() { SupportedClass=Asset::StaticClass(); bCreateNew=bEditAfterNew=true; } \
UObject* Factory::FactoryCreateNew(UClass* Class,UObject* Parent,FName Name,EObjectFlags Flags,UObject*,FFeedbackContext*) { return NewObject<Asset>(Parent,Class,Name,Flags|RF_Transactional); }
COMBAT_FACTORY(UCombatProjectileAssetFactory,UCombatProjectileDefinition)
COMBAT_FACTORY(UCombatBuffAssetFactory,UCombatBuffDefinition)
COMBAT_FACTORY(UCombatSkillSetAssetFactory,UCombatSkillSet)
#undef COMBAT_FACTORY

void UCombatSkillGraphNode::AllocateDefaultPins()
{
    CreatePin(EGPD_Input,TEXT("Skill"),TEXT("进入"));
    if(Skill) for(int32 I=0;I<Skill->Derivations.Num();++I)
    {
        const auto& D=Skill->Derivations[I];
        auto* Pin=CreatePin(EGPD_Output,TEXT("Skill"),*FString::FromInt(I));
        Pin->PinFriendlyName=FText::FromString(Skill->bUseMontageNotifies && Skill->Montage
            ? FString::Printf(TEXT("%d · %s · %s"),I,*StaticEnum<ECombatDerivationTrigger>()->GetDisplayNameTextByValue(int64(D.Trigger)).ToString(),D.WindowName.IsNone()?TEXT("无窗口限制"):*D.WindowName.ToString())
            : FString::Printf(TEXT("%d · %s · %.2f–%.2fs"),I,*StaticEnum<ECombatDerivationTrigger>()->GetDisplayNameTextByValue(int64(D.Trigger)).ToString(),D.WindowStart,D.WindowEnd));
    }
    auto* Pin=CreatePin(EGPD_Output,TEXT("Skill"),TEXT("New")); Pin->PinFriendlyName=FText::FromString(TEXT("＋ 新建派生"));
}
FText UCombatSkillGraphNode::GetNodeTitle(ENodeTitleType::Type) const
{ return FText::FromString(Skill ? Skill->GetName()+TEXT("\n")+Skill->SkillTag.ToString() : TEXT("缺失技能")); }
const FPinConnectionResponse UCombatSkillGraphSchema::CanCreateConnection(const UEdGraphPin* A,const UEdGraphPin* B) const
{
    if(!A || !B || A->Direction==B->Direction) return FPinConnectionResponse(CONNECT_RESPONSE_DISALLOW,TEXT("连接输出到输入"));
    return FPinConnectionResponse(CONNECT_RESPONSE_BREAK_OTHERS_A,TEXT("设置技能派生"));
}
bool UCombatSkillGraphSchema::TryCreateConnection(UEdGraphPin* A,UEdGraphPin* B) const
{
    if(CanCreateConnection(A,B).Response==CONNECT_RESPONSE_DISALLOW) return false;
    UEdGraphPin* Out=A->Direction==EGPD_Output?A:B; UEdGraphPin* In=A->Direction==EGPD_Input?A:B;
    auto* From=Cast<UCombatSkillGraphNode>(Out->GetOwningNode()); auto* To=Cast<UCombatSkillGraphNode>(In->GetOwningNode());
    if(!From || !To || !From->Skill || !To->Skill) return false;
    const FScopedTransaction Transaction(FText::FromString(TEXT("连接技能派生"))); From->Skill->Modify(); From->Modify(); To->Modify();
    int32 Index=FCString::Atoi(*Out->PinName.ToString());
    if(Out->PinName==TEXT("New"))
    {
        Index=From->Skill->Derivations.AddDefaulted(); auto& Rule=From->Skill->Derivations[Index];
        Rule.InputTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Input.Attack")); Rule.WindowEnd=From->Skill->Duration;
        Out->PinName=*FString::FromInt(Index); Out->PinFriendlyName=FText::FromString(FString::Printf(TEXT("%d · Input"),Index));
        From->CreatePin(EGPD_Output,TEXT("Skill"),TEXT("New"))->PinFriendlyName=FText::FromString(TEXT("＋ 新建派生"));
    }
    if(!From->Skill->Derivations.IsValidIndex(Index)) return false;
    From->Skill->Derivations[Index].TargetSkill=To->Skill->SkillTag;
    Out->BreakAllPinLinks(); Out->MakeLinkTo(In); From->Skill->MarkPackageDirty(); From->GetGraph()->NotifyGraphChanged(); return true;
}
void UCombatSkillGraphSchema::BreakPinLinks(UEdGraphPin& Pin,bool bNotify) const
{
    const FScopedTransaction Transaction(FText::FromString(TEXT("移除技能派生连接")));
    TArray<UEdGraphPin*> Outputs=Pin.Direction==EGPD_Output?TArray<UEdGraphPin*>{&Pin}:Pin.LinkedTo;
    for(auto* Out:Outputs)
    {
        auto* Node=Cast<UCombatSkillGraphNode>(Out->GetOwningNode());
        const int32 Index=FCString::Atoi(*Out->PinName.ToString());
        if(Node && Node->Skill && Out->PinName!=TEXT("New") && Node->Skill->Derivations.IsValidIndex(Index))
        { Node->Skill->Modify(); Node->Skill->Derivations[Index].TargetSkill=FGameplayTag(); Node->Skill->MarkPackageDirty(); }
    }
    Super::BreakPinLinks(Pin,bNotify);
}
void UCombatSkillGraphSchema::OnPinConnectionDoubleCicked(UEdGraphPin* A,UEdGraphPin* B,const FVector2f&) const
{
    auto* Out=A->Direction==EGPD_Output?A:B;
    if(auto* Node=Cast<UCombatSkillGraphNode>(Out->GetOwningNode()))
        if(auto* G=Cast<UCombatSkillGraph>(Node->GetGraph()); G && G->OnSelectRule) G->OnSelectRule(Node->Skill,FCString::Atoi(*Out->PinName.ToString()));
}

TArray<FString> UCombatSkillEditorLibrary::ValidateSkillAssets(const TArray<UObject*>& Assets)
{
    TArray<FString> Errors; TArray<UObject*> All=Assets;
    for(int32 Index=0;Index<All.Num();++Index)
    {
        UObject* A=All[Index];
        if(auto* Set=Cast<UCombatSkillSet>(A)) for(auto& S:Set->Skills) All.AddUnique(S);
        if(auto* S=Cast<UCombatSkillDefinition>(A)) for(const auto& E:S->Events) { if(E.Projectile) All.AddUnique(E.Projectile); if(E.Buff) All.AddUnique(E.Buff); }
        if(auto* S=Cast<UCombatSkillDefinition>(A); S && S->bUseMontageNotifies && S->Montage)
            for(const auto& N:S->Montage->Notifies) if(auto* Action=Cast<UCombatAnimNotify_SkillAction>(N.Notify)) { if(Action->Action.Projectile) All.AddUnique(Action->Action.Projectile); if(Action->Action.Buff) All.AddUnique(Action->Action.Buff); }
        if(auto* P=Cast<UCombatProjectileDefinition>(A); P && P->HitBuff) All.AddUnique(P->HitBuff);
    }
    TMap<FGameplayTag,UCombatSkillDefinition*> Skills;
    auto Error=[&](UObject* A,const FString& Message) { Errors.Add(GetNameSafe(A)+TEXT(": ")+Message); };
    for(UObject* A:All)
    {
        if(auto* S=Cast<UCombatSkillDefinition>(A))
        {
            if(!S->SkillTag.IsValid()) Error(S,TEXT("技能标签未登记"));
            else if(Skills.Contains(S->SkillTag) && Skills[S->SkillTag]!=S) Error(S,TEXT("技能标签重复"));
            else Skills.Add(S->SkillTag,S);
            if(!S->bDataDriven) continue;
            if(!FMath::IsFinite(S->Duration) || S->Duration<=0) Error(S,TEXT("持续时间必须为有限正数"));
            if(S->bAirOnly && S->bGroundOnly) Error(S,TEXT("不能同时限制地面与空中"));
            TSet<FGuid> Ids;
            const bool Native=S->bUseMontageNotifies && S->Montage;
            TSet<FName> NamedWindows;
            if(Native)
            {
                if(!S->Events.IsEmpty()) Error(S,TEXT("原生模式不执行旧 Events；请先关闭原生模式，再用转换按钮迁移。"));
                for(const auto& N:S->Montage->Notifies)
                {
                    if(auto* Window=Cast<UCombatAnimNotifyState_SkillWindow>(N.NotifyStateClass))
                    {
                        if(N.GetDuration()<=0 || N.GetTime()<0 || N.GetTime()+N.GetDuration()>S->Montage->GetPlayLength()+.001f) Error(S,TEXT("Montage 技能窗口范围无效"));
                        if(Window->WindowType==ECombatSkillWindowType::Derivation)
                        { if(Window->WindowName.IsNone()) Error(S,TEXT("Montage 派生窗口缺少名字")); else NamedWindows.Add(Window->WindowName); }
                    }
                    if(auto* Action=Cast<UCombatAnimNotify_SkillAction>(N.Notify))
                    {
                        const auto& E=Action->Action;
                        if(E.Type==ECombatSkillEventType::HitWindow || E.Type==ECombatSkillEventType::ComboWindow || E.Type==ECombatSkillEventType::CancelWindow) Error(S,TEXT("持续窗口必须使用 Combat Skill Window 通知状态"));
                        if(E.Type==ECombatSkillEventType::Projectile && !E.Projectile) Error(S,TEXT("Montage 发射事件缺少子弹资产"));
                        if((E.Type==ECombatSkillEventType::ApplyBuff || E.Type==ECombatSkillEventType::RemoveBuff) && !E.Buff) Error(S,TEXT("Montage Buff 事件缺少资产"));
                    }
                }
            }
            if(!Native) for(const auto& E:S->Events)
            {
                if(!E.Id.IsValid() || Ids.Contains(E.Id)) Error(S,TEXT("事件 GUID 缺失或重复，请复制事件而非复制 GUID")); Ids.Add(E.Id);
                if(!FMath::IsFinite(E.Time) || E.Time<0 || E.Time>S->Duration || !FMath::IsFinite(E.Duration) || E.Duration<0) Error(S,TEXT("事件时间超出技能范围"));
                if((E.Type==ECombatSkillEventType::HitWindow || E.Type==ECombatSkillEventType::CancelWindow || E.Type==ECombatSkillEventType::ComboWindow) && E.Time+E.Duration>S->Duration) Error(S,TEXT("窗口结束超过技能时长"));
                if(E.Type==ECombatSkillEventType::Projectile && !E.Projectile) Error(S,TEXT("发射事件缺少子弹资产"));
                if(E.Type==ECombatSkillEventType::Projectile && E.Time+(E.Bursts-1)*E.BurstInterval>S->Duration) Error(S,TEXT("连发超出技能时长"));
                if((E.Type==ECombatSkillEventType::ApplyBuff || E.Type==ECombatSkillEventType::RemoveBuff) && !E.Buff) Error(S,TEXT("Buff 事件缺少资产"));
            }
            for(const auto& R:S->Derivations)
            {
                if(!R.TargetSkill.IsValid()) Error(S,TEXT("派生目标为空"));
                if(!Native && (R.WindowStart<0 || R.WindowEnd<R.WindowStart || R.WindowEnd>S->Duration)) Error(S,TEXT("派生窗口无效"));
                if(Native && !R.WindowName.IsNone() && !NamedWindows.Contains(R.WindowName)) Error(S,TEXT("Montage 中不存在命名派生窗口：")+R.WindowName.ToString());
                if(Native && R.Trigger==ECombatDerivationTrigger::Completed && !R.WindowName.IsNone()) Error(S,TEXT("结束派生不应引用已经结束的 Montage 窗口"));
                if(R.Trigger==ECombatDerivationTrigger::Input && !R.InputTag.IsValid()) Error(S,TEXT("输入派生缺少输入标签"));
            }
        }
        if(auto* P=Cast<UCombatProjectileDefinition>(A))
        {
            if(!FMath::IsFinite(P->Speed) || !FMath::IsFinite(P->MaxSpeed) || !FMath::IsFinite(P->Lifetime) || !FMath::IsFinite(P->MaxDistance) || P->Speed<=0 || P->MaxSpeed<P->Speed || P->Lifetime<=0 || P->MaxDistance<=0) Error(P,TEXT("速度、寿命或距离无效"));
            if(P->Penetrations<0 || P->Bounces<0 || P->Radius<=0) Error(P,TEXT("碰撞参数无效"));
        }
        if(auto* B=Cast<UCombatBuffDefinition>(A))
        {
            if(!B->BuffTag.IsValid()) Error(B,TEXT("Buff 标签未登记"));
            if(B->MaxStacks<1 || B->Period<=0 || B->Duration<=0) Error(B,TEXT("叠层或时间无效"));
            for(const auto& M:B->AttributeModifiers) if(!M.Attribute.IsValid() || !FMath::IsFinite(M.Additive) || !FMath::IsFinite(M.Multiplier) || M.Multiplier<=0) Error(B,TEXT("属性修改器无效"));
        }
    }
    for(const auto& Pair:Skills) for(const auto& R:Pair.Value->Derivations)
        if(!Skills.Contains(R.TargetSkill)) Error(Pair.Value,TEXT("派生目标不在当前技能集合：")+R.TargetSkill.ToString());
    TSet<UCombatSkillDefinition*> Visiting,Done;
    TFunction<void(UCombatSkillDefinition*)> Visit=[&](UCombatSkillDefinition* S)
    {
        if(Visiting.Contains(S)) { Error(S,TEXT("存在自动派生循环")); return; } if(Done.Contains(S)) return;
        Visiting.Add(S);
        for(const auto& R:S->Derivations) if(R.Trigger!=ECombatDerivationTrigger::Input) if(auto* const* Next=Skills.Find(R.TargetSkill)) Visit(*Next);
        Visiting.Remove(S); Done.Add(S);
    };
    for(const auto& Pair:Skills) Visit(Pair.Value);
    return Errors;
}

static void SaveCombatAsset(UObject* Asset)
{
    Asset->MarkPackageDirty(); FSavePackageArgs Args; Args.TopLevelFlags=RF_Public|RF_Standalone; Args.SaveFlags=SAVE_NoError;
    UPackage::SavePackage(Asset->GetOutermost(),Asset,*FPackageName::LongPackageNameToFilename(Asset->GetOutermost()->GetName(),FPackageName::GetAssetPackageExtension()),Args);
}
template<class T> static T* NewCombatAsset(const FString& Path)
{
    if(auto* Existing=LoadObject<T>(nullptr,*Path)) return Existing;
    auto* Asset=NewObject<T>(CreatePackage(*Path),*FPackageName::GetLongPackageAssetName(Path),RF_Public|RF_Standalone|RF_Transactional);
    FAssetRegistryModule::AssetCreated(Asset); return Asset;
}
UCombatSkillDefinition* UCombatSkillEditorLibrary::CopyAsDataSkill(UCombatSkillDefinition* Source,const FString& Destination)
{
    if(!Source || !FPackageName::IsValidLongPackageName(Destination) || FPackageName::DoesPackageExist(Destination)) return nullptr;
    auto* Copy=DuplicateObject<UCombatSkillDefinition>(Source,CreatePackage(*Destination),*FPackageName::GetLongPackageAssetName(Destination));
    Copy->SetFlags(RF_Public|RF_Standalone|RF_Transactional); Copy->bDataDriven=true; Copy->AbilityClass=nullptr; Copy->SkillTag=FGameplayTag();
    if(!Source->bDataDriven && Copy->Montage)
    {
        Copy->Duration=Copy->Montage->GetPlayLength();
        Copy->Events.Reset();
        const TMap<FString,ECombatSkillEventType> Types={{TEXT("Move"),ECombatSkillEventType::Movement},{TEXT("Projectile"),ECombatSkillEventType::Projectile},{TEXT("AreaWarning"),ECombatSkillEventType::AreaWarning},{TEXT("AreaRelease"),ECombatSkillEventType::AreaRelease},{TEXT("HitOpen"),ECombatSkillEventType::HitWindow},{TEXT("ComboOpen"),ECombatSkillEventType::ComboWindow},{TEXT("Cancelable"),ECombatSkillEventType::CancelWindow},{TEXT("Finish"),ECombatSkillEventType::Finish}};
        for(const auto& N:Copy->Montage->Notifies) if(auto* Notify=Cast<UCombatAnimNotify_Event>(N.Notify))
        {
            FString Name=Notify->EventTag.ToString(); Name.RemoveFromStart(TEXT("Combat.Event."));
            if(const auto* Type=Types.Find(Name))
            {
                auto& E=Copy->Events.AddDefaulted_GetRef(); E.Type=*Type; E.Time=N.GetTriggerTime(); E.Label=Name; E.Duration=FMath::Max(0.f,Copy->Duration-E.Time);
                if(E.Type==ECombatSkillEventType::HitWindow) for(const auto& Close:Copy->Montage->Notifies) if(auto* End=Cast<UCombatAnimNotify_Event>(Close.Notify); End && End->EventTag.ToString()==TEXT("Combat.Event.HitClose") && Close.GetTriggerTime()>E.Time) E.Duration=FMath::Min(E.Duration,Close.GetTriggerTime()-E.Time);
            }
        }
        UE_LOG(LogTemp,Warning,TEXT("Copied known montage events only. Custom Blueprint logic is NOT converted. Assign a new skill tag and projectile definitions before use."));
    }
    if(!Source->bDataDriven && Source->NextSkillTag.IsValid())
    {
        FCombatSkillDerivation Rule; Rule.TargetSkill=Source->NextSkillTag; Rule.InputTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Input.Attack")); Rule.WindowEnd=Copy->Duration;
        for(const auto& E:Copy->Events) if(E.Type==ECombatSkillEventType::ComboWindow) { Rule.WindowStart=E.Time; break; }
        Copy->Derivations.Add(Rule);
    }
    Copy->NextSkillTag=FGameplayTag();
    for(auto& E:Copy->Events) E.Id=FGuid::NewGuid(); for(auto& R:Copy->Derivations) R.Id=FGuid::NewGuid();
    FAssetRegistryModule::AssetCreated(Copy); Copy->MarkPackageDirty(); return Copy;
}
bool UCombatSkillEditorLibrary::EquipSkillSet(UCombatSkillSet* Set,UBlueprint* Blueprint)
{
    if(!Set || !Blueprint || !Blueprint->GeneratedClass || !Blueprint->GeneratedClass->IsChildOf(ACombatCharacter::StaticClass())) return false;
    if(!ValidateSkillAssets({Set}).IsEmpty()) return false;
    auto* Default=Cast<ACombatCharacter>(Blueprint->GeneratedClass->GetDefaultObject());
    if(Default && Default->GetMesh()->GetSkeletalMeshAsset()) for(UCombatSkillDefinition* S:Set->Skills)
        if(S && S->Montage && S->Montage->GetSkeleton()!=Default->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton())
        { UE_LOG(LogTemp,Error,TEXT("Skill %s montage skeleton does not match character"),*S->GetName()); return false; }
    const FScopedTransaction Transaction(FText::FromString(TEXT("装备技能集合"))); Blueprint->Modify();
    auto* C=Cast<ACombatCharacter>(Blueprint->GeneratedClass->GetDefaultObject()); C->Modify(); C->DesignerSkillSet=Set;
    FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint); FKismetEditorUtilities::CompileBlueprint(Blueprint); return Blueprint->Status!=BS_Error;
}
void UCombatSkillEditorLibrary::OpenSkillEditor(UObject* Asset) { if(Asset) FCombatSkillEditor::Open(Asset); }

bool UCombatSkillEditorLibrary::StartSkillPreview(UCombatSkillDefinition* Skill,UCombatSkillSet* Set)
{
    if(!GEditor || !Skill || !Skill->bDataDriven) return false;
    TArray<UObject*> ToValidate{Skill}; if(Set) ToValidate.Add(Set);
    if(!ValidateSkillAssets(ToValidate).IsEmpty()) return false;
    auto Run=[WeakSkill=TWeakObjectPtr<UCombatSkillDefinition>(Skill),WeakSet=TWeakObjectPtr<UCombatSkillSet>(Set)]
    {
        if(!GEditor || !GEditor->PlayWorld || !WeakSkill.IsValid()) return;
        if(auto* Mode=GEditor->PlayWorld->GetAuthGameMode<ACombatGameMode>()) Mode->SpawnBoss();
        ACombatCharacter* Player=nullptr; ACombatCharacter* Target=nullptr;
        for(TActorIterator<ACombatCharacter> It(GEditor->PlayWorld);It;++It)
        {
            if(It->bIsBoss) { Target=*It; if(auto* AI=Cast<AAIController>(It->GetController())) if(AI->BrainComponent) AI->BrainComponent->StopLogic(TEXT("Skill editor preview")); }
            else Player=*It;
        }
        if(!Player) return;
        Player->ResetCombatState(); if(Target) { Target->ResetCombatState(); if(auto* AI=Cast<AAIController>(Target->GetController())) if(AI->BrainComponent) AI->BrainComponent->StopLogic(TEXT("Skill editor preview")); }
        TArray<UCombatSkillDefinition*> Skills; if(WeakSet.IsValid()) for(UCombatSkillDefinition* S:WeakSet->Skills) Skills.Add(S); Skills.AddUnique(WeakSkill.Get());
        Player->EquipRuntimeSkills(Skills);
        Player->SetActorLocation(FVector(0,0,100)); Player->SetActorRotation(FRotator::ZeroRotator);
        if(Target) { Target->SetActorLocation(FVector(650,0,100)); Player->SetCombatTarget(Target); }
        Player->RequestSkillByTag(WeakSkill->SkillTag);
    };
    if(GEditor->PlayWorld) { Run(); return true; }
    auto Handle=MakeShared<FDelegateHandle>();
    *Handle=FEditorDelegates::PostPIEStarted.AddLambda([Run,Handle](bool){FEditorDelegates::PostPIEStarted.Remove(*Handle); Run();});
    FRequestPlaySessionParams Params; Params.SessionDestination=EPlaySessionDestinationType::InProcess; Params.WorldType=EPlaySessionWorldType::PlayInEditor; Params.bAllowOnlineSubsystem=false;
    Params.GlobalMapOverride=FPackageName::DoesPackageExist(TEXT("/Game/Combat/SkillEditorExamples/L_SkillEditorTest"))?TEXT("/Game/Combat/SkillEditorExamples/L_SkillEditorTest"):TEXT("/Game/Combat/Maps/L_CombatArena");
    GEditor->RequestPlaySession(Params); return true;
}
 AActor* UCombatSkillEditorLibrary::SpawnPreviewObstacle(FVector Location,FVector Size)
{
    if(!GEditor || !GEditor->PlayWorld) return nullptr;
    FActorSpawnParameters P; P.ObjectFlags|=RF_Transient;
    auto* A=GEditor->PlayWorld->SpawnActor<AStaticMeshActor>(Location,FRotator::ZeroRotator,P);
    if(A)
    {
        A->SetMobility(EComponentMobility::Movable); A->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        A->SetActorScale3D(Size.GetAbs()/100.f); A->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll")); A->SetActorLabel(TEXT("SkillPreview_Obstacle"));
    }
    return A;
}
AActor* UCombatSkillEditorLibrary::SpawnPreviewTarget(FVector Location,bool bHostile)
{
    if(!GEditor || !GEditor->PlayWorld) return nullptr;
    UClass* Class=LoadClass<ACombatCharacter>(nullptr,TEXT("/Game/Combat/Characters/BP_CombatBoss.BP_CombatBoss_C"));
    if(!Class) return nullptr;
    auto* A=GEditor->PlayWorld->SpawnActorDeferred<ACombatCharacter>(Class,FTransform(Location),nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(A)
    {
        A->bIsBoss=bHostile; A->SetFlags(RF_Transient); A->FinishSpawning(FTransform(Location)); A->SetActorLabel(TEXT("SkillPreview_Target"));
        if(auto* AI=Cast<AAIController>(A->GetController())) if(AI->BrainComponent) AI->BrainComponent->StopLogic(TEXT("Preview target"));
    }
    return A;
}
bool UCombatSkillEditorLibrary::SetPreviewResolution(int32 Width,int32 Height)
{
    if(!GEditor || !GEditor->PlayWorld || Width<320 || Height<240 || Width>7680 || Height>4320) return false;
    auto* Client=GEditor->PlayWorld->GetGameViewport();
    auto* Viewport=Client?Client->GetGameViewport():nullptr;
    if(!Viewport) return false;
    Viewport->SetFixedViewportSize(Width,Height); return Viewport->GetSizeXY()==FIntPoint(Width,Height);
}

UCombatSkillSet* UCombatSkillEditorLibrary::CreateExamples()
{
    const FString Root=TEXT("/Game/Combat/SkillEditorExamples/");
    // Existing examples are designers' assets, never regenerated over saved edits.
    if(auto* Existing=LoadObject<UCombatSkillSet>(nullptr,*(Root+TEXT("DA_ExampleSkillSet")))) return Existing;
    auto* Burn=NewCombatAsset<UCombatBuffDefinition>(Root+TEXT("Buff_Burn")); Burn->BuffTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Buff.Burn")); Burn->Duration=4; Burn->MaxStacks=3; Burn->HealthPerPeriod=-4;
    auto* Armor=NewCombatAsset<UCombatBuffDefinition>(Root+TEXT("Buff_Armor")); Armor->BuffTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Buff.Armor")); Armor->bSuperArmor=true; Armor->Duration=3;
    auto* Slow=NewCombatAsset<UCombatBuffDefinition>(Root+TEXT("Buff_Slow")); Slow->BuffTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Buff.Slow")); Slow->MoveSpeedMultiplier=.5f;
    auto* Power=NewCombatAsset<UCombatBuffDefinition>(Root+TEXT("Buff_Power")); Power->BuffTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Buff.Power")); Power->DamageMultiplier=1.5f;
    auto* Fan=NewCombatAsset<UCombatProjectileDefinition>(Root+TEXT("Projectile_Piercing")); Fan->Penetrations=2; Fan->HitBuff=Burn;
    Fan->Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Combat/VFX/SM_SwordWave.SM_SwordWave"));
    Fan->Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Combat/Materials/M_SwordWave.M_SwordWave"));
    auto* Bounce=NewCombatAsset<UCombatProjectileDefinition>(Root+TEXT("Projectile_Bounce")); Bounce->Mesh=Fan->Mesh; Bounce->Material=Fan->Material; Bounce->Bounces=3;
    auto* Missile=NewCombatAsset<UCombatProjectileDefinition>(Root+TEXT("Projectile_Missile")); Missile->Mesh=Fan->Mesh; Missile->Material=Fan->Material; Missile->Motion=ECombatProjectileMotion::Guided; Missile->Speed=700; Missile->Acceleration=400; Missile->ExplosionRadius=260; Missile->HitBuff=Slow; Missile->LostTarget=ECombatLostTarget::Reacquire;
    auto* Set=NewCombatAsset<UCombatSkillSet>(Root+TEXT("DA_ExampleSkillSet"));
    for(int32 I=0;I<6;++I)
    {
        auto* S=NewCombatAsset<UCombatSkillDefinition>(Root+FString::Printf(TEXT("Skill_%d"),I+1));
        S->bDataDriven=true; S->Duration=1.4f; S->Cooldown=.1f; S->SkillTag=FGameplayTag::RequestGameplayTag(*FString::Printf(TEXT("Combat.Skill.Editor.Sample%d"),I+1)); S->GraphPosition=FVector2D((I%3)*360,(I/3)*240);
        if(I==0) { S->InputTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Input.Attack")); S->Priority=200; }
        FCombatSkillEvent E; E.Time=.15f;
        if(I<3)
        {
            E.Type=ECombatSkillEventType::Projectile; E.Projectile=I==2?Missile:Fan; E.Pattern=I==2?ECombatFirePattern::Single:ECombatFirePattern::Fan; E.Count=3; E.Label=I==2?TEXT("制导导弹"):TEXT("扇形穿透弹");
            if(I<2) { auto& R=S->Derivations.AddDefaulted_GetRef(); R.TargetSkill=FGameplayTag::RequestGameplayTag(*FString::Printf(TEXT("Combat.Skill.Editor.Sample%d"),I+2)); R.InputTag=FGameplayTag::RequestGameplayTag(TEXT("Combat.Input.Attack")); R.WindowStart=.3f; R.WindowEnd=1.3f; R.bRequireHit=I==1; }
        }
        else if(I==3) { E.Type=ECombatSkillEventType::Projectile; E.Projectile=Bounce; E.Label=TEXT("反弹弹"); }
        else { E.Type=ECombatSkillEventType::ApplyBuff; E.Buff=I==4?Armor:Power; E.Label=I==4?TEXT("霸体"):TEXT("增伤"); }
        S->Events.Add(E); FCombatSkillEvent Cancel; Cancel.Type=ECombatSkillEventType::CancelWindow; Cancel.Time=.5f; Cancel.Duration=.9f; Cancel.Label=TEXT("可取消"); S->Events.Add(Cancel);
        Set->Skills.Add(S); SaveCombatAsset(S);
    }
    for(UObject* A:TArray<UObject*>{Burn,Armor,Slow,Power,Fan,Bounce,Missile,Set}) SaveCombatAsset(A);
    return Set;
}
