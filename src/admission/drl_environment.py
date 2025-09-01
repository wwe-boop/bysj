"""
自定义Gym环境，用于DRL准入控制训练

将Hypatia仿真环境封装为与Gymnasium兼容的接口
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Optional

from src.core.config import SystemConfig
from src.core.state import NetworkState, UserRequest, PerformanceMetrics
from src.hypatia.hypatia_adapter import HypatiaAdapter
from src.simulation.simulation_engine import SimulationEngine
from src.admission.admission_controller import AdmissionDecision


class HypatiaAdmissionEnv(gym.Env):
    """
    Hypatia准入控制Gym环境
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, config: SystemConfig, simulation_engine: SimulationEngine):
        super(HypatiaAdmissionEnv, self).__init__()

        self.config = config
        self.sim_engine = simulation_engine
        self.hypatia_adapter: HypatiaAdapter = simulation_engine.hypatia_adapter

        # 状态空间
        state_dim = self.config.drl.state_dim
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32)

        # 动作空间 (5个离散动作)
        self.action_space = spaces.Discrete(self.config.drl.action_dim)

        self.current_request: Optional[UserRequest] = None
        self.current_network_state: Optional[NetworkState] = None
        self.current_perf_metrics: Optional[PerformanceMetrics] = None
        self.qoe_history = [] # 用于计算稳定性

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 重置仿真环境
        self.sim_engine.initialize()
        self.qoe_history = []
        
        # 获取初始状态
        system_state = self.sim_engine._get_current_system_state()
        self.current_network_state = system_state.network_state
        self.current_perf_metrics = system_state.performance_metrics
        
        # 生成一个初始请求
        self.current_request = self.sim_engine.traffic_generator.generate_requests(0.0, 1.0)[0]

        observation = self._get_observation(
            self.current_request, self.current_network_state, self.current_perf_metrics
        )
        info = self._get_info()

        return observation, info

    def step(self, action):
        # 1. 记录决策前状态
        state_before = self.sim_engine._get_current_system_state()
        
        # 2. 执行动作
        decision = self._action_to_decision(action)
        self.sim_engine._process_user_request(self.current_request, decision)

        # 3. 推进仿真
        self.sim_engine._simulation_step()
        
        # 4. 获取决策后状态
        state_after = self.sim_engine._get_current_system_state()
        self.current_network_state = state_after.network_state
        self.current_perf_metrics = state_after.performance_metrics
        self.qoe_history.append(state_after.performance_metrics.qoe_score)
        if len(self.qoe_history) > 100: # 维持最近100个记录
            self.qoe_history.pop(0)

        # 5. 计算奖励
        reward = self._calculate_reward(decision, state_before, state_after, self.current_request)

        # 6. 判断是否结束
        terminated = self.sim_engine.current_time >= self.sim_engine.duration
        truncated = False

        # 7. 生成下一个请求
        self.current_request = self.sim_engine.traffic_generator.generate_requests(
            self.sim_engine.current_time, self.sim_engine.time_step
        )[0]

        observation = self._get_observation(
            self.current_request, self.current_network_state, self.current_perf_metrics
        )
        info = self._get_info()

        return observation, reward, terminated, truncated, info

    def _get_observation(self, user_request, network_state, perf_metrics):
        """提取并拼接所有状态特征，形成最终的状态向量"""
        # 按照 design/algorithm_design.md 的定义构建状态
        
        # 1. 全局网络状态
        link_utils = list(network_state.link_utilization.values())
        mean_util = np.mean(link_utils) if link_utils else 0
        max_util = np.max(link_utils) if link_utils else 0
        std_util = np.std(link_utils) if link_utils else 0
        
        # TODO: 按流量类型划分 active_flows (EF/AF/BE)
        num_ef = len([f for f in network_state.active_flows if f.get('type') == 'EF'])
        num_af = len([f for f in network_state.active_flows if f.get('type') == 'AF'])
        num_be = len([f for f in network_state.active_flows if f.get('type') == 'BE'])

        # 2. QoE状态
        # TODO: 从 perf_metrics 中获取更详细的QoE
        qoe_ef = perf_metrics.qoe_score # 简化
        qoe_af = perf_metrics.qoe_score # 简化
        qoe_be = perf_metrics.qoe_score # 简化
        qos_violation_rate = perf_metrics.packet_loss_rate # 简化

        # 3. 新流量请求信息
        req_features = [
            user_request.bandwidth_mbps / 100.0,
            user_request.max_latency_ms / 1000.0,
            # 更多请求特征...
        ]

        # 4. 定位特征
        pos_metrics = self.sim_engine.current_positioning_metrics
        crlb_norm = np.mean(pos_metrics.crlb_values) if pos_metrics.crlb_values else 1.0
        gdop_norm = np.mean(pos_metrics.gdop_values) if pos_metrics.gdop_values else 10.0

        # 5. 路由与切换稳定性特征 (占位)
        handover_pred = 0.1
        seam_flag = 0.0

        # 拼接所有特征
        features = [
            mean_util, max_util, std_util, num_ef, num_af, num_be,
            qoe_ef, qoe_af, qoe_be, qos_violation_rate,
            crlb_norm / 10.0, gdop_norm / 10.0, # 归一化
            handover_pred, seam_flag
        ]
        features.extend(req_features)

        # 填充到固定维度
        current_dim = len(features)
        if current_dim < self.config.drl.state_dim:
            features.extend([0.0] * (self.config.drl.state_dim - current_dim))
        
        return np.array(features[:self.config.drl.state_dim], dtype=np.float32)

    def _get_info(self):
        return {
            "time_step": self.sim_engine.current_time,
            "request_id": self.current_request.request_id if self.current_request else -1,
        }
    
    def _calculate_reward(self, decision: AdmissionDecision, state_before: 'SystemState', 
                          state_after: 'SystemState', flow_info: UserRequest) -> float:
        """根据 design/algorithm_design.md 实现复合奖励函数"""
        
        # 1. QoE变化
        qoe_change = state_after.performance_metrics.qoe_score - state_before.performance_metrics.qoe_score

        # 2. 动作特定奖惩
        action_reward = 0
        if decision == AdmissionDecision.ACCEPT:
            action_reward = qoe_change
        elif decision == AdmissionDecision.REJECT:
            action_reward = 0.1  # 避免无脑拒绝的保守奖励
        elif decision == AdmissionDecision.DEGRADED_ACCEPT:
            action_reward = qoe_change * 0.8
        elif decision == AdmissionDecision.DELAYED_ACCEPT:
            # 简化：延迟惩罚
            action_reward = qoe_change * 0.9 - 0.1
        elif decision == AdmissionDecision.PARTIAL_ACCEPT:
            action_reward = qoe_change * 0.7
        
        # 3. 公平性奖励
        fairness_bonus = self._calculate_fairness_bonus(state_after)
        
        # 4. QoS违规惩罚
        # 简化：使用丢包率作为违规指标
        violation_penalty = state_after.performance_metrics.packet_loss_rate * (-10.0)

        # 5. 定位目标奖励
        pos_metrics = state_after.positioning_metrics
        crlb_norm = np.mean(pos_metrics.crlb_values)/10.0 if pos_metrics.crlb_values else 1.0
        gdop_norm = np.mean(pos_metrics.gdop_values)/10.0 if pos_metrics.gdop_values else 1.0
        pos_reward = (1.0 - crlb_norm) + (1.0 - gdop_norm)
        
        # 6. 网络效率奖励
        link_utils = list(state_after.network_state.link_utilization.values())
        efficiency_bonus = np.mean(link_utils) * 0.5 if link_utils else 0
        
        # 7. 长期稳定性奖励
        stability_bonus = self._calculate_stability_bonus()

        # 加权求和
        # TODO: 从配置中读取权重
        total_reward = (action_reward + 
                        0.2 * fairness_bonus + 
                        0.3 * pos_reward +
                        violation_penalty + 
                        0.2 * efficiency_bonus + 
                        0.1 * stability_bonus)

        return total_reward

    def _calculate_fairness_bonus(self, state: 'SystemState') -> float:
        # TODO: 需要按用户或类型区分的QoE列表
        qoe_values = [state.performance_metrics.qoe_score] * 3 # 简化
        if not qoe_values or len(qoe_values) == 0: return 0
        
        sum_qoe = sum(qoe_values)
        sum_sq_qoe = sum(x**2 for x in qoe_values)
        
        if sum_sq_qoe == 0: return 1.0
        
        fairness_index = (sum_qoe ** 2) / (len(qoe_values) * sum_sq_qoe)
        return fairness_index

    def _calculate_stability_bonus(self) -> float:
        if len(self.qoe_history) < 10:
            return 0.0
        qoe_variance = np.var(self.qoe_history[-10:])
        stability_bonus = max(0, 1.0 - qoe_variance) # 方差越小，奖励越高
        return stability_bonus

    def _action_to_decision(self, action: int) -> AdmissionDecision:
        action_map = {
            0: AdmissionDecision.ACCEPT,
            1: AdmissionDecision.REJECT,
            2: AdmissionDecision.DEGRADED_ACCEPT,
            3: AdmissionDecision.DELAYED_ACCEPT,
            4: AdmissionDecision.PARTIAL_ACCEPT
        }
        return action_map.get(action, AdmissionDecision.REJECT)

    def render(self, mode='human'):
        # 简单的文本渲染
        print(f"Time: {self.sim_engine.current_time}, Request: {self.current_request.request_id if self.current_request else None}")

    def close(self):
        print("Closing Hypatia Admission Environment.")
