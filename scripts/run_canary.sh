#!/bin/bash
# ChangeLens Canary Deployment Test Runner

set -e

echo "Starting Canary deployment test..."

# Configuration
K6_SCRIPT="load/k6/scenario_canary.js"
OUTPUT_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
JSON_OUTPUT="${OUTPUT_DIR}/canary_${TIMESTAMP}.json"
CSV_OUTPUT="${OUTPUT_DIR}/canary_${TIMESTAMP}.csv"

# Create results directory
mkdir -p ${OUTPUT_DIR}

# Run k6 test
echo "Running k6 load test..."
k6 run \
    --out json=${JSON_OUTPUT} \
    --env API_V1_URL=http://localhost:8001 \
    --env API_V2_URL=http://localhost:8001 \
    --env P99_THRESHOLD_MS=500 \
    --env ERR_THRESHOLD=0.05 \
    --env WINDOW_SEC=10 \
    --env CONSEC_WINDOWS=2 \
    ${K6_SCRIPT}

# Parse results
echo "Parsing k6 results..."
python scripts/parse_k6.py ${JSON_OUTPUT} ${CSV_OUTPUT} 10

# Generate plots
echo "Generating plots..."
python scripts/plot_results.py ${CSV_OUTPUT} --scenario canary --output-dir ${OUTPUT_DIR}

echo "Canary test completed!"
echo "Results: ${CSV_OUTPUT}"
echo "Plots: ${OUTPUT_DIR}/latency_canary.png, ${OUTPUT_DIR}/error_rate_canary.png"
