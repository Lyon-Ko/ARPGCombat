#include "CombatSkillEditorTypes.h"
#include "CombatAnimNotify.h"
#include "Animation/AnimMontage.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "ScopedTransaction.h"
#include "Misc/PackageName.h"

UAnimMontage* UCombatSkillEditorLibrary::ConvertToMontageNotifies(UCombatSkillDefinition* Skill,const FString& Destination)
{
    if(!Skill || !Skill->bDataDriven || !Skill->Montage || (GEditor && GEditor->PlayWorld)) return nullptr;
    if(Skill->bUseMontageNotifies) return Skill->Montage;
    if(!FPackageName::IsValidLongPackageName(Destination) || FPackageName::DoesPackageExist(Destination) || FindPackage(nullptr,*Destination)) return nullptr;
    const float Length=Skill->Montage->GetPlayLength();
    auto WindowEvent=[](ECombatSkillEventType T){return T==ECombatSkillEventType::HitWindow || T==ECombatSkillEventType::CancelWindow || T==ECombatSkillEventType::ComboWindow;};
    // Validate before creating or modifying anything. A partial conversion is never committed.
    for(const auto& E:Skill->Events)
        if(!FMath::IsFinite(E.Time) || E.Time<0 || E.Time>Length || (WindowEvent(E.Type) && (!FMath::IsFinite(E.Duration) || E.Duration<=0 || E.Time+E.Duration>Length+.001f))) return nullptr;
    for(const auto& R:Skill->Derivations)
        if(!FMath::IsFinite(R.WindowStart) || !FMath::IsFinite(R.WindowEnd) || R.WindowStart<0 || R.WindowEnd>Length+.001f || R.WindowEnd<=R.WindowStart || (R.Trigger==ECombatDerivationTrigger::Completed && R.WindowEnd<Skill->Duration-.001f)) return nullptr;
    for(const auto& N:Skill->Montage->Notifies)
        if(Cast<UCombatAnimNotify_SkillAction>(N.Notify) || Cast<UCombatAnimNotifyState_SkillWindow>(N.NotifyStateClass)) return nullptr;
    const FScopedTransaction Transaction(FText::FromString(TEXT("迁移技能时序到独立 Montage")));
    Skill->Modify();
    auto* Montage=DuplicateObject<UAnimMontage>(Skill->Montage,CreatePackage(*Destination),*FPackageName::GetLongPackageAssetName(Destination));
    Montage->SetFlags(RF_Public|RF_Standalone|RF_Transactional); Montage->Modify();
    // Only known legacy combat notifies are removed from the copy. Original montage is untouched.
    Montage->Notifies.RemoveAll([](const FAnimNotifyEvent& N){return Cast<UCombatAnimNotify_Event>(N.Notify)!=nullptr;});
    const int32 FirstTrack=Montage->AnimNotifyTracks.Num();
    for(const FName Name:{FName(TEXT("Skill Actions")),FName(TEXT("Hit Windows")),FName(TEXT("Derivation Windows")),FName(TEXT("Cancel Windows"))})
    { FAnimNotifyTrack Track; Track.TrackName=Name; Track.TrackColor=FLinearColor(.15f,.6f,.9f); Montage->AnimNotifyTracks.Add(Track); }
    auto Point=[&](float At,int32 Track)->FAnimNotifyEvent&
    {
        auto& N=Montage->Notifies.AddDefaulted_GetRef(); N.Link(Montage,At); N.TrackIndex=Track; N.Guid=FGuid::NewGuid();
        N.TriggerTimeOffset=GetTriggerTimeOffsetForType(Montage->CalculateOffsetForNotify(At));
        return N;
    };
    auto Window=[&](float Start,float End,ECombatSkillWindowType Type,FName Name)
    {
        auto* State=NewObject<UCombatAnimNotifyState_SkillWindow>(Montage,NAME_None,RF_Transactional);
        State->WindowType=Type; State->WindowName=Name;
        auto& N=Point(Start,FirstTrack+(Type==ECombatSkillWindowType::Hit?1:Type==ECombatSkillWindowType::Derivation?2:3));
        N.NotifyStateClass=State; N.SetDuration(End-Start); N.EndLink.Link(Montage,End);
        N.EndTriggerTimeOffset=GetTriggerTimeOffsetForType(Montage->CalculateOffsetForNotify(End));
    };
    for(const auto& E:Skill->Events)
    {
        if(WindowEvent(E.Type)) Window(E.Time,E.Time+E.Duration,E.Type==ECombatSkillEventType::HitWindow?ECombatSkillWindowType::Hit:E.Type==ECombatSkillEventType::ComboWindow?ECombatSkillWindowType::Derivation:ECombatSkillWindowType::Cancel,*FString::Printf(TEXT("Window_%s"),*E.Id.ToString(EGuidFormats::Digits).Left(8)));
        else
        {
            auto* Notify=NewObject<UCombatAnimNotify_SkillAction>(Montage,NAME_None,RF_Transactional); Notify->Action=E;
            Notify->Action.Time=0; // Timing is owned by the native notify link, never this payload.
            auto& N=Point(E.Time,FirstTrack); N.Notify=Notify;
        }
    }
    for(auto& R:Skill->Derivations)
    {
        R.WindowName=NAME_None;
        if(R.Trigger!=ECombatDerivationTrigger::Completed)
        {
            R.WindowName=*FString::Printf(TEXT("Derive_%s"),*R.Id.ToString(EGuidFormats::Digits).Left(8));
            Window(R.WindowStart,R.WindowEnd,ECombatSkillWindowType::Derivation,R.WindowName);
        }
    }
    Montage->RefreshCacheData(); Montage->PostEditChange(); Montage->MarkPackageDirty();
    Skill->Montage=Montage; Skill->Duration=Length; Skill->Events.Reset(); Skill->bUseMontageNotifies=true; Skill->SchemaVersion=2; Skill->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Montage);
    return Montage;
}
void UCombatSkillEditorLibrary::OpenSkillMontage(UCombatSkillDefinition* Skill)
{ if(GEditor && Skill && Skill->Montage) GEditor->GetEditorSubsystem<UAssetEditorSubsystem>()->OpenEditorForAsset(Skill->Montage); }
TArray<UCombatSkillDefinition*> UCombatSkillEditorLibrary::FindMontageSkills(UAnimMontage* Montage)
{
    TArray<UCombatSkillDefinition*> Result; if(!Montage) return Result;
    TArray<FAssetData> Assets; FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get().GetAssetsByClass(UCombatSkillDefinition::StaticClass()->GetClassPathName(),Assets);
    for(const auto& A:Assets) if(auto* S=Cast<UCombatSkillDefinition>(A.GetAsset()); S && S->Montage==Montage) Result.Add(S);
    return Result;
}
