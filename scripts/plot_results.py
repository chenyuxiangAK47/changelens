"""
ChangeLens Results Plotter
Generates visualization plots for deployment scenarios.
"""

import csv
import sys
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime

# Deployment schedule constants
WARMUP_DURATION = 60
BLUEGREEN_SWITCH_TIME = 120
CANARY_5_PCT_TIME = 120
CANARY_25_PCT_TIME = 180
CANARY_100_PCT_TIME = 240


def load_csv(csv_file: str):
    """Load metrics from CSV file."""
    results = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                'time': float(row['window_start']),
                'p99': float(row['p99_ms']),
                'error_rate': float(row['error_rate']),
                'p50': float(row['p50_ms']),
                'p95': float(row['p95_ms']),
            })
    return results


def plot_latency(results: list, scenario: str, output_file: str):
    """Plot P99 latency over time with rollout/rollback markers."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    times = [r['time'] for r in results]
    p99s = [r['p99'] for r in results]
    
    ax.plot(times, p99s, 'b-', linewidth=2, label='P99 Latency')
    ax.axhline(y=500, color='r', linestyle='--', alpha=0.5, label='P99 Threshold (500ms)')
    
    # Add rollout markers
    if scenario == 'bluegreen':
        ax.axvline(x=BLUEGREEN_SWITCH_TIME, color='g', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(BLUEGREEN_SWITCH_TIME, max(p99s) * 0.9, 'Blue-Green Switch\n(100% to v2)', 
                ha='center', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    elif scenario == 'canary':
        ax.axvline(x=CANARY_5_PCT_TIME, color='orange', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=CANARY_25_PCT_TIME, color='orange', linestyle='--', alpha=0.7, linewidth=1.5)
        ax.axvline(x=CANARY_100_PCT_TIME, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(CANARY_5_PCT_TIME, max(p99s) * 0.9, '5%', ha='center', fontsize=9)
        ax.text(CANARY_25_PCT_TIME, max(p99s) * 0.85, '25%', ha='center', fontsize=9)
        ax.text(CANARY_100_PCT_TIME, max(p99s) * 0.8, '100%', ha='center', fontsize=9)
        ax.text((CANARY_5_PCT_TIME + CANARY_100_PCT_TIME) / 2, max(p99s) * 0.95, 
                'Canary Rollout', ha='center', fontsize=10, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Detect rollback (simplified: if P99 exceeds threshold)
    rollback_times = []
    for i, r in enumerate(results):
        if r['p99'] > 500:  # Threshold
            rollback_times.append(r['time'])
    
    if rollback_times:
        rollback_time = min(rollback_times)
        ax.axvline(x=rollback_time, color='r', linestyle='-', alpha=0.8, linewidth=2)
        ax.text(rollback_time, max(p99s) * 0.7, 'ROLLBACK', ha='center', fontsize=12,
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.3), fontweight='bold')
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('P99 Latency (ms)', fontsize=12)
    ax.set_title(f'P99 Latency Over Time - {scenario.upper()} Deployment', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved latency plot to {output_file}")


def plot_error_rate(results: list, scenario: str, output_file: str):
    """Plot error rate over time with rollout/rollback markers."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    times = [r['time'] for r in results]
    error_rates = [r['error_rate'] * 100 for r in results]  # Convert to percentage
    
    ax.plot(times, error_rates, 'r-', linewidth=2, label='Error Rate')
    ax.axhline(y=5.0, color='r', linestyle='--', alpha=0.5, label='Error Threshold (5%)')
    
    # Add rollout markers
    if scenario == 'bluegreen':
        ax.axvline(x=BLUEGREEN_SWITCH_TIME, color='g', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(BLUEGREEN_SWITCH_TIME, max(error_rates) * 0.9 if error_rates else 5, 
                'Blue-Green Switch\n(100% to v2)', ha='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    elif scenario == 'canary':
        ax.axvline(x=CANARY_5_PCT_TIME, color='orange', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(x=CANARY_25_PCT_TIME, color='orange', linestyle='--', alpha=0.7, linewidth=1.5)
        ax.axvline(x=CANARY_100_PCT_TIME, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(CANARY_5_PCT_TIME, max(error_rates) * 0.9 if error_rates else 5, '5%', ha='center', fontsize=9)
        ax.text(CANARY_25_PCT_TIME, max(error_rates) * 0.85 if error_rates else 4, '25%', ha='center', fontsize=9)
        ax.text(CANARY_100_PCT_TIME, max(error_rates) * 0.8 if error_rates else 3, '100%', ha='center', fontsize=9)
        ax.text((CANARY_5_PCT_TIME + CANARY_100_PCT_TIME) / 2, max(error_rates) * 0.95 if error_rates else 6,
                'Canary Rollout', ha='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Detect rollback
    rollback_times = []
    for i, r in enumerate(results):
        if r['error_rate'] > 0.05:  # 5% threshold
            rollback_times.append(r['time'])
    
    if rollback_times:
        rollback_time = min(rollback_times)
        ax.axvline(x=rollback_time, color='r', linestyle='-', alpha=0.8, linewidth=2)
        ax.text(rollback_time, max(error_rates) * 0.7 if error_rates else 4, 'ROLLBACK', ha='center', fontsize=12,
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.3), fontweight='bold')
    
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Error Rate (%)', fontsize=12)
    ax.set_title(f'Error Rate Over Time - {scenario.upper()} Deployment', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved error rate plot to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Plot ChangeLens results')
    parser.add_argument('csv_file', help='Input CSV file with metrics')
    parser.add_argument('--scenario', choices=['bluegreen', 'canary'], required=True,
                       help='Deployment scenario')
    parser.add_argument('--output-dir', default='./results', help='Output directory for plots')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    results = load_csv(args.csv_file)
    
    if not results:
        print("No data to plot", file=sys.stderr)
        sys.exit(1)
    
    # Generate plots
    latency_file = output_dir / f'latency_{args.scenario}.png'
    error_file = output_dir / f'error_rate_{args.scenario}.png'
    
    plot_latency(results, args.scenario, str(latency_file))
    plot_error_rate(results, args.scenario, str(error_file))
    
    print(f"\nPlots generated:")
    print(f"  - {latency_file}")
    print(f"  - {error_file}")


if __name__ == '__main__':
    main()
