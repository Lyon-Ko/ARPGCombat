#include "CombatLocomotionSettings.h"
#include "CombatLocomotionConfig.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

namespace
{
struct FParameter { const TCHAR* Section; const TCHAR* Key; SIZE_T Offset; bool bBoolean; float Min; float Max; };
const FParameter Parameters[] = {
#define LOCO_FLOAT(Member, Section, Key, Default, Min, Max, Description) {TEXT(#Section), TEXT(#Key), STRUCT_OFFSET(FCombatLocomotionSettings, Member), false, static_cast<float>(Min), static_cast<float>(Max)},
#define LOCO_BOOL(Member, Section, Key, Default, Description) {TEXT(#Section), TEXT(#Key), STRUCT_OFFSET(FCombatLocomotionSettings, Member), true, 0, 1},
#include "CombatLocomotionParameters.inl"
#undef LOCO_FLOAT
#undef LOCO_BOOL
};
FAutoConsoleCommandWithWorld ReloadCommand(TEXT("Combat.Locomotion.Reload"), TEXT("Apply the locomotion Data Asset; invalid values leave the previous configuration active."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World) {
        if(auto* Subsystem = World ? World->GetSubsystem<UCombatLocomotionSubsystem>() : nullptr) Subsystem->ReloadConfiguration();
    }));
}

bool UCombatLocomotionSubsystem::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game || Type == EWorldType::PIE; }
void UCombatLocomotionSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    // The player's Blueprint also holds a hard reference so the asset is cooked.
    Configuration = LoadObject<UCombatLocomotionConfig>(nullptr, TEXT("/Game/Combat/Config/DA_Locomotion.DA_Locomotion"));
    Load(true);
}
TStatId UCombatLocomotionSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UCombatLocomotionSubsystem, STATGROUP_Tickables); }
void UCombatLocomotionSubsystem::Tick(float DeltaTime)
{
    const double Now = FPlatformTime::Seconds();
    if(Now >= NextPollTime) { NextPollTime = Now + .2; Load(false); }
}
FString UCombatLocomotionSubsystem::GetConfigurationPath() const { return Configuration ? Configuration->GetPathName() : FString(); }
void UCombatLocomotionSubsystem::SetConfiguration(UCombatLocomotionConfig* Asset)
{
    if(Asset && Asset != Configuration)
    {
        Configuration = Asset;
        bHasLastAttempt = false;
        Load(true);
    }
}
bool UCombatLocomotionSubsystem::ReloadConfiguration() { return Load(true); }
bool UCombatLocomotionSubsystem::Reject(const FString& Error)
{
    if(LastError != Error)
    {
        UE_LOG(LogTemp, Error, TEXT("Locomotion Data Asset rejected (keeping revision %d): %s"), Revision, *Error);
        if(GEngine) GEngine->AddOnScreenDebugMessage(72101, 15.f, FColor::Red, TEXT("DA_Locomotion: ") + Error);
    }
    LastError = Error;
    return false;
}
bool UCombatLocomotionSubsystem::Load(bool bForce)
{
    if(!Configuration) return Reject(TEXT("No locomotion Data Asset assigned"));
    const FCombatLocomotionSettings Candidate = Configuration->MakeSnapshot();
    bool bChanged = !bHasLastAttempt;
    for(const FParameter& P : Parameters)
    {
        const uint8* Current = reinterpret_cast<const uint8*>(&Candidate) + P.Offset;
        const uint8* Previous = reinterpret_cast<const uint8*>(&LastAttempt) + P.Offset;
        if(P.bBoolean)
            bChanged |= *reinterpret_cast<const bool*>(Current) != *reinterpret_cast<const bool*>(Previous);
        else
            bChanged |= *reinterpret_cast<const float*>(Current) != *reinterpret_cast<const float*>(Previous);
    }
    if(!bForce && !bChanged) return LastError.IsEmpty();
    LastAttempt = Candidate;
    bHasLastAttempt = true;
    for(const FParameter& P : Parameters)
        if(!P.bBoolean)
        {
            const float Number = *reinterpret_cast<const float*>(reinterpret_cast<const uint8*>(&Candidate) + P.Offset);
            if(!FMath::IsFinite(Number) || Number < P.Min || Number > P.Max)
                return Reject(FString::Printf(TEXT("[%s] %s must be %g..%g"), P.Section, P.Key, P.Min, P.Max));
        }
    if(Candidate.AnimationJogSpeed >= Candidate.AnimationFastSpeed) return Reject(TEXT("Animation.JogSpeed must be below FastSpeed"));
    if(Candidate.CameraPitchMin > Candidate.CameraPitchMax) return Reject(TEXT("Camera.LockedPitchMin must be <= LockedPitchMax"));
    if(Candidate.CameraLockedMinDistance > Candidate.CameraLockedMaxDistance) return Reject(TEXT("Camera.LockedMinDistance must be <= LockedMaxDistance"));
    if(Candidate.CameraHideDistance >= Candidate.CameraRevealDistance) return Reject(TEXT("Camera.HideDistance must be below RevealDistance"));
    if(Candidate.JumpCount != FMath::FloorToFloat(Candidate.JumpCount)) return Reject(TEXT("Air.JumpCount must be an integer"));
    Settings = Candidate;
    LastError.Empty();
    ++Revision;
    UE_LOG(LogTemp, Display, TEXT("Locomotion Data Asset applied, revision %d: %s"), Revision, *GetConfigurationPath());
    if(GEngine)
    {
        GEngine->RemoveOnScreenDebugMessage(72101);
        GEngine->AddOnScreenDebugMessage(72102, 4.f, FColor::Green, FString::Printf(TEXT("DA_Locomotion applied: r%d"), Revision));
    }
    return true;
}
float UCombatLocomotionSubsystem::GetParameter(FName Section, FName Key) const
{
    for(const FParameter& P : Parameters)
        if(Section == FName(P.Section) && Key == FName(P.Key))
        {
            const uint8* Address = reinterpret_cast<const uint8*>(&Settings) + P.Offset;
            return P.bBoolean ? (*reinterpret_cast<const bool*>(Address) ? 1.f : 0.f) : *reinterpret_cast<const float*>(Address);
        }
    return 0.f;
}
const FCombatLocomotionSettings& UCombatLocomotionSubsystem::For(const UObject* Context)
{
    if(const UWorld* World = Context ? Context->GetWorld() : nullptr)
        if(const auto* Subsystem = World->GetSubsystem<UCombatLocomotionSubsystem>()) return Subsystem->GetSettings();
    static const FCombatLocomotionSettings Defaults;
    return Defaults;
}
UCombatLocomotionSubsystem* UCombatLocomotionSubsystem::GetForWorld(const UObject* Context)
{
    return Context && Context->GetWorld() ? Context->GetWorld()->GetSubsystem<UCombatLocomotionSubsystem>() : nullptr;
}
