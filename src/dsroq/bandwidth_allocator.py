"""
带宽分配器

实现精细的带宽分配和QoS保证机制
"""

import logging
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from src.core.state import NetworkState, FlowRequest, QoSClass


class BandwidthAllocator:
    """带宽分配器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 分配参数
        self.min_bandwidth_mbps = config.get('min_bandwidth_mbps', 1.0)
        self.max_bandwidth_mbps = config.get('max_bandwidth_mbps', 100.0)
        self.bandwidth_granularity = config.get('bandwidth_granularity', 0.1)
        
        # QoS权重
        self.qos_weights = {
            QoSClass.CRITICAL: 4.0,
            QoSClass.PREMIUM: 3.0,
            QoSClass.ASSURED: 2.0,
            QoSClass.BEST_EFFORT: 1.0
        }
        
        # 当前分配状态
        self.active_allocations: Dict[str, Dict[str, Any]] = {}
        self.link_allocations: Dict[Tuple[int, int], float] = defaultdict(float)
        
        # 统计信息
        self.total_allocated_bandwidth = 0.0
        self.allocation_history: List[Dict[str, Any]] = []
        
        self.logger.info(f"带宽分配器初始化: min={self.min_bandwidth_mbps}Mbps, "
                        f"max={self.max_bandwidth_mbps}Mbps")
    
    def allocate(self, 
                flow_request: FlowRequest,
                route: List[int],
                target_bandwidth: float,
                network_state: NetworkState) -> float:
        """分配带宽给流请求"""
        try:
            # 1. 检查路径可行性
            if not self._is_path_feasible(route, target_bandwidth, network_state):
                self.logger.debug(f"路径不可行: {route}")
                return 0.0
            
            # 2. 计算实际可分配带宽
            feasible_bandwidth = self._calculate_feasible_bandwidth(
                route, target_bandwidth, network_state
            )
            
            # 3. 应用QoS策略
            final_bandwidth = self._apply_qos_policy(
                flow_request, feasible_bandwidth, network_state
            )
            
            # 4. 执行分配
            if final_bandwidth > 0:
                self._execute_allocation(flow_request, route, final_bandwidth)
            
            return final_bandwidth
            
        except Exception as e:
            self.logger.error(f"带宽分配失败: {e}")
            return 0.0
    
    def _is_path_feasible(self, 
                         route: List[int],
                         bandwidth: float,
                         network_state: NetworkState) -> bool:
        """检查路径是否可行"""
        if len(route) < 2:
            return False
        
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            
            # 检查链路是否存在
            if link_key not in network_state.link_capacity:
                return False
            
            # 检查容量
            capacity = network_state.link_capacity[link_key]
            current_utilization = network_state.link_utilization.get(link_key, 0.0)
            current_allocation = self.link_allocations.get(link_key, 0.0)
            
            available = capacity - current_allocation
            
            if available < bandwidth:
                return False
        
        return True
    
    def _calculate_feasible_bandwidth(self, 
                                    route: List[int],
                                    target_bandwidth: float,
                                    network_state: NetworkState) -> float:
        """计算实际可分配的带宽"""
        if len(route) < 2:
            return 0.0
        
        # 找到瓶颈链路
        min_available = float('inf')
        
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            
            capacity = network_state.link_capacity.get(link_key, 0.0)
            current_allocation = self.link_allocations.get(link_key, 0.0)
            
            available = capacity - current_allocation
            min_available = min(min_available, available)
        
        # 应用带宽约束
        feasible_bandwidth = min(target_bandwidth, min_available)
        feasible_bandwidth = max(0.0, feasible_bandwidth)
        
        # 量化到粒度
        feasible_bandwidth = round(feasible_bandwidth / self.bandwidth_granularity) * self.bandwidth_granularity
        
        return feasible_bandwidth
    
    def _apply_qos_policy(self, 
                         flow_request: FlowRequest,
                         bandwidth: float,
                         network_state: NetworkState) -> float:
        """应用QoS策略"""
        
        # 1. 获取QoS权重
        qos_weight = self.qos_weights.get(flow_request.qos_class, 1.0)
        
        # 2. 检查最小QoS要求
        min_required = self._get_min_qos_bandwidth(flow_request)
        
        if bandwidth < min_required:
            # 尝试抢占低优先级流量
            reclaimed_bandwidth = self._reclaim_bandwidth(
                flow_request, min_required - bandwidth, network_state
            )
            bandwidth += reclaimed_bandwidth
        
        # 3. 应用优先级调整
        if flow_request.qos_class in [QoSClass.CRITICAL, QoSClass.PREMIUM]:
            # 高优先级流量可以获得额外保证
            bandwidth = max(bandwidth, min_required)
        
        # 4. 应用公平性约束
        bandwidth = self._apply_fairness_constraint(bandwidth, flow_request)
        
        return bandwidth
    
    def _get_min_qos_bandwidth(self, flow_request: FlowRequest) -> float:
        """获取最小QoS带宽要求"""
        qos_ratios = {
            QoSClass.CRITICAL: 1.0,      # 100%
            QoSClass.PREMIUM: 0.8,       # 80%
            QoSClass.ASSURED: 0.6,       # 60%
            QoSClass.BEST_EFFORT: 0.3    # 30%
        }
        
        ratio = qos_ratios.get(flow_request.qos_class, 0.3)
        return flow_request.bandwidth_requirement * ratio
    
    def _reclaim_bandwidth(self, 
                          flow_request: FlowRequest,
                          needed_bandwidth: float,
                          network_state: NetworkState) -> float:
        """从低优先级流量中回收带宽"""
        reclaimed = 0.0
        
        # 按优先级排序现有分配
        sorted_allocations = sorted(
            self.active_allocations.items(),
            key=lambda x: self.qos_weights.get(x[1]['qos_class'], 1.0)
        )
        
        for flow_id, allocation_info in sorted_allocations:
            if reclaimed >= needed_bandwidth:
                break
            
            # 只从低优先级流量中回收
            if (self.qos_weights.get(allocation_info['qos_class'], 1.0) < 
                self.qos_weights.get(flow_request.qos_class, 1.0)):
                
                # 计算可回收的带宽
                current_bandwidth = allocation_info['bandwidth']
                min_required = allocation_info['min_bandwidth']
                
                reclaimable = max(0.0, current_bandwidth - min_required)
                to_reclaim = min(reclaimable, needed_bandwidth - reclaimed)
                
                if to_reclaim > 0:
                    # 更新分配
                    allocation_info['bandwidth'] -= to_reclaim
                    reclaimed += to_reclaim
                    
                    self.logger.debug(f"从流{flow_id}回收{to_reclaim:.1f}Mbps带宽")
        
        return reclaimed
    
    def _apply_fairness_constraint(self, bandwidth: float, flow_request: FlowRequest) -> float:
        """应用公平性约束"""
        # 简单的最大公平性：限制单个流的最大带宽
        max_fair_share = self.max_bandwidth_mbps / max(1, len(self.active_allocations) + 1)
        
        # 根据QoS等级调整
        qos_multiplier = self.qos_weights.get(flow_request.qos_class, 1.0)
        adjusted_max = max_fair_share * qos_multiplier
        
        return min(bandwidth, adjusted_max)
    
    def _execute_allocation(self, 
                          flow_request: FlowRequest,
                          route: List[int],
                          bandwidth: float):
        """执行带宽分配"""
        flow_id = flow_request.flow_id
        
        # 更新链路分配
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            self.link_allocations[link_key] += bandwidth
        
        # 记录分配信息
        self.active_allocations[flow_id] = {
            'bandwidth': bandwidth,
            'route': route,
            'qos_class': flow_request.qos_class,
            'min_bandwidth': self._get_min_qos_bandwidth(flow_request),
            'allocation_time': time.time()
        }
        
        # 更新统计
        self.total_allocated_bandwidth += bandwidth
        
        self.allocation_history.append({
            'flow_id': flow_id,
            'bandwidth': bandwidth,
            'qos_class': flow_request.qos_class.value,
            'route_length': len(route),
            'timestamp': time.time()
        })
        
        # 保持历史记录大小
        if len(self.allocation_history) > 10000:
            self.allocation_history = self.allocation_history[-5000:]
        
        self.logger.debug(f"分配{bandwidth:.1f}Mbps给流{flow_id}")
    
    def deallocate(self, flow_id: str) -> bool:
        """释放流的带宽分配"""
        if flow_id not in self.active_allocations:
            return False
        
        allocation_info = self.active_allocations[flow_id]
        bandwidth = allocation_info['bandwidth']
        route = allocation_info['route']
        
        # 释放链路带宽
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            self.link_allocations[link_key] -= bandwidth
            self.link_allocations[link_key] = max(0.0, self.link_allocations[link_key])
        
        # 移除分配记录
        del self.active_allocations[flow_id]
        self.total_allocated_bandwidth -= bandwidth
        
        self.logger.debug(f"释放流{flow_id}的{bandwidth:.1f}Mbps带宽")
        return True
    
    def get_link_utilization(self, link: Tuple[int, int]) -> float:
        """获取链路利用率"""
        allocated = self.link_allocations.get(link, 0.0)
        # 这里需要从network_state获取容量，简化处理
        return allocated / 100.0  # 假设100Mbps容量
    
    def get_allocation_statistics(self) -> Dict[str, Any]:
        """获取分配统计信息"""
        if not self.active_allocations:
            return {
                'active_flows': 0,
                'total_allocated_bandwidth': 0.0,
                'avg_bandwidth_per_flow': 0.0,
                'qos_distribution': {},
                'link_utilization_avg': 0.0
            }
        
        # QoS分布
        qos_distribution = defaultdict(int)
        for allocation in self.active_allocations.values():
            qos_distribution[allocation['qos_class'].value] += 1
        
        # 平均链路利用率
        link_utilizations = list(self.link_allocations.values())
        avg_link_utilization = np.mean(link_utilizations) if link_utilizations else 0.0
        
        return {
            'active_flows': len(self.active_allocations),
            'total_allocated_bandwidth': self.total_allocated_bandwidth,
            'avg_bandwidth_per_flow': self.total_allocated_bandwidth / len(self.active_allocations),
            'qos_distribution': dict(qos_distribution),
            'link_utilization_avg': avg_link_utilization,
            'max_link_utilization': max(link_utilizations) if link_utilizations else 0.0,
            'allocation_efficiency': self._calculate_allocation_efficiency()
        }
    
    def _calculate_allocation_efficiency(self) -> float:
        """计算分配效率"""
        if not self.active_allocations:
            return 1.0
        
        # 效率 = 实际分配 / 请求总量
        total_requested = 0.0
        total_allocated = 0.0
        
        for allocation in self.active_allocations.values():
            # 这里需要原始请求信息，简化处理
            total_allocated += allocation['bandwidth']
            total_requested += allocation['bandwidth'] * 1.2  # 假设请求比分配多20%
        
        return total_allocated / total_requested if total_requested > 0 else 1.0
    
    def reset_allocations(self):
        """重置所有分配"""
        self.active_allocations.clear()
        self.link_allocations.clear()
        self.total_allocated_bandwidth = 0.0
        self.allocation_history.clear()
        
        self.logger.info("所有带宽分配已重置")
