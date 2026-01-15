# ChangeLens Research Suite Runner
# Orchestrates complete research workflow: multi-run experiments, aggregation, and reporting

param(
    [int]$NRuns = 10,
    [int]$BaseSeed = 42,
    [string]$PythonCmd = "python"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ChangeLens Research Experiment Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Configuration
$RESULTS_DIR = "results"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$EXPERIMENT_DIR = "$RESULTS_DIR/experiment_$TIMESTAMP"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Runs per scenario: $NRuns" -ForegroundColor Gray
Write-Host "  Base seed: $BaseSeed" -ForegroundColor Gray
Write-Host "  Output directory: $EXPERIMENT_DIR" -ForegroundColor Gray
Write-Host ""

# Step 1: Run Canary experiments
Write-Host "Step 1: Running Canary deployment experiments..." -ForegroundColor Green
$canaryDir = "$EXPERIMENT_DIR/canary"
& $PythonCmd scripts/run_experiment_suite.py `
    --scenario canary `
    --n-runs $NRuns `
    --base-seed $BaseSeed `
    --output-dir $canaryDir `
    --python-cmd $PythonCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Canary experiments failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Run Blue-Green experiments
Write-Host "Step 2: Running Blue-Green deployment experiments..." -ForegroundColor Green
$bluegreenDir = "$EXPERIMENT_DIR/bluegreen"
& $PythonCmd scripts/run_experiment_suite.py `
    --scenario bluegreen `
    --n-runs $NRuns `
    --base-seed $BaseSeed `
    --output-dir $bluegreenDir `
    --python-cmd $PythonCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Blue-Green experiments failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Aggregate results
Write-Host "Step 3: Aggregating results with statistical analysis..." -ForegroundColor Green
$aggregatedFile = "$EXPERIMENT_DIR/aggregated_results.json"

& $PythonCmd scripts/statistical_analysis.py `
    --runs-dir $EXPERIMENT_DIR `
    --scenario both `
    --output $aggregatedFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Statistical analysis failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Generate summary report
Write-Host "Step 4: Generating research summary report..." -ForegroundColor Green
$summaryFile = "$EXPERIMENT_DIR/summary.md"

& $PythonCmd scripts/generate_summary.py `
    --results $aggregatedFile `
    --output $summaryFile `
    --n-runs $NRuns

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Summary generation failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Final summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Research Suite Completed Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results:" -ForegroundColor Yellow
Write-Host "  Experiment directory: $EXPERIMENT_DIR" -ForegroundColor Gray
Write-Host "  Canary results: $canaryDir" -ForegroundColor Gray
Write-Host "  Blue-Green results: $bluegreenDir" -ForegroundColor Gray
Write-Host "  Aggregated statistics: $aggregatedFile" -ForegroundColor Gray
Write-Host "  Summary report: $summaryFile" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review the summary report: $summaryFile" -ForegroundColor Gray
Write-Host "  2. Check individual run results in run_* subdirectories" -ForegroundColor Gray
Write-Host "  3. Examine aggregated statistics: $aggregatedFile" -ForegroundColor Gray
Write-Host ""
