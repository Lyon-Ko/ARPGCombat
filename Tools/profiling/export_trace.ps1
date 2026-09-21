#Requires -Version 5.1
<#
.SYNOPSIS
Exports an existing UE 5.8 trace with bounded, hidden Unreal Insights runs.
.DESCRIPTION
Starts UnrealInsights.exe only when this script is invoked. It never captures a
trace or launches an editor. Times are trace-relative seconds; default 0..60 s,
maximum window 60 s. Threads/Timers are metadata inventories; timing events and
statistics are restricted to GameThread. Each pass reanalyses the input trace.
Choose a window containing the scenario: the default may contain startup only.
OutputDirectory must be empty to avoid accepting stale exports or overwriting work.
UE can create its normal analysis cache alongside the input trace.
.EXAMPLE
./export_trace.ps1 -RawTracePath 'D:\Traces\run.utrace' -StartTime 10 -EndTime 15
.NOTES
Source-verified against D:\UE5.8\UE_5.8\Engine:
Source/Developer/TraceInsights/Private/Insights/Tests/FunctionalTests/ExportCommandsTests.cpp:86,168,234
Source/Developer/TraceInsights/Private/Insights/TimingProfiler/TimingProfilerManager.cpp:903
Response files avoid nested command-line quoting. No unfiltered event export.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$RawTracePath,
    [string]$OutputDirectory,
    [double]$StartTime = 0,
    [double]$EndTime = 60,
    [ValidateRange(10, 600)][int]$TimeoutSeconds = 120,
    [ValidateRange(1, 512)][int]$MaxOutputMiB = 128,
    [ValidateRange(1, 10000)][int]$MaxTimerCount = 1000,
    [string]$InsightsExecutable = 'D:\UE5.8\UE_5.8\Engine\Binaries\Win64\UnrealInsights.exe'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-SafeAbsolutePath([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -match '[\x00-\x1f"*?]') {
        throw 'Paths must be nonempty literal filesystem paths without control characters, quotes or wildcards.'
    }
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Value)
    $resolved = [System.IO.Path]::GetFullPath($resolved)
    if ($resolved -notmatch '^[A-Za-z]:\\') {
        throw 'Use a local absolute drive path; network paths and non-filesystem providers are unsupported.'
    }
    return $resolved
}

