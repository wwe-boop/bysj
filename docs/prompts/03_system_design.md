# 系统设计（精简提纲）

- 分层架构：DRL准入控制层 / 融合定位层（CRLB/GDOP/SINR/协作指标）/ Hypatia网络状态层 / DSROQ资源分配层 / ns3执行层
- 模块：状态提取器、PPO Agent、动作执行器、星座管理器、拓扑计算器、MCTS路由器、李雅普诺夫调度器
- 技术栈：Hypatia + PyTorch + SB3 + Flask + Vue/Cesium + Docker
- 交互流程：请求到达→状态提取→DRL决策→DSROQ分配→Hypatia仿真→评估与学习
- 代码骨架：src/ 下模块划分，design/ 下详细设计，docs/ 下论文
