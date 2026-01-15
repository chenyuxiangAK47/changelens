"""
ChangeLens Experiment Configuration Capture
Captures complete experiment metadata for reproducibility.
"""

import json
import os
import subprocess
import platform
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def get_git_commit_hash() -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_docker_image_tags() -> Dict[str, str]:
    """Get Docker image tags for services."""
    tags = {}
    try:
        result = subprocess.run(
            ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            images = result.stdout.strip().split('\n')
            for img in images:
                if 'changelens' in img.lower():
                    parts = img.split(':')
                    if len(parts) == 2:
                        service_name = parts[0].replace('changelens-', '').replace('changelens/', '')
                        tags[service_name] = parts[1]
    except Exception:
        pass
    return tags


def get_host_info() -> Dict[str, any]:
    """Get host system information."""
    try:
        return {
            'cpu_cores': psutil.cpu_count(logical=True),
            'cpu_physical_cores': psutil.cpu_count(logical=False),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
        }
    except Exception:
        return {
            'cpu_cores': 'unknown',
            'memory_gb': 'unknown',
            'platform': platform.platform(),
            'python_version': platform.python_version(),
        }


def get_environment_vars() -> Dict[str, str]:
    """Get relevant environment variables."""
    relevant_vars = [
        'REG_CPU', 'REG_DB', 'REG_DOWNSTREAM',
        'P99_THRESHOLD_MS', 'ERR_THRESHOLD', 'WINDOW_SEC', 'CONSEC_WINDOWS',
        'DOWNSTREAM_LATENCY_MS', 'DOWNSTREAM_SPIKE_PROB', 'DOWNSTREAM_SPIKE_MS', 'DOWNSTREAM_ERROR_PROB',
        'API_V1_URL', 'API_V2_URL',
    ]
    
    env_vars = {}
    for var in relevant_vars:
        value = os.getenv(var)
        if value is not None:
            env_vars[var] = value
    
    return env_vars


def capture_config(
    run_id: int,
    scenario: str,
    output_dir: Path,
    random_seed: int,
    load_params: Optional[Dict] = None
) -> Dict:
    """
    Capture complete experiment configuration.
    
    Args:
        run_id: Experiment run identifier
        scenario: Deployment scenario ('canary' or 'bluegreen')
        output_dir: Directory to save config.json
        random_seed: Random seed used for this run
        load_params: Optional load testing parameters
    
    Returns:
        Configuration dictionary
    """
    config = {
        'run_id': run_id,
        'scenario': scenario,
        'timestamp': datetime.now().isoformat(),
        'git_commit': get_git_commit_hash(),
        'docker_images': get_docker_image_tags(),
        'environment': get_environment_vars(),
        'load_params': load_params or {
            'vus': 10,
            'duration': '10m',
            'warmup_duration': 60,
        },
        'random_seed': random_seed,
        'host_info': get_host_info(),
    }
    
    # Save to file
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = output_dir / 'config.json'
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config


def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Capture experiment configuration')
    parser.add_argument('--run-id', type=int, required=True, help='Run ID')
    parser.add_argument('--scenario', type=str, required=True, choices=['canary', 'bluegreen'])
    parser.add_argument('--output-dir', type=str, required=True, help='Output directory')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    args = parser.parse_args()
    
    config = capture_config(
        run_id=args.run_id,
        scenario=args.scenario,
        output_dir=Path(args.output_dir),
        random_seed=args.seed
    )
    
    print(f"Configuration saved to {Path(args.output_dir) / 'config.json'}")
    print(json.dumps(config, indent=2))


if __name__ == '__main__':
    main()
