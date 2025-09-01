"""
WebSocket事件处理器
"""

import logging
from flask_socketio import emit, join_room, leave_room, disconnect
from typing import Dict, Set

logger = logging.getLogger(__name__)


class SocketIOHandler:
    """WebSocket事件处理器"""
    
    def __init__(self, socketio, api_server):
        self.socketio = socketio
        self.api_server = api_server
        self.connected_clients: Set[str] = set()
        self.simulation_subscribers: Set[str] = set()
        self.positioning_subscribers: Set[str] = set()
        self.network_subscribers: Set[str] = set()
        
    def setup_events(self):
        """设置WebSocket事件处理"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接事件"""
            try:
                client_id = self._get_client_id()
                self.connected_clients.add(client_id)
                
                logger.info(f"客户端连接: {client_id}, 总连接数: {len(self.connected_clients)}")
                
                # 发送连接确认
                emit('connection_established', {
                    'message': '连接成功',
                    'clientId': client_id,
                    'serverTime': self._get_current_timestamp(),
                    'simulationRunning': self._is_simulation_running()
                })
                
            except Exception as e:
                logger.error(f"处理连接事件失败: {e}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开事件"""
            try:
                client_id = self._get_client_id()
                
                # 从所有订阅中移除
                self.connected_clients.discard(client_id)
                self.simulation_subscribers.discard(client_id)
                self.positioning_subscribers.discard(client_id)
                self.network_subscribers.discard(client_id)
                
                logger.info(f"客户端断开: {client_id}, 总连接数: {len(self.connected_clients)}")
                
            except Exception as e:
                logger.error(f"处理断开事件失败: {e}")
        
        @self.socketio.on('subscribe_simulation')
        def handle_subscribe_simulation(data):
            """订阅仿真更新"""
            try:
                client_id = self._get_client_id()
                self.simulation_subscribers.add(client_id)
                
                logger.info(f"客户端 {client_id} 订阅仿真更新")
                
                # 发送当前仿真状态
                if self._is_simulation_running():
                    simulation_engine = self.api_server.get_simulation_engine()
                    if simulation_engine:
                        current_status = simulation_engine.get_current_status()
                        emit('simulation_status', current_status)
                
                emit('subscription_confirmed', {
                    'type': 'simulation',
                    'message': '已订阅仿真更新'
                })
                
            except Exception as e:
                logger.error(f"处理仿真订阅失败: {e}")
                emit('error', {'message': '订阅失败'})
        
        @self.socketio.on('unsubscribe_simulation')
        def handle_unsubscribe_simulation(data):
            """取消订阅仿真更新"""
            try:
                client_id = self._get_client_id()
                self.simulation_subscribers.discard(client_id)
                
                logger.info(f"客户端 {client_id} 取消订阅仿真更新")
                
                emit('subscription_cancelled', {
                    'type': 'simulation',
                    'message': '已取消订阅仿真更新'
                })
                
            except Exception as e:
                logger.error(f"处理取消仿真订阅失败: {e}")
        
        @self.socketio.on('subscribe_positioning')
        def handle_subscribe_positioning(data):
            """订阅定位更新"""
            try:
                client_id = self._get_client_id()
                self.positioning_subscribers.add(client_id)
                
                logger.info(f"客户端 {client_id} 订阅定位更新")
                
                emit('subscription_confirmed', {
                    'type': 'positioning',
                    'message': '已订阅定位更新'
                })
                
            except Exception as e:
                logger.error(f"处理定位订阅失败: {e}")
                emit('error', {'message': '订阅失败'})
        
        @self.socketio.on('subscribe_network')
        def handle_subscribe_network(data):
            """订阅网络状态更新"""
            try:
                client_id = self._get_client_id()
                self.network_subscribers.add(client_id)
                
                logger.info(f"客户端 {client_id} 订阅网络状态更新")
                
                emit('subscription_confirmed', {
                    'type': 'network',
                    'message': '已订阅网络状态更新'
                })
                
            except Exception as e:
                logger.error(f"处理网络订阅失败: {e}")
                emit('error', {'message': '订阅失败'})
        
        @self.socketio.on('ping')
        def handle_ping(data):
            """处理心跳包"""
            try:
                emit('pong', {
                    'timestamp': self._get_current_timestamp(),
                    'clientTimestamp': data.get('timestamp') if data else None
                })
                
            except Exception as e:
                logger.error(f"处理心跳包失败: {e}")
        
        @self.socketio.on('get_status')
        def handle_get_status(data):
            """获取系统状态"""
            try:
                status = {
                    'simulation': {
                        'running': self._is_simulation_running(),
                        'currentTime': 0.0,
                        'progress': 0.0
                    },
                    'connections': {
                        'total': len(self.connected_clients),
                        'simulationSubscribers': len(self.simulation_subscribers),
                        'positioningSubscribers': len(self.positioning_subscribers),
                        'networkSubscribers': len(self.network_subscribers)
                    },
                    'timestamp': self._get_current_timestamp()
                }
                
                # 如果仿真正在运行，获取详细状态
                if self._is_simulation_running():
                    simulation_engine = self.api_server.get_simulation_engine()
                    if simulation_engine:
                        current_status = simulation_engine.get_current_status()
                        status['simulation'].update(current_status)
                
                emit('status_response', status)
                
            except Exception as e:
                logger.error(f"获取状态失败: {e}")
                emit('error', {'message': '获取状态失败'})
    
    def broadcast_simulation_update(self, data: Dict):
        """广播仿真更新"""
        try:
            if self.simulation_subscribers:
                self.socketio.emit('simulation_update', data, 
                                 room=list(self.simulation_subscribers))
                logger.debug(f"广播仿真更新到 {len(self.simulation_subscribers)} 个客户端")
        except Exception as e:
            logger.error(f"广播仿真更新失败: {e}")
    
    def broadcast_positioning_update(self, data: Dict):
        """广播定位更新"""
        try:
            if self.positioning_subscribers:
                self.socketio.emit('positioning_update', data,
                                 room=list(self.positioning_subscribers))
                logger.debug(f"广播定位更新到 {len(self.positioning_subscribers)} 个客户端")
        except Exception as e:
            logger.error(f"广播定位更新失败: {e}")
    
    def broadcast_network_update(self, data: Dict):
        """广播网络状态更新"""
        try:
            if self.network_subscribers:
                self.socketio.emit('network_update', data,
                                 room=list(self.network_subscribers))
                logger.debug(f"广播网络更新到 {len(self.network_subscribers)} 个客户端")
        except Exception as e:
            logger.error(f"广播网络更新失败: {e}")
    
    def broadcast_to_all(self, event: str, data: Dict):
        """向所有连接的客户端广播"""
        try:
            if self.connected_clients:
                self.socketio.emit(event, data, broadcast=True)
                logger.debug(f"广播事件 {event} 到所有客户端")
        except Exception as e:
            logger.error(f"广播事件失败: {e}")
    
    def send_to_client(self, client_id: str, event: str, data: Dict):
        """向特定客户端发送消息"""
        try:
            if client_id in self.connected_clients:
                self.socketio.emit(event, data, room=client_id)
                logger.debug(f"发送事件 {event} 到客户端 {client_id}")
        except Exception as e:
            logger.error(f"发送消息到客户端失败: {e}")
    
    def get_connection_stats(self) -> Dict:
        """获取连接统计"""
        return {
            'totalConnections': len(self.connected_clients),
            'simulationSubscribers': len(self.simulation_subscribers),
            'positioningSubscribers': len(self.positioning_subscribers),
            'networkSubscribers': len(self.network_subscribers)
        }
    
    def _get_client_id(self) -> str:
        """获取客户端ID"""
        from flask import request
        return request.sid
    
    def _get_current_timestamp(self) -> float:
        """获取当前时间戳"""
        import time
        return time.time()
    
    def _is_simulation_running(self) -> bool:
        """检查仿真是否正在运行"""
        try:
            from .routes.simulation import _simulation_running
            return _simulation_running
        except:
            return False


