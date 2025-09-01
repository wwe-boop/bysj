"""
统计分析API路由
"""

import logging
from flask import Blueprint, request, jsonify

statistics_bp = Blueprint('statistics', __name__)
logger = logging.getLogger(__name__)


@statistics_bp.route('/performance', methods=['GET'])
def get_performance_statistics():
    """获取性能统计"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 获取性能监控器
        performance_monitor = _simulation_engine.performance_monitor
        if not performance_monitor:
            return jsonify({
                'success': False,
                'error': '性能监控器不可用'
            }), 503
        
        # 获取统计信息
        stats = performance_monitor.get_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@statistics_bp.route('/summary', methods=['GET'])
def get_summary_statistics():
    """获取汇总统计"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 收集各模块统计信息
        summary = {
            'simulation': {
                'currentTime': _simulation_engine.current_time,
                'duration': _simulation_engine.duration,
                'progress': (_simulation_engine.current_time / _simulation_engine.duration) * 100 if _simulation_engine.duration > 0 else 0
            },
            'network': {
                'totalSatellites': len(_simulation_engine.current_network_state.satellites) if _simulation_engine.current_network_state else 0,
                'activeFlows': len(_simulation_engine.current_network_state.active_flows) if _simulation_engine.current_network_state else 0
            },
            'admission': {},
            'positioning': {},
            'performance': {}
        }
        
        # 准入控制统计
        if hasattr(_simulation_engine, 'admission_controller'):
            admission_stats = _simulation_engine.admission_controller.get_statistics()
            summary['admission'] = {
                'totalRequests': admission_stats.get('total_requests', 0),
                'acceptanceRate': admission_stats.get('acceptance_rate', 0.0),
                'avgDecisionTime': admission_stats.get('avg_decision_time', 0.0)
            }
        
        # 定位服务统计
        if hasattr(_simulation_engine, 'positioning_calculator'):
            positioning_stats = getattr(_simulation_engine.positioning_calculator, 'get_statistics', lambda: {})()
            summary['positioning'] = {
                'averageAccuracy': positioning_stats.get('average_accuracy', 0.0),
                'coverageRatio': positioning_stats.get('coverage_ratio', 0.0),
                'averageGdop': positioning_stats.get('average_gdop', 0.0)
            }
        
        # 性能统计
        if hasattr(_simulation_engine, 'performance_monitor'):
            performance_stats = _simulation_engine.performance_monitor.get_summary()
            summary['performance'] = performance_stats
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取汇总统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@statistics_bp.route('/export', methods=['GET'])
def export_statistics():
    """导出统计数据"""
    try:
        # 获取查询参数
        format_type = request.args.get('format', 'json')
        start_time = request.args.get('start_time', type=float)
        end_time = request.args.get('end_time', type=float)
        
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 收集导出数据
        export_data = {
            'metadata': {
                'exportTime': _simulation_engine.current_time,
                'format': format_type,
                'timeRange': [start_time, end_time] if start_time and end_time else None
            },
            'performance': {},
            'admission': {},
            'positioning': {},
            'network': {}
        }
        
        # 性能数据
        if hasattr(_simulation_engine, 'performance_monitor'):
            export_data['performance'] = _simulation_engine.performance_monitor.export_data()
        
        # 准入控制数据
        if hasattr(_simulation_engine, 'admission_controller'):
            admission_stats = _simulation_engine.admission_controller.get_statistics()
            export_data['admission'] = admission_stats
        
        # 网络数据
        if _simulation_engine.current_network_state:
            network_state = _simulation_engine.current_network_state
            export_data['network'] = {
                'satellites': len(network_state.satellites),
                'activeFlows': len(network_state.active_flows),
                'linkUtilization': network_state.link_utilization
            }
        
        if format_type == 'json':
            return jsonify({
                'success': True,
                'data': export_data
            })
        elif format_type == 'csv':
            # 这里可以实现CSV导出
            return jsonify({
                'success': False,
                'error': 'CSV导出功能暂未实现'
            }), 501
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的导出格式: {format_type}'
            }), 400
        
    except Exception as e:
        logger.error(f"导出统计数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
