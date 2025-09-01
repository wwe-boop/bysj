## 设计—论文—实现 对齐清单

### 1. 目的与范围
- 明确 design 与 docs（论文）的一致性，并核对当前代码实现的覆盖度与差距。
- 输出可执行的行动项与验收标准，指导后续补齐工作。

### 2. 汇总结论
- 结论：总体架构与论文一致，已具备端到端原型；实现侧在真实仿真联动、DRL训练闭环、Beam Hint 联动及实验批跑与统计等方面尚有差距。

### 3. 对齐项明细

#### 3.1 架构与模块
- 状态：已对齐
- 说明：分层架构（DRL 准入 → DSROQ → Hypatia/仿真 → 可视化）与 `docs/03_system_design.md`、`docs/07_system_impl.md` 一致。
- 主要代码：`src/admission/*`，`src/dsroq/*`，`src/hypatia/*`，`src/positioning/*`，`web/*`
- 行动项：无
- 验收：N/A

#### 3.2 DRL 准入控制（状态/动作/奖励/训练）
- 状态：部分对齐
- 差距：
  - 训练环境：`PPO` 使用 `DummyVecEnv` 占位，未与真实观测对接。
  - 奖励函数：未完全纳入公平性/稳定性/定位项（CRLB/GDOP/SINR）。
  - 训练评估：缺少可复现训练/评估脚本与指标落盘流程。
- 行动项：
  - 接入真实环境观测（来自 `HypatiaAdapter/NS3Simulator`）替换 Dummy 环境。
  - 扩展奖励：QoE 变化 + Jain 公平性 + 效率 + 稳定性 + 定位项（CRLB/GDOP/SINR）。
  - 完成训练/评估脚本（多场景评测、日志与曲线导出）。
- 验收：
  - 训练可复现，指标（mean/std）与论文区间一致；推理端到端稳定。

#### 3.3 DSROQ（MCTS/李雅普诺夫/带宽分配）
- 状态：已对齐（架构完整）
- 差距：
  - 与 Beam Hint/定位的联动策略未接入；算法参数未全面配置化。
- 行动项：
  - 在优化目标中引入 `beam_hint` 的软约束或次级目标，支持轻量重路由/重分配。
  - 参数化路由/调度权重，纳入配置与实验维度。
- 验收：
  - 有/无 Hint 对比实验显著差异；统计指标（路由时延/分配成功率/利用率）导出完整。

#### 3.4 Hypatia 与 ns-3 联动
- 状态：部分对齐
- 差距：
  - `HypatiaAdapter` 默认走简化分支；`NS3Simulator` 为自研简化模拟，未接真实 ns-3。
- 对齐方案（落地计划）：
  1) 配置开关
  - 在 `SystemConfig` 增加 `backend` 节点，含开关：

    ```yaml
    backend:
      hypatia_mode: real   # real | simplified
      ns3_mode: real       # real | simplified
      data_dir: /data/hypatia   # 生成/读取 TLE/ISL/GSL/动态状态的根目录
    ```

  2) 适配器改造（`src/hypatia/hypatia_adapter.py`）
  - 构造函数接收 `backend` 配置；按 `hypatia_mode` 选择真实/简化路径：
    - real：生成/读取 TLE、ISL、GSL、动态状态；提供 `get_network_state/links/capacity/utilization` 实测或近似真实映射。
    - simplified：沿用现有简化轨道与链路模型。
  - 若 `ns3_mode=real`，通过统一接口委派给真实 ns-3 绑定（或预留适配层）；否则使用现有 `NS3Simulator`。

  3) 仿真引擎接入（`src/simulation/simulation_engine.py`）
  - 初始化时将 `config.backend` 传入 `HypatiaAdapter`，并在状态获取处读取真实/简化产出的容量/利用率/时延。
  - 将性能指标收集对齐为：吞吐、平均/分位延迟、丢包、利用率，来源于 ns-3（real）或 `NS3Simulator`（simplified）。

  4) 校准与验收
  - 指标与阈值（针对相同输入流与拓扑）：
    - 容量估计误差（简化 vs 真实）≤ 15%
    - 端到端时延比值（简化/真实）∈ [0.67, 1.5]
    - 丢包率差值 ≤ 0.05
  - 功能验证：运行时可通过配置切换 `real/simplified`，无需代码改动；API 输出字段一致。

  5) 冒烟与批跑
  - 冒烟：启动最小场景，轮询 `/api/.../status|metrics`，对比 real/simplified 两组关键指标并落盘 CSV。
  - 批跑：对星座/负载/故障场景在两模式下跑对照，生成校准报告（自动绘制散点/回归图）。

