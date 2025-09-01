# 第6章 实验设计与结果分析

## 6.1 实验环境搭建

- Hypatia配置：星座、时间步、ISL、路由选项与仿真时长。
- 计算环境：CPU/GPU、并行评估、随机种子管理、日志与追踪。

## 6.2 数据集与参数设置

- 星座与场景：小/中/大规模；静态/慢变/快变；故障类型。
- 流量与QoS：泊松/突发/周期/混合；EF/AF/BE配置；ITU-T参考。
- DRL超参：γ、λ、学习率、batch、n_steps、clip、epochs等。

## 6.3 基线方法对比

阈值/负载/启发式/ML（SVM/RF/NN）/DRL（DQN/A3C/DDPG/PPO）、无准入与“完美准入”参考。

### 6.3.1 独立与协同评测协议（新增）

- 仅准入评测（Admission-only）：采用本文DRL准入，调度固定为安全基线（启发式/静态/最短路+比例带宽）；度量准入带来的纯增益。
- 仅调度评测（Scheduling-only）：采用本文DSROQ/李雅普诺夫调度，准入固定为阈值/负载基线；度量调度带来的纯增益。
- 联合评测（Joint）：本文准入+本文调度协同运行；度量协同增益与上界接近度。
- 报告方式：三组曲线并列展示（QoE/AR/Jain/Util/Delay/Thr/PLR/决策时延/定位可用性），并附显著性检验与置信区间。

## 6.4 性能指标与统计方法

QoE均值/分布、公平性指数、准入/拒绝/降级/延迟率、网络利用率、时延/丢包/吞吐、计算复杂度与决策时延；置信区间与显著性检验。

切换与路由稳定性指标（新增）：
- 切换率/每用户：单位时间发生的切换次数；ping-pong率：短时间内往返切换占比；切换中断时长CDF。
- 路由变更率/流：单位时间的路径更新次数；平均路由寿命；重路由冷却违规率；跨缝路径占比。
- 资源预留失败率：MBB预留失败导致的中断事件占比。

指标JSON结构建议（无额外脚本）：
```json
{
  "MethodA": {
    "qoe": {"mean": 0.85, "ci95": 0.02},
    "handover": {"rate": 0.6, "pingpong": 3.1, "outage_ms": 12.4},
    "routing": {"change_rate": 0.15, "avg_lifetime": 35.2, "seam_ratio": 8.7}
  },
  "MethodB": { }
}
```
上表结构即可直接被任意可视化工具读取（如Jupyter或现有`qoe_metrics_plot.py`），无需新增脚本。

### 6.4.1 指标JSON最小样例与脚本对齐（新增）

最小可运行样例（可直接供 `qoe_metrics_plot.py` 与 `admission_rates_plot.py` 使用）：
```json
{
  "MethodA": {
    "qoe": {"mean": 0.86, "ci95": 0.02},
    "admission": {"accept": 0.72, "reject": 0.18, "degrade": 0.06, "delay": 0.04},
    "fairness": {"jain": 0.91},
    "util": 0.78,
    "delay_ms": 42.5,
    "thr_mbps": 125.3,
    "plr": 0.012,
    "handover": {"rate": 0.58, "pingpong": 3.0, "outage_ms": 11.8},
    "routing": {"change_rate": 0.14, "avg_lifetime": 36.0, "seam_ratio": 8.1}
  },
  "MethodB": {
    "qoe": {"mean": 0.81, "ci95": 0.03},
    "admission": {"accept": 0.65, "reject": 0.22, "degrade": 0.09, "delay": 0.04},
    "fairness": {"jain": 0.87},
    "util": 0.74,
    "delay_ms": 48.2,
    "thr_mbps": 118.9,
    "plr": 0.016,
    "handover": {"rate": 0.62, "pingpong": 3.6, "outage_ms": 13.1},
    "routing": {"change_rate": 0.18, "avg_lifetime": 31.5, "seam_ratio": 9.4}
  }
}
```

