# 第4章 基于DRL的智能准入控制

## 本章贡献（速览）

- 提出时间感知的DRL准入框架，动作涵盖接受/拒绝/降级/延迟/部分，适配动态拓扑与异构业务。
- 设计QoE驱动的复合奖励并纳入定位可用性项，实现QoE-定位双目标的长期优化。
- 注入切换与路由稳定性特征（预测切换次数/最早切换时间/跨缝标志/接触裕度），抑制高频震荡。
- 与DSROQ的解耦接口：准入产出“集合+画像+约束”，下层据此联合路由/带宽/调度并可独立演进。
## 4.1 马尔可夫决策过程建模

- 状态S：链路利用率统计、EF/AF/BE流量状态、QoE与QoS违规率、轨道相位、拓扑变化率、容量/负载预测、历史趋势、新流请求属性（类型/带宽/时延/位置/时长），以及定位相关特征（CRLB/GDOP、可见波束数、协作卫星数、平均/最小SINR、Beam Hint）。
- 动作A：拒绝、接受、降级接受、延迟接受、部分接受。
- 奖励R：QoE变化为主；公平性奖励与违规惩罚；效率奖励；定位可用性与质量提升奖励；权重与归一化策略。

## 4.2 时间感知状态空间设计

包含当前与短期历史/预测特征，反映动态拓扑与业务演化；采用滑动窗口与轻量预测器提升稳定性与泛化。

## 4.3 细粒度动作空间

- 接受：直接进入下层DSROQ。
- 降级接受：放宽部分QoS或降低带宽；形成退化请求再次评估。
- 延迟接受：排队等待下一个时窗（附带延迟惩罚）。
- 部分接受：按比例下调带宽/速率上限。

## 4.4 QoE驱动奖励函数（公式）

- 定义：\( \Delta\mathrm{QoE}_t = \mathrm{QoE}_{t}^{\text{after}} - \mathrm{QoE}_{t}^{\text{before}} \)
- 公平性（Jain）：\( J(\mathbf{x}) = \frac{\left(\sum_i x_i\right)^2}{n\sum_i x_i^2} \)
- 定位可用性：\( A^{pos}_t \in [0,1] \)（基于可见波束/协作卫星/CRLB阈值综合打分）
- 奖励：
\[ r_t = w_1\,\Delta\mathrm{QoE}_t + w_2\,J(\mathbf{x}_t) + w_3\,\mathrm{Util}_t + w_4\,A^{pos}_t - w_5\,\mathrm{Viol}_t - w_6\,\mathrm{DelayPen}_t \]

## 4.5 PPO算法实现与训练细节（伪代码）

```python
# 伪代码：PPO with HypatiaAdmissionEnv（含定位特征）
obs = env.reset()
while not done:
    action = agent.policy(obs)
    next_obs, reward, done, info = env.step(action)
    # obs 包含: 网络 + QoE + (CRLB, GDOP, visible_beams, coop_sats, beam_hint, SINR)
    buffer.add(obs, action, reward, next_obs, done)
    obs = next_obs
agent.update(buffer)
```

---

## 4.6 DSROQ执行与接口（合并）

- 接口与流程：
  - 准入动作（接受/降级/部分/延迟）→ 触发路由与带宽联合分配 → 李雅普诺夫风格调度执行。
  - 核心接口：`route, bw = route_and_allocate(flow, topology, link_caps)`；`apply_schedule(current_flows)`。
- 代价整合与约束（匿名化对齐参考A/B）：
  - 代价：\( C = C_{net} + \lambda_{pos}\,\Phi(\mathrm{CRLB},\,\mathrm{GDOP},\,\text{visible\_beams},\,\text{coop\_sats}) \)
  - 约束：最小可见波束/协作卫星下限，CRLB阈值过滤；冷却时间限制跨束/跨链路迁移频率以维持定位几何。
- 重分配触发与稳定性：
  - 触发门限与冷却时间避免频繁全局重分配；优先增量调整与缓存复用以降低震荡。
- 输出与评估：
  - 产出路由与带宽方案，统计定位几何保持率、CRLB/GDOP分布变化、\(A^{pos}\) 与 QoE 的联合改进。

## 4.7 状态与奖励字段对照表（新增）

状态向量主要字段与规范：

| 字段 | 含义 | 归一化/范围 | 来源 |
| --- | --- | --- | --- |
| link_util | 链路利用率统计（均值/分位） | [0,1] | 仿真/监控 |
| qoe_stats | QoE历史/趋势特征 | [0,1] 归一化 | 评估模块 |
| traffic_mix | EF/AF/BE占比与速率 | [0,1] | 生成器/监控 |
| crlb | 定位CRLB（位置估计下界） | min-max至[0,1]；单位与阈值见第5章 | Positioning |
| gdop | 几何精度因子GDOP | min-max至[0,1] | Positioning |
| visible_beams | 可见波束数 | 标准化（/上限） | Positioning/Hypatia |
| coop_sats | 协作卫星数 | 标准化（/上限） | Positioning/Hypatia |
| sinr_avg/sinr_min | 平均/最小SINR | dB转线性后归一化 | 物理/链路模型 |
| beam_hint_k | 推荐波束集合大小 | 标准化 | Positioning |
| handover_pred_count | 预测切换次数 | 标准化（/窗口） | 预测器 |
| earliest_handover_s | 最早切换时间 | /窗口长度归一 | 预测器 |
| seam_flag | 是否跨缝路径风险 | {0,1} | 路由/几何推断 |
| contact_margin_s | 接触裕度 | /窗口长度归一 | Hypatia |

奖励权重建议（可调）：

| 项 | 符号 | 默认 | 建议范围 |
| --- | --- | --- | --- |
| QoE增量 | \(w_1\) | 1.0 | [0.5, 2.0] |
| 公平性 | \(w_2\) | 0.2 | [0.0, 0.5] |
| 资源利用 | \(w_3\) | 0.2 | [0.0, 0.5] |
| 定位可用性 | \(w_4\) | 0.3 | [0.0, 1.0] |
| 违规惩罚 | \(w_5\) | 0.8 | [0.5, 2.0] |
| 延迟惩罚 | \(w_6\) | 0.3 | [0.0, 1.0] |

注：权重需与第6章敏感性分析联动报告；字段命名与取值范围在实现中应保持与此处一致性。

---

## 附：图表清单（建议）
- 奖励函数分解图与权重敏感性曲线（含定位权重）
- 定位特征重要性/消融对比图
- 训练曲线（回报、损失、熵、价值函数误差）
- 准入-执行联动时序与代价/约束示意图

---

## 参考公式对齐
详见 `docs/reference/formula_alignment.md`。

---

## 本章小结与局限

- 小结：本章给出了时间感知的DRL准入、复合奖励与定位/切换特征注入，并通过与DSROQ的清晰接口实现解耦协同。
- 局限：
  - 训练样本效率与泛化仍受限于场景多样性；
  - 切换预测与接触计划存在模型误差，需与鲁棒性/不确定性建模结合；
  - 极端拥塞下，细粒度动作的搜索空间增大带来训练不稳定，需策略蒸馏/约束强化。
