"""
ChangeLens ML Dataset Builder
Extracts features from experiment runs and creates labeled dataset for ML training.
"""

import json
import csv
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats


def load_csv_metrics(csv_file: str) -> List[Dict]:
    """Load metrics from CSV file."""
    metrics = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics.append({
                'window_start': float(row['window_start']),
                'window_end': float(row['window_end']),
                'p50_ms': float(row['p50_ms']),
                'p95_ms': float(row['p95_ms']),
                'p99_ms': float(row['p99_ms']),
                'error_count': int(row['error_count']),
                'total_requests': int(row['total_requests']),
                'error_rate': float(row['error_rate'])
            })
    return metrics


def load_events(events_file: str) -> Dict:
    """Load rollback events from JSON file."""
    try:
        with open(events_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "rollback_triggered": False,
            "rollback_time": None,
            "trigger_reason": None,
            "deployment_start": 120.0,
            "rollout_stages": []
        }


def load_config(config_file: str) -> Dict:
    """Load experiment configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def calculate_baseline(metrics: List[Dict], baseline_duration: int = 60) -> Dict[str, float]:
    """Calculate baseline metrics from warmup period."""
    baseline_metrics = [m for m in metrics if m['window_start'] < baseline_duration]
    
    if not baseline_metrics:
        # Fallback: use first few windows
        baseline_metrics = metrics[:6] if len(metrics) >= 6 else metrics
    
    if not baseline_metrics:
        return {'p99_ms': 100.0, 'error_rate': 0.01}
    
    avg_p99 = np.mean([m['p99_ms'] for m in baseline_metrics])
    avg_error_rate = np.mean([m['error_rate'] for m in baseline_metrics])
    
    return {
        'p99_ms': avg_p99,
        'error_rate': avg_error_rate
    }


def extract_post_deployment_windows(metrics: List[Dict], deployment_start: float = 120.0, 
                                     window_duration: int = 120) -> List[Dict]:
    """Extract windows from deployment start to deployment_start + window_duration."""
    post_deployment = [
        m for m in metrics 
        if deployment_start <= m['window_start'] < deployment_start + window_duration
    ]
    return sorted(post_deployment, key=lambda x: x['window_start'])


def calculate_trend(values: List[float]) -> float:
    """Calculate linear regression slope (trend) of values over time."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    slope, _ = np.polyfit(x, values, 1)
    return slope


def calculate_rolling_stats(values: List[float], window_size: int = 3) -> Tuple[float, float]:
    """Calculate rolling mean and std of last N values."""
    if len(values) < window_size:
        window_size = len(values)
    if window_size == 0:
        return 0.0, 0.0
    
    last_n = values[-window_size:]
    return np.mean(last_n), np.std(last_n)


def get_traffic_percentage(window_start: float, rollout_stages: List[Dict], 
                           scenario: str) -> float:
    """Get traffic percentage at given time based on rollout stages."""
    if scenario == 'bluegreen':
        # Blue-Green: instant 100% switch at deployment start
        return 1.0 if window_start >= 120.0 else 0.0
    
    # Canary: gradual rollout
    if not rollout_stages:
        return 0.0
    
    for stage in sorted(rollout_stages, key=lambda x: x.get('time', 0), reverse=True):
        if window_start >= stage.get('time', 0):
            return stage.get('traffic_pct', 0.0)
    
    return 0.0


def get_deployment_stage(window_start: float, rollout_stages: List[Dict], 
                         scenario: str) -> int:
    """Get deployment stage number (0=warmup, 1=5%, 2=25%, 3=100%)."""
    if window_start < 120.0:
        return 0  # Warmup
    
    if scenario == 'bluegreen':
        return 3  # 100% traffic
    
    # Canary stages
    if not rollout_stages:
        return 1
    
    for i, stage in enumerate(sorted(rollout_stages, key=lambda x: x.get('time', 0))):
        if window_start >= stage.get('time', 0):
            return i + 1
    
    return 1


