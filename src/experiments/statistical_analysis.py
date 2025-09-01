"""
统计分析模块
提供t检验、ANOVA、效应量计算等统计分析功能
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import ttest_ind, f_oneway, kruskal
from typing import Dict, List, Any, Tuple, Optional
import warnings
from dataclasses import dataclass

warnings.filterwarnings('ignore')


@dataclass
class StatisticalResult:
    """统计检验结果"""
    test_name: str
    statistic: float
    p_value: float
    effect_size: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    interpretation: str = ""
    significant: bool = False
    
    def __post_init__(self):
        self.significant = self.p_value < 0.05


class StatisticalAnalyzer:
    """统计分析器"""
    
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
        
    def analyze_experiment_results(self, results: List[Any]) -> Dict[str, Any]:
        """分析实验结果"""
        # 转换为DataFrame
        df = self._results_to_dataframe(results)
        
        analysis = {
            'descriptive_stats': self._descriptive_statistics(df),
            'normality_tests': self._test_normality(df),
            'comparison_tests': self._comparison_tests(df),
            'effect_sizes': self._calculate_effect_sizes(df),
            'confidence_intervals': self._calculate_confidence_intervals(df)
        }
        
        return analysis
    
    def compare_algorithms(self, results_by_algorithm: Dict[str, List[Any]]) -> Dict[str, StatisticalResult]:
        """比较不同算法的性能"""
        comparison_results = {}
        
        # 提取指标数据
        metrics_data = {}
        for algorithm, results in results_by_algorithm.items():
            df = self._results_to_dataframe(results)
            metrics_data[algorithm] = df
        
        # 获取所有指标
        all_metrics = set()
        for df in metrics_data.values():
            metric_columns = [col for col in df.columns if col.startswith('metric_')]
            all_metrics.update(metric_columns)
        
        # 对每个指标进行比较
        for metric in all_metrics:
            metric_name = metric.replace('metric_', '')
            
            # 收集各算法的数据
            algorithm_data = []
            algorithm_names = []
            
            for algorithm, df in metrics_data.items():
                if metric in df.columns:
                    data = df[metric].dropna().values
                    if len(data) > 0:
                        algorithm_data.append(data)
                        algorithm_names.append(algorithm)
            
            if len(algorithm_data) >= 2:
                # 执行ANOVA或Kruskal-Wallis检验
                if len(algorithm_data) == 2:
                    # 两组比较：t检验
                    result = self._two_sample_test(algorithm_data[0], algorithm_data[1])
                    result.test_name = f"t-test_{metric_name}"
                else:
                    # 多组比较：ANOVA
                    result = self._anova_test(algorithm_data, algorithm_names)
                    result.test_name = f"ANOVA_{metric_name}"
                
                comparison_results[metric_name] = result
        
        return comparison_results
    
    def ablation_analysis(self, baseline_results: List[Any], 
                         ablation_results: Dict[str, List[Any]]) -> Dict[str, Dict[str, StatisticalResult]]:
        """消融分析"""
        baseline_df = self._results_to_dataframe(baseline_results)
        ablation_analysis = {}
        
        for ablation_type, results in ablation_results.items():
            ablation_df = self._results_to_dataframe(results)
            ablation_analysis[ablation_type] = {}
            
            # 获取指标列
            metric_columns = [col for col in baseline_df.columns if col.startswith('metric_')]
            
            for metric_col in metric_columns:
                metric_name = metric_col.replace('metric_', '')
                
                if metric_col in baseline_df.columns and metric_col in ablation_df.columns:
                    baseline_data = baseline_df[metric_col].dropna().values
                    ablation_data = ablation_df[metric_col].dropna().values
                    
                    if len(baseline_data) > 0 and len(ablation_data) > 0:
                        result = self._two_sample_test(baseline_data, ablation_data)
                        result.test_name = f"ablation_{ablation_type}_{metric_name}"
                        
                        # 计算性能变化
                        baseline_mean = np.mean(baseline_data)
                        ablation_mean = np.mean(ablation_data)
                        performance_change = (ablation_mean - baseline_mean) / baseline_mean * 100
                        
                        result.interpretation = f"性能变化: {performance_change:.2f}%"
                        
                        ablation_analysis[ablation_type][metric_name] = result
        
        return ablation_analysis
    
    def _two_sample_test(self, group1: np.ndarray, group2: np.ndarray) -> StatisticalResult:
        """两样本检验"""
        # 检验正态性
        _, p_norm1 = stats.shapiro(group1) if len(group1) <= 5000 else (0, 0.05)
        _, p_norm2 = stats.shapiro(group2) if len(group2) <= 5000 else (0, 0.05)
        
        # 检验方差齐性
        _, p_var = stats.levene(group1, group2)
        
        if p_norm1 > 0.05 and p_norm2 > 0.05 and p_var > 0.05:
            # 使用t检验
            statistic, p_value = ttest_ind(group1, group2, equal_var=True)
            test_name = "Independent t-test"
            
            # 计算Cohen's d
            pooled_std = np.sqrt(((len(group1) - 1) * np.var(group1, ddof=1) + 
                                 (len(group2) - 1) * np.var(group2, ddof=1)) / 
                                (len(group1) + len(group2) - 2))
            effect_size = (np.mean(group1) - np.mean(group2)) / pooled_std
            
        elif p_norm1 > 0.05 and p_norm2 > 0.05:
            # 使用Welch's t检验
            statistic, p_value = ttest_ind(group1, group2, equal_var=False)
            test_name = "Welch's t-test"
            
            # 计算Cohen's d
            s1, s2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
            effect_size = (np.mean(group1) - np.mean(group2)) / np.sqrt((s1**2 + s2**2) / 2)
            
        else:
            # 使用Mann-Whitney U检验
            statistic, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
            test_name = "Mann-Whitney U test"
            
            # 计算效应量 (r)
            n1, n2 = len(group1), len(group2)
            z_score = stats.norm.ppf(p_value / 2)
            effect_size = abs(z_score) / np.sqrt(n1 + n2)
        
        # 计算置信区间
        diff_mean = np.mean(group1) - np.mean(group2)
        se_diff = np.sqrt(np.var(group1, ddof=1) / len(group1) + np.var(group2, ddof=1) / len(group2))
        df = len(group1) + len(group2) - 2
        t_critical = stats.t.ppf(1 - self.alpha / 2, df)
        ci_lower = diff_mean - t_critical * se_diff
        ci_upper = diff_mean + t_critical * se_diff
        
        # 解释结果
        if p_value < 0.001:
            significance = "highly significant (p < 0.001)"
        elif p_value < 0.01:
            significance = "very significant (p < 0.01)"
        elif p_value < 0.05:
            significance = "significant (p < 0.05)"
        else:
            significance = "not significant (p >= 0.05)"
        
        interpretation = f"{test_name}: {significance}"
        
        return StatisticalResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=(ci_lower, ci_upper),
            interpretation=interpretation
        )
    
    def _anova_test(self, groups: List[np.ndarray], group_names: List[str]) -> StatisticalResult:
        """方差分析"""
        # 检验正态性
        normal_groups = []
        for group in groups:
            if len(group) > 3:
                _, p_norm = stats.shapiro(group) if len(group) <= 5000 else (0, 0.05)
                normal_groups.append(p_norm > 0.05)
            else:
                normal_groups.append(False)
        
        # 检验方差齐性
        _, p_var = stats.levene(*groups)
        
        if all(normal_groups) and p_var > 0.05:
            # 使用ANOVA
            statistic, p_value = f_oneway(*groups)
            test_name = "One-way ANOVA"
            
            # 计算eta squared (效应量)
            ss_between = sum(len(group) * (np.mean(group) - np.mean(np.concatenate(groups)))**2 
                           for group in groups)
            ss_total = sum((x - np.mean(np.concatenate(groups)))**2 for group in groups for x in group)
            effect_size = ss_between / ss_total if ss_total > 0 else 0
            
        else:
            # 使用Kruskal-Wallis检验
            statistic, p_value = kruskal(*groups)
            test_name = "Kruskal-Wallis test"
            
            # 计算效应量 (epsilon squared)
            n_total = sum(len(group) for group in groups)
            effect_size = (statistic - len(groups) + 1) / (n_total - len(groups))
        
        # 解释结果
        if p_value < 0.001:
            significance = "highly significant (p < 0.001)"
        elif p_value < 0.01:
            significance = "very significant (p < 0.01)"
        elif p_value < 0.05:
            significance = "significant (p < 0.05)"
        else:
            significance = "not significant (p >= 0.05)"
        
        interpretation = f"{test_name}: {significance}"
        
        return StatisticalResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            effect_size=effect_size,
            interpretation=interpretation
        )
    
    def _descriptive_statistics(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """描述性统计"""
        metric_columns = [col for col in df.columns if col.startswith('metric_')]
        
        descriptive_stats = {}
        for col in metric_columns:
            metric_name = col.replace('metric_', '')
            data = df[col].dropna()
            
            if len(data) > 0:
                descriptive_stats[metric_name] = {
                    'count': len(data),
                    'mean': float(np.mean(data)),
                    'std': float(np.std(data, ddof=1)),
                    'min': float(np.min(data)),
                    'max': float(np.max(data)),
                    'median': float(np.median(data)),
                    'q25': float(np.percentile(data, 25)),
                    'q75': float(np.percentile(data, 75)),
                    'skewness': float(stats.skew(data)),
                    'kurtosis': float(stats.kurtosis(data))
                }
        
        return descriptive_stats
    
    def _test_normality(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """正态性检验"""
        metric_columns = [col for col in df.columns if col.startswith('metric_')]
        
        normality_tests = {}
        for col in metric_columns:
            metric_name = col.replace('metric_', '')
            data = df[col].dropna()
            
            if len(data) > 3:
                # Shapiro-Wilk检验
                if len(data) <= 5000:
                    shapiro_stat, shapiro_p = stats.shapiro(data)
                else:
                    shapiro_stat, shapiro_p = np.nan, np.nan
                
                # Kolmogorov-Smirnov检验
                ks_stat, ks_p = stats.kstest(data, 'norm', args=(np.mean(data), np.std(data, ddof=1)))
                
                normality_tests[metric_name] = {
                    'shapiro_statistic': float(shapiro_stat) if not np.isnan(shapiro_stat) else None,
                    'shapiro_p_value': float(shapiro_p) if not np.isnan(shapiro_p) else None,
                    'ks_statistic': float(ks_stat),
                    'ks_p_value': float(ks_p),
                    'is_normal': bool(shapiro_p > 0.05 if not np.isnan(shapiro_p) else ks_p > 0.05)
                }
        
        return normality_tests
    
    def _comparison_tests(self, df: pd.DataFrame) -> Dict[str, Any]:
        """比较检验"""
        # 这里可以根据实验设计进行组间比较
        # 暂时返回空字典，具体实现取决于实验设计
        return {}
    
    def _calculate_effect_sizes(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算效应量"""
        # 这里可以计算各种效应量
        # 暂时返回空字典，具体实现取决于比较需求
        return {}
    
    def _calculate_confidence_intervals(self, df: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
        """计算置信区间"""
        metric_columns = [col for col in df.columns if col.startswith('metric_')]
        
        confidence_intervals = {}
        for col in metric_columns:
            metric_name = col.replace('metric_', '')
            data = df[col].dropna()
            
            if len(data) > 1:
                mean = np.mean(data)
                se = stats.sem(data)
                ci = stats.t.interval(1 - self.alpha, len(data) - 1, loc=mean, scale=se)
                confidence_intervals[metric_name] = (float(ci[0]), float(ci[1]))
        
        return confidence_intervals
    
    def _results_to_dataframe(self, results: List[Any]) -> pd.DataFrame:
        """将结果转换为DataFrame"""
        data = []
        for result in results:
            if hasattr(result, '__dict__'):
                row = result.__dict__.copy()
            else:
                row = result
            
            # 展平嵌套字典
            flat_row = {}
            for key, value in row.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_row[f"{key}_{sub_key}"] = sub_value
                else:
                    flat_row[key] = value
            
            data.append(flat_row)
        
        return pd.DataFrame(data)
    
    def generate_statistical_report(self, analysis_results: Dict[str, Any]) -> str:
        """生成统计分析报告"""
        report = []
        report.append("# 统计分析报告\n")
        
        # 描述性统计
        if 'descriptive_stats' in analysis_results:
            report.append("## 描述性统计\n")
            for metric, stats in analysis_results['descriptive_stats'].items():
                report.append(f"### {metric}")
                report.append(f"- 样本数: {stats['count']}")
                report.append(f"- 均值: {stats['mean']:.4f}")
                report.append(f"- 标准差: {stats['std']:.4f}")
                report.append(f"- 中位数: {stats['median']:.4f}")
                report.append(f"- 范围: [{stats['min']:.4f}, {stats['max']:.4f}]")
                report.append("")
        
        # 正态性检验
        if 'normality_tests' in analysis_results:
            report.append("## 正态性检验\n")
            for metric, test_results in analysis_results['normality_tests'].items():
                report.append(f"### {metric}")
                if test_results['shapiro_p_value'] is not None:
                    report.append(f"- Shapiro-Wilk检验: p = {test_results['shapiro_p_value']:.4f}")
                report.append(f"- Kolmogorov-Smirnov检验: p = {test_results['ks_p_value']:.4f}")
                report.append(f"- 正态分布: {'是' if test_results['is_normal'] else '否'}")
                report.append("")
        
        return "\n".join(report)