- 验收：
  - 配置开关生效、两模式运行一致；核心指标满足阈值；生成校准报告与对照图表。

#### 3.5 定位与 Beam Hint
- 状态：部分对齐
- 现状：`PositioningCalculator` 已实现 CRLB/GDOP/SINR/可见星；`beam_hint.py` 为占位（固定推荐）。
- 差距：
  - 未实现基于可见性 + FIM 增益打分的 Beam Hint；未与 DSROQ 联动触发重分配。
- 行动项：
  - 实现 Beam Hint 打分（可见性、FIM 增益、几何多样性）与预算选择。
  - 在准入/DSROQ 中加入 `pos_quality` 触发策略（延迟/降级/重分配）。
- 验收：
  - Beam Hint 有效性实验通过（CRLB/GDOP/QoE/admission_rate 明显提升）。

#### 3.6 实验与消融（批跑与统计）
- 状态：部分对齐
- 差距：
  - 场景批跑与消融维度（状态/奖励/动作集）自动化不足；统计检验与图表导出不全。
- 行动项：
  - 实现场景批跑（负载/星座/故障/动作集/奖励项）。
  - 完善 t 检验/ANOVA 与图表导出（与论文图一致）。
- 验收：
  - 一键生成论文图表与表格，含显著性标注与可复现实验日志。

#### 3.7 Web/API 与前端
- 状态：部分对齐（训练/评估看板已接入）
- 现状：
  - 后端：`web/backend/src/api/routes/admission.py` 已扩展训练/评估相关路由。
  - 前端：新增 `web/frontend/src/api/drl.ts`，组件 `web/frontend/src/components/DRLEnvironmentState.vue`、`DRLTrainingChart.vue`、`RewardBreakdown.vue`，视图 `web/frontend/src/views/DRLTraining.vue`；`web/frontend/src/router/index.ts` 已注册训练路由，`web/frontend/src/views/Layout.vue` 增加入口。
- 差距：
  - 消融结果/对比视图未完成（多维切换、统计显著性标注、结果表导出）。
  - Beam Hint 可视化（地图/链路/星座叠加层）与指标看板未接入；与 DSROQ/准入的联动指标缺失。
  - 训练/评估数据导出（CSV/PNG）未统一；指标实时推送机制待确认与完善（如无则补充流式/WS）。
- 行动项：
  - 实现“消融实验”页面：维度切换（状态/动作/奖励/星座/负载）、对比曲线与结果表，含 t 检验/ANOVA 标注与导出。
  - 实现 Beam Hint 可视化图层（轨道/可见星/链路/推荐 Beam）与指标卡；与 DSROQ/准入页面联动。
  - 统一 API/数据协议与导出：训练/评估指标、消融结果与 Beam Hint 数据的 CSV/PNG 一键导出。
- 验收：
  - 前端可实时查看 QoE/准入/定位/Hint 与消融结果；训练/评估曲线与结果表支持导出；若开启实时推送可平滑更新。

#### 3.8 文档与复现
- 状态：基础完成
- 已完成：
  - 指南：`docs/hypatia_setup.md`（安装与模式切换、最小可跑、配置与场景、故障排查）
  - 默认配置：`experiments/configs/default.yaml`
  - 默认场景清单：`experiments/scenarios/defaults.yaml`
- 待完善：
  - 训练/评估与批跑脚本的复现指引与一键命令
  - 论文图表一键生成流程与显著性检验示例
- 验收：
  - 新环境按文档可无障碍启动 simplified 模式并查看指标；
  - 按指引可切换 real Hypatia 并完成冒烟；
  - 补齐训练/批跑后可复现主要实验。

### 4. 优先级与里程碑
- P0（立即）：
  - Hypatia 真实数据管线可切换；DRL 奖励补全并对接真实观测；Beam Hint 核心算法与 DSROQ 联动；批跑与统计脚本。
- P1（近期）：
  - 前端实验看板与 Hint 可视化；算法参数配置化与实验维度管理。
- P2（随访）：
  - 文档完善与复现流程优化；结果归档与长程回归测试。

### 5. 参考文件
- 设计：`design/system_architecture.md`，`design/algorithm_design.md`，`design/experiment_design.md`
- 论文：`docs/03_system_design.md`，`docs/07_system_impl.md`，其余章节
- 代码：
  - 准入：`src/admission/`
  - DSROQ：`src/dsroq/`
  - Hypatia：`src/hypatia/`
  - 定位：`src/positioning/`
  - Web：`web/backend`，`web/frontend`

### 6. 变更记录
- v0.1（初版）：整理对齐清单与行动项（自动生成）。


