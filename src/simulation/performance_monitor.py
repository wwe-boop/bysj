"""
性能监控器

监控和分析系统性能指标
"""

import time
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from collections import deque, defaultdict

from src.core.config import SystemConfig
from src.core.state import SystemState, PerformanceMetrics


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 监控参数
        self.monitoring_interval = 1.0  # 监控间隔（秒）
        self.history_length = 3600  # 保持1小时的历史数据
        
        # 性能指标历史
        self.throughput_history = deque(maxlen=self.history_length)
        self.latency_history = deque(maxlen=self.history_length)
        self.qoe_history = deque(maxlen=self.history_length)
        self.positioning_history = deque(maxlen=self.history_length)
        self.admission_rate_history = deque(maxlen=self.history_length)
        self.resource_utilization_history = deque(maxlen=self.history_length)
        
        # 时间戳历史
        self.timestamp_history = deque(maxlen=self.history_length)
        
        # 统计数据
        self.total_updates = 0
        self.alert_count = 0
        self.performance_alerts = []
        
        # 阈值设置
        self.thresholds = {
            'min_throughput': 10.0,  # Mbps
            'max_latency': 200.0,    # ms
            'min_qoe': 0.6,          # 0-1
            'min_positioning_score': 0.5,  # 0-1
            'min_admission_rate': 0.7,      # 0-1
            'max_resource_utilization': 0.9  # 0-1
        }
        
        self.logger.info("性能监控器初始化完成")
    
    def update(self, system_state: SystemState):
        """更新性能指标"""
        try:
            current_time = system_state.performance_metrics.time_step
            metrics = system_state.performance_metrics
            
            # 记录指标
            self.throughput_history.append(metrics.average_throughput)
            self.latency_history.append(metrics.average_latency)
            self.qoe_history.append(metrics.qoe_score)
            self.positioning_history.append(metrics.positioning_score)
            self.admission_rate_history.append(metrics.admission_rate)
            self.resource_utilization_history.append(metrics.resource_utilization)
            self.timestamp_history.append(current_time)
            
            self.total_updates += 1
            
            # 检查性能警报
            self._check_performance_alerts(metrics, current_time)
            
            # 定期日志
            if self.total_updates % 60 == 0:  # 每60次更新记录一次
                self._log_performance_summary()
                
        except Exception as e:
            self.logger.error(f"性能监控更新失败: {e}")
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics, current_time: float):
        """检查性能警报"""
        alerts = []
        
        # 吞吐量检查
        if metrics.average_throughput < self.thresholds['min_throughput']:
            alerts.append({
                'type': 'low_throughput',
                'message': f"吞吐量过低: {metrics.average_throughput:.1f} < {self.thresholds['min_throughput']}",
                'severity': 'warning',
                'time': current_time
            })
        
        # 延迟检查
        if metrics.average_latency > self.thresholds['max_latency']:
            alerts.append({
                'type': 'high_latency',
                'message': f"延迟过高: {metrics.average_latency:.1f} > {self.thresholds['max_latency']}",
                'severity': 'warning',
                'time': current_time
            })
        
        # QoE检查
        if metrics.qoe_score < self.thresholds['min_qoe']:
            alerts.append({
                'type': 'low_qoe',
                'message': f"QoE评分过低: {metrics.qoe_score:.2f} < {self.thresholds['min_qoe']}",
                'severity': 'critical',
                'time': current_time
            })
        
        # 定位质量检查
        if metrics.positioning_score < self.thresholds['min_positioning_score']:
            alerts.append({
                'type': 'low_positioning',
                'message': f"定位质量过低: {metrics.positioning_score:.2f} < {self.thresholds['min_positioning_score']}",
                'severity': 'warning',
                'time': current_time
            })
        
        # 准入成功率检查
        if metrics.admission_rate < self.thresholds['min_admission_rate']:
            alerts.append({
                'type': 'low_admission_rate',
                'message': f"准入成功率过低: {metrics.admission_rate:.2f} < {self.thresholds['min_admission_rate']}",
                'severity': 'critical',
                'time': current_time
            })
        
        # 资源利用率检查
        if metrics.resource_utilization > self.thresholds['max_resource_utilization']:
            alerts.append({
                'type': 'high_resource_utilization',
                'message': f"资源利用率过高: {metrics.resource_utilization:.2f} > {self.thresholds['max_resource_utilization']}",
                'severity': 'warning',
                'time': current_time
            })
        
        # 记录警报
        for alert in alerts:
            self.performance_alerts.append(alert)
            self.alert_count += 1
            
            if alert['severity'] == 'critical':
                self.logger.warning(f"性能警报: {alert['message']}")
            else:
                self.logger.info(f"性能提醒: {alert['message']}")
        
        # 保持警报历史大小
        if len(self.performance_alerts) > 1000:
            self.performance_alerts = self.performance_alerts[-500:]
    
    def _log_performance_summary(self):
        """记录性能摘要"""
        if not self.throughput_history:
            return
        
        # 计算最近的平均值
        recent_window = min(60, len(self.throughput_history))
        
        avg_throughput = np.mean(list(self.throughput_history)[-recent_window:])
        avg_latency = np.mean(list(self.latency_history)[-recent_window:])
        avg_qoe = np.mean(list(self.qoe_history)[-recent_window:])
        avg_positioning = np.mean(list(self.positioning_history)[-recent_window:])
        
        self.logger.info(f"性能摘要 (最近{recent_window}次): "
                        f"吞吐量={avg_throughput:.1f}Mbps, "
                        f"延迟={avg_latency:.1f}ms, "
                        f"QoE={avg_qoe:.2f}, "
                        f"定位={avg_positioning:.2f}")
    
    def get_current_metrics(self) -> Dict[str, float]:
        """获取当前性能指标"""
        if not self.throughput_history:
            return {}
        
        return {
            'throughput': self.throughput_history[-1],
            'latency': self.latency_history[-1],
            'qoe_score': self.qoe_history[-1],
            'positioning_score': self.positioning_history[-1],
            'admission_rate': self.admission_rate_history[-1],
            'resource_utilization': self.resource_utilization_history[-1]
        }
    
    def get_statistics(self, window_size: Optional[int] = None) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.throughput_history:
            return {
                'total_updates': 0,
                'alert_count': 0,
                'avg_metrics': {},
                'trend_analysis': {'overall': 'no_data'},
                'performance_grade': 'N/A'
            }
        
        # 确定窗口大小
        if window_size is None:
            window_size = len(self.throughput_history)
        else:
            window_size = min(window_size, len(self.throughput_history))
        
        # 获取最近的数据
        recent_throughput = list(self.throughput_history)[-window_size:]
        recent_latency = list(self.latency_history)[-window_size:]
        recent_qoe = list(self.qoe_history)[-window_size:]
        recent_positioning = list(self.positioning_history)[-window_size:]
        recent_admission = list(self.admission_rate_history)[-window_size:]
        recent_utilization = list(self.resource_utilization_history)[-window_size:]
        
        # 计算统计指标
        avg_metrics = {
            'throughput': np.mean(recent_throughput),
            'latency': np.mean(recent_latency),
            'qoe_score': np.mean(recent_qoe),
            'positioning_score': np.mean(recent_positioning),
            'admission_rate': np.mean(recent_admission),
            'resource_utilization': np.mean(recent_utilization)
        }
        
        # 趋势分析
        trend_analysis = self._analyze_trends(window_size)
        
        # 性能等级评估
        performance_grade = self._calculate_performance_grade(avg_metrics)
        
        return {
            'total_updates': self.total_updates,
            'alert_count': self.alert_count,
            'window_size': window_size,
            'avg_metrics': avg_metrics,
            'std_metrics': {
                'throughput': np.std(recent_throughput),
                'latency': np.std(recent_latency),
                'qoe_score': np.std(recent_qoe),
                'positioning_score': np.std(recent_positioning)
            },
            'min_max_metrics': {
                'throughput': (np.min(recent_throughput), np.max(recent_throughput)),
                'latency': (np.min(recent_latency), np.max(recent_latency)),
                'qoe_score': (np.min(recent_qoe), np.max(recent_qoe)),
                'positioning_score': (np.min(recent_positioning), np.max(recent_positioning))
            },
            'trend_analysis': trend_analysis,
            'performance_grade': performance_grade,
            'recent_alerts': self.performance_alerts[-10:] if self.performance_alerts else []
        }
    
    def _analyze_trends(self, window_size: int) -> Dict[str, str]:
        """分析性能趋势"""
        if window_size < 10:
            return {'overall': 'insufficient_data'}
        
        # 分析最近一半vs前一半的趋势
        half_window = window_size // 2
        
        def get_trend(data):
            if len(data) < 10:
                return 'stable'
            
            first_half = np.mean(data[:half_window])
            second_half = np.mean(data[half_window:])
            
            change_ratio = (second_half - first_half) / max(first_half, 0.001)
            
            if change_ratio > 0.1:
                return 'improving'
            elif change_ratio < -0.1:
                return 'degrading'
            else:
                return 'stable'
        
        recent_data = {
            'throughput': list(self.throughput_history)[-window_size:],
            'latency': list(self.latency_history)[-window_size:],
            'qoe_score': list(self.qoe_history)[-window_size:],
            'positioning_score': list(self.positioning_history)[-window_size:]
        }
        
        trends = {}
        for metric, data in recent_data.items():
            trends[metric] = get_trend(data)
        
        # 整体趋势评估
        improving_count = sum(1 for trend in trends.values() if trend == 'improving')
        degrading_count = sum(1 for trend in trends.values() if trend == 'degrading')
        
        if improving_count > degrading_count:
            trends['overall'] = 'improving'
        elif degrading_count > improving_count:
            trends['overall'] = 'degrading'
        else:
            trends['overall'] = 'stable'
        
        return trends
    
    def _calculate_performance_grade(self, metrics: Dict[str, float]) -> str:
        """计算性能等级"""
        score = 0
        total_weight = 0
        
        # 各指标权重和评分
        metric_weights = {
            'qoe_score': 0.3,
            'positioning_score': 0.2,
            'admission_rate': 0.2,
            'throughput': 0.15,
            'resource_utilization': 0.15
        }
        
        for metric, weight in metric_weights.items():
            if metric in metrics:
                value = metrics[metric]
                
                # 归一化评分
                if metric == 'throughput':
                    normalized_score = min(1.0, value / 50.0)  # 50Mbps为满分
                elif metric == 'resource_utilization':
                    normalized_score = 1.0 - value  # 利用率越低越好
                else:
                    normalized_score = value  # 其他指标直接使用
                
                score += normalized_score * weight
                total_weight += weight
        
        if total_weight > 0:
            final_score = score / total_weight
        else:
            final_score = 0.0
        
        # 等级划分
        if final_score >= 0.9:
            return 'A'
        elif final_score >= 0.8:
            return 'B'
        elif final_score >= 0.7:
            return 'C'
        elif final_score >= 0.6:
            return 'D'
        else:
            return 'F'
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        stats = self.get_statistics()
        
        return {
            'avg_throughput': stats['avg_metrics'].get('throughput', 0.0),
            'avg_latency': stats['avg_metrics'].get('latency', 0.0),
            'avg_qoe_score': stats['avg_metrics'].get('qoe_score', 0.0),
            'avg_positioning_score': stats['avg_metrics'].get('positioning_score', 0.0),
            'performance_grade': stats['performance_grade'],
            'overall_trend': stats['trend_analysis'].get('overall', 'unknown'),
            'total_alerts': self.alert_count
        }
    
    def reset(self):
        """重置监控器"""
        self.throughput_history.clear()
        self.latency_history.clear()
        self.qoe_history.clear()
        self.positioning_history.clear()
        self.admission_rate_history.clear()
        self.resource_utilization_history.clear()
        self.timestamp_history.clear()
        
        self.total_updates = 0
        self.alert_count = 0
        self.performance_alerts.clear()
        
        self.logger.info("性能监控器已重置")
    
    def export_data(self) -> Dict[str, Any]:
        """导出监控数据"""
        return {
            'timestamps': list(self.timestamp_history),
            'throughput': list(self.throughput_history),
            'latency': list(self.latency_history),
            'qoe_score': list(self.qoe_history),
            'positioning_score': list(self.positioning_history),
            'admission_rate': list(self.admission_rate_history),
            'resource_utilization': list(self.resource_utilization_history),
            'alerts': self.performance_alerts.copy(),
            'thresholds': self.thresholds.copy()
        }
