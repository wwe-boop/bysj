"""
仿真引擎

整合所有模块的主仿真引擎
"""

import time
import logging
from typing import Dict, List, Any, Optional, Callable
import numpy as np
from dataclasses import dataclass

from src.core.config import SystemConfig
from src.core.state import NetworkState, UserRequest, SystemState, PerformanceMetrics
from src.hypatia.hypatia_adapter import HypatiaAdapter
from src.admission.admission_controller import AdmissionController
from src.admission.threshold_admission import ThresholdAdmissionController
from src.admission.positioning_aware_admission import PositioningAwareAdmissionController
from src.dsroq.dsroq_controller import DSROQController
from src.positioning.positioning_calculator import PositioningCalculator
from .traffic_generator import TrafficGenerator
from .event_scheduler import EventScheduler
from .performance_monitor import PerformanceMonitor


@dataclass
class SimulationResult:
    """仿真结果"""
    duration_seconds: float
    total_requests: int
    accepted_requests: int
    rejected_requests: int
    average_throughput: float
    average_latency: float
    qoe_score: float
    positioning_score: float
    system_efficiency: float
    detailed_metrics: Dict[str, Any]


class SimulationEngine:
    """仿真引擎"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 仿真参数
        self.duration = config.simulation.duration_seconds
        self.time_step = config.simulation.time_step_seconds
        self.current_time = 0.0
        self.is_running = False
        
        # 核心组件
        self.hypatia_adapter = None
        self.admission_controller = None
        self.dsroq_controller = None
        self.positioning_calculator = None
        
        # 仿真组件
        self.traffic_generator = None
        self.event_scheduler = None
        self.performance_monitor = None
        
        # 状态
        self.current_network_state = None
        self.current_positioning_metrics = None
        self.active_users = {}
        
        # 回调函数
        self.step_callbacks: List[Callable] = []
        self.result_callbacks: List[Callable] = []
        
        self.logger.info(f"仿真引擎初始化: 持续时间={self.duration}s, 时间步长={self.time_step}s")
    
    def initialize(self) -> bool:
        """初始化仿真环境"""
        try:
            self.logger.info("初始化仿真环境...")
            
            # 1. 初始化Hypatia适配器（支持后端模式切换）
            self.hypatia_adapter = HypatiaAdapter(self.config.backend.__dict__)
            self.hypatia_adapter.initialize(self.config.constellation.__dict__, self.config.backend.__dict__)
            self.logger.info("✓ Hypatia适配器初始化完成")
            
            # 2. 初始化准入控制器
            self._initialize_admission_controller()
            self.logger.info("✓ 准入控制器初始化完成")
            
            # 3. 初始化DSROQ控制器
            self.dsroq_controller = DSROQController(self.config.dsroq.__dict__)
            self.logger.info("✓ DSROQ控制器初始化完成")
            
            # 4. 初始化定位计算器
            self.positioning_calculator = PositioningCalculator(self.config.positioning.__dict__)
            self.logger.info("✓ 定位计算器初始化完成")
            
            # 5. 初始化仿真组件
            self.traffic_generator = TrafficGenerator(self.config.simulation.__dict__)
            self.event_scheduler = EventScheduler()
            self.performance_monitor = PerformanceMonitor(self.config)
            self.logger.info("✓ 仿真组件初始化完成")
            
            # 6. 获取初始网络状态
            self.current_network_state = self.hypatia_adapter.get_network_state(0.0)
            self.logger.info("✓ 初始网络状态获取完成")
            
            self.logger.info("仿真环境初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"仿真环境初始化失败: {e}")
            return False
    
    def _initialize_admission_controller(self):
        """初始化准入控制器"""
        algorithm = self.config.admission.algorithm.lower()
        
        if algorithm == 'positioning_aware':
            self.admission_controller = PositioningAwareAdmissionController(
                self.config.admission.__dict__
            )
        elif algorithm == 'drl':
            try:
                from src.admission.drl_admission import DRLAdmissionController
                self.admission_controller = DRLAdmissionController(
                    self.config.admission.__dict__
                )
            except ImportError:
                self.logger.warning("DRL不可用，回退到阈值控制")
                self.admission_controller = ThresholdAdmissionController(
                    self.config.admission.__dict__
                )
        else:
            self.admission_controller = ThresholdAdmissionController(
                self.config.admission.__dict__
            )
    
    def run_simulation(self) -> SimulationResult:
        """运行完整仿真"""
        if not self.initialize():
            raise RuntimeError("仿真环境初始化失败")
        
        self.logger.info(f"开始仿真: 持续时间={self.duration}s")
        start_time = time.time()
        self.is_running = True
        self.current_time = 0.0
        
        try:
            # 主仿真循环
            while self.current_time < self.duration and self.is_running:
                self._simulation_step()
                self.current_time += self.time_step
                
                # 执行回调
                for callback in self.step_callbacks:
                    callback(self.current_time, self._get_current_system_state())
                
                # 进度报告
                if int(self.current_time) % 60 == 0:  # 每分钟报告一次
                    progress = (self.current_time / self.duration) * 100
                    self.logger.info(f"仿真进度: {progress:.1f}% ({self.current_time:.0f}s)")
            
            # 生成仿真结果
            result = self._generate_simulation_result(time.time() - start_time)
            
            # 执行结果回调
            for callback in self.result_callbacks:
                callback(result)
            
            self.logger.info(f"仿真完成: 总时长={result.duration_seconds:.1f}s, "
                           f"总请求={result.total_requests}, "
                           f"接受率={result.accepted_requests/max(1,result.total_requests):.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"仿真执行失败: {e}")
            raise
        finally:
            self.is_running = False
    
    def _simulation_step(self):
        """执行一个仿真步骤"""
        try:
            # 1. 更新网络状态
            self.current_network_state = self.hypatia_adapter.get_network_state(self.current_time)
            
            # 2. 生成新的用户请求
            new_requests = self.traffic_generator.generate_requests(
                self.current_time, self.time_step
            )
            
            # 3. 处理事件
            events = self.event_scheduler.get_events(self.current_time)
            for event in events:
                self._handle_event(event)
            
            # 4. 处理新用户请求
            for request in new_requests:
                self._process_user_request(request)
            
            # 5. 更新DSROQ队列状态
            self.dsroq_controller.update_queue_states(self.current_network_state)
            
            # 6. 更新性能监控
            system_state = self._get_current_system_state()
            self.performance_monitor.update(system_state)
            
            # 7. 清理过期的用户会话
            self._cleanup_expired_sessions()
            
        except Exception as e:
            self.logger.error(f"仿真步骤执行失败: {e}")
    
    def _process_user_request(self, user_request: UserRequest):
        """处理用户请求"""
        try:
            # 1. 计算定位指标
            positioning_metrics = None
            if hasattr(self.positioning_calculator, 'calculate_positioning_quality'):
                positioning_metrics = self.positioning_calculator.calculate_positioning_quality(
                    [(user_request.user_lat, user_request.user_lon)],
                    self.current_network_state,
                    self.current_time
                )
                # 转换为字典格式
                if positioning_metrics:
                    positioning_metrics = {
                        'visible_satellites': [],  # 简化处理
                        'gdop': positioning_metrics.gdop_values[0] if positioning_metrics.gdop_values else float('inf'),
                        'positioning_accuracy': positioning_metrics.positioning_accuracy[0] if positioning_metrics.positioning_accuracy else 0.0
                    }
            
            # 2. 准入控制决策
            admission_result = self.admission_controller.make_admission_decision(
                user_request, self.current_network_state, positioning_metrics
            )
            
            # 3. 如果接受，进行资源分配
            if admission_result.decision.value in ['accept', 'degraded_accept', 'partial_accept']:
                allocation_result = self.dsroq_controller.process_user_request(
                    user_request, self.current_network_state
                )
                
                if allocation_result:
                    # 成功分配，记录活跃用户
                    self.active_users[user_request.user_id] = {
                        'request': user_request,
                        'admission_result': admission_result,
                        'allocation_result': allocation_result,
                        'start_time': self.current_time,
                        'end_time': self.current_time + user_request.duration_seconds
                    }
                    
                    # 调度结束事件
                    self.event_scheduler.schedule_event(
                        self.current_time + user_request.duration_seconds,
                        'user_session_end',
                        {'user_id': user_request.user_id}
                    )
                    
                    self.logger.debug(f"用户{user_request.user_id}请求成功处理")
                else:
                    self.logger.debug(f"用户{user_request.user_id}资源分配失败")
            else:
                self.logger.debug(f"用户{user_request.user_id}准入被拒绝: {admission_result.reason}")
                
        except Exception as e:
            self.logger.error(f"处理用户请求失败: {e}")
    
    def _handle_event(self, event: Dict[str, Any]):
        """处理事件"""
        event_type = event.get('type')
        event_data = event.get('data', {})
        
        if event_type == 'user_session_end':
            user_id = event_data.get('user_id')
            if user_id in self.active_users:
                # 释放资源
                allocation_result = self.active_users[user_id]['allocation_result']
                if hasattr(self.dsroq_controller.bandwidth_allocator, 'deallocate'):
                    self.dsroq_controller.bandwidth_allocator.deallocate(allocation_result.flow_id)
                
                del self.active_users[user_id]
                self.logger.debug(f"用户{user_id}会话结束")
    
    def _cleanup_expired_sessions(self):
        """清理过期的用户会话"""
        expired_users = []
        for user_id, user_info in self.active_users.items():
            if self.current_time >= user_info['end_time']:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self._handle_event({
                'type': 'user_session_end',
                'data': {'user_id': user_id}
            })
    
    def _get_current_system_state(self) -> SystemState:
        """获取当前系统状态"""
        # 计算定位指标
        if self.active_users:
            user_locations = [(info['request'].user_lat, info['request'].user_lon) 
                            for info in self.active_users.values()]
            positioning_metrics = self.positioning_calculator.calculate_positioning_quality(
                user_locations, self.current_network_state, self.current_time
            )
        else:
            positioning_metrics = self.positioning_calculator.calculate_positioning_quality(
                [], self.current_network_state, self.current_time
            )
        
        # 计算性能指标
        performance_metrics = self._calculate_performance_metrics()
        
        return SystemState(
            network_state=self.current_network_state,
            positioning_metrics=positioning_metrics,
            performance_metrics=performance_metrics
        )
    
    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """计算性能指标"""
        # 获取统计信息
        admission_stats = self.admission_controller.get_statistics()
        dsroq_stats = self.dsroq_controller.get_statistics()
        
        # 计算吞吐量
        total_bandwidth = sum(
            info['allocation_result'].allocated_bandwidth 
            for info in self.active_users.values()
        )
        
        # 计算延迟
        avg_latency = np.mean([
            info['allocation_result'].estimated_latency 
            for info in self.active_users.values()
        ]) if self.active_users else 0.0
        
        # 计算QoE评分
        qoe_score = self._calculate_qoe_score()
        
        return PerformanceMetrics(
            time_step=self.current_time,
            average_throughput=total_bandwidth,
            average_latency=avg_latency,
            packet_loss_rate=0.0,  # 简化
            jitter=0.0,  # 简化
            average_positioning_accuracy=0.8,  # 简化
            positioning_coverage=0.9,  # 简化
            average_gdop=5.0,  # 简化
            average_crlb=1.0,  # 简化
            admission_rate=admission_stats.get('acceptance_rate', 0.0),
            resource_utilization=dsroq_stats.get('success_rate', 0.0),
            energy_consumption=0.5,  # 简化
            qoe_score=qoe_score,
            positioning_score=0.8,  # 简化
            joint_objective=qoe_score * 0.7 + 0.8 * 0.3
        )
    
    def _calculate_qoe_score(self) -> float:
        """计算QoE评分"""
        if not self.active_users:
            return 1.0
        
        scores = []
        for user_info in self.active_users.values():
            request = user_info['request']
            allocation = user_info['allocation_result']
            
            # 带宽满足度
            bandwidth_satisfaction = min(1.0, allocation.allocated_bandwidth / request.bandwidth_mbps)
            
            # 延迟满足度
            latency_satisfaction = max(0.0, 1.0 - allocation.estimated_latency / request.max_latency_ms)
            
            # 综合QoE
            qoe = 0.6 * bandwidth_satisfaction + 0.4 * latency_satisfaction
            scores.append(qoe)
        
        return np.mean(scores)
    
    def _generate_simulation_result(self, execution_time: float) -> SimulationResult:
        """生成仿真结果"""
        admission_stats = self.admission_controller.get_statistics()
        dsroq_stats = self.dsroq_controller.get_statistics()
        performance_stats = self.performance_monitor.get_summary()
        
        return SimulationResult(
            duration_seconds=execution_time,
            total_requests=admission_stats.get('total_requests', 0),
            accepted_requests=admission_stats.get('accepted_requests', 0),
            rejected_requests=admission_stats.get('rejected_requests', 0),
            average_throughput=performance_stats.get('avg_throughput', 0.0),
            average_latency=performance_stats.get('avg_latency', 0.0),
            qoe_score=performance_stats.get('avg_qoe_score', 0.0),
            positioning_score=performance_stats.get('avg_positioning_score', 0.0),
            system_efficiency=dsroq_stats.get('success_rate', 0.0),
            detailed_metrics={
                'admission_stats': admission_stats,
                'dsroq_stats': dsroq_stats,
                'performance_stats': performance_stats
            }
        )
    
    def add_step_callback(self, callback: Callable):
        """添加步骤回调函数"""
        self.step_callbacks.append(callback)
    
    def add_result_callback(self, callback: Callable):
        """添加结果回调函数"""
        self.result_callbacks.append(callback)
    
    def stop_simulation(self):
        """停止仿真"""
        self.is_running = False
        self.logger.info("仿真已停止")
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前仿真状态"""
        return {
            'current_time': self.current_time,
            'progress': (self.current_time / self.duration) * 100,
            'is_running': self.is_running,
            'active_users': len(self.active_users),
            'total_satellites': len(self.current_network_state.satellites) if self.current_network_state else 0
        }