def infer_regression_type(config: Dict) -> str:
    """Infer regression type from config or environment variables."""
    # Check environment variables in config
    env = config.get('environment', {})
    
    # Check for regression flags (common patterns)
    reg_cpu = env.get('REG_CPU', '0') == '1' or env.get('REG_CPU', False) is True
    reg_db = env.get('REG_DB', '0') == '1' or env.get('REG_DB', False) is True
    reg_downstream = env.get('REG_DOWNSTREAM', '0') == '1' or env.get('REG_DOWNSTREAM', False) is True
    
    if reg_cpu and reg_db and reg_downstream:
        return 'all'  # All regressions enabled
    elif reg_cpu:
        return 'cpu'
    elif reg_db:
        return 'db'
    elif reg_downstream:
        return 'downstream'
    else:
        return 'none'


def extract_features(metrics: List[Dict], events: Dict, config: Dict, 
                     scenario: str, feature_window: int = 120) -> Dict:
    """Extract features from metrics for ML model."""
    deployment_start = events.get('deployment_start', 120.0)
    rollout_stages = events.get('rollout_stages', [])
    
    # Get baseline metrics
    baseline = calculate_baseline(metrics)
    
    # Extract post-deployment windows
    post_deployment = extract_post_deployment_windows(
        metrics, deployment_start, feature_window
    )
    
    if len(post_deployment) == 0:
        # Not enough data, return None
        return None
    
    # Extract per-window metrics
    p99_values = [m['p99_ms'] for m in post_deployment]
    p95_values = [m['p95_ms'] for m in post_deployment]
    p50_values = [m['p50_ms'] for m in post_deployment]
    error_rates = [m['error_rate'] for m in post_deployment]
    error_counts = [m['error_count'] for m in post_deployment]
    total_requests = [m['total_requests'] for m in post_deployment]
    
    # Calculate deltas from baseline
    p99_deltas = [p99 - baseline['p99_ms'] for p99 in p99_values]
    error_rate_deltas = [er - baseline['error_rate'] for er in error_rates]
    
    # Aggregate features
    features = {
        # Per-window statistics
        'p99_mean': np.mean(p99_values),
        'p99_max': np.max(p99_values),
        'p99_std': np.std(p99_values),
        'p95_mean': np.mean(p95_values),
        'p95_max': np.max(p95_values),
        'error_rate_mean': np.mean(error_rates),
        'error_rate_max': np.max(error_rates),
        'total_requests_mean': np.mean(total_requests),
        
        # Baseline comparison
        'p99_delta_mean': np.mean(p99_deltas),
        'p99_delta_max': np.max(p99_deltas),
        'p99_delta_std': np.std(p99_deltas),
        'error_rate_delta_mean': np.mean(error_rate_deltas),
        'error_rate_delta_max': np.max(error_rate_deltas),
        
        # Trend features
        'p99_trend': calculate_trend(p99_values),
        'error_rate_trend': calculate_trend(error_rates),
        
        # Rolling statistics
        'p99_rolling_mean_3': calculate_rolling_stats(p99_values, 3)[0],
        'p99_rolling_std_3': calculate_rolling_stats(p99_values, 3)[1],
        
        # Deployment context
        'time_since_deployment': feature_window,  # Fixed for all windows in this period
        'traffic_percentage': get_traffic_percentage(
            post_deployment[-1]['window_start'], rollout_stages, scenario
        ),
        'deployment_stage': get_deployment_stage(
            post_deployment[-1]['window_start'], rollout_stages, scenario
        ),
        'scenario_canary': 1 if scenario == 'canary' else 0,
        'scenario_bluegreen': 1 if scenario == 'bluegreen' else 0,
        
        # Number of windows available
        'n_windows': len(post_deployment)
    }
    
    # Labels
    features['will_rollback'] = 1 if events.get('rollback_triggered', False) else 0
    features['regression_type'] = infer_regression_type(config)
    
    # Additional metadata
    features['rollback_time'] = events.get('rollback_time')
    features['deployment_start'] = deployment_start
    
    return features


