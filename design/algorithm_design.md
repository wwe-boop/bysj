# 算法设计

## 1. DRL准入控制算法

### 1.1 马尔可夫决策过程建模

#### 状态空间设计 (State Space)

基于Hypatia的时间感知状态空间：

```python
def extract_state_from_hypatia(self, time_step, new_flow_request):
    """从Hypatia提取状态信息构建状态向量"""

    # 从Hypatia satgenpy获取网络拓扑信息
    topology = self.satgen.get_topology_at_time(time_step)
    satellites = self.satgen.get_satellite_positions(time_step)

    # 从Hypatia获取链路状态
    link_utilization = self.satgen.get_link_utilization()
    link_capacity = self.satgen.get_link_capacity()

    # 构建状态向量
    state = [
        # 全局网络状态 (来自Hypatia)
        np.mean(link_utilization),     # 平均链路利用率
        np.max(link_utilization),      # 最大链路利用率
        np.std(link_utilization),      # 利用率标准差
        len(self.current_ef_flows),    # EF流量数量
        len(self.current_af_flows),    # AF流量数量
        len(self.current_be_flows),    # BE流量数量

        # QoE状态 (基于DSROQ计算)
        self.calculate_average_qoe('EF'),
        self.calculate_average_qoe('AF'),
        self.calculate_average_qoe('BE'),
        self.calculate_qos_violation_rate(),

        # Hypatia时间维度信息
        self.get_orbit_phase(satellites, time_step),
        self.calculate_topology_change_rate(time_step),
        self.predict_future_capacity(time_step + 300),  # 5分钟后
        time_step - self.last_admission_time,

        # 新流量请求信息
        new_flow_request.type,
        new_flow_request.min_bandwidth,
        new_flow_request.max_bandwidth,
        new_flow_request.max_latency,
        *self.encode_location(new_flow_request.src),
        *self.encode_location(new_flow_request.dst),
        new_flow_request.expected_duration,

        # 历史趋势信息
        *self.get_qoe_trend_window(300),  # 5分钟趋势
        self.get_admission_rate_history(),
        self.predict_network_load(time_step + 60)  # 1分钟后负载预测
    ]

##### 融合定位特征（加入状态向量）
- 定位质量：CRLB_norm、GDOP、mean_SINR、visible_beams_cnt、coop_sat_cnt
- 注：取值需标准化至[0,1]，并可对关键特征做滑动窗口平滑

    return np.array(state, dtype=np.float32)
```

#### 动作空间设计 (Action Space)

细粒度动作空间定义：

```python
class AdmissionAction(Enum):
    REJECT = 0              # 完全拒绝
    ACCEPT = 1              # 完全接受
    DEGRADED_ACCEPT = 2     # 降级接受 (降低QoS要求)
    DELAYED_ACCEPT = 3      # 延迟接受 (排队等待)
    PARTIAL_ACCEPT = 4      # 部分接受 (降低带宽需求)

def execute_action(self, action, flow_request, time_step):
    """执行准入控制动作"""
    if action == AdmissionAction.ACCEPT:
        return self.dsroq_interface.allocate_full_resources(flow_request)

    elif action == AdmissionAction.DEGRADED_ACCEPT:
        # 降级QoS要求：延迟容忍度+50%，带宽需求-20%
        degraded_request = FlowRequest(
            type=flow_request.type,
            min_bandwidth=flow_request.min_bandwidth * 0.8,
            max_bandwidth=flow_request.max_bandwidth * 0.8,
            max_latency=flow_request.max_latency * 1.5,
            src=flow_request.src,
            dst=flow_request.dst,
            duration=flow_request.duration
        )
        return self.dsroq_interface.allocate_full_resources(degraded_request)

    elif action == AdmissionAction.DELAYED_ACCEPT:
        # 加入等待队列，延迟处理
        self.admission_queue.append((flow_request, time_step + self.delay_time))
        return None, None

    elif action == AdmissionAction.PARTIAL_ACCEPT:
        # 只分配最小带宽需求
        partial_request = FlowRequest(
            type=flow_request.type,
            min_bandwidth=flow_request.min_bandwidth,
            max_bandwidth=flow_request.min_bandwidth,
            max_latency=flow_request.max_latency,
            src=flow_request.src,
            dst=flow_request.dst,
            duration=flow_request.duration
        )
        return self.dsroq_interface.allocate_full_resources(partial_request)

    else:  # REJECT
        return None, None
```

