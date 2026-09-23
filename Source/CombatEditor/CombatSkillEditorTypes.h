#pragma once
#include "CoreMinimal.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphSchema.h"
#include "Factories/Factory.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "CombatTypes.h"
#include "CombatSkillEditorTypes.generated.h"

UCLASS()
class UCombatSkillAssetFactory : public UFactory
{
    GENERATED_BODY()
public:
    UCombatSkillAssetFactory();
    virtual UObject* FactoryCreateNew(UClass* Class,UObject* Parent,FName Name,EObjectFlags Flags,UObject* Context,FFeedbackContext* Warn) override;
};
UCLASS()
class UCombatProjectileAssetFactory : public UFactory
{
    GENERATED_BODY()
public:
    UCombatProjectileAssetFactory();
    virtual UObject* FactoryCreateNew(UClass* Class,UObject* Parent,FName Name,EObjectFlags Flags,UObject* Context,FFeedbackContext* Warn) override;
};
UCLASS()
class UCombatBuffAssetFactory : public UFactory
{
    GENERATED_BODY()
public:
    UCombatBuffAssetFactory();
    virtual UObject* FactoryCreateNew(UClass* Class,UObject* Parent,FName Name,EObjectFlags Flags,UObject* Context,FFeedbackContext* Warn) override;
};
UCLASS()
class UCombatSkillSetAssetFactory : public UFactory
{
    GENERATED_BODY()
public:
    UCombatSkillSetAssetFactory();
    virtual UObject* FactoryCreateNew(UClass* Class,UObject* Parent,FName Name,EObjectFlags Flags,UObject* Context,FFeedbackContext* Warn) override;
};

UCLASS()
class UCombatSkillGraphNode : public UEdGraphNode
{
    GENERATED_BODY()
public:
    UPROPERTY() TObjectPtr<UCombatSkillDefinition> Skill;
    virtual void AllocateDefaultPins() override;
    virtual FText GetNodeTitle(ENodeTitleType::Type Type) const override;
    virtual FLinearColor GetNodeTitleColor() const override { return FLinearColor(.06f,.35f,.55f); }
    virtual TSharedPtr<SGraphNode> CreateVisualWidget() override;
};
UCLASS()
class UCombatSkillGraph : public UEdGraph
{
    GENERATED_BODY()
public:
    TFunction<void(UCombatSkillDefinition*,int32)> OnSelectRule;
};
UCLASS()
class UCombatSkillGraphSchema : public UEdGraphSchema
{
    GENERATED_BODY()
public:
    virtual const FPinConnectionResponse CanCreateConnection(const UEdGraphPin* A,const UEdGraphPin* B) const override;
    virtual bool TryCreateConnection(UEdGraphPin* A,UEdGraphPin* B) const override;
    virtual void BreakPinLinks(UEdGraphPin& Pin,bool bSendsNodeNotification) const override;
    virtual void OnPinConnectionDoubleCicked(UEdGraphPin* A,UEdGraphPin* B,const FVector2f& Position) const override;
    virtual FLinearColor GetPinTypeColor(const FEdGraphPinType& Type) const override { return FLinearColor(.2f,.75f,1.f); }
};

/** A transactional details projection, copied back into the owning asset after a property edit. */
UCLASS()
class UCombatSkillEventSelection : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, Category="时间轴事件") FCombatSkillEvent Event;
    UPROPERTY(EditAnywhere, Category="派生连线") FCombatSkillDerivation Rule;
};

UCLASS()
class UCombatSkillEditorLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static TArray<FString> ValidateSkillAssets(const TArray<UObject*>& Assets);
    UFUNCTION(BlueprintCallable, Category="Combat|Montage") static UAnimMontage* ConvertToMontageNotifies(UCombatSkillDefinition* Skill,const FString& Destination);
    UFUNCTION(BlueprintCallable, Category="Combat|Montage") static void OpenSkillMontage(UCombatSkillDefinition* Skill);
    UFUNCTION(BlueprintCallable, Category="Combat|Montage") static TArray<UCombatSkillDefinition*> FindMontageSkills(UAnimMontage* Montage);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static UCombatSkillSet* CreateExamples();
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static UCombatSkillDefinition* CopyAsDataSkill(UCombatSkillDefinition* Source,const FString& Destination);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static bool EquipSkillSet(UCombatSkillSet* Set,UBlueprint* CharacterBlueprint);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static void OpenSkillEditor(UObject* Asset);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static bool StartSkillPreview(UCombatSkillDefinition* Skill,UCombatSkillSet* Set);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static AActor* SpawnPreviewObstacle(FVector Location,FVector Size);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static AActor* SpawnPreviewTarget(FVector Location,bool bHostile=true);
    UFUNCTION(BlueprintCallable, Category="Combat|Skill Editor") static bool SetPreviewResolution(int32 Width=1920,int32 Height=1080);
};
