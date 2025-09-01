"""
网络状态API路由
"""

import logging
from flask import Blueprint, request, jsonify

network_bp = Blueprint('network', __name__)
logger = logging.getLogger(__name__)


@network_bp.route('/state', methods=['GET'])
def get_network_state():
    """获取当前网络状态"""
    try:
        # 获取仿真引擎
        try:
            from ..routes.simulation import _simulation_engine
        except ImportError:
            from routes.simulation import _simulation_engine
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
        
        # 限制返回的数据量
        max_satellites = request.args.get('max_satellites', 100, type=int)
        max_links = request.args.get('max_links', 200, type=int)
        
        satellites = network_state.satellites[:max_satellites]
        links = []
        
        # 生成链路信息
        for i, sat in enumerate(satellites[:max_links//4]):
            for j in range(min(4, len(satellites) - i - 1)):
                if i + j + 1 < len(satellites):
                    target_sat = satellites[i + j + 1]
                    links.append({
                        'id': f"link_{sat['id']}_{target_sat['id']}",
                        'source': sat['id'],
                        'target': target_sat['id'],
                        'capacity': 1000.0,  # Mbps
                        'utilization': network_state.link_utilization.get(f"{sat['id']}-{target_sat['id']}", 0.0),
                        'latency': 20.0,  # ms
                        'active': True
                    })
        
        result = {
            'timeStep': network_state.time_step,
            'satellites': satellites,
            'links': links[:max_links],
            'activeFlows': len(network_state.active_flows),
            'totalSatellites': len(network_state.satellites),
            'linkUtilization': dict(list(network_state.link_utilization.items())[:50])
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取网络状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/topology', methods=['GET'])
def get_network_topology():
    """获取网络拓扑"""
    try:
        # 获取仿真引擎
        try:
            from ..routes.simulation import _simulation_engine
        except ImportError:
            from routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 简化的拓扑数据
        max_nodes = request.args.get('max_nodes', 50, type=int)
        satellites = network_state.satellites[:max_nodes]
        
        # 生成邻接矩阵
        adjacency_matrix = []
        for i in range(len(satellites)):
            row = [0] * len(satellites)
            # 简单的连接规则：每个卫星连接到最近的几个卫星
            for j in range(len(satellites)):
                if i != j and abs(i - j) <= 3:
                    row[j] = 1
            adjacency_matrix.append(row)
        
        return jsonify({
            'success': True,
            'data': {
                'satellites': satellites,
                'adjacencyMatrix': adjacency_matrix,
                'timestamp': network_state.time_step
            }
        })
        
    except Exception as e:
        logger.error(f"获取网络拓扑失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/satellites', methods=['GET'])
def get_satellites():
    """获取卫星信息"""
    try:
        # 获取仿真引擎
        try:
            from ..routes.simulation import _simulation_engine
        except ImportError:
            from routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        satellites = network_state.satellites[offset:offset + limit]
        
        return jsonify({
            'success': True,
            'data': {
                'satellites': satellites,
                'total': len(network_state.satellites),
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f"获取卫星信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/links', methods=['GET'])
def get_links():
    """获取链路信息"""
    try:
        # 获取仿真引擎
        try:
            from ..routes.simulation import _simulation_engine
        except ImportError:
            from routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 生成链路信息
        links = []
        satellites = network_state.satellites[:50]  # 限制数量
        
        for i, sat in enumerate(satellites):
            for j in range(i + 1, min(i + 5, len(satellites))):
                target_sat = satellites[j]
                link_id = f"link_{sat['id']}_{target_sat['id']}"
                
                links.append({
                    'id': link_id,
                    'source': sat['id'],
                    'target': target_sat['id'],
                    'capacity': 1000.0,
                    'utilization': network_state.link_utilization.get(f"{sat['id']}-{target_sat['id']}", 0.0),
                    'latency': 20.0,
                    'active': True
                })
        
        return jsonify({
            'success': True,
            'data': {
                'links': links,
                'total': len(links)
            }
        })
        
    except Exception as e:
        logger.error(f"获取链路信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/flows', methods=['GET'])
def get_flows():
    """获取流量信息"""
    try:
        # 获取仿真引擎
        try:
            from ..routes.simulation import _simulation_engine
        except ImportError:
            from routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 转换流量信息格式
        flows = []
        for flow in network_state.active_flows:
            flows.append({
                'id': flow.flow_id,
                'source': flow.source_satellite,
                'destination': flow.destination_satellite,
                'bandwidth': flow.bandwidth_mbps,
                'latency': flow.latency_ms,
                'qosClass': flow.qos_class.value,
                'route': flow.route,
                'priority': flow.priority
            })
        
        return jsonify({
            'success': True,
            'data': {
                'flows': flows,
                'total': len(flows)
            }
        })
        
    except Exception as e:
        logger.error(f"获取流量信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@network_bp.route('/utilization', methods=['GET'])
def get_network_utilization():
    """获取网络利用率"""
    try:
        # 获取仿真引擎
        try:
            from ..routes.simulation import _simulation_engine
        except ImportError:
            from routes.simulation import _simulation_engine
        if not _simulation_engine:
            return jsonify({
                'success': False,
                'error': '仿真引擎未启动'
            }), 503
        
        network_state = _simulation_engine.current_network_state
        if not network_state:
            return jsonify({
                'success': False,
                'error': '网络状态不可用'
            }), 503
        
        # 计算整体利用率
        total_capacity = len(network_state.satellites) * 1000.0  # 假设每个卫星1Gbps
        total_used = sum(network_state.link_utilization.values())
        overall_utilization = total_used / total_capacity if total_capacity > 0 else 0.0
        
        # 计算各个区域的利用率
        region_utilization = {
            'north': 0.3,
            'south': 0.2,
            'equator': 0.5,
            'polar': 0.1
        }
        
        return jsonify({
            'success': True,
            'data': {
                'overallUtilization': overall_utilization,
                'regionUtilization': region_utilization,
                'linkUtilization': dict(list(network_state.link_utilization.items())[:100]),
                'totalCapacity': total_capacity,
                'totalUsed': total_used,
                'timestamp': network_state.time_step
            }
        })
        
    except Exception as e:
        logger.error(f"获取网络利用率失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
