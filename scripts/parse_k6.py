"""
ChangeLens k6 Results Parser
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
    
    Args:
        json_file: Path to k6 JSON output file
        window_sec: Time window size in seconds
    
    Returns:
        List of windowed metrics dictionaries
    """
    with open(json_file, 'r') as f:
        lines = f.readlines()
    
    # k6 JSON output is one JSON object per line
    all_metrics = []
    for line in lines:
        if line.strip():
            try:
                data = json.loads(line)
                all_metrics.append(data)
            except json.JSONDecodeError:
                continue
    
    if not all_metrics:
        print("Warning: No valid JSON data found in file", file=sys.stderr)
        return []
    
    # Extract metrics from the last summary (k6 outputs incremental updates)
    # We'll process all data points
    windows = defaultdict(lambda: {
        'latencies': [],
        'errors': 0,
        'total': 0,
        'start_time': None
    })
    
    test_start_time = None
    
    # Process all metric updates
    for data in all_metrics:
        metrics = data.get('metrics', {})
        
        # Get test start time
        if test_start_time is None:
            test_start_time = data.get('root_group', {}).get('start_time', 0)
            if test_start_time == 0:
                # Try to get from first metric
                for metric_name, metric_data in metrics.items():
                    values = metric_data.get('values', [])
                    if values:
                        test_start_time = values[0].get('time', 0)
                        break
        
        # Process http_req_duration
        http_req_duration = metrics.get('http_req_duration', {})
        if http_req_duration:
            values = http_req_duration.get('values', [])
            for point in values:
                timestamp = point.get('time', 0)
                value = point.get('value', 0)
                
                if test_start_time and timestamp > 0:
                    elapsed = (timestamp - test_start_time) / 1000  # seconds since start
                    window_key = int(elapsed / window_sec)
                    
                    if windows[window_key]['start_time'] is None:
                        windows[window_key]['start_time'] = elapsed
                    
                    windows[window_key]['latencies'].append(value)
                    windows[window_key]['total'] += 1
        
        # Process http_req_status for errors
        http_req_status = metrics.get('http_req_status', {})
        for status_code, status_data in http_req_status.items():
            if not status_code.startswith('2'):  # Non-2xx are errors
                values = status_data.get('values', [])
                for point in values:
                    timestamp = point.get('time', 0)
                    count = point.get('value', 0)
                    
                    if test_start_time and timestamp > 0:
                        elapsed = (timestamp - test_start_time) / 1000
                        window_key = int(elapsed / window_sec)
                        windows[window_key]['errors'] += count
    
    # If we don't have per-point data, use aggregated metrics from last summary
    if not any(w['latencies'] for w in windows.values()):
        last_data = all_metrics[-1]
        metrics = last_data.get('metrics', {})
        
        # Try to extract aggregated stats
        http_req_duration = metrics.get('http_req_duration', {})
        if http_req_duration:
            # Use aggregated percentiles if available
            p50 = http_req_duration.get('values', {}).get('p(50)', 0)
            p95 = http_req_duration.get('values', {}).get('p(95)', 0)
            p99 = http_req_duration.get('values', {}).get('p(99)', 0)
            count = http_req_duration.get('values', {}).get('count', 0)
            
            if count > 0:
                # Create a single window with aggregated data
                windows[0] = {
                    'latencies': [p50, p95, p99] * (count // 3),  # Approximate distribution
                    'errors': 0,
                    'total': count,
                    'start_time': 0
                }
                
                # Count errors
                http_req_status = metrics.get('http_req_status', {})
                for status_code, status_data in http_req_status.items():
                    if not status_code.startswith('2'):
                        count_val = status_data.get('values', {}).get('count', 0)
                        windows[0]['errors'] += count_val
    
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
        
        p50_idx = max(0, int(n * 0.50))
        p95_idx = max(0, int(n * 0.95))
        p99_idx = max(0, int(n * 0.99))
        
        result = {
            'window_start': window['start_time'] if window['start_time'] is not None else window_key * window_sec,
            'window_end': (window['start_time'] if window['start_time'] is not None else window_key * window_sec) + window_sec,
            'p50_ms': latencies[p50_idx] if p50_idx < n else latencies[-1],
            'p95_ms': latencies[p95_idx] if p95_idx < n else latencies[-1],
            'p99_ms': latencies[p99_idx] if p99_idx < n else latencies[-1],
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


def main():
    if len(sys.argv) < 3:
        print("Usage: parse_k6.py <k6_json_file> <output_csv> [window_sec]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_csv = sys.argv[2]
    window_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    print(f"Parsing {json_file} with {window_sec}s windows...")
    results = parse_k6_json(json_file, window_sec)
    write_csv(results, output_csv)


if __name__ == '__main__':
    main()
