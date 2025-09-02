"""
系统配置管理

支持从YAML/JSON文件加载配置，包括星座参数、DRL参数、
DSROQ参数、定位参数等。
"""

import os
import yaml
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class ConstellationConfig:
    """星座配置"""
    name: str = "starlink"
    num_orbits: int = 72
    num_sats_per_orbit: int = 22
    altitude_km: float = 550.0
    inclination_deg: float = 53.0
    eccentricity: float = 0.0
    arg_of_perigee_deg: float = 0.0
    mean_motion_rev_per_day: float = 15.19
    # TLE 配置
    use_tle: bool = False
    tle_file: Optional[str] = None

    @property
    def num_satellites(self) -> int:
        """计算总卫星数"""
        return self.num_orbits * self.num_sats_per_orbit


@dataclass 
class DRLRewardWeights:
    """DRL奖励权重配置 (对齐 design/algorithm_design.md 第219-227行)"""
    qoe: float = 1.0         # w1: QoE增量权重
    fairness: float = 0.2    # w2: 公平性权重
    utilization: float = 0.2 # w3: 资源利用权重 (效率)
    efficiency: float = 0.2  # w3: 同 utilization (兼容)
    positioning: float = 0.3 # w4: 定位可用性权重 (lambda_pos)
    violation: float = 0.8   # w5: 违规惩罚权重
    delay: float = 0.3       # w6: 延迟惩罚权重
    stability: float = 0.2   # 额外: 稳定性权重

@dataclass
class DRLConfig:
    """DRL配置"""
    algorithm: str = "PPO"
    learning_rate: float = 3e-4
    batch_size: int = 64
    buffer_size: int = 100000
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    entropy_coef: float = 0.01
    value_function_coef: float = 0.5
    max_grad_norm: float = 0.5
    n_epochs: int = 10
    n_steps: int = 2048
    device: str = "cpu"  # "cpu" or "cuda"
    
    # 状态空间配置
    state_dim: int = 128
    action_dim: int = 5  # ACCEPT, REJECT, DEGRADED_ACCEPT, DELAYED_ACCEPT, PARTIAL_ACCEPT
    
    # 训练配置
    total_timesteps: int = 1000000
    eval_freq: int = 10000
    save_freq: int = 50000
    log_interval: int = 1000
    
    # 奖励权重配置
    reward_weights: DRLRewardWeights = field(default_factory=DRLRewardWeights)
    
    # 探索参数
    epsilon: float = 0.1
    epsilon_decay: float = 0.995
    min_epsilon: float = 0.01


@dataclass
class AdmissionConfig:
    """准入控制配置"""
    algorithm: str = "DRL"  # "DRL", "threshold", "random"

    # 阈值准入控制参数
    max_users_per_satellite: int = 100
    min_signal_strength_dbm: float = -120.0
    max_latency_threshold_ms: float = 50.0
    min_bandwidth_threshold_mbps: float = 1.0

    # DRL准入控制参数
    use_positioning_aware: bool = True
    positioning_weight: float = 0.3
    qos_weight: float = 0.7


@dataclass
class ResourceAllocationConfig:
    """资源分配配置"""
    algorithm: str = "DSROQ"  # "DSROQ", "proportional", "equal"

    # 比例分配参数
    fairness_factor: float = 0.5
    efficiency_factor: float = 0.5

    # 等分配置
    min_allocation_mbps: float = 0.5
    max_allocation_mbps: float = 10.0


@dataclass
class DSROQConfig:
    """DSROQ配置"""
    # MCTS路由参数
    mcts_iterations: int = 1000
    mcts_exploration_constant: float = 1.414
    mcts_max_depth: int = 10
    
    # 李雅普诺夫调度参数
    lyapunov_weight: float = 1.0
    queue_weight: float = 1.0
    utility_weight: float = 1.0
    
    # 带宽分配参数
    min_bandwidth_mbps: float = 1.0
    max_bandwidth_mbps: float = 100.0
    bandwidth_granularity: float = 0.1

    # 路由与协同参数 (新增)
    seam_penalty: float = 0.5                 # 跨缝路径的附加代价
    path_change_penalty: float = 0.2          # 路径变更的惩罚
    reroute_cooldown_ms: int = 5000           # 重路由的冷却时间
    lambda_pos: float = 0.2                   # 定位质量在代价函数中的权重


@dataclass
class PositioningQualityWeights:
    """定位质量权重配置"""
    visibility: float = 0.3    # 可见性权重
    gdop: float = 0.25         # GDOP权重
    accuracy: float = 0.25     # 精度权重
    signal: float = 0.15       # 信号强度权重
    geometry: float = 0.05     # 几何分布权重

@dataclass
class PositioningAvailabilityWeights:
    """定位可用性权重配置"""
    crlb: float = 0.35         # CRLB权重
    gdop: float = 0.25         # GDOP权重
    visibility: float = 0.25   # 可见性权重
    cooperation: float = 0.15  # 协作度权重

