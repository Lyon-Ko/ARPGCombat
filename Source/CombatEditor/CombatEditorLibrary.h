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
class UUserWidget;
class UWidgetBlueprint;
class UStateTree;
class ANavMeshBoundsVolume; class UNiagaraSystem;

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
};
