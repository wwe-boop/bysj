"""
DSROQ 核心组件
"""
from typing import Dict, Any, List

# 假设的 state 和 config 导入
try:
    from src.core.state import FlowRequest
    from src.core.config import DSROQConfig
except ImportError:
    # 简单的占位符类，用于独立测试
    class FlowRequest: pass
    class DSROQConfig: pass


class LyapunovScheduler:
    """
    李雅普诺夫调度器
    根据 design/algorithm_design.md 中的伪代码实现
    """

    def __init__(self, config: DSROQConfig):
        """
        初始化李雅普诺夫调度器
        :param config: DSROQ 配置
        """
        self.V = getattr(config, 'lyapunov_weight', 1.0)  # 李雅普诺夫参数
        self.queue_states: Dict[int, float] = {}  # 队列状态 {node_id: queue_length}
        
        # 设计文档中的调度参数 (algorithm_design.md 第483-485行)
        self.queue_backlog_limit = getattr(config, 'queue_backlog_limit', 100.0)  # 队列积压告警阈值
        self.lambda_pos = getattr(config, 'lambda_pos', 0.2)  # 定位质量权重

    def schedule_flow(self, flow_request: FlowRequest, route: List[int]) -> Dict[str, Any]:
        """
        为单个流进行调度
        :param flow_request: 流量请求
        :param route: 路由路径
        :return: 调度决策
        """
        # 1. 更新此流可能影响的队列状态
        self._update_queue_states(flow_request, route)

        # 2. 计算李雅普诺夫漂移+惩罚
        drift_plus_penalty = self._calculate_drift_plus_penalty(flow_request, route)

        # 3. 基于漂移最小化做出调度决策（简化）
        # 在一个更完整的实现中，这里会决定速率、优先级等
        scheduling_decision = self._make_scheduling_decision(drift_plus_penalty)

        return scheduling_decision

    def _update_queue_states(self, flow_request: FlowRequest, route: List[int]):
        """
        （简化）更新队列状态。
        在真实实现中，这将由网络监控模块驱动。
        这里我们只做简单模拟。
        """
        arrival_rate = getattr(flow_request, 'bandwidth_requirement', 0)
        for node in route:
            if node not in self.queue_states:
                self.queue_states[node] = 0
            # 简单地增加队列长度，实际应考虑服务速率
            self.queue_states[node] += arrival_rate * 0.1 

    def _calculate_drift_plus_penalty(self, flow_request: FlowRequest, route: List[int]) -> float:
        """
        计算李雅普诺夫漂移+惩罚
        """
        drift = 0.0
        
        # 估算漂移
        for node in route:
            queue_length = self.queue_states.get(node, 0.0)
            arrival_rate = self._get_arrival_rate(node, flow_request)
            service_rate = self._get_service_rate(node)
            # 漂移计算: E[Q(t+1)^2 - Q(t)^2] 的近似
            drift += queue_length * (arrival_rate - service_rate)

        # 计算QoE惩罚
        penalty = self.V * self._calculate_qoe_penalty(flow_request, route)

        return drift + penalty

    def _get_arrival_rate(self, node: int, flow_request: FlowRequest) -> float:
        """获取节点的到达速率（简化）"""
        return getattr(flow_request, 'bandwidth_requirement', 0)

    def _get_service_rate(self, node: int) -> float:
        """获取节点的服务速率（简化）"""
        # 假设一个固定的服务速率
        return 50.0

    def _calculate_qoe_penalty(self, flow_request: FlowRequest, route: List[int]) -> float:
        """
        计算QoE惩罚项（包含定位退化代价）
        根据 algorithm_design.md 第443-458行的定义
        """
        penalty = 0.0
        flow_type = getattr(flow_request, 'qos_class', 'BE')
        
        # 基于流量类型的QoE惩罚
        if flow_type == 'EF':  # EF流量对延迟敏感
            path_delay = self._calculate_path_delay(route)
            max_latency = getattr(flow_request, 'latency_requirement', 100)
            penalty = max(0, path_delay - max_latency)
        elif flow_type == 'AF':  # AF流量对丢包敏感
            path_loss_rate = self._calculate_path_loss_rate(route)
            penalty = path_loss_rate * 10
        else:  # BE流量对吞吐量敏感
            path_throughput = self._calculate_path_throughput(route)
            min_bandwidth = getattr(flow_request, 'bandwidth_requirement', 1)
            penalty = max(0, min_bandwidth - path_throughput)
        
        # 加入定位退化代价（设计文档扩展）
        positioning_penalty = self._calculate_positioning_penalty(route)
        penalty += self.lambda_pos * positioning_penalty
        
        return penalty
    
    def _calculate_positioning_penalty(self, route: List[int]) -> float:
        """计算定位质量退化的惩罚"""
        # 简化实现：路径越长，定位质量可能越差
        if len(route) <= 2:
            return 0.0
        
        # 基于路径长度和跨度估算定位惩罚
        hop_penalty = (len(route) - 2) * 0.5  # 每增加一跳增加0.5惩罚
        
        # 如果路径过长，可能影响协作定位
        if len(route) > 6:
            hop_penalty *= 1.5  # 额外惩罚
        
        return hop_penalty

    def _calculate_path_delay(self, route: List[int]) -> float:
        """计算路径延迟（简化）"""
        # 假设每跳有固定延迟
        return len(route) * 10.0  # ms

    def _calculate_path_loss_rate(self, route: List[int]) -> float:
        """计算路径丢包率（简化）"""
        # 假设每跳有固定丢包率
        return 1.0 - (0.999 ** len(route))

    def _calculate_path_throughput(self, route: List[int]) -> float:
        """计算路径吞吐量（简化）"""
        # 假设路径吞吐量等于瓶颈链路容量
        return 50.0 # Mbps

    def _make_scheduling_decision(self, drift_plus_penalty: float) -> Dict[str, Any]:
        """
        基于漂移值做出调度决策（增强版）
        考虑队列稳定性和定位质量保持
        """
        # 检查队列积压状态
        max_queue_length = max(self.queue_states.values()) if self.queue_states else 0
        is_congested = max_queue_length > self.queue_backlog_limit
        
        # 根据漂移和拥塞状态决定调度策略
        if drift_plus_penalty > 1000 or is_congested:
            # 严重拥塞，需要保守策略
            return {
                "priority": 1,
                "rate_limit_mbps": 20.0,
                "scheduling_mode": "conservative",
                "queue_management": "drop_tail"  # 可能需要丢弃尾部数据包
            }
        elif drift_plus_penalty > 500:
            # 中等负载，平衡策略
            return {
                "priority": 5,
                "rate_limit_mbps": 40.0,
                "scheduling_mode": "balanced",
                "queue_management": "active_queue"  # 主动队列管理
            }
        else:
            # 轻负载，可以更激进
            return {
                "priority": 10,
                "rate_limit_mbps": 100.0,
                "scheduling_mode": "aggressive",
                "queue_management": "fair_queue"  # 公平队列
            }

    def get_queue_states(self) -> Dict[int, float]:
        """返回当前队列状态"""
        return self.queue_states
