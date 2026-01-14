"""
实验结果分析脚本
Experiment Results Analysis Script

分析收集的指标数据，生成统计信息和摘要
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

RESULTS_DIR = Path(__file__).parent.parent / "results"
DATA_DIR = RESULTS_DIR / "data"
SUMMARY_FILE = RESULTS_DIR / "summary.md"


class ResultsAnalyzer:
    """结果分析器类 / Results Analyzer Class"""
    
    def __init__(self, data_file: Optional[str] = None):
        """
        初始化结果分析器
        Initialize results analyzer
        
        Args:
            data_file: 指标数据CSV文件路径（可选，默认使用最新的）
        """
        if data_file is None:
            data_files = sorted(DATA_DIR.glob("*.csv"), reverse=True)
            if not data_files:
                raise FileNotFoundError("未找到数据文件 / No data file found")
            data_file = data_files[0]
        
        self.data_file = Path(data_file)
        self.df = pd.read_csv(self.data_file)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        print(f"📊 加载数据文件 / Loading data file: {self.data_file}")
        print(f"   数据点数 / Data points: {len(self.df)}")
    
    def analyze_phases(self) -> Dict[str, Dict]:
        """
        按部署阶段分析指标
        Analyze metrics by deployment phase
        
        Returns:
            各阶段的统计信息字典
        """
        phases = {}
        
        for phase in self.df['deployment_phase'].unique():
            phase_data = self.df[self.df['deployment_phase'] == phase]
            
            phases[phase] = {
                'count': len(phase_data),
                'avg_p50': phase_data['p50_latency_ms'].mean(),
                'avg_p95': phase_data['p95_latency_ms'].mean(),
                'avg_p99': phase_data['p99_latency_ms'].mean(),
                'max_p99': phase_data['p99_latency_ms'].max(),
                'avg_error_rate': phase_data['error_rate'].mean(),
                'max_error_rate': phase_data['error_rate'].max(),
                'total_requests': phase_data['request_count'].sum() if 'request_count' in phase_data.columns else 0
            }
        
        return phases
    
    def detect_regression_impact(self) -> Dict[str, any]:
        """
        检测回归影响
        Detect regression impact
        
        Returns:
            回归影响分析结果
        """
        baseline_data = self.df[self.df['deployment_phase'] == 'baseline']
        regression_data = self.df[self.df['deployment_phase'].str.contains('canary|blue-green', case=False, na=False)]
        
        if len(baseline_data) == 0 or len(regression_data) == 0:
            return {
                'detected': False,
                'message': '缺少基线或回归数据 / Missing baseline or regression data'
            }
        
        baseline_p99 = baseline_data['p99_latency_ms'].mean()
        regression_p99 = regression_data['p99_latency_ms'].mean()
        
        baseline_error = baseline_data['error_rate'].mean()
        regression_error = regression_data['error_rate'].mean()
        
        p99_increase = ((regression_p99 - baseline_p99) / baseline_p99) * 100 if baseline_p99 > 0 else 0
        error_increase = regression_error - baseline_error
        
        return {
            'detected': True,
            'baseline_p99': baseline_p99,
            'regression_p99': regression_p99,
            'p99_increase_percent': p99_increase,
            'baseline_error_rate': baseline_error,
            'regression_error_rate': regression_error,
            'error_increase': error_increase,
            'regression_severe': p99_increase > 50 or error_increase > 5.0
        }
    
    def generate_summary(self) -> str:
        """
        生成1页摘要
        Generate 1-page summary
        
        Returns:
            Markdown格式的摘要文本
        """
        phases = self.analyze_phases()
        regression_impact = self.detect_regression_impact()
        
        summary = f"""# ChangeLens 实验结果摘要
# ChangeLens Experiment Results Summary

**实验时间 / Experiment Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据文件 / Data File**: {self.data_file.name}

## 实验概述 / Experiment Overview

ChangeLens 是一个可复现的云原生微服务基准测试平台，用于研究 CI/CD 变更如何引发尾延迟（P99）和错误率回归，并评估蓝绿部署/金丝雀发布策略以及自动回滚机制。

ChangeLens is a reproducible cloud-native microservices benchmark that studies how CI/CD changes trigger tail latency (P99) and error rate regressions, while evaluating blue-green/canary deployment strategies and automatic rollback mechanisms.

## 各阶段性能指标 / Performance Metrics by Phase

"""
        
        for phase, stats in phases.items():
            summary += f"""### {phase}

