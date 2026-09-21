[CmdletBinding()]
param([string]$Engine = 'D:\UE5.8\UE_5.8')
$ErrorActionPreference = 'Stop'
$combatPython = Join-Path $Engine 'Engine\Binaries\ThirdParty\Python3\Win64\python.exe'
$combatTarget = Join-Path $PSScriptRoot 'vendor\python311'
$combatRequirements = Join-Path $PSScriptRoot 'vendor\requirements-cp311-win64.txt'
& $combatPython -m pip install --upgrade --target $combatTarget --only-binary=:all: --no-deps --require-hashes --index-url https://pypi.org/simple -r $combatRequirements
exit $LASTEXITCODE
