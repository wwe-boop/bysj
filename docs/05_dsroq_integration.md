# 第5章 协作定位（匿名化参考B）

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

## 参考公式对齐
详见 `docs/reference/formula_alignment.md`（参考B）。
