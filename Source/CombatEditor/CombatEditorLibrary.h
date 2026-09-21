#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "CombatEditorLibrary.generated.h"

class UBlueprint;
class UAnimBlueprint;
class UAnimInstance;
class UAnimSequence;
class UBlendSpace;
class USkeleton;
class APlayerController;
class UUserWidget;
class UWidgetBlueprint;
class UStateTree;
class ANavMeshBoundsVolume; class UNiagaraSystem; class UNiagaraEmitter;
class UMaterialInterface;

/** Authoring only. Never linked into the packaged runtime module. */
UCLASS()
class COMBATEDITOR_API UCombatEditorLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool BuildNavBounds(ANavMeshBoundsVolume* Volume, FVector Size);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static UWidgetBlueprint* CreateHUD(const FString& AssetPath, TSubclassOf<UUserWidget> ParentClass);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static UAnimBlueprint* CreateLocomotion(const FString& AssetPath, TSubclassOf<UAnimInstance> ParentClass, USkeleton* Skeleton, UBlendSpace* BlendSpace, UAnimSequence* AirSequence);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static UStateTree* CreateCombatStateTree(const FString& AssetPath, const TArray<FString>& TaskStructPaths);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool CompileAndSave(UBlueprint* Blueprint);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool ConfigureNiagara(UNiagaraSystem* System, FLinearColor Color, float SpriteSize = 12.f, float RibbonWidth = 8.f);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool RebuildBlendSpace(UBlendSpace* BlendSpace);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool InjectPlayerKey(APlayerController* Controller, FName Key, bool bPressed);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool StartPIEWindow(int32 Width = 1920, int32 Height = 1080);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static UNiagaraSystem* CreateNiagaraFromEmitter(const FString& AssetPath, UNiagaraEmitter* Emitter);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static FString InspectNiagara(UNiagaraSystem* System);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool SetNiagaraInput(UNiagaraSystem* System, const FString& EmitterName, const FString& ModuleName, const FString& InputName, const FString& Value);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool SetCombatNiagaraRenderers(UNiagaraSystem* System, UMaterialInterface* Material, FLinearColor Color, FVector2D SpriteSize, float RibbonWidth = 3.f);
    UFUNCTION(BlueprintCallable, Category="Combat|Editor")
    static bool CompileAndSaveNiagara(UNiagaraSystem* System);
};
