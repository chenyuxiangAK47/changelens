# ChangeLens Canary Deployment Test Runner (PowerShell)

Write-Host "Starting Canary deployment test..." -ForegroundColor Green

# Configuration
$K6_SCRIPT = "load/k6/scenario_canary.js"
$OUTPUT_DIR = "results"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$JSON_OUTPUT = "$OUTPUT_DIR/canary_$TIMESTAMP.json"
$CSV_OUTPUT = "$OUTPUT_DIR/canary_$TIMESTAMP.csv"

# Create results directory
if (-not (Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Path $OUTPUT_DIR | Out-Null
}

# Run k6 test
Write-Host "Running k6 load test..." -ForegroundColor Yellow
k6 run `
    --out "json=$JSON_OUTPUT" `
    --env "API_V1_URL=http://localhost:8001" `
    --env "API_V2_URL=http://localhost:8002" `
    --env "P99_THRESHOLD_MS=500" `
    --env "ERR_THRESHOLD=0.05" `
    --env "WINDOW_SEC=10" `
    --env "CONSEC_WINDOWS=2" `
    $K6_SCRIPT

if ($LASTEXITCODE -ne 0) {
    Write-Host "k6 test failed!" -ForegroundColor Red
    exit 1
}

# Parse results
Write-Host "Parsing k6 results..." -ForegroundColor Yellow
python scripts/parse_k6.py $JSON_OUTPUT $CSV_OUTPUT 10

if ($LASTEXITCODE -ne 0) {
    Write-Host "Parsing failed!" -ForegroundColor Red
    exit 1
}

# Generate plots
Write-Host "Generating plots..." -ForegroundColor Yellow
python scripts/plot_results.py $CSV_OUTPUT --scenario canary --output-dir $OUTPUT_DIR

if ($LASTEXITCODE -ne 0) {
    Write-Host "Plot generation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nCanary test completed!" -ForegroundColor Green
Write-Host "Results: $CSV_OUTPUT" -ForegroundColor Cyan
Write-Host "Plots: $OUTPUT_DIR/latency_canary.png, $OUTPUT_DIR/error_rate_canary.png" -ForegroundColor Cyan
