# CERBER V2 — local RTX 2080: load .env → prepare → train → export
param(
    [ValidateSet("prepare", "train", "export", "all")]
    [string]$Phase = "all",
    [switch]$FullSeraphim,
    [int]$Batch = 0,
    [int]$Epochs = 0
)
$ErrorActionPreference = "Stop"
$PackRoot = Split-Path $PSScriptRoot -Parent
$Repo = (Resolve-Path (Join-Path $PackRoot "..\..\..")).Path
Set-Location $Repo

$VenvPy = Join-Path $PackRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Error "BLOCKED: missing $VenvPy — run setup_local_rtx2080.ps1 first"
}

# load repo .env (KEY=VALUE)
$EnvFile = Join-Path $Repo ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $k = $line.Substring(0, $i).Trim()
        $v = $line.Substring($i + 1).Trim()
        Set-Item -Path "Env:$k" -Value $v
    }
}

if (-not $env:CERBER_V2_ROOT) {
    $env:CERBER_V2_ROOT = "D:/NULLXES/datasets/cerber_v2"
}
if (-not $env:HF_TOKEN) {
    Write-Error "BLOCKED: HF_TOKEN missing in .env"
}

New-Item -ItemType Directory -Force -Path $env:CERBER_V2_ROOT | Out-Null
if ($env:HF_HOME) { New-Item -ItemType Directory -Force -Path $env:HF_HOME | Out-Null }

$TrainCfg = Join-Path $PackRoot "configs\train_rtx2080.yaml"
$Scripts = Join-Path $PackRoot "scripts"
$Best = Join-Path $Repo "runs\detect\cerber-detect\v2-pursuit-2080\weights\best.pt"

Write-Host "=== CERBER V2 local 2080 ==="
Write-Host "CERBER_V2_ROOT=$env:CERBER_V2_ROOT"
Write-Host "HF_TOKEN set: $([bool]$env:HF_TOKEN)"
Write-Host "train_cfg=$TrainCfg"

if ($Phase -eq "prepare" -or $Phase -eq "all") {
    $prep = @(
        $VenvPy, (Join-Path $Scripts "prepare_data.py"),
        "--root", $env:CERBER_V2_ROOT,
        "--merge-local-uav"
    )
    if ($FullSeraphim) { $prep += "--full-seraphim" }
    & $prep[0] $prep[1..($prep.Length - 1)]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Phase -eq "train" -or $Phase -eq "all") {
    $tr = @(
        $VenvPy, (Join-Path $Scripts "train.py"),
        "--train-config", $TrainCfg,
        "--data", (Join-Path $env:CERBER_V2_ROOT "data.yaml"),
        "--weights", (Join-Path $Repo "06_autonomy\models\weights\cerber-cv-v2\best.pt")
    )
    if ($Batch -gt 0) { $tr += @("--batch", "$Batch") }
    if ($Epochs -gt 0) { $tr += @("--epochs", "$Epochs") }
    & $tr[0] $tr[1..($tr.Length - 1)]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Phase -eq "export" -or $Phase -eq "all") {
    if (-not (Test-Path $Best)) {
        Write-Error "BLOCKED: missing $Best"
    }
    & $VenvPy (Join-Path $Scripts "export_onnx.py") --weights $Best
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== DONE phase=$Phase ==="
