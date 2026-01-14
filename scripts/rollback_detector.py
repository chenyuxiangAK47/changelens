"""
回滚检测器
Rollback Detector

监控P99延迟和错误率，当超过阈值时自动触发回滚
"""
import time
import requests
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

# 配置 / Configuration
API_URL = "http://localhost:8000"
METRICS_ENDPOINT = f"{API_URL}/api/metrics"

# 回滚阈值 / Rollback Thresholds
P99_THRESHOLD_MULTIPLIER = 1.5  # P99超过基线1.5倍时触发回滚
ERROR_RATE_THRESHOLD = 5.0  # 错误率超过5%时触发回滚

# 基线指标（用于比较）
# Baseline metrics (for comparison)
baseline_p99: Optional[float] = None
baseline_error_rate: Optional[float] = None


class RollbackDetector:
    """回滚检测器类 / Rollback Detector Class"""
    
    def __init__(self, deployment_strategy: str = "blue-green"):
        """
        初始化回滚检测器
        Initialize rollback detector
        
        Args:
            deployment_strategy: 部署策略 ("blue-green" 或 "canary")
        """
        self.deployment_strategy = deployment_strategy
        self.rollback_script = Path(__file__).parent.parent / "deployment" / deployment_strategy / "rollback.sh"
        
        if not self.rollback_script.exists():
            raise FileNotFoundError(f"回滚脚本不存在 / Rollback script not found: {self.rollback_script}")
    
    def get_metrics(self) -> Optional[dict]:
        """
        获取当前指标
        Get current metrics
        
        Returns:
            指标字典，如果获取失败则返回None
        """
        try:
            response = requests.get(METRICS_ENDPOINT, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取指标失败 / Failed to get metrics: {e}")
            return None
    
    def set_baseline(self, p99: float, error_rate: float):
        """
        设置基线指标
        Set baseline metrics
        
        Args:
            p99: 基线P99延迟（毫秒）
            error_rate: 基线错误率（百分比）
        """
        global baseline_p99, baseline_error_rate
        baseline_p99 = p99
        baseline_error_rate = error_rate
        print(f"📊 基线指标已设置 / Baseline metrics set:")
        print(f"   P99延迟: {p99:.2f}ms")
        print(f"   错误率: {error_rate:.2f}%")
    
    def check_rollback_conditions(self, metrics: dict) -> Tuple[bool, str]:
        """
        检查是否需要回滚
        Check if rollback is needed
        
        Args:
            metrics: 当前指标字典
        
        Returns:
            (是否需要回滚, 原因描述)
        """
        if baseline_p99 is None or baseline_error_rate is None:
            return False, "基线未设置 / Baseline not set"
        
        p99 = metrics.get('p99_latency_ms', 0)
        error_rate = metrics.get('error_rate', 0)
        
        # 检查P99阈值
        # Check P99 threshold
        p99_threshold = baseline_p99 * P99_THRESHOLD_MULTIPLIER
        if p99 > p99_threshold:
            return True, f"P99延迟超过阈值: {p99:.2f}ms > {p99_threshold:.2f}ms (基线: {baseline_p99:.2f}ms)"
        
        # 检查错误率阈值
        # Check error rate threshold
        if error_rate > ERROR_RATE_THRESHOLD:
            return True, f"错误率超过阈值: {error_rate:.2f}% > {ERROR_RATE_THRESHOLD}%"
        
        return False, "指标正常 / Metrics normal"
    
    def trigger_rollback(self) -> bool:
        """
        触发回滚
        Trigger rollback
        
        Returns:
            回滚是否成功
        """
        print(f"⏪ 触发回滚 / Triggering rollback...")
        print(f"   部署策略 / Deployment Strategy: {self.deployment_strategy}")
        print(f"   回滚脚本 / Rollback Script: {self.rollback_script}")
        
        try:
            # 执行回滚脚本
            # Execute rollback script
            result = subprocess.run(
                ["bash", str(self.rollback_script)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ 回滚成功 / Rollback successful")
                print(result.stdout)
                return True
            else:
                print(f"❌ 回滚失败 / Rollback failed")
                print(result.stderr)
                return False
        
        except subprocess.TimeoutExpired:
            print(f"❌ 回滚超时 / Rollback timeout")
            return False
        except Exception as e:
            print(f"❌ 回滚异常 / Rollback exception: {e}")
            return False
    
    def monitor_and_detect(self, interval_seconds: int = 5, duration_seconds: Optional[int] = None):
        """
        持续监控并检测回滚条件
        Continuously monitor and detect rollback conditions
        
        Args:
            interval_seconds: 检查间隔（秒）
            duration_seconds: 总监控时长（秒），None表示无限监控
        """
        start_time = time.time()
        iteration = 0
        
        print(f"🔍 开始监控回滚条件 / Starting rollback condition monitoring")
        print(f"   检查间隔 / Check interval: {interval_seconds}秒")
        print(f"   P99阈值倍数 / P99 Threshold Multiplier: {P99_THRESHOLD_MULTIPLIER}x")
        print(f"   错误率阈值 / Error Rate Threshold: {ERROR_RATE_THRESHOLD}%")
        print("-" * 60)
        
        try:
            while True:
                iteration += 1
                metrics = self.get_metrics()
                
                if metrics:
                    should_rollback, reason = self.check_rollback_conditions(metrics)
                    
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{iteration}] {timestamp} | "
                          f"P99: {metrics['p99_latency_ms']:.2f}ms | "
                          f"错误率: {metrics['error_rate']:.2f}% | "
                          f"阶段: {metrics['deployment_phase']}")
                    
                    if should_rollback:
                        print(f"⚠️  检测到回滚条件 / Rollback condition detected: {reason}")
                        if self.trigger_rollback():
                            print(f"✅ 回滚完成，停止监控 / Rollback completed, stopping monitoring")
                            break
                        else:
                            print(f"❌ 回滚失败，继续监控 / Rollback failed, continuing monitoring")
                else:
                    print(f"[{iteration}] {datetime.now().strftime('%H:%M:%S')} | ❌ 无法获取指标 / Unable to get metrics")
                
                # 检查是否达到总时长
                # Check if total duration reached
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\n⚠️  监控被用户中断 / Monitoring interrupted by user")
        
        finally:
            print("-" * 60)
            print(f"✅ 监控结束 / Monitoring ended")
            print(f"   总检查次数 / Total checks: {iteration}")


def main():
    """主函数 / Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ChangeLens 回滚检测器 / ChangeLens Rollback Detector')
    parser.add_argument('--strategy', type=str, default='blue-green', 
                       choices=['blue-green', 'canary'],
                       help='部署策略 / Deployment strategy')
    parser.add_argument('--interval', type=int, default=5, 
                       help='检查间隔（秒） / Check interval (seconds)')
    parser.add_argument('--duration', type=int, default=None, 
                       help='总监控时长（秒） / Total monitoring duration (seconds)')
    parser.add_argument('--baseline-p99', type=float, default=None, 
                       help='基线P99延迟（毫秒） / Baseline P99 latency (ms)')
    parser.add_argument('--baseline-error-rate', type=float, default=None, 
                       help='基线错误率（百分比） / Baseline error rate (percentage)')
    
    args = parser.parse_args()
    
    detector = RollbackDetector(deployment_strategy=args.strategy)
    
    # 设置基线（如果提供）
    # Set baseline (if provided)
    if args.baseline_p99 and args.baseline_error_rate:
        detector.set_baseline(args.baseline_p99, args.baseline_error_rate)
    else:
        # 从当前指标获取基线
        # Get baseline from current metrics
        print("📊 获取基线指标 / Getting baseline metrics...")
        metrics = detector.get_metrics()
        if metrics:
            detector.set_baseline(metrics['p99_latency_ms'], metrics['error_rate'])
        else:
            print("❌ 无法获取基线指标，使用默认值 / Unable to get baseline metrics, using defaults")
            detector.set_baseline(100.0, 0.0)  # 默认基线 / Default baseline
    
    # 开始监控
    # Start monitoring
    detector.monitor_and_detect(
        interval_seconds=args.interval,
        duration_seconds=args.duration
    )


if __name__ == "__main__":
    main()
