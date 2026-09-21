[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$TracePath)
$ErrorActionPreference = 'Stop'
$traceFile = (Resolve-Path -LiteralPath $TracePath).Path
if ($traceFile.Contains('"') -or [IO.Path]::GetExtension($traceFile) -ne '.utrace') { throw 'Expected literal .utrace path' }
$outputDir = Join-Path (Split-Path $traceFile -Parent) ('csv-scopes-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'))
[void][IO.Directory]::CreateDirectory($outputDir)
$exportBase = $outputDir.Replace('\','/')
$responseFile = Join-Path $outputDir 'commands.rsp'
$commands = @(
    ('TimingInsights.ExportThreads "{0}/Threads.csv"' -f $exportBase),
    ('TimingInsights.ExportTimers "{0}/Timers.csv"' -f $exportBase),
    ('TimingInsights.ExportTimingEvents "{0}/CsvScopes.csv" -threads=GameThread -timers=UpdateCoreCsvStats*,FEngineLoop*,UMassEntityEditorSubsystem* -columns=ThreadName,TimerName,StartTime,EndTime,Duration,Depth' -f $exportBase)
)
[IO.File]::WriteAllLines($responseFile, $commands, [Text.UTF8Encoding]::new($false))
$logPath = Join-Path $outputDir 'Insights.log'
$argsText = '-NoUI -AutoQuit -OpenTraceFile="{0}" -ExecOnAnalysisCompleteCmd="@={1}" -ABSLOG="{2}" -log' -f $traceFile.Replace('\','/'),$responseFile.Replace('\','/'),$logPath.Replace('\','/')
$run = [ordered]@{trace=$traceFile;output=$outputDir;commands=$commands;status='starting';utc=[DateTime]::UtcNow.ToString('o')}
$process = $null
try {
    $process = Start-Process -FilePath 'D:\UE5.8\UE_5.8\Engine\Binaries\Win64\UnrealInsights.exe' -ArgumentList $argsText -WindowStyle Hidden -WorkingDirectory $outputDir -PassThru
    if (-not $process.WaitForExit(60000)) { throw 'Insights scope discovery exceeded 60 seconds' }
    $process.Refresh()
    $run.exit_code = $process.ExitCode
    if ($process.ExitCode -ne 0) { throw 'Insights scope discovery failed' }
    foreach ($name in @('Threads.csv','Timers.csv','CsvScopes.csv')) {
        if (-not (Test-Path -LiteralPath (Join-Path $outputDir $name))) { throw "Missing $name" }
    }
    $run.status = 'complete'
} catch {
    $run.status = 'failed'; $run.error = $_.Exception.Message
    throw
} finally {
    if ($null -ne $process) { if (-not $process.HasExited) { $process.Kill(); [void]$process.WaitForExit(5000) }; $process.Dispose() }
    [IO.File]::WriteAllText((Join-Path $outputDir 'manifest.json'), ($run | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    Write-Output $outputDir
}
