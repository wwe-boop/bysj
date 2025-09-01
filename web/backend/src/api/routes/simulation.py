"""
仿真控制API路由
"""

import logging
import threading
from flask import Blueprint, request, jsonify, current_app
from marshmallow import Schema, fields, ValidationError

from src.core.config import SystemConfig
from src.simulation.simulation_engine import SimulationEngine

simulation_bp = Blueprint('simulation', __name__)
logger = logging.getLogger(__name__)

# 全局仿真状态
_simulation_engine = None
_simulation_thread = None
_simulation_running = False


class SimulationConfigSchema(Schema):
    """仿真配置验证模式"""
    scenario = fields.Str(required=True)
    duration = fields.Float(missing=300.0)
    parameters = fields.Dict(missing=dict)


class SimulationStatusSchema(Schema):
    """仿真状态响应模式"""
    isRunning = fields.Bool()
    currentTime = fields.Float()
    progress = fields.Float()
    scenario = fields.Str(allow_none=True)
    startTime = fields.Float(allow_none=True)
    duration = fields.Float(allow_none=True)


@simulation_bp.route('/status', methods=['GET'])
def get_simulation_status():
    """获取仿真状态"""
    try:
        global _simulation_engine, _simulation_running
        
        status = {
            'isRunning': _simulation_running,
            'currentTime': 0.0,
            'progress': 0.0,
            'scenario': None,
            'startTime': None,
            'duration': None
        }
        
        if _simulation_engine and _simulation_running:
            current_status = _simulation_engine.get_current_status()
            status.update({
                'currentTime': current_status.get('current_time', 0.0),
                'progress': current_status.get('progress', 0.0),
                'scenario': getattr(_simulation_engine, 'current_scenario', None),
                'duration': _simulation_engine.duration
            })
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"获取仿真状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    """启动仿真"""
    try:
        global _simulation_engine, _simulation_thread, _simulation_running
        
        if _simulation_running:
            return jsonify({
                'success': False,
                'error': '仿真已在运行中'
            }), 400
        
        # 验证请求数据
        schema = SimulationConfigSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 获取场景管理器
        from flask import current_app
        scenario_manager = getattr(current_app, 'scenario_manager', None)
        if not scenario_manager:
            # 创建场景管理器
            from src.simulation.scenario_manager import ScenarioManager
            scenario_manager = ScenarioManager()
        
        # 获取场景
        scenario = scenario_manager.get_scenario(data['scenario'])
        if not scenario:
            return jsonify({
                'success': False,
                'error': f'场景不存在: {data["scenario"]}'
            }), 404
        
        # 创建系统配置
        config = SystemConfig()
        
        # 应用场景配置
        config = scenario_manager.apply_scenario_to_config(scenario, config)
        
        # 应用用户自定义参数
        if data.get('duration'):
            config.simulation.duration_seconds = data['duration']
        
        # 创建仿真引擎
        _simulation_engine = SimulationEngine(config)
        _simulation_engine.current_scenario = data['scenario']
        
        # 添加回调函数
        def simulation_step_callback(current_time, system_state):
            # 通过WebSocket广播仿真更新
            try:
                from flask_socketio import emit
                emit('simulation_update', {
                    'current_time': current_time,
                    'progress': (current_time / _simulation_engine.duration) * 100,
                    'active_users': len(_simulation_engine.active_users),
                    'performance_metrics': {
                        'throughput': system_state.performance_metrics.average_throughput,
                        'latency': system_state.performance_metrics.average_latency,
                        'qoe_score': system_state.performance_metrics.qoe_score,
                        'admission_rate': system_state.performance_metrics.admission_rate
                    }
                }, broadcast=True)
            except Exception as e:
                logger.error(f"WebSocket广播失败: {e}")
        
        def simulation_result_callback(result):
            # 仿真完成回调
            global _simulation_running
            _simulation_running = False
            
            try:
                from flask_socketio import emit
                emit('simulation_completed', {
                    'result': {
                        'total_requests': result.total_requests,
                        'accepted_requests': result.accepted_requests,
                        'rejected_requests': result.rejected_requests,
                        'average_throughput': result.average_throughput,
                        'average_latency': result.average_latency,
                        'qoe_score': result.qoe_score,
                        'system_efficiency': result.system_efficiency
                    }
                }, broadcast=True)
            except Exception as e:
                logger.error(f"WebSocket广播失败: {e}")
        
        _simulation_engine.add_step_callback(simulation_step_callback)
        _simulation_engine.add_result_callback(simulation_result_callback)
        
        # 启动仿真线程
        def run_simulation():
            global _simulation_running
            try:
                _simulation_running = True
                
                # 广播仿真开始
                from flask_socketio import emit
                emit('simulation_started', {
                    'scenario': data['scenario'],
                    'timestamp': _simulation_engine.current_time
                }, broadcast=True)
                
                # 运行仿真
                result = _simulation_engine.run_simulation()
                logger.info(f"仿真完成: {result.total_requests}个请求")
                
            except Exception as e:
                logger.error(f"仿真执行失败: {e}")
                _simulation_running = False
                
                try:
                    from flask_socketio import emit
                    emit('simulation_error', {'error': str(e)}, broadcast=True)
                except:
                    pass
        
        _simulation_thread = threading.Thread(target=run_simulation)
        _simulation_thread.daemon = True
        _simulation_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'仿真已启动: {data["scenario"]}'
        })
        
    except Exception as e:
        logger.error(f"启动仿真失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/stop', methods=['POST'])
def stop_simulation():
    """停止仿真"""
    try:
        global _simulation_engine, _simulation_running
        
        if not _simulation_running:
            return jsonify({
                'success': False,
                'error': '没有正在运行的仿真'
            }), 400
        
        if _simulation_engine:
            _simulation_engine.stop_simulation()
        
        _simulation_running = False
        
        # 广播仿真停止
        try:
            from flask_socketio import emit
            emit('simulation_stopped', {
                'timestamp': _simulation_engine.current_time if _simulation_engine else 0
            }, broadcast=True)
        except Exception as e:
            logger.error(f"WebSocket广播失败: {e}")
        
        return jsonify({
            'success': True,
            'message': '仿真已停止'
        })
        
    except Exception as e:
        logger.error(f"停止仿真失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/pause', methods=['POST'])
def pause_simulation():
    """暂停仿真"""
    try:
        global _simulation_engine, _simulation_running
        
        if not _simulation_running or not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '没有正在运行的仿真'
            }), 400
        
        # 这里可以实现暂停逻辑
        # 目前的仿真引擎不支持暂停，可以作为未来扩展
        
        return jsonify({
            'success': False,
            'error': '暂停功能暂未实现'
        }), 501
        
    except Exception as e:
        logger.error(f"暂停仿真失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/resume', methods=['POST'])
def resume_simulation():
    """恢复仿真"""
    try:
        # 恢复功能暂未实现
        return jsonify({
            'success': False,
            'error': '恢复功能暂未实现'
        }), 501
        
    except Exception as e:
        logger.error(f"恢复仿真失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/reset', methods=['POST'])
def reset_simulation():
    """重置仿真"""
    try:
        global _simulation_engine, _simulation_running
        
        if _simulation_running:
            return jsonify({
                'success': False,
                'error': '请先停止当前仿真'
            }), 400
        
        _simulation_engine = None
        _simulation_running = False
        
        return jsonify({
            'success': True,
            'message': '仿真已重置'
        })
        
    except Exception as e:
        logger.error(f"重置仿真失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/config', methods=['GET'])
def get_simulation_config():
    """获取仿真配置"""
    try:
        global _simulation_engine
        
        if not _simulation_engine:
            # 返回默认配置
            config = SystemConfig()
            return jsonify({
                'success': True,
                'data': {
                    'scenario': 'basic_performance',
                    'duration': config.simulation.duration_seconds,
                    'parameters': {}
                }
            })
        
        return jsonify({
            'success': True,
            'data': {
                'scenario': getattr(_simulation_engine, 'current_scenario', 'unknown'),
                'duration': _simulation_engine.duration,
                'parameters': {}
            }
        })
        
    except Exception as e:
        logger.error(f"获取仿真配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@simulation_bp.route('/config', methods=['PUT'])
def update_simulation_config():
    """更新仿真配置"""
    try:
        if _simulation_running:
            return jsonify({
                'success': False,
                'error': '仿真运行时无法修改配置'
            }), 400
        
        # 验证请求数据
        schema = SimulationConfigSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({
                'success': False,
                'error': '请求参数无效',
                'details': err.messages
            }), 400
        
        # 这里可以保存配置到数据库或文件
        # 目前只是简单返回成功
        
        return jsonify({
            'success': True,
            'message': '配置已更新'
        })
        
    except Exception as e:
        logger.error(f"更新仿真配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
