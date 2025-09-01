"""
系统状态数据结构定义

定义了网络状态、流量请求、决策、分配结果等核心数据结构。
使用dataclass确保类型安全和序列化支持。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np


class FlowType(Enum):
    """流量类型"""
    VOICE = "voice"
    VIDEO = "video"
    DATA = "data"
    EMERGENCY = "emergency"


class QoSClass(Enum):
    """QoS等级"""
    BEST_EFFORT = "best_effort"
    ASSURED = "assured"
    PREMIUM = "premium"
    CRITICAL = "critical"


class ActionType(Enum):
    """DRL动作类型"""
    ACCEPT = "accept"
    REJECT = "reject"
    DEGRADED_ACCEPT = "degraded_accept"
    DELAYED_ACCEPT = "delayed_accept"
    PARTIAL_ACCEPT = "partial_accept"


@dataclass
class UserRequest:
    """用户请求"""
    user_id: str
    service_type: str  # "voice", "video", "data", "navigation", "emergency", "location_based"
    bandwidth_mbps: float
    max_latency_ms: float
    min_reliability: float  # 0-1
    priority: int  # 1-10, 10为最高优先级
    user_lat: float
    user_lon: float
    duration_seconds: float
    timestamp: float = 0.0
    qos_class: str = "best_effort"

    def to_flow_request(self, flow_id: str, destination: Tuple[float, float]) -> 'FlowRequest':
        """转换为FlowRequest"""
        flow_type_map = {
            'voice': FlowType.VOICE,
            'video': FlowType.VIDEO,
            'data': FlowType.DATA,
            'emergency': FlowType.EMERGENCY
        }

        qos_class_map = {
            'best_effort': QoSClass.BEST_EFFORT,
            'assured': QoSClass.ASSURED,
            'premium': QoSClass.PREMIUM,
            'critical': QoSClass.CRITICAL
        }

        return FlowRequest(
            flow_id=flow_id,
            source=(self.user_lat, self.user_lon),
            destination=destination,
            flow_type=flow_type_map.get(self.service_type, FlowType.DATA),
            qos_class=qos_class_map.get(self.qos_class, QoSClass.BEST_EFFORT),
            bandwidth_requirement=self.bandwidth_mbps,
            latency_requirement=self.max_latency_ms,
            reliability_requirement=self.min_reliability,
            duration=self.duration_seconds,
            priority=self.priority,
            arrival_time=self.timestamp
        )


@dataclass
class FlowRequest:
    """流量请求"""
    flow_id: str
    source: Tuple[float, float]  # (lat, lon)
    destination: Tuple[float, float]  # (lat, lon)
    flow_type: FlowType
    qos_class: QoSClass
    bandwidth_requirement: float  # Mbps
    latency_requirement: float  # ms
    reliability_requirement: float  # 0-1
    duration: float  # seconds
    arrival_time: float
    priority: int = 1
    positioning_required: bool = False  # 是否需要定位服务


@dataclass
class NetworkState:
    """网络状态"""
    time_step: float
    satellites: List[Dict[str, Any]]  # 卫星位置、状态等
    links: List[Dict[str, Any]]  # 链路状态、容量、利用率等
    topology: np.ndarray  # 邻接矩阵
    link_utilization: Dict[Tuple[int, int], float]  # 链路利用率
    link_capacity: Dict[Tuple[int, int], float]  # 链路容量
    active_flows: List[FlowRequest]  # 当前活跃流量
    queue_lengths: Dict[int, float]  # 节点队列长度


@dataclass
class PositioningMetrics:
    """定位相关指标"""
    time_step: float
    user_locations: List[Tuple[float, float]]
    crlb_values: List[float]  # 每个用户的CRLB
    gdop_values: List[float]  # 每个用户的GDOP
    visible_satellites_count: List[int]  # 每个用户可见卫星数
    average_sinr: List[float]  # 每个用户的平均SINR
    positioning_accuracy: List[float]  # 定位精度估计
    coverage_quality: float  # 整体覆盖质量 0-1


@dataclass
class Decision:
    """DRL决策结果"""
    action: ActionType
    confidence: float  # 决策置信度
    flow_id: str
    modified_requirements: Optional[Dict[str, Any]] = None  # 降级后的需求
    delay_time: Optional[float] = None  # 延迟时间
    partial_bandwidth: Optional[float] = None  # 部分带宽


@dataclass
class AllocationResult:
    """资源分配结果"""
    flow_id: str
    route: List[int]  # 路由路径（卫星ID序列）
    allocated_bandwidth: float
    expected_latency: float
    expected_reliability: float
    allocation_success: bool
    allocation_time: float
    resource_cost: float  # 资源消耗成本


@dataclass
class PerformanceMetrics:
    """性能指标"""
    time_step: float
    # QoE指标
    average_throughput: float
    average_latency: float
    packet_loss_rate: float
    jitter: float
    
    # 定位质量指标
    average_positioning_accuracy: float
    positioning_coverage: float
    average_gdop: float
    average_crlb: float
    
    # 系统指标
    admission_rate: float
    resource_utilization: float
    energy_consumption: float
    
    # 联合优化指标
    qoe_score: float  # 综合QoE评分
    positioning_score: float  # 定位质量评分
    joint_objective: float  # 联合目标函数值


@dataclass
class SystemState:
    """完整系统状态"""
    network_state: NetworkState
    positioning_metrics: PositioningMetrics
    performance_metrics: PerformanceMetrics
    pending_requests: List[FlowRequest] = field(default_factory=list)
    recent_decisions: List[Decision] = field(default_factory=list)
    recent_allocations: List[AllocationResult] = field(default_factory=list)
