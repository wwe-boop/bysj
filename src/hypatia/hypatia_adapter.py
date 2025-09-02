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
    from satgen.tles.generate_tles_from_scratch import (
        generate_tles_from_scratch_manual,
        generate_tles_from_scratch_with_sgp,
    )
    from satgen.ground_stations.read_ground_stations import read_ground_stations_extended
    from satgen.ground_stations.extend_ground_stations import extend_ground_stations
    from satgen.isls.read_isls import read_isls
    from satgen.isls.generate_plus_grid_isls import generate_plus_grid_isls
    from satgen.interfaces.read_gsl_interfaces_info import read_gsl_interfaces_info
    from satgen.dynamic_state.generate_dynamic_state import generate_dynamic_state
    from satgen.distance_tools.distance_tools import (
        geodetic2cartesian,
    )
    from astropy import units as u
    # Skyfield 用于 TLE 推算
    from skyfield.api import EarthSatellite, load, wgs84
    HYPATIA_AVAILABLE = True
    logging.info("成功导入Hypatia模块")
except ImportError as e:
    logging.error(f"无法导入Hypatia模块: {e}")
    HYPATIA_AVAILABLE = False

try:
    from ..core.interfaces import HypatiaInterface
    from ..core.state import NetworkState, FlowRequest, PositioningMetrics, UserRequest
    from ..core.config import ConstellationConfig, BackendConfig
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    src_path = os.path.join(os.path.dirname(__file__), '..', '..')
    if src_path not in sys.path:
        sys.path.append(src_path)

    from core.interfaces import HypatiaInterface
    from core.state import NetworkState, FlowRequest, PositioningMetrics, UserRequest
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

        # 后端模式（仅 real 支持）
        self.ns3_mode: str = backend_config.ns3_mode
        self.use_simplified = False
        # 仅保留 real 模式，不再使用 ConstellationManager 简化分支
        self.constellation_manager: Optional[ConstellationManager] = None
        
        self._initialize()
    def initialize(self, constellation_config: Dict[str, Any]) -> None:
        """实现接口要求的初始化方法（已在构造函数内部完成）。"""
        # 允许运行时变更配置并重新初始化
        if constellation_config:
            try:
                # 仅更新已知字段
                for k, v in constellation_config.items():
                    if hasattr(self.constellation_config, k):
                        setattr(self.constellation_config, k, v)
            except Exception:
                pass
        if not self.initialized:
            self._initialize()
        else:
            self.logger.info("HypatiaAdapter 已初始化，跳过重复初始化")

    def _initialize(self):
        """根据后端配置初始化适配器"""
        try:
            self.logger.info("初始化Hypatia适配器...")

            if not HYPATIA_AVAILABLE:
                raise ImportError("Hypatia (satgenpy) 依赖不可用，无法启用 real 模式")

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

            # 可选：生成动态状态（昂贵）。当前按需计算网络状态，跳过预生成。

            self.simulation_start_time = time.time()
            self.initialized = True

            self.logger.info("Hypatia适配器初始化完成")

        except Exception as e:
            self.logger.error(f"Hypatia适配器初始化失败: {e}")
            raise
    
    def _initialize_simplified(self):
        """已移除，仅保留 real 模式"""
        raise NotImplementedError("仅支持 real 模式")

    def _generate_constellation(self):
        """生成卫星星座"""
        config = self.constellation_config
        # 生成TLE文件
        tles_filename = os.path.join(self.temp_gen_dir, "tles.txt")

        # 使用Hypatia的TLE生成功能
        # 使用 SGP4 生成更稳健的 TLE（避免 epoch 计算异常）
        generate_tles_from_scratch_with_sgp(
            tles_filename,
            config.name,
            config.num_orbits,
            config.num_sats_per_orbit,
            0,
            config.inclination_deg,
            config.eccentricity,
            config.arg_of_perigee_deg,
            0.0   # raan_offset_deg
        )

        # 统一将 TLE 纪元改为 2024-01-01（24001.00000000），并修正校验位
        self._fix_tles_epoch(tles_filename, epoch_yy="24", epoch_day_str="001.00000000")

        # 读取生成的卫星信息
        tles = read_tles(tles_filename)
        self.satellites = tles["satellites"]
        self.epoch = tles["epoch"]
        self.logger.info(f"生成了{len(self.satellites)}颗卫星")
        # Skyfield 卫星对象
        self.sf_satellites = []
        with open(tles_filename, 'r') as f:
            lines = f.read().splitlines()
        i = 1
        while i + 2 < len(lines):
            name = lines[i]
            l1 = lines[i+1]
            l2 = lines[i+2]
            self.sf_satellites.append(EarthSatellite(l1, l2, name))
            i += 3
        # 时间尺度
        self.ts = load.timescale()

    def _fix_tles_epoch(self, filename: str, epoch_yy: str, epoch_day_str: str) -> None:
        """重写 TLE 第1行的纪元字段（列 19-32），同时重算校验位。"""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            # 第一行是 "<n_orbits> <n_sats_per_orbit>\n"，之后按 3 行一组
            i = 1
            while i + 2 < len(lines):
                # name 行: lines[i]
                l1 = lines[i + 1].rstrip('\n')
                l2 = lines[i + 2].rstrip('\n')
                if len(l1) >= 69 and l1.startswith('1 '):
                    # 列 0..67（68个字符）重新生成，列 18:20 年份，20:32 年儒略日
                    l1_body = list(l1)
                    l1_body[18:20] = list(epoch_yy)
                    # 确保 epoch_day_str 长度为 12
                    epoch_field = epoch_day_str
                    if len(epoch_field) < 12:
                        epoch_field = epoch_field + ('0' * (12 - len(epoch_field)))
                    l1_body[20:32] = list(epoch_field)
                    # 重新计算校验（前 68 位）
                    body_68 = ''.join(l1_body[:68])
                    s = 0
                    for ch in body_68:
                        if ch.isdigit():
                            s += int(ch)
                        if ch == '-':
                            s += 1
                    checksum = str(s % 10)
                    l1_new = body_68 + checksum
                    lines[i + 1] = l1_new + '\n'
                i += 3
            with open(filename, 'w') as f:
                f.writelines(lines)
            self.logger.info("已将 TLE 纪元统一为 2024-01-01 并修正校验位")
        except Exception as e:
            self.logger.warning(f"修正 TLE 纪元失败（忽略继续）: {e}")

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
        gs_basic = os.path.join(self.temp_gen_dir, "ground_stations.txt")
        gs_extended = os.path.join(self.temp_gen_dir, "ground_stations_extended.txt")
        self._generate_ground_stations_file(gs_basic, major_cities)
        extend_ground_stations(gs_basic, gs_extended)
        self.ground_stations = read_ground_stations_extended(gs_extended)
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
            1, 0
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

        output_dynamic_state_dir = os.path.join(self.temp_gen_dir, "dynamic_state")
        os.makedirs(output_dynamic_state_dir, exist_ok=True)
        # 描述文件中的阈值
        max_gsl_length_m = 1089686.0
        max_isl_length_m = 5016062.5
        generate_dynamic_state(
            output_dynamic_state_dir,
            self.epoch,
            int(self.simulation_end_time_s * 1e9),
            int(self.dynamic_state_update_interval_ms * 1e6),
            0,
            self.satellites,
            self.ground_stations,
            self.isls,
            self.gsl_interfaces_info,
            max_gsl_length_m,
            max_isl_length_m,
            "algorithm_free_one_only_over_isls",
            False
        )
        self.logger.info("动态状态生成完成")

    def get_network_state(self, time_step: float) -> NetworkState:
        """获取当前时刻的网络状态"""
        if not self.initialized:
            raise RuntimeError("Hypatia适配器未初始化")

        self.current_time = time_step

        # 基于 TLE 计算卫星位置与三维坐标
        # 计算当前时间（datetime）用于 Skyfield 推算
        try:
            epoch_dt = self.epoch.datetime
        except Exception:
            import datetime as _dt
            epoch_dt = _dt.datetime(2024, 1, 1, 0, 0, 0)
        import datetime as _dt
        t_sec = 1.0 if (time_step is None or time_step <= 0) else float(time_step)
        date_dt = epoch_dt + _dt.timedelta(seconds=t_sec)
        satellite_positions = []
        # 计算时间：避免与 TLE epoch 完全相同导致的计算异常，加入微小正偏移
        # Skyfield 推算子星点与高度
        t_sf = self.ts.utc(date_dt.year, date_dt.month, date_dt.day, date_dt.hour, date_dt.minute, date_dt.second)
        satellite_positions = []
        for sid, sf_sat in enumerate(self.sf_satellites):
            geocentric = sf_sat.at(t_sf)
            sp = wgs84.subpoint(geocentric)
            lat = sp.latitude.degrees
            lon = sp.longitude.degrees
            alt_m = sp.elevation.m
            x, y, z = geodetic2cartesian(lat, lon, alt_m)
            satellite_positions.append({'id': sid, 'lat': lat, 'lon': lon, 'alt': self.constellation_config.altitude_km, 'x': x, 'y': y, 'z': z})

        # 基于 ISL 计算链路与拓扑（直接按当前时刻计算，避免预生成动态状态依赖）
        num_sats = len(self.satellites)
        topology = np.zeros((num_sats, num_sats))
        links = []
        id_to_xyz = {s['id']: (s['x'], s['y'], s['z']) for s in satellite_positions}
        for (a, b) in self.isls:
            x1, y1, z1 = id_to_xyz[a]
            x2, y2, z2 = id_to_xyz[b]
            dist_km = ((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2) ** 0.5 / 1000.0
            propagation_delay = dist_km / 299792.458
            base_capacity = 10.0
            capacity = max(1.0, base_capacity * (1.0 - min(dist_km, 10000.0) / 10000.0))
            links.append({'source_id': a, 'dest_id': b, 'distance_km': dist_km, 'propagation_delay_ms': propagation_delay, 'capacity_gbps': capacity, 'available': True})
            topology[a][b] = 1
            topology[b][a] = 1

        link_utilization = {(l['source_id'], l['dest_id']): 0.0 for l in links}
        link_capacity = {(l['source_id'], l['dest_id']): l['capacity_gbps'] for l in links}

        return NetworkState(time_step=time_step, satellites=satellite_positions, links=links, topology=topology, link_utilization=link_utilization, link_capacity=link_capacity, active_flows=[], queue_lengths={i: 0 for i in range(len(satellite_positions))})
    
    def get_positioning_metrics(self, time_step: float, 
                              user_locations: List[Tuple[float, float]]) -> PositioningMetrics:
        """获取定位相关指标"""
        if not self.initialized:
            raise RuntimeError("Hypatia适配器未初始化")
        
        # 获取卫星位置（基于 TLE）
        epoch_str = str(self.epoch)
        date_str = str(self.epoch + time_step * u.s)
        satellites = []
        for sid, sat in enumerate(self.satellites):
            gs_shadow = create_basic_ground_station_for_satellite_shadow(sat, epoch_str, date_str)
            satellites.append({'id': sid, 'lat': float(gs_shadow['latitude_degrees_str']), 'lon': float(gs_shadow['longitude_degrees_str']), 'alt': self.constellation_config.altitude_km})
        
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
        
        # 更新时间（基于 TLE 推进）
        # 若存在 ns3 模拟器，推进其内部时间
        if hasattr(self, 'simulator') and self.simulator is not None:
            try:
                self.simulator.step(time_step)
            except Exception:
                pass
        
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

    def get_orbit_phase(self, time_step: Optional[float] = None) -> float:
        """获取星座轨道相位（简化）"""
        current_time = time_step if time_step is not None else self.current_time
        # 假设轨道周期为96分钟
        orbit_period = 96 * 60
        return (current_time % orbit_period) / orbit_period

    def get_topology_change_rate(self) -> float:
        """获取拓扑变化率（简化）"""
        # 这是一个简化实现，实际需要对比不同时间点的拓扑
        # 返回一个固定的小值，表示拓扑在缓慢变化
        return 0.01
    
    def predict_future_capacity(self, horizon_s: int) -> float:
        """预测未来网络容量（简化）"""
        # 近似：以当前 ISL 容量和为基线，做固定折减
        try:
            epoch_str = str(self.epoch)
            date_str = str(self.epoch + (self.current_time) * u.s)
            # 以当前链路容量之和做基准
            current_state = self.get_network_state(self.current_time)
            current_capacity = sum(l.get('capacity_gbps', 0.0) for l in current_state.links)
        except Exception:
            current_capacity = 0.0
        return max(0.0, current_capacity * 0.95)

    def get_routing_stability_metrics(self, user_request: 'UserRequest') -> Dict[str, Any]:
        """获取路由与切换稳定性指标（占位）"""
        # 这是一个占位符实现，实际需要复杂的预测模型
        return {
            'handover_pred_count_norm': 0.1,  # 预测切换次数（归一化）
            'earliest_handover_norm': 0.8,    # 最早切换时间（归一化）
            'seam_flag': 0.0,                 # 跨缝风险标志
            'contact_margin_norm': 0.9        # 接触裕度（归一化）
        }

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
