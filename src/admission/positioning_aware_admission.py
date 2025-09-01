"""
定位感知的准入控制

结合定位质量指标的智能准入控制策略
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

from src.admission.admission_controller import AdmissionController, AdmissionResult, AdmissionDecision
from src.admission.threshold_admission import ThresholdAdmissionController
from src.admission.drl_admission import DRLAdmissionController
from src.core.state import NetworkState, UserRequest


class PositioningAwareAdmissionController(AdmissionController):
    """定位感知的准入控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 定位质量权重
        self.positioning_weight = config.get('positioning_weight', 0.3)
        self.qos_weight = config.get('qos_weight', 0.7)
        
        # 定位质量阈值
        self.min_visible_satellites = config.get('min_visible_satellites', 4)
        self.max_gdop_threshold = config.get('max_gdop_threshold', 10.0)
        self.min_positioning_accuracy = config.get('min_positioning_accuracy', 0.1)
        self.min_elevation_angle = config.get('min_elevation_angle', 10.0)
        
        # 基础准入控制器
        base_algorithm = config.get('base_algorithm', 'threshold')
        if base_algorithm == 'drl':
            try:
                self.base_controller = DRLAdmissionController(config)
            except ImportError:
                self.logger.warning("DRL不可用，回退到阈值控制")
                self.base_controller = ThresholdAdmissionController(config)
        else:
            self.base_controller = ThresholdAdmissionController(config)
        
        # 定位服务类型权重
        self.service_positioning_weights = {
            'navigation': 1.0,      # 导航服务对定位质量要求最高
            'emergency': 0.9,       # 紧急服务
            'location_based': 0.8,  # 基于位置的服务
            'voice': 0.3,          # 语音服务
            'video': 0.2,          # 视频服务
            'data': 0.1            # 数据服务
        }
        
        self.logger.info(f"初始化定位感知准入控制器: "
                        f"positioning_weight={self.positioning_weight}, "
                        f"min_visible_sats={self.min_visible_satellites}")
    
    def make_admission_decision(self, 
                              user_request: UserRequest,
                              network_state: NetworkState,
                              positioning_metrics: Optional[Dict[str, Any]] = None) -> AdmissionResult:
        """基于定位感知做出准入决策"""
        start_time = time.time()
        
        try:
            # 1. 获取基础准入决策
            base_result = self.base_controller.make_admission_decision(
                user_request, network_state, positioning_metrics
            )
            
            # 2. 如果没有定位信息，直接返回基础决策
            if positioning_metrics is None:
                self.logger.debug("无定位信息，使用基础决策")
                self._finalize_decision(base_result, start_time)
                return base_result
            
            # 3. 评估定位质量
            positioning_quality = self._evaluate_positioning_quality(
                user_request, positioning_metrics
            )
            
            # 4. 根据定位质量调整决策
            adjusted_result = self._adjust_decision_with_positioning(
                base_result, user_request, positioning_quality, positioning_metrics
            )
            
            self._finalize_decision(adjusted_result, start_time)
            return adjusted_result
            
        except Exception as e:
            self.logger.error(f"定位感知决策失败: {e}")
            # 回退到基础决策
            fallback_result = self.base_controller.make_admission_decision(
                user_request, network_state, positioning_metrics
            )
            self._finalize_decision(fallback_result, start_time)
            return fallback_result
    
    def _evaluate_positioning_quality(self, 
                                    user_request: UserRequest,
                                    positioning_metrics: Dict[str, Any]) -> Dict[str, float]:
        """评估定位质量"""
        quality_metrics = {}
        
        # 1. 可见卫星数量评分
        visible_satellites = positioning_metrics.get('visible_satellites', [])
        visible_count = len(visible_satellites)
        
        if visible_count >= self.min_visible_satellites:
            satellite_score = min(1.0, visible_count / 10.0)  # 10颗卫星为满分
        else:
            satellite_score = 0.0
        
        quality_metrics['satellite_visibility'] = satellite_score
        
        # 2. GDOP评分
        gdop = positioning_metrics.get('gdop', float('inf'))
        if gdop != float('inf') and gdop > 0:
            gdop_score = max(0.0, 1.0 - (gdop - 1.0) / self.max_gdop_threshold)
        else:
            gdop_score = 0.0
        
        quality_metrics['gdop_quality'] = gdop_score
        
        # 3. 定位精度评分
        positioning_accuracy = positioning_metrics.get('positioning_accuracy', 0.0)
        accuracy_score = max(0.0, positioning_accuracy)
        quality_metrics['positioning_accuracy'] = accuracy_score
        
        # 4. 信号强度评分
        if visible_satellites:
            signal_strengths = [sat.get('signal_strength_dbm', -140) 
                              for sat in visible_satellites]
            avg_signal = np.mean(signal_strengths)
            # 将信号强度从[-140, -80]映射到[0, 1]
            signal_score = max(0.0, min(1.0, (avg_signal + 140) / 60.0))
        else:
            signal_score = 0.0
        
        quality_metrics['signal_strength'] = signal_score
        
        # 5. 几何分布评分
        if len(visible_satellites) >= 4:
            elevation_angles = [sat.get('elevation', 0) for sat in visible_satellites]
            elevation_spread = np.std(elevation_angles) if elevation_angles else 0
            geometry_score = min(1.0, elevation_spread / 45.0)  # 45度标准差为满分
        else:
            geometry_score = 0.0
        
        quality_metrics['geometry_distribution'] = geometry_score
        
        # 6. 综合定位质量评分
        weights = {
            'satellite_visibility': 0.3,
            'gdop_quality': 0.25,
            'positioning_accuracy': 0.25,
            'signal_strength': 0.15,
            'geometry_distribution': 0.05
        }
        
        overall_quality = sum(quality_metrics[key] * weights[key] 
                            for key in weights.keys())
        quality_metrics['overall_quality'] = overall_quality
        
        return quality_metrics
    
    def _adjust_decision_with_positioning(self, 
                                        base_result: AdmissionResult,
                                        user_request: UserRequest,
                                        positioning_quality: Dict[str, float],
                                        positioning_metrics: Dict[str, Any]) -> AdmissionResult:
        """根据定位质量调整决策"""
        
        # 获取服务类型的定位重要性
        service_positioning_importance = self.service_positioning_weights.get(
            user_request.service_type, 0.5
        )
        
        # 计算定位质量对决策的影响权重
        positioning_influence = self.positioning_weight * service_positioning_importance
        
        overall_quality = positioning_quality['overall_quality']
        
        # 根据基础决策和定位质量调整
        if base_result.decision == AdmissionDecision.ACCEPT:
            # 如果基础决策是接受，检查定位质量是否足够
            if overall_quality < 0.3 and service_positioning_importance > 0.7:
                # 定位质量太差且服务对定位要求高，降级或拒绝
                if overall_quality < 0.1:
                    return AdmissionResult(
                        decision=AdmissionDecision.REJECT,
                        reason="定位质量不足，无法提供服务",
                        positioning_metrics=positioning_quality
                    )
                else:
                    return AdmissionResult(
                        decision=AdmissionDecision.DEGRADED_ACCEPT,
                        allocated_bandwidth=base_result.allocated_bandwidth * 0.8,
                        allocated_satellite=base_result.allocated_satellite,
                        confidence=base_result.confidence * 0.8,
                        reason="定位质量一般，降级服务",
                        positioning_metrics=positioning_quality
                    )
            else:
                # 定位质量可接受，保持原决策但调整置信度
                confidence_boost = overall_quality * positioning_influence
                return AdmissionResult(
                    decision=base_result.decision,
                    allocated_bandwidth=base_result.allocated_bandwidth,
                    allocated_satellite=base_result.allocated_satellite,
                    confidence=min(1.0, base_result.confidence + confidence_boost),
                    reason=f"定位质量良好 (质量={overall_quality:.2f})",
                    positioning_metrics=positioning_quality
                )
        
        elif base_result.decision == AdmissionDecision.REJECT:
            # 如果基础决策是拒绝，检查是否因为定位质量好可以接受
            if overall_quality > 0.8 and service_positioning_importance < 0.3:
                # 定位质量很好且服务对定位要求不高，可以考虑降级接受
                return AdmissionResult(
                    decision=AdmissionDecision.DEGRADED_ACCEPT,
                    allocated_bandwidth=user_request.bandwidth_mbps * 0.5,
                    allocated_satellite=self._find_best_satellite(
                        user_request, None, positioning_metrics
                    ),
                    confidence=0.6,
                    reason="定位质量优秀，提供降级服务",
                    positioning_metrics=positioning_quality
                )
            else:
                # 保持拒绝决策
                return AdmissionResult(
                    decision=base_result.decision,
                    reason=f"{base_result.reason} (定位质量={overall_quality:.2f})",
                    positioning_metrics=positioning_quality
                )
        
        elif base_result.decision == AdmissionDecision.DEGRADED_ACCEPT:
            # 如果基础决策是降级接受，根据定位质量调整降级程度
            if overall_quality > 0.7:
                # 定位质量好，减少降级程度
                bandwidth_factor = 0.9
                confidence_boost = 0.1
            elif overall_quality < 0.3:
                # 定位质量差，增加降级程度
                bandwidth_factor = 0.6
                confidence_boost = -0.1
            else:
                # 定位质量一般，保持原降级程度
                bandwidth_factor = 0.8
                confidence_boost = 0.0
            
            return AdmissionResult(
                decision=base_result.decision,
                allocated_bandwidth=base_result.allocated_bandwidth * bandwidth_factor,
                allocated_satellite=base_result.allocated_satellite,
                confidence=max(0.1, min(1.0, base_result.confidence + confidence_boost)),
                reason=f"根据定位质量调整降级程度 (质量={overall_quality:.2f})",
                positioning_metrics=positioning_quality
            )
        
        else:
            # 其他决策类型，保持原决策但添加定位信息
            return AdmissionResult(
                decision=base_result.decision,
                allocated_bandwidth=base_result.allocated_bandwidth,
                allocated_satellite=base_result.allocated_satellite,
                confidence=base_result.confidence,
                delay_seconds=base_result.delay_seconds,
                reason=f"{base_result.reason} (定位质量={overall_quality:.2f})",
                positioning_metrics=positioning_quality
            )
    
    def _finalize_decision(self, result: AdmissionResult, start_time: float):
        """完成决策处理"""
        decision_time = time.time() - start_time
        self.decision_times.append(decision_time)
        self.update_statistics(result)
        
        positioning_quality = result.positioning_metrics.get('overall_quality', 0.0) \
                            if result.positioning_metrics else 0.0
        
        self.logger.debug(f"定位感知准入决策: {result.decision.value}, "
                         f"定位质量: {positioning_quality:.2f}, "
                         f"置信度: {result.confidence:.2f}, "
                         f"卫星: {result.allocated_satellite}, "
                         f"带宽: {result.allocated_bandwidth:.1f}Mbps")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息（包含定位相关统计）"""
        base_stats = super().get_statistics()
        
        # 添加定位相关统计
        base_stats['base_controller_stats'] = self.base_controller.get_statistics()
        
        return base_stats
