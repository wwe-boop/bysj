"""
API路由处理器

处理RESTful API请求
"""

import logging
from typing import Dict, Any, Optional
from flask import jsonify, request


class APIRoutes:
    """API路由处理器"""
    
    def __init__(self, web_server):
        self.web_server = web_server
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_scenarios(self):
        """获取所有场景"""
        try:
            scenarios = self.web_server.scenario_manager.list_scenarios()
            scenario_details = []
            
            for scenario_name in scenarios:
                scenario = self.web_server.scenario_manager.get_scenario(scenario_name)
                if scenario:
                    summary = self.web_server.scenario_manager.get_scenario_summary(scenario)
                    scenario_details.append(summary)
            
            return jsonify({
                'success': True,
                'scenarios': scenario_details
            })
            
        except Exception as e:
            self.logger.error(f"获取场景列表失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def get_scenario(self, name: str):
        """获取特定场景"""
        try:
            scenario = self.web_server.scenario_manager.get_scenario(name)
            if not scenario:
                return jsonify({
                    'success': False,
                    'error': f'场景不存在: {name}'
                }), 404
            
            summary = self.web_server.scenario_manager.get_scenario_summary(scenario)
            
            return jsonify({
                'success': True,
                'scenario': summary
            })
            
        except Exception as e:
            self.logger.error(f"获取场景失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def start_simulation(self):
        """启动仿真"""
        try:
            data = request.get_json()
            scenario_name = data.get('scenario', 'basic_performance')
            
            if self.web_server.simulation_running:
                return jsonify({
                    'success': False,
                    'error': '仿真已在运行中'
                }), 400
            
            success = self.web_server.start_simulation_async(scenario_name)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'仿真已启动: {scenario_name}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '启动仿真失败'
                }), 500
                
        except Exception as e:
            self.logger.error(f"启动仿真API失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def stop_simulation(self):
        """停止仿真"""
        try:
            if not self.web_server.simulation_running:
                return jsonify({
                    'success': False,
                    'error': '没有正在运行的仿真'
                }), 400
            
            success = self.web_server.stop_simulation_async()
            
            if success:
                return jsonify({
                    'success': True,
                    'message': '仿真已停止'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '停止仿真失败'
                }), 500
                
        except Exception as e:
            self.logger.error(f"停止仿真API失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def get_simulation_status(self):
        """获取仿真状态"""
        try:
            if not self.web_server.simulation_running:
                return jsonify({
                    'success': True,
                    'status': 'stopped',
                    'simulation_running': False
                })
            
            status_data = {
                'success': True,
                'status': 'running',
                'simulation_running': True
            }
            
            if self.web_server.simulation_engine:
                current_status = self.web_server.simulation_engine.get_current_status()
                status_data.update(current_status)
            
            return jsonify(status_data)
            
        except Exception as e:
            self.logger.error(f"获取仿真状态失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def get_network_state(self):
        """获取网络状态"""
        try:
            network_state = self.web_server.get_current_network_state()
            
            if network_state is None:
                return jsonify({
                    'success': False,
                    'error': '没有可用的网络状态数据'
                }), 404
            
            return jsonify({
                'success': True,
                'network_state': network_state
            })
            
        except Exception as e:
            self.logger.error(f"获取网络状态失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def get_performance_metrics(self):
        """获取性能指标"""
        try:
            metrics = self.web_server.get_performance_metrics()
            
            if metrics is None:
                return jsonify({
                    'success': False,
                    'error': '没有可用的性能指标数据'
                }), 404
            
            return jsonify({
                'success': True,
                'metrics': metrics
            })
            
        except Exception as e:
            self.logger.error(f"获取性能指标失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
