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
- **Web前端系统**: 完整的Vue.js前端界面
- **后端API系统**: 完整的Flask REST API
- **DRL训练界面**: 深度强化学习训练和监控
- **实验批跑系统**: 批量实验、消融实验、统计分析

## ✅ 对齐完成的设计文档章节
- **3.2 DRL准入控制**: 状态/动作/奖励/训练功能完整实现
- **3.6 实验与消融**: 批跑与统计分析系统完整实现
- **3.7 Web/API与前端**: 基础功能齐全，支持实时监控

## 🚧 需要完善的模块

### Beam Hint与定位联动 (3.5节)
- **状态**: 基础定位服务已实现，缺少Beam Hint算法
- **要求**:
  - 基于可见性+FIM增益的Beam Hint打分
  - 与DSROQ联动的重分配策略
  - 定位质量触发机制

### Hypatia真实数据管线 (3.4节)
- **状态**: 使用简化适配器，需要真实Hypatia集成
- **要求**:
  - 真实TLE/ISL/GSL数据管线
  - 可配置的真实/简化模式切换
  - 与参考参数对齐的校准

### Web系统架构 (已完成)
```
web/
├── frontend/                    # Vue.js前端 ✅
│   ├── src/
│   │   ├── views/              # 页面视图 ✅
│   │   │   ├── Layout.vue      # 主布局
│   │   │   ├── Dashboard.vue   # 仪表板
│   │   │   ├── Simulation.vue  # 仿真控制
│   │   │   ├── DRLTraining.vue # DRL训练
│   │   │   ├── Experiments.vue # 实验批跑
│   │   │   └── ...            # 其他页面
│   │   ├── components/         # Vue组件 ✅
│   │   ├── stores/            # Pinia状态管理 ✅
│   │   ├── api/               # API接口 ✅
│   │   └── utils/             # 工具函数 ✅
│   ├── package.json
│   └── vite.config.ts
├── backend/                    # Flask后端API ✅
│   ├── src/api/
│   │   ├── main.py            # API入口 ✅
│   │   ├── routes/            # API路由 ✅
│   │   │   ├── simulation.py  # 仿真控制
│   │   │   ├── admission.py   # 准入控制(含DRL)
│   │   │   ├── experiments.py # 实验批跑
│   │   │   └── ...           # 其他路由
│   │   ├── websocket.py       # WebSocket处理 ✅
│   │   └── middleware.py      # 中间件 ✅
│   └── requirements.txt
├── docker-compose.yml          # 容器化部署 ✅
└── run_web_system.py          # 一键启动脚本 ✅
```

### 实验批跑系统架构 (新增)
```
src/experiments/                # 实验批跑模块 ✅
├── batch_runner.py             # 批量实验运行器
├── experiment_config.py        # 实验配置管理
├── statistical_analysis.py    # 统计分析模块
├── chart_generator.py          # 图表生成器
└── __init__.py
```

提示：如需进一步细化某一部分，请告诉我具体章节，我会在对应文档中继续完善。
