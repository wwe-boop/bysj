"""
基于深度强化学习的准入控制

实现使用PPO算法的智能准入控制策略
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging

from src.admission.admission_controller import AdmissionController, AdmissionResult, AdmissionDecision
from src.core.state import NetworkState, UserRequest

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.env_util import make_vec_env
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class AdmissionEnvironment:
    """准入控制环境（用于DRL训练）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dim = config.get('state_dim', 128)
        self.action_dim = config.get('action_dim', 5)
        
        # 状态空间：网络状态 + 用户请求 + 定位信息
        self.observation_space_size = self.state_dim
        
        # 动作空间：5种准入决策
        self.action_space_size = self.action_dim
        
        # 奖励权重
        self.qos_weight = config.get('qos_weight', 0.7)
        self.positioning_weight = config.get('positioning_weight', 0.3)
        
    def extract_state_features(self, 
                             user_request: UserRequest,
                             network_state: NetworkState,
                             positioning_metrics: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """提取状态特征"""
        features = []
        
        # 1. 用户请求特征 (10维)
        features.extend([
            user_request.bandwidth_mbps / 100.0,  # 归一化带宽
            user_request.max_latency_ms / 1000.0,  # 归一化延迟
            user_request.min_reliability,
            user_request.priority / 10.0,  # 归一化优先级
            user_request.user_lat / 90.0,  # 归一化纬度
            user_request.user_lon / 180.0,  # 归一化经度
            user_request.duration_seconds / 3600.0,  # 归一化持续时间
            float(user_request.service_type == 'voice'),
            float(user_request.service_type == 'video'),
            float(user_request.service_type == 'data')
        ])
        
        # 2. 网络状态特征 (50维)
        # 卫星负载统计
        satellite_loads = [self._calculate_satellite_load(sat['id'], network_state) 
                          for sat in network_state.satellites[:50]]  # 取前50颗卫星
        if len(satellite_loads) < 50:
            satellite_loads.extend([0.0] * (50 - len(satellite_loads)))
        features.extend(satellite_loads)
        
        # 3. 链路质量特征 (20维)
        link_qualities = []
        link_count = 0
        for (src, dst), utilization in network_state.link_utilization.items():
            if link_count >= 20:
                break
            link_qualities.append(1.0 - utilization)  # 质量 = 1 - 利用率
            link_count += 1
        
        if len(link_qualities) < 20:
            link_qualities.extend([0.0] * (20 - len(link_qualities)))
        features.extend(link_qualities)
        
        # 4. 定位相关特征 (20维)
        if positioning_metrics:
            # 可见卫星数量
            visible_count = len(positioning_metrics.get('visible_satellites', []))
            features.append(min(1.0, visible_count / 50.0))  # 归一化
            
            # 平均信号强度
            visible_sats = positioning_metrics.get('visible_satellites', [])
            if visible_sats:
                avg_signal = np.mean([sat.get('signal_strength_dbm', -120) 
                                    for sat in visible_sats])
                features.append((avg_signal + 140) / 20.0)  # 归一化到[0,1]
            else:
                features.append(0.0)
            
            # GDOP值
            gdop = positioning_metrics.get('gdop', float('inf'))
            if gdop != float('inf'):
                features.append(min(1.0, 1.0 / gdop))  # GDOP越小越好
            else:
                features.append(0.0)
            
            # 定位精度
            accuracy = positioning_metrics.get('positioning_accuracy', 0.0)
            features.append(accuracy)
            
            # 填充剩余维度
            features.extend([0.0] * 16)
        else:
            features.extend([0.0] * 20)
        
        # 5. 系统统计特征 (28维)
        # 总体负载
        total_load = np.mean([self._calculate_satellite_load(sat['id'], network_state) 
                             for sat in network_state.satellites])
        features.append(total_load)
        
        # 活跃流数量
        active_flows = len(network_state.active_flows)
        features.append(min(1.0, active_flows / 1000.0))  # 归一化
        
        # 填充到目标维度
        current_dim = len(features)
        if current_dim < self.state_dim:
            features.extend([0.0] * (self.state_dim - current_dim))
        elif current_dim > self.state_dim:
            features = features[:self.state_dim]
        
        return np.array(features, dtype=np.float32)
    
    def _calculate_satellite_load(self, satellite_id: int, network_state: NetworkState) -> float:
        """计算卫星负载"""
        queue_length = network_state.queue_lengths.get(satellite_id, 0.0)
        max_queue_length = 100.0
        return min(1.0, queue_length / max_queue_length)
    
    def calculate_reward(self, 
                        decision: AdmissionDecision,
                        user_request: UserRequest,
                        network_state: NetworkState,
                        positioning_metrics: Optional[Dict[str, Any]] = None) -> float:
        """计算奖励"""
        reward = 0.0
        
        if decision == AdmissionDecision.ACCEPT:
            # 接受奖励
            reward += 10.0
            
            # QoS满足奖励
            if positioning_metrics:
                positioning_quality = positioning_metrics.get('positioning_accuracy', 0.0)
                reward += positioning_quality * 5.0 * self.positioning_weight
            
            # 网络效率奖励
            avg_load = np.mean([self._calculate_satellite_load(sat['id'], network_state) 
                               for sat in network_state.satellites])
            reward += (1.0 - avg_load) * 3.0 * self.qos_weight
            
        elif decision == AdmissionDecision.DEGRADED_ACCEPT:
            # 降级接受奖励
            reward += 5.0
            
        elif decision == AdmissionDecision.REJECT:
            # 拒绝惩罚（如果网络有容量但拒绝）
            avg_load = np.mean([self._calculate_satellite_load(sat['id'], network_state) 
                               for sat in network_state.satellites])
            if avg_load < 0.8:  # 网络负载不高但拒绝
                reward -= 5.0
            else:
                reward += 1.0  # 合理拒绝
        
        return reward


class DRLAdmissionController(AdmissionController):
    """基于DRL的准入控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if not TORCH_AVAILABLE:
            raise ImportError("DRL准入控制需要PyTorch和stable-baselines3")
        
        self.drl_config = config
        self.environment = AdmissionEnvironment(config)
        
        # 模型参数
        self.model_path = config.get('model_path', 'models/admission_ppo.zip')
        self.training_mode = config.get('training_mode', False)
        
        # 初始化模型
        self.model = None
        self._initialize_model()
        
        # 探索参数
        self.epsilon = config.get('epsilon', 0.1)  # 探索率
        self.epsilon_decay = config.get('epsilon_decay', 0.995)
        self.min_epsilon = config.get('min_epsilon', 0.01)
        
        self.logger.info(f"初始化DRL准入控制器: training_mode={self.training_mode}")
    
    def _initialize_model(self):
        """初始化DRL模型"""
        try:
            if self.training_mode:
                # 训练模式：创建新模型
                self.model = PPO(
                    "MlpPolicy",
                    env=DummyVecEnv([lambda: self._create_dummy_env()]),
                    learning_rate=self.drl_config.get('learning_rate', 3e-4),
                    n_steps=self.drl_config.get('n_steps', 2048),
                    batch_size=self.drl_config.get('batch_size', 64),
                    gamma=self.drl_config.get('gamma', 0.99),
                    device=self.drl_config.get('device', 'cpu'),
                    verbose=1
                )
            else:
                # 推理模式：加载预训练模型
                try:
                    self.model = PPO.load(self.model_path)
                    self.logger.info(f"加载预训练模型: {self.model_path}")
                except:
                    self.logger.warning("无法加载预训练模型，使用随机初始化模型")
                    self.model = PPO(
                        "MlpPolicy",
                        env=DummyVecEnv([lambda: self._create_dummy_env()]),
                        device=self.drl_config.get('device', 'cpu')
                    )
        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}")
            self.model = None
    
    def _create_dummy_env(self):
        """创建虚拟环境（用于模型初始化）"""
        class DummyEnv:
            def __init__(self):
                self.observation_space = type('obj', (object,), {
                    'shape': (128,), 'dtype': np.float32
                })()
                self.action_space = type('obj', (object,), {
                    'n': 5
                })()
            
            def reset(self):
                return np.zeros(128, dtype=np.float32)
            
            def step(self, action):
                return np.zeros(128, dtype=np.float32), 0.0, True, {}
        
        return DummyEnv()
    
    def make_admission_decision(self, 
                              user_request: UserRequest,
                              network_state: NetworkState,
                              positioning_metrics: Optional[Dict[str, Any]] = None) -> AdmissionResult:
        """使用DRL做出准入决策"""
        start_time = time.time()
        
        try:
            if self.model is None:
                # 回退到简单策略
                return self._fallback_decision(user_request, network_state, positioning_metrics)
            
            # 提取状态特征
            state_features = self.environment.extract_state_features(
                user_request, network_state, positioning_metrics
            )
            
            # 使用模型预测动作
            if np.random.random() < self.epsilon and self.training_mode:
                # 探索：随机动作
                action = np.random.randint(0, 5)
                confidence = 0.5
            else:
                # 利用：模型预测
                action, _ = self.model.predict(state_features, deterministic=not self.training_mode)
                confidence = 0.8
            
            # 将动作转换为决策
            decision = self._action_to_decision(action)
            
            # 找到最佳卫星
            best_satellite = self._find_best_satellite(user_request, network_state, positioning_metrics)
            
            # 计算分配的带宽
            allocated_bandwidth = self._calculate_allocated_bandwidth(
                decision, user_request, best_satellite, network_state
            )
            
            result = AdmissionResult(
                decision=decision,
                confidence=confidence,
                allocated_bandwidth=allocated_bandwidth,
                allocated_satellite=best_satellite,
                reason=f"DRL决策: action={action}"
            )
            
            # 更新探索率
            if self.training_mode:
                self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
            
            self._finalize_decision(result, start_time)
            return result
            
        except Exception as e:
            self.logger.error(f"DRL决策失败: {e}")
            return self._fallback_decision(user_request, network_state, positioning_metrics)
    
    def _action_to_decision(self, action: int) -> AdmissionDecision:
        """将动作转换为决策"""
        action_map = {
            0: AdmissionDecision.ACCEPT,
            1: AdmissionDecision.REJECT,
            2: AdmissionDecision.DEGRADED_ACCEPT,
            3: AdmissionDecision.DELAYED_ACCEPT,
            4: AdmissionDecision.PARTIAL_ACCEPT
        }
        return action_map.get(action, AdmissionDecision.REJECT)
    
    def _calculate_allocated_bandwidth(self, 
                                     decision: AdmissionDecision,
                                     user_request: UserRequest,
                                     satellite_id: Optional[int],
                                     network_state: NetworkState) -> float:
        """计算分配的带宽"""
        if decision == AdmissionDecision.REJECT:
            return 0.0
        elif decision == AdmissionDecision.ACCEPT:
            return user_request.bandwidth_mbps
        elif decision == AdmissionDecision.DEGRADED_ACCEPT:
            return user_request.bandwidth_mbps * 0.7  # 降级到70%
        elif decision == AdmissionDecision.PARTIAL_ACCEPT:
            return user_request.bandwidth_mbps * 0.5  # 部分接受50%
        else:
            return user_request.bandwidth_mbps
    
    def _fallback_decision(self, 
                          user_request: UserRequest,
                          network_state: NetworkState,
                          positioning_metrics: Optional[Dict[str, Any]]) -> AdmissionResult:
        """回退决策（当DRL不可用时）"""
        # 简单的基于负载的决策
        avg_load = np.mean([self._calculate_satellite_load(sat['id'], network_state) 
                           for sat in network_state.satellites])
        
        if avg_load < 0.7:
            decision = AdmissionDecision.ACCEPT
        elif avg_load < 0.9:
            decision = AdmissionDecision.DEGRADED_ACCEPT
        else:
            decision = AdmissionDecision.REJECT
        
        best_satellite = self._find_best_satellite(user_request, network_state, positioning_metrics)
        allocated_bandwidth = self._calculate_allocated_bandwidth(
            decision, user_request, best_satellite, network_state
        )
        
        return AdmissionResult(
            decision=decision,
            confidence=0.6,
            allocated_bandwidth=allocated_bandwidth,
            allocated_satellite=best_satellite,
            reason="回退策略"
        )
    
    def _finalize_decision(self, result: AdmissionResult, start_time: float):
        """完成决策处理"""
        decision_time = time.time() - start_time
        self.decision_times.append(decision_time)
        self.update_statistics(result)
        
        self.logger.debug(f"DRL准入决策: {result.decision.value}, "
                         f"置信度: {result.confidence:.2f}, "
                         f"卫星: {result.allocated_satellite}, "
                         f"带宽: {result.allocated_bandwidth:.1f}Mbps")
