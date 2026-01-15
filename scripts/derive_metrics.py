"""
ChangeLens Derived Metrics Calculator
Computes research-grade metrics: TTD, Recovery Time, Impact Scope
"""

import json
import csv
import sys
from pathlib import Path
from typing import Dict, Optional, List


def load_csv(csv_file: str) -> List[Dict]:
    """Load metrics CSV file."""
    results = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                'window_start': float(row['window_start']),
                'window_end': float(row['window_end']),
                'p99_ms': float(row['p99_ms']),
                'error_rate': float(row['error_rate']),
                'total_requests': int(row['total_requests']),
                'error_count': int(row['error_count']),
            })
    return results


def load_events(events_file: str) -> Dict:
    """Load rollback events JSON file."""
    try:
        with open(events_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default if file doesn't exist
        return {
            "rollback_triggered": False,
            "rollback_time": None,
            "trigger_reason": None,
            "consecutive_bad_windows": 0,
            "deployment_start": None,
            "rollout_stages": []
        }


def calculate_baseline(metrics: List[Dict], baseline_window: int = 60) -> Dict[str, float]:
    """
    Calculate baseline metrics from warmup period.
    
    Args:
        metrics: List of windowed metrics
        baseline_window: Duration of baseline period in seconds
    
    Returns:
        Dictionary with baseline p99 and error_rate
    """
    baseline_metrics = [m for m in metrics if m['window_start'] < baseline_window]
    
    if not baseline_metrics:
        # Fallback: use first few windows
        baseline_metrics = metrics[:6]  # ~60 seconds if 10s windows
    
    if not baseline_metrics:
        return {'p99_ms': 100.0, 'error_rate': 0.01}  # Default baseline
    
    avg_p99 = sum(m['p99_ms'] for m in baseline_metrics) / len(baseline_metrics)
    avg_error_rate = sum(m['error_rate'] for m in baseline_metrics) / len(baseline_metrics)
    
    return {
        'p99_ms': avg_p99,
        'error_rate': avg_error_rate
    }


def calculate_ttd(metrics: List[Dict], events: Dict, scenario: str) -> Optional[float]:
    """
    Calculate Time-to-Detection: time from deployment start to rollback trigger.
    
    Args:
        metrics: Windowed metrics
        events: Rollback events
        scenario: 'canary' or 'bluegreen'
    
    Returns:
        TTD in seconds, or None if no rollback occurred
    """
    if not events.get('rollback_triggered', False):
        return None
    
    deployment_start = events.get('deployment_start')
    rollback_time = events.get('rollback_time')
    
    if deployment_start is None or rollback_time is None:
        # Infer from scenario
        if scenario == 'canary':
            deployment_start = 120.0  # CANARY_5_PCT_TIME
        else:  # bluegreen
            deployment_start = 120.0  # BLUEGREEN_SWITCH_TIME
        
        # Try to infer rollback_time from metrics
        # Find first window where error_rate > 0.05 or p99 > 500
        for m in metrics:
            if m['window_start'] >= deployment_start:
                if m['p99_ms'] > 500 or m['error_rate'] > 0.05:
                    # Check if next window also bad (consecutive bad windows)
                    next_idx = metrics.index(m) + 1
                    if next_idx < len(metrics):
                        next_m = metrics[next_idx]
                        if next_m['p99_ms'] > 500 or next_m['error_rate'] > 0.05:
                            rollback_time = next_m['window_end']
                            break
    
    if rollback_time is None:
        return None
    
    ttd = rollback_time - deployment_start
    return max(0, ttd)


def calculate_recovery_time(metrics: List[Dict], events: Dict, baseline_window: int = 60) -> Optional[float]:
    """
    Calculate Recovery Time: time from rollback trigger to metrics return to baseline.
    
    Args:
        metrics: Windowed metrics
        events: Rollback events
        baseline_window: Duration of baseline period
    
    Returns:
        Recovery time in seconds, or None if no rollback occurred
    """
    if not events.get('rollback_triggered', False):
        return None
    
    rollback_time = events.get('rollback_time')
    if rollback_time is None:
        return None
    
    baseline = calculate_baseline(metrics, baseline_window)
    baseline_p99 = baseline['p99_ms']
    baseline_error_rate = baseline['error_rate']
    
    # Recovery criteria: P99 < baseline + 10% AND error_rate < baseline + 1%
    recovery_p99_threshold = baseline_p99 * 1.1
    recovery_error_threshold = baseline_error_rate + 0.01
    
    # Find first window after rollback where metrics recover
    for m in metrics:
        if m['window_start'] >= rollback_time:
            if m['p99_ms'] < recovery_p99_threshold and m['error_rate'] < recovery_error_threshold:
                recovery_time = m['window_end'] - rollback_time
                return max(0, recovery_time)
    
    # If no recovery found, return time to end of experiment
    if metrics:
        last_window = metrics[-1]
        recovery_time = last_window['window_end'] - rollback_time
        return max(0, recovery_time)
    
    return None


def calculate_impact_scope(metrics: List[Dict], events: Dict, scenario: str) -> Dict[str, float]:
    """
    Calculate Impact Scope: percentage of traffic affected before rollback.
    
    Args:
        metrics: Windowed metrics
        events: Rollback events
        scenario: 'canary' or 'bluegreen'
    
    Returns:
        Dictionary with impact metrics
    """
    if not events.get('rollback_triggered', False):
        return {
            'traffic_to_v2_pct': 0.0,
            'affected_users_pct': 0.0,
            'total_requests_before_rollback': 0,
            'error_rate_during_regression': 0.0
        }
    
    deployment_start = events.get('deployment_start', 120.0)
    rollback_time = events.get('rollback_time')
    
    if rollback_time is None:
        # Estimate from metrics
        for m in metrics:
            if m['window_start'] >= deployment_start:
                if m['p99_ms'] > 500 or m['error_rate'] > 0.05:
                    rollback_time = m['window_end']
                    break
    
    if rollback_time is None:
        return {
            'traffic_to_v2_pct': 0.0,
            'affected_users_pct': 0.0,
            'total_requests_before_rollback': 0,
            'error_rate_during_regression': 0.0
        }
    
    # Calculate traffic percentage to v2 before rollback based on scenario
    rollout_stages = events.get('rollout_stages', [])
    
    if scenario == 'canary':
        # Canary: weighted average of traffic percentages
        total_time = rollback_time - deployment_start
        if total_time <= 0:
            traffic_pct = 0.0
        elif total_time <= 60:  # 5% phase
            traffic_pct = 0.05
        elif total_time <= 120:  # 25% phase
            # Weighted: 60s at 5%, rest at 25%
            traffic_pct = (60 * 0.05 + (total_time - 60) * 0.25) / total_time
        else:  # 100% phase
            # Weighted: 60s at 5%, 60s at 25%, rest at 100%
            traffic_pct = (60 * 0.05 + 60 * 0.25 + (total_time - 120) * 1.0) / total_time
    else:  # bluegreen
        # Blue-Green: 100% after switch
        traffic_pct = 1.0 if rollback_time > deployment_start else 0.0
    
    # Calculate metrics during regression period
    regression_metrics = [m for m in metrics 
                          if deployment_start <= m['window_start'] < rollback_time]
    
    if not regression_metrics:
        regression_metrics = [m for m in metrics if m['window_start'] >= deployment_start][:3]
    
    total_requests = sum(m['total_requests'] for m in regression_metrics)
    total_errors = sum(m['error_count'] for m in regression_metrics)
    error_rate_during_regression = total_errors / total_requests if total_requests > 0 else 0.0
    
    # Affected users = traffic_to_v2 × error_rate
    affected_users_pct = traffic_pct * error_rate_during_regression
    
    return {
        'traffic_to_v2_pct': traffic_pct * 100,  # Convert to percentage
        'affected_users_pct': affected_users_pct * 100,
        'total_requests_before_rollback': total_requests,
        'error_rate_during_regression': error_rate_during_regression
    }


def calculate_all_metrics(csv_file: str, events_file: str, scenario: str) -> Dict:
    """
    Calculate all derived metrics for a single run.
    
    Args:
        csv_file: Path to metrics CSV
        events_file: Path to events JSON
        scenario: 'canary' or 'bluegreen'
    
    Returns:
        Dictionary with all derived metrics
    """
    metrics = load_csv(csv_file)
    events = load_events(events_file)
    
    baseline = calculate_baseline(metrics)
    ttd = calculate_ttd(metrics, events, scenario)
    recovery_time = calculate_recovery_time(metrics, events)
    impact_scope = calculate_impact_scope(metrics, events, scenario)
    
    return {
        'baseline': baseline,
        'ttd_seconds': ttd,
        'recovery_time_seconds': recovery_time,
        'impact_scope': impact_scope,
        'rollback_triggered': events.get('rollback_triggered', False)
    }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate derived research metrics')
    parser.add_argument('--csv', type=str, required=True, help='Metrics CSV file')
    parser.add_argument('--events', type=str, required=True, help='Events JSON file')
    parser.add_argument('--scenario', type=str, required=True, choices=['canary', 'bluegreen'])
    parser.add_argument('--output', type=str, required=True, help='Output JSON file')
    
    args = parser.parse_args()
    
    metrics = calculate_all_metrics(args.csv, args.events, args.scenario)
    
    with open(args.output, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"Derived metrics saved to {args.output}")
    print(f"TTD: {metrics['ttd_seconds']}s")
    print(f"Recovery Time: {metrics['recovery_time_seconds']}s")
    print(f"Impact Scope - Traffic to v2: {metrics['impact_scope']['traffic_to_v2_pct']:.2f}%")
    print(f"Impact Scope - Affected Users: {metrics['impact_scope']['affected_users_pct']:.2f}%")


if __name__ == '__main__':
    main()
