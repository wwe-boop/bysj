#!/usr/bin/env python3
"""
启动LEO卫星网络仿真系统Web服务器
"""

import sys
import logging
import argparse
from pathlib import Path

# 添加src目录到路径
sys.path.append('src')

from src.core.config import SystemConfig
from src.api.web_server import WebServer


def setup_logging(debug: bool = False):
    """设置日志"""
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('web_server.log')
        ]
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='LEO卫星网络仿真系统Web服务器')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口 (默认: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器主机 (默认: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    try:
        # 创建系统配置
        logger.info("初始化系统配置...")
        config = SystemConfig()
        
        # 调整配置以适合Web演示
        config.simulation.duration_seconds = 300.0  # 5分钟默认仿真
        config.simulation.flow_arrival_rate = 5.0   # 适中的到达率
        config.simulation.num_users = 50            # 适中的用户数
        
        # 创建Web服务器
        logger.info("创建Web服务器...")
        web_server = WebServer(config, port=args.port)
        
        # 启动服务器
        logger.info(f"启动Web服务器...")
        logger.info(f"访问地址: http://{args.host}:{args.port}")
        logger.info("按 Ctrl+C 停止服务器")
        
        web_server.run(debug=args.debug, host=args.host)
        
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