def find_experiment_runs(results_dir: Path) -> List[Tuple[Path, str, int]]:
    """Find all experiment runs in results directory."""
    runs = []
    
    # Look for experiment_* directories
    for exp_dir in results_dir.glob('experiment_*'):
        for scenario in ['canary', 'bluegreen']:
            scenario_dir = exp_dir / scenario
            if not scenario_dir.exists():
                continue
            
            # Look for run_* directories
            for run_dir in scenario_dir.glob('run_*'):
                # Check if required files exist
                csv_files = list(run_dir.glob(f'{scenario}_*.csv'))
                events_file = run_dir / 'events.json'
                config_file = run_dir / 'config.json'
                
                if csv_files and events_file.exists() and config_file.exists():
                    runs.append((run_dir, scenario, len(runs)))
    
    return runs


def build_dataset(results_dir: str, output_file: str, feature_window: int = 120):
    """Build ML dataset from experiment results."""
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory {results_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Find all experiment runs
    runs = find_experiment_runs(results_path)
    
    if len(runs) == 0:
        print(f"Warning: No experiment runs found in {results_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(runs)} experiment runs")
    
    # Extract features from each run
    all_features = []
    failed_runs = 0
    
    for run_dir, scenario, idx in runs:
        # Find CSV file
        csv_files = list(run_dir.glob(f'{scenario}_*.csv'))
        if not csv_files:
            failed_runs += 1
            continue
        
        csv_file = csv_files[0]
        events_file = run_dir / 'events.json'
        config_file = run_dir / 'config.json'
        
        try:
            # Load data
            metrics = load_csv_metrics(str(csv_file))
            events = load_events(str(events_file))
            config = load_config(str(config_file))
            
            # Extract features
            features = extract_features(metrics, events, config, scenario, feature_window)
            
            if features is None:
                failed_runs += 1
                continue
            
            # Add run metadata
            features['run_id'] = idx
            features['run_path'] = str(run_dir)
            
            all_features.append(features)
            
        except Exception as e:
            print(f"Warning: Failed to process {run_dir}: {e}", file=sys.stderr)
            failed_runs += 1
            continue
    
    if len(all_features) == 0:
        print("Error: No valid features extracted", file=sys.stderr)
        sys.exit(1)
    
    print(f"Successfully extracted features from {len(all_features)} runs")
    if failed_runs > 0:
        print(f"Failed to process {failed_runs} runs", file=sys.stderr)
    
    # Convert to DataFrame-like structure and save as CSV
    fieldnames = [
        'run_id', 'run_path',
        'p99_mean', 'p99_max', 'p99_std',
        'p95_mean', 'p95_max',
        'error_rate_mean', 'error_rate_max',
        'total_requests_mean',
        'p99_delta_mean', 'p99_delta_max', 'p99_delta_std',
        'error_rate_delta_mean', 'error_rate_delta_max',
        'p99_trend', 'error_rate_trend',
        'p99_rolling_mean_3', 'p99_rolling_std_3',
        'time_since_deployment', 'traffic_percentage', 'deployment_stage',
        'scenario_canary', 'scenario_bluegreen',
        'n_windows',
        'will_rollback', 'regression_type',
        'rollback_time', 'deployment_start'
    ]
    
    # Create output directory
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for feat in all_features:
            # Only write features that are in fieldnames
            row = {k: feat.get(k, '') for k in fieldnames}
            writer.writerow(row)
    
    print(f"Dataset saved to {output_file}")
    print(f"Total samples: {len(all_features)}")
    print(f"Rollback samples: {sum(1 for f in all_features if f['will_rollback'] == 1)}")
    print(f"Non-rollback samples: {sum(1 for f in all_features if f['will_rollback'] == 0)}")


def main():
    parser = argparse.ArgumentParser(
        description='Build ML dataset from ChangeLens experiment results'
    )
    parser.add_argument(
        '--results-dir',
        type=str,
        default='results',
        help='Directory containing experiment results'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ml/dataset.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--feature-window',
        type=int,
        default=120,
        help='Feature extraction window in seconds (default: 120)'
    )
    
    args = parser.parse_args()
    
    build_dataset(args.results_dir, args.output, args.feature_window)


if __name__ == '__main__':
    main()
