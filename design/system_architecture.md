# 系统架构设计

## 1. 总体架构

### 1.1 分层决策架构

本系统采用分层决策架构，将准入控制与资源分配解耦，实现高效的决策流程：

```
┌─────────────────────────────────────────────────────────────┐
│                    DRL准入控制层                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   状态提取器     │  │   PPO Agent     │  │   动作执行器     │ │
│  │ (State Extractor)│  │                │  │ (Action Executor)│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼ 决策接口
┌─────────────────────────────────────────────────────────────┐
│             Hypatia网络状态层 + 融合定位层                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  星座/拓扑管理器  │  │   定位指标计算   │  │   状态/质量监控  │ │
│  │ (Const/Topo Mgr) │  │(Pos Metrics Calc)│  │(State/Pos Mon)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼ 路由接口
┌─────────────────────────────────────────────────────────────┐
│                   DSROQ资源分配层                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   MCTS路由器     │  │   带宽分配器     │  │ 李雅普诺夫调度器 │ │
│  │  (MCTS Router)  │  │(Bandwidth Alloc)│  │(Lyapunov Sched) │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼ 执行接口
┌─────────────────────────────────────────────────────────────┐
│                 Hypatia仿真执行层                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   ns3仿真器      │  │   性能监控器     │  │   QoE计算器     │ │
│  │ (ns3 Simulator) │  │(Perf Monitor)   │  │ (QoE Calculator)│ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件说明

#### DRL准入控制层
- **状态提取器**：从Hypatia获取网络状态，构建时间感知状态向量
- **PPO Agent**：基于状态做出准入决策（接受/拒绝/降级/延迟/部分接受）
- **动作执行器**：将DRL决策转换为具体的网络操作

#### Hypatia网络状态层 + 融合定位层
- **星座管理器**：管理LEO卫星星座配置和轨道计算
- **拓扑计算器**：实时计算网络拓扑变化
- **定位指标计算**（新增）：计算 CRLB、GDOP、可见波束数、协同卫星数、平均SINR 等（参考 reference/2404.01148v1.pdf）
- **状态监控器**：监控链路状态、流量状态、QoE与定位指标

#### DSROQ资源分配层
- **MCTS路由器**：基于蒙特卡洛树搜索的路由算法
- **带宽分配器**：为接受的流量分配带宽资源
- **李雅普诺夫调度器**：基于李雅普诺夫优化的调度算法

#### Hypatia仿真执行层
- **ns3仿真器**：包级网络仿真执行
- **性能监控器**：实时监控网络性能指标
- **QoE计算器**：计算用户体验质量指标

## 2. 技术栈选择

### 2.1 核心框架
- **Hypatia**：LEO卫星网络仿真框架
  - satgenpy：卫星网络生成和路由
  - ns3-sat-sim：ns-3包级仿真
  - satviz：Cesium 3D可视化
- **PyTorch**：深度学习框架
- **Stable-Baselines3**：强化学习算法库
- **SimPy**：离散事件仿真（与Hypatia集成）

### 2.2 开发工具
- **后端**：Python 3.8+, Flask, Redis, PostgreSQL
- **前端**：Vue.js 3, CesiumJS, ECharts, Element Plus
- **部署**：Docker, Docker Compose, Kubernetes
- **监控**：Prometheus, Grafana, MLflow
- **测试**：pytest, unittest, coverage

### 2.3 数据处理
- **科学计算**：NumPy, SciPy, Pandas
- **网络分析**：NetworkX, igraph
- **可视化**：Matplotlib, Plotly, Seaborn
- **地理计算**：Cartopy, Geopy, Skyfield

注：定位/协作定位方法与接口详见 `design/系统.md` 3.8 节，算法细节见 `design/algorithm_design.md` 第3章，实验方案见 `design/experiment_design.md` 第4章。

## 3. 数据流设计

### 3.1 实时决策流程

```
流量请求到达 → 状态提取（网络+定位） → DRL决策 → 动作执行 → 联合评估（QoE+定位） → 学习更新
     ↓            ↓         ↓         ↓         ↓         ↓
  [新流量]    [网络状态]  [准入动作]  [资源分配]  [QoE指标]  [策略更新]
     │            │         │         │         │         │
     │            │         │         │         │         │
  Hypatia     Hypatia    PPO Agent   DSROQ    Hypatia   PPO Agent
  流量生成     状态监控    神经网络    算法      仿真器     经验回放
