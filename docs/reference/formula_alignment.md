# 参考公式与本系统记号对齐（匿名化）

本文件对齐两类参考：
- 参考A（联合路由/带宽/调度框架） → 对应 reference/2508.21047v1.pdf
- 参考B（协作定位/多波束调度） → 对应 reference/2404.01148v1.pdf

正文保持匿名化，只在此处标注参考A/B。

---

## 1. 通用与本稿自定义
- MDP与折扣回报、Jain指数：采用通用定义（教材级），不依赖参考A/B特定推导。
- 本稿奖励组合：
  \[ r_t = w_1\,\Delta\mathrm{QoE}_t + w_2\,J(\mathbf{x}_t) + w_3\,\mathrm{Util}_t + w_4\,A^{pos}_t 
     - w_5\,\mathrm{Viol}_t - w_6\,\mathrm{DelayPen}_t \]
- 定位可用性（组合指标）：\( A^{pos} = f(\text{visible beams},\, \text{coop sats},\, \mathbb{1}[\mathrm{CRLB}\le\tau]) \)

## 2. 参考A（DSROQ思想）对齐
- 李雅普诺夫漂移-惩罚：\( \Delta(\mathbf{Q}) + V\,\mathbb{E}\{\text{Penalty}\} \) 的思想用于下层调度稳定与代价权衡；本稿以统一记号表达。
- 搜索/近似最优的路由与资源分配：本稿以MCTS实现对齐。
- 本稿扩展：将定位成本整合进搜索代价 \( C = C_{net} + \lambda_{pos}\,\Phi(\cdot) \)，并以阈值过滤不可行解。

## 3. 参考B（协作定位）对齐
- 定位质量度量：CRLB/GDOP作为定位质量与几何指标；不复述推导，仅作为指标来源。
- 多波束协作：以 Beam Hint/协作集的形式影响路由/带宽/调度偏好与可行域。
- 本稿扩展：在状态与奖励中引入定位可用性与特征，形成策略—资源—定位闭环。

## 4. 章节映射
- 第3章（系统设计）：定位特征注入与接口；与参考A/B的融合位置。
- 第4章（DRL准入）：参考B的指标→状态/奖励；参考A的联合优化思想→策略层约束。
- 第5章（DSROQ执行）：参考A的执行框架＋参考B的Beam Hint/阈值→代价与可行域。
- 第7章（系统实现）：API与可视化，承接对齐后的接口与数据流。

## 5. 记号速查
- \( \Delta\mathrm{QoE}_t\)：QoE增量；\(J(\cdot)\)：Jain公平性；\(\mathrm{Util}\)：网络利用率；\(\mathrm{Viol}\)：违规率；\(A^{pos}\)：定位可用性。
- 定位特征：CRLB、GDOP、visible beams、coop sats、beam hint、SINR。
- 约束阈值：\(\tau\)（CRLB）、\(b_{min}\)（可见波束）、\(s_{min}\)（协作卫星）。
