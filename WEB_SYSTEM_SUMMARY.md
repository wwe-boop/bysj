# LEO卫星网络仿真系统Web界面 - 完整实现总结

## 系统概述

我已经为您创建了一个完整的LEO卫星网络仿真系统Web界面，包含前端Vue.js应用和后端Flask API。该系统提供了直观的用户界面来控制和监控LEO卫星网络仿真。

## 系统架构

```
web/
├── frontend/                    # Vue.js前端应用
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   │   ├── Layout.vue      # 主布局
│   │   │   ├── Dashboard.vue   # 仪表板
│   │   │   ├── Simulation.vue  # 仿真控制
│   │   │   ├── Admission.vue   # 准入控制
│   │   │   └── Positioning.vue # 定位服务
│   │   ├── components/         # 可复用组件
│   │   │   ├── MetricCard.vue  # 指标卡片
│   │   │   ├── PerformanceChart.vue # 性能图表
│   │   │   ├── RealTimeChart.vue    # 实时图表
│   │   │   ├── EventLog.vue         # 事件日志
│   │   │   ├── AdmissionStats.vue   # 准入统计
│   │   │   └── PositioningStats.vue # 定位统计
│   │   ├── stores/             # Pinia状态管理
│   │   │   ├── app.ts          # 应用状态
│   │   │   ├── simulation.ts   # 仿真状态
│   │   │   └── websocket.ts    # WebSocket状态
│   │   ├── api/                # API接口
│   │   │   ├── index.ts        # 基础API配置
│   │   │   ├── simulation.ts   # 仿真API
│   │   │   └── admission.ts    # 准入控制API
│   │   └── assets/styles/      # 样式文件
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── backend/                     # Flask后端API
│   ├── src/api/
│   │   ├── main.py             # API主入口
│   │   ├── routes/             # API路由
│   │   │   ├── simulation.py   # 仿真控制路由
│   │   │   ├── network.py      # 网络状态路由
│   │   │   ├── admission.py    # 准入控制路由
│   │   │   ├── positioning.py  # 定位服务路由
│   │   │   ├── statistics.py   # 统计分析路由
│   │   │   └── scenarios.py    # 场景管理路由
│   │   ├── websocket.py        # WebSocket处理
│   │   ├── middleware.py       # 中间件
│   │   └── utils/              # 工具函数
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml           # 容器化部署
└── README.md                   # 详细文档
```

## 核心功能

### 1. 仪表板 (Dashboard)
- **系统状态监控**: 实时显示仿真状态、连接状态
- **关键指标展示**: 吞吐量、延迟、QoE评分等
- **性能趋势图表**: 历史性能数据可视化
- **实时日志**: 系统事件和操作日志

### 2. 仿真控制 (Simulation)
- **场景选择**: 从预定义场景中选择仿真场景
- **参数配置**: 设置仿真持续时间等参数
- **控制操作**: 启动、停止、重置仿真
- **实时监控**: 仿真进度和性能指标
- **事件日志**: 仿真过程中的事件记录

### 3. 准入控制 (Admission)
- **算法配置**: 选择和配置准入控制算法
- **参数调整**: 最大用户数、信号强度阈值等
- **测试功能**: 提交测试准入请求
- **统计分析**: 准入成功率、决策时间等统计
- **历史记录**: 准入决策历史查看

### 4. 定位服务 (Positioning)
- **参数配置**: 仰角掩码、GDOP阈值等
- **定位测试**: 指定位置的定位质量测试
- **指标查询**: 查询特定位置或用户集合的定位指标（Apos/CRLB/GDOP等）
- **统计信息**: 定位精度、覆盖率等统计
- **覆盖分析**: 全球定位覆盖范围分析

## 技术特性

### 前端技术
- **Vue 3 + TypeScript**: 现代化前端框架
- **Element Plus**: 企业级UI组件库
- **Pinia**: 轻量级状态管理
- **ECharts**: 专业图表库
- **Vite**: 快速构建工具
- **响应式设计**: 支持多种设备

