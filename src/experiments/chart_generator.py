"""
图表生成器
生成论文级别的图表和表格，支持显著性标注
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import warnings

from .statistical_analysis import StatisticalResult

warnings.filterwarnings('ignore')

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 论文风格设置
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, output_dir: str = "experiments/figures", 
                 style: str = "paper", dpi: int = 300):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.style = style
        self.dpi = dpi
        
        # 论文风格配置
        if style == "paper":
            self._setup_paper_style()
    
    def _setup_paper_style(self):
        """设置论文风格"""
        plt.rcParams.update({
            'figure.figsize': (8, 6),
            'font.size': 12,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'figure.dpi': self.dpi,
            'savefig.dpi': self.dpi,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.1
        })
    
    def generate_algorithm_comparison_chart(self, 
                                          results_by_algorithm: Dict[str, List[Any]],
                                          metric: str = "avg_qoe",
                                          statistical_results: Optional[Dict[str, StatisticalResult]] = None,
                                          title: str = "算法性能比较") -> str:
        """生成算法比较图表"""
        
        # 准备数据
        algorithms = list(results_by_algorithm.keys())
        metric_data = []
        
        for algorithm in algorithms:
            results = results_by_algorithm[algorithm]
            values = [getattr(r, 'metrics', {}).get(metric, 0) for r in results if hasattr(r, 'metrics')]
            if not values:  # 如果没有metrics属性，尝试直接访问
                values = [getattr(r, metric, 0) for r in results if hasattr(r, metric)]
            metric_data.append(values)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 箱线图
        box_plot = ax.boxplot(metric_data, labels=algorithms, patch_artist=True)
        
        # 设置颜色
        colors = sns.color_palette("husl", len(algorithms))
        for patch, color in zip(box_plot['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # 添加均值点
        means = [np.mean(data) for data in metric_data]
        ax.scatter(range(1, len(algorithms) + 1), means, 
                  color='red', marker='D', s=50, zorder=3, label='均值')
        
        # 添加显著性标注
        if statistical_results and metric in statistical_results:
            stat_result = statistical_results[metric]
            if stat_result.significant:
                self._add_significance_annotation(ax, stat_result, len(algorithms))
        
        # 设置标签和标题
        ax.set_xlabel('算法')
        ax.set_ylabel(self._get_metric_label(metric))
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 保存图表
        filename = f"algorithm_comparison_{metric}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def generate_ablation_study_chart(self, 
                                    baseline_results: List[Any],
                                    ablation_results: Dict[str, List[Any]],
                                    metric: str = "avg_qoe",
                                    title: str = "消融实验结果") -> str:
        """生成消融实验图表"""
        
        # 计算基线性能
        baseline_values = [getattr(r, 'metrics', {}).get(metric, 0) for r in baseline_results if hasattr(r, 'metrics')]
        baseline_mean = np.mean(baseline_values)
        baseline_std = np.std(baseline_values)
        
        # 计算各消融的性能变化
        ablation_names = []
        performance_changes = []
        error_bars = []
        
        for ablation_name, results in ablation_results.items():
            values = [getattr(r, 'metrics', {}).get(metric, 0) for r in results if hasattr(r, 'metrics')]
            if values:
                mean_value = np.mean(values)
                std_value = np.std(values)
                
                # 计算相对于基线的变化百分比
                change_percent = (mean_value - baseline_mean) / baseline_mean * 100
                
                ablation_names.append(ablation_name.replace('_', ' ').title())
                performance_changes.append(change_percent)
                error_bars.append(std_value / baseline_mean * 100)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 条形图
        bars = ax.bar(ablation_names, performance_changes, 
                     yerr=error_bars, capsize=5, alpha=0.7)
        
        # 设置颜色（正值绿色，负值红色）
        for bar, change in zip(bars, performance_changes):
            if change >= 0:
                bar.set_color('green')
            else:
                bar.set_color('red')
        
        # 添加零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
        
        # 设置标签和标题
        ax.set_xlabel('消融类型')
        ax.set_ylabel('性能变化 (%)')
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 旋转x轴标签
        plt.xticks(rotation=45, ha='right')
        
        # 保存图表
        filename = f"ablation_study_{metric}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def generate_performance_trend_chart(self, 
                                       results: List[Any],
                                       metrics: List[str] = ["avg_qoe", "avg_throughput", "avg_latency"],
                                       title: str = "性能趋势") -> str:
        """生成性能趋势图表"""
        
        # 按时间戳排序
        sorted_results = sorted(results, key=lambda x: getattr(x, 'timestamp', 0))
        
        # 提取数据
        timestamps = [getattr(r, 'timestamp', 0) for r in sorted_results]
        
        # 创建子图
        fig, axes = plt.subplots(len(metrics), 1, figsize=(12, 4 * len(metrics)), sharex=True)
        if len(metrics) == 1:
            axes = [axes]
        
        for i, metric in enumerate(metrics):
            values = [getattr(r, 'metrics', {}).get(metric, 0) for r in sorted_results]
            
            axes[i].plot(timestamps, values, marker='o', linewidth=2, markersize=4)
            axes[i].set_ylabel(self._get_metric_label(metric))
            axes[i].set_title(f"{self._get_metric_label(metric)} 趋势")
            axes[i].grid(True, alpha=0.3)
            
            # 添加趋势线
            if len(values) > 1:
                z = np.polyfit(range(len(values)), values, 1)
                p = np.poly1d(z)
                axes[i].plot(timestamps, p(range(len(values))), 
                           "--", alpha=0.8, color='red', label='趋势线')
                axes[i].legend()
        
        axes[-1].set_xlabel('时间戳')
        plt.suptitle(title, fontsize=16)
        
        # 保存图表
        filename = "performance_trend.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def generate_correlation_heatmap(self, 
                                   results: List[Any],
                                   metrics: Optional[List[str]] = None,
                                   title: str = "指标相关性热图") -> str:
        """生成指标相关性热图"""
        
        # 构建数据矩阵
        data_dict = {}
        for result in results:
            if hasattr(result, 'metrics'):
                for metric, value in result.metrics.items():
                    if metrics is None or metric in metrics:
                        if metric not in data_dict:
                            data_dict[metric] = []
                        data_dict[metric].append(value)
        
        # 创建DataFrame
        df = pd.DataFrame(data_dict)
        
        # 计算相关性矩阵
        corr_matrix = df.corr()
        
        # 创建热图
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 生成热图
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                   square=True, fmt='.2f', cbar_kws={"shrink": .8})
        
        ax.set_title(title)
        
        # 保存图表
        filename = "correlation_heatmap.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def generate_statistical_summary_table(self, 
                                         statistical_results: Dict[str, StatisticalResult],
                                         filename: str = "statistical_summary.csv") -> str:
        """生成统计摘要表格"""
        
        # 准备表格数据
        table_data = []
        for metric, result in statistical_results.items():
            row = {
                '指标': self._get_metric_label(metric),
                '检验方法': result.test_name,
                '统计量': f"{result.statistic:.4f}",
                'p值': f"{result.p_value:.4f}" if result.p_value >= 0.001 else "< 0.001",
                '效应量': f"{result.effect_size:.4f}" if result.effect_size else "N/A",
                '显著性': "是" if result.significant else "否",
                '置信区间': f"[{result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f}]" if result.confidence_interval else "N/A"
            }
            table_data.append(row)
        
        # 创建DataFrame并保存
        df = pd.DataFrame(table_data)
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        return str(filepath)
    
    def _add_significance_annotation(self, ax, stat_result: StatisticalResult, num_groups: int):
        """添加显著性标注"""
        if stat_result.significant:
            # 获取y轴范围
            y_max = ax.get_ylim()[1]
            y_pos = y_max * 1.05
            
            # 添加显著性标记
            if stat_result.p_value < 0.001:
                sig_text = "***"
            elif stat_result.p_value < 0.01:
                sig_text = "**"
            elif stat_result.p_value < 0.05:
                sig_text = "*"
            else:
                sig_text = "ns"
            
            # 在图表顶部添加标注
            ax.text(num_groups / 2, y_pos, sig_text, 
                   ha='center', va='bottom', fontsize=14, fontweight='bold')
            
            # 添加连接线
            if num_groups == 2:
                ax.plot([1, 2], [y_pos * 0.98, y_pos * 0.98], 'k-', linewidth=1)
    
    def _get_metric_label(self, metric: str) -> str:
        """获取指标的中文标签"""
        label_map = {
            'avg_qoe': 'QoE评分',
            'avg_throughput': '平均吞吐量 (Mbps)',
            'avg_latency': '平均延迟 (ms)',
            'avg_admission_rate': '准入成功率',
            'avg_positioning_accuracy': '定位精度 (m)',
            'avg_gdop': '平均GDOP',
            'final_qoe': '最终QoE评分',
            'final_throughput': '最终吞吐量 (Mbps)',
            'final_latency': '最终延迟 (ms)',
            'final_admission_rate': '最终准入率',
            'total_requests': '总请求数',
            'total_accepted': '接受请求数',
            'total_rejected': '拒绝请求数'
        }
        return label_map.get(metric, metric)
    
    def generate_comprehensive_report(self, 
                                    experiment_results: Dict[str, Any],
                                    output_filename: str = "experiment_report") -> List[str]:
        """生成综合实验报告"""
        generated_files = []
        
        # 1. 算法比较图表
        if 'algorithm_comparison' in experiment_results:
            for metric in ['avg_qoe', 'avg_throughput', 'avg_latency']:
                chart_file = self.generate_algorithm_comparison_chart(
                    experiment_results['algorithm_comparison'],
                    metric=metric,
                    statistical_results=experiment_results.get('statistical_results', {})
                )
                generated_files.append(chart_file)
        
        # 2. 消融实验图表
        if 'ablation_results' in experiment_results:
            for ablation_type, ablation_data in experiment_results['ablation_results'].items():
                chart_file = self.generate_ablation_study_chart(
                    experiment_results.get('baseline_results', []),
                    {ablation_type: ablation_data},
                    title=f"{ablation_type.replace('_', ' ').title()} 消融实验"
                )
                generated_files.append(chart_file)
        
        # 3. 性能趋势图表
        if 'all_results' in experiment_results:
            trend_file = self.generate_performance_trend_chart(
                experiment_results['all_results']
            )
            generated_files.append(trend_file)
        
        # 4. 相关性热图
        if 'all_results' in experiment_results:
            heatmap_file = self.generate_correlation_heatmap(
                experiment_results['all_results']
            )
            generated_files.append(heatmap_file)
        
        # 5. 统计摘要表格
        if 'statistical_results' in experiment_results:
            table_file = self.generate_statistical_summary_table(
                experiment_results['statistical_results']
            )
            generated_files.append(table_file)
        
        return generated_files
