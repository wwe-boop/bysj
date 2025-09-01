"""
李雅普诺夫优化器

实现基于李雅普诺夫稳定性理论的队列管理和资源分配优化
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from src.core.state import NetworkState, FlowRequest


class LyapunovOptimizer:
    """李雅普诺夫优化器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 李雅普诺夫参数
        self.lyapunov_weight = config.get('lyapunov_weight', 1.0)
        self.queue_weight = config.get('queue_weight', 1.0)
        self.utility_weight = config.get('utility_weight', 1.0)
        
        # 队列状态
        self.queue_backlogs: Dict[int, float] = defaultdict(float)
        self.virtual_queues: Dict[str, float] = defaultdict(float)  # 用于QoS约束
        
        # 历史统计
        self.queue_history: Dict[int, List[float]] = defaultdict(list)
        self.utility_history: List[float] = []
        
        # 优化参数
        self.max_queue_length = config.get('max_queue_length', 1000.0)
        self.convergence_threshold = config.get('convergence_threshold', 0.01)
        
        self.logger.info(f"李雅普诺夫优化器初始化: weight={self.lyapunov_weight}")
    
    def optimize_allocation(self, 
                          flow_request: FlowRequest,
                          route: List[int],
                          network_state: NetworkState,
                          available_bandwidth: float) -> float:
        """使用李雅普诺夫优化分配带宽"""
        try:
            # 1. 更新队列状态
            self._update_queue_states(network_state)
            
            # 2. 计算李雅普诺夫漂移加惩罚
            optimal_allocation = self._solve_lyapunov_optimization(
                flow_request, route, available_bandwidth, network_state
            )
            
            # 3. 应用约束
            constrained_allocation = self._apply_constraints(
                optimal_allocation, flow_request, route, network_state
            )
            
            # 4. 更新虚拟队列
            self._update_virtual_queues(flow_request, constrained_allocation)
            
            return constrained_allocation
            
        except Exception as e:
            self.logger.error(f"李雅普诺夫优化失败: {e}")
            # 回退到简单分配
            return min(available_bandwidth, flow_request.bandwidth_requirement)
    
    def _solve_lyapunov_optimization(self, 
                                   flow_request: FlowRequest,
                                   route: List[int],
                                   available_bandwidth: float,
                                   network_state: NetworkState) -> float:
        """求解李雅普诺夫优化问题"""
        
        # 目标：最大化 Utility - V * Queue_Penalty
        # 其中 V 是李雅普诺夫权重
        
        # 1. 计算效用函数
        def utility_function(bandwidth: float) -> float:
            if bandwidth <= 0:
                return 0.0
            
            # 对数效用函数（凹函数，体现边际效用递减）
            base_utility = np.log(1 + bandwidth)
            
            # QoS奖励
            qos_bonus = 0.0
            if bandwidth >= flow_request.bandwidth_requirement:
                qos_bonus = 2.0  # 满足QoS要求的奖励
            
            # 优先级权重
            priority_weight = flow_request.priority / 10.0
            
            return (base_utility + qos_bonus) * priority_weight
        
        # 2. 计算队列惩罚
        def queue_penalty(bandwidth: float) -> float:
            penalty = 0.0
            
            for i, satellite_id in enumerate(route):
                # 当前队列长度
                current_queue = self.queue_backlogs.get(satellite_id, 0.0)
                
                # 预期队列增长（简化模型）
                queue_increase = bandwidth * 0.1  # 假设处理率
                
                # 李雅普诺夫惩罚项
                penalty += current_queue * queue_increase
            
            return penalty * self.lyapunov_weight
        
        # 3. 网格搜索找到最优分配
        best_allocation = 0.0
        best_objective = float('-inf')
        
        # 搜索范围：0 到 available_bandwidth
        search_points = np.linspace(0, available_bandwidth, 100)
        
        for bandwidth in search_points:
            utility = utility_function(bandwidth)
            penalty = queue_penalty(bandwidth)
            objective = utility - penalty
            
            if objective > best_objective:
                best_objective = objective
                best_allocation = bandwidth
        
        return best_allocation
    
    def _apply_constraints(self, 
                         allocation: float,
                         flow_request: FlowRequest,
                         route: List[int],
                         network_state: NetworkState) -> float:
        """应用各种约束条件"""
        
        # 1. 容量约束
        path_capacity = self._get_path_capacity(route, network_state)
        allocation = min(allocation, path_capacity)
        
        # 2. QoS约束
        min_required = flow_request.bandwidth_requirement * 0.5  # 最低50%
        allocation = max(allocation, min_required) if allocation > 0 else 0.0
        
        # 3. 队列稳定性约束
        for satellite_id in route:
            current_queue = self.queue_backlogs.get(satellite_id, 0.0)
            if current_queue > self.max_queue_length * 0.8:
                # 队列过长，减少分配
                allocation *= 0.8
        
        # 4. 公平性约束（简化）
        allocation = min(allocation, 50.0)  # 最大50Mbps防止单流占用过多资源
        
        return max(0.0, allocation)
    
    def _get_path_capacity(self, route: List[int], network_state: NetworkState) -> float:
        """获取路径容量（瓶颈链路）"""
        if len(route) < 2:
            return 0.0
        
        min_capacity = float('inf')
        
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            
            capacity = network_state.link_capacity.get(link_key, 0.0)
            utilization = network_state.link_utilization.get(link_key, 0.0)
            
            available_capacity = capacity * (1.0 - utilization)
            min_capacity = min(min_capacity, available_capacity)
        
        return max(0.0, min_capacity)
    
    def _update_queue_states(self, network_state: NetworkState):
        """更新队列状态"""
        # 从网络状态更新队列积压
        for satellite_id, queue_length in network_state.queue_lengths.items():
            self.queue_backlogs[satellite_id] = queue_length
            
            # 记录历史
            self.queue_history[satellite_id].append(queue_length)
            if len(self.queue_history[satellite_id]) > 1000:  # 保持最近1000个记录
                self.queue_history[satellite_id].pop(0)
    
    def _update_virtual_queues(self, flow_request: FlowRequest, allocation: float):
        """更新虚拟队列（用于QoS约束）"""
        # QoS虚拟队列
        qos_key = f"qos_{flow_request.qos_class.value}"
        
        # 计算QoS违反程度
        required_bandwidth = flow_request.bandwidth_requirement
        qos_violation = max(0.0, required_bandwidth - allocation)
        
        # 更新虚拟队列
        current_virtual_queue = self.virtual_queues[qos_key]
        self.virtual_queues[qos_key] = max(0.0, current_virtual_queue + qos_violation - 1.0)
    
    def update_queue_states(self, network_state: NetworkState):
        """外部接口：更新队列状态"""
        self._update_queue_states(network_state)
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        if not self.queue_backlogs:
            return {
                'avg_queue_length': 0.0,
                'max_queue_length': 0.0,
                'queue_stability': 1.0,
                'virtual_queue_violations': 0
            }
        
        queue_lengths = list(self.queue_backlogs.values())
        
        # 计算队列稳定性指标
        stability_score = self._calculate_stability_score()
        
        # 虚拟队列违反次数
        virtual_violations = sum(1 for q in self.virtual_queues.values() if q > 10.0)
        
        return {
            'avg_queue_length': np.mean(queue_lengths),
            'max_queue_length': np.max(queue_lengths),
            'min_queue_length': np.min(queue_lengths),
            'queue_stability': stability_score,
            'virtual_queue_violations': virtual_violations,
            'total_virtual_queue_backlog': sum(self.virtual_queues.values())
        }
    
    def _calculate_stability_score(self) -> float:
        """计算队列稳定性评分"""
        if not self.queue_history:
            return 1.0
        
        stability_scores = []
        
        for satellite_id, history in self.queue_history.items():
            if len(history) < 10:
                continue
            
            # 计算队列长度的方差（稳定性指标）
            recent_history = history[-50:]  # 最近50个时间点
            variance = np.var(recent_history)
            
            # 归一化稳定性评分
            stability = 1.0 / (1.0 + variance / 100.0)
            stability_scores.append(stability)
        
        return np.mean(stability_scores) if stability_scores else 1.0
    
    def get_lyapunov_drift(self) -> float:
        """计算李雅普诺夫漂移"""
        if not self.queue_backlogs:
            return 0.0
        
        # 简化的漂移计算
        total_queue_energy = sum(q**2 for q in self.queue_backlogs.values())
        virtual_queue_energy = sum(q**2 for q in self.virtual_queues.values())
        
        return total_queue_energy + virtual_queue_energy
    
    def reset_queues(self):
        """重置队列状态"""
        self.queue_backlogs.clear()
        self.virtual_queues.clear()
        self.queue_history.clear()
        self.utility_history.clear()
        
        self.logger.info("队列状态已重置")
    
    def is_system_stable(self) -> bool:
        """检查系统是否稳定"""
        stability_score = self._calculate_stability_score()
        max_queue = max(self.queue_backlogs.values()) if self.queue_backlogs else 0.0
        
        # 稳定性条件
        is_stable = (
            stability_score > 0.7 and  # 稳定性评分足够高
            max_queue < self.max_queue_length * 0.9  # 队列长度在合理范围内
        )
        
        return is_stable
