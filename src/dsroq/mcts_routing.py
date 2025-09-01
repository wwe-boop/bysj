"""
MCTS路由算法

实现基于蒙特卡洛树搜索的卫星网络路由算法
"""

import time
import random
import math
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from src.core.state import NetworkState, FlowRequest


class MCTSNode:
    """MCTS树节点"""
    
    def __init__(self, satellite_id: int, parent: Optional['MCTSNode'] = None):
        self.satellite_id = satellite_id
        self.parent = parent
        self.children: List['MCTSNode'] = []
        self.visits = 0
        self.total_reward = 0.0
        self.untried_actions: List[int] = []
        
    def is_fully_expanded(self) -> bool:
        """检查节点是否完全展开"""
        return len(self.untried_actions) == 0
    
    def is_leaf(self) -> bool:
        """检查是否为叶节点"""
        return len(self.children) == 0
    
    def add_child(self, satellite_id: int) -> 'MCTSNode':
        """添加子节点"""
        child = MCTSNode(satellite_id, self)
        self.children.append(child)
        if satellite_id in self.untried_actions:
            self.untried_actions.remove(satellite_id)
        return child
    
    def update(self, reward: float):
        """更新节点统计信息"""
        self.visits += 1
        self.total_reward += reward
    
    def get_average_reward(self) -> float:
        """获取平均奖励"""
        return self.total_reward / self.visits if self.visits > 0 else 0.0
    
    def get_ucb_value(self, exploration_constant: float = 1.414) -> float:
        """计算UCB值"""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.get_average_reward()
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        ) if self.parent else 0.0
        
        return exploitation + exploration
    
    def select_best_child(self, exploration_constant: float = 1.414) -> 'MCTSNode':
        """选择最佳子节点"""
        return max(self.children, key=lambda child: child.get_ucb_value(exploration_constant))
    
    def get_path_from_root(self) -> List[int]:
        """获取从根节点到当前节点的路径"""
        path = []
        node = self
        while node is not None:
            path.append(node.satellite_id)
            node = node.parent
        return list(reversed(path))