脚本字段对齐（文档级约定）：
- `scripts/plots/qoe_metrics_plot.py`：读取 `qoe.mean`（必需），可选读取 `delay_ms/thr_mbps/plr/handover/routing` 衍生曲线。
- `scripts/plots/admission_rates_plot.py`：读取 `admission.{accept,reject,degrade,delay}` 四项作为条形图。
- `scripts/plots/fairness_heatmap.py`：单独读取敏感性矩阵文件（示例结构如下）。

敏感性热力图示例文件 `experiments/results/sensitivity_matrix.json`：
```json
{
  "x_labels": ["w_pos=0.0", "0.1", "0.2", "0.3"],
  "y_labels": ["seam=0.0", "0.3", "0.5", "0.7"],
  "matrix": [
    [0.80, 0.82, 0.85, 0.83],
    [0.81, 0.84, 0.86, 0.84],
    [0.79, 0.83, 0.86, 0.85],
    [0.78, 0.82, 0.85, 0.84]
  ],
  "metric": "qoe.mean"
}
```

新增定位相关指标：
- 定位可用性 \( A^{pos} \in [0,1] \)：由可见波束/协作卫星/CRLB阈值综合打分；
- 定位质量：CRLB分布（均值/p95）、GDOP分布；
- 协作度：每用户平均协作卫星数、平均可见波束数。

## 6.5 多场景评估结果

- 规模/负载/动态性/故障/QoS分布的组合场景实验与结果分析。
- 稳定性与鲁棒性：对参数扰动与故障的敏感性评估。
- 切换与seam场景：极区/跨缝高频切换；ISL开闭窗周期；网关拥塞与回传受限；对比不同Δτ与 \( \kappa_{seam},\kappa_{chg} \) 的影响。

## 6.6 消融与敏感性

- 状态/动作/奖励/结构/训练策略消融。
- 超参数敏感性（曲线/热力图）。
- 定位特征消融：去掉（CRLB/GDOP/协作统计/Beam Hint）对子指标与联合指标的影响。

## 6.7 本章小结

总结在多维度指标与场景下的优势、局限与可推广性。

### 6.4.2 噪声/融合敏感性与稳定性评测（新增）

- 噪声协方差敏感性：设置不同 `R` 水平与结构（各测量 TOA/TDOA/AOA 的方差/相关性），观察 CRLB/GDOP 分布及 `Apos` 变化；联动 `qoe.mean`/`admission` 指标。
- 融合加权敏感性：对 \(w_{TOA}, w_{TDOA}, w_{AOA}\) 在 simplex 上栅格/贝叶斯优化，比较定位/业务联合指标。
- NLOS/同步误差鲁棒性：以场景开关/注入偏差的方式，评估定位质量退化下的策略联动效果（触发保守/延迟/降级）。
- 调度稳定性：报告路由寿命、重路由冷却违规率、跨缝占比随 `seam_penalty`、`reroute_cooldown_ms`、`lambda_pos` 的联动曲线/热力图。
- 复杂度与时延：记录策略推理时延、MCTS 搜索时间、指标计算时间，绘制性能—复杂度折衷曲线。

输出建议：
```json
{
  "Noise_R_sweep": {
    "qoe": {"mean": 0.84},
    "positioning": {"crlb_mean": 42.1, "gdop_mean": 1.9, "Apos": 0.73}
  },
  "Fusion_weight_grid": {
    "metric": "qoe.mean",
    "grid": [[0.82,0.84],[0.85,0.86]]
  },
  "Stability_curves": {
    "avg_lifetime": [35.2, 38.1, 41.0],
    "change_rate": [0.18, 0.15, 0.12]
  }
}
```

---

