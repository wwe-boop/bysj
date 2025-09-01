# 第4章 基于DRL的智能准入控制

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

---

## 附：图表清单（建议）
- 奖励函数分解图与权重敏感性曲线（含定位权重）
- 定位特征重要性/消融对比图
- 训练曲线（回报、损失、熵、价值函数误差）
- 准入-执行联动时序与代价/约束示意图

---

## 参考公式对齐
详见 `docs/reference/formula_alignment.md`。
