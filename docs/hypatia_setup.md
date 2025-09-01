# Hypatia 环境安装与模式切换指引

本项目支持 Hypatia/ns-3 的真实与简化两种模式，默认使用简化模式便于快速演示；当完成 Hypatia 安装后，可一键切换到真实模式进行更高保真仿真。

## 1. 环境准备
- Python 依赖：使用 `environment.yml` 或 `requirements.txt`
- 系统依赖（建议）：`cmake`、`gfortran`、`GEOS/PROJ`
- 可选：`pandoc`、`TeXLive (xelatex)`（用于论文编译）

## 2. 安装/构建 Hypatia（可选，启用真实模式时需要）
1) 初始化/下载 Hypatia 相关组件
```bash
make hypatia-init
```
2) 构建与校验（参考官方脚本/文档）
- 生成/读取 TLE、ISL、GSL、动态状态等所需资源
- 如需 satviz，可配置 Cesium Token

## 3. 后端模式配置
在配置文件（如 `experiments/configs/default.yaml`）中新增/修改 `backend` 节点：
```yaml
backend:
  hypatia_mode: simplified   # real | simplified
  ns3_mode: simplified       # real | simplified
  data_dir: /tmp/hypatia_temp
```

- `hypatia_mode=real` 需确保 Hypatia 依赖可用；否则将自动回退到 `simplified`。
- `ns3_mode=real` 预留真实 ns-3 接入（当前仍使用内置 NS3Simulator 作为占位）。
- `data_dir` 用于生成/读取 TLE/ISL/GSL/动态状态等数据。

## 4. 运行与验证
1) 启动仿真/服务（示例）
```bash
python run_web_system.py
```
2) 验证接口可用性（示例）
```bash
curl -s http://localhost:5000/api/status | jq .
```
3) 切换模式后再次运行，比较关键指标（吞吐/时延/丢包/利用率）是否合理。

## 5. 常见问题
- 未安装 Hypatia 但设置了 `hypatia_mode=real`：系统将回退 `simplified` 并在日志中提示。
- 指标校准：如需与真实模式对齐，请参照 `docs/design_implementation_alignment.md` 第 3.4 节的阈值与批跑流程生成校准报告。

---
备注：后续将补充 ns-3 真实接入适配层与详细的 Hypatia 数据生成脚本说明。
