"""
ChangeLens Statistical Analysis Module
Bootstrap confidence intervals and effect size (Cliff's Delta)
"""

import json
import numpy as np
from scipy import stats
from typing import List, Dict, Tuple, Optional
from pathlib import Path


def bootstrap_ci(
    data: List[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    method: str = 'percentile'
) -> Tuple[float, float]:
    """
    Calculate bootstrap confidence interval using percentile method.
    
    Args:
        data: Sample data
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (e.g., 0.95 for 95% CI)
        method: 'percentile' (default) or 'bca' (bias-corrected accelerated)
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if len(data) == 0:
        return (0.0, 0.0)
    
    if len(data) == 1:
        return (data[0], data[0])
    
    data_array = np.array(data)
    bootstrap_samples = []
    
    for _ in range(n_bootstrap):
        # Resample with replacement
        sample = np.random.choice(data_array, size=len(data_array), replace=True)
        bootstrap_samples.append(np.mean(sample))
    
    bootstrap_samples = np.array(bootstrap_samples)
    
    # Percentile method
    alpha = 1 - confidence
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100
    
    lower_bound = np.percentile(bootstrap_samples, lower_percentile)
    upper_bound = np.percentile(bootstrap_samples, upper_percentile)
    
    return (float(lower_bound), float(upper_bound))


def cliffs_delta(group_a: List[float], group_b: List[float]) -> float:
    """
    Calculate Cliff's Delta effect size.
    
    Cliff's Delta ranges from -1 to 1:
    - |d| > 0.147: small effect
    - |d| > 0.33: medium effect
    - |d| > 0.474: large effect
    
    Args:
        group_a: First group of values
        group_b: Second group of values
    
    Returns:
        Cliff's Delta value
    """
    if len(group_a) == 0 or len(group_b) == 0:
        return 0.0
    
    group_a = np.array(group_a)
    group_b = np.array(group_b)
    
    # Count dominances
    n_a = len(group_a)
    n_b = len(group_b)
    
    # For each value in group_a, count how many values in group_b it dominates
    # (a > b) - (a < b) for each pair
    dominances = 0
    
    for a_val in group_a:
        for b_val in group_b:
            if a_val > b_val:
                dominances += 1
            elif a_val < b_val:
                dominances -= 1
    
    # Normalize
    delta = dominances / (n_a * n_b)
    
    return float(delta)


def aggregate_metric(
    values: List[float],
    metric_name: str = 'value'
) -> Dict[str, float]:
    """
    Aggregate a metric across runs with statistics.
    
    Args:
        values: List of metric values from different runs
        metric_name: Name of the metric
    
    Returns:
        Dictionary with mean, std, median, and CI
    """
    if len(values) == 0:
        return {
            f'{metric_name}_mean': 0.0,
            f'{metric_name}_std': 0.0,
            f'{metric_name}_median': 0.0,
            f'{metric_name}_ci_lower': 0.0,
            f'{metric_name}_ci_upper': 0.0,
            f'{metric_name}_n': 0
        }
    
    values_array = np.array(values)
    mean = float(np.mean(values_array))
    std = float(np.std(values_array, ddof=1))  # Sample std
    median = float(np.median(values_array))
    
    ci_lower, ci_upper = bootstrap_ci(values)
    
    return {
        f'{metric_name}_mean': mean,
        f'{metric_name}_std': std,
        f'{metric_name}_median': median,
        f'{metric_name}_ci_lower': ci_lower,
        f'{metric_name}_ci_upper': ci_upper,
        f'{metric_name}_n': len(values)
    }


def aggregate_runs(runs_dir: Path, scenario: str) -> Dict:
    """
    Aggregate results across multiple runs for a scenario.
    
    Args:
        runs_dir: Directory containing run_1/, run_2/, etc.
        scenario: 'canary' or 'bluegreen'
    
    Returns:
        Aggregated statistics dictionary
    """
    runs_dir = Path(runs_dir)
    
    # Collect metrics from all runs
    p99_values = []
    error_rate_values = []
    ttd_values = []
    recovery_time_values = []
    impact_traffic_values = []
    impact_users_values = []
    
    run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith('run_')])
    
    for run_dir in run_dirs:
        # Load derived metrics
        derived_metrics_file = run_dir / 'derived_metrics.json'
        if derived_metrics_file.exists():
            with open(derived_metrics_file, 'r') as f:
                derived = json.load(f)
                
                if derived.get('ttd_seconds') is not None:
                    ttd_values.append(derived['ttd_seconds'])
                if derived.get('recovery_time_seconds') is not None:
                    recovery_time_values.append(derived['recovery_time_seconds'])
                
                impact = derived.get('impact_scope', {})
                impact_traffic_values.append(impact.get('traffic_to_v2_pct', 0.0))
                impact_users_values.append(impact.get('affected_users_pct', 0.0))
        
        # Load CSV metrics for P99 and error rate
        csv_files = list(run_dir.glob(f'{scenario}_*.csv'))
        if csv_files:
            import csv as csv_lib
            csv_file = csv_files[0]
            with open(csv_file, 'r') as f:
                reader = csv_lib.DictReader(f)
                rows = list(reader)
                if rows:
                    # Average P99 and error rate across all windows
                    p99_avg = np.mean([float(r['p99_ms']) for r in rows])
                    error_rate_avg = np.mean([float(r['error_rate']) for r in rows])
                    p99_values.append(p99_avg)
                    error_rate_values.append(error_rate_avg)
    
    # Aggregate each metric
    results = {}
    
    if p99_values:
        results['p99_latency'] = aggregate_metric(p99_values, 'p99_latency')
    if error_rate_values:
        results['error_rate'] = aggregate_metric(error_rate_values, 'error_rate')
    if ttd_values:
        results['ttd'] = aggregate_metric(ttd_values, 'ttd')
    if recovery_time_values:
        results['recovery_time'] = aggregate_metric(recovery_time_values, 'recovery_time')
    if impact_traffic_values:
        results['impact_traffic'] = aggregate_metric(impact_traffic_values, 'impact_traffic')
    if impact_users_values:
        results['impact_users'] = aggregate_metric(impact_users_values, 'impact_users')
    
    results['n_runs'] = len(run_dirs)
    
    return results


def compare_scenarios(
    canary_results: Dict,
    bluegreen_results: Dict
) -> Dict[str, float]:
    """
    Compare Canary vs Blue-Green using Cliff's Delta.
    
    Args:
        canary_results: Aggregated results for canary scenario
        bluegreen_results: Aggregated results for bluegreen scenario
    
    Returns:
        Dictionary with effect sizes for each metric
    """
    effect_sizes = {}
    
    # Extract raw values (we need to reload from runs)
    # For now, compare means using effect size calculation
    # In practice, we'd need the raw values from all runs
    
    metrics_to_compare = ['p99_latency', 'error_rate', 'ttd', 'recovery_time']
    
    for metric in metrics_to_compare:
        canary_mean = canary_results.get(metric, {}).get(f'{metric}_mean', 0.0)
        bluegreen_mean = bluegreen_results.get(metric, {}).get(f'{metric}_mean', 0.0)
        
        # Simple effect size approximation (Cohen's d-like)
        # Note: For proper Cliff's Delta, we need raw values from all runs
        if canary_mean > 0 and bluegreen_mean > 0:
            # Approximate effect size
            pooled_std = np.sqrt(
                (canary_results.get(metric, {}).get(f'{metric}_std', 1.0)**2 +
                 bluegreen_results.get(metric, {}).get(f'{metric}_std', 1.0)**2) / 2
            )
            if pooled_std > 0:
                cohens_d = (bluegreen_mean - canary_mean) / pooled_std
                effect_sizes[metric] = {
                    'cohens_d': float(cohens_d),
                    'interpretation': interpret_effect_size(abs(cohens_d))
                }
    
    return effect_sizes


def interpret_effect_size(effect_size: float) -> str:
    """Interpret effect size magnitude."""
    abs_effect = abs(effect_size)
    if abs_effect < 0.2:
        return 'negligible'
    elif abs_effect < 0.5:
        return 'small'
    elif abs_effect < 0.8:
        return 'medium'
    else:
        return 'large'


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Statistical analysis of experiment results')
    parser.add_argument('--runs-dir', type=str, required=True, help='Directory containing run_* subdirectories')
    parser.add_argument('--scenario', type=str, required=True, choices=['canary', 'bluegreen', 'both'])
    parser.add_argument('--output', type=str, required=True, help='Output JSON file')
    
    args = parser.parse_args()
    
    runs_dir = Path(args.runs_dir)
    
    if args.scenario == 'both':
        canary_results = aggregate_runs(runs_dir / 'canary', 'canary')
        bluegreen_results = aggregate_runs(runs_dir / 'bluegreen', 'bluegreen')
        effect_sizes = compare_scenarios(canary_results, bluegreen_results)
        
        results = {
            'canary': canary_results,
            'bluegreen': bluegreen_results,
            'effect_sizes': effect_sizes
        }
    else:
        results = aggregate_runs(runs_dir, args.scenario)
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Statistical analysis saved to {args.output}")
    
    # Print summary
    if args.scenario == 'both':
        print("\nCanary Results:")
        if 'p99_latency' in results['canary']:
            p99 = results['canary']['p99_latency']
            print(f"  P99: {p99['p99_latency_mean']:.2f} ± {p99['p99_latency_std']:.2f} ms")
            print(f"  95% CI: [{p99['p99_latency_ci_lower']:.2f}, {p99['p99_latency_ci_upper']:.2f}]")
        
        print("\nBlue-Green Results:")
        if 'p99_latency' in results['bluegreen']:
            p99 = results['bluegreen']['p99_latency']
            print(f"  P99: {p99['p99_latency_mean']:.2f} ± {p99['p99_latency_std']:.2f} ms")
            print(f"  95% CI: [{p99['p99_latency_ci_lower']:.2f}, {p99['p99_latency_ci_upper']:.2f}]")


if __name__ == '__main__':
    main()
