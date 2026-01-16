# ChangeLens Full ML Pipeline Runner
# Runs experiments with regressions enabled, then trains and evaluates ML models

param(
    [int]$NRuns = 3,  # Reduced from 10 to save time/CPU
    [int]$BaseSeed = 42,
    [string]$PythonCmd = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ChangeLens Full ML Pipeline" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker services
Write-Host "Step 1: Checking Docker services..." -ForegroundColor Green
try {
    $dockerCheck = docker-compose ps 2>&1
    if ($LASTEXITCODE -ne 0 -and $dockerCheck -match "pipe|connect") {
        Write-Host "✗ ERROR: Docker services not available!" -ForegroundColor Red
        Write-Host "  Please start Docker Desktop and try again." -ForegroundColor Yellow
        exit 1
    }
    
    # Start services if needed
    Write-Host "Ensuring Docker services are running..." -ForegroundColor Yellow
    docker-compose up -d 2>&1 | Out-Null
    Start-Sleep -Seconds 5
    
    Write-Host "✓ Docker services ready" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Docker check failed, continuing anyway..." -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Set environment variables for regressions
Write-Host "Step 2: Enabling regressions for experiments..." -ForegroundColor Green
$env:REG_CPU = "1"
$env:REG_DB = "1"
$env:REG_DOWNSTREAM = "1"

# Restart api_v2 with regression flags
Write-Host "Restarting api_v2 service with regressions enabled..." -ForegroundColor Yellow
docker-compose up -d --force-recreate api_v2
Start-Sleep -Seconds 5

Write-Host "✓ Regressions enabled (REG_CPU=1, REG_DB=1, REG_DOWNSTREAM=1)" -ForegroundColor Green
Write-Host ""

# Step 3: Run research suite
Write-Host "Step 3: Running research experiment suite (NRuns=$NRuns)..." -ForegroundColor Green
Write-Host "  This will run $NRuns Canary + $NRuns Blue-Green experiments..." -ForegroundColor Gray
Write-Host ""

& $PythonCmd scripts/run_research_suite.ps1 -NRuns $NRuns -BaseSeed $BaseSeed -PythonCmd $PythonCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ERROR: Research suite failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Generate ML dataset
Write-Host "Step 4: Generating ML dataset from experiment results..." -ForegroundColor Green
& $PythonCmd scripts/ml_dataset.py --results-dir results --output ml/dataset.csv

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ERROR: ML dataset generation failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 5: Train ML models
Write-Host "Step 5: Training ML models..." -ForegroundColor Green
& $PythonCmd scripts/ml_train.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ERROR: ML model training failed!" -ForegroundColor Red
    Write-Host "  This might be due to insufficient rollback samples." -ForegroundColor Yellow
    Write-Host "  Try running with more runs: .\scripts\run_full_ml_pipeline.ps1 -NRuns 5" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 6: Evaluate ML models
Write-Host "Step 6: Evaluating ML models..." -ForegroundColor Green
& $PythonCmd scripts/ml_eval.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ERROR: ML model evaluation failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ML Pipeline Completed Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results:" -ForegroundColor Yellow
Write-Host "  Dataset: ml/dataset.csv" -ForegroundColor Gray
Write-Host "  Models: ml/models/" -ForegroundColor Gray
Write-Host "  Evaluation: ml/results/" -ForegroundColor Gray
Write-Host ""
