# 面向低轨卫星互联网的智能准入与联合调度-协作定位一体化系统（硕士毕业论文）

## 项目概述

本项目面向"融合定位 + 智能调度"一体化目标，基于DSROQ与Hypatia框架进行扩展创新：
- 在资源受限、动态拓扑的LEO网络中，构建"准入-分配-定位协同"的分层决策系统
- 引入融合定位（参考 reference/2404.01148v1.pdf）作为核心模块，与调度/准入共同驱动全局优化
- 以QoE与定位精度（CRLB/GDOP等）为联合目标，进行实时、长期的联合优化

## 核心创新点

1. 融合定位 × 智能调度：提出"定位质量 × QoE"的联合优化范式
2. DRL实时准入控制：细粒度动作（接受/拒绝/降级/延迟/部分）+ 时间感知状态
3. 准入-分配-定位协同：分层架构将准入、路由/带宽、定位指标联动优化
4. Hypatia高保真仿真：嵌入定位指标计算（CRLB/GDOP），实现端到端评估
5. 多目标奖励：QoE + 定位精度 + 公平性 + 网络效率 + 稳定性
6. 工程化交付：可视化、可复现、可扩展，面向硕士毕业论文答辩

## 技术架构

```
DRL准入控制层 (我们的创新)
     ↓ 决策接口
Hypatia satgenpy层 (网络状态生成)
     ↓ 路由接口  
DSROQ资源分配层 (MCTS + 李雅普诺夫)
     ↓ 执行接口
Hypatia ns3-sat-sim层 (包级仿真)
```

## 目录结构

```
bysj/
├── docs/                     # 论文文档
├── design/                   # 系统设计文档
├── src/                      # 系统核心代码
├── experiments/              # 实验配置与结果
├── data/                     # 数据管理
├── reference/                # 文献管理
├── deploy/                   # 部署配置
├── web/                      # Web界面
└── tests/                    # 测试代码
```

## 快速开始

### 环境要求
- Python 3.7+
- Ubuntu 18+ (推荐)
- CUDA 11.0+ (可选，用于GPU加速)

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/wwe-boop/bysj.git
cd bysj
```

2. 安装项目依赖
```bash
pip install -r requirements.txt
```

3. 运行测试
```bash
python -m pytest tests/
```

### 运行示例

```bash
# 启动DRL训练
python src/admission/train.py --config experiments/configs/drl_params.yaml

# 启动可视化界面
python src/api/main.py

# 运行基线对比实验
python experiments/run_baselines.py
```

## 文档导航

- [系统设计](design/system_architecture.md) - 详细的系统架构设计
- [算法设计](design/algorithm_design.md) - DRL算法和DSROQ集成
- [实验设计](design/experiment_design.md) - 实验方案和评估指标
- [图表生成指南](docs/guides/figure_generation.md) - 论文图表生成方法

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

- 项目链接：[https://github.com/wwe-boop/bysj]

---

## 引用原则（仓库级）
- 允许在参考列表或 `reference/` 目录中保留外部研究的链接/DOI/编号；
- 正文与设计类文档不直接出现具体论文题名与作者姓名，仅总结方法脉络与共性结论；
- 图表与结果若借鉴外部结论，需在参考中可追溯，但正文避免显名；
- 对比或综述建议采用"近年会议工作/代表性方法"等匿名化表述。
