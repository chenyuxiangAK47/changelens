"""
ChangeLens Summary Report Generator
Generates research-ready summary document with methodology, results, and analysis.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


def format_ci(lower: float, upper: float, mean: float, unit: str = '') -> str:
    """Format confidence interval as string."""
    return f"{mean:.2f}{unit} [{lower:.2f}, {upper:.2f}]"


def generate_summary(
    aggregated_results: Dict,
    output_dir: Path,
    n_runs: int = 10
) -> str:
    """
    Generate research-ready summary markdown.
    
    Args:
        aggregated_results: Aggregated statistical results
        output_dir: Output directory
        n_runs: Number of runs
    
    Returns:
        Markdown summary text
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    summary = f"""# ChangeLens Experiment Results Summary

**Generated**: {timestamp}  
**Experiment Runs**: {n_runs} per scenario

---

## Methodology

### Experimental Design

We conducted a comparative evaluation of Blue-Green and Canary deployment strategies using the ChangeLens benchmark. Each scenario was executed **{n_runs} times** with different random seeds (base seed: 42, seeds: 42-{41+n_runs}) to ensure statistical validity.

### System Configuration

- **Microservices**: API v1 (baseline), API v2 (with regressions), Downstream service
- **Database**: PostgreSQL 15
- **Load Generator**: k6 with 10 concurrent virtual users
- **Test Duration**: 10 minutes per run (60s warmup + 540s main test)
- **Regression Types**: CPU contention, missing DB index, downstream latency/errors
- **Rollback Thresholds**: P99 latency > 500ms OR error rate > 5% for 2 consecutive windows

### Deployment Schedules

**Blue-Green Deployment**:
- T=120s: Instant 100% traffic switch from v1 to v2

**Canary Deployment**:
- T=120s: 5% traffic to v2
- T=180s: 25% traffic to v2  
- T=240s: 100% traffic to v2

### Statistical Analysis

- **Confidence Intervals**: 95% bootstrap confidence intervals (percentile method, 1000 bootstrap samples)
- **Effect Size**: Cliff's Delta for non-parametric comparison
- **Metrics**: Mean ± standard deviation with 95% CI

---

## Results

### Performance Metrics

"""
    
    # Add results for each scenario
    if 'canary' in aggregated_results and 'bluegreen' in aggregated_results:
        canary = aggregated_results['canary']
        bluegreen = aggregated_results['bluegreen']
        
        # P99 Latency
        if 'p99_latency' in canary and 'p99_latency' in bluegreen:
            c_p99 = canary['p99_latency']
            b_p99 = bluegreen['p99_latency']
            
            summary += f"""#### P99 Latency

| Scenario | Mean ± SD (ms) | 95% CI (ms) |
|----------|----------------|-------------|
| **Canary** | {c_p99['p99_latency_mean']:.2f} ± {c_p99['p99_latency_std']:.2f} | [{c_p99['p99_latency_ci_lower']:.2f}, {c_p99['p99_latency_ci_upper']:.2f}] |
| **Blue-Green** | {b_p99['p99_latency_mean']:.2f} ± {b_p99['p99_latency_std']:.2f} | [{b_p99['p99_latency_ci_lower']:.2f}, {b_p99['p99_latency_ci_upper']:.2f}] |

"""
        
        # Error Rate
        if 'error_rate' in canary and 'error_rate' in bluegreen:
            c_err = canary['error_rate']
            b_err = bluegreen['error_rate']
            
            summary += f"""#### Error Rate

| Scenario | Mean ± SD (%) | 95% CI (%) |
|----------|---------------|------------|
| **Canary** | {c_err['error_rate_mean']*100:.2f} ± {c_err['error_rate_std']*100:.2f} | [{c_err['error_rate_ci_lower']*100:.2f}, {c_err['error_rate_ci_upper']*100:.2f}] |
| **Blue-Green** | {b_err['error_rate_mean']*100:.2f} ± {b_err['error_rate_std']*100:.2f} | [{b_err['error_rate_ci_lower']*100:.2f}, {b_err['error_rate_ci_upper']*100:.2f}] |

"""
        
        # TTD
        if 'ttd' in canary and 'ttd' in bluegreen:
            c_ttd = canary['ttd']
            b_ttd = bluegreen['ttd']
            
            summary += f"""#### Time-to-Detection (TTD)

| Scenario | Mean ± SD (s) | 95% CI (s) |
|----------|---------------|------------|
| **Canary** | {c_ttd['ttd_mean']:.2f} ± {c_ttd['ttd_std']:.2f} | [{c_ttd['ttd_ci_lower']:.2f}, {c_ttd['ttd_ci_upper']:.2f}] |
| **Blue-Green** | {b_ttd['ttd_mean']:.2f} ± {b_ttd['ttd_std']:.2f} | [{b_ttd['ttd_ci_lower']:.2f}, {b_ttd['ttd_ci_upper']:.2f}] |

"""
        
        # Recovery Time
        if 'recovery_time' in canary and 'recovery_time' in bluegreen:
            c_rec = canary['recovery_time']
            b_rec = bluegreen['recovery_time']
            
            summary += f"""#### Recovery Time

| Scenario | Mean ± SD (s) | 95% CI (s) |
|----------|---------------|------------|
| **Canary** | {c_rec['recovery_time_mean']:.2f} ± {c_rec['recovery_time_std']:.2f} | [{c_rec['recovery_time_ci_lower']:.2f}, {c_rec['recovery_time_ci_upper']:.2f}] |
| **Blue-Green** | {b_rec['recovery_time_mean']:.2f} ± {b_rec['recovery_time_std']:.2f} | [{b_rec['recovery_time_ci_lower']:.2f}, {b_rec['recovery_time_ci_upper']:.2f}] |

"""
        
        # Impact Scope
        if 'impact_traffic' in canary and 'impact_users' in canary:
            c_traffic = canary['impact_traffic']
            c_users = canary['impact_users']
            
            summary += f"""#### Impact Scope (Canary)

- **Traffic to v2 before rollback**: {c_traffic['impact_traffic_mean']:.2f}% [{c_traffic['impact_traffic_ci_lower']:.2f}, {c_traffic['impact_traffic_ci_upper']:.2f}]
- **Affected users**: {c_users['impact_users_mean']:.2f}% [{c_users['impact_users_ci_lower']:.2f}, {c_users['impact_users_ci_upper']:.2f}]

"""
        
        # Effect Sizes
        if 'effect_sizes' in aggregated_results:
            summary += """### Effect Size Comparison

"""
            for metric, effect in aggregated_results['effect_sizes'].items():
                if 'cohens_d' in effect:
                    summary += f"- **{metric}**: Cohen's d = {effect['cohens_d']:.3f} ({effect.get('interpretation', 'unknown')} effect)\n"
    
    summary += """
---

## Key Findings

1. **Deployment Strategy Comparison**: Canary deployment shows [describe findings based on results]

2. **Time-to-Detection**: [Describe TTD findings]

3. **Recovery Characteristics**: [Describe recovery time findings]

4. **Impact Mitigation**: Canary deployment limits impact to [X]% of traffic before rollback, compared to 100% for Blue-Green.

---

## Threats to Validity

1. **External Validity**: Results are based on a synthetic microservice benchmark. Real-world systems may exhibit different characteristics due to network conditions, hardware variations, and application-specific behaviors.

2. **Internal Validity**: The controlled regression scenarios (CPU, DB, downstream) may not capture all types of performance regressions encountered in production systems.

3. **Measurement Validity**: Metrics are collected using 10-second aggregation windows. Finer-grained analysis might reveal additional patterns, but coarser windows might miss rapid changes.

---

## Reproducibility

All experiments were conducted with:
- Fixed random seeds (42-51) for deterministic behavior
- Docker containerization for consistent environments
- Complete configuration capture (git commit, docker images, environment variables)
- Configuration files saved in `results/run_*/config.json`

To reproduce these results:
1. Ensure Docker services are running: `docker compose up -d`
2. Run experiment suite: `python scripts/run_experiment_suite.py --scenario canary --n-runs 10`
3. Aggregate results: `python scripts/statistical_analysis.py --runs-dir results/canary --scenario canary --output aggregated.json`

---

*Generated by ChangeLens Research Infrastructure*
"""
    
    return summary


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate research summary report')
    parser.add_argument('--results', type=str, required=True, help='Aggregated results JSON file')
    parser.add_argument('--output', type=str, default='results/summary.md', help='Output markdown file')
    parser.add_argument('--n-runs', type=int, default=10, help='Number of runs per scenario')
    
    args = parser.parse_args()
    
    # Load aggregated results
    with open(args.results, 'r') as f:
        aggregated_results = json.load(f)
    
    # Generate summary
    summary = generate_summary(
        aggregated_results=aggregated_results,
        output_dir=Path(args.output).parent,
        n_runs=args.n_runs
    )
    
    # Save summary
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"Summary report saved to {output_path}")


if __name__ == '__main__':
    main()
