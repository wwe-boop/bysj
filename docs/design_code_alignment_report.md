## 代码—设计对齐报告（模块级）

本文档按模块核对 design 与实际代码实现的一致性，给出状态结论、关键证据、差异与建议改进项。

### 评估结论概览
- **DRL 准入控制（Admission/DRL）**: 部分一致（状态/动作/奖励设计已落地；与定位/仿真对接存在缺口）
- **DSROQ（路由+调度）**: 部分一致（核心类到位；数据结构/字段命名与设计不完全对齐）
- **Hypatia 适配层**: 部分一致（支持 simplified/real 开关；real 模式数据通路占位）
- **定位与 Beam Hint**: 部分一致（指标与 Apos 抽象实现较完整；与 DRL/DSROQ 的联动尚需打通）
- **仿真引擎（Simulation Engine）**: 部分一致（流程完整；对象对接与字段命名不一致导致闭环不稳）
- **核心配置/接口（Config/Interfaces/State）**: 基本一致（配置项覆盖齐全；少数类型/字段在下游使用不一致）

---

### 1. DRL 准入控制（`src/admission/`）
- **状态**: 部分一致
- **证据**:
  - `src/admission/drl_environment.py`：
    - 状态向量包含网络统计、QoE、时间维、请求特征、定位特征、稳定性特征、历史特征，符合 `design/algorithm_design.md` 1.1 的范围。
    - 奖励函数包含 QoE 变化、公平性、利用率、违规、延迟、定位可用性、稳定性各项，并由 `SystemConfig.drl.reward_weights` 配置。
  - `src/admission/drl_admission.py`：PPO 创建/加载与推理链路可用，动作到决策映射与设计一致（5 动作）。
- **不一致/缺口**:
  - 环境取用的 `positioning_metrics` 期望键为 `crlb_norm/gdop_norm/...`，但 `SimulationEngine` 实际传入的字典仅含 `gdop/positioning_accuracy/visible_satellites`，键名与语义不对齐，且 `current_positioning_metrics` 未被维护。
  - 稳定性特征来源 `HypatiaAdapter.get_routing_stability_metrics` 为占位固定值。
  - 训练/评估闭环脚手架缺失（批跑、落盘、日志）。
- **建议**:
  - 统一定位特征供给：在 `SimulationEngine` 内部将 `PositioningCalculator` 输出经 `positioning/metrics.py:PositioningMetrics.get_drl_state_features()` 规范化后注入 `drl_environment`。
  - 在 `HypatiaAdapter` 实现最小可用的稳定性度量（基于 TEG/可见性窗口近似）。
  - 增加训练与评估脚本（参考 `docs/06_experiments.md` 协议），统一指标落盘。

---

### 2. DSROQ 路由与调度（`src/dsroq/`）
- **状态**: 部分一致
- **证据**:
  - `src/dsroq/core.py:LyapunovScheduler`：实现与 `design/algorithm_design.md` 李雅普诺夫伪代码一致，提供 `schedule_flow` 与 `drift+penalty` 计算。
  - `src/dsroq/dsroq_controller.py`：整合 MCTS 路由与调度，暴露 `process_user_request/find_route/allocate_bandwidth`。
- **不一致/缺口**:
  - `AllocationResult` 字段对齐问题：控制器构造结果时使用了 `expected_latency`，而 `core/state.py:AllocationResult` 需要 `expected_latency/expected_reliability/allocation_success/resource_cost` 等；`SimulationEngine` 读取字段名为 `estimated_latency`，与前者不一致。
  - 队列更新 `update_queue_states` 为空实现；与设计中的调度更新职责未对齐。
  - 与 Beam Hint/定位的联动（`lambda_pos`、`seam_penalty` 等）未在路由/代价显式注入。
- **建议**:
  - 统一 `AllocationResult` 字段：在 DSROQ 与 SimulationEngine 内统一使用 `expected_latency` 命名，并补齐 `expected_reliability/allocation_success/resource_cost` 赋值；或调整数据类以适配现状。
  - 在 MCTS 代价中注入 `seam_penalty/path_change_penalty/reroute_cooldown_ms/lambda_pos`，并将 Beam Hint 作为软约束因子。
  - 实现最简 `update_queue_states`（从 `NetworkState.queue_lengths` 与链路负载推导）。

---

### 3. Hypatia 适配层（`src/hypatia/hypatia_adapter.py`）
- **状态**: 部分一致
- **证据**:
  - 支持 `BackendConfig.hypatia_mode/ns3_mode/data_dir`，符合 `design/system_architecture.md` 的 real/simplified 切换设计。
  - simplified 模式下的 `get_network_state/get_orbit_phase/get_topology_change_rate/predict_future_capacity` 可用；real 模式存在生成与读取流程骨架。
- **不一致/缺口**:
  - real 模式 `get_network_state` 标记为占位，尚未接入动态状态读取。
  - `get_routing_stability_metrics` 为固定占位值。
