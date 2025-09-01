# 术语与缩写表（Glossary）

> 说明：本文统一采用中文为主、括号给出英文与缩写（如有）。

- LEO（Low Earth Orbit，近地轨道）：高度约 160–2000 km 的轨道层，具备低时延与广覆盖特性。
- QoE（Quality of Experience，用户体验质量）：从用户感知出发的综合体验指标，受时延、丢包、吞吐、波动等影响。
- QoS（Quality of Service，服务质量）：网络层面可测度的性能保障指标，如带宽、时延、抖动、丢包。
- EF/AF/BE（Expedited/Assured/Best Effort，业务分类）：分别表示加速转发、可保障转发、尽力而为三类业务优先级。
- 准入控制（Admission Control）：决定新业务/新流是否接入网络的策略与机制。
- DRL（Deep Reinforcement Learning，深度强化学习）：结合深度学习与强化学习的序贯决策方法。
- PPO（Proximal Policy Optimization，近端策略优化）：常用的策略梯度类 DRL 算法，收敛稳定性较好。
- DSROQ（Routing/Bandwidth/Scheduling Joint Optimization，联合路由/带宽/调度优化）：本文指代的下层执行优化与控制框架。
- Hypatia：LEO 卫星网络仿真/建模平台（本项目作为仿真后端与数据源接口）。
- MDP（Markov Decision Process，马尔可夫决策过程）：由状态、动作、转移、奖励、折扣构成的决策建模框架。
- 状态（State）：用于决策的特征集合，包括网络、业务、QoE/QoS、定位等信息。
- 动作（Action）：策略可采取的决策，如接受、拒绝、降级、延迟、部分接受等。
- 奖励（Reward）：用于评价动作优劣的信号，如 ΔQoE、公平性、效率、违规惩罚、定位可用性等加权组合。
- Jain 公平性（Jain’s Fairness Index）：度量分配公平性的指标，范围 (0,1]，越接近 1 越公平。
- 网络利用率（Utilization, Util）：链路或全网资源的使用程度占比。
- 违规率（Violations, Viol）：QoS/约束被违反的比例。
- 定位可用性（A_pos）：本文定义的定位可用性评分，范围 [0,1]。
- CRLB（Cramér–Rao Lower Bound，克拉美-罗下界）：估计方差的理论下界，用于度量定位精度下限。
- GDOP（Geometric Dilution of Precision，几何精度因子）：由几何构型导致的定位精度劣化因子，越小越好。
- SINR（Signal-to-Interference-plus-Noise Ratio，信干噪比）：接收信号与干扰/噪声的比值，越大越好。
- Beam Hint（波束调度提示）：为提升定位/通信目标而推荐的波束/卫星组合集合。
- 可见波束（Visible Beams）：在给定时刻对用户可见/可服务的波束数量或集合。
- 协作卫星（Cooperative Satellites）：参与为同一用户提供几何/测量支撑的卫星集合。
- MCTS（Monte Carlo Tree Search，蒙特卡洛树搜索）：常用于路由/调度搜索与策略改进的启发式方法。
- 李雅普诺夫优化（Lyapunov Optimization）：在队列/稳定性约束下的在线控制与调度方法。
- 置信区间（Confidence Interval, CI）：统计上对均值等指标区间置信度的度量，常用 95%CI。
- CDF（Cumulative Distribution Function，累积分布函数）：描述随机变量取值不超过某值的概率分布函数。
- 消融实验（Ablation Study）：移除或替换系统组件以评估其对性能的影响。
- 敏感性分析（Sensitivity Analysis）：研究超参数或权重变化对结果的影响。
- 可视化（Visualization）：将系统状态、指标与结果以图形化方式呈现（如 ECharts、Cesium）。
- API（Application Programming Interface，应用编程接口）：模块间通信的接口定义。
- KPI（Key Performance Indicator，关键绩效指标）：用于衡量系统目标达成情况的核心指标集合。
- 资源重分配（Reallocation）：在网络状态变化或约束触发下对路由/带宽/调度方案进行调整。
- 冷却时间（Cooldown）：限制频繁迁移/切换以稳定拓扑/几何的时间窗口设置。

---

若发现术语缺漏或需统一翻译，请在本文件中追加或修订，并在首次出现处保持与此表一致的写法。
