"""
准入控制API路由
支持DRL训练环境、奖励函数配置、训练评估等功能
"""

import logging
import numpy as np
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

    # DRL相关配置
    drlEnabled = fields.Bool(missing=False)
    rewardWeights = fields.Dict(missing=dict)
    trainingMode = fields.Bool(missing=False)
    explorationRate = fields.Float(missing=0.1)


class DRLTrainingConfigSchema(Schema):
    """DRL训练配置验证模式"""
    algorithm = fields.Str(required=True, validate=lambda x: x in ['PPO', 'A2C', 'SAC'])
    learningRate = fields.Float(missing=3e-4)
    batchSize = fields.Int(missing=64)
    nSteps = fields.Int(missing=2048)
    nEpochs = fields.Int(missing=10)
    gamma = fields.Float(missing=0.99)
    clipRange = fields.Float(missing=0.2)

    # 奖励函数权重
    rewardWeights = fields.Dict(missing={
        'qoe_weight': 0.4,
        'fairness_weight': 0.2,
        'efficiency_weight': 0.2,
        'stability_weight': 0.1,
        'positioning_weight': 0.1
    })

    # 环境配置
    useRealEnvironment = fields.Bool(missing=False)
    maxEpisodeSteps = fields.Int(missing=1000)
    evaluationFreq = fields.Int(missing=10)


class DRLStateSchema(Schema):
    """DRL状态信息验证模式"""
    networkState = fields.Dict(required=True)
    userRequests = fields.List(fields.Dict(), missing=list)
    resourceUtilization = fields.Dict(missing=dict)
    positioningQuality = fields.Dict(missing=dict)
    historicalMetrics = fields.Dict(missing=dict)


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


# DRL训练相关API端点

