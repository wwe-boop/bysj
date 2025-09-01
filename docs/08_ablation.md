# 第8章 消融实验与参数分析

## 8.1 状态空间消融

移除时间/历史/预测要素对性能的影响，分析关键特征的重要性。

## 8.2 动作空间消融

从二元（接收/拒绝）到细粒度动作的增量效果评估。

## 8.3 奖励函数消融

仅ΔQoE、加入公平性、加入效率、加入违规惩罚的组合对比与权重敏感性。

## 8.4 超参数敏感性

学习率、折扣、clip、n_steps、batch、epochs等的敏感性曲线与热力图。

## 8.5 本章小结

总结各组件与超参对整体性能与稳定性的贡献与影响。

---

## 附：消融实验流程（伪代码）

```python
def run_ablation(configs):
    results = {}
    for name, cfg in configs.items():
        env = make_env(cfg.env)
        agent = make_agent(cfg.agent)
        res = evaluate(agent, env, seeds=cfg.seeds)
        results[name] = aggregate(res)
    return compare(results)
```

## 附：图表清单（建议）
- 组件消融柱状/折线对比图
- 权重/超参数敏感性热力图与曲线
- 稳定性（方差/置信区间）对比图
- 定位特征消融：
  - CRLB/GDOP移除/加入对 QoE/AR/定位可用性的影响
  - 可见波束/协作卫星移除/加入的影响
  - Beam Hint 移除/加入对定位与网络双目标的影响

---

## 附：图表生成命令示例（定位消融）

```bash
# QoE对比（含95%CI）
python scripts/plots/qoe_metrics_plot.py \
  --input experiments/results/positioning_ablation_example.json \
  --output docs/assets/ablation_qoe_positioning.png

# 定位可用性/准入率/降级率对比
python scripts/plots/admission_rates_plot.py \
  --input experiments/results/positioning_ablation_example.json \
  --output docs/assets/ablation_rates_positioning.png

# 敏感性热力图（示例：自备矩阵JSON）
python scripts/plots/fairness_heatmap.py \
  --input experiments/results/sensitivity_matrix.json \
  --output docs/assets/ablation_sensitivity_positioning.png
```