#### 奖励函数设计 (Reward Function)

联合多目标奖励函数（QoE + 定位）：

```python
def calculate_reward(self, action, state_before, state_after, flow_info):
    """联合考虑 QoE 与 定位精度（CRLB/GDOP）的奖励"""

    """计算奖励函数"""

    # 基础QoE变化奖励
    qoe_change = state_after.weighted_qoe - state_before.weighted_qoe

    # 动作特定奖励
    action_reward = 0
    if action == AdmissionAction.ACCEPT:
        action_reward = qoe_change
    elif action == AdmissionAction.REJECT:
        action_reward = 0.1  # 保守奖励，避免无脑拒绝
    elif action == AdmissionAction.DEGRADED_ACCEPT:
        action_reward = qoe_change * 0.8  # 降级惩罚
    elif action == AdmissionAction.DELAYED_ACCEPT:
        delay_penalty = self.calculate_delay_penalty(flow_info.delay_time)
        action_reward = qoe_change * 0.9 - delay_penalty
    elif action == AdmissionAction.PARTIAL_ACCEPT:
        action_reward = qoe_change * 0.7  # 部分接受惩罚

    # 公平性奖励 (Jain公平性指数)
    fairness_bonus = self.calculate_fairness_bonus(state_after)

    # QoS违规惩罚
    violation_penalty = state_after.qos_violation_rate * (-10.0)


    # 定位目标奖励（归一化后，越小越好）
    pos_reward = 0
    if hasattr(state_after, 'crlb_norm'):
        pos_reward += (1.0 - state_after.crlb_norm)
    if hasattr(state_after, 'gdop_norm'):
        pos_reward += (1.0 - state_after.gdop_norm)
    pos_reward *= getattr(self, 'lambda_pos', 0.2)  # 权重可配

    # 网络效率奖励
    efficiency_bonus = state_after.network_utilization * 0.5

    # 长期稳定性奖励
    stability_bonus = self.calculate_stability_bonus(state_after)

    total_reward = (action_reward + fairness_bonus + pos_reward +
                   violation_penalty + efficiency_bonus + stability_bonus)

    return total_reward

def calculate_fairness_bonus(self, state):
    """计算公平性奖励"""
    qoe_values = [state.qoe_ef, state.qoe_af, state.qoe_be]
    # Jain公平性指数
    numerator = (sum(qoe_values)) ** 2
    denominator = len(qoe_values) * sum(x**2 for x in qoe_values)
    fairness_index = numerator / denominator if denominator > 0 else 0
    return fairness_index * 2.0  # 公平性权重

def calculate_stability_bonus(self, state):
    """计算长期稳定性奖励"""
    qoe_variance = np.var(self.qoe_history[-10:])  # 最近10步的QoE方差
    stability_bonus = max(0, 2.0 - qoe_variance)  # 方差越小，奖励越高
    return stability_bonus
```

### 1.2 PPO算法实现

```python
class HypatiaAdmissionAgent:
    """基于Hypatia的DRL准入控制Agent"""

    def __init__(self, state_dim, action_dim, hypatia_config):
        self.hypatia_env = HypatiaAdmissionEnvironment(hypatia_config)

        # PPO超参数
        self.ppo_config = {
            'learning_rate': 3e-4,
            'n_steps': 2048,
            'batch_size': 64,
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'clip_range': 0.2,
            'ent_coef': 0.01,
            'vf_coef': 0.5,
            'max_grad_norm': 0.5
        }

        self.ppo_agent = PPO(
            policy="MlpPolicy",
            env=self.hypatia_env,
            **self.ppo_config,
            verbose=1,
            tensorboard_log="./logs/"
        )

    def train_with_hypatia_simulation(self, total_timesteps):
        """使用Hypatia进行训练"""
        # 设置训练回调
        callback = TrainingCallback()

        # 开始训练
        self.ppo_agent.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            tb_log_name="hypatia_admission_ppo"
        )

    def evaluate_performance(self, test_scenarios):
        """评估性能"""
        results = {}
        for scenario_name, scenario_config in test_scenarios.items():
            # 加载测试场景
            self.hypatia_env.load_scenario(scenario_config)

            # 运行评估
            episode_rewards = []
            qoe_metrics = []
            admission_stats = []

            for episode in range(100):
                obs = self.hypatia_env.reset()
                total_reward = 0
                episode_qoe = []
                episode_admissions = {'accept': 0, 'reject': 0, 'degrade': 0}

                done = False
                while not done:
                    action, _ = self.ppo_agent.predict(obs, deterministic=True)
                    obs, reward, done, info = self.hypatia_env.step(action)

                    total_reward += reward
                    episode_qoe.append(info['current_qoe'])
                    episode_admissions[info['action_type']] += 1

                episode_rewards.append(total_reward)
                qoe_metrics.append(np.mean(episode_qoe))
                admission_stats.append(episode_admissions)

            results[scenario_name] = {
                'mean_reward': np.mean(episode_rewards),
                'std_reward': np.std(episode_rewards),
                'mean_qoe': np.mean(qoe_metrics),
                'admission_rate': np.mean([s['accept']/(s['accept']+s['reject']+s['degrade'])
                                         for s in admission_stats])
            }

        return results
```