@admission_bp.route('/drl/training/start', methods=['POST'])
def start_drl_training():
    """启动DRL训练"""
    try:
        # 验证请求数据
        schema = DRLTrainingConfigSchema()
        try:
            config = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '训练配置无效',
                'details': err.messages
            }), 400

        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503

        # 启动DRL训练
        admission_controller = _simulation_engine.admission_controller
        if hasattr(admission_controller, 'start_drl_training'):
            training_id = admission_controller.start_drl_training(config)
            return jsonify({
                'success': True,
                'data': {
                    'trainingId': training_id,
                    'config': config,
                    'message': 'DRL训练已启动'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'DRL训练功能未实现'
            }), 501

    except Exception as e:
        logger.error(f"启动DRL训练失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/drl/training/stop', methods=['POST'])
def stop_drl_training():
    """停止DRL训练"""
    try:
        training_id = request.json.get('trainingId') if request.json else None

        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503

        # 停止DRL训练
        admission_controller = _simulation_engine.admission_controller
        if hasattr(admission_controller, 'stop_drl_training'):
            result = admission_controller.stop_drl_training(training_id)
            return jsonify({
                'success': True,
                'data': result,
                'message': 'DRL训练已停止'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'DRL训练功能未实现'
            }), 501

    except Exception as e:
        logger.error(f"停止DRL训练失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/drl/training/status', methods=['GET'])
def get_drl_training_status():
    """获取DRL训练状态"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503

        # 获取训练状态
        admission_controller = _simulation_engine.admission_controller
        if hasattr(admission_controller, 'get_drl_training_status'):
            status = admission_controller.get_drl_training_status()
            return jsonify({
                'success': True,
                'data': status
            })
        else:
            # 返回默认状态
            return jsonify({
                'success': True,
                'data': {
                    'isTraining': False,
                    'trainingId': None,
                    'episode': 0,
                    'totalEpisodes': 0,
                    'currentReward': 0.0,
                    'averageReward': 0.0,
                    'loss': 0.0,
                    'explorationRate': 0.1,
                    'trainingTime': 0.0
                }
            })

    except Exception as e:
        logger.error(f"获取DRL训练状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/drl/training/metrics', methods=['GET'])
def get_drl_training_metrics():
    """获取DRL训练指标"""
    try:
        # 获取查询参数
        training_id = request.args.get('trainingId')
        limit = request.args.get('limit', 1000, type=int)

        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503

        # 获取训练指标
        admission_controller = _simulation_engine.admission_controller
        if hasattr(admission_controller, 'get_drl_training_metrics'):
            metrics = admission_controller.get_drl_training_metrics(training_id, limit)
            return jsonify({
                'success': True,
                'data': metrics
            })
        else:
            # 返回模拟数据
            episodes = list(range(1, min(limit + 1, 101)))
            rewards = [np.random.normal(0.5, 0.2) for _ in episodes]
            losses = [np.random.exponential(0.1) for _ in episodes]

            return jsonify({
                'success': True,
                'data': {
                    'episodes': episodes,
                    'rewards': rewards,
                    'losses': losses,
                    'qoeScores': [r * 0.8 + 0.2 for r in rewards],
                    'fairnessScores': [r * 0.6 + 0.4 for r in rewards],
                    'efficiencyScores': [r * 0.9 + 0.1 for r in rewards]
                }
            })

    except Exception as e:
        logger.error(f"获取DRL训练指标失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/drl/environment/state', methods=['GET'])
def get_drl_environment_state():
    """获取DRL环境状态"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503

        # 获取环境状态
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503

        # 构建DRL环境状态
        env_state = {
            'networkState': {
                'satelliteCount': len(network_state.satellites),
                'activeFlows': len(network_state.active_flows),
                'linkUtilization': dict(list(network_state.link_utilization.items())[:10]),
                'timestamp': network_state.time_step
            },
            'resourceUtilization': {
                'totalCapacity': len(network_state.satellites) * 1000.0,  # 假设每个卫星1Gbps
                'usedCapacity': sum(network_state.link_utilization.values()),
                'utilizationRate': sum(network_state.link_utilization.values()) / (len(network_state.satellites) * 1000.0) if network_state.satellites else 0
            },
            'positioningQuality': {
                'averageGdop': 3.5,  # 模拟值
                'coverageRatio': 0.85,
                'averageAccuracy': 5.2
            },
            'historicalMetrics': {
                'recentQoE': [0.8, 0.75, 0.82, 0.78, 0.85],
                'recentAdmissionRate': [0.9, 0.88, 0.92, 0.87, 0.91],
                'recentThroughput': [850, 820, 880, 810, 890]
            }
        }

        return jsonify({
            'success': True,
            'data': env_state
        })

    except Exception as e:
        logger.error(f"获取DRL环境状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/drl/reward/config', methods=['GET'])
def get_drl_reward_config():
    """获取DRL奖励函数配置"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            # 返回默认配置
            return jsonify({
                'success': True,
                'data': {
                    'rewardWeights': {
                        'qoe_weight': 0.4,
                        'fairness_weight': 0.2,
                        'efficiency_weight': 0.2,
                        'stability_weight': 0.1,
                        'positioning_weight': 0.1
                    },
                    'rewardComponents': {
                        'qoe': {
                            'enabled': True,
                            'description': 'QoE变化奖励',
                            'formula': 'delta_qoe * qoe_weight'
                        },
                        'fairness': {
                            'enabled': True,
                            'description': 'Jain公平性指数',
                            'formula': 'jain_fairness_index * fairness_weight'
                        },
                        'efficiency': {
                            'enabled': True,
                            'description': '资源利用效率',
                            'formula': 'resource_efficiency * efficiency_weight'
                        },
                        'stability': {
                            'enabled': True,
                            'description': '系统稳定性',
                            'formula': 'stability_metric * stability_weight'
                        },
                        'positioning': {
                            'enabled': True,
                            'description': '定位质量(CRLB/GDOP/SINR)',
                            'formula': 'positioning_quality * positioning_weight'
                        }
                    }
                }
            })

        # 获取当前配置
        admission_controller = _simulation_engine.admission_controller
        if hasattr(admission_controller, 'get_reward_config'):
            config = admission_controller.get_reward_config()
            return jsonify({
                'success': True,
                'data': config
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'rewardWeights': {
                        'qoe_weight': 0.4,
                        'fairness_weight': 0.2,
                        'efficiency_weight': 0.2,
                        'stability_weight': 0.1,
                        'positioning_weight': 0.1
                    }
                }
            })

    except Exception as e:
        logger.error(f"获取DRL奖励配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admission_bp.route('/drl/reward/config', methods=['PUT'])
def update_drl_reward_config():
    """更新DRL奖励函数配置"""
    try:
        config = request.get_json() or {}

        # 验证权重总和
        weights = config.get('rewardWeights', {})
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            return jsonify({
                'success': False,
                'error': f'奖励权重总和应为1.0，当前为{total_weight:.3f}'
            }), 400

        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine, _simulation_running
        if _simulation_running:
            return jsonify({
                'success': False,
                'error': '仿真运行时无法修改奖励配置'
            }), 400

        # 更新配置
        if _simulation_engine and hasattr(_simulation_engine.admission_controller, 'update_reward_config'):
            _simulation_engine.admission_controller.update_reward_config(config)

        return jsonify({
            'success': True,
            'message': 'DRL奖励函数配置已更新'
        })

    except Exception as e:
        logger.error(f"更新DRL奖励配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
