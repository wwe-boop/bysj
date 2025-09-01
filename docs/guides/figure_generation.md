# 图表生成指南（本地可复现）

本文档说明如何从实验结果生成论文所需图表。所有脚本位于 `scripts/plots/`，输出默认写入 `docs/assets/`。

## 1. 前置依赖

```bash
pip install matplotlib numpy
```

## 2. 结果文件格式

- QoE与率类对比：期望为JSON，示例：
```json
{
  "PPO": {"qoe": {"mean": 4.12, "ci95": 0.08}},
  "Threshold": {"qoe": {"mean": 3.61, "ci95": 0.10}},
  "LoadBased": {"qoe": {"mean": 3.89, "ci95": 0.07}}
}
```
- 准入/拒绝/降级率：
```json
{
  "PPO": {"admission_rate": 0.76, "rejection_rate": 0.18, "degradation_rate": 0.06},
  "Threshold": {"admission_rate": 0.62, "rejection_rate": 0.31, "degradation_rate": 0.07}
}
```
- 热力图矩阵：
```json
{ "labels": ["w_qoe","w_fair","w_eff"],
  "matrix": [[0.81,0.75,0.70],
              [0.78,0.80,0.73],
              [0.74,0.76,0.79]] }
```

## 3. 生成命令

- QoE对比图：
```bash
python scripts/plots/qoe_metrics_plot.py \
  --input experiments/results/qoe_summary.json \
  --output docs/assets/qoe_comparison.png
```

- 准入/拒绝/降级率图：
```bash
python scripts/plots/admission_rates_plot.py \
  --input experiments/results/admission_rates.json \
  --output docs/assets/admission_rates.png
```

- 公平性/敏感性热力图：
```bash
python scripts/plots/fairness_heatmap.py \
  --input experiments/results/sensitivity_matrix.json \
  --output docs/assets/sensitivity_heatmap.png
```

## 4. 章节内引用示例

在对应MD章节中引用图片（相对路径）：

```markdown
![](../assets/qoe_comparison.png)
```

## 5. 常见问题

- 字体过小：可修改脚本内 `figsize` 或在保存前设置 `plt.rcParams['font.size'] = 12`。
- 中文渲染：请选择支持中文的字体（如 Noto Sans CJK/思源黑体/苹方），确保图片内全部为中文标签。
- CI计算：脚本读取结果文件内的 `ci95` 字段，不进行统计计算；请在聚合脚本中预先写入。

---

## 6. 定位特征消融示例

- 样例文件：`experiments/results/positioning_ablation_example.json`
- 生成命令：
```bash
python scripts/plots/qoe_metrics_plot.py \
  --input experiments/results/positioning_ablation_example.json \
  --output docs/assets/ablation_qoe_positioning.png

python scripts/plots/admission_rates_plot.py \
  --input experiments/results/positioning_ablation_example.json \
  --output docs/assets/ablation_rates_positioning.png
```

## 7. 非数据型图片清单（AI 生成提示词）

统一风格约定（适用于所有提示词）：
- 白底、极简扁平矢量风，蓝色/青色为主色，细线条、轻阴影
- 中文标签（如 QoE、准入、DSROQ、定位），不放真实数据/数值坐标
- 输出尺寸 2400×1350（16:9），PNG 或 SVG，干净留白与统一字体风格

- intro_tech_roadmap（docs/assets/intro_tech_roadmap.png）：
```
白底极简扁平矢量信息图，蓝/青配色。
标题：「技术路线图」。从左到右：问题 → 方法 → 系统 → 实验 → 结论。
问题：「LEO 动态与 QoE 挑战」；方法：「DRL 准入（守门员） + DSROQ 执行」；
系统：「基于 Hypatia 的平台 + 定位模块」；实验：「QoE、准入率、公平性、利用率」；
结论：「QoE 提升、定位可用性提升」。使用简单图标与细线，全部中文标签，无真实数据。
```

- intro_motivation_problem（docs/assets/intro_motivation_problem.png）：
```
白底概念示意图。左侧：「挑战」— 动态拓扑、资源受限、QoE 下降；
中间云朵：「研究空白：缺少面向 QoE 的准入」；右侧：「我们的思路」— DRL 准入 + DSROQ、面向定位协同、面向长期 QoE。
蓝/青配色，中文标签，细分隔线，无数字。
```

- intro_contributions_matrix（docs/assets/intro_contributions_matrix.png）：
```
干净的矩阵信息图。列：目标、方法、系统、实验。行：传统方法、机器学习、既有 DRL、本文工作。
用中性对勾/圆点表示（不含分数），突出「本文工作」行但不过度强调。中文标签。
```

- related_work_taxonomy（docs/assets/related_work_taxonomy.png）：
```
白底分类树。根节点：「LEO 网络资源管理」。
分支：「路由」「带宽分配」「调度」「准入控制」（叶子：阈值、负载感知、启发式、机器学习、DRL）。
独立分支：「协作定位」包含 CRLB/GDOP、波束调度。中文标签、细线条。
```

