"""
准入控制器基类

定义了准入控制的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import numpy as np

from src.core.interfaces import AdmissionInterface
from src.core.state import NetworkState, UserRequest


class AdmissionDecision(Enum):
    """准入决策类型"""
    ACCEPT = "accept"                    # 接受
    REJECT = "reject"                    # 拒绝
    DEGRADED_ACCEPT = "degraded_accept"  # 降级接受
    DELAYED_ACCEPT = "delayed_accept"    # 延迟接受
    PARTIAL_ACCEPT = "partial_accept"    # 部分接受


@dataclass
class AdmissionResult:
    """准入控制结果"""
    decision: AdmissionDecision
    confidence: float = 1.0              # 决策置信度 [0, 1]
    allocated_bandwidth: float = 0.0     # 分配的带宽 (Mbps)
    allocated_satellite: Optional[int] = None  # 分配的卫星ID
    delay_seconds: float = 0.0           # 延迟时间 (秒)
    reason: str = ""                     # 决策原因
    qos_metrics: Dict[str, float] = None # QoS指标
    positioning_metrics: Dict[str, float] = None  # 定位指标


class AdmissionController(AdmissionInterface, ABC):
    """准入控制器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 统计信息
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.degraded_requests = 0
        self.delayed_requests = 0
        self.partial_requests = 0
        
        # 性能指标
        self.decision_times = []
        self.qos_violations = 0
        
    @abstractmethod
    def make_admission_decision(self, 
                              user_request: UserRequest,
                              network_state: NetworkState,
                              positioning_metrics: Optional[Dict[str, Any]] = None) -> AdmissionResult:
        """
        做出准入决策
        
        Args:
            user_request: 用户请求
            network_state: 当前网络状态
            positioning_metrics: 定位相关指标
            
        Returns:
            AdmissionResult: 准入决策结果
        """
        pass
    
    def update_statistics(self, result: AdmissionResult):
        """更新统计信息"""
        self.total_requests += 1
        
        if result.decision == AdmissionDecision.ACCEPT:
            self.accepted_requests += 1
        elif result.decision == AdmissionDecision.REJECT:
            self.rejected_requests += 1
        elif result.decision == AdmissionDecision.DEGRADED_ACCEPT:
            self.degraded_requests += 1
        elif result.decision == AdmissionDecision.DELAYED_ACCEPT:
            self.delayed_requests += 1
        elif result.decision == AdmissionDecision.PARTIAL_ACCEPT:
            self.partial_requests += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.total_requests == 0:
            return {
                'total_requests': 0,
                'acceptance_rate': 0.0,
                'rejection_rate': 0.0,
                'degraded_rate': 0.0,
                'delayed_rate': 0.0,
                'partial_rate': 0.0,
                'avg_decision_time': 0.0,
                'qos_violation_rate': 0.0
            }
        
        return {
            'total_requests': self.total_requests,
            'acceptance_rate': self.accepted_requests / self.total_requests,
            'rejection_rate': self.rejected_requests / self.total_requests,
            'degraded_rate': self.degraded_requests / self.total_requests,
            'delayed_rate': self.delayed_requests / self.total_requests,
            'partial_rate': self.partial_requests / self.total_requests,
            'avg_decision_time': np.mean(self.decision_times) if self.decision_times else 0.0,
            'qos_violation_rate': self.qos_violations / self.total_requests
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.degraded_requests = 0
        self.delayed_requests = 0
        self.partial_requests = 0
        self.decision_times = []
        self.qos_violations = 0
    
    def _calculate_satellite_load(self, satellite_id: int, network_state: NetworkState) -> float:
        """计算卫星负载"""
        # 简化的负载计算：基于队列长度
        queue_length = network_state.queue_lengths.get(satellite_id, 0.0)
        max_queue_length = 100.0  # 假设最大队列长度
        return min(1.0, queue_length / max_queue_length)
    
    def _calculate_link_quality(self, satellite_id: int, network_state: NetworkState) -> float:
        """计算链路质量"""
        # 简化的链路质量计算：基于链路利用率
        total_utilization = 0.0
        link_count = 0
        
        for (src, dst), utilization in network_state.link_utilization.items():
            if src == satellite_id or dst == satellite_id:
                total_utilization += utilization
                link_count += 1
        
        if link_count == 0:
            return 1.0
        
        avg_utilization = total_utilization / link_count
        return 1.0 - avg_utilization  # 利用率越低，质量越高
    
    def _find_best_satellite(self, 
                           user_request: UserRequest,
                           network_state: NetworkState,
                           positioning_metrics: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """找到最佳卫星"""
        best_satellite = None
        best_score = -1.0
        
        # 如果有定位信息，优先考虑可见卫星
        visible_satellites = None
        if positioning_metrics and 'visible_satellites' in positioning_metrics:
            visible_satellites = set(sat['id'] for sat in positioning_metrics['visible_satellites'])
        
        for satellite in network_state.satellites:
            sat_id = satellite['id']
            
            # 如果有可见卫星信息，只考虑可见卫星
            if visible_satellites is not None and sat_id not in visible_satellites:
                continue
            
            # 计算卫星评分
            load = self._calculate_satellite_load(sat_id, network_state)
            link_quality = self._calculate_link_quality(sat_id, network_state)
            
            # 综合评分：负载越低越好，链路质量越高越好
            score = (1.0 - load) * 0.6 + link_quality * 0.4
            
            if score > best_score:
                best_score = score
                best_satellite = sat_id
        
        return best_satellite
