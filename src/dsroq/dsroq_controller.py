"""
DSROQ控制器

整合MCTS路由和李雅普诺夫优化的主控制器
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from src.core.interfaces import DSROQInterface
from src.core.state import NetworkState, FlowRequest, UserRequest, AllocationResult
from .mcts_routing import MCTSRouter
from .lyapunov_optimizer import LyapunovOptimizer
from .bandwidth_allocator import BandwidthAllocator


class DSROQController(DSROQInterface):
    """DSROQ资源分配控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化子模块
        self.mcts_router = MCTSRouter(config)
        self.lyapunov_optimizer = LyapunovOptimizer(config)
        self.bandwidth_allocator = BandwidthAllocator(config)
        
        # 性能统计
        self.total_requests = 0
        self.successful_allocations = 0
        self.failed_allocations = 0
        self.routing_times = []
        self.allocation_times = []
        
        # QoS统计
        self.qos_violations = 0
        self.bandwidth_utilization_history = []
        self.latency_history = []
        
        self.logger.info("DSROQ控制器初始化完成")
    
    def process_user_request(self, 
                           user_request: UserRequest,
                           network_state: NetworkState) -> Optional[AllocationResult]:
        """处理用户请求，返回资源分配结果"""
        start_time = time.time()
        
        try:
            self.total_requests += 1
            
            # 1. 将用户请求转换为流请求
            flow_request = self._convert_to_flow_request(user_request, network_state)
            
            # 2. 使用MCTS找到路由
            route = self.find_route(flow_request, network_state)
            if route is None:
                self.failed_allocations += 1
                self.logger.debug(f"无法为用户{user_request.user_id}找到路由")
                return None
            
            # 3. 使用李雅普诺夫优化分配带宽
            allocated_bandwidth = self.allocate_bandwidth(flow_request, route, network_state)
            if allocated_bandwidth <= 0:
                self.failed_allocations += 1
                self.logger.debug(f"无法为用户{user_request.user_id}分配带宽")
                return None
            
            # 4. 创建分配结果
            allocation_result = AllocationResult(
                flow_id=flow_request.flow_id,
                route=route,
                allocated_bandwidth=allocated_bandwidth,
                estimated_latency=self._estimate_latency(route, network_state),
                qos_class=flow_request.qos_class,
                allocation_time=time.time()
            )
            
            # 5. 更新网络状态
            self._update_network_state(allocation_result, network_state)
            
            self.successful_allocations += 1
            allocation_time = time.time() - start_time
            self.allocation_times.append(allocation_time)
            
            self.logger.debug(f"成功为用户{user_request.user_id}分配资源: "
                            f"路由长度={len(route)}, 带宽={allocated_bandwidth:.1f}Mbps")
            
            return allocation_result
            
        except Exception as e:
            self.logger.error(f"处理用户请求失败: {e}")
            self.failed_allocations += 1
            return None
    
    def find_route(self, flow_request: FlowRequest, network_state: NetworkState) -> Optional[List[int]]:
        """使用MCTS找到最优路由"""
        start_time = time.time()
        
        try:
            route = self.mcts_router.find_route(flow_request, network_state)
            
            routing_time = time.time() - start_time
            self.routing_times.append(routing_time)
            
            return route
            
        except Exception as e:
            self.logger.error(f"路由查找失败: {e}")
            return None
    
    def allocate_bandwidth(self, 
                         flow_request: FlowRequest, 
                         route: List[int],
                         network_state: NetworkState) -> float:
        """使用李雅普诺夫优化分配带宽"""
        try:
            # 1. 检查路径可用带宽
            available_bandwidth = self._get_path_available_bandwidth(route, network_state)
            
            # 2. 使用李雅普诺夫优化器计算最优分配
            optimal_bandwidth = self.lyapunov_optimizer.optimize_allocation(
                flow_request, route, network_state, available_bandwidth
            )
            
            # 3. 使用带宽分配器进行精细分配
            allocated_bandwidth = self.bandwidth_allocator.allocate(
                flow_request, route, optimal_bandwidth, network_state
            )
            
            return allocated_bandwidth
            
        except Exception as e:
            self.logger.error(f"带宽分配失败: {e}")
            return 0.0
    
    def process_admission_decision(self, 
                                 decision: Any,
                                 flow_request: FlowRequest,
                                 network_state: NetworkState) -> Optional[AllocationResult]:
        """处理准入决策，返回资源分配结果"""
        # 这个方法主要用于与准入控制模块的集成
        if hasattr(decision, 'decision') and decision.decision.value == 'accept':
            # 如果准入控制决定接受，进行资源分配
            user_request = self._convert_to_user_request(flow_request)
            return self.process_user_request(user_request, network_state)
        else:
            return None
    
    def update_queue_states(self, network_state: NetworkState) -> None:
        """更新队列状态用于李雅普诺夫优化"""
        self.lyapunov_optimizer.update_queue_states(network_state)
    
    def _convert_to_flow_request(self, user_request: UserRequest, network_state: NetworkState) -> FlowRequest:
        """将用户请求转换为流请求"""
        # 找到最近的卫星作为目标
        destination_satellite = self._find_nearest_satellite(
            user_request.user_lat, user_request.user_lon, network_state
        )
        
        destination = (
            network_state.satellites[destination_satellite]['lat'],
            network_state.satellites[destination_satellite]['lon']
        ) if destination_satellite is not None else (0.0, 0.0)
        
        return user_request.to_flow_request(
            flow_id=f"flow_{user_request.user_id}_{int(time.time())}",
            destination=destination
        )
    
    def _convert_to_user_request(self, flow_request: FlowRequest) -> UserRequest:
        """将流请求转换为用户请求（用于兼容性）"""
        return UserRequest(
            user_id=flow_request.flow_id,
            service_type=flow_request.flow_type.value,
            bandwidth_mbps=flow_request.bandwidth_requirement,
            max_latency_ms=flow_request.latency_requirement,
            min_reliability=flow_request.reliability_requirement,
            priority=flow_request.priority,
            user_lat=flow_request.source[0],
            user_lon=flow_request.source[1],
            duration_seconds=flow_request.duration,
            timestamp=flow_request.arrival_time
        )
    
    def _find_nearest_satellite(self, lat: float, lon: float, network_state: NetworkState) -> Optional[int]:
        """找到最近的卫星"""
        min_distance = float('inf')
        nearest_satellite = None
        
        for satellite in network_state.satellites:
            if not satellite.get('active', True):
                continue
            
            # 简化的距离计算
            sat_lat = satellite['lat']
            sat_lon = satellite['lon']
            distance = np.sqrt((lat - sat_lat)**2 + (lon - sat_lon)**2)
            
            if distance < min_distance:
                min_distance = distance
                nearest_satellite = satellite['id']
        
        return nearest_satellite
    
    def _get_path_available_bandwidth(self, route: List[int], network_state: NetworkState) -> float:
        """获取路径可用带宽"""
        if len(route) < 2:
            return 0.0
        
        min_bandwidth = float('inf')
        
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            
            # 获取链路容量
            capacity = network_state.link_capacity.get(link_key, 0.0)
            
            # 获取链路利用率
            utilization = network_state.link_utilization.get(link_key, 0.0)
            
            # 计算可用带宽
            available = capacity * (1.0 - utilization)
            min_bandwidth = min(min_bandwidth, available)
        
        return max(0.0, min_bandwidth)
    
    def _estimate_latency(self, route: List[int], network_state: NetworkState) -> float:
        """估算路径延迟"""
        if len(route) < 2:
            return 0.0
        
        total_latency = 0.0
        
        for i in range(len(route) - 1):
            # 传播延迟（基于距离）
            sat1 = next(sat for sat in network_state.satellites if sat['id'] == route[i])
            sat2 = next(sat for sat in network_state.satellites if sat['id'] == route[i + 1])
            
            distance = np.sqrt(
                (sat1['x'] - sat2['x'])**2 + 
                (sat1['y'] - sat2['y'])**2 + 
                (sat1['z'] - sat2['z'])**2
            )
            
            # 光速传播延迟 (距离单位为km)
            propagation_delay = distance / 300000.0 * 1000  # ms
            
            # 处理延迟（简化）
            processing_delay = 1.0  # 1ms
            
            total_latency += propagation_delay + processing_delay
        
        return total_latency
    
    def _update_network_state(self, allocation_result: AllocationResult, network_state: NetworkState):
        """更新网络状态"""
        route = allocation_result.route
        bandwidth = allocation_result.allocated_bandwidth
        
        # 更新链路利用率
        for i in range(len(route) - 1):
            link_key = (route[i], route[i + 1])
            
            if link_key in network_state.link_capacity:
                capacity = network_state.link_capacity[link_key]
                current_utilization = network_state.link_utilization.get(link_key, 0.0)
                
                # 增加利用率
                additional_utilization = bandwidth / capacity if capacity > 0 else 0.0
                new_utilization = min(1.0, current_utilization + additional_utilization)
                network_state.link_utilization[link_key] = new_utilization
        
        # 更新队列长度（简化）
        for sat_id in route:
            current_queue = network_state.queue_lengths.get(sat_id, 0.0)
            network_state.queue_lengths[sat_id] = current_queue + bandwidth * 0.1
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.total_requests == 0:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'avg_routing_time': 0.0,
                'avg_allocation_time': 0.0,
                'qos_violation_rate': 0.0
            }
        
        return {
            'total_requests': self.total_requests,
            'successful_allocations': self.successful_allocations,
            'failed_allocations': self.failed_allocations,
            'success_rate': self.successful_allocations / self.total_requests,
            'avg_routing_time': np.mean(self.routing_times) if self.routing_times else 0.0,
            'avg_allocation_time': np.mean(self.allocation_times) if self.allocation_times else 0.0,
            'qos_violations': self.qos_violations,
            'qos_violation_rate': self.qos_violations / self.total_requests
        }
