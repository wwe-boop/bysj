"""
Web服务器

提供Flask Web应用和API服务
"""

import os
import logging
import threading
from typing import Dict, Any, Optional
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import socketio

from src.core.config import SystemConfig
from src.simulation.simulation_engine import SimulationEngine
from src.simulation.scenario_manager import ScenarioManager
from .api_routes import APIRoutes
from .websocket_handler import WebSocketHandler


class WebServer:
    """Web服务器"""
    
    def __init__(self, config: SystemConfig, port: int = 5000):
        self.config = config
        self.port = port
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 创建Flask应用
        self.app = Flask(__name__, 
                        template_folder='../../web/templates',
                        static_folder='../../web/static')
        self.app.config['SECRET_KEY'] = 'leo_satellite_simulation_2024'
        
        # 启用CORS
        CORS(self.app)
        
        # 创建SocketIO
        self.sio = socketio.Server(cors_allowed_origins="*")
        self.app.wsgi_app = socketio.WSGIApp(self.sio, self.app.wsgi_app)
        
        # 仿真相关
        self.simulation_engine: Optional[SimulationEngine] = None
        self.scenario_manager = ScenarioManager()
        self.simulation_thread: Optional[threading.Thread] = None
        self.simulation_running = False
        
        # 初始化路由和WebSocket处理器
        self.api_routes = APIRoutes(self)
        self.websocket_handler = WebSocketHandler(self)
        
        self._setup_routes()
        self._setup_websocket_events()
        
        self.logger.info(f"Web服务器初始化完成，端口: {port}")
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html')
        
        @self.app.route('/dashboard')
        def dashboard():
            """仪表板"""
            return render_template('dashboard.html')
        
        @self.app.route('/simulation')
        def simulation():
            """仿真页面"""
            return render_template('simulation.html')
        
        @self.app.route('/visualization')
        def visualization():
            """可视化页面"""
            return render_template('visualization.html')
        
        @self.app.route('/scenarios')
        def scenarios():
            """场景管理页面"""
            return render_template('scenarios.html')
        
        @self.app.route('/api/status')
        def api_status():
            """API状态"""
            return jsonify({
                'status': 'running',
                'simulation_running': self.simulation_running,
                'total_satellites': self.config.constellation.num_satellites,
                'version': '1.0.0'
            })
        
        # API路由
        self.app.add_url_rule('/api/scenarios', 'get_scenarios', 
                             self.api_routes.get_scenarios, methods=['GET'])
        self.app.add_url_rule('/api/scenarios/<name>', 'get_scenario', 
                             self.api_routes.get_scenario, methods=['GET'])
        self.app.add_url_rule('/api/simulation/start', 'start_simulation', 
                             self.api_routes.start_simulation, methods=['POST'])
        self.app.add_url_rule('/api/simulation/stop', 'stop_simulation', 
                             self.api_routes.stop_simulation, methods=['POST'])
        self.app.add_url_rule('/api/simulation/status', 'simulation_status', 
                             self.api_routes.get_simulation_status, methods=['GET'])
        self.app.add_url_rule('/api/network/state', 'network_state', 
                             self.api_routes.get_network_state, methods=['GET'])
        self.app.add_url_rule('/api/performance/metrics', 'performance_metrics', 
                             self.api_routes.get_performance_metrics, methods=['GET'])
    
    def _setup_websocket_events(self):
        """设置WebSocket事件"""
        
        @self.sio.event
        def connect(sid, environ):
            self.logger.info(f"客户端连接: {sid}")
            self.websocket_handler.on_connect(sid)
        
        @self.sio.event
        def disconnect(sid):
            self.logger.info(f"客户端断开: {sid}")
            self.websocket_handler.on_disconnect(sid)
        
        @self.sio.event
        def subscribe_simulation(sid, data):
            """订阅仿真更新"""
            self.websocket_handler.subscribe_simulation(sid, data)
        
        @self.sio.event
        def unsubscribe_simulation(sid, data):
            """取消订阅仿真更新"""
            self.websocket_handler.unsubscribe_simulation(sid, data)
    
    def start_simulation_async(self, scenario_name: str) -> bool:
        """异步启动仿真"""
        if self.simulation_running:
            return False
        
        try:
            # 获取场景
            scenario = self.scenario_manager.get_scenario(scenario_name)
            if not scenario:
                self.logger.error(f"场景不存在: {scenario_name}")
                return False
            
            # 应用场景配置
            config = self.scenario_manager.apply_scenario_to_config(scenario, self.config)
            
            # 创建仿真引擎
            self.simulation_engine = SimulationEngine(config)
            
            # 添加回调
            self.simulation_engine.add_step_callback(self._simulation_step_callback)
            self.simulation_engine.add_result_callback(self._simulation_result_callback)
            
            # 启动仿真线程
            self.simulation_thread = threading.Thread(
                target=self._run_simulation,
                args=(scenario_name,)
            )
            self.simulation_running = True
            self.simulation_thread.start()
            
            self.logger.info(f"仿真已启动: {scenario_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动仿真失败: {e}")
            self.simulation_running = False
            return False
    
    def stop_simulation_async(self) -> bool:
        """异步停止仿真"""
        if not self.simulation_running:
            return False
        
        try:
            if self.simulation_engine:
                self.simulation_engine.stop_simulation()
            
            self.simulation_running = False
            
            if self.simulation_thread and self.simulation_thread.is_alive():
                self.simulation_thread.join(timeout=5.0)
            
            self.logger.info("仿真已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止仿真失败: {e}")
            return False
    
    def _run_simulation(self, scenario_name: str):
        """运行仿真"""
        try:
            # 广播仿真开始
            self.sio.emit('simulation_started', {
                'scenario': scenario_name,
                'timestamp': self.simulation_engine.current_time
            })
            
            # 运行仿真
            result = self.simulation_engine.run_simulation()
            
            # 广播仿真完成
            self.sio.emit('simulation_completed', {
                'result': {
                    'total_requests': result.total_requests,
                    'accepted_requests': result.accepted_requests,
                    'rejected_requests': result.rejected_requests,
                    'average_throughput': result.average_throughput,
                    'average_latency': result.average_latency,
                    'qoe_score': result.qoe_score,
                    'system_efficiency': result.system_efficiency
                }
            })
            
        except Exception as e:
            self.logger.error(f"仿真执行失败: {e}")
            self.sio.emit('simulation_error', {'error': str(e)})
        finally:
            self.simulation_running = False
    
    def _simulation_step_callback(self, current_time: float, system_state):
        """仿真步骤回调"""
        try:
            # 每5秒广播一次状态更新
            if int(current_time) % 5 == 0:
                self.sio.emit('simulation_update', {
                    'current_time': current_time,
                    'progress': (current_time / self.simulation_engine.duration) * 100,
                    'active_users': len(self.simulation_engine.active_users),
                    'performance_metrics': {
                        'throughput': system_state.performance_metrics.average_throughput,
                        'latency': system_state.performance_metrics.average_latency,
                        'qoe_score': system_state.performance_metrics.qoe_score,
                        'admission_rate': system_state.performance_metrics.admission_rate
                    }
                })
        except Exception as e:
            self.logger.error(f"仿真步骤回调失败: {e}")
    
    def _simulation_result_callback(self, result):
        """仿真结果回调"""
        self.logger.info(f"仿真完成: {result.total_requests}个请求")
    
    def get_current_network_state(self) -> Optional[Dict[str, Any]]:
        """获取当前网络状态"""
        if not self.simulation_engine:
            return None
        
        try:
            network_state = self.simulation_engine.current_network_state
            if not network_state:
                return None
            
            return {
                'time_step': network_state.time_step,
                'satellites': network_state.satellites[:50],  # 只返回前50颗卫星
                'active_flows': len(network_state.active_flows),
                'total_satellites': len(network_state.satellites),
                'link_utilization': dict(list(network_state.link_utilization.items())[:20])
            }
        except Exception as e:
            self.logger.error(f"获取网络状态失败: {e}")
            return None
    
    def get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """获取性能指标"""
        if not self.simulation_engine or not self.simulation_engine.performance_monitor:
            return None
        
        try:
            return self.simulation_engine.performance_monitor.get_current_metrics()
        except Exception as e:
            self.logger.error(f"获取性能指标失败: {e}")
            return None
    
    def run(self, debug: bool = False, host: str = '0.0.0.0'):
        """运行Web服务器"""
        self.logger.info(f"启动Web服务器: http://{host}:{self.port}")
        self.app.run(host=host, port=self.port, debug=debug, threaded=True)
