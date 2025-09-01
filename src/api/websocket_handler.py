"""
WebSocket处理器

处理实时通信和数据推送
"""

import logging
from typing import Dict, Set, Any


class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self, web_server):
        self.web_server = web_server
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 客户端订阅管理
        self.connected_clients: Set[str] = set()
        self.simulation_subscribers: Set[str] = set()
        
    def on_connect(self, sid: str):
        """客户端连接"""
        self.connected_clients.add(sid)
        
        # 发送初始状态
        self.web_server.sio.emit('connection_established', {
            'message': '连接成功',
            'server_status': 'running',
            'simulation_running': self.web_server.simulation_running
        }, room=sid)
        
        self.logger.info(f"客户端 {sid} 已连接，当前连接数: {len(self.connected_clients)}")
    
    def on_disconnect(self, sid: str):
        """客户端断开"""
        self.connected_clients.discard(sid)
        self.simulation_subscribers.discard(sid)
        
        self.logger.info(f"客户端 {sid} 已断开，当前连接数: {len(self.connected_clients)}")
    
    def subscribe_simulation(self, sid: str, data: Dict[str, Any]):
        """订阅仿真更新"""
        self.simulation_subscribers.add(sid)
        
        # 发送当前仿真状态
        if self.web_server.simulation_running and self.web_server.simulation_engine:
            current_status = self.web_server.simulation_engine.get_current_status()
            self.web_server.sio.emit('simulation_status', current_status, room=sid)
        
        self.web_server.sio.emit('subscription_confirmed', {
            'type': 'simulation',
            'message': '已订阅仿真更新'
        }, room=sid)
        
        self.logger.info(f"客户端 {sid} 订阅仿真更新")
    
    def unsubscribe_simulation(self, sid: str, data: Dict[str, Any]):
        """取消订阅仿真更新"""
        self.simulation_subscribers.discard(sid)
        
        self.web_server.sio.emit('subscription_cancelled', {
            'type': 'simulation',
            'message': '已取消订阅仿真更新'
        }, room=sid)
        
        self.logger.info(f"客户端 {sid} 取消订阅仿真更新")
    
    def broadcast_to_simulation_subscribers(self, event: str, data: Dict[str, Any]):
        """向仿真订阅者广播消息"""
        for sid in self.simulation_subscribers:
            self.web_server.sio.emit(event, data, room=sid)
    
    def broadcast_to_all(self, event: str, data: Dict[str, Any]):
        """向所有连接的客户端广播消息"""
        self.web_server.sio.emit(event, data)
    
    def send_to_client(self, sid: str, event: str, data: Dict[str, Any]):
        """向特定客户端发送消息"""
        if sid in self.connected_clients:
            self.web_server.sio.emit(event, data, room=sid)
    
    def get_connection_stats(self) -> Dict[str, int]:
        """获取连接统计"""
        return {
            'total_connections': len(self.connected_clients),
            'simulation_subscribers': len(self.simulation_subscribers)
        }
