"""
ChangeLens k6 Results Parser (Fixed for k6 JSON format)
Parses k6 JSON output and generates windowed metrics CSV.
"""

import json
import sys
import csv
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

def parse_k6_json(json_file: str, window_sec: int = 10) -> List[Dict]:
    """
    Parse k6 JSON output and compute windowed metrics.
    Handles k6's actual JSON format with Point types.
    """
    with open(json_file, 'r') as f:
        lines = f.readlines()
    
    # k6 JSON output is one JSON object per line
    all_data = []
    for line in lines:
        if line.strip():
            try:
                data = json.loads(line)
                all_data.append(data)
            except json.JSONDecodeError:
                continue
    
    if not all_data:
        print("Warning: No valid JSON data found in file", file=sys.stderr)
        return []
    
    # Extract Point data for http_req_duration and errors
    windows = defaultdict(lambda: {
        'latencies': [],
        'errors': 0,
        'total': 0,
        'start_time': None
    })
    
    test_start_time = None
    
    # Process all data points
    for data in all_data:
        # Skip Metric type definitions, only process Point data
        if data.get('type') != 'Point':
            continue
        
        metric_name = data.get('metric', '')
        point_data = data.get('data', {})
        
        if not point_data:
            continue
        
        # Extract timestamp
        time_str = point_data.get('time', '')
        if not time_str:
            continue
        
        # Parse ISO 8601 timestamp
        try:
            # Handle timezone offset format
            if '+' in time_str and ':' in time_str.split('+')[1]:
                # Format: 2026-01-14T16:20:15.1029059+08:00
                timestamp = datetime.fromisoformat(time_str)
            else:
                # Try parsing without timezone
                timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            if test_start_time is None:
                test_start_time = timestamp
            elapsed_seconds = (timestamp - test_start_time).total_seconds()
        except (ValueError, TypeError) as e:
            # Skip if we can't parse the timestamp
            continue
        
        # Skip warmup period (first 60 seconds)
        if elapsed_seconds < 60:
            continue
        
        window_key = int(elapsed_seconds / window_sec)
        
        # Process http_req_duration
        if metric_name == 'http_req_duration':
            value = point_data.get('value', 0)
            if value > 0:
                if windows[window_key]['start_time'] is None:
                    windows[window_key]['start_time'] = elapsed_seconds
                
                windows[window_key]['latencies'].append(value)
                windows[window_key]['total'] += 1
        
        # Process http_reqs to count errors (status != 200)
        elif metric_name == 'http_reqs':
            tags = point_data.get('tags', {})
            status = tags.get('status', '')
            expected_response = tags.get('expected_response', 'true')
            
            # Count as error if status is not 200 or expected_response is false
            if status and status != '200':
                windows[window_key]['errors'] += 1
            elif expected_response == 'false':
                windows[window_key]['errors'] += 1
    
    # Compute statistics for each window
    results = []
    for window_key in sorted(windows.keys()):
        window = windows[window_key]
        
        if not window['latencies']:
            continue
        
        latencies = sorted(window['latencies'])
        n = len(latencies)
        
        if n == 0:
            continue
        
        p50_idx = max(0, min(n - 1, int(n * 0.50)))
        p95_idx = max(0, min(n - 1, int(n * 0.95)))
        p99_idx = max(0, min(n - 1, int(n * 0.99)))
        
        result = {
            'window_start': window['start_time'] if window['start_time'] is not None else window_key * window_sec,
            'window_end': (window['start_time'] if window['start_time'] is not None else window_key * window_sec) + window_sec,
            'p50_ms': latencies[p50_idx],
            'p95_ms': latencies[p95_idx],
            'p99_ms': latencies[p99_idx],
            'error_count': window['errors'],
            'total_requests': window['total'],
            'error_rate': window['errors'] / window['total'] if window['total'] > 0 else 0.0
        }
        
        results.append(result)
    
    return results


def write_csv(results: List[Dict], output_file: str):
    """Write results to CSV file."""
    if not results:
        print("No results to write", file=sys.stderr)
        return
    
    fieldnames = ['window_start', 'window_end', 'p50_ms', 'p95_ms', 'p99_ms', 
                  'error_count', 'total_requests', 'error_rate']
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Wrote {len(results)} windows to {output_file}")


def extract_rollback_events(json_file: str, csv_file: str = None, scenario: str = 'bluegreen') -> Dict:
    """
    Extract rollback events from k6 JSON output or infer from CSV metrics.
    Since k6 JSON doesn't include console.log output, we infer rollback from metrics.
    """
    events = {
        "rollback_triggered": False,
        "rollback_time": None,
        "trigger_reason": None,
        "consecutive_bad_windows": 0,
        "deployment_start": 120.0,  # Default deployment start time
        "rollout_stages": []
    }
    
    # If CSV file is provided, infer rollback from metrics
    if csv_file:
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Deployment start time
            deployment_start = 120.0
            if scenario == 'canary':
                events['rollout_stages'] = [
                    {"time": 120, "traffic_pct": 0.05},
                    {"time": 180, "traffic_pct": 0.25},
                    {"time": 240, "traffic_pct": 1.0}
                ]
            else:  # bluegreen
                events['rollout_stages'] = [
                    {"time": 120, "traffic_pct": 1.0}
                ]
            
            # Find rollback: first time after deployment_start where we have 2 consecutive bad windows
            consecutive_bad = 0
            for i, row in enumerate(rows):
                window_start = float(row['window_start'])
                if window_start < deployment_start:
                    continue
                
                p99 = float(row['p99_ms'])
                error_rate = float(row['error_rate'])
                
                # Bad window: P99 > 500ms OR error_rate > 5%
                if p99 > 500 or error_rate > 0.05:
                    consecutive_bad += 1
                    if consecutive_bad >= 2:
                        # Rollback triggered
                        events['rollback_triggered'] = True
                        events['rollback_time'] = window_start
                        events['trigger_reason'] = 'p99_threshold' if p99 > 500 else 'error_rate_threshold'
                        events['consecutive_bad_windows'] = consecutive_bad
                        break
                else:
                    consecutive_bad = 0
        except Exception as e:
            print(f"Warning: Could not infer rollback events from CSV: {e}", file=sys.stderr)
    
    return events


def main():
    if len(sys.argv) < 3:
        print("Usage: parse_k6.py <k6_json_file> <output_csv> [window_sec] [events_json]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_csv = sys.argv[2]
    window_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    events_json = sys.argv[4] if len(sys.argv) > 4 else None
    
    print(f"Parsing {json_file} with {window_sec}s windows...")
    results = parse_k6_json(json_file, window_sec)
    write_csv(results, output_csv)
    
    # Extract and save rollback events (infer from CSV)
    # Determine scenario from file path or default
    scenario = 'bluegreen'
    if 'canary' in json_file.lower() or 'canary' in output_csv.lower():
        scenario = 'canary'
    
    events = extract_rollback_events(json_file, csv_file=output_csv, scenario=scenario)
    if events_json:
        import json as json_lib
        with open(events_json, 'w') as f:
            json_lib.dump(events, f, indent=2)
        print(f"Events saved to {events_json}")
        if events['rollback_triggered']:
            print(f"Rollback detected at {events['rollback_time']:.2f}s")


if __name__ == '__main__':
    main()
