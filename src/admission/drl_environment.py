"""
自定义Gym环境，用于DRL准入控制训练

将Hypatia仿真环境封装为与Gymnasium兼容的接口
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Optional

from src.core.config import SystemConfig
from src.core.state import NetworkState, UserRequest, PerformanceMetrics, SystemState
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
        self.fairness_history = {} # 用于计算公平性
        self.last_admission_time = 0.0 # 用于计算时间维度信息

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 重置仿真环境
        self.sim_engine.initialize()
        self.qoe_history = []
        self.fairness_history = {}
        self.last_admission_time = 0.0
        
        # 获取初始状态
        system_state = self.sim_engine._get_current_system_state()
        self.current_network_state = system_state.network_state
        self.current_perf_metrics = system_state.performance_metrics
        
        # 生成一个初始请求
        self.current_request = self.sim_engine.traffic_generator.generate_requests(0.0, 1.0)[0]

        observation = self._get_observation(
            self.current_request, 
            self.current_network_state, 
            perf_metrics=self.current_perf_metrics,
            positioning_metrics=self.sim_engine.current_positioning_metrics
        )
        info = self._get_info()

        return observation, info

    def step(self, action):
        # 1. 记录决策前状态
        state_before = self.sim_engine._get_current_system_state()
        
        # 2. 执行动作
        decision = self._action_to_decision(action)
        self.sim_engine._process_user_request(self.current_request, decision)
        self.last_admission_time = self.sim_engine.current_time

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
            self.current_request, 
            self.current_network_state, 
            perf_metrics=self.current_perf_metrics,
            positioning_metrics=self.sim_engine.current_positioning_metrics
        )
        info = self._get_info()

        return observation, reward, terminated, truncated, info

    def _get_observation(self, 
                         user_request: UserRequest, 
                         network_state: NetworkState, 
                         perf_metrics: Optional[PerformanceMetrics] = None,
                         positioning_metrics: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """
        提取并拼接所有状态特征，形成最终的状态向量
        严格按照 design/algorithm_design.md 和 docs/04_admission_drl.md 的定义构建
        """
        # 0. 默认值
        perf_metrics = perf_metrics or self.current_perf_metrics
        positioning_metrics = positioning_metrics or self.sim_engine.current_positioning_metrics

        # 1. 全局网络状态
        link_utils = list(network_state.link_utilization.values())
        mean_util = np.mean(link_utils) if link_utils else 0
        max_util = np.max(link_utils) if link_utils else 0
        std_util = np.std(link_utils) if link_utils else 0
        
        num_ef = len([f for f in network_state.active_flows if f.get('service_type') == 'EF'])
        num_af = len([f for f in network_state.active_flows if f.get('service_type') == 'AF'])
        num_be = len([f for f in network_state.active_flows if f.get('service_type') == 'BE'])

        # 2. QoE状态
        qoe_stats = perf_metrics.get_qoe_stats()
        qoe_ef = qoe_stats.get('EF', {}).get('avg', 0)
        qoe_af = qoe_stats.get('AF', {}).get('avg', 0)
        qoe_be = qoe_stats.get('BE', {}).get('avg', 0)
        qos_violation_rate = perf_metrics.qos_violation_rate

        # 3. 时间维度信息
        orbit_phase = self.hypatia_adapter.get_orbit_phase() # 假设适配器提供
        topology_change_rate = self.hypatia_adapter.get_topology_change_rate()
        future_capacity = self.hypatia_adapter.predict_future_capacity(300)
        time_since_last_admission = self.sim_engine.current_time - self.last_admission_time
        
        # 4. 新流量请求信息
        req_features = [
            user_request.service_type_encoded,
            user_request.bandwidth_mbps / 100.0, # 归一化
            user_request.max_latency_ms / 1000.0, # 归一化
            user_request.expected_duration_s / 3600.0, # 归一化
            *user_request.src_pos_normalized,
            *user_request.dst_pos_normalized,
        ]

        # 5. 定位质量特征 (直接使用归一化指标)
        pos_metrics = positioning_metrics or {}
        pos_features = [
            pos_metrics.get('crlb_norm', 1.0),
            pos_metrics.get('gdop_norm', 1.0),
            pos_metrics.get('mean_sinr_norm', 0.0),
            pos_metrics.get('visible_beams_cnt_norm', 0.0),
            pos_metrics.get('coop_sat_cnt_norm', 0.0)
        ]

        # 6. 路由与切换稳定性特征 (从hypatia获取，若无则为占位)
        stability_metrics = self.hypatia_adapter.get_routing_stability_metrics(user_request)
        stability_features = [
            stability_metrics.get('handover_pred_count_norm', 0.0),
            stability_metrics.get('earliest_handover_norm', 1.0),
            stability_metrics.get('seam_flag', 0.0),
            stability_metrics.get('contact_margin_norm', 1.0)
        ]

        # 7. 历史与趋势特征
        qoe_trend = np.mean(self.qoe_history[-10:]) - np.mean(self.qoe_history[-20:-10]) if len(self.qoe_history) >= 20 else 0
        admission_rate_history = self.sim_engine.admission_controller.get_admission_rate()

        # 拼接所有特征
        features = [
            # 全局
            mean_util, max_util, std_util, num_ef, num_af, num_be,
            # QoE
            qoe_ef, qoe_af, qoe_be, qos_violation_rate,
            # 时间
            orbit_phase, topology_change_rate, future_capacity, time_since_last_admission,
            # 历史
            admission_rate_history, qoe_trend,
        ]
        features.extend(req_features)
        features.extend(pos_features)
        features.extend(stability_features)

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
        """
        根据 design/algorithm_design.md 实现奖励函数
        r_t = w1*ΔQoE + w2*Fair + w3*Eff + w4*Apos - w5*Viol - w6*DelayPen
        """
        # 使用设计文档中的默认权重（algorithm_design.md 第228行）
        default_weights = {
            'qoe': 1.0,          # w1 - QoE增量
            'fairness': 0.2,     # w2 - 公平性  
            'efficiency': 0.2,   # w3 - 资源利用
            'positioning': 0.3,  # w4 - 定位可用性（lambda_pos）
            'violation': 0.8,    # w5 - 违规惩罚
            'delay': 0.3,        # w6 - 延迟惩罚
            'stability': 0.2     # 额外：稳定性
        }
        weights = getattr(self.config.drl, 'reward_weights', default_weights)
        
        # 1. QoE变化奖励 (w1*ΔQoE)
        qoe_change = state_after.performance_metrics.qoe_score - state_before.performance_metrics.qoe_score
        
        # 根据动作类型调整（algorithm_design.md 第144-155行）
        if decision == AdmissionDecision.ACCEPT:
            action_modifier = 1.0
        elif decision == AdmissionDecision.REJECT:
            qoe_change = 0.1  # 保守奖励，避免无脑拒绝
            action_modifier = 1.0
        elif decision == AdmissionDecision.DEGRADED_ACCEPT:
            action_modifier = 0.8  # 降级惩罚
        elif decision == AdmissionDecision.DELAYED_ACCEPT:
            action_modifier = 0.9  # 延迟惩罚
        elif decision == AdmissionDecision.PARTIAL_ACCEPT:
            action_modifier = 0.7  # 部分接受惩罚
        else:
            action_modifier = 1.0
            
        qoe_reward = qoe_change * action_modifier

        # 2. 公平性奖励 (w2*Fair) - Jain公平性指数
        self._update_fairness_history(state_after)
        fairness_reward = self._calculate_jain_fairness() * 2.0  # 公平性权重

        # 3. 网络效率奖励 (w3*Eff)
        link_utils = list(state_after.network_state.link_utilization.values())
        network_utilization = np.mean(link_utils) if link_utils else 0
        efficiency_reward = network_utilization * 0.5
        
        # 4. 定位可用性奖励 (w4*Apos) - 优先使用Apos指标
        pos_metrics = getattr(state_after, 'positioning_metrics', {})
        if isinstance(pos_metrics, dict):
            # 按设计文档：优先使用Apos
            apos = pos_metrics.get('Apos', pos_metrics.get('pos_availability'))
            if apos is not None:
                positioning_reward = float(apos)
            else:
                # 回退到CRLB和GDOP组合（algorithm_design.md 第167-169行）
                crlb_norm = pos_metrics.get('crlb_norm', 1.0)
                gdop_norm = pos_metrics.get('gdop_norm', 1.0)
                positioning_reward = (1.0 - crlb_norm) + (1.0 - gdop_norm)
        else:
            positioning_reward = 0.0
        
        # 5. QoS违规惩罚 (w5*Viol)
        violation_penalty = state_after.performance_metrics.qos_violation_rate * 10.0
        
        # 6. 延迟惩罚 (w6*DelayPen) - 仅对DELAYED_ACCEPT
        delay_penalty = 0.0
        if decision == AdmissionDecision.DELAYED_ACCEPT:
            delay_penalty = self._calculate_delay_penalty(flow_info)
        
        # 7. 长期稳定性奖励（额外）
        stability_bonus = self._calculate_stability_bonus()
        
        # 加权求和
        total_reward = (
            weights.get('qoe', default_weights['qoe']) * qoe_reward +
            weights.get('fairness', default_weights['fairness']) * fairness_reward +
            weights.get('efficiency', default_weights['efficiency']) * efficiency_reward +
            weights.get('positioning', default_weights['positioning']) * positioning_reward -
            weights.get('violation', default_weights['violation']) * violation_penalty -
            weights.get('delay', default_weights['delay']) * delay_penalty +
            weights.get('stability', default_weights['stability']) * stability_bonus
        )

        return total_reward
    
    def _calculate_delay_penalty(self, flow_info: UserRequest) -> float:
        """计算延迟惩罚（基于流量类型）"""
        if flow_info.service_type == 'EF':  # EF对延迟最敏感
            return 5.0
        elif flow_info.service_type == 'AF':
            return 2.0
        else:  # BE
            return 1.0

    def _update_fairness_history(self, state: 'SystemState'):
        """更新用于计算公平性的历史数据"""
        # 假设 perf_metrics 能提供按服务类型的QoE
        qoe_per_type = state.performance_metrics.get_qoe_per_service_type()
        for service_type, qoe in qoe_per_type.items():
            if service_type not in self.fairness_history:
                self.fairness_history[service_type] = []
            self.fairness_history[service_type].append(qoe)
            # 维持一个滑动窗口
            if len(self.fairness_history[service_type]) > 50:
                self.fairness_history[service_type].pop(0)

    def _calculate_jain_fairness(self) -> float:
        """使用Jain's Fairness Index计算公平性奖励"""
        avg_qoe_per_type = []
        for service_type, qoe_list in self.fairness_history.items():
            if qoe_list:
                avg_qoe_per_type.append(np.mean(qoe_list))
        
        if not avg_qoe_per_type:
            return 0.0
        
        num_classes = len(avg_qoe_per_type)
        sum_qoe = sum(avg_qoe_per_type)
        sum_sq_qoe = sum(x**2 for x in avg_qoe_per_type)
        
        if sum_sq_qoe == 0:
            return 1.0 # 完美公平
        
        fairness_index = (sum_qoe ** 2) / (num_classes * sum_sq_qoe)
        return fairness_index

    def _calculate_stability_bonus(self) -> float:
        """计算长期稳定性奖励 (QoE方差的倒数)"""
        if len(self.qoe_history) < 20: # 需要足够数据点
            return 0.0
        qoe_variance = np.var(self.qoe_history[-20:])
        # 方差越小，奖励越高，避免除以零
        stability_bonus = 1.0 / (1.0 + qoe_variance)
        return stability_bonus

    def _evaluate_positioning_quality(self, positioning_metrics: Dict[str, Any]) -> Dict[str, float]:
        """评估定位质量，逻辑源自 positioning_aware_admission.py"""
        quality_metrics = {
            'satellite_visibility': 0.0, 'gdop_quality': 0.0, 
            'positioning_accuracy': 0.0, 'signal_strength': 0.0,
            'geometry_distribution': 0.0, 'overall_quality': 0.0
        }
        if not positioning_metrics:
            return quality_metrics

        # 1. 可见卫星数量评分
        visible_satellites = positioning_metrics.get('visible_satellites', [])
        visible_count = len(visible_satellites)
        if visible_count >= 4:
            quality_metrics['satellite_visibility'] = min(1.0, visible_count / 10.0)

        # 2. GDOP评分
        gdop = positioning_metrics.get('gdop', float('inf'))
        if gdop > 0 and gdop != float('inf'):
            quality_metrics['gdop_quality'] = max(0.0, 1.0 - (gdop - 1.0) / 10.0)

        # 3. 定位精度评分
        accuracy = positioning_metrics.get('positioning_accuracy', 0.0)
        quality_metrics['positioning_accuracy'] = max(0.0, accuracy)

        # 4. 信号强度评分
        if visible_satellites:
            signals = [s.get('signal_strength_dbm', -140) for s in visible_satellites]
            avg_signal = np.mean(signals)
            quality_metrics['signal_strength'] = max(0.0, min(1.0, (avg_signal + 140) / 60.0))

        # 5. 几何分布评分
        if visible_count >= 4:
            elevations = [s.get('elevation', 0) for s in visible_satellites]
            quality_metrics['geometry_distribution'] = min(1.0, np.std(elevations) / 45.0)

        # 6. 综合评分
        weights = self.config.admission.positioning_quality_weights
        overall_quality = (quality_metrics['satellite_visibility'] * weights.visibility +
                           quality_metrics['gdop_quality'] * weights.gdop +
                           quality_metrics['positioning_accuracy'] * weights.accuracy +
                           quality_metrics['signal_strength'] * weights.signal +
                           quality_metrics['geometry_distribution'] * weights.geometry)
        quality_metrics['overall_quality'] = overall_quality
        
        return quality_metrics

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
