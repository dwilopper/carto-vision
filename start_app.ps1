$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundledPython = Join-Path $env:USERPROFILE ".cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe"

if (Test-Path $bundledPython) {
    $python = $bundledPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} else {
    Write-Error "Python not found. Install Python 3.12+ or use the Codex bundled runtime."
    exit 1
}

Set-Location $projectRoot

Write-Host "Starting CartoVision Diploma..." -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "User: demo / demo123" -ForegroundColor Yellow
Write-Host "Admin: admin / admin123" -ForegroundColor Yellow

if ($python -eq "py") {
    & py -3 run_app.py
} else {
    & $python run_app.py
}
