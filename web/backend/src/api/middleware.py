"""
API中间件
"""

import time
import logging
from flask import request, g, jsonify
from functools import wraps

logger = logging.getLogger(__name__)


def setup_middleware(app):
    """设置中间件"""
    
    @app.before_request
    def before_request():
        """请求前处理"""
        g.start_time = time.time()
        g.request_id = generate_request_id()
        
        # 记录请求信息
        logger.info(f"[{g.request_id}] {request.method} {request.path} - {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 计算请求处理时间
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        # 添加请求ID
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        # 记录响应信息
        logger.info(f"[{getattr(g, 'request_id', 'unknown')}] {response.status_code} - {duration:.3f}s")
        
        return response
    
    @app.errorhandler(429)
    def rate_limit_handler(e):
        """速率限制处理"""
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'code': 429
        }), 429


def rate_limit(max_requests=100, window=60):
    """速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 这里可以实现速率限制逻辑
            # 目前只是简单通过
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 这里可以实现认证逻辑
        # 目前只是简单通过
        return f(*args, **kwargs)
    return decorated_function


def validate_json(f):
    """JSON验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), 400
        return f(*args, **kwargs)
    return decorated_function


def generate_request_id():
    """生成请求ID"""
    import uuid
    return str(uuid.uuid4())[:8]
