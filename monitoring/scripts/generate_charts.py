"""
图表生成脚本
Chart Generation Script

从收集的指标数据生成P99延迟和错误率随时间变化的图表
包含部署阶段和回滚点的标注
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import json

# 设置中文字体支持 / Set Chinese font support
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 结果目录 / Results directory
RESULTS_DIR = Path(__file__).parent.parent.parent / "results"
CHARTS_DIR = RESULTS_DIR / "charts"
DATA_DIR = RESULTS_DIR / "data"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


class ChartGenerator:
    """图表生成器类 / Chart Generator Class"""
    
    def __init__(self, data_file: Optional[str] = None):
        """
        初始化图表生成器
        Initialize chart generator
        
        Args:
            data_file: 指标数据CSV文件路径（可选，默认使用最新的）
        """
        if data_file is None:
            # 查找最新的数据文件
            # Find latest data file
            data_files = sorted(DATA_DIR.glob("metrics_*.csv"), reverse=True)
            if not data_files:
                raise FileNotFoundError("未找到指标数据文件 / No metrics data file found")
            data_file = data_files[0]
        
        self.data_file = Path(data_file)
        self.df = pd.read_csv(self.data_file)
        
        # 转换时间戳
        # Convert timestamp
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        print(f"📊 加载数据文件 / Loading data file: {self.data_file}")
        print(f"   数据点数 / Data points: {len(self.df)}")
    
    def generate_p99_chart(self, output_file: Optional[str] = None, 
                           deployment_phases: Optional[List[Tuple[str, str, str]]] = None,
                           rollback_points: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        生成P99延迟随时间变化图表
        Generate P99 latency vs time chart
        
        Args:
            output_file: 输出文件路径（可选）
            deployment_phases: 部署阶段列表 [(开始时间, 结束时间, 阶段名称), ...]
            rollback_points: 回滚点列表 [(时间, 描述), ...]
        
        Returns:
            输出文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = CHARTS_DIR / f"p99_latency_vs_time_{timestamp}.png"
        else:
            output_file = Path(output_file)
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制P99延迟曲线
        # Plot P99 latency curve
        ax.plot(self.df['timestamp'], self.df['p99_latency_ms'], 
                linewidth=2, color='#2E86AB', label='P99延迟 / P99 Latency (ms)')
        
        # 添加P95和P50作为参考
        # Add P95 and P50 as reference
        ax.plot(self.df['timestamp'], self.df['p95_latency_ms'], 
                linewidth=1, color='#A23B72', alpha=0.6, linestyle='--', label='P95延迟 / P95 Latency (ms)')
        ax.plot(self.df['timestamp'], self.df['p50_latency_ms'], 
                linewidth=1, color='#F18F01', alpha=0.6, linestyle='--', label='P50延迟 / P50 Latency (ms)')
        
        # 标注部署阶段
        # Annotate deployment phases
        if deployment_phases:
            colors = ['#06A77D', '#F18F01', '#D00000', '#7209B7']
            for i, (start, end, phase_name) in enumerate(deployment_phases):
                start_time = pd.to_datetime(start)
                end_time = pd.to_datetime(end)
                ax.axvspan(start_time, end_time, alpha=0.2, color=colors[i % len(colors)], 
                          label=f'部署阶段: {phase_name} / Phase: {phase_name}')
        
        # 标注回滚点
        # Annotate rollback points
        if rollback_points:
            for rollback_time, description in rollback_points:
                rollback_dt = pd.to_datetime(rollback_time)
                # 找到最接近的数据点
                # Find closest data point
                idx = (self.df['timestamp'] - rollback_dt).abs().idxmin()
                p99_value = self.df.loc[idx, 'p99_latency_ms']
                
                ax.plot(rollback_dt, p99_value, 'ro', markersize=12, 
                       markerfacecolor='red', markeredgecolor='darkred', markeredgewidth=2,
                       label='回滚点 / Rollback Point' if rollback_points.index((rollback_time, description)) == 0 else '')
                ax.annotate(f'回滚 / Rollback\n{description}', 
                           xy=(rollback_dt, p99_value),
                           xytext=(10, 20), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 设置图表属性
        # Set chart properties
        ax.set_xlabel('时间 / Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('延迟 (毫秒) / Latency (ms)', fontsize=12, fontweight='bold')
        ax.set_title('P99延迟随时间变化 / P99 Latency vs Time', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=10)
        
        # 格式化x轴时间显示
        # Format x-axis time display
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ P99延迟图表已生成 / P99 latency chart generated: {output_file}")
        return str(output_file)
    
    def generate_error_rate_chart(self, output_file: Optional[str] = None,
                                  deployment_phases: Optional[List[Tuple[str, str, str]]] = None,
                                  rollback_points: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        生成错误率随时间变化图表
        Generate error rate vs time chart
        
        Args:
            output_file: 输出文件路径（可选）
            deployment_phases: 部署阶段列表
            rollback_points: 回滚点列表
        
        Returns:
            输出文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = CHARTS_DIR / f"error_rate_vs_time_{timestamp}.png"
        else:
            output_file = Path(output_file)
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制错误率曲线
        # Plot error rate curve
        ax.plot(self.df['timestamp'], self.df['error_rate'], 
                linewidth=2, color='#D00000', label='错误率 / Error Rate (%)')
        
        # 添加阈值线（5%）
        # Add threshold line (5%)
        ax.axhline(y=5.0, color='orange', linestyle='--', linewidth=2, 
                  label='回滚阈值 / Rollback Threshold (5%)', alpha=0.7)
        
        # 标注部署阶段
        # Annotate deployment phases
        if deployment_phases:
            colors = ['#06A77D', '#F18F01', '#D00000', '#7209B7']
            for i, (start, end, phase_name) in enumerate(deployment_phases):
                start_time = pd.to_datetime(start)
                end_time = pd.to_datetime(end)
                ax.axvspan(start_time, end_time, alpha=0.2, color=colors[i % len(colors)], 
                          label=f'部署阶段: {phase_name} / Phase: {phase_name}')
        
        # 标注回滚点
        # Annotate rollback points
        if rollback_points:
            for rollback_time, description in rollback_points:
                rollback_dt = pd.to_datetime(rollback_time)
                idx = (self.df['timestamp'] - rollback_dt).abs().idxmin()
                error_value = self.df.loc[idx, 'error_rate']
                
                ax.plot(rollback_dt, error_value, 'ro', markersize=12, 
                       markerfacecolor='red', markeredgecolor='darkred', markeredgewidth=2,
                       label='回滚点 / Rollback Point' if rollback_points.index((rollback_time, description)) == 0 else '')
                ax.annotate(f'回滚 / Rollback\n{description}', 
                           xy=(rollback_dt, error_value),
                           xytext=(10, 20), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 设置图表属性
        # Set chart properties
        ax.set_xlabel('时间 / Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('错误率 (%) / Error Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title('错误率随时间变化 / Error Rate vs Time', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=10)
        
        # 格式化x轴时间显示
        # Format x-axis time display
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 错误率图表已生成 / Error rate chart generated: {output_file}")
        return str(output_file)
    
    def generate_both_charts(self, deployment_phases: Optional[List[Tuple[str, str, str]]] = None,
                            rollback_points: Optional[List[Tuple[str, str]]] = None) -> Tuple[str, str]:
        """
        生成两个图表
        Generate both charts
        
        Returns:
            (P99图表路径, 错误率图表路径)
        """
        p99_file = self.generate_p99_chart(deployment_phases=deployment_phases, rollback_points=rollback_points)
        error_file = self.generate_error_rate_chart(deployment_phases=deployment_phases, rollback_points=rollback_points)
        return p99_file, error_file


def main():
    """主函数 / Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ChangeLens 图表生成工具 / ChangeLens Chart Generator')
    parser.add_argument('--data', type=str, default=None, help='数据文件路径 / Data file path')
    parser.add_argument('--phases', type=str, default=None, help='部署阶段JSON文件路径 / Deployment phases JSON file path')
    parser.add_argument('--rollbacks', type=str, default=None, help='回滚点JSON文件路径 / Rollback points JSON file path')
    
    args = parser.parse_args()
    
    # 加载部署阶段和回滚点（如果提供）
    # Load deployment phases and rollback points (if provided)
    deployment_phases = None
    rollback_points = None
    
    if args.phases:
        with open(args.phases, 'r', encoding='utf-8') as f:
            phases_data = json.load(f)
            deployment_phases = [(p['start'], p['end'], p['name']) for p in phases_data]
    
    if args.rollbacks:
        with open(args.rollbacks, 'r', encoding='utf-8') as f:
            rollbacks_data = json.load(f)
            rollback_points = [(r['time'], r['description']) for r in rollbacks_data]
    
    generator = ChartGenerator(data_file=args.data)
    p99_file, error_file = generator.generate_both_charts(
        deployment_phases=deployment_phases,
        rollback_points=rollback_points
    )
    
    print(f"\n📈 图表生成完成 / Charts generated:")
    print(f"   P99延迟图表 / P99 Latency Chart: {p99_file}")
    print(f"   错误率图表 / Error Rate Chart: {error_file}")


if __name__ == "__main__":
    main()
