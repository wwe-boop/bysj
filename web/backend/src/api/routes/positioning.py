"""
定位服务API路由
"""

import logging
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError

positioning_bp = Blueprint('positioning', __name__)
logger = logging.getLogger(__name__)


class PositioningRequestSchema(Schema):
    """定位请求验证模式"""
    userId = fields.Str(required=True)
    lat = fields.Float(required=True, validate=lambda x: -90 <= x <= 90)
    lon = fields.Float(required=True, validate=lambda x: -180 <= x <= 180)
    accuracy = fields.Float(missing=10.0, validate=lambda x: x > 0)


class PositioningConfigSchema(Schema):
    """定位配置验证模式"""
    elevationMaskDeg = fields.Float(missing=10.0)
    maxGdopThreshold = fields.Float(missing=10.0)
    minVisibleSatellites = fields.Int(missing=4)
    signalNoiseRatio = fields.Float(missing=30.0)


@positioning_bp.route('/request', methods=['POST'])
def process_positioning_request():
    """处理定位请求"""
    try:
        # 验证请求数据
        schema = PositioningRequestSchema()
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
        
        # 获取当前网络状态
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 计算定位质量
        positioning_calculator = _simulation_engine.positioning_calculator
        user_locations = [(data['lat'], data['lon'])]
        
        positioning_metrics = positioning_calculator.calculate_positioning_quality(
            user_locations, network_state, _simulation_engine.current_time
        )
        
        if not positioning_metrics or not positioning_metrics.gdop_values:
            return jsonify({
                'success': False,
                'error': '无法计算定位质量'
            }), 503
        
        # 模拟定位结果
        import random
        import numpy as np
        
        gdop = positioning_metrics.gdop_values[0]
        accuracy = positioning_metrics.positioning_accuracy[0]
        
        # 添加定位误差
        lat_error = np.random.normal(0, accuracy / 111000)  # 转换为度
        lon_error = np.random.normal(0, accuracy / (111000 * np.cos(np.radians(data['lat']))))
        
        estimated_lat = data['lat'] + lat_error
        estimated_lon = data['lon'] + lon_error
        
        # 获取可见卫星
        visible_satellites = []
        signal_strength = []
        
        for i, satellite in enumerate(network_state.satellites[:20]):  # 限制数量
            # 简化的可见性计算
            sat_lat = satellite.get('lat', 0)
            sat_lon = satellite.get('lon', 0)
            
            # 计算距离
            distance = np.sqrt((sat_lat - data['lat'])**2 + (sat_lon - data['lon'])**2)
            
            if distance < 50:  # 简化的可见性判断
                visible_satellites.append(satellite['id'])
                # 模拟信号强度
                signal_strength.append(random.uniform(-100, -80))
        
        result = {
            'userId': data['userId'],
            'estimatedLat': float(estimated_lat),
            'estimatedLon': float(estimated_lon),
            'accuracy': float(accuracy),
            'gdop': float(gdop),
            'visibleSatellites': visible_satellites,
            'signalStrength': signal_strength,
            'timestamp': _simulation_engine.current_time
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"处理定位请求失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@positioning_bp.route('/quality', methods=['GET'])
def get_positioning_quality():
    """获取定位质量指标"""
    try:
        # 获取查询参数
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if lat is None or lon is None:
            return jsonify({
                'success': False,
                'error': '缺少位置参数'
            }), 400
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({
                'success': False,
                'error': '位置参数无效'
            }), 400
        
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 获取当前网络状态
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 计算定位质量
        positioning_calculator = _simulation_engine.positioning_calculator
        user_locations = [(lat, lon)]
        
        positioning_metrics = positioning_calculator.calculate_positioning_quality(
            user_locations, network_state, _simulation_engine.current_time
        )
        
        if not positioning_metrics:
            return jsonify({
                'success': False,
                'error': '无法计算定位质量'
            }), 503
        
        result = {
            'lat': lat,
            'lon': lon,
            'gdop': positioning_metrics.gdop_values[0] if positioning_metrics.gdop_values else float('inf'),
            'accuracy': positioning_metrics.positioning_accuracy[0] if positioning_metrics.positioning_accuracy else 0.0,
            'coverageRatio': positioning_metrics.coverage_ratio,
            'visibleSatellitesCount': positioning_metrics.visible_satellites_count[0] if positioning_metrics.visible_satellites_count else 0,
            'avgSignalStrength': positioning_metrics.avg_signal_strength[0] if positioning_metrics.avg_signal_strength else 0.0,
            'timestamp': positioning_metrics.time_step
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取定位质量失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@positioning_bp.route('/coverage', methods=['GET'])
def get_positioning_coverage():
    """获取定位覆盖范围"""
    try:
        # 获取查询参数
        resolution = request.args.get('resolution', 10, type=int)  # 网格分辨率
        lat_min = request.args.get('lat_min', -60, type=float)
        lat_max = request.args.get('lat_max', 60, type=float)
        lon_min = request.args.get('lon_min', -180, type=float)
        lon_max = request.args.get('lon_max', 180, type=float)
        
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 获取当前网络状态
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 生成网格点
        import numpy as np
        
        lat_step = (lat_max - lat_min) / resolution
        lon_step = (lon_max - lon_min) / resolution
        
        coverage_data = []
        
        for i in range(resolution):
            for j in range(resolution):
                lat = lat_min + i * lat_step
                lon = lon_min + j * lon_step
                
                # 计算该点的定位质量
                try:
                    positioning_metrics = _simulation_engine.positioning_calculator.calculate_positioning_quality(
                        [(lat, lon)], network_state, _simulation_engine.current_time
                    )
                    
                    if positioning_metrics and positioning_metrics.gdop_values:
                        gdop = positioning_metrics.gdop_values[0]
                        accuracy = positioning_metrics.positioning_accuracy[0]
                        visible_count = positioning_metrics.visible_satellites_count[0] if positioning_metrics.visible_satellites_count else 0
                    else:
                        gdop = float('inf')
                        accuracy = 0.0
                        visible_count = 0
                    
                    coverage_data.append({
                        'lat': lat,
                        'lon': lon,
                        'gdop': gdop,
                        'accuracy': accuracy,
                        'visibleSatellites': visible_count,
                        'quality': 'good' if gdop < 5 and visible_count >= 4 else 'poor'
                    })
                    
                except Exception as e:
                    logger.warning(f"计算点({lat}, {lon})定位质量失败: {e}")
                    coverage_data.append({
                        'lat': lat,
                        'lon': lon,
                        'gdop': float('inf'),
                        'accuracy': 0.0,
                        'visibleSatellites': 0,
                        'quality': 'poor'
                    })
        
        return jsonify({
            'success': True,
            'data': {
                'coverage': coverage_data,
                'resolution': resolution,
                'bounds': {
                    'latMin': lat_min,
                    'latMax': lat_max,
                    'lonMin': lon_min,
                    'lonMax': lon_max
                },
                'timestamp': _simulation_engine.current_time
            }
        })
        
    except Exception as e:
        logger.error(f"获取定位覆盖失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@positioning_bp.route('/statistics', methods=['GET'])
def get_positioning_statistics():
    """获取定位服务统计信息"""
    try:
        # 获取仿真引擎
        from ..routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        # 获取统计信息
        positioning_calculator = _simulation_engine.positioning_calculator
        if hasattr(positioning_calculator, 'get_statistics'):
            stats = positioning_calculator.get_statistics()
        else:
            stats = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'average_accuracy': 0.0,
                'average_gdop': 0.0,
                'coverage_ratio': 0.0
            }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取定位统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@positioning_bp.route('/config', methods=['GET'])
def get_positioning_config():
    """获取定位服务配置"""
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
                    'elevationMaskDeg': config.positioning.elevation_mask_deg,
                    'maxGdopThreshold': config.positioning.max_gdop_threshold,
                    'minVisibleSatellites': 4,
                    'signalNoiseRatio': 30.0
                }
            })
        
        # 获取当前配置
        positioning_calculator = _simulation_engine.positioning_calculator
        config_data = {
            'elevationMaskDeg': getattr(positioning_calculator, 'elevation_mask_deg', 10.0),
            'maxGdopThreshold': getattr(positioning_calculator, 'max_gdop_threshold', 10.0),
            'minVisibleSatellites': getattr(positioning_calculator, 'min_visible_satellites', 4),
            'signalNoiseRatio': getattr(positioning_calculator, 'signal_noise_ratio', 30.0)
        }
        
        return jsonify({
            'success': True,
            'data': config_data
        })
        
    except Exception as e:
        logger.error(f"获取定位配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@positioning_bp.route('/config', methods=['PUT'])
def update_positioning_config():
    """更新定位服务配置"""
    try:
        # 验证请求数据
        schema = PositioningConfigSchema()
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
            'message': '定位服务配置已更新'
        })
        
    except Exception as e:
        logger.error(f"更新定位配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