class MCTSRouter:
    """MCTS路由器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # MCTS参数
        self.iterations = config.get('mcts_iterations', 1000)
        self.exploration_constant = config.get('mcts_exploration_constant', 1.414)
        self.max_depth = config.get('mcts_max_depth', 10)
        self.simulation_depth = config.get('simulation_depth', 5)
        
        # 路由约束
        self.max_hops = config.get('max_hops', 8)
        self.min_link_capacity = config.get('min_link_capacity', 1.0)  # Mbps
        
        self.logger.info(f"MCTS路由器初始化: iterations={self.iterations}, "
                        f"exploration={self.exploration_constant}")
    
    def find_route(self, flow_request: FlowRequest, network_state: NetworkState) -> Optional[List[int]]:
        """使用MCTS找到最优路由"""
        try:
            # 1. 找到源和目标卫星
            source_satellite = self._find_nearest_satellite(flow_request.source, network_state)
            destination_satellite = self._find_nearest_satellite(flow_request.destination, network_state)
            
            if source_satellite is None or destination_satellite is None:
                self.logger.warning("无法找到源或目标卫星")
                return None
            
            if source_satellite == destination_satellite:
                return [source_satellite]
            
            # 2. 运行MCTS算法
            route = self._mcts_search(source_satellite, destination_satellite, 
                                    flow_request, network_state)
            
            if route and len(route) > 1:
                self.logger.debug(f"找到路由: {route}, 长度: {len(route)}")
                return route
            else:
                self.logger.debug("MCTS未找到有效路由")
                return None
                
        except Exception as e:
            self.logger.error(f"MCTS路由查找失败: {e}")
            return None
    
    def _mcts_search(self, 
                    source: int, 
                    destination: int,
                    flow_request: FlowRequest,
                    network_state: NetworkState) -> Optional[List[int]]:
        """执行MCTS搜索"""
        
        # 创建根节点
        root = MCTSNode(source)
        root.untried_actions = self._get_neighbors(source, network_state)
        
        start_time = time.time()
        
        for iteration in range(self.iterations):
            # 检查超时
            if time.time() - start_time > 1.0:  # 1秒超时
                break
            
            # 1. 选择
            node = self._select(root)
            
            # 2. 展开
            if not node.is_fully_expanded() and len(node.get_path_from_root()) < self.max_depth:
                node = self._expand(node, network_state)
            
            # 3. 模拟
            reward = self._simulate(node, destination, flow_request, network_state)
            
            # 4. 回传
            self._backpropagate(node, reward)
        
        # 选择最佳路径
        return self._select_best_path(root, destination)
    
    def _select(self, root: MCTSNode) -> MCTSNode:
        """选择阶段：选择最有前途的节点"""
        node = root
        
        while not node.is_leaf() and node.is_fully_expanded():
            node = node.select_best_child(self.exploration_constant)
        
        return node
    
    def _expand(self, node: MCTSNode, network_state: NetworkState) -> MCTSNode:
        """展开阶段：添加新的子节点"""
        if node.untried_actions:
            action = random.choice(node.untried_actions)
            child = node.add_child(action)
            child.untried_actions = self._get_neighbors(action, network_state)
            
            # 避免回路
            path = child.get_path_from_root()
            child.untried_actions = [sat for sat in child.untried_actions 
                                   if sat not in path[:-1]]
            
            return child
        
        return node
    
    def _simulate(self, 
                 node: MCTSNode, 
                 destination: int,
                 flow_request: FlowRequest,
                 network_state: NetworkState) -> float:
        """模拟阶段：随机模拟到终点"""
        
        current_path = node.get_path_from_root()
        current_satellite = current_path[-1]
        
        # 如果已经到达目标
        if current_satellite == destination:
            return self._evaluate_path(current_path, flow_request, network_state)
        
        # 随机模拟
        simulation_path = current_path.copy()
        
        for _ in range(self.simulation_depth):
            if simulation_path[-1] == destination:
                break
            
            neighbors = self._get_neighbors(simulation_path[-1], network_state)
            # 避免回路
            neighbors = [sat for sat in neighbors if sat not in simulation_path]
            
            if not neighbors:
                break
            
            # 选择下一跳（带有启发式）
            next_satellite = self._select_next_hop_heuristic(
                simulation_path[-1], destination, neighbors, network_state
            )
            
            simulation_path.append(next_satellite)
        
        return self._evaluate_path(simulation_path, flow_request, network_state)
    
    def _backpropagate(self, node: MCTSNode, reward: float):
        """回传阶段：更新路径上所有节点的统计信息"""
        while node is not None:
            node.update(reward)
            node = node.parent
    
    def _select_best_path(self, root: MCTSNode, destination: int) -> Optional[List[int]]:
        """选择最佳路径"""
        # 使用访问次数最多的路径
        best_path = None
        best_score = -1
        
        def dfs_find_paths(node: MCTSNode, current_path: List[int]):
            nonlocal best_path, best_score
            
            current_path.append(node.satellite_id)
            
            if node.satellite_id == destination:
                # 找到到达目标的路径
                score = node.visits + node.get_average_reward()
                if score > best_score:
                    best_score = score
                    best_path = current_path.copy()
            else:
                # 继续搜索子节点
                for child in node.children:
                    if len(current_path) < self.max_hops:
                        dfs_find_paths(child, current_path)
            
            current_path.pop()
        
        dfs_find_paths(root, [])
        
        return best_path
    
    def _get_neighbors(self, satellite_id: int, network_state: NetworkState) -> List[int]:
        """获取卫星的邻居"""
        neighbors = []
        
        for i, row in enumerate(network_state.topology):
            if i != satellite_id and network_state.topology[satellite_id][i] == 1:
                # 检查链路容量
                link_key = (satellite_id, i)
                capacity = network_state.link_capacity.get(link_key, 0.0)
                utilization = network_state.link_utilization.get(link_key, 0.0)
                available_capacity = capacity * (1.0 - utilization)
                
                if available_capacity >= self.min_link_capacity:
                    neighbors.append(i)
        
        return neighbors
    
    def _find_nearest_satellite(self, location: Tuple[float, float], 
                              network_state: NetworkState) -> Optional[int]:
        """找到最近的卫星"""
        lat, lon = location
        min_distance = float('inf')
        nearest_satellite = None
        
        for satellite in network_state.satellites:
            if not satellite.get('active', True):
                continue
            
            sat_lat = satellite['lat']
            sat_lon = satellite['lon']
            distance = np.sqrt((lat - sat_lat)**2 + (lon - sat_lon)**2)
            
            if distance < min_distance:
                min_distance = distance
                nearest_satellite = satellite['id']
        
        return nearest_satellite
    
    def _select_next_hop_heuristic(self, 
                                  current: int, 
                                  destination: int,
                                  neighbors: List[int],
                                  network_state: NetworkState) -> int:
        """启发式选择下一跳"""
        if not neighbors:
            return current
        
        # 获取目标卫星位置
        dest_satellite = next(sat for sat in network_state.satellites 
                            if sat['id'] == destination)
        dest_lat, dest_lon = dest_satellite['lat'], dest_satellite['lon']
        
        best_neighbor = neighbors[0]
        min_distance = float('inf')
        
        for neighbor in neighbors:
            neighbor_satellite = next(sat for sat in network_state.satellites 
                                    if sat['id'] == neighbor)
            neighbor_lat, neighbor_lon = neighbor_satellite['lat'], neighbor_satellite['lon']
            
            # 计算到目标的距离
            distance = np.sqrt((dest_lat - neighbor_lat)**2 + (dest_lon - neighbor_lon)**2)
            
            # 考虑链路质量
            link_key = (current, neighbor)
            utilization = network_state.link_utilization.get(link_key, 0.0)
            quality_factor = 1.0 - utilization
            
            # 综合评分
            score = distance / quality_factor
            
            if score < min_distance:
                min_distance = score
                best_neighbor = neighbor
        
        return best_neighbor
    
    def _evaluate_path(self, 
                      path: List[int],
                      flow_request: FlowRequest,
                      network_state: NetworkState) -> float:
        """评估路径质量"""
        if len(path) < 2:
            return 0.0
        
        reward = 0.0
        
        # 1. 路径长度惩罚
        length_penalty = len(path) * 0.1
        reward -= length_penalty
        
        # 2. 带宽可用性奖励
        min_available_bandwidth = float('inf')
        total_utilization = 0.0
        
        for i in range(len(path) - 1):
            link_key = (path[i], path[i + 1])
            
            capacity = network_state.link_capacity.get(link_key, 0.0)
            utilization = network_state.link_utilization.get(link_key, 0.0)
            
            if capacity > 0:
                available_bandwidth = capacity * (1.0 - utilization)
                min_available_bandwidth = min(min_available_bandwidth, available_bandwidth)
                total_utilization += utilization
        
        # 带宽奖励
        if min_available_bandwidth != float('inf'):
            bandwidth_reward = min(10.0, min_available_bandwidth / flow_request.bandwidth_requirement)
            reward += bandwidth_reward
        
        # 3. 负载均衡奖励
        avg_utilization = total_utilization / (len(path) - 1) if len(path) > 1 else 0.0
        load_balance_reward = (1.0 - avg_utilization) * 5.0
        reward += load_balance_reward
        
        # 4. 到达目标奖励
        if len(path) >= 2:
            reward += 20.0  # 基础到达奖励
        
        return reward
