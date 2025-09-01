"""
系统主流水线

实现"状态提取 → DRL决策 → DSROQ分配 → Hypatia执行"的完整流程。
支持实时决策和批量训练模式。
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from .interfaces import HypatiaInterface, DRLInterface, DSROQInterface, PositioningInterface
from .state import (
    SystemState, NetworkState, PositioningMetrics, FlowRequest, 
    Decision, AllocationResult, PerformanceMetrics, ActionType
)
from .config import SystemConfig


class SystemPipeline:
    """系统主流水线"""
    
    def __init__(
        self,
        hypatia: HypatiaInterface,
        drl_agent: DRLInterface,
        dsroq: DSROQInterface,
        positioning: PositioningInterface,
        config: SystemConfig
    ):
        self.hypatia = hypatia
        self.drl_agent = drl_agent
        self.dsroq = dsroq
        self.positioning = positioning
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        
        # 系统状态
        self.current_time = 0.0
        self.system_state: Optional[SystemState] = None
        self.experience_buffer: List[Tuple[np.ndarray, Decision, float, np.ndarray, bool]] = []
        
        # 性能统计
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.degraded_requests = 0
        
    def initialize(self) -> None:
        """初始化系统"""
        self.logger.info("初始化系统流水线...")
        
        # 初始化Hypatia
        constellation_config = self.config.constellation.__dict__
        self.hypatia.initialize(constellation_config)
        
        # 初始化系统状态
        self._update_system_state()
        
        self.logger.info("系统初始化完成")
    
    def step(self, new_requests: List[FlowRequest]) -> Dict[str, Any]:
        """执行一个时间步"""
        step_start_time = time.time()
        
        # 1. 更新系统状态
        self._update_system_state()
        
        # 2. 处理新的流量请求
        decisions = []
        allocations = []
        
        for request in new_requests:
            decision, allocation = self._process_flow_request(request)
            decisions.append(decision)
            if allocation:
                allocations.append(allocation)
        
        # 3. 推进仿真
        self.hypatia.step_simulation(self.config.simulation.time_step_seconds)
        self.current_time += self.config.simulation.time_step_seconds
        
        # 4. 更新DSROQ队列状态
        self.dsroq.update_queue_states(self.system_state.network_state)
        
        # 5. 计算性能指标
        performance_metrics = self._calculate_performance_metrics()
        
        # 6. 更新系统状态
        self.system_state.recent_decisions = decisions
        self.system_state.recent_allocations = allocations
        self.system_state.performance_metrics = performance_metrics
        
        step_time = time.time() - step_start_time
        
        return {
            'time_step': self.current_time,
            'decisions': decisions,
            'allocations': allocations,
            'performance_metrics': performance_metrics,
            'step_time': step_time
        }
    
    def _process_flow_request(self, request: FlowRequest) -> Tuple[Decision, Optional[AllocationResult]]:
        """处理单个流量请求"""
        self.total_requests += 1
        
        # 1. 构建DRL状态向量
        state_vector = self.drl_agent.get_state_vector(
            self.system_state.network_state,
            self.system_state.positioning_metrics,
            request,
            self.system_state.network_state.active_flows
        )
        
        # 2. DRL决策
        decision = self.drl_agent.predict(state_vector)
        decision.flow_id = request.flow_id
        
        # 3. 根据决策进行资源分配
        allocation = None
        if decision.action in [ActionType.ACCEPT, ActionType.DEGRADED_ACCEPT, ActionType.PARTIAL_ACCEPT]:
            allocation = self.dsroq.process_admission_decision(
                decision, request, self.system_state.network_state
            )
            
            if allocation and allocation.allocation_success:
                # 4. 执行流量分配
                success = self.hypatia.execute_flow_allocation(
                    request, allocation.route, allocation.allocated_bandwidth
                )
                
                if success:
                    self.accepted_requests += 1
                    if decision.action == ActionType.DEGRADED_ACCEPT:
                        self.degraded_requests += 1
                else:
                    # 分配失败，修改决策为拒绝
                    decision.action = ActionType.REJECT
                    allocation = None
                    self.rejected_requests += 1
            else:
                # 资源分配失败
                decision.action = ActionType.REJECT
                allocation = None
                self.rejected_requests += 1
        else:
            self.rejected_requests += 1
        
        return decision, allocation
    
    def _update_system_state(self) -> None:
        """更新系统状态"""
        # 获取网络状态
        network_state = self.hypatia.get_network_state(self.current_time)
        
        # 获取定位指标
        user_locations = self._get_current_user_locations()
        positioning_metrics = self.positioning.calculate_positioning_quality(
            user_locations, network_state, self.current_time
        )
        
        # 获取性能指标
        performance_metrics = self._calculate_performance_metrics()
        
        # 更新系统状态
        if self.system_state is None:
            self.system_state = SystemState(
                network_state=network_state,
                positioning_metrics=positioning_metrics,
                performance_metrics=performance_metrics
            )
        else:
            self.system_state.network_state = network_state
            self.system_state.positioning_metrics = positioning_metrics
            self.system_state.performance_metrics = performance_metrics
    
    def _get_current_user_locations(self) -> List[Tuple[float, float]]:
        """获取当前用户位置"""
        # TODO: 从配置或用户移动模型获取
        # 暂时返回固定位置
        locations = []
        for i in range(self.config.simulation.num_users):
            lat = 40.0 + (i % 10) * 0.1  # 简单的网格分布
            lon = -74.0 + (i // 10) * 0.1
            locations.append((lat, lon))
        return locations
    
    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """计算性能指标"""
        # 从Hypatia获取基础性能指标
        hypatia_metrics = self.hypatia.get_performance_metrics()
        
        # 计算准入率
        admission_rate = self.accepted_requests / max(self.total_requests, 1)
        
        # 计算联合目标函数
        qoe_score = self._calculate_qoe_score(hypatia_metrics)
        positioning_score = self._calculate_positioning_score()
        joint_objective = (
            self.config.qoe_weight * qoe_score + 
            self.config.positioning_weight * positioning_score
        )
        
        return PerformanceMetrics(
            time_step=self.current_time,
            average_throughput=hypatia_metrics.get('throughput', 0.0),
            average_latency=hypatia_metrics.get('latency', 0.0),
            packet_loss_rate=hypatia_metrics.get('packet_loss', 0.0),
            jitter=hypatia_metrics.get('jitter', 0.0),
            average_positioning_accuracy=np.mean(self.system_state.positioning_metrics.positioning_accuracy) if self.system_state else 0.0,
            positioning_coverage=self.system_state.positioning_metrics.coverage_quality if self.system_state else 0.0,
            average_gdop=np.mean(self.system_state.positioning_metrics.gdop_values) if self.system_state else 0.0,
            average_crlb=np.mean(self.system_state.positioning_metrics.crlb_values) if self.system_state else 0.0,
            admission_rate=admission_rate,
            resource_utilization=hypatia_metrics.get('utilization', 0.0),
            energy_consumption=hypatia_metrics.get('energy', 0.0),
            qoe_score=qoe_score,
            positioning_score=positioning_score,
            joint_objective=joint_objective
        )
    
    def _calculate_qoe_score(self, hypatia_metrics: Dict[str, float]) -> float:
        """计算QoE评分"""
        # 简化的QoE计算，基于延迟、吞吐量、丢包率
        latency = hypatia_metrics.get('latency', 100.0)  # ms
        throughput = hypatia_metrics.get('throughput', 10.0)  # Mbps
        packet_loss = hypatia_metrics.get('packet_loss', 0.01)  # 0-1
        
        # 归一化到0-1范围
        latency_score = max(0, 1 - latency / 500.0)  # 500ms为最差
        throughput_score = min(1, throughput / 100.0)  # 100Mbps为最佳
        loss_score = max(0, 1 - packet_loss / 0.1)  # 10%丢包为最差
        
        return (latency_score + throughput_score + loss_score) / 3.0
    
    def _calculate_positioning_score(self) -> float:
        """计算定位质量评分"""
        if not self.system_state or not self.system_state.positioning_metrics:
            return 0.0
        
        metrics = self.system_state.positioning_metrics
        
        # 基于CRLB、GDOP和覆盖质量计算
        crlb_score = 1.0 / (1.0 + np.mean(metrics.crlb_values))
        gdop_score = 1.0 / (1.0 + np.mean(metrics.gdop_values))
        coverage_score = metrics.coverage_quality
        
        return (
            self.config.positioning.crlb_weight * crlb_score +
            self.config.positioning.gdop_weight * gdop_score +
            self.config.positioning.coverage_weight * coverage_score
        )
    
    def train_step(self) -> Dict[str, float]:
        """执行一步DRL训练"""
        if len(self.experience_buffer) < self.config.drl.batch_size:
            return {}
        
        # 从经验缓冲区采样
        batch = self.experience_buffer[-self.config.drl.batch_size:]
        
        # 训练DRL智能体
        training_metrics = self.drl_agent.learn(batch)
        
        return training_metrics
    
    def add_experience(self, state: np.ndarray, decision: Decision, reward: float, 
                      next_state: np.ndarray, done: bool) -> None:
        """添加经验到缓冲区"""
        self.experience_buffer.append((state, decision, reward, next_state, done))
        
        # 限制缓冲区大小
        if len(self.experience_buffer) > self.config.drl.buffer_size:
            self.experience_buffer.pop(0)
    
    def get_system_state(self) -> SystemState:
        """获取当前系统状态"""
        return self.system_state
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            'total_requests': self.total_requests,
            'accepted_requests': self.accepted_requests,
            'rejected_requests': self.rejected_requests,
            'degraded_requests': self.degraded_requests,
            'admission_rate': self.accepted_requests / max(self.total_requests, 1),
            'degradation_rate': self.degraded_requests / max(self.accepted_requests, 1),
            'current_time': self.current_time
        }
