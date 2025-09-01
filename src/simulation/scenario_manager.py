"""
场景管理器

管理不同的仿真场景和配置
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from src.core.config import SystemConfig


@dataclass
class SimulationScenario:
    """仿真场景"""
    name: str
    description: str
    duration_seconds: float
    traffic_pattern: str
    constellation_config: Dict[str, Any]
    admission_config: Dict[str, Any]
    dsroq_config: Dict[str, Any]
    positioning_config: Dict[str, Any]
    simulation_config: Dict[str, Any]
    expected_results: Optional[Dict[str, Any]] = None
    tags: List[str] = None


class ScenarioManager:
    """场景管理器"""
    
    def __init__(self, scenarios_dir: str = "scenarios"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.scenarios_dir = Path(scenarios_dir)
        self.scenarios_dir.mkdir(exist_ok=True)
        
        # 预定义场景
        self.predefined_scenarios = self._create_predefined_scenarios()
        
        # 加载的场景
        self.loaded_scenarios: Dict[str, SimulationScenario] = {}
        
        self.logger.info(f"场景管理器初始化: 场景目录={self.scenarios_dir}")
    
    def _create_predefined_scenarios(self) -> List[SimulationScenario]:
        """创建预定义场景"""
        scenarios = []
        
        # 基础性能测试场景
        scenarios.append(SimulationScenario(
            name="basic_performance",
            description="基础性能测试：均匀流量分布，测试系统基本功能",
            duration_seconds=300.0,
            traffic_pattern="mixed",
            constellation_config={
                "name": "starlink",
                "num_orbits": 72,
                "num_sats_per_orbit": 22,
                "altitude_km": 550.0,
                "inclination_deg": 53.0
            },
            admission_config={
                "algorithm": "threshold",
                "max_users_per_satellite": 100,
                "min_signal_strength_dbm": -120.0
            },
            dsroq_config={
                "mcts_iterations": 1000,
                "lyapunov_weight": 1.0,
                "min_bandwidth_mbps": 1.0
            },
            positioning_config={
                "elevation_mask_deg": 10.0,
                "max_gdop_threshold": 10.0
            },
            simulation_config={
                "flow_arrival_rate": 5.0,
                "num_users": 50,
                "user_distribution": "uniform"
            },
            expected_results={
                "min_admission_rate": 0.8,
                "max_avg_latency": 150.0,
                "min_qoe_score": 0.7
            },
            tags=["basic", "performance", "uniform"]
        ))
        
        # 高负载压力测试场景
        scenarios.append(SimulationScenario(
            name="high_load_stress",
            description="高负载压力测试：大量用户同时请求服务",
            duration_seconds=600.0,
            traffic_pattern="data_heavy",
            constellation_config={
                "name": "starlink",
                "num_orbits": 72,
                "num_sats_per_orbit": 22,
                "altitude_km": 550.0,
                "inclination_deg": 53.0
            },
            admission_config={
                "algorithm": "positioning_aware",
                "max_users_per_satellite": 150,
                "positioning_weight": 0.3
            },
            dsroq_config={
                "mcts_iterations": 800,
                "lyapunov_weight": 1.5,
                "min_bandwidth_mbps": 0.5
            },
            positioning_config={
                "elevation_mask_deg": 15.0,
                "max_gdop_threshold": 8.0
            },
            simulation_config={
                "flow_arrival_rate": 20.0,
                "num_users": 200,
                "user_distribution": "clustered"
            },
            expected_results={
                "min_admission_rate": 0.6,
                "max_avg_latency": 200.0,
                "min_qoe_score": 0.6
            },
            tags=["stress", "high_load", "clustered"]
        ))
        
        # 紧急通信场景
        scenarios.append(SimulationScenario(
            name="emergency_communication",
            description="紧急通信场景：灾区通信，高优先级流量",
            duration_seconds=900.0,
            traffic_pattern="emergency",
            constellation_config={
                "name": "starlink",
                "num_orbits": 72,
                "num_sats_per_orbit": 22,
                "altitude_km": 550.0,
                "inclination_deg": 53.0
            },
            admission_config={
                "algorithm": "positioning_aware",
                "max_users_per_satellite": 80,
                "positioning_weight": 0.4
            },
            dsroq_config={
                "mcts_iterations": 1200,
                "lyapunov_weight": 0.8,
                "min_bandwidth_mbps": 0.5
            },
            positioning_config={
                "elevation_mask_deg": 5.0,
                "max_gdop_threshold": 15.0
            },
            simulation_config={
                "flow_arrival_rate": 8.0,
                "num_users": 80,
                "user_distribution": "hotspot"
            },
            expected_results={
                "min_admission_rate": 0.9,
                "max_avg_latency": 100.0,
                "min_qoe_score": 0.8
            },
            tags=["emergency", "high_priority", "hotspot"]
        ))
        
        # 视频流媒体场景
        scenarios.append(SimulationScenario(
            name="video_streaming",
            description="视频流媒体场景：大带宽需求，延迟敏感",
            duration_seconds=1200.0,
            traffic_pattern="video_streaming",
            constellation_config={
                "name": "starlink",
                "num_orbits": 72,
                "num_sats_per_orbit": 22,
                "altitude_km": 550.0,
                "inclination_deg": 53.0
            },
            admission_config={
                "algorithm": "threshold",
                "max_users_per_satellite": 60,
                "min_bandwidth_threshold_mbps": 2.0
            },
            dsroq_config={
                "mcts_iterations": 1000,
                "lyapunov_weight": 1.2,
                "min_bandwidth_mbps": 2.0
            },
            positioning_config={
                "elevation_mask_deg": 10.0,
                "max_gdop_threshold": 12.0
            },
            simulation_config={
                "flow_arrival_rate": 3.0,
                "num_users": 40,
                "user_distribution": "clustered"
            },
            expected_results={
                "min_admission_rate": 0.75,
                "max_avg_latency": 120.0,
                "min_qoe_score": 0.75
            },
            tags=["video", "high_bandwidth", "latency_sensitive"]
        ))
        
        # 导航服务场景
        scenarios.append(SimulationScenario(
            name="navigation_services",
            description="导航服务场景：定位精度要求高，低带宽",
            duration_seconds=1800.0,
            traffic_pattern="navigation",
            constellation_config={
                "name": "starlink",
                "num_orbits": 72,
                "num_sats_per_orbit": 22,
                "altitude_km": 550.0,
                "inclination_deg": 53.0
            },
            admission_config={
                "algorithm": "positioning_aware",
                "max_users_per_satellite": 200,
                "positioning_weight": 0.6
            },
            dsroq_config={
                "mcts_iterations": 600,
                "lyapunov_weight": 0.5,
                "min_bandwidth_mbps": 0.1
            },
            positioning_config={
                "elevation_mask_deg": 15.0,
                "max_gdop_threshold": 5.0
            },
            simulation_config={
                "flow_arrival_rate": 15.0,
                "num_users": 150,
                "user_distribution": "uniform"
            },
            expected_results={
                "min_admission_rate": 0.85,
                "max_avg_latency": 80.0,
                "min_positioning_score": 0.8
            },
            tags=["navigation", "positioning", "low_bandwidth"]
        ))
        
        return scenarios
    
    def get_scenario(self, name: str) -> Optional[SimulationScenario]:
        """获取场景"""
        # 首先检查已加载的场景
        if name in self.loaded_scenarios:
            return self.loaded_scenarios[name]
        
        # 检查预定义场景
        for scenario in self.predefined_scenarios:
            if scenario.name == name:
                return scenario
        
        # 尝试从文件加载
        return self.load_scenario(name)
    
    def list_scenarios(self) -> List[str]:
        """列出所有可用场景"""
        scenario_names = []
        
        # 预定义场景
        scenario_names.extend([s.name for s in self.predefined_scenarios])
        
        # 已加载场景
        scenario_names.extend(self.loaded_scenarios.keys())
        
        # 文件中的场景
        for file_path in self.scenarios_dir.glob("*.json"):
            scenario_name = file_path.stem
            if scenario_name not in scenario_names:
                scenario_names.append(scenario_name)
        
        return sorted(list(set(scenario_names)))
    
    def save_scenario(self, scenario: SimulationScenario) -> bool:
        """保存场景到文件"""
        try:
            file_path = self.scenarios_dir / f"{scenario.name}.json"
            
            scenario_dict = asdict(scenario)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scenario_dict, f, indent=2, ensure_ascii=False)
            
            self.loaded_scenarios[scenario.name] = scenario
            self.logger.info(f"场景已保存: {scenario.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存场景失败: {e}")
            return False
    
    def load_scenario(self, name: str) -> Optional[SimulationScenario]:
        """从文件加载场景"""
        try:
            file_path = self.scenarios_dir / f"{name}.json"
            
            if not file_path.exists():
                self.logger.warning(f"场景文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_dict = json.load(f)
            
            scenario = SimulationScenario(**scenario_dict)
            self.loaded_scenarios[name] = scenario
            
            self.logger.info(f"场景已加载: {name}")
            return scenario
            
        except Exception as e:
            self.logger.error(f"加载场景失败: {e}")
            return None
    
    def create_scenario_from_config(self, 
                                  name: str,
                                  description: str,
                                  config: SystemConfig,
                                  duration_seconds: float = 600.0,
                                  traffic_pattern: str = "mixed",
                                  tags: List[str] = None) -> SimulationScenario:
        """从系统配置创建场景"""
        scenario = SimulationScenario(
            name=name,
            description=description,
            duration_seconds=duration_seconds,
            traffic_pattern=traffic_pattern,
            constellation_config=asdict(config.constellation),
            admission_config=asdict(config.admission),
            dsroq_config=asdict(config.dsroq),
            positioning_config=asdict(config.positioning),
            simulation_config=asdict(config.simulation),
            tags=tags or []
        )
        
        return scenario
    
    def apply_scenario_to_config(self, scenario: SimulationScenario, config: SystemConfig) -> SystemConfig:
        """将场景应用到系统配置"""
        # 更新各个配置模块
        for key, value in scenario.constellation_config.items():
            if hasattr(config.constellation, key):
                setattr(config.constellation, key, value)
        
        for key, value in scenario.admission_config.items():
            if hasattr(config.admission, key):
                setattr(config.admission, key, value)
        
        for key, value in scenario.dsroq_config.items():
            if hasattr(config.dsroq, key):
                setattr(config.dsroq, key, value)
        
        for key, value in scenario.positioning_config.items():
            if hasattr(config.positioning, key):
                setattr(config.positioning, key, value)
        
        for key, value in scenario.simulation_config.items():
            if hasattr(config.simulation, key):
                setattr(config.simulation, key, value)
        
        # 更新仿真持续时间
        config.simulation.duration_seconds = scenario.duration_seconds
        
        return config
    
    def get_scenarios_by_tag(self, tag: str) -> List[SimulationScenario]:
        """根据标签获取场景"""
        scenarios = []
        
        # 检查预定义场景
        for scenario in self.predefined_scenarios:
            if scenario.tags and tag in scenario.tags:
                scenarios.append(scenario)
        
        # 检查已加载场景
        for scenario in self.loaded_scenarios.values():
            if scenario.tags and tag in scenario.tags:
                scenarios.append(scenario)
        
        return scenarios
    
    def validate_scenario(self, scenario: SimulationScenario) -> List[str]:
        """验证场景配置"""
        errors = []
        
        # 基本验证
        if scenario.duration_seconds <= 0:
            errors.append("仿真持续时间必须大于0")
        
        if not scenario.traffic_pattern:
            errors.append("必须指定流量模式")
        
        # 星座配置验证
        constellation = scenario.constellation_config
        if constellation.get('num_orbits', 0) <= 0:
            errors.append("轨道数量必须大于0")
        
        if constellation.get('num_sats_per_orbit', 0) <= 0:
            errors.append("每轨道卫星数量必须大于0")
        
        if constellation.get('altitude_km', 0) <= 0:
            errors.append("轨道高度必须大于0")
        
        # 准入控制配置验证
        admission = scenario.admission_config
        if admission.get('max_users_per_satellite', 0) <= 0:
            errors.append("每卫星最大用户数必须大于0")
        
        # DSROQ配置验证
        dsroq = scenario.dsroq_config
        if dsroq.get('mcts_iterations', 0) <= 0:
            errors.append("MCTS迭代次数必须大于0")
        
        # 仿真配置验证
        simulation = scenario.simulation_config
        if simulation.get('flow_arrival_rate', 0) <= 0:
            errors.append("流量到达率必须大于0")
        
        return errors
    
    def get_scenario_summary(self, scenario: SimulationScenario) -> Dict[str, Any]:
        """获取场景摘要"""
        total_satellites = (scenario.constellation_config.get('num_orbits', 0) * 
                          scenario.constellation_config.get('num_sats_per_orbit', 0))
        
        return {
            'name': scenario.name,
            'description': scenario.description,
            'duration_minutes': scenario.duration_seconds / 60.0,
            'traffic_pattern': scenario.traffic_pattern,
            'total_satellites': total_satellites,
            'admission_algorithm': scenario.admission_config.get('algorithm', 'unknown'),
            'expected_users': scenario.simulation_config.get('num_users', 0),
            'arrival_rate': scenario.simulation_config.get('flow_arrival_rate', 0),
            'tags': scenario.tags or [],
            'has_expected_results': scenario.expected_results is not None
        }
