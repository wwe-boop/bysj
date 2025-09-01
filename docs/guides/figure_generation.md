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
- 中文渲染：需配置本地字体或改用英文字体；图片内尽量使用英文标签。
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
