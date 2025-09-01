"""
星座管理器

管理LEO卫星星座的轨道计算、位置更新、拓扑生成等功能。
支持多种星座配置（Starlink、Kuiper等）。
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional
import math
from pathlib import Path

try:
    from ..utils.tle_loader import TLELoader
    HAS_TLE = True
except Exception:
    HAS_TLE = False


class ConstellationManager:
    """LEO卫星星座管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 星座参数
        self.name = config.get('name', 'starlink')
        self.num_orbits = config.get('num_orbits', 72)
        self.num_sats_per_orbit = config.get('num_sats_per_orbit', 22)
        self.altitude_km = config.get('altitude_km', 550.0)
        self.inclination_deg = config.get('inclination_deg', 53.0)
        self.eccentricity = config.get('eccentricity', 0.0)
        
        # TLE 相关配置
        self.use_tle: bool = bool(config.get('use_tle', False)) and HAS_TLE
        self.tle_file: Optional[str] = config.get('tle_file')
        self.tle_loader: Optional[TLELoader] = None

        # 计算轨道参数（当未启用 TLE 或解析失败时使用简化模型）
        self.earth_radius_km = 6371.0
        self.orbital_radius_km = self.earth_radius_km + self.altitude_km
        self.orbital_period_sec = self._calculate_orbital_period()
        
        # 卫星状态
        self.satellites: List[Dict[str, Any]] = []
        self.current_time = 0.0
        
        self.logger.info(f"初始化星座: {self.name}, {self.num_orbits}轨道, "
                         f"每轨道{self.num_sats_per_orbit}颗卫星, 高度{self.altitude_km}km, "
                         f"use_tle={self.use_tle}")
    
    def initialize(self) -> None:
        """初始化卫星星座"""
        self.satellites = []

        # 若启用 TLE，尝试加载
        if self.use_tle and self.tle_file:
            try:
                tle_path = Path(self.tle_file)
                if not tle_path.exists():
                    self.logger.warning(f"TLE 文件不存在: {tle_path}，回退到简化星座")
                else:
                    self.tle_loader = TLELoader(str(tle_path))
                    num_loaded = self.tle_loader.load()
                    self.logger.info(f"TLE 加载完成，共 {num_loaded} 颗卫星")
                    # 使用 TLE 驱动位置更新，不再预生成简化卫星清单
                    return
            except Exception as e:
                self.logger.warning(f"TLE 加载失败，回退到简化星座: {e}")
                self.tle_loader = None

        # 简化模型：根据星座参数生成
        for orbit_idx in range(self.num_orbits):
            for sat_idx in range(self.num_sats_per_orbit):
                satellite = self._create_satellite(orbit_idx, sat_idx)
                self.satellites.append(satellite)

        self.logger.info(f"创建了{len(self.satellites)}颗卫星（简化模型）")
    
    def _create_satellite(self, orbit_idx: int, sat_idx: int) -> Dict[str, Any]:
        """创建单颗卫星"""
        # 计算轨道平面的升交点赤经
        raan_deg = (orbit_idx * 360.0 / self.num_orbits) % 360.0
        
        # 计算卫星在轨道中的平近点角
        mean_anomaly_deg = (sat_idx * 360.0 / self.num_sats_per_orbit) % 360.0
        
        satellite = {
            'id': orbit_idx * self.num_sats_per_orbit + sat_idx,
            'orbit_idx': orbit_idx,
            'sat_idx': sat_idx,
            'altitude_km': self.altitude_km,
            'inclination_deg': self.inclination_deg,
            'raan_deg': raan_deg,  # 升交点赤经
            'mean_anomaly_deg': mean_anomaly_deg,  # 平近点角
            'eccentricity': self.eccentricity,
            'lat': 0.0,  # 将在update_positions中计算
            'lon': 0.0,
            'alt': self.altitude_km,
            'velocity_kmps': self._calculate_orbital_velocity(),
            'active': True
        }
        
        return satellite
    
    def _calculate_orbital_period(self) -> float:
        """计算轨道周期（秒）"""
        # 使用开普勒第三定律
        GM = 3.986004418e14  # 地球引力参数 (m³/s²)
        a = self.orbital_radius_km * 1000  # 转换为米
        period = 2 * math.pi * math.sqrt(a**3 / GM)
        return period
    
    def _calculate_orbital_velocity(self) -> float:
        """计算轨道速度（km/s）"""
        GM = 3.986004418e5  # 地球引力参数 (km³/s²)
        v = math.sqrt(GM / self.orbital_radius_km)
        return v
    
    def update_time(self, time_seconds: float) -> None:
        """更新时间并重新计算卫星位置"""
        self.current_time = time_seconds
        self._update_satellite_positions()
    
    def _update_satellite_positions(self) -> None:
        """更新所有卫星的位置"""
        # 若使用 TLE：直接由 TLE 位置覆盖
        if self.use_tle and self.tle_loader is not None:
            tle_positions = self.tle_loader.positions_at_time(self.current_time)
            # 简化：将 TLE 返回的顺序作为 id 映射
            self.satellites = []
            for idx, p in enumerate(tle_positions):
                satellite = {
                    'id': idx,
                    'orbit_idx': 0,
                    'sat_idx': idx,
                    'altitude_km': p['alt'],
                    'inclination_deg': self.inclination_deg,
                    'raan_deg': 0.0,
                    'mean_anomaly_deg': 0.0,
                    'eccentricity': self.eccentricity,
                    'lat': p['lat'],
                    'lon': p['lon'],
                    'alt': p['alt'],
                    'velocity_kmps': self._calculate_orbital_velocity(),
                    'active': True
                }
                self.satellites.append(satellite)
            return

        for satellite in self.satellites:
            # 计算当前时刻的平近点角
            mean_motion = 2 * math.pi / self.orbital_period_sec  # rad/s
            current_mean_anomaly = (satellite['mean_anomaly_deg'] * math.pi / 180.0 + 
                                  mean_motion * self.current_time) % (2 * math.pi)
            
            # 计算真近点角（假设圆轨道，真近点角=平近点角）
            true_anomaly = current_mean_anomaly
            
            # 计算轨道坐标系中的位置
            r = self.orbital_radius_km
            x_orbit = r * math.cos(true_anomaly)
            y_orbit = r * math.sin(true_anomaly)
            z_orbit = 0.0
            
            # 转换到地心坐标系
            lat, lon, alt = self._orbit_to_geographic(
                x_orbit, y_orbit, z_orbit,
                satellite['inclination_deg'],
                satellite['raan_deg'],
                self.current_time
            )
            
            # 更新卫星位置
            satellite['lat'] = lat
            satellite['lon'] = lon
            satellite['alt'] = alt
    
    def _orbit_to_geographic(self, x_orbit: float, y_orbit: float, z_orbit: float,
                           inclination_deg: float, raan_deg: float, time_seconds: float) -> Tuple[float, float, float]:
        """将轨道坐标转换为地理坐标"""
        # 转换为弧度
        inc_rad = math.radians(inclination_deg)
        raan_rad = math.radians(raan_deg)
        
        # 地球自转角度
        earth_rotation_rate = 7.2921159e-5  # rad/s
        earth_rotation = earth_rotation_rate * time_seconds
        
        # 旋转矩阵：轨道坐标系 -> 地心坐标系
        cos_inc = math.cos(inc_rad)
        sin_inc = math.sin(inc_rad)
        cos_raan = math.cos(raan_rad)
        sin_raan = math.sin(raan_rad)
        
        # 应用旋转变换
        x_ecef = (cos_raan * x_orbit - sin_raan * cos_inc * y_orbit)
        y_ecef = (sin_raan * x_orbit + cos_raan * cos_inc * y_orbit)
        z_ecef = sin_inc * y_orbit
        
        # 考虑地球自转
        x_final = x_ecef * math.cos(earth_rotation) + y_ecef * math.sin(earth_rotation)
        y_final = -x_ecef * math.sin(earth_rotation) + y_ecef * math.cos(earth_rotation)
        z_final = z_ecef
        
        # 转换为地理坐标
        r = math.sqrt(x_final**2 + y_final**2 + z_final**2)
        lat = math.degrees(math.asin(z_final / r))
        lon = math.degrees(math.atan2(y_final, x_final))
        alt = r - self.earth_radius_km
        
        # 经度归一化到[-180, 180]
        lon = ((lon + 180) % 360) - 180
        
        return lat, lon, alt
    
    def get_satellite_positions(self, time_step: float) -> List[Dict[str, Any]]:
        """获取指定时刻的卫星位置"""
        if abs(time_step - self.current_time) > 1e-6:
            self.update_time(time_step)
        
        return [sat.copy() for sat in self.satellites if sat['active']]
    
    def get_topology_matrix(self, time_step: float) -> np.ndarray:
        """获取网络拓扑邻接矩阵"""
        satellites = self.get_satellite_positions(time_step)
        n_sats = len(satellites)
        
        # 初始化邻接矩阵
        topology = np.zeros((n_sats, n_sats), dtype=int)
        
        # 计算卫星间的连接
        for i, sat1 in enumerate(satellites):
            for j, sat2 in enumerate(satellites):
                if i != j and self._can_communicate(sat1, sat2):
                    topology[i][j] = 1
        
        return topology
    
    def _can_communicate(self, sat1: Dict[str, Any], sat2: Dict[str, Any]) -> bool:
        """判断两颗卫星是否可以通信"""
        # 计算两颗卫星之间的距离
        distance = self._calculate_distance(sat1, sat2)
        
        # 最大通信距离（简化模型）
        max_distance_km = 5000.0  # ISL最大距离
        
        # 同轨道内相邻卫星可以通信
        if (sat1['orbit_idx'] == sat2['orbit_idx'] and 
            abs(sat1['sat_idx'] - sat2['sat_idx']) <= 1):
            return distance <= max_distance_km
        
        # 相邻轨道的卫星可以通信
        orbit_diff = abs(sat1['orbit_idx'] - sat2['orbit_idx'])
        if orbit_diff == 1 or orbit_diff == self.num_orbits - 1:  # 考虑环形
            return distance <= max_distance_km
        
        return False
    
    def _calculate_distance(self, sat1: Dict[str, Any], sat2: Dict[str, Any]) -> float:
        """计算两颗卫星之间的距离"""
        # 转换为笛卡尔坐标
        lat1, lon1, alt1 = sat1['lat'], sat1['lon'], sat1['alt']
        lat2, lon2, alt2 = sat2['lat'], sat2['lon'], sat2['alt']
        
        # 转换为弧度
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
        
        # 计算笛卡尔坐标
        r1 = self.earth_radius_km + alt1
        r2 = self.earth_radius_km + alt2
        
        x1 = r1 * math.cos(lat1_rad) * math.cos(lon1_rad)
        y1 = r1 * math.cos(lat1_rad) * math.sin(lon1_rad)
        z1 = r1 * math.sin(lat1_rad)
        
        x2 = r2 * math.cos(lat2_rad) * math.cos(lon2_rad)
        y2 = r2 * math.cos(lat2_rad) * math.sin(lon2_rad)
        z2 = r2 * math.sin(lat2_rad)
        
        # 计算欧几里得距离
        distance = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        
        return distance
    
    def get_link_states(self, time_step: float) -> List[Dict[str, Any]]:
        """获取链路状态信息"""
        satellites = self.get_satellite_positions(time_step)
        topology = self.get_topology_matrix(time_step)
        
        links = []
        n_sats = len(satellites)
        
        for i in range(n_sats):
            for j in range(i+1, n_sats):  # 避免重复
                if topology[i][j] == 1:
                    sat1, sat2 = satellites[i], satellites[j]
                    distance = self._calculate_distance(sat1, sat2)
                    
                    # 计算链路质量指标
                    propagation_delay = distance / 299792.458  # 光速传播延迟 (ms)
                    
                    # 简化的链路容量模型
                    base_capacity = 10.0  # Gbps
                    capacity = base_capacity * (1.0 - distance / 10000.0)  # 距离衰减
                    capacity = max(1.0, capacity)  # 最小1Gbps
                    
                    link = {
                        'source_id': sat1['id'],
                        'dest_id': sat2['id'],
                        'distance_km': distance,
                        'propagation_delay_ms': propagation_delay,
                        'capacity_gbps': capacity,
                        'available': True,
                        'quality': 1.0 - distance / 10000.0  # 质量因子
                    }
                    
                    links.append(link)
        
        return links
    
    def get_satellite_by_id(self, sat_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取卫星信息"""
        for sat in self.satellites:
            if sat['id'] == sat_id:
                return sat.copy()
        return None
    
    def get_ground_station_coverage(self, gs_lat: float, gs_lon: float, 
                                  time_step: float, min_elevation: float = 10.0) -> List[int]:
        """获取地面站可见的卫星列表"""
        satellites = self.get_satellite_positions(time_step)
        visible_sats = []
        
        for sat in satellites:
            elevation = self._calculate_elevation_angle(
                gs_lat, gs_lon, sat['lat'], sat['lon'], sat['alt']
            )
            
            if elevation >= min_elevation:
                visible_sats.append(sat['id'])
        
        return visible_sats
    
    def _calculate_elevation_angle(self, gs_lat: float, gs_lon: float,
                                 sat_lat: float, sat_lon: float, sat_alt: float) -> float:
        """计算卫星相对于地面站的仰角"""
        # 转换为弧度
        gs_lat_rad = math.radians(gs_lat)
        gs_lon_rad = math.radians(gs_lon)
        sat_lat_rad = math.radians(sat_lat)
        sat_lon_rad = math.radians(sat_lon)
        
        # 计算地面站和卫星的笛卡尔坐标
        gs_r = self.earth_radius_km
        sat_r = self.earth_radius_km + sat_alt
        
        gs_x = gs_r * math.cos(gs_lat_rad) * math.cos(gs_lon_rad)
        gs_y = gs_r * math.cos(gs_lat_rad) * math.sin(gs_lon_rad)
        gs_z = gs_r * math.sin(gs_lat_rad)
        
        sat_x = sat_r * math.cos(sat_lat_rad) * math.cos(sat_lon_rad)
        sat_y = sat_r * math.cos(sat_lat_rad) * math.sin(sat_lon_rad)
        sat_z = sat_r * math.sin(sat_lat_rad)
        
        # 计算从地面站到卫星的向量
        dx = sat_x - gs_x
        dy = sat_y - gs_y
        dz = sat_z - gs_z
        
        # 计算地面站的法向量（指向天顶）
        norm_x = gs_x / gs_r
        norm_y = gs_y / gs_r
        norm_z = gs_z / gs_r
        
        # 计算仰角
        dot_product = dx * norm_x + dy * norm_y + dz * norm_z
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        if distance == 0:
            return 90.0
        
        elevation_rad = math.asin(dot_product / distance)
        elevation_deg = math.degrees(elevation_rad)
        
        return max(0.0, elevation_deg)
