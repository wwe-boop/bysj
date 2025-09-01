"""
准入控制API路由
"""

import logging
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError

admission_bp = Blueprint('admission', __name__)
logger = logging.getLogger(__name__)


class UserRequestSchema(Schema):
    """用户请求验证模式"""
    userId = fields.Str(required=True)
    serviceType = fields.Str(required=True)
    bandwidthMbps = fields.Float(required=True, validate=lambda x: x > 0)
    maxLatencyMs = fields.Float(required=True, validate=lambda x: x > 0)
    minReliability = fields.Float(required=True, validate=lambda x: 0 <= x <= 1)
    priority = fields.Int(required=True, validate=lambda x: 1 <= x <= 10)
    userLat = fields.Float(required=True, validate=lambda x: -90 <= x <= 90)
    userLon = fields.Float(required=True, validate=lambda x: -180 <= x <= 180)
    durationSeconds = fields.Float(required=True, validate=lambda x: x > 0)


class AdmissionConfigSchema(Schema):
    """准入控制配置验证模式"""
    algorithm = fields.Str(missing='threshold')
    maxUsersPerSatellite = fields.Int(missing=100)
    minSignalStrengthDbm = fields.Float(missing=-120.0)
    positioningWeight = fields.Float(missing=0.3)
    qosThresholds = fields.Dict(missing=dict)


