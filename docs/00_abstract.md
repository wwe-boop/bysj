# 摘要（中文）

本研究面向动态拓扑与资源受限的低轨（LEO）卫星网络，提出一种以用户体验（QoE）为目标的智能准入控制与系统化实现框架。方法层面，上层采用深度强化学习（DRL）作为“守门员”，设计时间感知状态空间与细粒度动作（接受/拒绝/降级/延迟/部分），构建由QoE变化、公平性与网络效率等组成的复合奖励以优化长期收益；下层集成DSROQ，实现对路由、带宽与调度的联合分配与执行。系统层面，构建基于Hypatia的端到端工程平台，并引入融合/协作定位模块：以CRLB/GDOP等定位质量指标为特征，结合波束调度提示（Beam Hint）与可见波束/协作卫星统计，将定位质量约束与网络决策协同，使准入-分配与定位可用性形成闭环优化。我们在多星座规模、负载水平、动态与故障场景下，对比阈值、负载、启发式、传统机器学习及其他DRL方法。结果表明，所提方法在平均QoE、准入率、Jain公平性、网络利用率与定位可用性等指标上取得显著提升，同时保持决策延迟可控；消融与敏感性分析进一步验证了时间信息、奖励设计与定位特征对性能的关键贡献。研究成果具备可复现性与工程落地性，为LEO网络的QoE优化、定位协同与资源一体化管理提供了新思路。

**关键词**：LEO卫星网络；准入控制；深度强化学习；QoE；DSROQ；Hypatia；协作定位；CRLB；GDOP

---

# Abstract (English)

We propose a QoE-driven admission control and system framework for low Earth orbit (LEO) satellite networks featuring dynamic topology and constrained resources. A deep reinforcement learning (DRL) agent serves as a top-layer gatekeeper with a time-aware state space and a fine-grained action set (accept/reject/degrade/delay/partial). A composite reward captures QoE improvement, fairness, and network efficiency for long-term optimization, while the lower layer integrates DSROQ to jointly perform routing, bandwidth allocation, and scheduling. At the system level, we build an end-to-end platform on Hypatia and incorporate a fusion/cooperative positioning module: positioning quality (CRLB/GDOP), beam scheduling hints, and visible beams/cooperative satellites are injected as features and constraints to jointly optimize admission-allocation decisions and positioning availability. Across diverse constellations, loads, dynamics, and failures, our method outperforms threshold-, load-, heuristic-, classical ML-, and other DRL-based baselines in average QoE, admission rate, Jain’s fairness, network utilization, and positioning availability, with controllable decision latency. Ablation and sensitivity analyses confirm the key roles of temporal information, reward design, and positioning features. The framework is reproducible and engineering-ready, offering a unified perspective on QoE optimization, positioning cooperation, and resource management in LEO networks.

**Keywords**: LEO satellite networks; Admission control; Deep reinforcement learning; QoE; DSROQ; Hypatia; Cooperative positioning; CRLB; GDOP
