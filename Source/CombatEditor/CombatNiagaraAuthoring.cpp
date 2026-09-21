#include "CombatEditorLibrary.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraScriptSource.h"
#include "NiagaraGraph.h"
#include "NiagaraNodeFunctionCall.h"
#include "NiagaraParameterMapHistory.h"
#include "NiagaraEditorModule.h"
#include "INiagaraEditorTypeUtilities.h"
#include "EdGraphSchema_Niagara.h"
#include "ViewModels/Stack/NiagaraStackGraphUtilities.h"
#include "ViewModels/Stack/NiagaraParameterHandle.h"
#include "Modules/ModuleManager.h"
#include "NiagaraSpriteRendererProperties.h"
#include "NiagaraRibbonRendererProperties.h"
#include "NiagaraMeshRendererProperties.h"
#include "Materials/MaterialInterface.h"
#include "EdGraph/EdGraphSchema.h"
#include "Misc/PackageName.h"
#include "UObject/SavePackage.h"

namespace CombatNiagara
{
    bool ValidValue(FNiagaraVariable Variable, const FString& Value)
    {
        auto& Module = FModuleManager::LoadModuleChecked<FNiagaraEditorModule>(TEXT("NiagaraEditor"));
        auto Utilities = Module.GetTypeUtilities(Variable.GetType());
        return Utilities.IsValid() && Utilities->CanHandlePinDefaults() && Utilities->SetValueFromPinDefaultString(Value, Variable);
    }

    bool Owned(const UNiagaraSystem* System)
    {
        return System && System->GetPackage()->GetName().StartsWith(TEXT("/Game/Combat/"));
    }

    UNiagaraGraph* Graph(const FNiagaraEmitterHandle& Handle)
    {
        const auto* Data = Handle.GetEmitterData();
        auto* Source = Data ? Cast<UNiagaraScriptSource>(Data->GraphSource) : nullptr;
        return Source ? Source->NodeGraph.Get() : nullptr;
    }

    void Inputs(const FNiagaraEmitterHandle& Handle, UNiagaraNodeFunctionCall& Node,
        TArray<FNiagaraVariable>& Variables, TSet<FNiagaraVariable>& Hidden)
    {
        FNiagaraStackGraphUtilities::GetStackFunctionInputs(Node, Variables, Hidden,
            FCompileConstantResolver(Handle.GetInstance(), ENiagaraScriptUsage::Function),
            FNiagaraStackGraphUtilities::ENiagaraGetStackFunctionInputPinsOptions::ModuleInputsOnly);
    }
}

FString UCombatEditorLibrary::InspectNiagara(UNiagaraSystem* System)
{
    if (!System) return TEXT("ERROR null system");
    FString Report = FString::Printf(TEXT("SYSTEM %s valid=%d ready=%d\n"), *System->GetPathName(), System->IsValid(), System->IsReadyToRun());
    for (const auto& Handle : System->GetEmitterHandles())
    {
        Report += FString::Printf(TEXT("EMITTER %s enabled=%d\n"), *Handle.GetName().ToString(), Handle.GetIsEnabled());
        if (const auto* Data = Handle.GetEmitterData())
        {
            for (auto* Renderer : Data->GetRenderers())
            {
                Report += FString::Printf(TEXT(" RENDERER %s enabled=%d\n"), *Renderer->GetClass()->GetName(), Renderer->GetIsEnabled());
                TArray<UMaterialInterface*> Materials;
                Renderer->GetUsedMaterials(nullptr, Materials);
                for (auto* Material : Materials) Report += TEXT("  MATERIAL ") + GetPathNameSafe(Material) + TEXT("\n");
            }
        }
        if (auto* Graph = CombatNiagara::Graph(Handle))
        {
            for (UEdGraphNode* GraphNode : Graph->Nodes)
            {
                if (auto* Node = Cast<UNiagaraNodeFunctionCall>(GraphNode))
                {
                    Report += TEXT(" MODULE ") + Node->GetFunctionName() + TEXT(" script=") + GetPathNameSafe(Node->FunctionScript) + TEXT("\n");
                    TArray<FNiagaraVariable> Inputs;
                    TSet<FNiagaraVariable> Hidden;
                    CombatNiagara::Inputs(Handle, *Node, Inputs, Hidden);
                    for (const auto& Input : Inputs)
                        Report += FString::Printf(TEXT("  INPUT %s type=%s hidden=%d\n"), *Input.GetName().ToString(), *Input.GetType().GetName(), Hidden.Contains(Input));
                }
                // Includes override defaults and static switches; linked defaults are not active values.
                for (auto* Pin : GraphNode->Pins)
                {
                    if (Pin && Pin->Direction == EGPD_Input && (!Pin->DefaultValue.IsEmpty() || Pin->LinkedTo.Num()))
                        Report += FString::Printf(TEXT("  PIN %s.%s default=%s links=%d\n"), *GraphNode->GetName(), *Pin->PinName.ToString(), *Pin->DefaultValue, Pin->LinkedTo.Num());
                }
            }
        }
    }
    return Report;
}

