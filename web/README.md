# LEO卫星网络仿真系统 Web界面

基于Vue 3 + Flask的LEO卫星网络智能准入控制与资源分配系统Web界面。

## 系统架构

```
web/
├── frontend/                 # Vue.js前端
│   ├── src/
│   │   ├── components/      # Vue组件
│   │   ├── views/          # 页面视图
│   │   ├── stores/         # Pinia状态管理
│   │   ├── api/            # API接口
│   │   └── utils/          # 工具函数
│   ├── package.json
│   └── vite.config.ts
├── backend/                 # Flask后端API
│   ├── src/api/
│   │   ├── main.py         # API入口
│   │   ├── routes/         # API路由
│   │   └── websocket/      # WebSocket处理
│   └── requirements.txt
└── docker-compose.yml       # 容器化部署
```

## 功能特性

### 前端功能
- 🎯 **实时仪表板** - 系统状态监控和关键指标展示
- 🎮 **仿真控制** - 场景选择、参数配置、启动/停止控制
- 📊 **数据可视化** - 性能趋势图表、实时监控图表
- 🌐 **网络拓扑** - 3D卫星网络可视化
- 🔐 **准入控制** - 算法配置、请求处理、统计分析
- 📍 **定位服务** - 定位质量监控、覆盖范围分析
- 📋 **场景管理** - 仿真场景的创建、编辑、验证
- 📈 **统计分析** - 性能数据导出、历史趋势分析

### 后端功能
- 🚀 **REST API** - 完整的RESTful API接口
- 🔌 **WebSocket** - 实时数据推送和事件通知
- 🎯 **仿真控制** - 仿真生命周期管理
- 📊 **性能监控** - 实时指标收集和分析
- 🌐 **网络状态** - 卫星网络状态查询
- 🔐 **准入控制** - 准入决策和统计
- 📍 **定位服务** - 定位质量计算
- 📋 **场景管理** - 场景CRUD操作

## 技术栈

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件**: Element Plus
- **状态管理**: Pinia
- **图表库**: ECharts
- **3D可视化**: Three.js/Cesium
- **HTTP客户端**: Axios
- **WebSocket**: Socket.IO Client

### 后端
- **框架**: Flask + Flask-SocketIO
- **API文档**: Flask-RESTX
- **数据验证**: Marshmallow
- **异步支持**: Eventlet
- **缓存**: Redis
- **日志**: Loguru

## 快速开始

### 方式一：使用启动脚本（推荐）

```bash
# 1. 确保已安装Python 3.8+和Node.js 16+
python --version
node --version

# 2. 安装后端依赖
pip install -r web/backend/requirements.txt

# 3. 运行启动脚本
python run_web_system.py
```

启动脚本会自动：
- 检查系统依赖
- 安装前端依赖
- 启动后端API服务 (http://localhost:5000)
- 启动前端开发服务 (http://localhost:3000)

### 方式二：手动启动

#### 启动后端
```bash
cd web/backend
pip install -r requirements.txt
python src/api/main.py --host 0.0.0.0 --port 5000 --debug
```

#### 启动前端
```bash
cd web/frontend
npm install
npm run dev
```

### 方式三：Docker部署

```bash
cd web
docker-compose up -d
```

## 访问地址

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:5000
- **API文档**: http://localhost:5000/api/docs
- **健康检查**: http://localhost:5000/api/health

## API接口

### 仿真控制
- `GET /api/simulation/status` - 获取仿真状态
- `POST /api/simulation/start` - 启动仿真
- `POST /api/simulation/stop` - 停止仿真
- `POST /api/simulation/reset` - 重置仿真

### 网络状态
- `GET /api/network/state` - 获取网络状态
- `GET /api/network/topology` - 获取网络拓扑
- `GET /api/network/satellites` - 获取卫星信息
- `GET /api/network/flows` - 获取流量信息

### 准入控制
- `POST /api/admission/request` - 处理准入请求
- `GET /api/admission/statistics` - 获取准入统计
- `GET /api/admission/config` - 获取准入配置
- `PUT /api/admission/config` - 更新准入配置

### 定位服务
- `POST /api/positioning/request` - 处理定位请求
- `GET /api/positioning/quality` - 获取定位质量
- `GET /api/positioning/coverage` - 获取覆盖范围
- `GET /api/positioning/statistics` - 获取定位统计

### 场景管理
- `GET /api/scenarios` - 获取所有场景
- `GET /api/scenarios/{name}` - 获取特定场景
- `POST /api/scenarios` - 创建场景
- `PUT /api/scenarios/{name}` - 更新场景
- `DELETE /api/scenarios/{name}` - 删除场景

## WebSocket事件

### 客户端发送
- `subscribe_simulation` - 订阅仿真更新
- `subscribe_positioning` - 订阅定位更新
- `subscribe_network` - 订阅网络更新
- `ping` - 心跳检测

### 服务器推送
- `simulation_update` - 仿真状态更新
- `simulation_started` - 仿真启动通知
- `simulation_completed` - 仿真完成通知
- `simulation_error` - 仿真错误通知
- `positioning_update` - 定位数据更新
- `network_update` - 网络状态更新

## 开发指南

### 前端开发
```bash
cd web/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

### 后端开发
```bash
cd web/backend

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python src/api/main.py --debug

# 运行测试
pytest

# 代码格式化
black src/
```

## 配置说明

### 前端配置 (vite.config.ts)
- 代理配置：API请求代理到后端
- 构建配置：输出目录、代码分割
- 插件配置：Vue、TypeScript、Element Plus

### 后端配置 (main.py)
- Flask应用配置
- CORS跨域配置
- SocketIO配置
- 日志配置

## 故障排除

### 常见问题

1. **前端无法连接后端**
   - 检查后端是否正常启动
   - 确认端口5000未被占用
   - 检查防火墙设置

2. **WebSocket连接失败**
   - 确认SocketIO服务正常运行
   - 检查浏览器WebSocket支持
   - 查看浏览器控制台错误信息

3. **仿真无法启动**
   - 检查仿真引擎是否正确初始化
   - 确认场景配置文件存在
   - 查看后端日志错误信息

4. **图表不显示**
   - 检查ECharts库是否正确加载
   - 确认数据格式正确
   - 查看浏览器控制台错误

### 日志查看
- 前端日志：浏览器开发者工具控制台
- 后端日志：终端输出或logs/目录下的日志文件

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License
