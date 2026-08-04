$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path "$PSScriptRoot\..\..\..\..").Path
$source = Join-Path $repoRoot 'Task\Comparison\S5\results\stage11\plots'
$version = Join-Path $repoRoot 'Task\Comparison\S6\archive\v03_20260804_before_chinese_plot_revision'
$target = Join-Path $version 'stage11_old_plots'
if (Test-Path $target) { throw 'archive target already exists' }
Copy-Item -LiteralPath $source -Destination $target -Recurse
Copy-Item (Join-Path $PSScriptRoot 'generated_plot_readme.txt') (Join-Path $target 'readme.txt')
Get-ChildItem -LiteralPath $target -Directory | ForEach-Object {
    Copy-Item (Join-Path $PSScriptRoot 'generated_plot_readme.txt') (Join-Path $_.FullName 'readme.txt')
}
$base = (Resolve-Path $version).Path
$rows = Get-ChildItem -LiteralPath $version -Recurse -File | Where-Object { $_.Name -ne 'archive_manifest.csv' } | ForEach-Object {
    [pscustomobject]@{
        relativePath = $_.FullName.Substring($base.Length + 1).Replace('\','/')
        fileSizeBytes = $_.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        archiveVersion = 'v03'
        archiveDate = '2026-08-04'
        archiveReason = 'before_chinese_plot_revision'
        sourceStage = 'S5_stage11'
    }
}
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $version 'archive_manifest.csv')
if ((Get-ChildItem -LiteralPath $target -Directory).Count -ne 86) { throw 'archived figure count is not 86' }
Write-Output 'PASS_STAGE11_ARCHIVE_86'
