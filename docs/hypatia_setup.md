# Hypatia 环境安装指引（占位）

本项目当前使用 Hypatia 作为仿真基础。正式集成前，先完成以下步骤：

1. 子模块初始化（若已配置）：
```bash
make hypatia-init
```

2. 安装依赖（建议独立环境）：
- Python: 使用 `environment.yml` 或 `requirements.txt`
- 系统：安装 `GEOS/PROJ`、`gfortran`、`cmake` 等构建依赖
- PDF编译：安装 `pandoc` 与 `TeXLive (xelatex)`（可选）

3. 构建 Hypatia：
- 参考官方文档执行 `hypatia_build.sh` 等脚本
- 如需 satviz 可视化，请配置 Cesium Token

4. 与本项目对接：
- 统一数据路径（星座、流量、结果）
- 在 `src/` 侧实现 `hypatia_adapter`，暴露：
  - `get_topology_at_time(t)`、`get_link_utilization()`、`add_flow_to_network()` 等接口

> 注：目前仓库内为占位集成，后续将逐步接入真实 Hypatia 接口与DSROQ流程。
