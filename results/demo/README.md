# Demo Results

This directory contains example experiment results demonstrating ChangeLens output.

## Purpose

These are sample results from a complete research experiment run, provided to show:
- Expected output structure
- Research report format (`summary.md`)
- Statistical aggregation (`aggregated_results.json`)
- Visualization examples (latency and error rate plots)

## Structure

```
demo/
├── README.md              # This file
├── aggregated_results.json  # Statistical aggregation across runs
├── summary.md             # Research report with methodology and results
├── canary/
│   └── run_1/            # Example canary deployment run
│       ├── config.json   # Experiment configuration
│       ├── *.csv         # Windowed metrics
│       ├── events.json   # Rollback events
│       ├── derived_metrics.json  # TTD, Recovery, Impact Scope
│       ├── latency_canary.png    # Latency visualization
│       └── error_rate_canary.png # Error rate visualization
└── bluegreen/
    └── run_1/            # Example blue-green deployment run
        └── (same structure)
```

## How to Generate Your Own Results

To reproduce these results or generate new ones:

```powershell
# 1. Setup environment
.\scripts\setup_venv.ps1
.\venv\Scripts\Activate.ps1

# 2. Start services
docker compose up -d

# 3. Run research suite
.\scripts\run_research_suite.ps1 -NRuns 10

# Results will be in: results/experiment_YYYYMMDD_HHMMSS/
```

## Note

These demo results are from a controlled experiment with:
- Regression types: CPU, DB, Downstream (all enabled)
- Deployment strategies: Canary and Blue-Green
- Rollback thresholds: P99 > 500ms OR error rate > 5%
- Number of runs: Varies (see individual config.json files)

For full reproducibility, check the `config.json` files in each run directory for complete experiment configuration.
