"""
ChangeLens Setup Verification Script
Verifies that all services are running and accessible.
"""

import sys
import requests
import time
from typing import Dict, Tuple

SERVICES = {
    'API v1': 'http://localhost:8001',
    'API v2': 'http://localhost:8002',
    'Downstream': 'http://localhost:8003',
}


def check_service(name: str, url: str) -> Tuple[bool, str]:
    """Check if a service is accessible."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"✓ {name} is healthy: {data.get('status', 'unknown')}"
        else:
            return False, f"✗ {name} returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"✗ {name} is not accessible at {url}"
    except Exception as e:
        return False, f"✗ {name} error: {str(e)}"


def check_version_endpoint(name: str, url: str) -> Tuple[bool, str]:
    """Check version endpoint and regression flags."""
    try:
        response = requests.get(f"{url}/version", timeout=5)
        if response.status_code == 200:
            data = response.json()
            regressions = data.get('regressions', {})
            reg_str = ", ".join([f"{k}={v}" for k, v in regressions.items()])
            return True, f"  Version: {data.get('version')}, Regressions: {reg_str}"
        else:
            return False, f"  Version endpoint returned {response.status_code}"
    except Exception as e:
        return False, f"  Version check error: {str(e)}"


def main():
    print("ChangeLens Setup Verification")
    print("=" * 50)
    
    all_ok = True
    
    for name, url in SERVICES.items():
        ok, message = check_service(name, url)
        print(message)
        if ok and name.startswith('API'):
            # Check version endpoint for API services
            _, version_msg = check_version_endpoint(name, url)
            print(version_msg)
        if not ok:
            all_ok = False
    
    print("\n" + "=" * 50)
    
    if all_ok:
        print("✓ All services are running correctly!")
        print("\nYou can now run:")
        print("  - PowerShell: .\\scripts\\run_canary.ps1")
        print("  - PowerShell: .\\scripts\\run_bluegreen.ps1")
        return 0
    else:
        print("✗ Some services are not accessible.")
        print("\nPlease ensure Docker Compose services are running:")
        print("  docker compose up -d")
        return 1


if __name__ == '__main__':
    sys.exit(main())
