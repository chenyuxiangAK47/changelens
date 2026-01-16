# Experiment Results

This directory contains experimental results from ChangeLens benchmark runs.

## Directory Structure

```
results/
├── experiment_YYYYMMDD_HHMMSS/    # Timestamped experiment runs
│   ├── canary/                     # Canary deployment results
│   │   ├── run_1/                  # Individual run results
│   │   │   ├── *.json             # k6 raw output
│   │   │   ├── *.csv              # Parsed metrics
│   │   │   ├── *.png              # Generated plots
│   │   │   ├── events.json        # Rollback events
│   │   │   ├── derived_metrics.json  # TTD, Recovery, Impact
│   │   │   └── config.json         # Experiment configuration
│   │   └── run_N/
│   ├── bluegreen/                  # Blue-Green deployment results
│   │   └── (same structure)
│   ├── aggregated_results.json     # Statistical aggregation
│   └── summary.md                   # Research report
└── README.md                        # This file
```

## Key Files

### aggregated_results.json
Statistical aggregation across all runs:
- Mean, standard deviation, median
- 95% bootstrap confidence intervals
- Effect size (Cliff's Delta)

### summary.md
Research report containing:
- Methodology
- Results with statistical analysis
- Key findings
- Threats to validity
- Reproducibility information

### config.json (per run)
Experiment configuration snapshot:
- Git commit hash
- Docker image tags
- Environment variables
- Random seed
- Host information

## Running Experiments

### Full Research Suite (10 runs per scenario)
```powershell
.\scripts\run_research_suite.ps1 -NRuns 10
```

### Single Scenario
```powershell
python scripts/run_experiment_suite.py --scenario canary --n-runs 10 --base-seed 42 --output-dir results/experiment_$(Get-Date -Format 'yyyyMMdd_HHmmss')/canary
```

## Viewing Results

1. **Aggregated Statistics**: Open `aggregated_results.json` in a JSON viewer
2. **Research Report**: Read `summary.md` for comprehensive analysis
3. **Visualizations**: Check `run_*/latency_*.png` and `run_*/error_rate_*.png`
4. **Individual Metrics**: Examine `run_*/derived_metrics.json` for TTD, Recovery Time, Impact Scope

## Note

Results are excluded from git by default (see `.gitignore`). To share results:
- Upload to a separate repository
- Include in research paper supplementary materials
- Share via cloud storage with appropriate access controls
