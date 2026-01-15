# ChangeLens Blue-Green Deployment Test Runner (PowerShell)

param(
    [int]$Seed = -1,  # -1 means random seed
    [string]$OutputDir = ""
)

Write-Host "Starting Blue-Green deployment test..." -ForegroundColor Green

# Configuration
$K6_SCRIPT = "load/k6/scenario_bluegreen.js"

# Determine output directory
if ($OutputDir -eq "") {
    $TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
    $OUTPUT_DIR = "results"
    $JSON_OUTPUT = "$OUTPUT_DIR/bluegreen_$TIMESTAMP.json"
    $CSV_OUTPUT = "$OUTPUT_DIR/bluegreen_$TIMESTAMP.csv"
} else {
    $OUTPUT_DIR = $OutputDir
    $TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
    $JSON_OUTPUT = "$OUTPUT_DIR/bluegreen_$TIMESTAMP.json"
    $CSV_OUTPUT = "$OUTPUT_DIR/bluegreen_$TIMESTAMP.csv"
}

# Create results directory
if (-not (Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Path $OUTPUT_DIR | Out-Null
}

# Set seed via environment variable if provided
if ($Seed -ge 0) {
    $env:K6_SEED = $Seed.ToString()
} else {
    $env:K6_SEED = $null
}

# Build k6 command
$k6Args = @(
    "run"
    "--out", "json=$JSON_OUTPUT"
    "--env", "API_V1_URL=http://localhost:8001"
    "--env", "API_V2_URL=http://localhost:8002"
    "--env", "P99_THRESHOLD_MS=500"
    "--env", "ERR_THRESHOLD=0.05"
    "--env", "WINDOW_SEC=10"
    "--env", "CONSEC_WINDOWS=2"
    $K6_SCRIPT
)

# Run k6 test
Write-Host "Running k6 load test..." -ForegroundColor Yellow
& k6 $k6Args

if ($LASTEXITCODE -ne 0) {
    Write-Host "k6 test failed!" -ForegroundColor Red
    exit 1
}

# Parse results
Write-Host "Parsing k6 results..." -ForegroundColor Yellow
$EVENTS_OUTPUT = "$OUTPUT_DIR/events.json"
python scripts/parse_k6.py $JSON_OUTPUT $CSV_OUTPUT 10 $EVENTS_OUTPUT

if ($LASTEXITCODE -ne 0) {
    Write-Host "Parsing failed!" -ForegroundColor Red
    exit 1
}

# Generate plots
Write-Host "Generating plots..." -ForegroundColor Yellow
python scripts/plot_results.py $CSV_OUTPUT --scenario bluegreen --output-dir $OUTPUT_DIR

if ($LASTEXITCODE -ne 0) {
    Write-Host "Plot generation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nBlue-Green test completed!" -ForegroundColor Green
Write-Host "Results: $CSV_OUTPUT" -ForegroundColor Cyan
Write-Host "Plots: $OUTPUT_DIR/latency_bluegreen.png, $OUTPUT_DIR/error_rate_bluegreen.png" -ForegroundColor Cyan
