# 第5章 协作定位（匿名化参考B）

## 本章贡献（速览）

- 将协作定位质量（CRLB/GDOP）与可用性指标系统性注入策略层与执行层，形成网络-定位协同的通用接口。
- 提出基于定位与可见性特征的Beam Hint与可行域约束，支撑准入与DSROQ代价的统一建模与优化。
- 给出可复现实验设计：Apos/CRLB/GDOP与网络指标联合报告、消融与敏感性分析全链条。
## 5.1 概述与目标

- 目标：在LEO多波束/多卫星协作环境中提升定位质量与可用性（以CRLB/GDOP为核心指标），同时与网络准入-分配联动，形成系统级协同。
- 思路：以协作定位特征与提示（Beam Hint/协作集、可见波束/协作卫星统计）驱动上层策略与下层执行，贯穿状态、奖励、代价与约束。

## 5.2 指标与度量（参考B）

- 定位界限：CRLB（均值/p95）、GDOP（均值/p95）。
- 可用性：\(A^{pos}\in[0,1]\)，由（可见波束、协作卫星、CRLB阈值）综合打分获得。
- 协作度：每用户平均可见波束数、协作卫星数；协作集大小分布。

## 5.3 协作提示与波束调度（匿名化）

- Beam Hint：基于可见性/相关性与功率/干扰约束生成的“推荐波束/卫星集合”。
- 外层调度建议：优先调度相关性较低的用户/波束组合以抑制干扰，形成更优几何。

## 5.4 与策略层（第4章）的融合

- 状态注入：在 \(s_t\) 中引入（CRLB、GDOP、visible beams、coop sats、SINR、Beam Hint）。
- 奖励扩展：加入 \(A^{pos}_t\) 项，兼顾QoE与定位双目标。

## 5.5 与执行层（第4章-DSROQ合并节）的融合

- 代价整合：\( C = C_{net} + \lambda_{pos}\,\Phi(\mathrm{CRLB},\mathrm{GDOP},\text{visible\_beams},\text{coop\_sats}) \)。
- 可行域约束：CRLB阈值、最小可见波束/协作卫星、迁移冷却时间以维持定位几何。

## 5.6 实验设计要点

- 指标：CRLB/GDOP分布、\(A^{pos}\)、协作集统计，与 QoE/AR/Util 等网络指标联合呈现。
- 消融：移除（CRLB/GDOP/协作统计/Beam Hint）观察对定位与网络双目标的影响。
- 敏感性：对 \(\lambda_{pos}\) 与阈值（\(\tau, b_{min}, s_{min}\)）做曲线/热力图分析。

## 5.7 图表建议

- CRLB/GDOP分布图（均值/p95、CDF/箱线图）。
- 可用性雷达图与协作柱状图（visible beams/coop sats）。
- Beam Hint 可视化叠加（Cesium层）。

---

## 5.8 匿名化公式片段（通用形态）

- 观测模型（抽象）：\( \mathbf{y} = \mathbf{h}(\mathbf{x}) + \mathbf{n} \)，其中 \(\mathbf{n}\sim \mathcal{N}(\mathbf{0},\mathbf{R})\)。
- Fisher信息矩阵（线性化近似）：\( \mathbf{J}(\mathbf{x}) = \mathbf{H}^\top \mathbf{R}^{-1} \mathbf{H} \)，\(\mathbf{H} = \partial \mathbf{h} / \partial \mathbf{x} \)。
- CRLB（位置估计下界）：\( \mathrm{Cov}(\hat{\mathbf{x}}) \succeq \mathbf{J}^{-1} \)，可报告 \(\operatorname{tr}(\mathbf{J}^{-1})\)、主对角线或其分位数（如p95）。
- GDOP（几何精度因子，归一化）：\( \mathrm{GDOP} = \sqrt{\operatorname{tr}\left((\mathbf{H}^\top \mathbf{H})^{-1}\right)} \)（在等噪声、等功率假设下的常用度量）。
- 可用性（本稿定义）：\( A^{pos} = f\big(\text{visible beams},\, \text{coop sats},\, \mathbb{1}[\operatorname{tr}(\mathbf{J}^{-1}) \le \tau]\big) \in [0,1] \)。

