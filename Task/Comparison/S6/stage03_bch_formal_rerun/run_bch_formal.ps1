param(
    [ValidateSet('Smoke','Formal')]
    [string]$Mode = 'Formal'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path "$PSScriptRoot\..\..\..\..").Path
$buildDir = Join-Path $repoRoot 'Task\BCH\simulation\build\s6_stage02_metrics_mingw'
$runner = Join-Path $buildDir 'bch_awgn_runner.exe'
$manifest = Join-Path $repoRoot 'Task\BCH\simulation\results\frame_pools\formal_k200\k200\manifest.json'
$resultRoot = Join-Path $repoRoot ('Task\Comparison\S6\results\bch\' + $(if ($Mode -eq 'Formal') {'formal_v02_20260804'} else {'smoke_v03_20260804'}))
New-Item -ItemType Directory -Force -Path $resultRoot | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'generated_result_readme.txt') (Join-Path $resultRoot 'readme.txt') -Force

$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem
$system = Get-CimInstance Win32_ComputerSystem
$gitCommit = (git -C $repoRoot rev-parse HEAD).Trim()
$gitBranch = (git -C $repoRoot branch --show-current).Trim()
$workingTreeStatus = ((git -C $repoRoot status --short) -join "`n")
$compilerVersion = (& g++ --version | Select-Object -First 1)
$powerScheme = ((powercfg /GETACTIVESCHEME) -join ' ').Trim()
$environment = [ordered]@{
    cpuManufacturer = $cpu.Manufacturer
    cpuModel = $cpu.Name.Trim()
    physicalCoreCount = [int]$cpu.NumberOfCores
    logicalProcessorCount = [int]$cpu.NumberOfLogicalProcessors
    cpuArchitecture = $env:PROCESSOR_ARCHITECTURE
    cpuBaseFrequency = [uint64]$cpu.MaxClockSpeed * 1000000
    cpuCacheInformation = [ordered]@{ l2Bytes = [uint64]$cpu.L2CacheSize * 1024; l3Bytes = [uint64]$cpu.L3CacheSize * 1024 }
    totalMemoryBytes = [uint64]$system.TotalPhysicalMemory
    osName = $os.Caption
    osEdition = $os.OperatingSystemSKU
    osVersion = $os.Version
    osBuild = $os.BuildNumber
    systemArchitecture = $os.OSArchitecture
    compilerId = 'GNU'
    compilerVersion = $compilerVersion
    cppStandard = 'C++17'
    buildType = 'Release'
    optimizationFlags = '-O3 -DNDEBUG (CMake MinGW Release default)'
    threadCount = 1
    timingClock = 'std::chrono::steady_clock'
    timingScope = 'hard decision ready -> decodeBchFrame -> payload and status ready'
    warmupFrames = 100
    timestamp = (Get-Date).ToUniversalTime().ToString('o')
    gitBranch = $gitBranch
    gitCommit = $gitCommit
    workingTreeStatus = $workingTreeStatus
    singleThread = $true
    performanceMode = $powerScheme
    frameDetailLogging = $false
    timingIncludesDynamicAllocation = $true
    executableSha256 = (Get-FileHash -Algorithm SHA256 $runner).Hash.ToLowerInvariant()
    buildCommand = 'cmake --build <buildDir> --config Release --parallel 1'
}
$environment | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $resultRoot 'execution_environment.json')
$environment.GetEnumerator() | ForEach-Object { "{0}: {1}" -f $_.Key, $(if ($_.Value -is [System.Collections.IDictionary]) {($_.Value | ConvertTo-Json -Compress)} else {$_.Value}) } |
    Set-Content -Encoding UTF8 (Join-Path $resultRoot 'execution_environment.txt')
$environmentHash = (Get-FileHash -Algorithm SHA256 (Join-Path $resultRoot 'execution_environment.json')).Hash.ToLowerInvariant()

$maxFrames = if ($Mode -eq 'Formal') {50000} else {1000}
$snrValues = if ($Mode -eq 'Formal') {0..30 | ForEach-Object {-5.0 + 0.5 * $_}} else {@(-5.0)}
$allSummary = @()
$allComplexity = @()
$allMemory = @()
foreach ($caseName in @('BCH-S200','BCH-B200')) {
    for ($snrIndex = 0; $snrIndex -lt $snrValues.Count; ++$snrIndex) {
        $esN0 = [double]$snrValues[$snrIndex]
        $pointName = ('{0}_esn0_{1:+0.0;-0.0;0.0}db' -f $caseName.ToLowerInvariant(), $esN0).Replace('+','p').Replace('-','m').Replace('.','p')
        $pointDir = Join-Path $resultRoot $pointName
        New-Item -ItemType Directory -Force -Path $pointDir | Out-Null
        Copy-Item (Join-Path $PSScriptRoot 'generated_result_readme.txt') (Join-Path $pointDir 'readme.txt') -Force
        & $runner --stage stage03_bch_formal_rerun --case $caseName --esn0-db $esN0 --snr-index $snrIndex `
            --frame-start 0 --frame-count $maxFrames --logical-frame-count $maxFrames --global-seed 20260804 `
            --frame-pool-manifest $manifest --output-dir $pointDir --no-progress --timing-warmup-frames 100 `
            --min-frames 1000 --target-frame-errors 200 --max-frames $maxFrames `
            --checkpoint (Join-Path $pointDir 'checkpoint.json') --checkpoint-interval 5000
        if ($LASTEXITCODE -ne 0) { throw "BCH runner failed: $caseName Es/N0=$esN0" }
        $summary = Import-Csv (Join-Path $pointDir 'summary.csv')
        $summary | Add-Member -NotePropertyName gitCommit -NotePropertyValue $gitCommit
        $summary | Add-Member -NotePropertyName environmentHash -NotePropertyValue $environmentHash
        $allSummary += $summary
        $allComplexity += Import-Csv (Join-Path $pointDir 'complexity_summary.csv')
        $allMemory += Import-Csv (Join-Path $pointDir 'memory_summary.csv')
    }
}
$allSummary | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $resultRoot 'bch_formal_results.csv')
$allComplexity | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $resultRoot 'bch_complexity_results.csv')
$allMemory | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $resultRoot 'bch_memory_results.csv')
if ($allSummary.Count -ne 2 * $snrValues.Count) { throw 'formal result point count mismatch' }
if (($allSummary | Where-Object {[double]$_.processedFrames -lt 1000 -or [double]$_.processedFrames -gt $maxFrames}).Count -ne 0) {
    throw 'processed frame count violates frozen stop bounds'
}
Write-Output ('PASS_BCH_{0}_{1}_POINTS' -f $Mode.ToUpperInvariant(), $allSummary.Count)
