[CmdletBinding()]
param(
    [ValidateSet('doctor','build','editor','assets','test','play','python','mcp')]
    [string]$Command = 'doctor',
    [string]$Path = '/Game',
    [ValidateSet('start','stop','status')][string]$Action = 'status',
    [string]$Code,
    [string]$File,
    [string]$Engine = 'D:\UE5.8\UE_5.8'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$projectFile = Join-Path $projectRoot 'Combat.uproject'
$env:COMBAT_ENGINE = $Engine
$python = Join-Path $Engine 'Engine\Binaries\ThirdParty\Python3\Win64\python.exe'
$cli = Join-Path $PSScriptRoot 'combat_remote.py'
switch ($Command) {
    'doctor' {
        foreach ($required in @($projectFile,$python,(Join-Path $Engine 'Engine\Build\BatchFiles\Build.bat'),(Join-Path $Engine 'Engine\Binaries\Win64\UnrealEditor.exe'))) {
            if (!(Test-Path -LiteralPath $required)) { throw "Missing: $required" }
            Write-Output "OK $required"
        }
        & git --version
        & git lfs version
        & $python --version
        & $python $cli status
        exit $LASTEXITCODE
    }
    'build' {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Close Unreal Editor gracefully before a full build (avoid locked modules / Live Coding).' }
        & (Join-Path $Engine 'Engine\Build\BatchFiles\Build.bat') CombatEditor Win64 Development "-Project=$projectFile" -WaitMutex -NoHotReloadFromIDE
        exit $LASTEXITCODE
    }
    'editor' {
        $existing = Get-Process UnrealEditor -ErrorAction SilentlyContinue
        if ($existing) { Write-Output 'Editor already running; checking matching project'; & $python $cli status; exit $LASTEXITCODE }
        $editorLog = Join-Path $projectRoot 'Saved\Logs\CombatEditorSession.log'
        Start-Process -FilePath (Join-Path $Engine 'Engine\Binaries\Win64\UnrealEditor.exe') -ArgumentList @(('"' + $projectFile + '"'), '-EnablePython', '-unattended', ('-abslog="' + $editorLog + '"')) -WorkingDirectory $projectRoot -WindowStyle Hidden
    }
    'assets' { & $python $cli list_assets $Path; exit $LASTEXITCODE }
    'test' { & $python $cli run_python --file (Join-Path $PSScriptRoot 'smoke_test.py'); exit $LASTEXITCODE }
    'play' { & $python $cli pie $Action; exit $LASTEXITCODE }
    'python' {
        if ($File) { & $python $cli run_python --file $File }
        elseif ($Code) { & $python $cli run_python --code $Code }
        else { throw 'python requires -File or -Code' }
        exit $LASTEXITCODE
    }
    'mcp' { & uv run --project $PSScriptRoot python (Join-Path $PSScriptRoot 'combat_mcp.py'); exit $LASTEXITCODE }
}
