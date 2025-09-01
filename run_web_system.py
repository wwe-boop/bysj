#!/usr/bin/env python3
"""
启动LEO卫星网络仿真系统Web服务
包含前端和后端的完整启动脚本
"""

import os
import sys
import subprocess
import threading
import time
import signal
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSystemLauncher:
    """Web系统启动器"""
    
    def __init__(self):
        self.processes = []
        self.running = False
        
    def check_dependencies(self):
        """检查依赖"""
        logger.info("检查系统依赖...")
        
        # 检查Python
        try:
            import flask
            import flask_socketio
            logger.info("✓ Python后端依赖已安装")
        except ImportError as e:
            logger.error(f"✗ Python后端依赖缺失: {e}")
            logger.info("请运行: pip install -r web/backend/requirements.txt")
            return False
        
        # 检查Node.js
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✓ Node.js已安装: {result.stdout.strip()}")
            else:
                logger.error("✗ Node.js未安装")
                return False
        except FileNotFoundError:
            logger.error("✗ Node.js未安装")
            return False
        
        # 检查npm
        try:
            result = subprocess.run(['npm', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✓ npm已安装: {result.stdout.strip()}")
            else:
                logger.error("✗ npm未安装")
                return False
        except FileNotFoundError:
            logger.error("✗ npm未安装")
            return False
        
        return True
    
    def install_frontend_dependencies(self):
        """安装前端依赖"""
        frontend_dir = Path("web/frontend")
        if not frontend_dir.exists():
            logger.error("前端目录不存在")
            return False
        
        package_json = frontend_dir / "package.json"
        node_modules = frontend_dir / "node_modules"
        
        if not package_json.exists():
            logger.error("package.json不存在")
            return False
        
        if not node_modules.exists():
            logger.info("安装前端依赖...")
            try:
                subprocess.run(['npm', 'install'], 
                             cwd=frontend_dir, check=True)
                logger.info("✓ 前端依赖安装完成")
            except subprocess.CalledProcessError as e:
                logger.error(f"✗ 前端依赖安装失败: {e}")
                return False
        else:
            logger.info("✓ 前端依赖已存在")
        
        return True
    
    def start_backend(self):
        """启动后端服务"""
        logger.info("启动后端API服务...")
        
        backend_script = Path("web/backend/src/api/main.py")
        if not backend_script.exists():
            logger.error("后端启动脚本不存在")
            return None
        
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path.cwd())
            
            process = subprocess.Popen([
                sys.executable, str(backend_script),
                '--host', '0.0.0.0',
                '--port', '5000',
                '--debug'
            ], env=env)
            
            logger.info("✓ 后端服务已启动 (PID: {})".format(process.pid))
            logger.info("  后端地址: http://localhost:5000")
            
            return process
            
        except Exception as e:
            logger.error(f"✗ 后端服务启动失败: {e}")
            return None
    
    def start_frontend(self):
        """启动前端服务"""
        logger.info("启动前端开发服务...")
        
        frontend_dir = Path("web/frontend")
        if not frontend_dir.exists():
            logger.error("前端目录不存在")
            return None
        
        try:
            process = subprocess.Popen([
                'npm', 'run', 'dev'
            ], cwd=frontend_dir)
            
            logger.info("✓ 前端服务已启动 (PID: {})".format(process.pid))
            logger.info("  前端地址: http://localhost:3000")
            
            return process
            
        except Exception as e:
            logger.error(f"✗ 前端服务启动失败: {e}")
            return None
    
    def wait_for_service(self, url, timeout=30):
        """等待服务启动"""
        import requests
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def start_system(self):
        """启动整个系统"""
        logger.info("=" * 50)
        logger.info("启动LEO卫星网络仿真系统Web服务")
        logger.info("=" * 50)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 安装前端依赖
        if not self.install_frontend_dependencies():
            return False
        
        # 启动后端
        backend_process = self.start_backend()
        if not backend_process:
            return False
        
        self.processes.append(backend_process)
        
        # 等待后端启动
        logger.info("等待后端服务启动...")
        if self.wait_for_service("http://localhost:5000/api/health"):
            logger.info("✓ 后端服务已就绪")
        else:
            logger.warning("⚠ 后端服务启动超时，但继续启动前端")
        
        # 启动前端
        frontend_process = self.start_frontend()
        if not frontend_process:
            self.stop_system()
            return False
        
        self.processes.append(frontend_process)
        
        # 等待前端启动
        logger.info("等待前端服务启动...")
        time.sleep(5)  # 前端启动需要更多时间
        
        self.running = True
        
        logger.info("=" * 50)
        logger.info("系统启动完成！")
        logger.info("前端地址: http://localhost:3000")
        logger.info("后端API: http://localhost:5000")
        logger.info("按 Ctrl+C 停止服务")
        logger.info("=" * 50)
        
        return True
    
    def stop_system(self):
        """停止系统"""
        logger.info("正在停止服务...")
        
        self.running = False
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"✓ 进程 {process.pid} 已停止")
            except subprocess.TimeoutExpired:
                logger.warning(f"强制终止进程 {process.pid}")
                process.kill()
            except Exception as e:
                logger.error(f"停止进程失败: {e}")
        
        self.processes.clear()
        logger.info("✓ 所有服务已停止")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}")
        self.stop_system()
        sys.exit(0)
    
    def run(self):
        """运行系统"""
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            if self.start_system():
                # 保持运行
                while self.running:
                    time.sleep(1)
                    
                    # 检查进程状态
                    for process in self.processes[:]:
                        if process.poll() is not None:
                            logger.error(f"进程 {process.pid} 意外退出")
                            self.processes.remove(process)
                    
                    # 如果所有进程都退出了，停止系统
                    if not self.processes:
                        logger.error("所有进程都已退出")
                        break
            else:
                logger.error("系统启动失败")
                return 1
                
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        except Exception as e:
            logger.error(f"系统运行错误: {e}")
        finally:
            self.stop_system()
        
        return 0


def main():
    """主函数"""
    launcher = WebSystemLauncher()
    return launcher.run()


if __name__ == "__main__":
    exit(main())