```

### 3.2 状态信息流

```python
# 从Hypatia提取的状态信息
hypatia_state = {
    'topology': satgen.get_topology_at_time(t),
    'satellites': satgen.get_satellite_positions(t),
    'links': satgen.get_link_states(t),
    'utilization': satgen.get_link_utilization(t),
    'capacity': satgen.get_link_capacity(t),
    'positioning': pos_module.metrics(t, user_locations, sat_beamset)  # CRLB/GDOP/可见波束等
}

# 构建DRL状态向量
drl_state = construct_state_vector(
    hypatia_state, 
    current_flows, 
    qoe_metrics, 
    new_flow_request
)
```

### 3.3 决策执行流

```python
# DRL决策
action = ppo_agent.predict(drl_state)

# 动作映射
if action == ACCEPT:
    route, bandwidth = dsroq.allocate_resources(flow_request)
    hypatia_sim.add_flow(flow_request, route, bandwidth)
elif action == DEGRADED_ACCEPT:
    degraded_request = degrade_qos(flow_request)
    route, bandwidth = dsroq.allocate_resources(degraded_request)
    hypatia_sim.add_flow(degraded_request, route, bandwidth)
# ... 其他动作处理
```

## 4. 接口设计

### 4.1 Hypatia集成接口

```python
class HypatiaInterface:
    """Hypatia框架集成接口"""
    
    def __init__(self, constellation_config):
        self.satgen = SatelliteNetworkGenerator(constellation_config)
        self.ns3_sim = NS3SatelliteSimulator()
        
    def get_network_state(self, time_step):
        """获取网络状态"""
        return {
            'topology': self.satgen.get_topology_at_time(time_step),
            'satellites': self.satgen.get_satellite_positions(time_step),
            'links': self.satgen.get_link_states(time_step)
        }
    
    def execute_flow_allocation(self, flow, route, bandwidth):
        """执行流量分配"""
        return self.ns3_sim.add_flow(flow, route, bandwidth)
    
    def get_performance_metrics(self):
        """获取性能指标"""
        return self.ns3_sim.get_performance_metrics()
```

### 4.2 DRL-DSROQ接口

```python
class DRLDSROQInterface:
    """DRL与DSROQ集成接口"""
    
    def __init__(self, dsroq_config):
        self.mcts_router = MCTSRouter(dsroq_config)
        self.lyapunov_scheduler = LyapunovScheduler(dsroq_config)
        
    def process_admission_decision(self, action, flow_request, network_state):
        """处理准入决策"""
        if action in [ACCEPT, DEGRADED_ACCEPT, PARTIAL_ACCEPT]:
            return self.allocate_resources(flow_request, network_state)
        else:
            return None, None
    
    def allocate_resources(self, flow_request, network_state):
        """分配网络资源"""
        route = self.mcts_router.find_route(flow_request, network_state)
        bandwidth = self.calculate_bandwidth_allocation(flow_request, route)
        return route, bandwidth
