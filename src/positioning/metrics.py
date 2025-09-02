"""
定位指标计算模块

按照设计文档规范实现CRLB、GDOP、可见性等指标的统一计算接口
"""

import json
import math
import os
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from .crlb_calculator import CRLBCalculator
from .gdop_calculator import GDOPCalculator
from .beam_hint import generate_beam_hint_with_state


class PositioningMetrics:
    """统一的定位指标计算器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.crlb_calculator = CRLBCalculator(self.config)
        self.gdop_calculator = GDOPCalculator(self.config)
        
        # 阈值配置
        self.min_visible_satellites = self.config.get('min_visible_satellites', 4)
        self.min_cooperative_satellites = self.config.get('min_cooperative_satellites', 2)
        self.crlb_threshold_m = self.config.get('crlb_threshold_m', 50.0)
        self.gdop_threshold = self.config.get('gdop_threshold', 10.0)
        
    def calculate_comprehensive_metrics(self, 
                                      time_s: float,
                                      users: List[Dict[str, Any]], 
                                      network_state: Any = None,
                                      positioning_calculator: Any = None) -> Dict[str, Any]:
        """计算综合定位指标"""
        
        if not users:
            return self._get_default_metrics()
        
        # 收集所有用户的指标
        user_metrics = []
        for user in users:
            lat = user.get('lat') or user.get('latitude', 0.0)
            lon = user.get('lon') or user.get('longitude', 0.0)
            
            if positioning_calculator and network_state:
                # 使用真实的计算器
                visible_sats = positioning_calculator.get_visible_satellites(
                    (lat, lon), time_s, network_state
                )
                user_metric = self._calculate_user_metrics(
                    (lat, lon), visible_sats, time_s, network_state
                )
            else:
                # 使用模拟数据
                user_metric = self._get_simulated_user_metrics(time_s, lat, lon)
            
            user_metrics.append(user_metric)
        
        # 聚合指标
        aggregated = self._aggregate_user_metrics(user_metrics)
        
        # 添加波束提示
        if positioning_calculator and network_state:
            beam_hint = generate_beam_hint_with_state(
                time_s, users, {'beams_per_user': 2}, 
                network_state, positioning_calculator
            )
            aggregated['beam_hint'] = beam_hint
        else:
            aggregated['beam_hint'] = {'strategy': 'fallback', 'version': 1}
        
        return aggregated
    
    def _calculate_user_metrics(self, 
                               user_location: Tuple[float, float],
                               visible_satellites: List[Dict[str, Any]], 
                               time_s: float,
                               network_state: Any) -> Dict[str, Any]:
        """计算单个用户的定位指标"""
        
        num_visible = len(visible_satellites)
        if num_visible < 4:
            return {
                'crlb': float('inf'),
                'gdop': float('inf'),
                'visible_satellites': num_visible,
                'cooperative_satellites': 0,
                'signal_quality': 0.0,
                'geometry_quality': 0.0,
                'positioning_availability': 0.0
            }
        
        # 计算CRLB
        crlb = self.crlb_calculator.calculate(user_location, visible_satellites)
        
        # 计算GDOP系列
        gdop_dict = self.gdop_calculator.calculate_all_dops(user_location, visible_satellites)
        gdop = gdop_dict['gdop']
        
        # 计算信号质量
        signal_qualities = []
        for sat in visible_satellites:
            signal_strength = sat.get('signal_strength_dbm', -130.0)
            noise_power = self.crlb_calculator.noise_power_dbm
            snr_db = signal_strength - noise_power
            snr_linear = 10**(snr_db / 10.0)
            signal_qualities.append(min(1.0, snr_linear / 100.0))  # 归一化
        
        avg_signal_quality = np.mean(signal_qualities) if signal_qualities else 0.0
        min_signal_quality = np.min(signal_qualities) if signal_qualities else 0.0
        
        # 计算几何质量
        geometry_quality = self.gdop_calculator.calculate_satellite_geometry_quality(
            user_location, visible_satellites
        )
        
        # 计算协作卫星数量（基于信号质量阈值）
        cooperative_count = sum(1 for sq in signal_qualities if sq > 0.3)
        
        # 计算定位可用性
        availability = self._calculate_positioning_availability(
            crlb, gdop, num_visible, cooperative_count
        )
        
        return {
            'crlb': crlb,
            'gdop': gdop,
            'gdop_dict': gdop_dict,
            'visible_satellites': num_visible,
            'cooperative_satellites': cooperative_count,
            'signal_quality_avg': avg_signal_quality,
            'signal_quality_min': min_signal_quality,
            'geometry_quality': geometry_quality,
            'positioning_availability': availability
        }
    
    def _calculate_positioning_availability(self, 
                                          crlb: float, 
                                          gdop: float,
                                          visible_count: int, 
                                          cooperative_count: int) -> float:
        """计算定位可用性指标 A^pos"""
        
        # 基本可用性条件
        if (visible_count < self.min_visible_satellites or 
            cooperative_count < self.min_cooperative_satellites):
            return 0.0
        
        # CRLB评分
        if crlb == float('inf') or crlb > self.crlb_threshold_m:
            crlb_score = 0.0
        else:
            crlb_score = max(0.0, 1.0 - crlb / self.crlb_threshold_m)
        
        # GDOP评分
        if gdop == float('inf') or gdop > self.gdop_threshold:
            gdop_score = 0.0
        else:
            gdop_score = max(0.0, 1.0 - (gdop - 1.0) / (self.gdop_threshold - 1.0))
        
        # 可见性评分
        visibility_score = min(1.0, visible_count / 10.0)
        
        # 协作度评分
        cooperation_score = min(1.0, cooperative_count / 6.0)
        
        # 加权组合
        weights = self.config.get('availability_weights', {
            'crlb': 0.35,
            'gdop': 0.25, 
            'visibility': 0.25,
            'cooperation': 0.15
        })
        
        availability = (weights['crlb'] * crlb_score +
                       weights['gdop'] * gdop_score +
                       weights['visibility'] * visibility_score +
                       weights['cooperation'] * cooperation_score)
        
        return min(1.0, max(0.0, availability))
    
    def get_drl_state_features(self, user_metrics: Dict[str, Any]) -> Dict[str, float]:
        """为DRL状态向量生成归一化的定位特征"""
        
        # 归一化CRLB
        crlb = user_metrics.get('crlb', float('inf'))
        if crlb == float('inf') or crlb > self.crlb_threshold_m:
            crlb_norm = 1.0
        else:
            crlb_norm = crlb / self.crlb_threshold_m
            
        # 归一化GDOP
        gdop = user_metrics.get('gdop', float('inf'))
        if gdop == float('inf') or gdop > self.gdop_threshold:
            gdop_norm = 1.0
        else:
            gdop_norm = max(0.0, (gdop - 1.0) / (self.gdop_threshold - 1.0))
            
        # 归一化可见波束/卫星数
        visible_count = user_metrics.get('visible_satellites', 0)
        visible_beams_cnt_norm = min(1.0, visible_count / 10.0) # 假设10个以上为良好
        
        # 归一化协作卫星数
        coop_count = user_metrics.get('cooperative_satellites', 0)
        coop_sat_cnt_norm = min(1.0, coop_count / 8.0) # 假设8个以上为良好
        
        # 归一化SINR (使用signal_quality_avg作为代理)
        mean_sinr_norm = user_metrics.get('signal_quality_avg', 0.0)
        
        return {
            'crlb_norm': crlb_norm,
            'gdop_norm': gdop_norm,
            'mean_sinr_norm': mean_sinr_norm,
            'visible_beams_cnt_norm': visible_beams_cnt_norm,
            'coop_sat_cnt_norm': coop_sat_cnt_norm,
        }
    
    def _get_simulated_user_metrics(self, time_s: float, lat: float, lon: float) -> Dict[str, Any]:
        """生成模拟的用户指标（用于回退）"""
        phase = (time_s % 600) / 600.0
        location_factor = (lat + lon) / 180.0  # 简单的位置因子
        
        crlb = 6.0 + 4.0 * math.sin(2 * math.pi * phase + location_factor)
        gdop = max(1.0, 2.0 + 3.0 * math.cos(2 * math.pi * phase))
        visible = 4 + int(3 * abs(math.sin(2 * math.pi * phase)))
        coop = max(2, int(visible * 0.7))
        
        return {
            'crlb': max(1.0, crlb),
            'gdop': gdop,
            'visible_satellites': visible,
            'cooperative_satellites': coop,
            'signal_quality_avg': 0.6 + 0.3 * math.sin(phase * 2 * math.pi),
            'signal_quality_min': 0.3 + 0.2 * math.cos(phase * 2 * math.pi),
            'geometry_quality': 0.7 + 0.2 * math.sin(phase * 4 * math.pi),
            'positioning_availability': self._calculate_positioning_availability(
                crlb, gdop, visible, coop
            )
        }
    
    def _aggregate_user_metrics(self, user_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """聚合多个用户的指标"""
        if not user_metrics:
            return self._get_default_metrics()
        
        # 提取有效值
        crlb_values = [m['crlb'] for m in user_metrics if m['crlb'] != float('inf')]
        gdop_values = [m['gdop'] for m in user_metrics if m['gdop'] != float('inf')]
        
        # 计算统计量
        crlb_stats = {
            'mean': np.mean(crlb_values) if crlb_values else float('inf'),
            'p95': np.percentile(crlb_values, 95) if crlb_values else float('inf'),
            'min': np.min(crlb_values) if crlb_values else float('inf'),
            'max': np.max(crlb_values) if crlb_values else float('inf')
        }
        
        gdop_stats = {
            'mean': np.mean(gdop_values) if gdop_values else float('inf'),
            'p95': np.percentile(gdop_values, 95) if gdop_values else float('inf'),
            'min': np.min(gdop_values) if gdop_values else float('inf'),
            'max': np.max(gdop_values) if gdop_values else float('inf')
        }
        
        # 其他指标的平均值
        avg_visible = np.mean([m['visible_satellites'] for m in user_metrics])
        avg_coop = np.mean([m['cooperative_satellites'] for m in user_metrics])
        avg_signal_quality = np.mean([m['signal_quality_avg'] for m in user_metrics])
        min_signal_quality = np.min([m['signal_quality_min'] for m in user_metrics])
        avg_pos_availability = np.mean([m['positioning_availability'] for m in user_metrics])
        
        return {
            'crlb': crlb_stats,
            'gdop': gdop_stats,
            'visible_beams': avg_visible,
            'coop_sats': avg_coop,
            'sinr_avg': avg_signal_quality,  # 信号质量作为SINR代理
            'sinr_min': min_signal_quality,
            'pos_availability': avg_pos_availability,
            'user_count': len(user_metrics),
            'valid_positioning_users': len(crlb_values)
        }
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """返回默认指标"""
        return {
            'crlb': {'mean': float('inf'), 'p95': float('inf'), 'min': float('inf'), 'max': float('inf')},
            'gdop': {'mean': float('inf'), 'p95': float('inf'), 'min': float('inf'), 'max': float('inf')},
            'visible_beams': 0.0,
            'coop_sats': 0.0,
            'sinr_avg': 0.0,
            'sinr_min': 0.0,
            'pos_availability': 0.0,
            'user_count': 0,
            'valid_positioning_users': 0
        }


# 全局实例
_positioning_metrics = PositioningMetrics()


def metrics(t: int, users: List[Any]) -> Dict[str, Any]:
    """向后兼容的接口函数"""
    return _positioning_metrics.calculate_comprehensive_metrics(float(t), users)


def get_positioning_metrics_calculator(config: Optional[Dict[str, Any]] = None) -> PositioningMetrics:
    """获取定位指标计算器实例"""
    if config:
        return PositioningMetrics(config)
    return _positioning_metrics


