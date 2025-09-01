"""
GDOP计算器

实现几何精度因子（Geometric Dilution of Precision）计算。
包括GDOP、PDOP、HDOP、VDOP等各种精度因子。
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any


class GDOPCalculator:
    """GDOP计算器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.earth_radius_km = 6371.0
    
    def calculate(self, user_location: Tuple[float, float], 
                 visible_satellites: List[Dict[str, Any]]) -> float:
        """计算GDOP"""
        if len(visible_satellites) < 4:
            return float('inf')
        
        try:
            # 构建几何矩阵
            geometry_matrix = self._build_geometry_matrix(user_location, visible_satellites)
            
            # 计算GDOP
            gdop = self._calculate_gdop_from_matrix(geometry_matrix)
            return gdop
            
        except Exception:
            return float('inf')
    
    def calculate_all_dops(self, user_location: Tuple[float, float], 
                          visible_satellites: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算所有DOP值"""
        if len(visible_satellites) < 4:
            return {
                'gdop': float('inf'),
                'pdop': float('inf'),
                'hdop': float('inf'),
                'vdop': float('inf'),
                'tdop': float('inf')
            }
        
        try:
            geometry_matrix = self._build_geometry_matrix(user_location, visible_satellites)
            
            # 计算协方差矩阵
            gtg = geometry_matrix.T @ geometry_matrix
            cov_matrix = np.linalg.inv(gtg)
            
            # 计算各种DOP
            gdop = math.sqrt(np.trace(cov_matrix))  # 几何精度因子
            pdop = math.sqrt(np.trace(cov_matrix[:3, :3]))  # 位置精度因子
            hdop = math.sqrt(cov_matrix[0, 0] + cov_matrix[1, 1])  # 水平精度因子
            vdop = math.sqrt(cov_matrix[2, 2])  # 垂直精度因子
            tdop = math.sqrt(cov_matrix[3, 3])  # 时间精度因子
            
            return {
                'gdop': gdop,
                'pdop': pdop,
                'hdop': hdop,
                'vdop': vdop,
                'tdop': tdop
            }
            
        except (np.linalg.LinAlgError, Exception):
            return {
                'gdop': float('inf'),
                'pdop': float('inf'),
                'hdop': float('inf'),
                'vdop': float('inf'),
                'tdop': float('inf')
            }
    
    def _build_geometry_matrix(self, user_location: Tuple[float, float], 
                             visible_satellites: List[Dict[str, Any]]) -> np.ndarray:
        """构建几何矩阵"""
        user_lat, user_lon = user_location
        n_sats = len(visible_satellites)
        
        # 转换用户位置为笛卡尔坐标
        user_x, user_y, user_z = self._geodetic_to_cartesian(user_lat, user_lon, 0.0)
        
        # 几何矩阵：每行对应一颗卫星，列为[dx/dr, dy/dr, dz/dr, 1]
        geometry_matrix = np.zeros((n_sats, 4))
        
        for i, sat in enumerate(visible_satellites):
            # 卫星位置
            sat_lat, sat_lon, sat_alt = sat['lat'], sat['lon'], sat['alt']
            sat_x, sat_y, sat_z = self._geodetic_to_cartesian(sat_lat, sat_lon, sat_alt)
            
            # 计算距离和方向
            dx = sat_x - user_x
            dy = sat_y - user_y
            dz = sat_z - user_z
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            
            if distance > 0:
                # 单位方向向量
                geometry_matrix[i, 0] = -dx / distance  # 东向
                geometry_matrix[i, 1] = -dy / distance  # 北向
                geometry_matrix[i, 2] = -dz / distance  # 天向
                geometry_matrix[i, 3] = 1.0  # 时钟偏差项
        
        return geometry_matrix
    
    def _calculate_gdop_from_matrix(self, geometry_matrix: np.ndarray) -> float:
        """从几何矩阵计算GDOP"""
        try:
            gtg = geometry_matrix.T @ geometry_matrix
            cov_matrix = np.linalg.inv(gtg)
            gdop = math.sqrt(np.trace(cov_matrix))
            return gdop
        except np.linalg.LinAlgError:
            return float('inf')
    
    def _geodetic_to_cartesian(self, lat_deg: float, lon_deg: float, alt_km: float) -> Tuple[float, float, float]:
        """将大地坐标转换为笛卡尔坐标"""
        lat_rad = math.radians(lat_deg)
        lon_rad = math.radians(lon_deg)
        
        # 地球半径加高度
        r = (self.earth_radius_km + alt_km) * 1000  # 转换为米
        
        x = r * math.cos(lat_rad) * math.cos(lon_rad)
        y = r * math.cos(lat_rad) * math.sin(lon_rad)
        z = r * math.sin(lat_rad)
        
        return x, y, z
    
    def calculate_satellite_geometry_quality(self, user_location: Tuple[float, float], 
                                           visible_satellites: List[Dict[str, Any]]) -> float:
        """计算卫星几何配置质量"""
        if len(visible_satellites) < 4:
            return 0.0
        
        try:
            # 计算卫星分布的均匀性
            elevations = [sat.get('elevation', 0.0) for sat in visible_satellites]
            azimuths = [sat.get('azimuth', 0.0) for sat in visible_satellites]
            
            # 仰角分布质量
            elevation_quality = self._calculate_elevation_distribution_quality(elevations)
            
            # 方位角分布质量
            azimuth_quality = self._calculate_azimuth_distribution_quality(azimuths)
            
            # GDOP质量
            gdop = self.calculate(user_location, visible_satellites)
            gdop_quality = 1.0 / (1.0 + gdop / 5.0) if gdop != float('inf') else 0.0
            
            # 综合质量评估
            overall_quality = (0.4 * elevation_quality + 
                             0.3 * azimuth_quality + 
                             0.3 * gdop_quality)
            
            return min(1.0, max(0.0, overall_quality))
            
        except Exception:
            return 0.0
    
    def _calculate_elevation_distribution_quality(self, elevations: List[float]) -> float:
        """计算仰角分布质量"""
        if not elevations:
            return 0.0
        
        # 理想情况：有高仰角卫星，分布均匀
        avg_elevation = np.mean(elevations)
        elevation_spread = np.std(elevations)
        
        # 平均仰角越高越好（但不要过高）
        avg_quality = min(1.0, avg_elevation / 60.0)
        
        # 分布越均匀越好
        spread_quality = min(1.0, elevation_spread / 30.0)
        
        return 0.7 * avg_quality + 0.3 * spread_quality
    
    def _calculate_azimuth_distribution_quality(self, azimuths: List[float]) -> float:
        """计算方位角分布质量"""
        if len(azimuths) < 4:
            return 0.0
        
        # 计算方位角的均匀分布程度
        # 理想情况：卫星在各个方向均匀分布
        
        # 将方位角分为8个扇区，计算每个扇区的卫星数量
        sectors = [0] * 8
        for azimuth in azimuths:
            sector = int(azimuth / 45.0) % 8
            sectors[sector] += 1
        
        # 计算分布均匀性
        total_sats = len(azimuths)
        expected_per_sector = total_sats / 8.0
        
        # 使用标准差衡量均匀性
        sector_std = np.std(sectors)
        uniformity = 1.0 / (1.0 + sector_std / expected_per_sector)
        
        return uniformity
    
    def calculate_time_varying_gdop(self, user_location: Tuple[float, float], 
                                  satellite_trajectories: List[List[Dict[str, Any]]], 
                                  time_points: List[float]) -> List[float]:
        """计算时变GDOP"""
        gdop_values = []
        
        for i, time_point in enumerate(time_points):
            if i < len(satellite_trajectories):
                visible_sats = satellite_trajectories[i]
                gdop = self.calculate(user_location, visible_sats)
                gdop_values.append(gdop)
            else:
                gdop_values.append(float('inf'))
        
        return gdop_values
    
    def find_optimal_satellite_subset(self, user_location: Tuple[float, float], 
                                    visible_satellites: List[Dict[str, Any]], 
                                    max_satellites: int = 8) -> List[Dict[str, Any]]:
        """找到最优的卫星子集以最小化GDOP"""
        if len(visible_satellites) <= max_satellites:
            return visible_satellites
        
        from itertools import combinations
        
        best_gdop = float('inf')
        best_subset = visible_satellites[:max_satellites]
        
        # 尝试所有可能的组合（限制计算量）
        max_combinations = 1000
        combinations_tried = 0
        
        for subset in combinations(visible_satellites, max_satellites):
            if combinations_tried >= max_combinations:
                break
            
            gdop = self.calculate(user_location, list(subset))
            if gdop < best_gdop:
                best_gdop = gdop
                best_subset = list(subset)
            
            combinations_tried += 1
        
        return best_subset
