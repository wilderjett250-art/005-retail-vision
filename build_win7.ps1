$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot '.venv-win7\Scripts\python.exe'
$Entry = Join-Path $ProjectRoot 'app_win7\launcher.py'
$SourcePath = Join-Path $ProjectRoot 'app_win7'
$WebAssets = Join-Path $ProjectRoot 'app_win7\web'
$ModelFile = Join-Path $ProjectRoot 'backend_original\text\best.onnx'
$DistRoot = Join-Path $ProjectRoot 'dist_win7'
$WorkRoot = Join-Path $ProjectRoot 'build_win7_work'
$SpecRoot = Join-Path $ProjectRoot 'build_win7_spec'
$UserBase = Join-Path $ProjectRoot '.pyuserbase-win7'
$WindowsKitRedistRoot = 'C:\Program Files (x86)\Windows Kits\10\Redist'
$UcrtRoot = Get-ChildItem -LiteralPath $WindowsKitRedistRoot -Directory -ErrorAction Stop |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName 'ucrt\DLLs\x64' } |
    Where-Object { Test-Path -LiteralPath (Join-Path $_ 'ucrtbase.dll') } |
    Select-Object -First 1

if (-not $UcrtRoot) {
    throw 'Windows SDK x64 UCRT redistributable directory was not found.'
}

New-Item -ItemType Directory -Path $UserBase -Force | Out-Null
$env:PYTHONUSERBASE = $UserBase
$PythonBase = & $Python -s -c 'import sys; print(sys.base_prefix)'
$env:PATH = "$UcrtRoot;$PythonBase;$(Split-Path -Parent $Python);$env:SystemRoot\System32;$env:SystemRoot"

foreach ($RequiredPath in @($Python, $Entry, $WebAssets, $ModelFile)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Required Win7 build input is missing: $RequiredPath"
    }
}

& $Python -s -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name 'ModernRetailTerminalWin7' `
    --distpath $DistRoot `
    --workpath $WorkRoot `
    --specpath $SpecRoot `
    --paths $SourcePath `
    --add-binary "$UcrtRoot\*.dll;." `
    --add-data "$WebAssets;web_win7" `
    --add-data "$ModelFile;runtime" `
    $Entry

if ($LASTEXITCODE -ne 0) {
    throw 'Windows 7 single-file build failed.'
}

Write-Host "Windows 7 build completed: $(Join-Path $DistRoot 'ModernRetailTerminalWin7.exe')"