## 2. DSROQ集成算法

### 2.1 Hypatia-DSROQ接口

```python
class HypatiaDSROQIntegration:
    """Hypatia与DSROQ的集成接口"""

    def __init__(self, hypatia_satgen, dsroq_config):
        self.satgen = hypatia_satgen
        self.mcts_router = MCTSRouter(dsroq_config)
        self.lyapunov_scheduler = LyapunovScheduler(dsroq_config)
        self.current_flows = []

    def execute_admission_decision(self, action, flow_request, time_step):
        """执行准入决策"""
        if action in [ACCEPT, DEGRADED_ACCEPT, PARTIAL_ACCEPT]:
            # 获取当前Hypatia网络状态
            topology = self.satgen.get_topology_at_time(time_step)

            # 使用DSROQ进行路由和带宽分配
            route, bandwidth = self.allocate_resources_with_dsroq(
                flow_request, topology, time_step
            )

            if route is not None:
                # 更新Hypatia网络状态
                self.satgen.add_flow_to_network(flow_request, route, bandwidth)

                # 启动李雅普诺夫调度
                self.lyapunov_scheduler.schedule_flow(flow_request, route)

                # 记录流量
                self.current_flows.append({
                    'flow': flow_request,
                    'route': route,
                    'bandwidth': bandwidth,
                    'start_time': time_step
                })

                return True, route, bandwidth

        return False, None, None

    def allocate_resources_with_dsroq(self, flow_request, topology, time_step):
        """使用DSROQ算法分配资源"""

        # MCTS路由搜索
        best_route = self.mcts_router.find_optimal_route(
            flow_request=flow_request,
            network_topology=topology,
            existing_flows=self.current_flows,
            time_step=time_step
        )

        if best_route is None:
            return None, None

        # 带宽分配
        allocated_bandwidth = self.calculate_bandwidth_allocation(
            flow_request, best_route, topology
        )

        return best_route, allocated_bandwidth

    def calculate_bandwidth_allocation(self, flow_request, route, topology):
        """计算带宽分配"""
        # 获取路径上的最小可用带宽
        min_available_bandwidth = float('inf')

        for i in range(len(route) - 1):
            link = (route[i], route[i+1])
            available_bw = topology.get_link_available_bandwidth(link)
            min_available_bandwidth = min(min_available_bandwidth, available_bw)

        # 分配带宽：不超过请求的最大带宽和链路可用带宽
        allocated_bw = min(
            flow_request.max_bandwidth,
            min_available_bandwidth,
            flow_request.min_bandwidth  # 至少保证最小带宽
        )

        return allocated_bw
```

### 2.2 李雅普诺夫调度优化

