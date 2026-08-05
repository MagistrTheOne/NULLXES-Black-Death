# CERBER V2 — create .venv + CUDA torch + deps for RTX 2080 SUPER (Windows)
$ErrorActionPreference = "Stop"
$PackRoot = Split-Path $PSScriptRoot -Parent
$Repo = (Resolve-Path (Join-Path $PackRoot "..\..\..")).Path
Set-Location $Repo

$Venv = Join-Path $PackRoot ".venv"
$Py = Join-Path $Venv "Scripts\python.exe"
$Pip = Join-Path $Venv "Scripts\pip.exe"

Write-Host "REPO=$Repo"
Write-Host "VENV=$Venv"

if (-not (Test-Path $Py)) {
    py -3.11 -m venv $Venv
    if (-not (Test-Path $Py)) { python -m venv $Venv }
}

& $Py -m pip install --upgrade pip setuptools wheel
& $Pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
& $Pip install -r (Join-Path $PackRoot "requirements_local_rtx2080.txt")

& $Py -c @"
import torch, onnxruntime as ort
print('torch', torch.__version__)
print('cuda', torch.cuda.is_available())
print('gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')
print('vram_gb', round(torch.cuda.get_device_properties(0).total_memory/1024**3, 2) if torch.cuda.is_available() else 'n/a')
print('ort', ort.__version__, ort.get_available_providers())
assert torch.cuda.is_available(), 'BLOCKED: CUDA torch missing'
print('SETUP_OK')
"@

Write-Host "Done. Next: .\scripts\run_local_rtx2080.ps1 -Phase all"
