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

    @property
    def num_satellites(self) -> int:
        """计算总卫星数"""
        return self.num_orbits * self.num_sats_per_orbit


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
    
    # 定位质量权重
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
