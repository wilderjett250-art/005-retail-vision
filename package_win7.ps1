$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceExe = Join-Path $ProjectRoot 'dist_win7\ModernRetailTerminalWin7.exe'
$AssetsRoot = Join-Path $ProjectRoot 'delivery_assets_win7'
$SampleSource = Join-Path $ProjectRoot 'diagnostics\normal_detection\samples'
$DeliveryRoot = Join-Path $ProjectRoot 'delivery_win7'
$PackageRoot = Join-Path $ProjectRoot 'package_win7_work'

# Keep this script ASCII-only so Windows PowerShell 5.1 can parse it reliably.
$Title = -join [char[]](0x73B0, 0x4EE3, 0x96F6, 0x552E, 0x7EC8, 0x7AEF, 0x667A, 0x6167, 0x8FD0, 0x8425, 0x5E73, 0x53F0)
$SampleDirectoryName = -join [char[]](0x793A, 0x4F8B, 0x56FE, 0x7247)
$Edition = -join [char[]](0x7248)
$Bit = -join [char[]](0x4F4D)
$Portable = -join [char[]](0x514D, 0x5B89, 0x88C5, 0x7248)
$DeliveredExeName = $Title + '_Windows7' + $Edition + '.exe'
$ZipName = $Title + '_Windows7_SP1_64' + $Bit + $Portable + '.zip'
$ZipPath = Join-Path $DeliveryRoot $ZipName

foreach ($RequiredPath in @($SourceExe, $AssetsRoot, $SampleSource)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Required Windows 7 delivery input is missing: $RequiredPath"
    }
}

$ResolvedProject = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
$ResolvedPackage = [IO.Path]::GetFullPath($PackageRoot).TrimEnd('\')
if (-not $ResolvedPackage.StartsWith($ResolvedProject + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Package work directory escaped the project boundary: $ResolvedPackage"
}

if (Test-Path -LiteralPath $PackageRoot) {
    Remove-Item -LiteralPath $PackageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $DeliveryRoot -Force | Out-Null
$SampleTarget = Join-Path $PackageRoot $SampleDirectoryName
New-Item -ItemType Directory -Path $SampleTarget -Force | Out-Null

$DeliveredExe = Join-Path $PackageRoot $DeliveredExeName
Copy-Item -LiteralPath $SourceExe -Destination $DeliveredExe
foreach ($AssetFile in Get-ChildItem -LiteralPath $AssetsRoot -File -Filter '*.txt') {
    $AssetText = Get-Content -LiteralPath $AssetFile.FullName -Raw -Encoding UTF8
    $AssetDestination = Join-Path $PackageRoot $AssetFile.Name
    [IO.File]::WriteAllText($AssetDestination, $AssetText, [Text.UTF8Encoding]::new($true))
}
Get-ChildItem -LiteralPath $SampleSource -File | Copy-Item -Destination $SampleTarget

$ExeHash = (Get-FileHash -LiteralPath $DeliveredExe -Algorithm SHA256).Hash
$HashText = "SHA256  $DeliveredExeName`r`n$ExeHash`r`n"
[IO.File]::WriteAllText((Join-Path $PackageRoot 'SHA256.txt'), $HashText, [Text.UTF8Encoding]::new($true))

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageRoot '*') -DestinationPath $ZipPath -CompressionLevel Optimal

Copy-Item -LiteralPath $DeliveredExe -Destination (Join-Path $DeliveryRoot $DeliveredExeName) -Force
Get-ChildItem -LiteralPath $PackageRoot -File -Filter '*.txt' | Copy-Item -Destination $DeliveryRoot -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'SHA256.txt') -Destination $DeliveryRoot -Force

Write-Host "Windows 7 delivery ZIP: $ZipPath"
