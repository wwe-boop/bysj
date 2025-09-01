# 项目提示词（极简跳转版）

本项目的详细提示词已按主题拆分至 docs/prompts/ 目录。请按需阅读对应条目：

- 总览与产出物：docs/prompts/00_overview.md
- 研究背景与意义：docs/prompts/01_background.md
- 文献综述：docs/prompts/02_related_work.md
- 系统设计：docs/prompts/03_system_design.md
- 方法与实验：docs/prompts/04_algorithm_and_experiments.md

详细的系统实现设计文档请查看：
- 系统架构：design/system_architecture.md
- 算法设计：design/algorithm_design.md
- 实验设计：design/experiment_design.md
- 详细系统说明：design/系统.md

# 开发原则

1. **真实集成优先**: 直接对接真实的Hypatia框架，不使用模拟实现
2. **完整功能实现**: 实现完整的DRL、DSROQ、定位算法，不简化核心逻辑
3. **可视化要求**: 必须提供REST API和前端可视化界面
4. **渐进式开发**: 可以慢慢来，但每个模块都要做到位
5. **直面困难**: 遇到技术困难时不得简化实现，应停止并说明问题与解决方案，寻求指导

# 当前实现状态

## ✅ 已完成模块
- **核心仿真引擎**: 完整的事件驱动仿真框架
- **Hypatia适配器**: 简化版本，支持1584颗卫星星座
- **准入控制**: 阈值、定位感知、DRL基础框架
- **DSROQ资源分配**: MCTS路由、李雅普诺夫优化、带宽分配
- **性能监控**: 实时指标监控和分析
- **场景管理**: 5个预定义仿真场景

## 🚧 需要完善的模块

### 前端系统 (Vue.js)
- **状态**: 仅有Flask模板，需要完整Vue前端
- **要求**:
  - Vue 3 + TypeScript + Vite
  - Element Plus UI组件库
  - 实时数据可视化 (Chart.js/ECharts)
  - 3D卫星网络可视化 (Three.js/Cesium)
  - WebSocket实时通信

### 后端API系统
- **状态**: 基础Flask框架，缺少完整API路由
- **要求**:
  - 完整的REST API (src/api/main.py)
  - 准入控制API (/api/admission/*)
  - 定位服务API (/api/positioning/*)
  - 统计分析API (/api/statistics/*)
  - WebSocket实时推送

### Web系统架构
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

提示：如需进一步细化某一部分，请告诉我具体章节，我会在对应文档中继续完善。