### 后端技术
- **Flask**: 轻量级Python Web框架
- **Flask-SocketIO**: WebSocket实时通信
- **RESTful API**: 标准化API接口
- **数据验证**: Marshmallow数据验证
- **异步支持**: Eventlet异步处理
- **日志系统**: 完整的日志记录

### 实时通信
- **WebSocket连接**: 实时数据推送
- **事件订阅**: 按需订阅不同类型的更新
- **心跳检测**: 连接状态监控
- **自动重连**: 连接断开自动恢复

## 启动方式

### 方式一：一键启动（推荐）
```bash
python run_web_system.py
```

### 方式二：Docker部署
```bash
cd web
docker-compose up -d
```

### 方式三：手动启动
```bash
# 启动后端
cd web/backend
pip install -r requirements.txt
python src/api/main.py

# 启动前端
cd web/frontend
npm install
npm run dev
```

## 访问地址
- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:5000
- **API文档**: http://localhost:5000/api/docs

## 主要API端点

### 仿真控制
- `GET /api/simulation/status` - 获取仿真状态
- `POST /api/simulation/start` - 启动仿真
- `POST /api/simulation/stop` - 停止仿真

### 准入控制
- `POST /api/admission/request` - 处理准入请求
- `GET /api/admission/statistics` - 获取准入统计

### 定位服务
- `GET /api/positioning/metrics` - 获取定位指标
- `POST /api/positioning/beam_hint` - 获取波束候选

### 网络状态
- `GET /api/network/state` - 获取网络状态
- `GET /api/network/topology` - 获取网络拓扑

## 系统集成

该Web系统与您现有的LEO卫星网络仿真系统完全集成：

1. **仿真引擎集成**: 通过API调用控制仿真引擎
2. **数据同步**: 实时获取仿真状态和性能数据
3. **配置管理**: 动态配置仿真参数和算法
4. **结果展示**: 可视化展示仿真结果和分析

## 扩展性

系统设计具有良好的扩展性：

1. **模块化设计**: 前后端分离，组件化开发
2. **API标准化**: RESTful API便于集成
3. **插件架构**: 支持新算法和功能模块
4. **配置驱动**: 通过配置文件扩展功能

## 部署建议

1. **开发环境**: 使用一键启动脚本
2. **测试环境**: 使用Docker Compose
3. **生产环境**: 使用Kubernetes或云服务
4. **监控**: 集成Prometheus和Grafana

这个Web系统为您的LEO卫星网络仿真研究提供了完整的可视化界面和控制平台，大大提升了系统的可用性和研究效率。

## 端点-数据结构映射（补充）

| 端点 | 关键请求字段 | 关键响应字段 | 相关章节 |
| --- | --- | --- | --- |
| `POST /api/admission/request` | `flows[]`, `profiles.weights`, `constraints.{lambda_pos,seam_penalty,reroute_cooldown_ms,beam_hint}` | `decision`, `accepted_flows[]`, `policies` | 第3.2.3/第4章 |
| `GET /api/positioning/metrics` | `time`, `users[]` | `apos`, `crlb_mean/p95`, `gdop_mean/p95` | 第5章 |
| `POST /api/positioning/beam_hint` | `time`, `users[]`, `budget` | 每用户`candidates[]` | 第5章 |
| `GET /api/network/topology` | - | 拓扑/可见性视图 | 第3.3.1 |
| `POST /api/simulation/start` | 场景/模式参数 | 运行状态/会话ID | 第6.8 |

字段命名应与 `docs/03_system_design.md` 中“接口契约总览”保持一致，便于前后端与实验脚本共享同一Schema。

## 容错/降级演示说明（补充）

- 目的：复现实效保护策略（第3.2.2），在模块异常或资源紧张时降级到“阈值准入+启发式调度”。
- 建议演示路径：
  1. 通过 `POST /api/simulation/start` 传入模式参数（示例：`{"admission_mode":"drl|threshold", "scheduler_mode":"dsroq|heuristic"}`）。
  2. 切换到 `threshold+heuristic` 后，对比 QoE/AR/Jain/Util/Delay 与 `drl+dsroq` 的差异。
  3. 在前端显示明显的模式标记与状态提示，防止结果误读。

注：上述为文档级接口建议，用于对齐论文与系统演示，不限定具体实现。
