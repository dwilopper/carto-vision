$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ScriptDir "runtime\python\python.exe"
$AppEntry = Join-Path $ScriptDir "run_app.py"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Host "РќРµ РЅР°Р№РґРµРЅ РІСЃС‚СЂРѕРµРЅРЅС‹Р№ Python: $PythonExe" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $AppEntry)) {
    Write-Host "РќРµ РЅР°Р№РґРµРЅ С„Р°Р№Р» Р·Р°РїСѓСЃРєР° РїСЂРёР»РѕР¶РµРЅРёСЏ: $AppEntry" -ForegroundColor Red
    exit 1
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host ""
Write-Host "Starting CartoVision..." -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8000 in your browser." -ForegroundColor DarkGray
Write-Host ""

& $PythonExe $AppEntry