bool UCombatEditorLibrary::SetNiagaraInput(UNiagaraSystem* System, const FString& EmitterName,
    const FString& ModuleName, const FString& InputName, const FString& Value)
{
    if (!CombatNiagara::Owned(System)) return false;
    for (auto& Handle : System->GetEmitterHandles())
    {
        if (Handle.GetName().ToString() != EmitterName) continue;
        auto* Graph = CombatNiagara::Graph(Handle);
        if (!Graph) return false;
        for (UEdGraphNode* GraphNode : Graph->Nodes)
        {
            auto* Node = Cast<UNiagaraNodeFunctionCall>(GraphNode);
            if (!Node || Node->GetFunctionName() != ModuleName) continue;
            TArray<FNiagaraVariable> Inputs;
            TSet<FNiagaraVariable> Hidden;
            CombatNiagara::Inputs(Handle, *Node, Inputs, Hidden);
            for (const auto& Input : Inputs)
            {
                if (Input.GetName().ToString() != InputName || Hidden.Contains(Input)) continue;
                if (!CombatNiagara::ValidValue(Input, Value)) return false;
                System->Modify(); Graph->Modify(); Node->Modify();
                const auto Alias = FNiagaraParameterHandle::CreateAliasedModuleParameterHandle(FNiagaraParameterHandle(Input.GetName()), Node);
                auto& Pin = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(*Node, Alias, Input.GetType(), FGuid(), FGuid());
                Pin.BreakAllPinLinks();
                Graph->GetSchema()->TrySetDefaultValue(Pin, Value);
                Graph->NotifyGraphChanged();
                System->MarkPackageDirty();
                return Pin.DefaultValue == Value;
            }
            // Static switches are input pins on the function, not parameter-map overrides.
            for (auto* Pin : Node->Pins)
            {
                if (Pin && Pin->Direction == EGPD_Input && Pin->PinName.ToString() == InputName && Pin->LinkedTo.IsEmpty())
                {
                    if (!CombatNiagara::ValidValue(UEdGraphSchema_Niagara::PinToNiagaraVariable(Pin), Value)) return false;
                    System->Modify(); Graph->Modify(); Node->Modify();
                    Graph->GetSchema()->TrySetDefaultValue(*Pin, Value);
                    Graph->NotifyGraphChanged();
                    System->MarkPackageDirty();
                    return Pin->DefaultValue == Value;
                }
            }
            return false;
        }
    }
    return false;
}

bool UCombatEditorLibrary::SetCombatNiagaraRenderers(UNiagaraSystem* System, UMaterialInterface* Material,
    FLinearColor Color, FVector2D SpriteSize, float RibbonWidth)
{
    if (!CombatNiagara::Owned(System) || !Material || !Material->GetPathName().StartsWith(TEXT("/Game/Combat/")) ||
        SpriteSize.X <= 0 || SpriteSize.Y <= 0 || RibbonWidth <= 0) return false;
    System->Modify();
    auto& Parameters = System->GetExposedParameters();
    Parameters.SetParameterValue(Color, FNiagaraVariable(FNiagaraTypeDefinition::GetColorDef(), TEXT("User.Tint")), true);
    Parameters.SetParameterValue(FVector2f(SpriteSize), FNiagaraVariable(FNiagaraTypeDefinition::GetVec2Def(), TEXT("User.SpriteSize")), true);
    Parameters.SetParameterValue(RibbonWidth, FNiagaraVariable(FNiagaraTypeDefinition::GetFloatDef(), TEXT("User.RibbonWidth")), true);
    int32 VisibleRenderers = 0;
    for (auto& Handle : System->GetEmitterHandles())
    {
        const FVersionedNiagaraEmitterBase Emitter(Handle.GetEmitterBase(), Handle.GetInstance().Version);
        if (auto* Data = Handle.GetEmitterData())
        {
            for (auto* Renderer : Data->GetRenderers())
            {
                Renderer->Modify();
                if (auto* Sprite = Cast<UNiagaraSpriteRendererProperties>(Renderer))
                {
                    Sprite->Material = Material;
                    Sprite->ColorBinding.SetValue(TEXT("User.Tint"), Emitter, Sprite->GetCurrentSourceMode());
                    Sprite->SpriteSizeBinding.SetValue(TEXT("User.SpriteSize"), Emitter, Sprite->GetCurrentSourceMode());
                    ++VisibleRenderers;
                }
                else if (auto* Ribbon = Cast<UNiagaraRibbonRendererProperties>(Renderer))
                {
                    Ribbon->Material = Material;
                    Ribbon->ColorBinding.SetValue(TEXT("User.Tint"), Emitter, Ribbon->GetCurrentSourceMode());
                    Ribbon->RibbonWidthBinding.SetValue(TEXT("User.RibbonWidth"), Emitter, Ribbon->GetCurrentSourceMode());
                    ++VisibleRenderers;
                }
                else if (Cast<UNiagaraMeshRendererProperties>(Renderer)) Renderer->SetIsEnabled(false);
                Renderer->PostEditChange();
            }
        }
    }
    System->MarkPackageDirty();
    return VisibleRenderers > 0;
}

bool UCombatEditorLibrary::CompileAndSaveNiagara(UNiagaraSystem* System)
{
    if (!CombatNiagara::Owned(System)) return false;
    System->RequestCompile(false);
    System->WaitForCompilationComplete(true, false);
    if (!System->IsValid() || !System->IsReadyToRun()) return false;
    System->MarkPackageDirty();
    FSavePackageArgs Args;
    Args.TopLevelFlags = RF_Public | RF_Standalone;
    Args.SaveFlags = SAVE_NoError;
    return UPackage::SavePackage(System->GetPackage(), System,
        *FPackageName::LongPackageNameToFilename(System->GetPackage()->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}
