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
        
        # 设计文档中的关键参数 (algorithm_design.md 第467-475行)
        self.seam_penalty = config.get('seam_penalty', 0.5)  # 跨缝路径的附加代价
        self.path_change_penalty = config.get('path_change_penalty', 0.3)  # 路径变更的惩罚
        self.reroute_cooldown_ms = config.get('reroute_cooldown_ms', 5000)  # 重路由冷却时间
        
        # 定位协同参数 (algorithm_design.md 第477-481行)
        self.lambda_pos = config.get('lambda_pos', 0.2)  # 定位质量权重
        self.crlb_threshold = config.get('crlb_threshold', 50.0)  # CRLB阈值
        self.min_visible_beams = config.get('min_visible_beams', 2)  # 最小可见波束数
        self.min_coop_sats = config.get('min_coop_sats', 2)  # 最小协作卫星数

        # Beam Hint 软约束权重（注入到路径评估）
        self.beam_hint_weight = config.get('beam_hint_weight', 0.2)
        
        # 路由历史（用于计算路径变更惩罚）
        self.route_history = {}  # flow_id -> (route, timestamp)
        self.last_reroute_time = {}  # flow_id -> timestamp
        
        self.logger.info(f"MCTS路由器初始化: iterations={self.iterations}, "
                        f"exploration={self.exploration_constant}, "
                        f"seam_penalty={self.seam_penalty}, lambda_pos={self.lambda_pos}")
    
    def find_route(self, flow_request: FlowRequest, network_state: NetworkState) -> Optional[List[int]]:
        """使用MCTS找到最优路由（考虑重路由冷却时间）"""
        try:
            # 检查重路由冷却时间
            flow_id = getattr(flow_request, 'flow_id', None)
            current_time = time.time() * 1000  # ms
            
            if flow_id and flow_id in self.last_reroute_time:
                time_since_last = current_time - self.last_reroute_time[flow_id]
                if time_since_last < self.reroute_cooldown_ms:
                    # 在冷却期内，返回原路由
                    if flow_id in self.route_history:
                        old_route, _ = self.route_history[flow_id]
                        self.logger.debug(f"流{flow_id}在重路由冷却期内，使用原路由")
                        return old_route
            
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
                # 记录路由历史
                if flow_id:
                    self.route_history[flow_id] = (route, current_time)
                    self.last_reroute_time[flow_id] = current_time
                
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
        """评估路径质量（整合定位质量和稳定性考虑）"""
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
        
        # 4. 跨缝惩罚（设计文档要求）
        seam_crossings = self._count_seam_crossings(path, network_state)
        seam_penalty_total = seam_crossings * self.seam_penalty * 10.0
        reward -= seam_penalty_total
        
        # 5. 路径变更惩罚（稳定性）
        flow_id = getattr(flow_request, 'flow_id', None)
        if flow_id and flow_id in self.route_history:
            old_route, _ = self.route_history[flow_id]
            if self._calculate_path_similarity(path, old_route) < 0.8:
                reward -= self.path_change_penalty * 5.0
        
        # 6. 定位质量奖励（lambda_pos权重）
        positioning_score = self._evaluate_positioning_quality(path, network_state)
        positioning_reward = positioning_score * self.lambda_pos * 10.0
        reward += positioning_reward
        
        # 7. Beam Hint 软约束（基于几何多样性与链路质量的近似评分）
        beam_hint_score = self._evaluate_beam_hint(path, network_state)
        reward += self.beam_hint_weight * beam_hint_score * 10.0

        # 8. 到达目标奖励
        if len(path) >= 2:
            reward += 20.0  # 基础到达奖励

        return reward
    
    def _count_seam_crossings(self, path: List[int], network_state: NetworkState) -> int:
        """计算路径中的跨缝次数"""
        # 简化实现：检查卫星是否在不同轨道平面
        seam_count = 0
        for i in range(len(path) - 1):
            sat1 = next((s for s in network_state.satellites if s['id'] == path[i]), None)
            sat2 = next((s for s in network_state.satellites if s['id'] == path[i+1]), None)
            if sat1 and sat2:
                # 检查是否跨越轨道平面（简化：用经度差判断）
                lon_diff = abs(sat1.get('lon', 0) - sat2.get('lon', 0))
                if lon_diff > 30:  # 超过30度认为是跨缝
                    seam_count += 1
        return seam_count
    
    def _calculate_path_similarity(self, path1: List[int], path2: List[int]) -> float:
        """计算两条路径的相似度"""
        if not path1 or not path2:
            return 0.0
        common_nodes = set(path1) & set(path2)
        return len(common_nodes) / max(len(path1), len(path2))
    
    def _evaluate_positioning_quality(self, path: List[int], network_state: NetworkState) -> float:
        """评估路径的定位质量支持"""
        # 简化实现：基于路径上卫星的分布和可见性
        if len(path) < 2:
            return 0.0
        
        # 检查路径上的卫星是否提供良好的几何分布
        satellites = [s for s in network_state.satellites if s['id'] in path]
        if len(satellites) < self.min_coop_sats:
            return 0.0
        
        # 计算几何多样性（简化）
        lats = [s.get('lat', 0) for s in satellites]
        lons = [s.get('lon', 0) for s in satellites]
        
        lat_spread = max(lats) - min(lats) if lats else 0
        lon_spread = max(lons) - min(lons) if lons else 0
        
        # 归一化评分
        geometry_score = min(1.0, (lat_spread + lon_spread) / 180.0)
        
        return geometry_score