@dataclass
class PositioningConfig:
    """定位配置"""
    # CRLB计算参数
    signal_power_dbm: float = -130.0
    noise_power_dbm: float = -140.0
    carrier_frequency_hz: float = 2.4e9
    bandwidth_hz: float = 20e6
    
    # GDOP计算参数
    elevation_mask_deg: float = 10.0
    max_range_km: float = 2000.0
    
    # 阈值配置
    min_visible_satellites: int = 4
    min_cooperative_satellites: int = 2
    crlb_threshold_m: float = 50.0
    gdop_threshold: float = 10.0
    
    # 权重配置
    positioning_quality_weights: PositioningQualityWeights = field(default_factory=PositioningQualityWeights)
    availability_weights: PositioningAvailabilityWeights = field(default_factory=PositioningAvailabilityWeights)
    
    # 定位质量权重（兼容性）
    crlb_weight: float = 0.4
    gdop_weight: float = 0.3
    coverage_weight: float = 0.3


@dataclass
class SimulationConfig:
    """仿真配置"""
    duration_seconds: float = 3600.0  # 1小时
    time_step_seconds: float = 1.0
    random_seed: int = 42
    
    # 流量生成参数
    flow_arrival_rate: float = 10.0  # flows per second
    flow_duration_mean: float = 60.0  # seconds
    flow_duration_std: float = 20.0
    
    # 用户分布
    num_users: int = 100
    user_distribution: str = "uniform"  # "uniform", "clustered", "realistic"


@dataclass
class APIConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_enabled: bool = True
    rate_limit: str = "100/minute"
    
    # 数据库配置
    database_url: str = "sqlite:///leo_system.db"
    redis_url: str = "redis://localhost:6379/0"


@dataclass
class VisualizationConfig:
    """可视化配置"""
    # 前端配置
    frontend_port: int = 3000
    cesium_ion_token: str = ""  # Cesium Ion访问令牌
    
    # 图表配置
    update_interval_ms: int = 1000
    max_data_points: int = 1000
    
    # 3D可视化
    satellite_scale: float = 1000.0
    orbit_opacity: float = 0.3
    link_opacity: float = 0.5


@dataclass
class BackendConfig:
    """后端仿真后端配置（仅保留 real 模式）"""
    # Hypatia 集成模式：仅支持 real
    hypatia_mode: str = "real"
    # ns-3 集成模式：仅保留 real（如未接入，可与 Hypatia 管线占位集成）
    ns3_mode: str = "real"
    # 数据目录：TLE/ISL/GSL/动态状态等生成或读取目录
    data_dir: str = "/tmp/hypatia_temp"


@dataclass
class SystemConfig:
    """完整系统配置"""
    constellation: ConstellationConfig = field(default_factory=ConstellationConfig)
    admission: AdmissionConfig = field(default_factory=AdmissionConfig)
    resource_allocation: ResourceAllocationConfig = field(default_factory=ResourceAllocationConfig)
    drl: DRLConfig = field(default_factory=DRLConfig)
    dsroq: DSROQConfig = field(default_factory=DSROQConfig)
    positioning: PositioningConfig = field(default_factory=PositioningConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    api: APIConfig = field(default_factory=APIConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    
    # 联合优化权重
    qoe_weight: float = 0.6
    positioning_weight: float = 0.4


def load_config(config_path: Optional[str] = None) -> SystemConfig:
    """加载系统配置"""
    if config_path is None:
        # 默认配置文件路径
        config_path = Path(__file__).parent.parent.parent / "experiments" / "configs" / "default.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}，使用默认配置")
        return SystemConfig()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                config_dict = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                config_dict = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
        
        # 递归更新配置
        config = SystemConfig()
        _update_config_from_dict(config, config_dict)
        return config
        
    except Exception as e:
        print(f"加载配置文件失败: {e}，使用默认配置")
        return SystemConfig()


def _update_config_from_dict(config_obj: Any, config_dict: Dict[str, Any]) -> None:
    """递归更新配置对象"""
    for key, value in config_dict.items():
        if hasattr(config_obj, key):
            attr = getattr(config_obj, key)
            if hasattr(attr, '__dict__') and isinstance(value, dict):
                # 递归更新嵌套配置
                _update_config_from_dict(attr, value)
            else:
                # 直接设置值
                setattr(config_obj, key, value)


def save_config(config: SystemConfig, config_path: str) -> None:
    """保存配置到文件"""
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 转换为字典
    config_dict = _config_to_dict(config)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        elif config_path.suffix.lower() == '.json':
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")


def _config_to_dict(config_obj: Any) -> Dict[str, Any]:
    """将配置对象转换为字典"""
    if hasattr(config_obj, '__dict__'):
        result = {}
        for key, value in config_obj.__dict__.items():
            if hasattr(value, '__dict__'):
                result[key] = _config_to_dict(value)
            else:
                result[key] = value
        return result
    else:
        return config_obj
