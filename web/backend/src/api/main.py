#!/usr/bin/env python3
"""
LEO卫星网络仿真系统后端API主入口

提供完整的REST API和WebSocket服务
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from src.core.config import SystemConfig
from src.simulation.simulation_engine import SimulationEngine
from src.simulation.scenario_manager import ScenarioManager

# 导入路由模块
from .routes import (
    simulation_bp,
    network_bp,
    admission_bp,
    positioning_bp,
    statistics_bp,
    scenarios_bp,
    experiments_bp
)
from .websocket import SocketIOHandler
from .middleware import setup_middleware
from .utils.logger import setup_logging


class APIServer:
    """API服务器"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.app = Flask(__name__)
        self.socketio = None
        self.simulation_engine = None
        self.scenario_manager = ScenarioManager()
        
        # 设置日志
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 初始化应用
        self._setup_app()
        self._setup_extensions()
        self._setup_routes()
        self._setup_websocket()
        self._setup_middleware()
        
        self.logger.info("API服务器初始化完成")
    
    def _setup_app(self):
        """设置Flask应用配置"""
        self.app.config.update({
            'SECRET_KEY': os.getenv('SECRET_KEY', 'leo-satellite-simulation-2024'),
            'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
            'TESTING': False,
            'JSON_AS_ASCII': False,
            'JSONIFY_PRETTYPRINT_REGULAR': True,
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
            
            # CORS配置
            'CORS_ORIGINS': ['http://localhost:3000', 'http://127.0.0.1:3000'],
            'CORS_METHODS': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'CORS_ALLOW_HEADERS': ['Content-Type', 'Authorization'],
            
            # SocketIO配置
            'SOCKETIO_ASYNC_MODE': 'eventlet',
            'SOCKETIO_CORS_ALLOWED_ORIGINS': '*',
            'SOCKETIO_LOGGER': True,
            'SOCKETIO_ENGINEIO_LOGGER': True
        })
        
        # 代理支持
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    def _setup_extensions(self):
        """设置Flask扩展"""
        # CORS
        CORS(self.app, 
             origins=self.app.config['CORS_ORIGINS'],
             methods=self.app.config['CORS_METHODS'],
             allow_headers=self.app.config['CORS_ALLOW_HEADERS'],
             supports_credentials=True)
        
        # SocketIO
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins=self.app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
            async_mode=self.app.config['SOCKETIO_ASYNC_MODE'],
            logger=self.app.config['SOCKETIO_LOGGER'],
            engineio_logger=self.app.config['SOCKETIO_ENGINEIO_LOGGER']
        )
    
    def _setup_routes(self):
        """设置API路由"""
        
        # 健康检查
        @self.app.route('/api/health')
        def health_check():
            return jsonify({
                'status': 'healthy',
                'version': '1.0.0',
                'timestamp': self._get_current_timestamp()
            })
        
        # 系统状态
        @self.app.route('/api/status')
        def system_status():
            return jsonify({
                'success': True,
                'data': {
                    'simulation_running': self.simulation_engine is not None and 
                                        getattr(self.simulation_engine, 'is_running', False),
                    'total_satellites': self.config.constellation.num_satellites,
                    'api_version': '1.0.0',
                    'uptime': self._get_uptime()
                }
            })
        
        # 注册蓝图
        self.app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
        self.app.register_blueprint(network_bp, url_prefix='/api/network')
        self.app.register_blueprint(admission_bp, url_prefix='/api/admission')
        self.app.register_blueprint(positioning_bp, url_prefix='/api/positioning')
        self.app.register_blueprint(statistics_bp, url_prefix='/api/statistics')
        self.app.register_blueprint(scenarios_bp, url_prefix='/api/scenarios')
        self.app.register_blueprint(experiments_bp, url_prefix='/api/experiments')
        
        # 错误处理
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'success': False,
                'error': 'API endpoint not found',
                'code': 404
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            self.logger.error(f"Internal server error: {error}")
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'code': 500
            }), 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(error):
            self.logger.error(f"Unhandled exception: {error}")
            return jsonify({
                'success': False,
                'error': str(error),
                'code': 500
            }), 500
    
    def _setup_websocket(self):
        """设置WebSocket处理"""
        self.websocket_handler = SocketIOHandler(self.socketio, self)
        self.websocket_handler.setup_events()
    
    def _setup_middleware(self):
        """设置中间件"""
        setup_middleware(self.app)
    
    def get_simulation_engine(self):
        """获取仿真引擎实例"""
        return self.simulation_engine
    
    def set_simulation_engine(self, engine):
        """设置仿真引擎实例"""
        self.simulation_engine = engine
    
    def get_scenario_manager(self):
        """获取场景管理器"""
        return self.scenario_manager
    
    def _get_current_timestamp(self):
        """获取当前时间戳"""
        import time
        return int(time.time())
    
    def _get_uptime(self):
        """获取系统运行时间"""
        import time
        if not hasattr(self, '_start_time'):
            self._start_time = time.time()
        return int(time.time() - self._start_time)
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """运行API服务器"""
        self.logger.info(f"启动API服务器: http://{host}:{port}")
        self.socketio.run(
            self.app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=False,  # 避免与SocketIO冲突
            log_output=True
        )


def create_app(config: SystemConfig = None) -> Flask:
    """应用工厂函数"""
    if config is None:
        config = SystemConfig()
    
    server = APIServer(config)
    return server.app


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LEO卫星网络仿真系统API服务器')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    try:
        # 创建系统配置
        config = SystemConfig()
        
        # 创建API服务器
        server = APIServer(config)
        
        # 运行服务器
        server.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭服务器...")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())