@admission_bp.route('/request', methods=['POST'])
def process_admission_request():
    """处理准入控制请求"""
    try:
        # 验证请求数据
        schema = UserRequestSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 创建用户请求对象
        from src.core.state import UserRequest
        user_request = UserRequest(
            user_id=data['userId'],
            service_type=data['serviceType'],
            bandwidth_mbps=data['bandwidthMbps'],
            max_latency_ms=data['maxLatencyMs'],
            min_reliability=data['minReliability'],
            priority=data['priority'],
            user_lat=data['userLat'],
            user_lon=data['userLon'],
            duration_seconds=data['durationSeconds'],
            timestamp=_simulation_engine.current_time
        )
        
        # 获取当前网络状态
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 计算定位指标
        positioning_metrics = None
        if hasattr(_simulation_engine.positioning_calculator, 'calculate_positioning_quality'):
            positioning_metrics = _simulation_engine.positioning_calculator.calculate_positioning_quality(
                [(user_request.user_lat, user_request.user_lon)],
                network_state,
                _simulation_engine.current_time
            )
            if positioning_metrics:
                positioning_metrics = {
                    'visible_satellites': [],
                    'gdop': positioning_metrics.gdop_values[0] if positioning_metrics.gdop_values else float('inf'),
                    'positioning_accuracy': positioning_metrics.positioning_accuracy[0] if positioning_metrics.positioning_accuracy else 0.0
                }
        
        # 执行准入控制决策
        admission_result = _simulation_engine.admission_controller.make_admission_decision(
            user_request, network_state, positioning_metrics
        )
        
        # 返回结果
        return jsonify({
            'success': True,
            'data': {
                'decision': admission_result.decision.value,
                'allocatedSatellite': admission_result.allocated_satellite,
                'allocatedBandwidth': admission_result.allocated_bandwidth,
                'confidence': admission_result.confidence,
                'reason': admission_result.reason,
                'timestamp': admission_result.timestamp
            }
        })
        
    except Exception as e:
        logger.error(f"处理准入请求失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/statistics', methods=['GET'])
def get_admission_statistics():
    """获取准入控制统计信息"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 获取统计信息
        stats = _simulation_engine.admission_controller.get_statistics()
        
        return jsonify({
            'success': True,
            'data': {
                'totalRequests': stats.get('total_requests', 0),
                'acceptedRequests': stats.get('accepted_requests', 0),
                'rejectedRequests': stats.get('rejected_requests', 0),
                'degradedRequests': stats.get('degraded_requests', 0),
                'delayedRequests': stats.get('delayed_requests', 0),
                'partialRequests': stats.get('partial_requests', 0),
                'acceptanceRate': stats.get('acceptance_rate', 0.0),
                'averageDecisionTime': stats.get('avg_decision_time', 0.0),
                'qosViolations': stats.get('qos_violations', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"获取准入统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/config', methods=['GET'])
def get_admission_config():
    """获取准入控制配置"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            # 返回默认配置
            from src.core.config import SystemConfig
            config = SystemConfig()
            return jsonify({
                'success': True,
                'data': {
                    'algorithm': config.admission.algorithm,
                    'maxUsersPerSatellite': config.admission.max_users_per_satellite,
                    'minSignalStrengthDbm': config.admission.min_signal_strength_dbm,
                    'positioningWeight': getattr(config.admission, 'positioning_weight', 0.3),
                    'qosThresholds': {}
                }
            })
        
        # 获取当前配置
        admission_controller = _simulation_engine.admission_controller
        config_data = {
            'algorithm': getattr(admission_controller, 'algorithm', 'threshold'),
            'maxUsersPerSatellite': getattr(admission_controller, 'max_users_per_satellite', 100),
            'minSignalStrengthDbm': getattr(admission_controller, 'min_signal_strength_dbm', -120.0),
            'positioningWeight': getattr(admission_controller, 'positioning_weight', 0.3),
            'qosThresholds': getattr(admission_controller, 'qos_thresholds', {})
        }
        
        return jsonify({
            'success': True,
            'data': config_data
        })
        
    except Exception as e:
        logger.error(f"获取准入配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/config', methods=['PUT'])
def update_admission_config():
    """更新准入控制配置"""
    try:
        # 验证请求数据
        schema = AdmissionConfigSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine, _simulation_running
        if _simulation_running:
            return jsonify({
                'success': False,
                'error': '仿真运行时无法修改配置'
            }), 400
        
        # 这里可以实现配置更新逻辑
        # 目前只是简单返回成功
        
        return jsonify({
            'success': True,
            'message': '准入控制配置已更新'
        })
        
    except Exception as e:
        logger.error(f"更新准入配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/algorithms', methods=['GET'])
def get_available_algorithms():
    """获取可用的准入控制算法"""
    try:
        algorithms = [
            {
                'name': 'threshold',
                'displayName': '阈值准入控制',
                'description': '基于资源阈值的简单准入控制算法',
                'parameters': [
                    {'name': 'maxUsersPerSatellite', 'type': 'int', 'default': 100},
                    {'name': 'minSignalStrengthDbm', 'type': 'float', 'default': -120.0}
                ]
            },
            {
                'name': 'positioning_aware',
                'displayName': '定位感知准入控制',
                'description': '考虑定位质量的准入控制算法',
                'parameters': [
                    {'name': 'maxUsersPerSatellite', 'type': 'int', 'default': 100},
                    {'name': 'positioningWeight', 'type': 'float', 'default': 0.3},
                    {'name': 'maxGdopThreshold', 'type': 'float', 'default': 10.0}
                ]
            },
            {
                'name': 'drl',
                'displayName': '深度强化学习准入控制',
                'description': '基于深度强化学习的智能准入控制算法',
                'parameters': [
                    {'name': 'modelPath', 'type': 'string', 'default': ''},
                    {'name': 'explorationRate', 'type': 'float', 'default': 0.1},
                    {'name': 'learningRate', 'type': 'float', 'default': 0.001}
                ]
            }
        ]
        
        return jsonify({
            'success': True,
            'data': algorithms
        })
        
    except Exception as e:
        logger.error(f"获取算法列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/history', methods=['GET'])
def get_admission_history():
    """获取准入控制历史记录"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': True,
                'data': {
                    'records': [],
                    'total': 0,
                    'limit': limit,
                    'offset': offset
                }
            })
        
        # 获取历史记录
        admission_controller = _simulation_engine.admission_controller
        if hasattr(admission_controller, 'get_decision_history'):
            history = admission_controller.get_decision_history(limit, offset)
        else:
            history = {'records': [], 'total': 0}
        
        return jsonify({
            'success': True,
            'data': {
                'records': history.get('records', []),
                'total': history.get('total', 0),
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f"获取准入历史失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
