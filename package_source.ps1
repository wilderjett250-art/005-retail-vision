$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkRoot = Join-Path $ProjectRoot 'source_delivery_work'
$DeliveryRoot = Join-Path $ProjectRoot 'delivery_source'

# Keep the script ASCII-only for Windows PowerShell 5.1 compatibility.
$Title = -join [char[]](0x73B0, 0x4EE3, 0x96F6, 0x552E, 0x7EC8, 0x7AEF, 0x667A, 0x6167, 0x8FD0, 0x8425, 0x5E73, 0x53F0)
$SourceLabel = -join [char[]](0x6E90, 0x7801)
$PackageName = $Title + '_' + $SourceLabel + '_Windows7'
$PackageRoot = Join-Path $WorkRoot $PackageName
$ZipPath = Join-Path $DeliveryRoot ($PackageName + '.zip')

$ResolvedProject = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
$ResolvedWork = [IO.Path]::GetFullPath($WorkRoot).TrimEnd('\')
if (-not $ResolvedWork.StartsWith($ResolvedProject + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Source work directory escaped the project boundary: $ResolvedWork"
}

$RequiredFiles = @(
    'app_win7\launcher.py',
    'app_win7\inference.py',
    'backend_original\text\best.onnx',
    'tests\validate_inference_parity.py',
    'tests\run_win7_ui_smoke.js',
    'build_win7.ps1',
    'package_win7.ps1',
    'requirements-win7.txt',
    'package.json',
    'README_SOURCE.md',
    'package_source.ps1'
)
foreach ($RelativePath in $RequiredFiles) {
    $SourcePath = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
        throw "Required source file is missing: $SourcePath"
    }
}

if (Test-Path -LiteralPath $WorkRoot) {
    Remove-Item -LiteralPath $WorkRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $DeliveryRoot -Force | Out-Null

function Copy-RelativeFile {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    $SourcePath = Join-Path $ProjectRoot $RelativePath
    $DestinationPath = Join-Path $PackageRoot $RelativePath
    $DestinationDirectory = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath
}

foreach ($RelativePath in $RequiredFiles) {
    Copy-RelativeFile $RelativePath
}

foreach ($WebFile in Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'app_win7\web') -File) {
    Copy-RelativeFile (Join-Path 'app_win7\web' $WebFile.Name)
}
foreach ($AssetFile in Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'delivery_assets_win7') -File) {
    Copy-RelativeFile (Join-Path 'delivery_assets_win7' $AssetFile.Name)
}
foreach ($SampleFile in Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'diagnostics\normal_detection\samples') -File) {
    Copy-RelativeFile (Join-Path 'diagnostics\normal_detection\samples' $SampleFile.Name)
}
foreach ($ReferenceFile in Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'diagnostics\header_fix_regression') -File -Filter '*.result.jpg') {
    Copy-RelativeFile (Join-Path 'diagnostics\header_fix_regression' $ReferenceFile.Name)
}

$ManifestPath = Join-Path $PackageRoot 'SOURCE_SHA256.txt'
$ManifestLines = foreach ($File in Get-ChildItem -LiteralPath $PackageRoot -Recurse -File | Sort-Object FullName) {
    $RelativePath = $File.FullName.Substring($PackageRoot.Length + 1).Replace('\', '/')
    $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
    "$Hash  $RelativePath"
}
[IO.File]::WriteAllText($ManifestPath, (($ManifestLines -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($true))

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -LiteralPath $PackageRoot -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host "Source package: $ZipPath"