```

### 4.3 模块边界与接口契约

#### 4.3.1 模块边界
*   **准入模块 (Admission)**:
    *   输入：新流到达事件、网络/定位状态特征（含CRLB/GDOP、可见波束/协作卫星、Beam Hint）、历史与趋势。
    *   输出：已接纳业务集合、优先级/权重画像、降级/延迟/部分接纳策略、队列约束提示。
*   **调度模块 (Scheduling/DSROQ)**:
    *   输入：准入输出的业务集合与策略约束、网络瞬时/预测状态、链路/队列信息。
    *   输出：多跳路由、带宽分配、调度次序与速率控制、队列权重更新；必要时触发重分配。

#### 4.3.2 接口契约总览

上层准入向下层DSROQ输出“集合+画像+约束”三要素；定位模块提供`Apos/CRLB/GDOP/Beam Hint`等服务性信号。

**接口示例 (Admission → DSROQ):**
```json
{
  "flows": [
    {
      "id": "u1",
      "class": "EF",
      "demand_mbps": 5.0,
      "latency_ms": 50,
      "duration_s": 120,
      "position": {"lat": 39.9, "lon": 116.4}
    }
  ],
  "profiles": {
    "weights": {"EF": 1.2, "AF": 1.0, "BE": 0.7},
    "lambda_pos": 0.2
  },
  "constraints": {
    "seam_penalty": 0.5,
    "reroute_cooldown_ms": 5000,
    "min_visible_beams": 2,
    "min_coop_sats": 2,
    "crlb_threshold": 50,
    "beam_hint": [
      {"user_id": "u1", "candidates": ["b12", "b45"]}
    ]
  }
}
```

#### 4.3.3 Web API 端点映射

*   **准入**: `POST /api/admission/request`（提交`flows/profiles/constraints`）。
*   **定位指标**: `GET|POST /api/positioning/metrics`（GET轻量参数查询；POST以JSON体提交复杂查询）。
*   **波束提示**: `POST /api/positioning/beam_hint`（获取每用户的候选波束集合）。
*   **网络视图**: `GET /api/network/topology`（供TEG/可视性可视化）；状态视图：`GET /api/network/state`（工程态）。

## 5. 可扩展性设计

### 5.1 模块化设计
- 每个组件都有清晰的接口定义
- 支持插件式的算法替换
- 配置驱动的参数管理

### 5.2 性能优化
- 并行化的Hypatia仿真
- GPU加速的DRL训练
- 缓存机制优化状态计算

### 5.3 监控与调试
- 全链路的性能监控
- 详细的日志记录
- 可视化的调试界面

## 6. 协同策略与建模

### 6.1 协同策略与失效保护

*   当定位质量退化或拥塞风险上升时，准入进入保守模式（优先级降低、延迟或部分接纳），调度触发李雅普诺夫稳定性保护的带宽回收与路径切换。
*   当业务结构变化（EF/AF/BE占比波动）时，准入动态调整权重画像，调度依据新画像重排队列与重分配带宽。
*   **失效保护**：任一模块异常时，降级到阈值准入 + 启发式调度的安全基线，保证可用性。

### 6.2 接触计划与时间扩展图建模

*   **接触计划 (Visibility/Contact Plan)**：由 `Hypatia` 产生卫星-地面/卫星-卫星的可见性窗口、仰角、Doppler与带宽上限，供状态提取与路由代价计算使用。
*   **时间扩展图 (Time-Expanded Graph, TEG)**：以时间步Δτ离散化网络，节点复制为 \( V_t \)，边带时间依赖代价 \( c_t(e) \) 与可用性指示 \( a_t(e)\in\{0,1\} \)。
*   **seam与重路由惩罚**：跨缝边附加代价 \( \kappa_{seam} \)；路径变更惩罚/冷却 \( \kappa_{chg},\ T_{cool} \) 以限制重路由频率，提升路由寿命与稳定性。

## 7. 实现落点索引

| 模块 | 文档关键点 | 实现落点 | 相关Web端点 |
| --- | --- | --- | --- |
| Hypatia/网络状态 | 接触计划、TEG节点/边 | `src/hypatia/network_state.py` | `GET /api/network/topology` |
| DSROQ-路由 | 跨缝惩罚、路径代价 | `src/dsroq/mcts_routing.py` |（内部计算）|
| DSROQ-调度 | 李雅普诺夫与重分配 | `src/dsroq/core.py` | `POST /api/simulation/start`（触发流程）|
| 准入控制 | DRL/PPO环境与策略 | `src/admission/*` | `POST /api/admission/request` |
| 定位协同 | Apos/CRLB/GDOP/Beam Hint | `src/positioning/` | `GET /api/positioning/metrics`, `POST /api/positioning/beam_hint` |

---

## 8. 差异与工程化扩展（新增）

- 指标抽象与接口统一：系统层定义 `Apos`，并在状态/奖励/代价/约束与 Web/API 字段中对齐；区别于参考中仅报告 CRLB/GDOP。
- 搜索与稳定性增强：以 MCTS 路由结合 `seam_penalty`、`path_change_penalty`、`reroute_cooldown_ms` 与 TEG 模型，面向可运行稳定性而不是仅理论最优。
- 软硬约束并行：硬约束过滤最小可见波束/协作卫星与 CRLB 阈值，软约束以 `lambda_pos` 注入代价；两类约束在架构层实现分层解耦。
- 未覆盖内容：稳定域/近最优界的理论证明与 EKF/UKF/PF 估计器实现细节不在本章展开，转由实验与实现部分体现其影响。

## 引用原则（工程文档）
- 工程文档与示意图不直接出现外部论文题名与作者；
- 如需参考，请在 `reference/` 目录保留链接/DOI/编号，正文仅描述方法；
- 对比或综述采用匿名化表述（如“近年会议工作/代表性方法”）。