```python
class LyapunovScheduler:
    """李雅普诺夫调度器"""

    def __init__(self, config):
        self.V = config.get('lyapunov_parameter', 1.0)  # 李雅普诺夫参数
        self.queue_states = {}  # 队列状态

    def schedule_flow(self, flow_request, route):
        """调度流量"""
        # 更新队列状态
        self.update_queue_states(flow_request, route)

        # 计算李雅普诺夫漂移加惩罚
        drift_plus_penalty = self.calculate_drift_plus_penalty(flow_request, route)

        # 基于漂移最小化进行调度决策
        scheduling_decision = self.make_scheduling_decision(drift_plus_penalty)

        return scheduling_decision

    def calculate_drift_plus_penalty(self, flow_request, route):
        """计算李雅普诺夫漂移加惩罚"""
        drift = 0
        penalty = 0

        # 计算队列长度变化的漂移
        for node in route:
            if node in self.queue_states:
                queue_length = self.queue_states[node]
                # 漂移计算：E[Q(t+1)^2 - Q(t)^2]
                arrival_rate = self.get_arrival_rate(node, flow_request)
                service_rate = self.get_service_rate(node)

                drift += queue_length * (arrival_rate - service_rate)

        # 计算QoE惩罚项
        penalty = self.V * self.calculate_qoe_penalty(flow_request, route)

        return drift + penalty

    def calculate_qoe_penalty(self, flow_request, route):
        """计算QoE惩罚项"""
        # 基于流量类型和路径质量计算QoE惩罚
        if flow_request.type == 'EF':
            # EF流量对延迟敏感
            path_delay = self.calculate_path_delay(route)
            penalty = max(0, path_delay - flow_request.max_latency)
        elif flow_request.type == 'AF':
            # AF流量对丢包敏感
            path_loss_rate = self.calculate_path_loss_rate(route)
            penalty = path_loss_rate * 10  # 丢包惩罚权重
        else:  # BE
            # BE流量对吞吐量敏感
            path_throughput = self.calculate_path_throughput(route)
            penalty = max(0, flow_request.min_bandwidth - path_throughput)

        return penalty
```

## 3. 协作定位与 Beam Hint（新增）

### 3.1 定位质量建模与特征注入
- 目标：将定位相关质量指标引入 DRL 状态，支撑“准入-分配-定位”协同优化。
- 指标：CRLB_norm、GDOP_norm、mean_SINR/min_SINR、visible_beams_cnt、cooperative_sat_cnt、pos_availability。
- 计算：基于卫星/波束可见性和测量模型构建 FIM，计算 CRLB；GDOP 基于几何构型；SINR 基于链路预算；特征统一归一化/平滑。
- 状态注入：在 `extract_state_from_hypatia` 中合并上述特征，作为 `state` 的一部分。

### 3.2 协作定位融合策略
- 多信息源融合（参考 `reference/协作定位.pdf`）：
  - 融合 TOA/TDOA/AOA 等测量，采用加权最小二乘/贝叶斯融合近似最优；
  - 在预算约束（并发束数/功率/时隙）下优先选择对 FIM 增益最大的观测组合。
- 协作收益：定义 `cooperation_gain = f(FIM_gain, GDOP_drop, CRLB_drop)` 作为辅助目标或奖励项。

### 3.3 Beam Hint 生成算法（启发式）
伪代码（面向最小可行实现）：

```python
def beam_schedule_hint(payload):
    """基于可见性与FIM增益的启发式波束/协作集合推荐"""
    t = payload.get('time')
    users = payload.get('users', [])
    budget = payload.get('budget', {'beams_per_user': 2})

    hint = {}
    for user in users:
        candidates = enumerate_visible_beams_and_sats(user, t)
        scored = []
        for cand in candidates:
            fim_gain = estimate_fim_gain(user, cand, t)
            snr = estimate_snr(user, cand, t)
            geometry = estimate_geometry_diversity(user, cand, t)  # 抑制GDOP
            score = 0.5*fim_gain + 0.3*snr + 0.2*geometry
            scored.append((cand, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        k = budget.get('beams_per_user', 2)
        hint[user['id']] = [c for c,_ in scored[:k]]
    return hint
```

备注：可在 DSROQ 中引入 `beam_hint_score` 作为资源分配时的软约束或次级目标，触发轻量重路由/重分配。

### 3.4 联合奖励与策略联动
- 奖励扩展：在 `calculate_reward` 中加入 `lambda_pos*(1-CRLB_norm + 1-GDOP_norm)`；
- 动作联动：当 `pos_quality` 低于阈值时，偏向 `DELAYED_ACCEPT/DEGRADED_ACCEPT`；
- 资源联动：当 `beam_hint` 提示可显著改善定位质量时，触发 DSROQ 重分配。

## 3. 算法优化策略

### 3.1 多目标优化
- QoE最大化
- 公平性保证
- 网络效率提升
- 长期稳定性

### 3.2 自适应学习
- 动态调整奖励函数权重
- 在线学习和离线学习结合
- 迁移学习应对不同场景

### 3.3 鲁棒性设计
- 对网络拓扑变化的适应性
- 对流量突发的处理能力
- 对系统故障的恢复能力
