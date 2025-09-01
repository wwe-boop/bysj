"""
API路由模块

包含所有的API端点定义
"""

from .simulation import simulation_bp
from .network import network_bp
from .admission import admission_bp
from .positioning import positioning_bp
from .statistics import statistics_bp
from .scenarios import scenarios_bp
from .experiments import experiments_bp

__all__ = [
    'simulation_bp',
    'network_bp', 
    'admission_bp',
    'positioning_bp',
    'statistics_bp',
    'scenarios_bp',
    'experiments_bp'
]
