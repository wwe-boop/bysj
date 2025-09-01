# 论文主文件（thesis_main）

本论文主题：面向低轨卫星互联网的智能准入与联合调度-协作定位一体化系统（An Integrated DRL Admission and Joint Scheduling System with Cooperative Positioning for LEO Internet）

本主文件汇总各章节内容，导读与编排如下：

- 01_intro.md（绪论）
- 02_related_work.md（相关工作）
- 03_system_design.md（系统总体设计）
- 04_admission_drl.md（DRL准入控制与执行接口合并）
- 05_dsroq_integration.md（协作定位）
- 06_experiments.md（实验设计与结果分析）
- 07_system_impl.md（系统实现与部署）
- 08_ablation.md（消融实验与参数分析）
- 09_conclusion.md（结论与展望）
- 参考公式对齐：参考A/B与本系统记号对齐见 `docs/reference/formula_alignment.md`

[说明] 建议后续将图表与参考文献采用相对路径统一管理，并使用文献库（refs.bib）。

---

## 图表与公式清单索引
- 第1章：研究路线图、贡献对比表；关键术语与定义
- 第3章：分层架构图、数据流/时序图；MDP与目标公式
- 第4章：奖励函数公式、PPO伪代码；训练曲线与特征重要性图；准入-执行联动示意
- 第5章：CRLB/GDOP分布、可用性与协作统计、Beam Hint 图示
- 第6章：指标定义公式、统计检验与对比图；热力图与CDF
- 第7章：API与训练伪代码、性能与资源占用图
- 第8章：消融流程伪代码、敏感性热力图与对比图
- 第9章：贡献总览图、结果回顾雷达图、未来路线图

---

## 引用原则
- 允许在参考列表中以匿名条目或编号方式引用外部研究成果；
- 正文不直接出现具体论文题名与作者姓名，仅总结方法脉络与共性结论；
- 对应贡献/数据应在参考中可追溯（DOI/链接），但避免在正文显式点名；
- 若需对比，使用“近年会议工作/代表性方法”等匿名化表述。
