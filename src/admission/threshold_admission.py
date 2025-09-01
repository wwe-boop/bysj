"""
基于阈值的准入控制

实现简单的基于阈值的准入控制策略
"""

import time
from typing import Dict, List, Any, Optional
import numpy as np

from src.admission.admission_controller import AdmissionController, AdmissionResult, AdmissionDecision
from src.core.state import NetworkState, UserRequest


class ThresholdAdmissionController(AdmissionController):
    """基于阈值的准入控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 阈值参数
        self.max_users_per_satellite = config.get('max_users_per_satellite', 100)
        self.min_signal_strength_dbm = config.get('min_signal_strength_dbm', -120.0)
        self.max_latency_threshold_ms = config.get('max_latency_threshold_ms', 50.0)
        self.min_bandwidth_threshold_mbps = config.get('min_bandwidth_threshold_mbps', 1.0)
        
        # 负载阈值
        self.max_satellite_load = 0.8  # 最大卫星负载
        self.max_link_utilization = 0.9  # 最大链路利用率
        
        self.logger.info(f"初始化阈值准入控制器: "
                        f"max_users={self.max_users_per_satellite}, "
                        f"min_signal={self.min_signal_strength_dbm}dBm, "
                        f"max_latency={self.max_latency_threshold_ms}ms")
    
    def make_admission_decision(self, 
                              user_request: UserRequest,
                              network_state: NetworkState,
                              positioning_metrics: Optional[Dict[str, Any]] = None) -> AdmissionResult:
        """基于阈值做出准入决策"""
        start_time = time.time()
        
        try:
            # 1. 检查基本QoS要求
            if not self._check_basic_qos(user_request):
                result = AdmissionResult(
                    decision=AdmissionDecision.REJECT,
                    reason="QoS要求超出系统能力"
                )
                self._finalize_decision(result, start_time)
                return result
            
            # 2. 找到候选卫星
            candidate_satellites = self._find_candidate_satellites(
                user_request, network_state, positioning_metrics
            )
            
            if not candidate_satellites:
                result = AdmissionResult(
                    decision=AdmissionDecision.REJECT,
                    reason="没有可用的卫星"
                )
                self._finalize_decision(result, start_time)
                return result
            
            # 3. 选择最佳卫星
            best_satellite = self._select_best_satellite(
                candidate_satellites, user_request, network_state
            )
            
            # 4. 检查资源可用性
            available_bandwidth = self._check_bandwidth_availability(
                best_satellite, user_request, network_state
            )
            
            if available_bandwidth >= user_request.bandwidth_mbps:
                # 完全接受
                result = AdmissionResult(
                    decision=AdmissionDecision.ACCEPT,
                    allocated_bandwidth=user_request.bandwidth_mbps,
                    allocated_satellite=best_satellite,
                    confidence=0.9,
                    reason="满足所有阈值条件"
                )
            elif available_bandwidth >= self.min_bandwidth_threshold_mbps:
                # 降级接受
                result = AdmissionResult(
                    decision=AdmissionDecision.DEGRADED_ACCEPT,
                    allocated_bandwidth=available_bandwidth,
                    allocated_satellite=best_satellite,
                    confidence=0.7,
                    reason=f"带宽降级至{available_bandwidth:.1f}Mbps"
                )
            else:
                # 拒绝
                result = AdmissionResult(
                    decision=AdmissionDecision.REJECT,
                    reason="可用带宽不足"
                )
            
            self._finalize_decision(result, start_time)
            return result
            
        except Exception as e:
            self.logger.error(f"准入决策失败: {e}")
            result = AdmissionResult(
                decision=AdmissionDecision.REJECT,
                reason=f"系统错误: {str(e)}"
            )
            self._finalize_decision(result, start_time)
            return result
    
    def _check_basic_qos(self, user_request: UserRequest) -> bool:
        """检查基本QoS要求"""
        # 检查带宽要求是否合理
        if user_request.bandwidth_mbps > 100.0:  # 假设最大带宽100Mbps
            return False
        
        # 检查延迟要求是否合理
        if user_request.max_latency_ms < 10.0:  # 最小延迟10ms
            return False
        
        return True
    
    def _find_candidate_satellites(self, 
                                 user_request: UserRequest,
                                 network_state: NetworkState,
                                 positioning_metrics: Optional[Dict[str, Any]]) -> List[int]:
        """找到候选卫星"""
        candidates = []
        
        # 如果有定位信息，优先考虑可见卫星
        visible_satellites = None
        if positioning_metrics and 'visible_satellites' in positioning_metrics:
            visible_satellites = {sat['id']: sat for sat in positioning_metrics['visible_satellites']}
        
        for satellite in network_state.satellites:
            sat_id = satellite['id']
            
            # 检查卫星是否可见
            if visible_satellites is not None:
                if sat_id not in visible_satellites:
                    continue
                
                # 检查信号强度（简化计算）
                sat_info = visible_satellites[sat_id]
                if 'signal_strength_dbm' in sat_info:
                    if sat_info['signal_strength_dbm'] < self.min_signal_strength_dbm:
                        continue
            
            # 检查卫星负载
            satellite_load = self._calculate_satellite_load(sat_id, network_state)
            if satellite_load > self.max_satellite_load:
                continue
            
            # 检查链路质量
            link_quality = self._calculate_link_quality(sat_id, network_state)
            if link_quality < 0.3:  # 最小链路质量阈值
                continue
            
            candidates.append(sat_id)
        
        return candidates
    
    def _select_best_satellite(self, 
                             candidates: List[int],
                             user_request: UserRequest,
                             network_state: NetworkState) -> int:
        """从候选卫星中选择最佳的"""
        best_satellite = candidates[0]
        best_score = -1.0
        
        for sat_id in candidates:
            # 计算综合评分
            load = self._calculate_satellite_load(sat_id, network_state)
            link_quality = self._calculate_link_quality(sat_id, network_state)
            
            # 评分：负载越低越好，链路质量越高越好
            score = (1.0 - load) * 0.6 + link_quality * 0.4
            
            if score > best_score:
                best_score = score
                best_satellite = sat_id
        
        return best_satellite
    
    def _check_bandwidth_availability(self, 
                                    satellite_id: int,
                                    user_request: UserRequest,
                                    network_state: NetworkState) -> float:
        """检查带宽可用性"""
        # 简化的带宽计算
        # 假设每个卫星有固定的总带宽容量
        total_capacity = 100.0  # 100 Mbps总容量
        
        # 计算当前使用的带宽（基于队列长度的简化估算）
        queue_length = network_state.queue_lengths.get(satellite_id, 0.0)
        used_bandwidth = queue_length * 0.1  # 简化转换
        
        available_bandwidth = max(0.0, total_capacity - used_bandwidth)
        return available_bandwidth
    
    def _finalize_decision(self, result: AdmissionResult, start_time: float):
        """完成决策处理"""
        decision_time = time.time() - start_time
        self.decision_times.append(decision_time)
        self.update_statistics(result)
        
        self.logger.debug(f"准入决策: {result.decision.value}, "
                         f"卫星: {result.allocated_satellite}, "
                         f"带宽: {result.allocated_bandwidth:.1f}Mbps, "
                         f"耗时: {decision_time*1000:.1f}ms")
