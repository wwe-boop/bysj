"""
系统核心接口定义

定义了Hypatia、DRL、DSROQ等组件的抽象接口，
确保模块间的松耦合和可测试性。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from .state import NetworkState, FlowRequest, Decision, AllocationResult, PositioningMetrics


class AdmissionInterface(ABC):
    """准入控制接口"""

    @abstractmethod
    def make_admission_decision(self, user_request: 'UserRequest', network_state: NetworkState,
                              positioning_metrics: Optional[Dict[str, Any]] = None) -> 'AdmissionResult':
        """做出准入决策"""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass

    @abstractmethod
    def reset_statistics(self) -> None:
        """重置统计信息"""
        pass


class DSROQInterface(ABC):
    """DSROQ资源分配接口"""

    @abstractmethod
    def process_user_request(self, user_request: 'UserRequest', network_state: NetworkState) -> Optional['AllocationResult']:
        """处理用户请求，返回资源分配结果"""
        pass

    @abstractmethod
    def find_route(self, flow_request: 'FlowRequest', network_state: NetworkState) -> Optional[List[int]]:
        """找到最优路由"""
        pass

    @abstractmethod
    def allocate_bandwidth(self, flow_request: 'FlowRequest', route: List[int], network_state: NetworkState) -> float:
        """分配带宽"""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass


class HypatiaInterface(ABC):
    """Hypatia框架集成接口"""
    
    @abstractmethod
    def initialize(self, constellation_config: Dict[str, Any]) -> None:
        """初始化卫星星座配置"""
        pass
    
    @abstractmethod
    def get_network_state(self, time_step: float) -> NetworkState:
        """获取当前时刻的网络状态"""
        pass
    
    @abstractmethod
    def get_positioning_metrics(self, time_step: float, user_locations: List[Tuple[float, float]]) -> PositioningMetrics:
        """获取定位相关指标（CRLB、GDOP等）"""
        pass
    
    @abstractmethod
    def execute_flow_allocation(self, flow: FlowRequest, route: List[int], bandwidth: float) -> bool:
        """执行流量分配到网络"""
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取当前性能指标（延迟、吞吐量、丢包率等）"""
        pass
    
    @abstractmethod
    def step_simulation(self, time_step: float) -> None:
        """推进仿真一个时间步"""
        pass


class DRLInterface(ABC):
    """深度强化学习接口"""
    
    @abstractmethod
    def predict(self, state: np.ndarray) -> Decision:
        """根据状态预测动作"""
        pass
    
    @abstractmethod
    def learn(self, experiences: List[Tuple[np.ndarray, Decision, float, np.ndarray, bool]]) -> Dict[str, float]:
        """从经验中学习，返回训练指标"""
        pass
    
    @abstractmethod
    def save_model(self, path: str) -> None:
        """保存模型"""
        pass
    
    @abstractmethod
    def load_model(self, path: str) -> None:
        """加载模型"""
        pass
    
    @abstractmethod
    def get_state_vector(self, network_state: NetworkState, positioning_metrics: PositioningMetrics, 
                        flow_request: FlowRequest, current_flows: List[FlowRequest]) -> np.ndarray:
        """构建DRL状态向量"""
        pass


class DSROQInterface(ABC):
    """DSROQ资源分配接口"""
    
    @abstractmethod
    def find_route(self, flow_request: FlowRequest, network_state: NetworkState) -> Optional[List[int]]:
        """使用MCTS找到最优路由"""
        pass
    
    @abstractmethod
    def allocate_bandwidth(self, flow_request: FlowRequest, route: List[int], 
                          network_state: NetworkState) -> float:
        """使用李雅普诺夫优化分配带宽"""
        pass
    
    @abstractmethod
    def process_admission_decision(self, decision: Decision, flow_request: FlowRequest, 
                                 network_state: NetworkState) -> Optional[AllocationResult]:
        """处理准入决策，返回资源分配结果"""
        pass
    
    @abstractmethod
    def update_queue_states(self, network_state: NetworkState) -> None:
        """更新队列状态用于李雅普诺夫优化"""
        pass


class PositioningInterface(ABC):
    """定位模块接口"""
    
    @abstractmethod
    def calculate_crlb(self, user_location: Tuple[float, float], 
                      visible_satellites: List[Dict[str, Any]]) -> float:
        """计算克拉美-罗下界（CRLB）"""
        pass
    
    @abstractmethod
    def calculate_gdop(self, user_location: Tuple[float, float], 
                      visible_satellites: List[Dict[str, Any]]) -> float:
        """计算几何精度因子（GDOP）"""
        pass
    
    @abstractmethod
    def get_visible_satellites(self, user_location: Tuple[float, float], 
                             time_step: float, network_state: NetworkState) -> List[Dict[str, Any]]:
        """获取用户可见的卫星列表"""
        pass
    
    @abstractmethod
    def calculate_positioning_quality(self, user_locations: List[Tuple[float, float]], 
                                    network_state: NetworkState, time_step: float) -> PositioningMetrics:
        """计算整体定位质量指标"""
        pass
