"""
网络状态提取器

从Hypatia仿真中提取网络状态信息，包括拓扑、链路状态、流量状态等。
为DRL智能体提供标准化的状态表示。
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional
from ..core.state import NetworkState


class NetworkStateExtractor:
    """网络状态提取器"""
    
    def __init__(self, constellation_manager):
        self.logger = logging.getLogger(__name__)
        self.constellation_manager = constellation_manager
        
        # 状态历史
        self.state_history: List[NetworkState] = []
        self.max_history_length = 100
        
    def extract_state(self, time_step: float, simulator) -> NetworkState:
        """提取完整的网络状态"""
        try:
            # 获取卫星位置和拓扑
            satellites = self.constellation_manager.get_satellite_positions(time_step)
            topology = self.constellation_manager.get_topology_matrix(time_step)
            links = self.constellation_manager.get_link_states(time_step)
            
            # 从仿真器获取动态信息
            link_utilization = simulator.get_link_utilization()
            link_capacity = simulator.get_link_capacity()
            active_flows = simulator.get_active_flows()
            queue_lengths = simulator.get_queue_lengths()
            
            # 创建网络状态对象
            network_state = NetworkState(
                time_step=time_step,
                satellites=satellites,
                links=links,
                topology=topology,
                link_utilization=link_utilization,
                link_capacity=link_capacity,
                active_flows=active_flows,
                queue_lengths=queue_lengths
            )
            
            # 添加到历史记录
            self._add_to_history(network_state)
            
            return network_state
            
        except Exception as e:
            self.logger.error(f"提取网络状态失败: {e}")
            raise
    
    def _add_to_history(self, state: NetworkState) -> None:
        """添加状态到历史记录"""
        self.state_history.append(state)
        
        # 限制历史长度
        if len(self.state_history) > self.max_history_length:
            self.state_history.pop(0)
    
    def get_state_features(self, network_state: NetworkState) -> Dict[str, np.ndarray]:
        """提取状态特征用于DRL"""
        features = {}
        
        # 拓扑特征
        features['topology'] = network_state.topology.astype(np.float32)
        
        # 卫星特征
        sat_features = self._extract_satellite_features(network_state.satellites)
        features['satellites'] = sat_features
        
        # 链路特征
        link_features = self._extract_link_features(network_state.links, network_state.link_utilization)
        features['links'] = link_features
        
        # 流量特征
        flow_features = self._extract_flow_features(network_state.active_flows)
        features['flows'] = flow_features
        
        # 队列特征
        queue_features = self._extract_queue_features(network_state.queue_lengths)
        features['queues'] = queue_features
        
        return features
    
    def _extract_satellite_features(self, satellites: List[Dict[str, Any]]) -> np.ndarray:
        """提取卫星特征"""
        if not satellites:
            return np.zeros((0, 6), dtype=np.float32)
        
        features = []
        for sat in satellites:
            sat_feature = [
                sat['lat'] / 90.0,  # 归一化纬度
                sat['lon'] / 180.0,  # 归一化经度
                sat['alt'] / 1000.0,  # 归一化高度 (km)
                sat['velocity_kmps'] / 10.0,  # 归一化速度
                1.0 if sat['active'] else 0.0,  # 活跃状态
                sat['id'] / len(satellites)  # 归一化ID
            ]
            features.append(sat_feature)
        
        return np.array(features, dtype=np.float32)
    
    def _extract_link_features(self, links: List[Dict[str, Any]], 
                             utilization: Dict[Any, float]) -> np.ndarray:
        """提取链路特征"""
        if not links:
            return np.zeros((0, 6), dtype=np.float32)
        
        features = []
        for link in links:
            # 获取链路利用率
            link_key = (link['source_id'], link['dest_id'])
            util = utilization.get(link_key, 0.0)
            
            link_feature = [
                link['distance_km'] / 10000.0,  # 归一化距离
                link['propagation_delay_ms'] / 100.0,  # 归一化延迟
                link['capacity_gbps'] / 100.0,  # 归一化容量
                util,  # 利用率
                1.0 if link['available'] else 0.0,  # 可用性
                link['quality']  # 质量因子
            ]
            features.append(link_feature)
        
        return np.array(features, dtype=np.float32)
    
    def _extract_flow_features(self, flows: List[Any]) -> np.ndarray:
        """提取流量特征"""
        if not flows:
            return np.zeros((0, 5), dtype=np.float32)
        
        features = []
        for flow in flows:
            flow_feature = [
                flow.bandwidth_requirement / 100.0,  # 归一化带宽需求
                flow.latency_requirement / 1000.0,  # 归一化延迟需求
                flow.reliability_requirement,  # 可靠性需求
                flow.priority / 10.0,  # 归一化优先级
                1.0 if flow.positioning_required else 0.0  # 定位需求
            ]
            features.append(flow_feature)
        
        return np.array(features, dtype=np.float32)
    
    def _extract_queue_features(self, queue_lengths: Dict[int, float]) -> np.ndarray:
        """提取队列特征"""
        if not queue_lengths:
            return np.zeros((0, 2), dtype=np.float32)
        
        features = []
        for node_id, queue_len in queue_lengths.items():
            queue_feature = [
                node_id / 1000.0,  # 归一化节点ID
                queue_len / 100.0  # 归一化队列长度
            ]
            features.append(queue_feature)
        
        return np.array(features, dtype=np.float32)
    
    def get_network_statistics(self, network_state: NetworkState) -> Dict[str, float]:
        """计算网络统计信息"""
        stats = {}
        
        # 拓扑统计
        topology = network_state.topology
        stats['num_nodes'] = topology.shape[0]
        stats['num_edges'] = np.sum(topology) / 2  # 无向图
        stats['avg_degree'] = np.mean(np.sum(topology, axis=1))
        stats['connectivity'] = self._calculate_connectivity(topology)
        
        # 链路统计
        if network_state.link_utilization:
            utilizations = list(network_state.link_utilization.values())
            stats['avg_utilization'] = np.mean(utilizations)
            stats['max_utilization'] = np.max(utilizations)
            stats['utilization_std'] = np.std(utilizations)
        else:
            stats['avg_utilization'] = 0.0
            stats['max_utilization'] = 0.0
            stats['utilization_std'] = 0.0
        
        # 容量统计
        if network_state.link_capacity:
            capacities = list(network_state.link_capacity.values())
            stats['total_capacity'] = np.sum(capacities)
            stats['avg_capacity'] = np.mean(capacities)
        else:
            stats['total_capacity'] = 0.0
            stats['avg_capacity'] = 0.0
        
        # 流量统计
        stats['num_active_flows'] = len(network_state.active_flows)
        
        if network_state.active_flows:
            bandwidths = [flow.bandwidth_requirement for flow in network_state.active_flows]
            stats['total_bandwidth_demand'] = np.sum(bandwidths)
            stats['avg_bandwidth_demand'] = np.mean(bandwidths)
        else:
            stats['total_bandwidth_demand'] = 0.0
            stats['avg_bandwidth_demand'] = 0.0
        
        # 队列统计
        if network_state.queue_lengths:
            queue_lens = list(network_state.queue_lengths.values())
            stats['avg_queue_length'] = np.mean(queue_lens)
            stats['max_queue_length'] = np.max(queue_lens)
        else:
            stats['avg_queue_length'] = 0.0
            stats['max_queue_length'] = 0.0
        
        return stats
    
    def _calculate_connectivity(self, topology: np.ndarray) -> float:
        """计算网络连通性"""
        if topology.shape[0] == 0:
            return 0.0
        
        # 使用简化的连通性度量：最大连通分量大小 / 总节点数
        try:
            # 计算连通分量（简化版本）
            n = topology.shape[0]
            visited = np.zeros(n, dtype=bool)
            max_component_size = 0
            
            for i in range(n):
                if not visited[i]:
                    component_size = self._dfs_component_size(topology, i, visited)
                    max_component_size = max(max_component_size, component_size)
            
            connectivity = max_component_size / n
            return connectivity
            
        except Exception:
            return 0.0
    
    def _dfs_component_size(self, topology: np.ndarray, start: int, visited: np.ndarray) -> int:
        """深度优先搜索计算连通分量大小"""
        stack = [start]
        size = 0
        
        while stack:
            node = stack.pop()
            if not visited[node]:
                visited[node] = True
                size += 1
                
                # 添加邻居节点
                for neighbor in range(topology.shape[1]):
                    if topology[node][neighbor] and not visited[neighbor]:
                        stack.append(neighbor)
        
        return size
    
    def get_temporal_features(self, window_size: int = 10) -> Optional[Dict[str, np.ndarray]]:
        """提取时序特征"""
        if len(self.state_history) < window_size:
            return None
        
        # 获取最近的状态窗口
        recent_states = self.state_history[-window_size:]
        
        # 提取时序特征
        temporal_features = {}
        
        # 利用率变化趋势
        utilization_trends = []
        for state in recent_states:
            if state.link_utilization:
                avg_util = np.mean(list(state.link_utilization.values()))
                utilization_trends.append(avg_util)
        
        if utilization_trends:
            temporal_features['utilization_trend'] = np.array(utilization_trends, dtype=np.float32)
        
        # 流量数量变化
        flow_counts = [len(state.active_flows) for state in recent_states]
        temporal_features['flow_count_trend'] = np.array(flow_counts, dtype=np.float32)
        
        # 队列长度变化
        queue_trends = []
        for state in recent_states:
            if state.queue_lengths:
                avg_queue = np.mean(list(state.queue_lengths.values()))
                queue_trends.append(avg_queue)
            else:
                queue_trends.append(0.0)
        
        temporal_features['queue_trend'] = np.array(queue_trends, dtype=np.float32)
        
        return temporal_features