- **建议**:
  - 按 `docs/design_implementation_alignment.md` 3.4 节计划完善 real 模式数据通路与指标校准；提供冒烟与对照脚本。

---

### 4. 定位与 Beam Hint（`src/positioning/`）
- **状态**: 部分一致
- **证据**:
  - `metrics.py:PositioningMetrics` 实现 CRLB/GDOP/可见性/协作度与 `Apos` 组合评分，提供 DRL 归一化特征生成函数；聚合统计与 Beam Hint 接口占位已接好。
  - `positioning_calculator.py` 存在，仿真引擎可调用计算定位质量。
- **不一致/缺口**:
  - Beam Hint 的状态感知打分与预算选择逻辑仍为简化/占位（`generate_beam_hint_with_state`）。
  - 与 DRL 环境的特征键名/对接在仿真链路中未统一（见第 1 节）。
- **建议**:
  - 按 `design/algorithm_design.md` 3.3 小节实现基于可见性+FIM 增益+几何多样性的 Hint 打分；产出 `beam_hint_score` 供 DSROQ 代价使用。
  - 在 `SimulationEngine` 内统一定位特征与键名，保证 DRL 环境可直接消费。

---

### 5. 仿真引擎（`src/simulation/simulation_engine.py`）
- **状态**: 部分一致
- **证据**:
  - 完整的主循环、组件初始化与回调框架；按设计集成 Hypatia/Admission/DSROQ/Positioning。
- **不一致/缺口**:
  - 决策判断使用 `admission_result.decision.value in ['accept', 'degraded_accept', 'partial_accept']`，而 `AdmissionDecision` 的取值为大写（如 `ACCEPT`），条件恒不满足。
  - `AllocationResult` 字段名在引擎读取时使用 `estimated_latency`，与 DSROQ 构造的 `expected_latency` 不一致。
  - 释放资源逻辑调用 `self.dsroq_controller.bandwidth_allocator.deallocate`，但 `bandwidth_allocator` 未在 DSROQ 控制器定义。
  - 未维护 `self.current_positioning_metrics` 供 DRL 环境直接读取。
- **建议**:
  - 统一枚举字符串或直接比较枚举：`admission_result.decision in {AdmissionDecision.ACCEPT,...}`。
  - 统一 `expected_latency/estimated_latency` 命名，避免字段漂移。
  - 去除或补齐 `bandwidth_allocator`；推荐将释放逻辑并入 DSROQ 控制器接口。
  - 在 `_simulation_step` 结束时缓存标准化的定位特征到 `self.current_positioning_metrics`（键名对齐 DRL 环境）。

---

### 6. 核心配置/接口/状态（`src/core/`）
- **状态**: 基本一致
- **证据**:
  - `core/config.py` 覆盖 DRL/DSROQ/Positioning/Backend 等关键参数，包含 `seam_penalty/path_change_penalty/reroute_cooldown_ms/lambda_pos` 等与设计一致的配置。
  - `core/interfaces.py`/`core/state.py` 的接口与数据类与设计契约一致，支持解耦与单测。
- **不一致/缺口**:
  - 下游模块对 `AllocationResult` 字段名使用不一致（见第 2/5 节）。
- **建议**:
  - 锁定数据契约：以 `core/state.py` 为单一事实源，修正 DSROQ 与 SimulationEngine 的字段使用；必要时在 `state.py` 增加兼容字段并标注弃用计划。

---

### 里程碑级修复清单（按优先级）
- P0（立即）
  - 统一 `AdmissionDecision` 判断、`AllocationResult` 字段名、在引擎维护标准化 `positioning_metrics`，打通 DRL 观测链路。
  - 在 DSROQ 代价中注入 `lambda_pos/seam_penalty/path_change_penalty/reroute_cooldown_ms`，最小化实现 Hint 软约束。
- P1（近期）
  - `HypatiaAdapter` real 模式数据通路与校准；稳定性度量从占位过渡到近似实现。
  - 训练/评估批跑与指标落盘（对齐 `docs/06_experiments.md`），前端看板联动。
- P2（随访）
  - Beam Hint 可视化与 DSROQ 联动实验页面；结果导出与统计检验一键化。

---

### 验收建议
- 以 `experiments/scenarios/defaults.yaml` 场景为基线，提供 simplified 模式的端到端跑通脚本（含指标 JSON/CSV 落盘），并验证：
  - DRL 状态维度与键名完全对齐，奖励各项不为零；
  - DSROQ 成功率>0.5、路由寿命/变更率/跨缝占比可计算；
  - 定位 `Apos` 与 CRLB/GDOP 指标随 Beam Hint/参数变化呈合理趋势。

（本报告依据以下文件审阅：`design/system_architecture.md`、`design/algorithm_design.md`、`design/experiment_design.md`、`src/admission/*`、`src/dsroq/*`、`src/hypatia/hypatia_adapter.py`、`src/positioning/*`、`src/simulation/simulation_engine.py`、`src/core/*`）


