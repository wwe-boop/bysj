"""
定位计算器

实现PositioningInterface接口，提供完整的定位质量计算功能。
集成CRLB、GDOP、协作定位等算法。
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional
import math

from ..core.interfaces import PositioningInterface
from ..core.state import NetworkState, PositioningMetrics
from .crlb_calculator import CRLBCalculator
from .gdop_calculator import GDOPCalculator
from .cooperative_positioning import CooperativePositioning


class PositioningCalculator(PositioningInterface):
    """定位质量计算器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 初始化子模块
        self.crlb_calculator = CRLBCalculator(config)
        self.gdop_calculator = GDOPCalculator(config)
        self.cooperative_positioning = CooperativePositioning(config)
        
        # 定位参数
        self.signal_power_dbm = config.get('signal_power_dbm', -130.0)
        self.noise_power_dbm = config.get('noise_power_dbm', -140.0)
        self.carrier_frequency_hz = config.get('carrier_frequency_hz', 2.4e9)
        self.bandwidth_hz = config.get('bandwidth_hz', 20e6)
        self.elevation_mask_deg = config.get('elevation_mask_deg', 10.0)
        self.max_range_km = config.get('max_range_km', 2000.0)
        
        # 地球参数
        self.earth_radius_km = 6371.0
        self.speed_of_light = 299792458.0  # m/s
        
    def calculate_crlb(self, user_location: Tuple[float, float], 
                      visible_satellites: List[Dict[str, Any]]) -> float:
        """计算克拉美-罗下界（CRLB）"""
        return self.crlb_calculator.calculate(user_location, visible_satellites)
    
    def calculate_gdop(self, user_location: Tuple[float, float], 
                      visible_satellites: List[Dict[str, Any]]) -> float:
        """计算几何精度因子（GDOP）"""
        return self.gdop_calculator.calculate(user_location, visible_satellites)
    
    def get_visible_satellites(self, user_location: Tuple[float, float], 
                             time_step: float, network_state: NetworkState) -> List[Dict[str, Any]]:
        """获取用户可见的卫星列表"""
        user_lat, user_lon = user_location
        visible_sats = []
        
        for sat in network_state.satellites:
            # 计算仰角
            elevation = self._calculate_elevation_angle(
                user_lat, user_lon, sat['lat'], sat['lon'], sat['alt']
            )
            
            # 计算距离
            distance = self._calculate_distance(user_location, sat)
            
            # 检查可见性条件
            if (elevation >= self.elevation_mask_deg and 
                distance <= self.max_range_km and 
                sat.get('active', True)):
                
                # 计算信号强度
                signal_strength = self._calculate_signal_strength(distance, elevation)
                
                # 添加定位相关信息
                visible_sat = sat.copy()
                visible_sat.update({
                    'elevation': elevation,
                    'distance_km': distance,
                    'signal_strength_dbm': signal_strength,
                    'azimuth': self._calculate_azimuth(user_lat, user_lon, sat['lat'], sat['lon'])
                })
                
                visible_sats.append(visible_sat)
        
        # 按信号强度排序
        visible_sats.sort(key=lambda x: x['signal_strength_dbm'], reverse=True)
        
        return visible_sats
    
    def calculate_positioning_quality(self, user_locations: List[Tuple[float, float]], 
                                    network_state: NetworkState, time_step: float) -> PositioningMetrics:
        """计算整体定位质量指标"""
        crlb_values = []
        gdop_values = []
        visible_satellites_count = []
        average_sinr = []
        positioning_accuracy = []
        
        for user_location in user_locations:
            # 获取可见卫星
            visible_sats = self.get_visible_satellites(user_location, time_step, network_state)
            visible_satellites_count.append(len(visible_sats))
            
            if len(visible_sats) >= 4:  # 至少需要4颗卫星
                # 计算CRLB
                crlb = self.calculate_crlb(user_location, visible_sats)
                crlb_values.append(crlb)
                
                # 计算GDOP
                gdop = self.calculate_gdop(user_location, visible_sats)
                gdop_values.append(gdop)
                
                # 计算平均SINR
                sinr = self._calculate_average_sinr(visible_sats)
                average_sinr.append(sinr)
                
                # 计算定位精度
                accuracy = self._estimate_positioning_accuracy(crlb, gdop, sinr, len(visible_sats))
                positioning_accuracy.append(accuracy)
                
                # 尝试协作定位优化
                if len(visible_sats) >= 6:  # 足够的卫星进行协作定位
                    cooperative_accuracy = self.cooperative_positioning.calculate_improvement(
                        user_location, visible_sats, network_state
                    )
                    positioning_accuracy[-1] = max(positioning_accuracy[-1], cooperative_accuracy)
            else:
                # 可见卫星不足
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
    
    def _calculate_elevation_angle(self, user_lat: float, user_lon: float,
                                 sat_lat: float, sat_lon: float, sat_alt: float) -> float:
        """计算卫星仰角"""
        # 转换为弧度
        user_lat_rad = math.radians(user_lat)
        user_lon_rad = math.radians(user_lon)
        sat_lat_rad = math.radians(sat_lat)
        sat_lon_rad = math.radians(sat_lon)
        
        # 计算地面站和卫星的笛卡尔坐标
        user_r = self.earth_radius_km
        sat_r = self.earth_radius_km + sat_alt
        
        user_x = user_r * math.cos(user_lat_rad) * math.cos(user_lon_rad)
        user_y = user_r * math.cos(user_lat_rad) * math.sin(user_lon_rad)
        user_z = user_r * math.sin(user_lat_rad)
        
        sat_x = sat_r * math.cos(sat_lat_rad) * math.cos(sat_lon_rad)
        sat_y = sat_r * math.cos(sat_lat_rad) * math.sin(sat_lon_rad)
        sat_z = sat_r * math.sin(sat_lat_rad)
        
        # 从用户到卫星的向量
        dx = sat_x - user_x
        dy = sat_y - user_y
        dz = sat_z - user_z
        
        # 用户位置的法向量（指向天顶）
        norm_x = user_x / user_r
        norm_y = user_y / user_r
        norm_z = user_z / user_r
        
        # 计算仰角
        dot_product = dx * norm_x + dy * norm_y + dz * norm_z
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        if distance == 0:
            return 90.0
        
        elevation_rad = math.asin(max(-1.0, min(1.0, dot_product / distance)))
        elevation_deg = math.degrees(elevation_rad)
        
        return max(0.0, elevation_deg)
    
    def _calculate_azimuth(self, user_lat: float, user_lon: float,
                         sat_lat: float, sat_lon: float) -> float:
        """计算方位角"""
        user_lat_rad = math.radians(user_lat)
        user_lon_rad = math.radians(user_lon)
        sat_lat_rad = math.radians(sat_lat)
        sat_lon_rad = math.radians(sat_lon)
        
        dlon = sat_lon_rad - user_lon_rad
        
        y = math.sin(dlon) * math.cos(sat_lat_rad)
        x = (math.cos(user_lat_rad) * math.sin(sat_lat_rad) - 
             math.sin(user_lat_rad) * math.cos(sat_lat_rad) * math.cos(dlon))
        
        azimuth_rad = math.atan2(y, x)
        azimuth_deg = math.degrees(azimuth_rad)
        
        return (azimuth_deg + 360) % 360
    
    def _calculate_distance(self, user_location: Tuple[float, float], 
                          satellite: Dict[str, Any]) -> float:
        """计算用户与卫星之间的距离"""
        user_lat, user_lon = user_location
        sat_lat, sat_lon, sat_alt = satellite['lat'], satellite['lon'], satellite['alt']
        
        # 转换为弧度
        user_lat_rad = math.radians(user_lat)
        user_lon_rad = math.radians(user_lon)
        sat_lat_rad = math.radians(sat_lat)
        sat_lon_rad = math.radians(sat_lon)
        
        # 计算笛卡尔坐标
        user_r = self.earth_radius_km
        sat_r = self.earth_radius_km + sat_alt
        
        user_x = user_r * math.cos(user_lat_rad) * math.cos(user_lon_rad)
        user_y = user_r * math.cos(user_lat_rad) * math.sin(user_lon_rad)
        user_z = user_r * math.sin(user_lat_rad)
        
        sat_x = sat_r * math.cos(sat_lat_rad) * math.cos(sat_lon_rad)
        sat_y = sat_r * math.cos(sat_lat_rad) * math.sin(sat_lon_rad)
        sat_z = sat_r * math.sin(sat_lat_rad)
        
        # 计算欧几里得距离
        distance = math.sqrt((sat_x - user_x)**2 + (sat_y - user_y)**2 + (sat_z - user_z)**2)
        
        return distance
    
    def _calculate_signal_strength(self, distance_km: float, elevation_deg: float) -> float:
        """计算信号强度"""
        # 自由空间路径损耗
        distance_m = distance_km * 1000
        fspl_db = 20 * math.log10(distance_m) + 20 * math.log10(self.carrier_frequency_hz) - 147.55
        
        # 大气衰减（简化模型）
        atmospheric_loss_db = 0.1 * (90 - elevation_deg) / 90  # 仰角越低衰减越大
        
        # 接收信号强度
        received_power_dbm = self.signal_power_dbm - fspl_db - atmospheric_loss_db
        
        return received_power_dbm
    
    def _calculate_average_sinr(self, visible_satellites: List[Dict[str, Any]]) -> float:
        """计算平均信噪比"""
        if not visible_satellites:
            return 0.0
        
        sinr_values = []
        for sat in visible_satellites:
            signal_power_dbm = sat['signal_strength_dbm']
            
            # 计算SINR
            sinr_db = signal_power_dbm - self.noise_power_dbm
            sinr_values.append(sinr_db)
        
        return np.mean(sinr_values)
    
    def _estimate_positioning_accuracy(self, crlb: float, gdop: float, 
                                     sinr: float, num_satellites: int) -> float:
        """估计定位精度"""
        if crlb == float('inf') or gdop == float('inf'):
            return 0.0
        
        # 基于多个因素的综合评估
        # 1. CRLB因子（越小越好）
        crlb_factor = 1.0 / (1.0 + crlb / 10.0)
        
        # 2. GDOP因子（越小越好）
        gdop_factor = 1.0 / (1.0 + gdop / 5.0)
        
        # 3. SINR因子（越大越好）
        sinr_factor = min(1.0, max(0.0, (sinr + 10) / 30.0))
        
        # 4. 卫星数量因子
        sat_factor = min(1.0, (num_satellites - 4) / 6.0 + 0.5)
        
        # 综合评估
        accuracy = (0.3 * crlb_factor + 0.3 * gdop_factor + 
                   0.2 * sinr_factor + 0.2 * sat_factor)
        
        return min(1.0, max(0.0, accuracy))
    
    def _calculate_coverage_quality(self, visible_counts: List[int], 
                                  accuracies: List[float]) -> float:
        """计算整体覆盖质量"""
        if not visible_counts:
            return 0.0
        
        # 覆盖率：有足够卫星进行定位的用户比例
        coverage_ratio = sum(1 for count in visible_counts if count >= 4) / len(visible_counts)
        
        # 平均定位精度
        valid_accuracies = [acc for acc in accuracies if acc > 0]
        avg_accuracy = np.mean(valid_accuracies) if valid_accuracies else 0.0
        
        # 卫星分布均匀性
        avg_visible = np.mean(visible_counts)
        std_visible = np.std(visible_counts)
        uniformity = 1.0 / (1.0 + std_visible / max(1.0, avg_visible))
        
        # 综合质量评估
        coverage_quality = (0.5 * coverage_ratio + 0.3 * avg_accuracy + 0.2 * uniformity)
        
        return min(1.0, max(0.0, coverage_quality))
