"""
流量生成器

生成各种类型的用户流量模式
"""

import random
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.core.state import UserRequest


@dataclass
class TrafficPattern:
    """流量模式"""
    name: str
    arrival_rate: float  # 每秒到达率
    service_types: List[str]
    service_weights: List[float]
    bandwidth_range: Tuple[float, float]  # (min, max) Mbps
    duration_range: Tuple[float, float]  # (min, max) seconds
    priority_range: Tuple[int, int]  # (min, max)
    geographic_distribution: str  # "uniform", "clustered", "hotspot"


class TrafficGenerator:
    """流量生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 基础参数
        self.flow_arrival_rate = config.get('flow_arrival_rate', 10.0)  # flows per second
        self.flow_duration_mean = config.get('flow_duration_mean', 60.0)  # seconds
        self.flow_duration_std = config.get('flow_duration_std', 20.0)
        
        # 用户分布
        self.num_users = config.get('num_users', 100)
        self.user_distribution = config.get('user_distribution', 'uniform')
        
        # 地理范围
        self.lat_range = config.get('lat_range', (-60.0, 60.0))
        self.lon_range = config.get('lon_range', (-180.0, 180.0))
        
        # 流量模式
        self.traffic_patterns = self._initialize_traffic_patterns()
        self.current_pattern = self.traffic_patterns[0]
        
        # 状态
        self.user_counter = 0
        self.request_history = []
        
        # 热点区域
        self.hotspots = self._generate_hotspots()
        
        self.logger.info(f"流量生成器初始化: 到达率={self.flow_arrival_rate}/s, "
                        f"用户数={self.num_users}, 分布={self.user_distribution}")
    
    def _initialize_traffic_patterns(self) -> List[TrafficPattern]:
        """初始化流量模式"""
        patterns = [
            # 数据流量模式
            TrafficPattern(
                name="data_heavy",
                arrival_rate=8.0,
                service_types=["data", "video", "voice"],
                service_weights=[0.6, 0.3, 0.1],
                bandwidth_range=(1.0, 50.0),
                duration_range=(30.0, 300.0),
                priority_range=(1, 7),
                geographic_distribution="uniform"
            ),
            
            # 视频流量模式
            TrafficPattern(
                name="video_streaming",
                arrival_rate=5.0,
                service_types=["video", "data"],
                service_weights=[0.8, 0.2],
                bandwidth_range=(5.0, 25.0),
                duration_range=(120.0, 1800.0),
                priority_range=(3, 8),
                geographic_distribution="clustered"
            ),
            
            # 紧急通信模式
            TrafficPattern(
                name="emergency",
                arrival_rate=2.0,
                service_types=["emergency", "voice"],
                service_weights=[0.7, 0.3],
                bandwidth_range=(0.5, 10.0),
                duration_range=(10.0, 120.0),
                priority_range=(8, 10),
                geographic_distribution="hotspot"
            ),
            
            # 导航服务模式
            TrafficPattern(
                name="navigation",
                arrival_rate=12.0,
                service_types=["navigation", "location_based", "data"],
                service_weights=[0.5, 0.3, 0.2],
                bandwidth_range=(0.1, 5.0),
                duration_range=(60.0, 600.0),
                priority_range=(4, 7),
                geographic_distribution="uniform"
            ),
            
            # 混合流量模式
            TrafficPattern(
                name="mixed",
                arrival_rate=10.0,
                service_types=["data", "video", "voice", "navigation", "location_based"],
                service_weights=[0.4, 0.25, 0.15, 0.15, 0.05],
                bandwidth_range=(0.5, 30.0),
                duration_range=(30.0, 600.0),
                priority_range=(1, 8),
                geographic_distribution="uniform"
            )
        ]
        
        return patterns
    
    def _generate_hotspots(self) -> List[Dict[str, Any]]:
        """生成热点区域"""
        hotspots = [
            # 主要城市热点
            {"lat": 40.7128, "lon": -74.0060, "radius": 50.0, "intensity": 3.0},  # 纽约
            {"lat": 35.6762, "lon": 139.6503, "radius": 40.0, "intensity": 2.5},  # 东京
            {"lat": 51.5074, "lon": -0.1278, "radius": 35.0, "intensity": 2.0},   # 伦敦
            {"lat": 37.7749, "lon": -122.4194, "radius": 30.0, "intensity": 2.2}, # 旧金山
            {"lat": 55.7558, "lon": 37.6176, "radius": 45.0, "intensity": 1.8},   # 莫斯科
            {"lat": -33.8688, "lon": 151.2093, "radius": 25.0, "intensity": 1.5}, # 悉尼
        ]
        
        return hotspots
    
    def generate_requests(self, current_time: float, time_step: float) -> List[UserRequest]:
        """生成指定时间段内的用户请求"""
        requests = []
        
        try:
            # 计算该时间段内的请求数量
            expected_requests = self.current_pattern.arrival_rate * time_step
            num_requests = np.random.poisson(expected_requests)
            
            for _ in range(num_requests):
                request = self._generate_single_request(current_time)
                if request:
                    requests.append(request)
                    self.request_history.append(request)
            
            # 保持历史记录大小
            if len(self.request_history) > 10000:
                self.request_history = self.request_history[-5000:]
            
            if requests:
                self.logger.debug(f"生成{len(requests)}个用户请求 @ t={current_time:.1f}s")
            
            return requests
            
        except Exception as e:
            self.logger.error(f"生成用户请求失败: {e}")
            return []
    
    def _generate_single_request(self, current_time: float) -> Optional[UserRequest]:
        """生成单个用户请求"""
        try:
            # 生成用户ID
            self.user_counter += 1
            user_id = f"user_{self.user_counter}_{int(current_time)}"
            
            # 选择服务类型
            service_type = np.random.choice(
                self.current_pattern.service_types,
                p=self.current_pattern.service_weights
            )
            
            # 生成带宽需求
            bandwidth_mbps = np.random.uniform(
                self.current_pattern.bandwidth_range[0],
                self.current_pattern.bandwidth_range[1]
            )
            
            # 生成持续时间
            duration_seconds = max(10.0, np.random.normal(
                self.flow_duration_mean, self.flow_duration_std
            ))
            
            # 生成QoS要求
            max_latency_ms, min_reliability = self._generate_qos_requirements(service_type)
            
            # 生成优先级
            priority = np.random.randint(
                self.current_pattern.priority_range[0],
                self.current_pattern.priority_range[1] + 1
            )
            
            # 生成地理位置
            user_lat, user_lon = self._generate_user_location()
            
            return UserRequest(
                user_id=user_id,
                service_type=service_type,
                bandwidth_mbps=round(bandwidth_mbps, 2),
                max_latency_ms=max_latency_ms,
                min_reliability=min_reliability,
                priority=priority,
                user_lat=user_lat,
                user_lon=user_lon,
                duration_seconds=round(duration_seconds, 1),
                timestamp=current_time
            )
            
        except Exception as e:
            self.logger.error(f"生成单个用户请求失败: {e}")
            return None
    
    def _generate_qos_requirements(self, service_type: str) -> Tuple[float, float]:
        """根据服务类型生成QoS要求"""
        qos_profiles = {
            "voice": (50.0, 0.99),      # 低延迟，高可靠性
            "video": (100.0, 0.95),     # 中等延迟，高可靠性
            "data": (200.0, 0.90),      # 较高延迟，中等可靠性
            "emergency": (30.0, 0.999), # 极低延迟，极高可靠性
            "navigation": (80.0, 0.98), # 低延迟，高可靠性
            "location_based": (150.0, 0.92)  # 中等延迟，中等可靠性
        }
        
        base_latency, base_reliability = qos_profiles.get(service_type, (200.0, 0.90))
        
        # 添加一些随机变化
        latency_variation = np.random.uniform(0.8, 1.2)
        reliability_variation = np.random.uniform(0.95, 1.0)
        
        max_latency_ms = base_latency * latency_variation
        min_reliability = min(0.999, base_reliability * reliability_variation)
        
        return max_latency_ms, min_reliability
    
    def _generate_user_location(self) -> Tuple[float, float]:
        """生成用户地理位置"""
        distribution = self.current_pattern.geographic_distribution
        
        if distribution == "uniform":
            # 均匀分布
            lat = np.random.uniform(self.lat_range[0], self.lat_range[1])
            lon = np.random.uniform(self.lon_range[0], self.lon_range[1])
            
        elif distribution == "clustered":
            # 聚集分布（围绕热点）
            if self.hotspots and np.random.random() < 0.7:  # 70%概率在热点附近
                hotspot = np.random.choice(self.hotspots)
                # 在热点周围生成位置
                angle = np.random.uniform(0, 2 * np.pi)
                distance = np.random.exponential(hotspot["radius"] / 3)
                
                lat = hotspot["lat"] + (distance / 111.0) * np.cos(angle)  # 1度≈111km
                lon = hotspot["lon"] + (distance / (111.0 * np.cos(np.radians(hotspot["lat"])))) * np.sin(angle)
            else:
                # 其余在随机位置
                lat = np.random.uniform(self.lat_range[0], self.lat_range[1])
                lon = np.random.uniform(self.lon_range[0], self.lon_range[1])
                
        elif distribution == "hotspot":
            # 热点分布（主要在热点区域）
            if self.hotspots:
                # 根据热点强度选择
                weights = [h["intensity"] for h in self.hotspots]
                hotspot = np.random.choice(self.hotspots, p=np.array(weights)/sum(weights))
                
                # 在热点内生成位置
                angle = np.random.uniform(0, 2 * np.pi)
                distance = np.random.uniform(0, hotspot["radius"])
                
                lat = hotspot["lat"] + (distance / 111.0) * np.cos(angle)
                lon = hotspot["lon"] + (distance / (111.0 * np.cos(np.radians(hotspot["lat"])))) * np.sin(angle)
            else:
                # 回退到均匀分布
                lat = np.random.uniform(self.lat_range[0], self.lat_range[1])
                lon = np.random.uniform(self.lon_range[0], self.lon_range[1])
        
        else:
            # 默认均匀分布
            lat = np.random.uniform(self.lat_range[0], self.lat_range[1])
            lon = np.random.uniform(self.lon_range[0], self.lon_range[1])
        
        # 确保在有效范围内
        lat = np.clip(lat, self.lat_range[0], self.lat_range[1])
        lon = np.clip(lon, self.lon_range[0], self.lon_range[1])
        
        return round(lat, 4), round(lon, 4)
    
    def set_traffic_pattern(self, pattern_name: str) -> bool:
        """设置流量模式"""
        for pattern in self.traffic_patterns:
            if pattern.name == pattern_name:
                self.current_pattern = pattern
                self.logger.info(f"切换到流量模式: {pattern_name}")
                return True
        
        self.logger.warning(f"未找到流量模式: {pattern_name}")
        return False
    
    def get_available_patterns(self) -> List[str]:
        """获取可用的流量模式"""
        return [pattern.name for pattern in self.traffic_patterns]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取流量生成统计"""
        if not self.request_history:
            return {
                'total_requests': 0,
                'service_type_distribution': {},
                'avg_bandwidth': 0.0,
                'avg_duration': 0.0,
                'geographic_spread': 0.0
            }
        
        # 服务类型分布
        service_types = [req.service_type for req in self.request_history]
        service_distribution = {}
        for service_type in set(service_types):
            service_distribution[service_type] = service_types.count(service_type)
        
        # 平均指标
        avg_bandwidth = np.mean([req.bandwidth_mbps for req in self.request_history])
        avg_duration = np.mean([req.duration_seconds for req in self.request_history])
        
        # 地理分布
        lats = [req.user_lat for req in self.request_history]
        lons = [req.user_lon for req in self.request_history]
        geographic_spread = np.sqrt(np.var(lats) + np.var(lons))
        
        return {
            'total_requests': len(self.request_history),
            'current_pattern': self.current_pattern.name,
            'service_type_distribution': service_distribution,
            'avg_bandwidth': avg_bandwidth,
            'avg_duration': avg_duration,
            'geographic_spread': geographic_spread,
            'hotspots_count': len(self.hotspots)
        }
    
    def reset(self):
        """重置流量生成器"""
        self.user_counter = 0
        self.request_history.clear()
        self.logger.info("流量生成器已重置")