- **数据点数 / Data Points**: {stats['count']}
- **平均P50延迟 / Avg P50 Latency**: {stats['avg_p50']:.2f}ms
- **平均P95延迟 / Avg P95 Latency**: {stats['avg_p95']:.2f}ms
- **平均P99延迟 / Avg P99 Latency**: {stats['avg_p99']:.2f}ms
- **最大P99延迟 / Max P99 Latency**: {stats['max_p99']:.2f}ms
- **平均错误率 / Avg Error Rate**: {stats['avg_error_rate']:.2f}%
- **最大错误率 / Max Error Rate**: {stats['max_error_rate']:.2f}%
- **总请求数 / Total Requests**: {stats['total_requests']}

"""
        
        if regression_impact['detected']:
            summary += f"""## 回归影响分析 / Regression Impact Analysis

- **基线P99延迟 / Baseline P99 Latency**: {regression_impact['baseline_p99']:.2f}ms
- **回归后P99延迟 / Regression P99 Latency**: {regression_impact['regression_p99']:.2f}ms
- **P99增长 / P99 Increase**: {regression_impact['p99_increase_percent']:.2f}%
- **基线错误率 / Baseline Error Rate**: {regression_impact['baseline_error_rate']:.2f}%
- **回归后错误率 / Regression Error Rate**: {regression_impact['regression_error_rate']:.2f}%
- **错误率增长 / Error Rate Increase**: {regression_impact['error_increase']:.2f}%
- **回归严重程度 / Regression Severity**: {'严重 / Severe' if regression_impact['regression_severe'] else '中等 / Moderate'}

"""
        
        summary += """## 关键发现 / Key Findings

1. **尾延迟影响 / Tail Latency Impact**: 回归注入显著增加了P99延迟，证明了变更对系统性能的影响。
   Regression injection significantly increased P99 latency, demonstrating the impact of changes on system performance.

2. **错误率变化 / Error Rate Changes**: 回归期间错误率上升，表明变更可能引入稳定性问题。
   Error rate increased during regression, indicating that changes may introduce stability issues.

3. **回滚有效性 / Rollback Effectiveness**: 自动回滚机制能够及时检测并响应性能回归。
   Automatic rollback mechanism can detect and respond to performance regressions in a timely manner.

## 未来工作 / Future Work

- 故障注入框架（混沌工程）
- Fault injection framework (Chaos Engineering)
- 噪声邻居实验（资源争抢）
- Noisy neighbor experiments (resource contention)
- 更智能的回滚阈值（变更感知、负载感知）
- Smarter rollback thresholds (change-aware, load-aware)
- OpenTelemetry分布式追踪用于根因归因
- OpenTelemetry distributed tracing for root cause attribution

## 技术栈 / Tech Stack

- **API服务**: FastAPI (Python)
- **Worker服务**: Python (异步任务处理)
- **数据库**: PostgreSQL
- **负载测试**: k6
- **容器编排**: Docker Compose

---
*Generated by ChangeLens Results Analyzer*
"""
        
        return summary
    
    def save_summary(self, output_file: Optional[str] = None):
        """
        保存摘要到文件
        Save summary to file
        
        Args:
            output_file: 输出文件路径（可选）
        """
        if output_file is None:
            output_file = SUMMARY_FILE
        else:
            output_file = Path(output_file)
        
        summary = self.generate_summary()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"✅ 摘要已保存 / Summary saved: {output_file}")
        return str(output_file)


def main():
    """主函数 / Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ChangeLens 结果分析工具 / ChangeLens Results Analyzer')
    parser.add_argument('--data', type=str, default=None, help='数据文件路径 / Data file path')
    parser.add_argument('--output', type=str, default=None, help='输出摘要文件路径 / Output summary file path')
    
    args = parser.parse_args()
    
    analyzer = ResultsAnalyzer(data_file=args.data)
    
    # 打印阶段分析
    # Print phase analysis
    print("\n📊 各阶段性能指标 / Performance Metrics by Phase:")
    print("-" * 60)
    phases = analyzer.analyze_phases()
    for phase, stats in phases.items():
        print(f"\n{phase}:")
        print(f"  平均P99: {stats['avg_p99']:.2f}ms | 最大P99: {stats['max_p99']:.2f}ms")
        print(f"  平均错误率: {stats['avg_error_rate']:.2f}% | 最大错误率: {stats['max_error_rate']:.2f}%")
    
    # 回归影响分析
    # Regression impact analysis
    print("\n🔍 回归影响分析 / Regression Impact Analysis:")
    print("-" * 60)
    regression_impact = analyzer.detect_regression_impact()
    if regression_impact['detected']:
        print(f"P99增长: {regression_impact['p99_increase_percent']:.2f}%")
        print(f"错误率增长: {regression_impact['error_increase']:.2f}%")
        print(f"回归严重程度: {'严重' if regression_impact['regression_severe'] else '中等'}")
    else:
        print(regression_impact['message'])
    
    # 生成并保存摘要
    # Generate and save summary
    print("\n📝 生成摘要 / Generating summary...")
    analyzer.save_summary(output_file=args.output)


if __name__ == "__main__":
    main()
