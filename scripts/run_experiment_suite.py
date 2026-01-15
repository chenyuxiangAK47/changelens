"""
ChangeLens Multi-Run Experiment Suite Runner
Orchestrates N runs of each scenario with different seeds.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Optional, Dict
import time


def run_experiment(
    scenario: str,
    run_id: int,
    seed: int,
    output_base_dir: Path,
    python_cmd: str = 'python'
) -> bool:
    """
    Run a single experiment.
    
    Args:
        scenario: 'canary' or 'bluegreen'
        run_id: Run identifier
        seed: Random seed
        output_base_dir: Base directory for results
        python_cmd: Python command to use
    
    Returns:
        True if successful, False otherwise
    """
    run_dir = output_base_dir / f'run_{run_id}'
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Run {run_id}/{scenario} (seed={seed})")
    print(f"{'='*60}")
    
    # Determine script based on platform
    import platform
    if platform.system() == 'Windows':
        script = f'scripts/run_{scenario}.ps1'
        cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', script,
               '-Seed', str(seed), '-OutputDir', str(run_dir)]
    else:
        script = f'scripts/run_{scenario}.sh'
        cmd = ['bash', script, '--seed', str(seed), '--output-dir', str(run_dir)]
    
    # Run experiment
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode != 0:
            print(f"ERROR: Experiment run {run_id} failed!")
            return False
        
        # Capture experiment configuration
        print(f"\nCapturing experiment configuration...")
        config_cmd = [
            python_cmd, 'scripts/experiment_config.py',
            '--run-id', str(run_id),
            '--scenario', scenario,
            '--output-dir', str(run_dir),
            '--seed', str(seed)
        ]
        
        config_result = subprocess.run(
            config_cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if config_result.returncode != 0:
            print(f"WARNING: Failed to capture config: {config_result.stderr}")
        
        # Find generated CSV and JSON files
        csv_files = list(run_dir.glob(f'{scenario}_*.csv'))
        json_files = list(run_dir.glob(f'{scenario}_*.json'))
        
        if not csv_files or not json_files:
            print(f"WARNING: Expected output files not found in {run_dir}")
            return False
        
        csv_file = csv_files[0]
        json_file = json_files[0]
        
        # Create events.json (will be populated by derive_metrics if needed)
        events_file = run_dir / 'events.json'
        default_events = {
            "rollback_triggered": False,
            "rollback_time": None,
            "trigger_reason": None,
            "consecutive_bad_windows": 0,
            "deployment_start": 120.0 if scenario == 'canary' else 120.0,
            "rollout_stages": []
        }
        with open(events_file, 'w') as f:
            json.dump(default_events, f, indent=2)
        
        # Calculate derived metrics
        print(f"Calculating derived metrics...")
        derive_cmd = [
            python_cmd, 'scripts/derive_metrics.py',
            '--csv', str(csv_file),
            '--events', str(events_file),
            '--scenario', scenario,
            '--output', str(run_dir / 'derived_metrics.json')
        ]
        
        derive_result = subprocess.run(
            derive_cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        if derive_result.returncode != 0:
            print(f"WARNING: Failed to calculate derived metrics: {derive_result.stderr}")
        else:
            print(derive_result.stdout)
        
        print(f"✓ Run {run_id} completed successfully")
        return True
        
    except Exception as e:
        print(f"ERROR: Exception during run {run_id}: {e}")
        return False


def run_experiment_suite(
    scenario: str,
    n_runs: int = 10,
    base_seed: int = 42,
    output_base_dir: Optional[Path] = None,
    python_cmd: str = 'python'
) -> Dict[str, any]:
    """
    Run N experiments for a scenario.
    
    Args:
        scenario: 'canary' or 'bluegreen'
        n_runs: Number of runs
        base_seed: Base seed (each run uses base_seed + run_id)
        output_base_dir: Base directory for results
        python_cmd: Python command to use
    
    Returns:
        Summary dictionary
    """
    if output_base_dir is None:
        output_base_dir = Path('results') / scenario
    
    output_base_dir = Path(output_base_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Running {n_runs} experiments for {scenario} scenario")
    print(f"Base seed: {base_seed}")
    print(f"Output directory: {output_base_dir}")
    print(f"{'='*60}\n")
    
    successful_runs = 0
    failed_runs = []
    
    for run_id in range(1, n_runs + 1):
        seed = base_seed + run_id - 1
        
        success = run_experiment(
            scenario=scenario,
            run_id=run_id,
            seed=seed,
            output_base_dir=output_base_dir,
            python_cmd=python_cmd
        )
        
        if success:
            successful_runs += 1
        else:
            failed_runs.append(run_id)
        
        # Small delay between runs
        if run_id < n_runs:
            time.sleep(2)
    
    summary = {
        'scenario': scenario,
        'n_runs': n_runs,
        'successful_runs': successful_runs,
        'failed_runs': failed_runs,
        'base_seed': base_seed,
        'output_dir': str(output_base_dir)
    }
    
    print(f"\n{'='*60}")
    print(f"Experiment Suite Summary")
    print(f"{'='*60}")
    print(f"Scenario: {scenario}")
    print(f"Total runs: {n_runs}")
    print(f"Successful: {successful_runs}")
    print(f"Failed: {len(failed_runs)}")
    if failed_runs:
        print(f"Failed run IDs: {failed_runs}")
    print(f"{'='*60}\n")
    
    return summary


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run multi-run experiment suite')
    parser.add_argument('--scenario', type=str, required=True, choices=['canary', 'bluegreen'])
    parser.add_argument('--n-runs', type=int, default=10, help='Number of runs')
    parser.add_argument('--base-seed', type=int, default=42, help='Base random seed')
    parser.add_argument('--output-dir', type=str, default=None, help='Output base directory')
    parser.add_argument('--python-cmd', type=str, default='python', help='Python command')
    
    args = parser.parse_args()
    
    summary = run_experiment_suite(
        scenario=args.scenario,
        n_runs=args.n_runs,
        base_seed=args.base_seed,
        output_base_dir=Path(args.output_dir) if args.output_dir else None,
        python_cmd=args.python_cmd
    )
    
    # Save summary
    summary_file = Path(args.output_dir or 'results') / args.scenario / 'suite_summary.json'
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Suite summary saved to {summary_file}")


if __name__ == '__main__':
    main()