## 附：指标定义（公式）
- 平均QoE：\( \overline{Q} = \frac{\sum_k w_k Q_k}{\sum_k w_k} \)
- 准入率：\( \mathrm{AR} = \frac{N_{accept}}{N_{requests}} \)，拒绝率：\( \mathrm{RR} = 1-\mathrm{AR} \)
- 降级/延迟率：同理定义为相应动作发生次数占比
- QoS违规率：\( \mathrm{Viol} = \frac{\sum_f \mathbb{1}[\text{QoS}_f\,\text{违反}]}{N_{active}} \)
- Jain公平性：\( J(\mathbf{x}) = \frac{(\sum_i x_i)^2}{n\sum_i x_i^2} \)
- 吞吐量：\( \mathrm{Thr} = \frac{\sum \text{bits delivered}}{\Delta t} \)
- 平均时延：\( \overline{T} = \frac{1}{N}\sum_i T_i \)；丢包率：\( \mathrm{PLR} = \frac{N_{lost}}{N_{sent}} \)
- 网络利用率：\( \mathrm{Util} = \frac{\text{used capacity}}{\text{total capacity}} \)
- 定位可用性：\( A^{pos} = f(\text{visible beams},\, \text{coop sats},\, \mathbb{1}[\mathrm{CRLB}\le\tau]) \)

## 附：统计方法
- 95%置信区间：\( \bar{x} \pm t_{\alpha/2,\nu} \cdot \frac{s}{\sqrt{n}} \)
- 两独立样本t检验：\( t = \frac{\bar{x}_1-\bar{x}_2}{\sqrt{s_1^2/n_1 + s_2^2/n_2}} \)
- 多组比较：ANOVA/非参检验；必要时Holm–Bonferroni校正

## 附：图表清单（建议）
- 综合对比：QoE/AR/Jain/Util/Delay/PLR/Thr
- 定位相关：CRLB/GDOP分布、可用性雷达图、协作统计柱状图
- CDF/箱线图：QoE分布、时延分布、CRLB分布
- 热力图：状态特征重要性、敏感性曲面
- 雷达图：多指标综合表现

---

## 6.8 端到端演示流程（含可视化联动）

1) 启动后端API（默认端口5000）：
```bash
python src/api/main.py
```

2) 运行仿真/训练或回放（示例）：
```bash
# 训练（示意）
python src/admission/train.py --config experiments/configs/drl_params.yaml
# 或回放/评测脚本
python experiments/run_baselines.py
```

示例：通过模式参数启动（容错/降级演示）
```bash
curl -X POST "http://127.0.0.1:5000/api/simulation/start" \
     -H "Content-Type: application/json" \
     -d '{"admission_mode":"drl","scheduler_mode":"dsroq"}'
```

3) 前端/可视化联动（示例调用）：
```bash
# 获取定位指标（GET：轻量查询，使用 query 参数）
curl "http://127.0.0.1:5000/api/positioning/metrics?time=0&users=[]"

# 获取定位指标（POST：复杂查询，使用 JSON 请求体）
curl -X POST "http://127.0.0.1:5000/api/positioning/metrics" \
     -H "Content-Type: application/json" \
     -d '{
           "time": 0,
           "users": [
             {"id": "u1", "lat": 39.9, "lon": 116.4},
             {"id": "u2", "lat": 31.2, "lon": 121.5}
           ]
         }'
# 获取波束调度提示
curl -X POST "http://127.0.0.1:5000/api/positioning/beam_hint" \
     -H "Content-Type: application/json" \
     -d '{"time":0, "users":[], "budget":{}}'
```

说明：`/api/positioning/metrics` 同时支持 GET 与 POST。GET 适合简单/少量用户的快速查询；当需要传递较复杂的用户列表或附加参数时，建议使用 POST 并以 JSON 体提交，与 `docs/03_system_design.md` 的接口契约字段保持一致。

4) 生成图表（示例数据见 experiments/results/）：
```bash
# QoE 对比
python scripts/plots/qoe_metrics_plot.py \
  --input experiments/results/positioning_ablation_example.json \
  --output docs/assets/ablation_qoe_positioning.png

# 准入/拒绝/降级 速率对比
python scripts/plots/admission_rates_plot.py \
  --input experiments/results/positioning_ablation_example.json \
  --output docs/assets/ablation_rates_positioning.png

# 敏感性热力图
python scripts/plots/fairness_heatmap.py \
  --input experiments/results/sensitivity_matrix.json \
  --output docs/assets/ablation_sensitivity_positioning.png
```

5) 生成论文PDF（Pandoc + XeLaTeX）：
```bash
bash docs/latex/build.sh
# 输出：docs/latex/thesis.pdf
```
