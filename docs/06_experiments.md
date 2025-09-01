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

## 6.4 性能指标与统计方法

QoE均值/分布、公平性指数、准入/拒绝/降级/延迟率、网络利用率、时延/丢包/吞吐、计算复杂度与决策时延；置信区间与显著性检验。

新增定位相关指标：
- 定位可用性 \( A^{pos} \in [0,1] \)：由可见波束/协作卫星/CRLB阈值综合打分；
- 定位质量：CRLB分布（均值/p95）、GDOP分布；
- 协作度：每用户平均协作卫星数、平均可见波束数。

## 6.5 多场景评估结果

- 规模/负载/动态性/故障/QoS分布的组合场景实验与结果分析。
- 稳定性与鲁棒性：对参数扰动与故障的敏感性评估。

## 6.6 消融与敏感性

- 状态/动作/奖励/结构/训练策略消融。
- 超参数敏感性（曲线/热力图）。
- 定位特征消融：去掉（CRLB/GDOP/协作统计/Beam Hint）对子指标与联合指标的影响。

## 6.7 本章小结

总结在多维度指标与场景下的优势、局限与可推广性。

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

3) 前端/可视化联动（示例调用）：
```bash
# 获取定位指标
curl "http://127.0.0.1:5000/api/positioning/metrics?time=0&users=[]"
# 获取波束调度提示
curl -X POST "http://127.0.0.1:5000/api/positioning/beam_hint" \
     -H "Content-Type: application/json" \
     -d '{"time":0, "users":[], "budget":{}}'
```

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
