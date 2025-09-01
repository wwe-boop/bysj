"""
基于深度强化学习的准入控制

实现使用PPO算法的智能准入控制策略
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging

from src.core.config import SystemConfig
from src.simulation.simulation_engine import SimulationEngine
from src.admission.admission_controller import AdmissionController, AdmissionResult, AdmissionDecision
from src.core.state import NetworkState, UserRequest
from src.admission.drl_environment import HypatiaAdmissionEnv

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class DRLAdmissionController(AdmissionController):
    """基于DRL的准入控制器"""
    
    def __init__(self, config: SystemConfig, simulation_engine: SimulationEngine):
        super().__init__(config.admission.__dict__)
        
        if not TORCH_AVAILABLE:
            raise ImportError("DRL准入控制需要PyTorch和stable-baselines3")
        
        self.config = config
        self.drl_config = config.drl
        self.sim_engine = simulation_engine

        # 为PPO创建Gym环境
        self.env = HypatiaAdmissionEnv(config, simulation_engine)
        
        # 模型参数
        self.model_path = self.config.admission.__dict__.get('model_path', 'models/admission_ppo.zip')
        self.training_mode = self.config.admission.__dict__.get('training_mode', False)
        
        # 初始化模型
        self.model = None
        self._initialize_model()
        
        # 探索参数
        self.epsilon = self.drl_config.__dict__.get('epsilon', 0.1)
        self.epsilon_decay = self.drl_config.__dict__.get('epsilon_decay', 0.995)
        self.min_epsilon = self.drl_config.__dict__.get('min_epsilon', 0.01)
        
        self.logger.info(f"初始化DRL准入控制器: training_mode={self.training_mode}")
    
    def _initialize_model(self):
        """初始化DRL模型"""
        try:
            vec_env = make_vec_env(lambda: self.env, n_envs=1)

            if self.training_mode:
                # 训练模式：创建新模型
                self.model = PPO(
                    "MlpPolicy",
                    env=vec_env,
                    learning_rate=self.drl_config.learning_rate,
                    n_steps=self.drl_config.n_steps,
                    batch_size=self.drl_config.batch_size,
                    gamma=self.drl_config.gamma,
                    device=self.drl_config.device,
                    verbose=1
                )
            else:
                # 推理模式：加载预训练模型
                try:
                    self.model = PPO.load(self.model_path, env=vec_env)
                    self.logger.info(f"加载预训练模型: {self.model_path}")
                except:
                    self.logger.warning("无法加载预训练模型，使用随机初始化模型")
                    self.model = PPO("MlpPolicy", env=vec_env, device=self.drl_config.device)

        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}")
            self.model = None

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
            # 注意：当前状态提取在env内部完成，对于推理，我们需要一种方式来获取它
            # 临时方案：直接调用env的内部方法
            state_features = self.env._get_observation(user_request, network_state, positioning_metrics)
            
            # 使用模型预测动作
            if np.random.random() < self.epsilon and self.training_mode:
                # 探索：随机动作
                action = self.env.action_space.sample()
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
        avg_load = np.mean([sat.get('load', 0.0) for sat in network_state.satellites])
        
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

    def _find_best_satellite(self,
                             user_request: UserRequest,
                             network_state: NetworkState,
                             positioning_metrics: Optional[Dict[str, Any]]) -> Optional[int]:
        # 这是一个简化的实现，实际需要更复杂的逻辑
        # 例如，考虑信号强度、负载、波束覆盖等
        if network_state.satellites:
            return network_state.satellites[0]['id']
        return None
