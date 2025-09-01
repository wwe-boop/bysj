from typing import Any, Dict, List, Tuple, Optional
import math



"""
Hypatia适配器

实现HypatiaInterface接口，提供与Hypatia框架的集成。
支持卫星网络生成、状态提取、仿真执行等功能。
"""

import logging
import os
import sys
from typing import Dict, List, Tuple, Any, Optional
import time

try:
    import numpy as np
except ImportError:
    logging.warning("numpy未安装，某些功能可能受限")
    np = None

# 添加Hypatia路径
hypatia_path = os.path.join(os.path.dirname(__file__), '..', '..', 'hypatia')
satgenpy_path = os.path.join(hypatia_path, 'satgenpy')
if satgenpy_path not in sys.path:
    sys.path.append(satgenpy_path)

# 导入Hypatia模块
try:
    # 尝试导入Hypatia模块
    import sys
    import os
    hypatia_satgen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'hypatia', 'satgenpy')
    if hypatia_satgen_path not in sys.path:
        sys.path.append(hypatia_satgen_path)

    from satgen.tles.read_tles import read_tles
    from satgen.tles.generate_tles_from_scratch import generate_tles_from_scratch_manual
    from satgen.ground_stations.read_ground_stations import read_ground_stations_extended
    from satgen.ground_stations.extend_ground_stations import extend_ground_stations
    from satgen.isls.read_isls import read_isls
    from satgen.isls.generate_plus_grid_isls import generate_plus_grid_isls
    from satgen.interfaces.read_gsl_interfaces_info import read_gsl_interfaces_info
    from satgen.dynamic_state.generate_dynamic_state import generate_dynamic_state_algorithm_free_one_only_over_isls
    HYPATIA_AVAILABLE = True
    logging.info("成功导入Hypatia模块")
except ImportError as e:
    logging.warning(f"无法导入Hypatia模块: {e}，将使用简化实现")
    HYPATIA_AVAILABLE = False

try:
    from ..core.interfaces import HypatiaInterface
    from ..core.state import NetworkState, FlowRequest, PositioningMetrics
    from ..core.config import ConstellationConfig, BackendConfig
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    src_path = os.path.join(os.path.dirname(__file__), '..', '..')
    if src_path not in sys.path:
        sys.path.append(src_path)

    from core.interfaces import HypatiaInterface
    from core.state import NetworkState, FlowRequest, PositioningMetrics
    from core.config import ConstellationConfig, BackendConfig
from .constellation import ConstellationManager
from .simulator import NS3Simulator