if ([double]::IsNaN($StartTime) -or [double]::IsInfinity($StartTime) -or
    [double]::IsNaN($EndTime) -or [double]::IsInfinity($EndTime) -or
    $StartTime -lt 0 -or $EndTime -le $StartTime -or ($EndTime - $StartTime) -gt 60) {
    throw 'Require finite 0 <= StartTime < EndTime and a window of at most 60 seconds.'
}
$tracePath = Get-SafeAbsolutePath $RawTracePath
$executablePath = Get-SafeAbsolutePath $InsightsExecutable
if (-not (Test-Path -LiteralPath $tracePath -PathType Leaf)) { throw "Trace file does not exist: $tracePath" }
if ([System.IO.Path]::GetExtension($tracePath) -ine '.utrace') { throw 'RawTracePath must be a .utrace file.' }
if ((Get-Item -LiteralPath $tracePath).Length -eq 0) { throw 'Trace file is empty.' }
if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) { throw "Unreal Insights executable does not exist: $executablePath" }
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path ([System.IO.Path]::GetDirectoryName($tracePath)) (
        'insights-export-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
}
$outputPath = Get-SafeAbsolutePath $OutputDirectory
if (Test-Path -LiteralPath $outputPath) {
    if (-not (Test-Path -LiteralPath $outputPath -PathType Container)) { throw 'OutputDirectory is not a directory.' }
    if (@(Get-ChildItem -LiteralPath $outputPath -Force).Count -ne 0) { throw 'OutputDirectory must be empty.' }
} else {
    [void][System.IO.Directory]::CreateDirectory($outputPath)
}
$manifestPath = Join-Path $outputPath 'manifest.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$manifest = [ordered]@{
    schema_version = 1
    status = 'running'
    started_utc = [DateTime]::UtcNow.ToString('o')
    finished_utc = $null
    raw_trace_path = $tracePath
    raw_trace_bytes = (Get-Item -LiteralPath $tracePath).Length
    insights_executable = $executablePath
    output_directory = $outputPath
    limits = [ordered]@{
        threads = @('GameThread'); start_time_seconds = $StartTime; end_time_seconds = $EndTime
        max_window_seconds = 60; timeout_seconds_per_pass = $TimeoutSeconds; max_passes = 2
        max_export_directory_bytes = [long]$MaxOutputMiB * 1MB; watchdog_interval_ms = 250
        max_statistics_timers = $MaxTimerCount
    }
    limitations = @(
        'Threads and Timers inventories cover all metadata; only timing events/statistics use the GameThread and time filters.'
        'The default window may cover startup only. Select scenario-relative times explicitly.'
        'The size watchdog samples every 250 ms and can overshoot; it does not limit input analysis memory or UE cache files.'
        'Events overlapping the time window can start before it or end after it; timestamps are not clipped.'
        'Header-only exports are recorded as empty and are not proof of useful scenario coverage.'
        'A failure may leave partial outputs; only a complete manifest establishes successful process and file checks.'
    )
    game_thread_ids = @()
    runs = @()
    outputs = @()
    error = $null
}
function Save-Manifest {
    [System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 10), $utf8)
}
function Get-ExportBytes {
    $sum = (Get-ChildItem -LiteralPath $outputPath -File -Recurse -Force | Measure-Object -Property Length -Sum).Sum
    if ($null -eq $sum) { return [long]0 }
    return [long]$sum
}
function Invoke-ExportPass([string]$Name, [string[]]$Commands, [string[]]$ExpectedFiles) {
    $responsePath = Join-Path $outputPath ($Name + '.rsp')
    $logPath = Join-Path $outputPath ($Name + '.log')
    [System.IO.File]::WriteAllLines($responsePath, $Commands, $utf8)
    $arguments = '-NoUI -AutoQuit -OpenTraceFile="{0}" -ExecOnAnalysisCompleteCmd="@={1}" -ABSLOG="{2}" -log' -f
        $tracePath.Replace('\', '/'), $responsePath.Replace('\', '/'), $logPath.Replace('\', '/')
    $run = [ordered]@{
        name = $Name; commands = $Commands; arguments = $arguments; response_file = $responsePath
        log_file = $logPath; started_utc = [DateTime]::UtcNow.ToString('o'); finished_utc = $null
        process_id = $null; exit_code = $null; status = 'starting'; expected_files = $ExpectedFiles
    }
    $manifest.runs += $run
    Save-Manifest
    $process = $null
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $process = Start-Process -FilePath $executablePath -ArgumentList $arguments -WorkingDirectory $outputPath -WindowStyle Hidden -PassThru
        $run.process_id = $process.Id
        $run.status = 'running'
        Save-Manifest
        while (-not $process.WaitForExit(250)) {
            if ($watch.Elapsed.TotalSeconds -ge $TimeoutSeconds) { throw "Pass $Name exceeded $TimeoutSeconds seconds." }
            if ((Get-ExportBytes) -gt $manifest.limits.max_export_directory_bytes) { throw "Pass $Name exceeded the output size limit." }
        }
        $process.Refresh()
        $run.exit_code = $process.ExitCode
        if ($null -eq $run.exit_code -or $run.exit_code -ne 0) { throw "Pass $Name failed with exit code $($run.exit_code)." }
        if ((Get-ExportBytes) -gt $manifest.limits.max_export_directory_bytes) { throw "Pass $Name exceeded the output size limit." }
        foreach ($file in $ExpectedFiles) {
            $path = Join-Path $outputPath $file
            if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) {
                throw "Pass $Name did not produce nonempty $file. Inspect $logPath."
            }
            $firstLines = @(Get-Content -LiteralPath $path -Encoding UTF8 -TotalCount 2)
            $manifest.outputs += [ordered]@{ name = $file; path = $path; bytes = (Get-Item -LiteralPath $path).Length; has_data_rows = ($firstLines.Count -gt 1) }
        }
        $run.status = 'complete'
    } catch {
        $run.status = 'failed'
        throw
    } finally {
        if ($null -ne $process) {
            if (-not $process.HasExited) {
                $process.Kill()
                if (-not $process.WaitForExit(5000)) { $manifest.error = 'The exporter could not confirm process termination within 5 seconds.' }
            }
            if ($process.HasExited) { $process.Refresh(); $run.exit_code = $process.ExitCode }
            $process.Dispose()
        }
        $run.finished_utc = [DateTime]::UtcNow.ToString('o')
        Save-Manifest
    }
}

try {
    Save-Manifest
    # Quote paths inside the response file, not inside the outer -Exec argument.
    $exportRoot = $outputPath.Replace('\', '/')
    Invoke-ExportPass 'metadata' @(
        ('TimingInsights.ExportThreads "{0}/Threads.csv"' -f $exportRoot)
        ('TimingInsights.ExportTimers "{0}/Timers.csv"' -f $exportRoot)
    ) @('Threads.csv', 'Timers.csv')
    $threads = @(Import-Csv -LiteralPath (Join-Path $outputPath 'Threads.csv') -Encoding UTF8)
    $gameThreads = @($threads | Where-Object { $_.Name -ceq 'GameThread' })
    if ($gameThreads.Count -eq 0) { throw 'No exact GameThread found in Threads.csv; filtered export was not started.' }
    $manifest.game_thread_ids = @($gameThreads | ForEach-Object { $_.Id })
    $culture = [Globalization.CultureInfo]::InvariantCulture
    $filters = '-threads=GameThread -startTime={0} -endTime={1}' -f $StartTime.ToString('R', $culture), $EndTime.ToString('R', $culture)
    Invoke-ExportPass 'gamethread' @(
        ('TimingInsights.ExportTimingEvents "{0}/TimingEvents.csv" {1} -columns=ThreadId,ThreadName,TimerId,TimerName,StartTime,EndTime,Duration,Depth' -f $exportRoot, $filters)
        ('TimingInsights.ExportTimerStatistics "{0}/TimerStatistics.csv" {1} -maxTimerCount={2} -sortBy=TotalInclusiveTime -sortOrder=Descending' -f $exportRoot, $filters, $MaxTimerCount)
    ) @('TimingEvents.csv', 'TimerStatistics.csv')
    $manifest.status = 'complete'
} catch {
    $manifest.status = 'failed'
    $manifest.error = $_.Exception.Message
    throw
} finally {
    $manifest.finished_utc = [DateTime]::UtcNow.ToString('o')
    Save-Manifest
}
Write-Output $manifestPath
