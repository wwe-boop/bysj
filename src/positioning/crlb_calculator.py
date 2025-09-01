"""
CRLB计算器

实现克拉美-罗下界（Cramér-Rao Lower Bound）计算。
用于评估定位精度的理论下界。
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any


class CRLBCalculator:
    """CRLB计算器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 信号参数
        self.signal_power_dbm = config.get('signal_power_dbm', -130.0)
        self.noise_power_dbm = config.get('noise_power_dbm', -140.0)
        self.carrier_frequency_hz = config.get('carrier_frequency_hz', 2.4e9)
        self.bandwidth_hz = config.get('bandwidth_hz', 20e6)
        
        # 物理常数
        self.speed_of_light = 299792458.0  # m/s
        self.earth_radius_km = 6371.0
    
    def calculate(self, user_location: Tuple[float, float], 
                 visible_satellites: List[Dict[str, Any]]) -> float:
        """计算CRLB"""
        if len(visible_satellites) < 4:
            return float('inf')
        
        try:
            # 构建几何矩阵
            geometry_matrix = self._build_geometry_matrix(user_location, visible_satellites)
            
            # 构建权重矩阵（基于信号质量）
            weight_matrix = self._build_weight_matrix(visible_satellites)
            
            # 计算Fisher信息矩阵
            fisher_matrix = geometry_matrix.T @ weight_matrix @ geometry_matrix
            
            # 计算CRLB（Fisher矩阵逆的迹）
            try:
                fisher_inv = np.linalg.inv(fisher_matrix)
                crlb = np.sqrt(np.trace(fisher_inv[:3, :3]))  # 只考虑位置（x,y,z）
                return crlb
            except np.linalg.LinAlgError:
                # 矩阵奇异，返回无穷大
                return float('inf')
                
        except Exception:
            return float('inf')
    
    def _build_geometry_matrix(self, user_location: Tuple[float, float], 
                             visible_satellites: List[Dict[str, Any]]) -> np.ndarray:
        """构建几何矩阵"""
        user_lat, user_lon = user_location
        n_sats = len(visible_satellites)
        
        # 转换用户位置为笛卡尔坐标
        user_x, user_y, user_z = self._geodetic_to_cartesian(user_lat, user_lon, 0.0)
        
        # 几何矩阵：每行对应一颗卫星，列为[dx/dr, dy/dr, dz/dr, c*dt/dr]
        geometry_matrix = np.zeros((n_sats, 4))
        
        for i, sat in enumerate(visible_satellites):
            # 卫星位置
            sat_lat, sat_lon, sat_alt = sat['lat'], sat['lon'], sat['alt']
            sat_x, sat_y, sat_z = self._geodetic_to_cartesian(sat_lat, sat_lon, sat_alt)
            
            # 计算距离
            dx = sat_x - user_x
            dy = sat_y - user_y
            dz = sat_z - user_z
            distance = math.sqrt(dx**2 + dy**2 + dz**2)
            
            if distance > 0:
                # 单位方向向量
                geometry_matrix[i, 0] = -dx / distance  # dx/dr
                geometry_matrix[i, 1] = -dy / distance  # dy/dr
                geometry_matrix[i, 2] = -dz / distance  # dz/dr
                geometry_matrix[i, 3] = 1.0  # c*dt/dr (时钟偏差项)
        
        return geometry_matrix
    
    def _build_weight_matrix(self, visible_satellites: List[Dict[str, Any]]) -> np.ndarray:
        """构建权重矩阵（基于信号质量）"""
        n_sats = len(visible_satellites)
        weight_matrix = np.zeros((n_sats, n_sats))
        
        for i, sat in enumerate(visible_satellites):
            # 计算信噪比
            signal_strength = sat.get('signal_strength_dbm', self.signal_power_dbm)
            snr_db = signal_strength - self.noise_power_dbm
            snr_linear = 10**(snr_db / 10.0)
            
            # 计算测距精度（基于信号带宽和SNR）
            range_accuracy = self._calculate_range_accuracy(snr_linear)
            
            # 权重为测距精度的倒数平方
            if range_accuracy > 0:
                weight_matrix[i, i] = 1.0 / (range_accuracy**2)
            else:
                weight_matrix[i, i] = 1e-10  # 避免除零
        
        return weight_matrix
    
    def _calculate_range_accuracy(self, snr_linear: float) -> float:
        """计算测距精度"""
        # 基于信号带宽和SNR的测距精度模型
        # σ_r = c / (2 * B * sqrt(2 * SNR))
        # 其中 c 是光速，B 是信号带宽，SNR 是信噪比
        
        if snr_linear <= 0:
            return float('inf')
        
        range_accuracy = self.speed_of_light / (2 * self.bandwidth_hz * math.sqrt(2 * snr_linear))
        return range_accuracy
    
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
    
    def calculate_position_crlb_3d(self, user_location: Tuple[float, float], 
                                  visible_satellites: List[Dict[str, Any]]) -> Tuple[float, float, float]:
        """计算3D位置的CRLB（分别返回x, y, z方向的精度）"""
        if len(visible_satellites) < 4:
            return float('inf'), float('inf'), float('inf')
        
        try:
            geometry_matrix = self._build_geometry_matrix(user_location, visible_satellites)
            weight_matrix = self._build_weight_matrix(visible_satellites)
            
            fisher_matrix = geometry_matrix.T @ weight_matrix @ geometry_matrix
            fisher_inv = np.linalg.inv(fisher_matrix)
            
            # 提取位置部分的协方差矩阵
            pos_cov = fisher_inv[:3, :3]
            
            # 计算各方向的标准差
            sigma_x = math.sqrt(pos_cov[0, 0])
            sigma_y = math.sqrt(pos_cov[1, 1])
            sigma_z = math.sqrt(pos_cov[2, 2])
            
            return sigma_x, sigma_y, sigma_z
            
        except (np.linalg.LinAlgError, Exception):
            return float('inf'), float('inf'), float('inf')
    
    def calculate_horizontal_crlb(self, user_location: Tuple[float, float], 
                                visible_satellites: List[Dict[str, Any]]) -> float:
        """计算水平方向的CRLB"""
        sigma_x, sigma_y, sigma_z = self.calculate_position_crlb_3d(user_location, visible_satellites)
        
        if sigma_x == float('inf') or sigma_y == float('inf'):
            return float('inf')
        
        # 水平精度为x和y方向精度的几何平均
        horizontal_crlb = math.sqrt(sigma_x**2 + sigma_y**2)
        return horizontal_crlb
    
    def calculate_vertical_crlb(self, user_location: Tuple[float, float], 
                              visible_satellites: List[Dict[str, Any]]) -> float:
        """计算垂直方向的CRLB"""
        sigma_x, sigma_y, sigma_z = self.calculate_position_crlb_3d(user_location, visible_satellites)
        return sigma_z