class HypatiaAdapter(HypatiaInterface):
    """Hypatia框架适配器"""

    def __init__(self, constellation_config: ConstellationConfig, backend_config: BackendConfig):
        self.logger = logging.getLogger(__name__)
        self.constellation_config = constellation_config
        self.backend_config = backend_config

        # Hypatia组件
        self.satellites = []
        self.ground_stations = []
        self.isls = []
        self.dynamic_state_update_interval_ms = 1000
        self.simulation_end_time_s = 3600

        # 网络状态
        self.current_time = 0.0
        self.time_step_ms = 1000
        self.fstate = {}  # 转发状态
        self.gsl_interfaces_info = {}

        # 状态
        self.initialized = False
        self.simulation_start_time = 0.0
        self.temp_gen_dir = backend_config.data_dir

        # 后端模式
        self.ns3_mode: str = backend_config.ns3_mode
        self.use_simplified = True  # 默认使用简化模式

        # 星座管理器（用于简化模式与 TLE 集成）
        self.constellation_manager: Optional[ConstellationManager] = None
        
        self._initialize()

    def _initialize(self):
        """根据后端配置初始化适配器"""
        try:
            self.logger.info("初始化Hypatia适配器...")

            # 决定使用真实模式还是简化模式
            if self.backend_config.hypatia_mode == "real" and HYPATIA_AVAILABLE:
                self.use_simplified = False
            else:
                self.use_simplified = True
                if self.backend_config.hypatia_mode == "real":
                    self.logger.warning("请求使用 real Hypatia 模式，但依赖不可用，回退到 simplified 模式")

            # 执行初始化
            if self.use_simplified:
                self.logger.info("使用简化实现（不依赖Hypatia）")
                self._initialize_simplified()
            else:
                self.logger.info("使用真实Hypatia实现")
                # 创建临时目录
                os.makedirs(self.temp_gen_dir, exist_ok=True)

                # 生成星座配置
                self._generate_constellation()

                # 生成地面站
                self._generate_ground_stations()

                # 生成ISL拓扑
                self._generate_isls()

                # 生成GSL接口信息
                self._generate_gsl_interfaces_info()

                # 生成描述文件
                self._generate_description()

                # 生成动态状态
                self._generate_dynamic_state()

            self.simulation_start_time = time.time()
            self.initialized = True

            self.logger.info("Hypatia适配器初始化完成")

        except Exception as e:
            self.logger.error(f"Hypatia适配器初始化失败: {e}")
            raise
    
    def _initialize_simplified(self):
        """简化初始化（不依赖Hypatia）"""
        # 使用 ConstellationManager（支持 use_tle）统一管理卫星与拓扑
        self.constellation_manager = ConstellationManager(self.constellation_config.__dict__)
        self.constellation_manager.initialize()
        self.logger.info("简化初始化完成")

    def _generate_constellation(self):
        """生成卫星星座"""
        config = self.constellation_config
        # 生成TLE文件
        tles_filename = os.path.join(self.temp_gen_dir, "tles.txt")

        # 使用Hypatia的TLE生成功能
        generate_tles_from_scratch_manual(
            tles_filename,
            config.name,
            config.num_orbits,
            config.num_sats_per_orbit,
            config.altitude_km * 1000,
            config.inclination_deg,
            config.eccentricity,
            config.arg_of_perigee_deg,
            0.0   # raan_offset_deg
        )

        # 读取生成的卫星信息
        self.satellites = read_tles(tles_filename)
        self.logger.info(f"生成了{len(self.satellites)}颗卫星")

    def _generate_ground_stations(self):
        """生成地面站"""
        # 使用一些主要城市作为地面站
        major_cities = [
            ("Tokyo", 35.6762, 139.6503), ("Delhi", 28.7041, 77.1025), ("Shanghai", 31.2304, 121.4737),
            ("São Paulo", -23.5558, -46.6396), ("Mexico City", 19.4326, -99.1332), ("Cairo", 30.0444, 31.2357),
            ("Mumbai", 19.0760, 72.8777), ("Beijing", 39.9042, 116.4074), ("Dhaka", 23.8103, 90.4125),
            ("Osaka", 34.6937, 135.5023), ("New York", 40.7128, -74.0060), ("Karachi", 24.8607, 67.0011),
            ("Buenos Aires", -34.6118, -58.3960), ("Chongqing", 29.4316, 106.9123), ("Istanbul", 41.0082, 28.9784),
            ("Kolkata", 22.5726, 88.3639), ("Manila", 14.5995, 120.9842), ("Lagos", 6.5244, 3.3792),
            ("Rio de Janeiro", -22.9068, -43.1729), ("Tianjin", 39.3434, 117.3616)
        ]
        gs_filename = os.path.join(self.temp_gen_dir, "ground_stations.txt")
        self._generate_ground_stations_file(gs_filename, major_cities)
        self.ground_stations = read_ground_stations_extended(gs_filename)
        self.logger.info(f"生成了{len(self.ground_stations)}个地面站")

    def _generate_ground_stations_file(self, filename: str, cities: List[Tuple[str, float, float]]):
        """生成地面站文件"""
        with open(filename, 'w') as f:
            for i, (name, lat, lon) in enumerate(cities):
                f.write(f"{i},{name},{lat},{lon},0.0\n")

    def _generate_isls(self):
        """生成星间链路"""
        config = self.constellation_config
        isls_filename = os.path.join(self.temp_gen_dir, "isls.txt")

        generate_plus_grid_isls(
            isls_filename,
            config.num_orbits,
            config.num_sats_per_orbit,
            1, True
        )
        self.isls = read_isls(isls_filename, len(self.satellites))
        self.logger.info(f"生成了{len(self.isls)}条星间链路")

    def _generate_gsl_interfaces_info(self):
        """生成GSL接口信息"""
        gsl_filename = os.path.join(self.temp_gen_dir, "gsl_interfaces_info.txt")
        with open(gsl_filename, 'w') as f:
            for i in range(len(self.satellites)):
                f.write(f"{i},1,1.0\n")
            for i in range(len(self.ground_stations)):
                node_id = len(self.satellites) + i
                f.write(f"{node_id},1,1.0\n")
        self.gsl_interfaces_info = read_gsl_interfaces_info(
            gsl_filename, len(self.satellites), len(self.ground_stations)
        )

    def _generate_description(self):
        """生成描述文件"""
        desc_filename = os.path.join(self.temp_gen_dir, "description.txt")
        with open(desc_filename, 'w') as f:
            f.write("max_gsl_length_m=1089686.0\n")
            f.write("max_isl_length_m=5016062.5\n")

    def _generate_dynamic_state(self):
        """生成动态状态"""
        dynamic_state_dir = os.path.join(self.temp_gen_dir, "dynamic_state")
        os.makedirs(dynamic_state_dir, exist_ok=True)

        generate_dynamic_state_algorithm_free_one_only_over_isls(
            self.temp_gen_dir,
            self.simulation_end_time_s * 1000 * 1000 * 1000,
            self.dynamic_state_update_interval_ms * 1000 * 1000,
            len(self.satellites),
            len(self.ground_stations),
            self.isls,
            self.gsl_interfaces_info,
            self.satellites,
            self.ground_stations
        )
        self.logger.info("动态状态生成完成")

    def get_network_state(self, time_step: float) -> NetworkState:
        """获取当前时刻的网络状态"""
        if not self.initialized:
            raise RuntimeError("Hypatia适配器未初始化")

        self.current_time = time_step

        if self.use_simplified:
            if self.constellation_manager is None:
                raise RuntimeError("简化模式下星座管理器未初始化")
            
            satellite_positions = self.constellation_manager.get_satellite_positions(time_step)
            topology = self.constellation_manager.get_topology_matrix(time_step)
            links = self.constellation_manager.get_link_states(time_step)
        else:
            # 真实模式下的状态获取逻辑
            # 注意：此处的动态状态读取逻辑需要根据Hypatia的实际输出进行实现
            # 这里暂时使用占位符
            self.logger.warning("真实Hypatia模式下的get_network_state尚未完全实现，使用占位符数据")
            num_sats = len(self.satellites)
            satellite_positions = [{'id': i, 'lat': 0, 'lon': 0, 'alt': self.constellation_config.altitude_km} for i in range(num_sats)]
            topology = np.zeros((num_sats, num_sats))
            links = []

        # 简化的链路利用率和容量（实际应该从ns3仿真获取）
        link_utilization = { (link['source_id'], link['dest_id']): 0.1 for link in links }
        link_capacity = { (link['source_id'], link['dest_id']): link.get('capacity_gbps', 10.0) for link in links }

        return NetworkState(
            time_step=time_step,
            satellites=satellite_positions,
            links=links,
            topology=topology,
            link_utilization=link_utilization,
            link_capacity=link_capacity,
            active_flows=[],
            queue_lengths={i: 0 for i in range(len(satellite_positions))}
        )
    
    def get_positioning_metrics(self, time_step: float, 
                              user_locations: List[Tuple[float, float]]) -> PositioningMetrics:
        """获取定位相关指标"""
        if not self.initialized:
            raise RuntimeError("Hypatia适配器未初始化")
        
        # 获取卫星位置
        satellites = self.constellation_manager.get_satellite_positions(time_step)
        
        # 计算每个用户的定位指标
        crlb_values = []
        gdop_values = []
        visible_satellites_count = []
        average_sinr = []
        positioning_accuracy = []
        
        for user_lat, user_lon in user_locations:
            # 计算可见卫星
            visible_sats = self._get_visible_satellites(
                user_lat, user_lon, satellites, time_step
            )
            
            visible_satellites_count.append(len(visible_sats))
            
            if len(visible_sats) >= 4:  # 至少需要4颗卫星进行定位
                # 计算CRLB
                crlb = self._calculate_crlb(user_lat, user_lon, visible_sats)
                crlb_values.append(crlb)
                
                # 计算GDOP
                gdop = self._calculate_gdop(user_lat, user_lon, visible_sats)
                gdop_values.append(gdop)
                
                # 计算平均SINR
                sinr = self._calculate_average_sinr(user_lat, user_lon, visible_sats)
                average_sinr.append(sinr)
                
                # 估计定位精度
                accuracy = self._estimate_positioning_accuracy(crlb, gdop, sinr)
                positioning_accuracy.append(accuracy)
            else:
                # 可见卫星不足，定位质量很差
                crlb_values.append(float('inf'))
                gdop_values.append(float('inf'))
                average_sinr.append(0.0)
                positioning_accuracy.append(0.0)
        
        # 计算整体覆盖质量
        coverage_quality = self._calculate_coverage_quality(
            visible_satellites_count, positioning_accuracy
        )
        
        return PositioningMetrics(
            time_step=time_step,
            user_locations=user_locations,
            crlb_values=crlb_values,
            gdop_values=gdop_values,
            visible_satellites_count=visible_satellites_count,
            average_sinr=average_sinr,
            positioning_accuracy=positioning_accuracy,
            coverage_quality=coverage_quality
        )
    
    def execute_flow_allocation(self, flow: FlowRequest, route: List[int], bandwidth: float) -> bool:
        """执行流量分配到网络"""
        if not self.initialized:
            raise RuntimeError("Hypatia适配器未初始化")
        
        try:
            # 在ns3仿真器中添加流量
            success = self.simulator.add_flow(flow, route, bandwidth)
            
            if success:
                self.logger.debug(f"成功分配流量 {flow.flow_id}: 路由={route}, 带宽={bandwidth}Mbps")
            else:
                self.logger.warning(f"流量分配失败 {flow.flow_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"执行流量分配时出错: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取当前性能指标"""
        if not self.initialized:
            return {}
        
        return self.simulator.get_performance_metrics()
    
    def step_simulation(self, time_step: float) -> None:
        """推进仿真一个时间步"""
        if not self.initialized:
            raise RuntimeError("Hypatia适配器未初始化")
        
        # 更新星座状态
        self.constellation_manager.update_time(self.current_time + time_step)
        
        # 推进ns3仿真
        self.simulator.step(time_step)
        
        self.current_time += time_step
    
    def _get_visible_satellites(self, user_lat: float, user_lon: float, 
                              satellites: List[Dict[str, Any]], time_step: float) -> List[Dict[str, Any]]:
        """计算用户可见的卫星"""
        visible_sats = []
        
        for sat in satellites:
            # 计算卫星与用户的仰角
            elevation = self._calculate_elevation_angle(
                user_lat, user_lon, sat['lat'], sat['lon'], sat['alt']
            )
            
            # 仰角大于10度认为可见
            if elevation > 10.0:
                sat_copy = sat.copy()
                sat_copy['elevation'] = elevation
                visible_sats.append(sat_copy)
        
        return visible_sats
    
    def _calculate_elevation_angle(self, user_lat: float, user_lon: float,
                                 sat_lat: float, sat_lon: float, sat_alt: float) -> float:
        """计算卫星仰角"""
        # 简化的仰角计算
        # 实际应该使用更精确的球面几何计算
        
        # 转换为弧度
        user_lat_rad = np.radians(user_lat)
        user_lon_rad = np.radians(user_lon)
        sat_lat_rad = np.radians(sat_lat)
        sat_lon_rad = np.radians(sat_lon)
        
        # 计算角距离
        dlat = sat_lat_rad - user_lat_rad
        dlon = sat_lon_rad - user_lon_rad
        
        a = np.sin(dlat/2)**2 + np.cos(user_lat_rad) * np.cos(sat_lat_rad) * np.sin(dlon/2)**2
        angular_distance = 2 * np.arcsin(np.sqrt(a))
        
        # 地球半径 (km)
        earth_radius = 6371.0
        
        # 计算仰角
        distance = earth_radius * angular_distance
        elevation_rad = np.arctan(sat_alt / distance)
        elevation_deg = np.degrees(elevation_rad)
        
        return max(0.0, elevation_deg)
    
    def _calculate_crlb(self, user_lat: float, user_lon: float, 
                       visible_sats: List[Dict[str, Any]]) -> float:
        """计算克拉美-罗下界（CRLB）"""
        # 简化的CRLB计算
        # 实际应该基于信号功率、噪声、几何配置等
        
        if len(visible_sats) < 4:
            return float('inf')
        
        # 基于可见卫星数量和几何配置的简化计算
        n_sats = len(visible_sats)
        
        # 计算几何因子
        elevations = [sat['elevation'] for sat in visible_sats]
        avg_elevation = np.mean(elevations)
        elevation_spread = np.std(elevations)
        
        # CRLB与卫星数量成反比，与几何配置相关
        base_crlb = 10.0  # 基础CRLB (米)
        crlb = base_crlb / np.sqrt(n_sats) * (1.0 / (1.0 + avg_elevation/90.0)) * (1.0 / (1.0 + elevation_spread/45.0))
        
        return max(0.1, crlb)
    
    def _calculate_gdop(self, user_lat: float, user_lon: float, 
                       visible_sats: List[Dict[str, Any]]) -> float:
        """计算几何精度因子（GDOP）"""
        # 简化的GDOP计算
        
        if len(visible_sats) < 4:
            return float('inf')
        
        # 基于卫星几何分布的简化计算
        elevations = [sat['elevation'] for sat in visible_sats]
        
        # GDOP与卫星分布的均匀性相关
        avg_elevation = np.mean(elevations)
        elevation_spread = np.std(elevations)
        
        # 理想情况下GDOP接近1，几何配置差时会增大
        gdop = 1.0 + 5.0 / (1.0 + avg_elevation/30.0) + 3.0 / (1.0 + elevation_spread/20.0)
        
        return max(1.0, gdop)
    
    def _calculate_average_sinr(self, user_lat: float, user_lon: float, 
                              visible_sats: List[Dict[str, Any]]) -> float:
        """计算平均信噪比"""
        if not visible_sats:
            return 0.0
        
        # 简化的SINR计算，基于仰角
        sinr_values = []
        for sat in visible_sats:
            elevation = sat['elevation']
            # SINR随仰角增加而改善
            sinr_db = 10.0 + elevation * 0.5  # 简化模型
            sinr_values.append(sinr_db)
        
        return np.mean(sinr_values)
    
    def _estimate_positioning_accuracy(self, crlb: float, gdop: float, sinr: float) -> float:
        """估计定位精度"""
        if crlb == float('inf') or gdop == float('inf'):
            return 0.0
        
        # 定位精度与CRLB、GDOP成反比，与SINR成正比
        accuracy = 1.0 / (crlb * gdop) * (sinr / 20.0)  # 归一化到0-1
        
        return min(1.0, max(0.0, accuracy))
    
    def _calculate_coverage_quality(self, visible_counts: List[int], 
                                  accuracies: List[float]) -> float:
        """计算整体覆盖质量"""
        if not visible_counts:
            return 0.0
        
        # 基于可见卫星数量和定位精度的综合评估
        coverage_ratio = sum(1 for count in visible_counts if count >= 4) / len(visible_counts)
        avg_accuracy = np.mean([acc for acc in accuracies if acc > 0])
        
        if np.isnan(avg_accuracy):
            avg_accuracy = 0.0
        
        coverage_quality = 0.7 * coverage_ratio + 0.3 * avg_accuracy
        
        return min(1.0, max(0.0, coverage_quality))

    def _calculate_topology_matrix(self, satellites: List[Dict[str, Any]], time_step: float):
        """计算网络拓扑矩阵"""
        n_sats = len(satellites)
        topology = np.zeros((n_sats, n_sats), dtype=int)

        # 基于ISL配置计算连接
        for isl in self.isls:
            sat1_id, sat2_id = isl
            if sat1_id < n_sats and sat2_id < n_sats:
                # 检查距离是否在ISL范围内
                distance = self._calculate_satellite_distance(
                    satellites[sat1_id], satellites[sat2_id]
                )

                # 最大ISL距离约5000km
                if distance <= 5000.0:
                    topology[sat1_id][sat2_id] = 1
                    topology[sat2_id][sat1_id] = 1

        return topology

    def _calculate_link_states(self, satellites: List[Dict[str, Any]], time_step: float) -> List[Dict[str, Any]]:
        """计算链路状态"""
        links = []

        for isl in self.isls:
            sat1_id, sat2_id = isl
            if sat1_id < len(satellites) and sat2_id < len(satellites):
                sat1, sat2 = satellites[sat1_id], satellites[sat2_id]

                # 计算距离
                distance = self._calculate_satellite_distance(sat1, sat2)

                if distance <= 5000.0:  # 最大ISL距离
                    # 计算传播延迟
                    propagation_delay = distance / 299792.458  # 光速传播延迟 (ms)

                    # 简化的容量模型
                    base_capacity = 10.0  # Gbps
                    capacity = base_capacity * (1.0 - distance / 10000.0)
                    capacity = max(1.0, capacity)

                    link = {
                        'source_id': sat1_id,
                        'dest_id': sat2_id,
                        'distance_km': distance,
                        'propagation_delay_ms': propagation_delay,
                        'capacity_gbps': capacity,
                        'available': True,
                        'quality': 1.0 - distance / 5000.0
                    }

                    links.append(link)

        return links

    def _calculate_satellite_distance(self, sat1: Dict[str, Any], sat2: Dict[str, Any]) -> float:
        """计算两颗卫星之间的距离"""
        x1, y1, z1 = sat1['x'], sat1['y'], sat1['z']
        x2, y2, z2 = sat2['x'], sat2['y'], sat2['z']

        distance = np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        return distance
