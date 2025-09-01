"""
协作定位

实现多用户协作定位算法，利用用户间的相对位置信息
提高整体定位精度。
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional


class CooperativePositioning:
    """协作定位算法"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.earth_radius_km = 6371.0
        
        # 协作定位参数
        self.max_cooperation_distance_km = config.get('max_cooperation_distance_km', 50.0)
        self.min_common_satellites = config.get('min_common_satellites', 3)
        self.cooperation_weight = config.get('cooperation_weight', 0.3)
    
    def calculate_improvement(self, user_location: Tuple[float, float], 
                            visible_satellites: List[Dict[str, Any]], 
                            network_state) -> float:
        """计算协作定位带来的精度改善"""
        try:
            # 基础定位精度（单用户）
            base_accuracy = self._calculate_base_accuracy(user_location, visible_satellites)
            
            # 寻找协作伙伴
            cooperation_partners = self._find_cooperation_partners(
                user_location, visible_satellites, network_state
            )
            
            if not cooperation_partners:
                return base_accuracy
            
            # 计算协作定位精度
            cooperative_accuracy = self._calculate_cooperative_accuracy(
                user_location, visible_satellites, cooperation_partners
            )
            
            # 返回改善后的精度
            return max(base_accuracy, cooperative_accuracy)
            
        except Exception:
            return self._calculate_base_accuracy(user_location, visible_satellites)
    
    def _calculate_base_accuracy(self, user_location: Tuple[float, float], 
                               visible_satellites: List[Dict[str, Any]]) -> float:
        """计算基础定位精度"""
        if len(visible_satellites) < 4:
            return 0.0
        
        # 简化的精度计算
        n_sats = len(visible_satellites)
        avg_elevation = np.mean([sat.get('elevation', 0.0) for sat in visible_satellites])
        
        # 基于卫星数量和平均仰角的简化精度模型
        base_accuracy = 1.0 / (1.0 + n_sats / 10.0) * (1.0 + avg_elevation / 90.0)
        
        return min(1.0, max(0.0, base_accuracy))
    
    def _find_cooperation_partners(self, user_location: Tuple[float, float], 
                                 user_satellites: List[Dict[str, Any]], 
                                 network_state) -> List[Dict[str, Any]]:
        """寻找协作定位伙伴"""
        partners = []
        
        # 模拟其他用户位置（实际应该从网络状态获取）
        other_users = self._generate_nearby_users(user_location)
        
        for other_user in other_users:
            other_location = (other_user['lat'], other_user['lon'])
            
            # 检查距离是否在协作范围内
            distance = self._calculate_distance(user_location, other_location)
            if distance > self.max_cooperation_distance_km:
                continue
            
            # 获取其他用户的可见卫星
            other_satellites = self._get_user_visible_satellites(other_location, network_state)
            
            # 检查共同可见卫星数量
            common_satellites = self._find_common_satellites(user_satellites, other_satellites)
            if len(common_satellites) < self.min_common_satellites:
                continue
            
            # 添加为协作伙伴
            partner = {
                'location': other_location,
                'satellites': other_satellites,
                'common_satellites': common_satellites,
                'distance': distance,
                'cooperation_strength': self._calculate_cooperation_strength(
                    user_location, other_location, common_satellites
                )
            }
            partners.append(partner)
        
        # 按协作强度排序
        partners.sort(key=lambda x: x['cooperation_strength'], reverse=True)
        
        # 返回最多3个最佳协作伙伴
        return partners[:3]
    
    def _generate_nearby_users(self, user_location: Tuple[float, float]) -> List[Dict[str, Any]]:
        """生成附近的用户（模拟）"""
        user_lat, user_lon = user_location
        nearby_users = []
        
        # 在用户周围生成一些随机用户
        for i in range(5):
            # 随机偏移（±0.5度，约±50km）
            lat_offset = (np.random.random() - 0.5) * 1.0
            lon_offset = (np.random.random() - 0.5) * 1.0
            
            nearby_user = {
                'id': f'user_{i}',
                'lat': user_lat + lat_offset,
                'lon': user_lon + lon_offset
            }
            nearby_users.append(nearby_user)
        
        return nearby_users
    
    def _get_user_visible_satellites(self, user_location: Tuple[float, float], 
                                   network_state) -> List[Dict[str, Any]]:
        """获取用户可见的卫星（简化实现）"""
        # 这里应该调用定位计算器的get_visible_satellites方法
        # 为了避免循环依赖，这里使用简化实现
        
        visible_sats = []
        for sat in network_state.satellites:
            # 简化的可见性检查
            elevation = self._calculate_elevation_angle(
                user_location[0], user_location[1], 
                sat['lat'], sat['lon'], sat['alt']
            )
            
            if elevation > 10.0:  # 仰角大于10度
                sat_copy = sat.copy()
                sat_copy['elevation'] = elevation
                visible_sats.append(sat_copy)
        
        return visible_sats
    
    def _find_common_satellites(self, user1_sats: List[Dict[str, Any]], 
                              user2_sats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """找到两个用户的共同可见卫星"""
        user1_ids = {sat['id'] for sat in user1_sats}
        user2_ids = {sat['id'] for sat in user2_sats}
        
        common_ids = user1_ids.intersection(user2_ids)
        
        common_sats = []
        for sat in user1_sats:
            if sat['id'] in common_ids:
                common_sats.append(sat)
        
        return common_sats
    
    def _calculate_cooperation_strength(self, user1_location: Tuple[float, float], 
                                      user2_location: Tuple[float, float], 
                                      common_satellites: List[Dict[str, Any]]) -> float:
        """计算协作强度"""
        # 基于距离和共同卫星数量的协作强度
        distance = self._calculate_distance(user1_location, user2_location)
        n_common = len(common_satellites)
        
        # 距离越近，共同卫星越多，协作强度越高
        distance_factor = 1.0 / (1.0 + distance / self.max_cooperation_distance_km)
        satellite_factor = min(1.0, n_common / 8.0)
        
        cooperation_strength = 0.6 * distance_factor + 0.4 * satellite_factor
        
        return cooperation_strength
    
    def _calculate_cooperative_accuracy(self, user_location: Tuple[float, float], 
                                      user_satellites: List[Dict[str, Any]], 
                                      partners: List[Dict[str, Any]]) -> float:
        """计算协作定位精度"""
        # 基础精度
        base_accuracy = self._calculate_base_accuracy(user_location, user_satellites)
        
        # 协作改善
        cooperation_improvement = 0.0
        
        for partner in partners:
            # 基于协作强度和几何配置计算改善
            strength = partner['cooperation_strength']
            common_sats = partner['common_satellites']
            
            # 几何多样性改善
            geometry_improvement = self._calculate_geometry_improvement(
                user_location, partner['location'], common_sats
            )
            
            cooperation_improvement += strength * geometry_improvement
        
        # 限制协作改善的最大值
        cooperation_improvement = min(0.3, cooperation_improvement)
        
        # 计算最终精度
        cooperative_accuracy = base_accuracy + self.cooperation_weight * cooperation_improvement
        
        return min(1.0, max(0.0, cooperative_accuracy))
    
    def _calculate_geometry_improvement(self, user1_location: Tuple[float, float], 
                                      user2_location: Tuple[float, float], 
                                      common_satellites: List[Dict[str, Any]]) -> float:
        """计算几何配置改善"""
        if len(common_satellites) < 3:
            return 0.0
        
        # 计算两个用户位置的基线向量
        baseline_distance = self._calculate_distance(user1_location, user2_location)
        
        # 基线越长（在合理范围内），几何配置改善越大
        baseline_factor = min(1.0, baseline_distance / 20.0)  # 20km为最优基线
        
        # 共同卫星的几何分布
        elevations = [sat.get('elevation', 0.0) for sat in common_satellites]
        avg_elevation = np.mean(elevations)
        elevation_factor = min(1.0, avg_elevation / 45.0)
        
        geometry_improvement = 0.5 * baseline_factor + 0.5 * elevation_factor
        
        return geometry_improvement
    
    def _calculate_distance(self, loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
        """计算两点间的距离（km）"""
        lat1, lon1 = loc1
        lat2, lon2 = loc2
        
        # 使用Haversine公式
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        distance = self.earth_radius_km * c
        return distance
    
    def _calculate_elevation_angle(self, user_lat: float, user_lon: float,
                                 sat_lat: float, sat_lon: float, sat_alt: float) -> float:
        """计算卫星仰角（简化实现）"""
        # 简化的仰角计算
        lat_diff = abs(sat_lat - user_lat)
        lon_diff = abs(sat_lon - user_lon)
        angular_distance = math.sqrt(lat_diff**2 + lon_diff**2)
        
        # 基于角距离和高度的简化仰角计算
        if angular_distance == 0:
            return 90.0
        
        elevation = math.degrees(math.atan(sat_alt / (angular_distance * 111.0)))  # 111km/度
        return max(0.0, elevation)
