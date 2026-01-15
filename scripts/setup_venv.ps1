# ChangeLens Environment Setup Script
# Creates Python virtual environment with correct dependencies

param(
    [string]$PythonVersion = "3.12"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ChangeLens Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = "python"
$versionOutput = & $pythonCmd --version 2>&1
Write-Host "  Found: $versionOutput" -ForegroundColor Gray

# Check if Python 3.12 is available
$python312 = "py -3.12"
$version312 = & $python312 --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python 3.12 found, using it for venv" -ForegroundColor Green
    $pythonCmd = $python312
} else {
    Write-Host "  Warning: Python 3.12 not found, using default Python" -ForegroundColor Yellow
    Write-Host "  Recommended: Install Python 3.12 from python.org" -ForegroundColor Yellow
}

# Create venv
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  venv already exists, skipping creation" -ForegroundColor Gray
    Write-Host "  To recreate, delete venv/ directory first" -ForegroundColor Gray
} else {
    & $pythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment!" -ForegroundColor Red
        Write-Host "  Try installing Python 3.12: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies!" -ForegroundColor Red
    Write-Host "  Check requirements.txt and Python version compatibility" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Activate venv: .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  2. Start services: docker compose up -d" -ForegroundColor Gray
Write-Host "  3. Run demo experiment: .\scripts\run_research_suite.ps1 -NRuns 3" -ForegroundColor Gray
Write-Host ""
Write-Host "For full research suite (N=10):" -ForegroundColor Yellow
Write-Host "  .\scripts\run_research_suite.ps1 -NRuns 10" -ForegroundColor Gray
Write-Host ""