> 说明：以上为通用形式，仅用于与系统设计对齐；不涉及具体论文题名/作者，详细对齐见 `docs/reference/formula_alignment.md`。

---

## 5.9 TEG与代价注入配置示例（新增）

如下为面向路由/调度的配置示例（文档级）：

```json
{
  "routing": {
    "time_step_s": 1,
    "seam_penalty": 0.5,
    "path_change_penalty": 0.2,
    "reroute_cooldown_ms": 5000
  },
  "positioning": {
    "lambda_pos": 0.2,
    "crlb_threshold": 50,
    "min_visible_beams": 2,
    "min_coop_sats": 2
  },
  "scheduling": {
    "lyapunov_weight": 1.0,
    "queue_backlog_limit": 10000
  }
}
```

字段命名一致性：示例中的键名需与第3.2.3“constraints”字段保持一致：`lambda_pos, crlb_threshold, min_visible_beams, min_coop_sats, seam_penalty, reroute_cooldown_ms`。如使用 `path_change_penalty/lyapunov_weight/queue_backlog_limit`，需在接口契约与系统综述（Summary）中同步出现。

输出-指标对齐建议：
- 路由寿命（avg_lifetime）、跨缝占比（seam_ratio）、路径变更率（change_rate）。
- 定位可用性 \(A^{pos}\)、CRLB/GDOP统计、可见波束/协作卫星均值。
- 队列稳定性/丢包/时延与吞吐，并与 \(\lambda_{pos}\)、`seam_penalty`、`reroute_cooldown_ms` 做敏感性联动。

---

## 5.10 与参考工作的差异与补充（新增）

- 工程化代价整合：在路由/调度层显式引入 `\lambda_{pos}\,\Phi(CRLB,GDOP,visible\_beams,coop\_sats)`，以统一方式权衡网络与定位目标；参考类调度论文多未将定位几何直接纳入代价。
- 搜索策略差异：采用 MCTS 进行路由近似最优搜索，替代常见的凸优化/后压（backpressure）或纯启发式路径选择。
- 可行域与稳定性约束：引入 `seam_penalty`、`path_change_penalty`、`reroute_cooldown_ms` 等工程稳定性约束，以提升路径寿命并抑制高频重路由。
- 指标扩展：定义组合指标 `Apos\in[0,1]` 并贯穿状态/奖励/代价；该指标为工程抽象，非通行的定位学术指标。
- 未覆盖/后续工作：
  - 理论层稳定性与性能保证：未给出基于 Foster–Lyapunov 的稳定域或近最优界证明；后续将补充虚拟队列/约束队列构造与证明套路。
  - 测量噪声与融合细化：当前以通用 FIM 近似表述，未展开 EKF/UKF/粒子滤波等估计器细节与 NLOS/同步误差模型；后续在实验与实现中补齐。
  - 与 backpressure 的系统对比：复杂度—性能权衡与可扩展性评估将作为扩展实验提供。

> 注：本节旨在与常见参考范式对齐并明确工程化扩展边界，详细公式对齐见“参考公式对齐”。

---

## 参考公式对齐
详见 `docs/reference/formula_alignment.md`（参考B）。

---

## 本章小结与局限

- 小结：本章建立了定位-网络协同的指标、接口与实验范式，为准入与调度的联合优化提供一致的特征与约束。
- 局限：
  - Beam Hint与协作集构造依赖可见性与相关性建模，极端遮挡/干扰下可能偏差；
  - 指标权重与阈值需场景化标定，跨场景迁移性有限；
  - 与物理层联动（波束成形/功控）的闭环尚未在本稿覆盖。
