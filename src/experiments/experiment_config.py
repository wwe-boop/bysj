"""
实验配置类
定义实验参数和消融实验配置
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ExperimentConfig:
    """实验配置"""
    experiment_name: str
    scenario_name: str
    duration_seconds: int = 300
    
    # 准入控制配置
    admission_config: Optional[Dict[str, Any]] = None
    
    # DSROQ配置
    dsroq_config: Optional[Dict[str, Any]] = None
    
    # 定位服务配置
    positioning_config: Optional[Dict[str, Any]] = None
    
    # 网络配置
    network_config: Optional[Dict[str, Any]] = None
    
    # 其他参数
    random_seed: Optional[int] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class AblationConfig:
    """消融实验配置"""
    # 状态空间消融
    state_ablations: List[str] = field(default_factory=list)
    
    # 奖励函数消融
    reward_ablations: List[str] = field(default_factory=list)
    
    # 动作空间消融
    action_ablations: List[str] = field(default_factory=list)
    
    # 算法比较
    algorithm_comparisons: List[str] = field(default_factory=list)
    
    # 网络负载消融
    load_ablations: List[float] = field(default_factory=list)
    
    # 星座配置消融
    constellation_ablations: List[str] = field(default_factory=list)
    
    # 故障场景消融
    failure_ablations: List[str] = field(default_factory=list)


class ExperimentConfigBuilder:
    """实验配置构建器"""
    
    @staticmethod
    def create_baseline_config(scenario_name: str = "urban_high_load") -> ExperimentConfig:
        """创建基线配置"""
        return ExperimentConfig(
            experiment_name="baseline",
            scenario_name=scenario_name,
            duration_seconds=300,
            admission_config={
                'algorithm': 'drl_ppo',
                'max_users_per_satellite': 100,
                'min_signal_strength_dbm': -120.0,
                'positioning_weight': 0.3,
                'use_positioning': True,
                'use_load_info': True,
                'use_history': True,
                'reward_weights': {
                    'qoe_weight': 0.4,
                    'fairness_weight': 0.2,
                    'efficiency_weight': 0.2,
                    'stability_weight': 0.1,
                    'positioning_weight': 0.1
                },
                'action_space': ['accept', 'reject', 'degraded_accept', 'delay']
            },
            dsroq_config={
                'routing_algorithm': 'mcts',
                'resource_allocation': 'lyapunov',
                'mcts_iterations': 1000,
                'exploration_constant': 1.414,
                'lyapunov_v': 10.0
            },
            positioning_config={
                'elevation_mask_deg': 10,
                'max_gdop_threshold': 10,
                'min_visible_satellites': 4,
                'beam_hint_enabled': True
            },
            description="基线配置，使用完整的DRL准入控制和DSROQ资源分配"
        )
    
    @staticmethod
    def create_threshold_config(scenario_name: str = "urban_high_load") -> ExperimentConfig:
        """创建阈值算法配置"""
        config = ExperimentConfigBuilder.create_baseline_config(scenario_name)
        config.experiment_name = "threshold_baseline"
        config.admission_config['algorithm'] = 'threshold'
        config.description = "阈值算法基线配置"
        return config
    
    @staticmethod
    def create_positioning_aware_config(scenario_name: str = "urban_high_load") -> ExperimentConfig:
        """创建定位感知配置"""
        config = ExperimentConfigBuilder.create_baseline_config(scenario_name)
        config.experiment_name = "positioning_aware"
        config.admission_config['algorithm'] = 'positioning_aware'
        config.description = "定位感知准入控制配置"
        return config
    
    @staticmethod
    def create_load_variation_configs(base_config: ExperimentConfig, 
                                    load_factors: List[float]) -> List[ExperimentConfig]:
        """创建负载变化配置"""
        configs = []
        for load_factor in load_factors:
            config = ExperimentConfig(**base_config.__dict__.copy())
            config.experiment_name = f"{base_config.experiment_name}_load_{load_factor}"
            config.network_config = config.network_config or {}
            config.network_config['load_factor'] = load_factor
            config.description = f"{base_config.description} (负载因子: {load_factor})"
            configs.append(config)
        return configs
    
    @staticmethod
    def create_constellation_configs(base_config: ExperimentConfig,
                                   constellation_types: List[str]) -> List[ExperimentConfig]:
        """创建星座配置"""
        configs = []
        for constellation_type in constellation_types:
            config = ExperimentConfig(**base_config.__dict__.copy())
            config.experiment_name = f"{base_config.experiment_name}_constellation_{constellation_type}"
            config.network_config = config.network_config or {}
            config.network_config['constellation_type'] = constellation_type
            config.description = f"{base_config.description} (星座: {constellation_type})"
            configs.append(config)
        return configs
    
    @staticmethod
    def create_failure_scenario_configs(base_config: ExperimentConfig,
                                      failure_types: List[str]) -> List[ExperimentConfig]:
        """创建故障场景配置"""
        configs = []
        for failure_type in failure_types:
            config = ExperimentConfig(**base_config.__dict__.copy())
            config.experiment_name = f"{base_config.experiment_name}_failure_{failure_type}"
            config.network_config = config.network_config or {}
            config.network_config['failure_scenario'] = failure_type
            config.description = f"{base_config.description} (故障场景: {failure_type})"
            configs.append(config)
        return configs
    
    @staticmethod
    def create_comprehensive_ablation_config() -> AblationConfig:
        """创建全面的消融实验配置"""
        return AblationConfig(
            state_ablations=[
                "no_positioning",
                "no_load_info", 
                "no_history",
                "no_network_state",
                "minimal_state"
            ],
            reward_ablations=[
                "no_fairness",
                "no_efficiency", 
                "no_stability",
                "no_positioning",
                "qoe_only",
                "equal_weights"
            ],
            action_ablations=[
                "binary_only",
                "no_degraded",
                "no_delay",
                "extended_actions"
            ],
            algorithm_comparisons=[
                "threshold",
                "positioning_aware",
                "drl_ppo",
                "drl_a2c",
                "drl_sac",
                "random"
            ],
            load_ablations=[0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5],
            constellation_ablations=[
                "starlink_1584",
                "kuiper_3236", 
                "oneweb_648",
                "custom_minimal"
            ],
            failure_ablations=[
                "no_failure",
                "satellite_failure_5pct",
                "satellite_failure_10pct",
                "link_failure_random",
                "ground_station_failure"
            ]
        )
    
    @staticmethod
    def create_paper_experiment_configs() -> List[ExperimentConfig]:
        """创建论文实验配置"""
        configs = []
        
        # 基础场景配置
        scenarios = [
            "urban_high_load",
            "rural_low_load", 
            "mixed_load",
            "emergency_scenario",
            "global_coverage"
        ]
        
        # 算法比较
        algorithms = [
            "threshold",
            "positioning_aware", 
            "drl_ppo",
            "drl_a2c",
            "drl_sac"
        ]
        
        for scenario in scenarios:
            for algorithm in algorithms:
                config = ExperimentConfigBuilder.create_baseline_config(scenario)
                config.experiment_name = f"paper_{scenario}_{algorithm}"
                config.admission_config['algorithm'] = algorithm
                config.tags = ["paper_experiment", scenario, algorithm]
                configs.append(config)
        
        return configs


class ExperimentValidator:
    """实验配置验证器"""
    
    @staticmethod
    def validate_config(config: ExperimentConfig) -> List[str]:
        """验证实验配置"""
        errors = []
        
        # 基本验证
        if not config.experiment_name:
            errors.append("实验名称不能为空")
        
        if not config.scenario_name:
            errors.append("场景名称不能为空")
        
        if config.duration_seconds <= 0:
            errors.append("仿真时长必须大于0")
        
        # 准入控制配置验证
        if config.admission_config:
            admission_config = config.admission_config
            
            if 'algorithm' in admission_config:
                valid_algorithms = ['threshold', 'positioning_aware', 'drl_ppo', 'drl_a2c', 'drl_sac']
                if admission_config['algorithm'] not in valid_algorithms:
                    errors.append(f"无效的准入算法: {admission_config['algorithm']}")
            
            if 'reward_weights' in admission_config:
                weights = admission_config['reward_weights']
                if isinstance(weights, dict):
                    total_weight = sum(weights.values())
                    if abs(total_weight - 1.0) > 0.01:
                        errors.append(f"奖励权重总和应为1.0，当前为{total_weight:.3f}")
        
        # DSROQ配置验证
        if config.dsroq_config:
            dsroq_config = config.dsroq_config
            
            if 'routing_algorithm' in dsroq_config:
                valid_routing = ['shortest_path', 'mcts', 'genetic']
                if dsroq_config['routing_algorithm'] not in valid_routing:
                    errors.append(f"无效的路由算法: {dsroq_config['routing_algorithm']}")
        
        return errors
    
    @staticmethod
    def validate_ablation_config(config: AblationConfig) -> List[str]:
        """验证消融配置"""
        errors = []
        
        # 验证状态消融
        valid_state_ablations = [
            "no_positioning", "no_load_info", "no_history", 
            "no_network_state", "minimal_state"
        ]
        for ablation in config.state_ablations:
            if ablation not in valid_state_ablations:
                errors.append(f"无效的状态消融: {ablation}")
        
        # 验证奖励消融
        valid_reward_ablations = [
            "no_fairness", "no_efficiency", "no_stability", 
            "no_positioning", "qoe_only", "equal_weights"
        ]
        for ablation in config.reward_ablations:
            if ablation not in valid_reward_ablations:
                errors.append(f"无效的奖励消融: {ablation}")
        
        # 验证动作消融
        valid_action_ablations = [
            "binary_only", "no_degraded", "no_delay", "extended_actions"
        ]
        for ablation in config.action_ablations:
            if ablation not in valid_action_ablations:
                errors.append(f"无效的动作消融: {ablation}")
        
        # 验证负载因子
        for load_factor in config.load_ablations:
            if load_factor <= 0:
                errors.append(f"负载因子必须大于0: {load_factor}")
        
        return errors