- related_method_comparison（docs/assets/related_method_comparison.png）：
```
极简对比矩阵。列：自适应性、QoE 感知、可扩展性、拓扑动态性。
行：阈值、负载感知、启发式、机器学习、DRL。中性对勾/圆点，中文标签，白底。
```

- system_overall_architecture（docs/assets/system_overall_architecture.png）：
```
白底分层架构图。上层：「DRL 准入（守门员）」；下层：「DSROQ（路由/带宽/调度）」。
左侧输入：「新流到达」→「状态提取」。箭头：接受/降级/延迟/部分 → DSROQ；拒绝 → 丢弃/排队。
右侧：「执行与监控」→「QoE 与 KPI」→「策略更新」。
标注：「定位特征：CRLB、GDOP、可见波束、协作卫星、SINR、Beam Hint」。全部中文标签。
```

- system_sequence_flow（docs/assets/system_sequence_flow.png）：
```
横向时序流程图，泳道：客户端、API、DRL 准入、DSROQ、Hypatia、监控。
步骤：请求 → 状态 → 决策 → 路由/带宽 → 执行 → 指标 → 更新。编号箭头，简洁图标，中文标签，无数据。
```

- system_sar_design（docs/assets/system_sar_design.png）：
```
三栏概念图：状态、动作、奖励。
状态标签：利用率、QoE、EF/AF/BE、动态性、预测、CRLB、GDOP、可见波束、协作卫星、SINR、Beam Hint。
动作：接受、拒绝、降级、延迟、部分。奖励框：
「ΔQoE + 公平性 + 效率 + 定位可用性 − 违规 − 延迟惩罚」（文本展示）。
```

- system_positioning_injection（docs/assets/system_positioning_injection.png）：
```
概念流程：「Hypatia → 定位模块」产出特征（CRLB、GDOP、可见波束、协作卫星、SINR、Beam Hint）
→「状态提取器」→「DRL 准入」与「评估（A_pos）」。虚线表示对 DSROQ 的约束。白底，蓝/青配色。
```

- drl_reward_decomposition（docs/assets/drl_reward_decomposition.png）：
```
概念甜甜圈或堆叠块，标注：ΔQoE、公平性、效率、A_pos、违规、延迟惩罚。
图例展示权重 w1..w6（不写具体数值）。中文标签，极简风格，无曲线、无数据。
```

- drl_to_dsroq_coupling（docs/assets/drl_to_dsroq_coupling.png）：
```
「DRL 准入」与「DSROQ」的联动流程图，带叠加标注：
「代价 C = C_net + λ_pos Φ(CRLB, GDOP, 可见波束, 协作卫星)」与「约束：阈值、冷却时间」。
中文标签，白底。
```

- positioning_concept（docs/assets/positioning_concept.png）：
```
极简概念图：地面用户与多颗 LEO 卫星/波束。
标注：可见波束、协作卫星、几何（GDOP）、CRLB（越小越好）。
无数字，中文标签，细线条，蓝/青配色。
```

- beam_hint_overlay（docs/assets/beam_hint_overlay.png）：
```
抽象地图底图，简化的地球局部与波束覆盖（六边形/圆形）。
用青色高亮推荐波束（Beam Hint），其他用浅灰；图例：推荐、候选。中文标签。
```

- positioning_availability_score（docs/assets/positioning_availability_score.png）：
```
「A_pos 可用性评分」方块图：输入「可见波束」「协作卫星」「CRLB ≤ τ」→「评分」→「A_pos ∈ [0,1]」。
中文标签，白底。
```

- impl_components_callgraph（docs/assets/impl_components_callgraph.png）：
```
组件图：API（Flask）、环境/Hypatia 适配器、DRL 智能体（PPO）、DSROQ 接口、定位模块、监控/日志、存储。
箭头体现主要调用：请求处理、状态提取、决策、执行、指标。中文标签，白底。
```

- impl_api_sequence（docs/assets/impl_api_sequence.png）：
```
两个迷你时序图：
（1）/api/admission/decision；（2）/api/positioning/{metrics, beam_hint}。
生命线：客户端 → API → 模块 → 响应。编号步骤，中文标签，极简风格。
```

- impl_deployment_topology（docs/assets/impl_deployment_topology.png）：
```
部署拓扑：前端（Vue）↔ 后端 API（Flask）↔ 核心（DRL、DSROQ、Hypatia 适配器）。
侧边：Prometheus/Grafana、MLflow、存储。将服务置于「Docker/K8s」集群框内。仅中文标签。
```

- impl_frontend_dashboard_mock（docs/assets/impl_frontend_dashboard_mock.png）：
```
干净的 UI 线框图（无真实数据）：左侧为 Cesium 地球区，右侧为指标卡片（QoE、准入、定位）。
简单图表占位（柱/折线无数值）。中文标签，扁平风格，白底。
```

- hypatia_integration（docs/assets/hypatia_integration.png）：
```
集成示意：「Hypatia 仿真器」连接到「适配器」，暴露 API：
get_topology_at_time(t)、get_link_utilization()、add_flow_to_network()。上游：数据（星座、流量）。下游：DRL/DSROQ 系统。
中文标签，极简，白底。
```
