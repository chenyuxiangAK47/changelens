"""
指标收集脚本
Metrics Collection Script

定期从API服务收集性能指标（P50/P95/P99延迟、错误率）
并保存到CSV文件用于后续分析和图表生成
"""
import time
import csv
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# API服务URL / API Service URL
API_URL = "http://localhost:8000"
METRICS_ENDPOINT = f"{API_URL}/api/metrics"

# 结果目录 / Results directory
RESULTS_DIR = Path(__file__).parent.parent.parent / "results" / "data"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class MetricsCollector:
    """指标收集器类 / Metrics Collector Class"""
    
    def __init__(self, output_file: Optional[str] = None):
        """
        初始化指标收集器
        Initialize metrics collector
        
        Args:
            output_file: 输出CSV文件路径（可选，默认使用时间戳）
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RESULTS_DIR / f"metrics_{timestamp}.csv"
        
        self.output_file = Path(output_file)
        self.metrics_data: List[Dict] = []
        
        # 创建CSV文件并写入表头
        # Create CSV file and write header
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'p50_latency_ms',
                'p95_latency_ms',
                'p99_latency_ms',
                'error_rate',
                'request_count',
                'deployment_phase',
                'regression_type'
            ])
    
    def collect_metrics(self) -> Optional[Dict]:
        """
        收集一次指标
        Collect metrics once
        
        Returns:
            指标数据字典，如果收集失败则返回None
        """
        try:
            response = requests.get(METRICS_ENDPOINT, timeout=5)
            response.raise_for_status()
            metrics = response.json()
            
            # 添加收集时间戳
            # Add collection timestamp
            metrics['collection_timestamp'] = datetime.now().isoformat()
            
            # 保存到内存
            # Save to memory
            self.metrics_data.append(metrics)
            
            # 追加到CSV文件
            # Append to CSV file
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    metrics['timestamp'],
                    metrics['p50_latency_ms'],
                    metrics['p95_latency_ms'],
                    metrics['p99_latency_ms'],
                    metrics['error_rate'],
                    metrics['request_count'],
                    metrics['deployment_phase'],
                    metrics.get('regression_type', '')
                ])
            
            return metrics
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 指标收集失败 / Metrics collection failed: {e}")
            return None
    
    def collect_continuous(self, interval_seconds: int = 5, duration_seconds: Optional[int] = None):
        """
        持续收集指标
        Collect metrics continuously
        
        Args:
            interval_seconds: 收集间隔（秒）
            duration_seconds: 总收集时长（秒），None表示无限收集
        """
        start_time = time.time()
        iteration = 0
        
        print(f"📊 开始收集指标 / Starting metrics collection")
        print(f"   输出文件 / Output file: {self.output_file}")
        print(f"   收集间隔 / Collection interval: {interval_seconds}秒")
        if duration_seconds:
            print(f"   总时长 / Total duration: {duration_seconds}秒")
        print("-" * 50)
        
        try:
            while True:
                iteration += 1
                metrics = self.collect_metrics()
                
                if metrics:
                    print(f"[{iteration}] {datetime.now().strftime('%H:%M:%S')} | "
                          f"P99: {metrics['p99_latency_ms']:.2f}ms | "
                          f"错误率: {metrics['error_rate']:.2f}% | "
                          f"阶段: {metrics['deployment_phase']} | "
                          f"回归: {metrics.get('regression_type', 'None')}")
                else:
                    print(f"[{iteration}] {datetime.now().strftime('%H:%M:%S')} | ❌ 收集失败 / Collection failed")
                
                # 检查是否达到总时长
                # Check if total duration reached
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\n⚠️  收集被用户中断 / Collection interrupted by user")
        
        finally:
            print("-" * 50)
            print(f"✅ 指标收集完成 / Metrics collection completed")
            print(f"   总收集次数 / Total collections: {iteration}")
            print(f"   数据文件 / Data file: {self.output_file}")
    
    def get_all_metrics(self) -> List[Dict]:
        """获取所有收集的指标 / Get all collected metrics"""
        return self.metrics_data


def main():
    """主函数 / Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ChangeLens 指标收集工具 / ChangeLens Metrics Collector')
    parser.add_argument('--interval', type=int, default=5, help='收集间隔（秒） / Collection interval (seconds)')
    parser.add_argument('--duration', type=int, default=None, help='总收集时长（秒） / Total duration (seconds)')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径 / Output file path')
    
    args = parser.parse_args()
    
    collector = MetricsCollector(output_file=args.output)
    collector.collect_continuous(
        interval_seconds=args.interval,
        duration_seconds=args.duration
    )


if __name__ == "__main__":
    main()
