"""
NS3仿真器

封装ns3网络仿真功能，提供流量注入、性能监控、仿真控制等接口。
支持包级仿真和性能指标收集。
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import time
import random

from ..core.state import FlowRequest


class NS3Simulator:
    """NS3仿真器封装"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 仿真状态
        self.initialized = False
        self.current_time = 0.0
        self.time_step = 1.0  # 默认时间步长（秒）
        
        # 网络状态
        self.active_flows: List[FlowRequest] = []
        self.link_utilization: Dict[Tuple[int, int], float] = {}
        self.link_capacity: Dict[Tuple[int, int], float] = {}
        self.queue_lengths: Dict[int, float] = {}
        
        # 性能指标
        self.performance_metrics: Dict[str, float] = {}
        self.flow_statistics: Dict[str, Dict[str, float]] = {}
        
        # 仿真参数
        self.packet_size_bytes = 1500
        self.buffer_size_packets = 1000
        
    def initialize(self) -> None:
        """初始化NS3仿真器"""
        try:
            self.logger.info("初始化NS3仿真器...")
            
            # 初始化网络状态
            self._initialize_network_state()
            
            # 初始化性能监控
            self._initialize_performance_monitoring()
            
            self.initialized = True
            self.logger.info("NS3仿真器初始化完成")
            
        except Exception as e:
            self.logger.error(f"NS3仿真器初始化失败: {e}")
            raise
    
    def _initialize_network_state(self) -> None:
        """初始化网络状态"""
        # 初始化链路容量（基于配置）
        num_sats = self.config.get('num_orbits', 72) * self.config.get('num_sats_per_orbit', 22)
        
        # 为每个可能的链路设置初始容量
        for i in range(num_sats):
            for j in range(i+1, num_sats):
                # 简化的容量分配
                base_capacity = 10.0  # Gbps
                capacity = base_capacity + random.uniform(-2.0, 2.0)
                capacity = max(1.0, capacity)
                
                self.link_capacity[(i, j)] = capacity
                self.link_capacity[(j, i)] = capacity  # 双向链路
                
                # 初始利用率为0
                self.link_utilization[(i, j)] = 0.0
                self.link_utilization[(j, i)] = 0.0
        
        # 初始化队列长度
        for i in range(num_sats):
            self.queue_lengths[i] = 0.0
    
    def _initialize_performance_monitoring(self) -> None:
        """初始化性能监控"""
        self.performance_metrics = {
            'throughput': 0.0,
            'latency': 0.0,
            'packet_loss': 0.0,
            'jitter': 0.0,
            'utilization': 0.0,
            'energy': 0.0
        }
    
    def add_flow(self, flow: FlowRequest, route: List[int], bandwidth: float) -> bool:
        """添加流量到仿真"""
        if not self.initialized:
            return False
        
        try:
            # 检查路由可行性
            if not self._validate_route(route, bandwidth):
                self.logger.warning(f"路由验证失败: {route}")
                return False
            
            # 更新链路利用率
            self._update_link_utilization(route, bandwidth, add=True)
            
            # 添加到活跃流量列表
            flow_copy = flow
            self.active_flows.append(flow_copy)
            
            # 初始化流量统计
            self.flow_statistics[flow.flow_id] = {
                'start_time': self.current_time,
                'bandwidth': bandwidth,
                'route': route.copy(),
                'packets_sent': 0,
                'packets_received': 0,
                'total_delay': 0.0,
                'total_jitter': 0.0
            }
            
            self.logger.debug(f"成功添加流量 {flow.flow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加流量失败: {e}")
            return False
    
    def _validate_route(self, route: List[int], bandwidth: float) -> bool:
        """验证路由可行性"""
        if len(route) < 2:
            return False
        
        # 检查每个链路的可用容量
        for i in range(len(route) - 1):
            src, dst = route[i], route[i+1]
            link_key = (src, dst)
            
            if link_key not in self.link_capacity:
                return False
            
            available_capacity = (self.link_capacity[link_key] * 
                                (1.0 - self.link_utilization.get(link_key, 0.0)))
            
            if available_capacity < bandwidth / 1000.0:  # 转换为Gbps
                return False
        
        return True
    
    def _update_link_utilization(self, route: List[int], bandwidth: float, add: bool = True) -> None:
        """更新链路利用率"""
        bandwidth_gbps = bandwidth / 1000.0  # 转换为Gbps
        
        for i in range(len(route) - 1):
            src, dst = route[i], route[i+1]
            link_key = (src, dst)
            
            if link_key in self.link_capacity:
                current_util = self.link_utilization.get(link_key, 0.0)
                capacity = self.link_capacity[link_key]
                
                if add:
                    new_util = current_util + bandwidth_gbps / capacity
                else:
                    new_util = current_util - bandwidth_gbps / capacity
                
                self.link_utilization[link_key] = max(0.0, min(1.0, new_util))
    
    def remove_flow(self, flow_id: str) -> bool:
        """移除流量"""
        try:
            # 查找并移除流量
            flow_to_remove = None
            for flow in self.active_flows:
                if flow.flow_id == flow_id:
                    flow_to_remove = flow
                    break
            
            if flow_to_remove is None:
                return False
            
            # 获取流量统计信息
            if flow_id in self.flow_statistics:
                stats = self.flow_statistics[flow_id]
                route = stats['route']
                bandwidth = stats['bandwidth']
                
                # 更新链路利用率
                self._update_link_utilization(route, bandwidth, add=False)
                
                # 移除统计信息
                del self.flow_statistics[flow_id]
            
            # 从活跃流量列表移除
            self.active_flows.remove(flow_to_remove)
            
            self.logger.debug(f"成功移除流量 {flow_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"移除流量失败: {e}")
            return False
    
    def step(self, time_step: float) -> None:
        """推进仿真一个时间步"""
        if not self.initialized:
            return
        
        self.current_time += time_step
        
        # 更新流量统计
        self._update_flow_statistics(time_step)
        
        # 更新队列状态
        self._update_queue_states()
        
        # 更新性能指标
        self._update_performance_metrics()
        
        # 检查流量到期
        self._check_flow_expiration()
    
    def _update_flow_statistics(self, time_step: float) -> None:
        """更新流量统计信息"""
        for flow_id, stats in self.flow_statistics.items():
            # 模拟数据包传输
            bandwidth_mbps = stats['bandwidth']
            packets_per_second = (bandwidth_mbps * 1e6) / (self.packet_size_bytes * 8)
            packets_this_step = int(packets_per_second * time_step)
            
            stats['packets_sent'] += packets_this_step
            
            # 模拟数据包接收（考虑丢包）
            loss_rate = self._calculate_packet_loss_rate(stats['route'])
            packets_received = int(packets_this_step * (1.0 - loss_rate))
            stats['packets_received'] += packets_received
            
            # 模拟延迟
            route_delay = self._calculate_route_delay(stats['route'])
            stats['total_delay'] += route_delay * packets_received
            
            # 模拟抖动
            jitter = random.uniform(0.0, route_delay * 0.1)
            stats['total_jitter'] += jitter * packets_received
    
    def _calculate_packet_loss_rate(self, route: List[int]) -> float:
        """计算路由的丢包率"""
        total_loss_rate = 0.0
        
        for i in range(len(route) - 1):
            src, dst = route[i], route[i+1]
            link_key = (src, dst)
            
            # 基于链路利用率计算丢包率
            utilization = self.link_utilization.get(link_key, 0.0)
            
            # 简化的丢包模型
            if utilization > 0.8:
                link_loss_rate = (utilization - 0.8) * 0.5  # 高利用率时丢包增加
            else:
                link_loss_rate = 0.001  # 基础丢包率
            
            total_loss_rate += link_loss_rate
        
        return min(0.5, total_loss_rate)  # 最大50%丢包率
    
    def _calculate_route_delay(self, route: List[int]) -> float:
        """计算路由延迟"""
        total_delay = 0.0
        
        for i in range(len(route) - 1):
            src, dst = route[i], route[i+1]
            
            # 传播延迟（基于距离）
            propagation_delay = 5.0  # 简化为固定值 (ms)
            
            # 队列延迟
            queue_delay = self.queue_lengths.get(src, 0.0) * 0.1  # ms
            
            # 处理延迟
            processing_delay = 1.0  # ms
            
            total_delay += propagation_delay + queue_delay + processing_delay
        
        return total_delay
    
    def _update_queue_states(self) -> None:
        """更新队列状态"""
        for node_id in self.queue_lengths.keys():
            # 基于流量负载更新队列长度
            incoming_load = 0.0
            
            for flow_id, stats in self.flow_statistics.items():
                route = stats['route']
                if node_id in route:
                    incoming_load += stats['bandwidth'] / 1000.0  # Gbps
            
            # 简化的队列模型
            service_rate = 10.0  # Gbps
            if incoming_load > service_rate:
                self.queue_lengths[node_id] += (incoming_load - service_rate) * 10
            else:
                self.queue_lengths[node_id] *= 0.9  # 队列逐渐减少
            
            # 限制队列长度
            self.queue_lengths[node_id] = max(0.0, min(self.buffer_size_packets, 
                                                     self.queue_lengths[node_id]))
    
    def _update_performance_metrics(self) -> None:
        """更新性能指标"""
        if not self.flow_statistics:
            return
        
        # 计算平均吞吐量
        total_throughput = 0.0
        total_delay = 0.0
        total_jitter = 0.0
        total_packets_sent = 0
        total_packets_received = 0
        
        for stats in self.flow_statistics.values():
            total_throughput += stats['bandwidth']
            total_packets_sent += stats['packets_sent']
            total_packets_received += stats['packets_received']
            
            if stats['packets_received'] > 0:
                total_delay += stats['total_delay']
                total_jitter += stats['total_jitter']
        
        # 更新指标
        self.performance_metrics['throughput'] = total_throughput
        
        if total_packets_received > 0:
            self.performance_metrics['latency'] = total_delay / total_packets_received
            self.performance_metrics['jitter'] = total_jitter / total_packets_received
        
        if total_packets_sent > 0:
            self.performance_metrics['packet_loss'] = 1.0 - (total_packets_received / total_packets_sent)
        
        # 计算平均利用率
        if self.link_utilization:
            self.performance_metrics['utilization'] = np.mean(list(self.link_utilization.values()))
        
        # 简化的能耗模型
        self.performance_metrics['energy'] = total_throughput * 0.1  # 简化计算
    
    def _check_flow_expiration(self) -> None:
        """检查并移除过期流量"""
        expired_flows = []
        
        for flow in self.active_flows:
            if flow.flow_id in self.flow_statistics:
                stats = self.flow_statistics[flow.flow_id]
                elapsed_time = self.current_time - stats['start_time']
                
                if elapsed_time >= flow.duration:
                    expired_flows.append(flow.flow_id)
        
        # 移除过期流量
        for flow_id in expired_flows:
            self.remove_flow(flow_id)
    
    def get_active_flows(self) -> List[FlowRequest]:
        """获取当前活跃流量"""
        return self.active_flows.copy()
    
    def get_link_utilization(self) -> Dict[Tuple[int, int], float]:
        """获取链路利用率"""
        return self.link_utilization.copy()
    
    def get_link_capacity(self) -> Dict[Tuple[int, int], float]:
        """获取链路容量"""
        return self.link_capacity.copy()
    
    def get_queue_lengths(self) -> Dict[int, float]:
        """获取队列长度"""
        return self.queue_lengths.copy()
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标"""
        return self.performance_metrics.copy()
    
    def get_flow_statistics(self) -> Dict[str, Dict[str, float]]:
        """获取流量统计信息"""
        return {k: v.copy() for k, v in self.flow_statistics.items()}
    
    def reset(self) -> None:
        """重置仿真状态"""
        self.current_time = 0.0
        self.active_flows.clear()
        self.flow_statistics.clear()
        
        # 重置链路利用率
        for key in self.link_utilization:
            self.link_utilization[key] = 0.0
        
        # 重置队列长度
        for key in self.queue_lengths:
            self.queue_lengths[key] = 0.0
        
        # 重置性能指标
        self._initialize_performance_monitoring()
        
        self.logger.info("仿真状态已重置")
