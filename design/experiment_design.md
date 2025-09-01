# 实验设计

## 1. 基于Hypatia的实验环境

### 1.1 星座配置

使用Hypatia内置的主流LEO星座配置：

```python
CONSTELLATION_CONFIGS = {
    'starlink_550': {
        'name': 'Starlink Shell 1',
        'altitude_km': 550,
        'inclination_degree': 53,
        'num_orbits': 72,
        'num_sats_per_orbit': 22,
        'total_satellites': 1584,
        'isl_data_rate_mbps': 1000,
        'ground_station_antenna_count': 4
    },
    'kuiper_630': {
        'name': 'Kuiper Shell 1',
        'altitude_km': 630,
        'inclination_degree': 51.9,
        'num_orbits': 34,
        'num_sats_per_orbit': 34,
        'total_satellites': 1156,
        'isl_data_rate_mbps': 1000,
        'ground_station_antenna_count': 4
    },
    'oneweb_1200': {
        'name': 'OneWeb',
        'altitude_km': 1200,
        'inclination_degree': 87.9,
        'num_orbits': 18,
        'num_sats_per_orbit': 40,
        'total_satellites': 720,
        'isl_data_rate_mbps': 500,
        'ground_station_antenna_count': 2
    }
}
```

### 1.2 Hypatia仿真参数

```python
SIMULATION_CONFIG = {
    'simulation_end_time_s': 3600,  # 1小时仿真
    'time_step_ms': 1000,           # 1秒时间步长
    'dynamic_state_update_interval_s': 1,
    'enable_isl_calculation': True,  # 启用星间链路
    'ground_station_selection': 'closest',
    'routing_algorithm': 'shortest_path_with_dsroq',
    'enable_detailed_logging': True,
    'output_format': 'csv'
}
```

### 1.3 地面站配置

```python
GROUND_STATIONS = [
    {'name': 'Beijing', 'lat': 39.9042, 'lon': 116.4074},
    {'name': 'New_York', 'lat': 40.7128, 'lon': -74.0060},
    {'name': 'London', 'lat': 51.5074, 'lon': -0.1278},
    {'name': 'Tokyo', 'lat': 35.6762, 'lon': 139.6503},
    {'name': 'Sydney', 'lat': -33.8688, 'lon': 151.2093},
    {'name': 'Sao_Paulo', 'lat': -23.5505, 'lon': -46.6333},
    {'name': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777},
    {'name': 'Cairo', 'lat': 30.0444, 'lon': 31.2357}
]
```

## 2. 基线对比方法

### 2.1 传统准入控制方法

```python
class BaselineAdmissionMethods:
    """基线准入控制方法集合"""

    def threshold_admission(self, flow_request, network_state):
        """固定阈值准入控制"""
        utilization_threshold = 0.8
        if network_state.avg_utilization < utilization_threshold:
            return 'ACCEPT'
        else:
            return 'REJECT'

    def load_based_admission(self, flow_request, network_state):
        """负载感知准入控制"""
        if flow_request.type == 'EF':
            threshold = 0.7  # EF流量更严格
        elif flow_request.type == 'AF':
            threshold = 0.8
        else:  # BE
            threshold = 0.9

        if network_state.avg_utilization < threshold:
            return 'ACCEPT'
        else:
            return 'REJECT'

    def bandwidth_reservation_admission(self, flow_request, network_state):
        """带宽预留准入控制"""
        reserved_bandwidth = {
            'EF': 0.3,  # 为EF预留30%带宽
            'AF': 0.4,  # 为AF预留40%带宽
            'BE': 0.3   # 为BE预留30%带宽
        }

        type_utilization = network_state.get_type_utilization(flow_request.type)
        if type_utilization < reserved_bandwidth[flow_request.type]:
            return 'ACCEPT'
        else:
            return 'REJECT'

    def ml_based_admission(self, flow_request, network_state):
        """传统机器学习准入控制"""
        # 使用随机森林进行决策
        features = self.extract_ml_features(flow_request, network_state)
        prediction = self.rf_model.predict([features])[0]
        return 'ACCEPT' if prediction == 1 else 'REJECT'

    def no_admission_control(self, flow_request, network_state):
        """无准入控制（接受所有请求）"""
        return 'ACCEPT'
```

### 2.2 其他DRL方法

```python
class DRLBaselineMethods:
    """DRL基线方法"""

    def dqn_admission(self, state):
        """DQN准入控制"""
        q_values = self.dqn_model.predict(state)
        action = np.argmax(q_values)
        return self.action_mapping[action]

    def a3c_admission(self, state):
        """A3C准入控制"""
        policy, value = self.a3c_model.predict(state)
        action = np.random.choice(len(policy), p=policy)
        return self.action_mapping[action]

    def ddpg_admission(self, state):
        """DDPG准入控制（连续动作空间）"""
        action = self.ddpg_model.predict(state)
        # 将连续动作映射到离散动作
        discrete_action = self.continuous_to_discrete(action)
        return self.action_mapping[discrete_action]
```

## 3. 性能评估指标

### 3.1+ 定位相关指标（新增）
```python
class PositioningMetrics:
    """定位相关评估指标（与 reference/2404.01148v1.pdf 对齐）"""
    def crlb_norm(self, users):
        # 将CRLB归一化至[0,1]
        pass
    def gdop_norm(self, users):
        # GDOP归一化，越小越好
        pass
    def visible_beams_cnt(self, users):
        # 可见波束数量统计
        pass
    def cooperation_gain(self, users):
        # 多卫星/多波束协作带来的精度提升
        pass
```


### 3.1 QoE相关指标

```python
class QoEMetrics:
    """QoE评估指标"""

    def calculate_average_qoe(self, flow_records):
        """计算平均QoE分数"""
        total_qoe = 0
        total_flows = len(flow_records)

        for flow in flow_records:
            if flow.type == 'EF':
                qoe = self.calculate_ef_qoe(flow)
            elif flow.type == 'AF':
                qoe = self.calculate_af_qoe(flow)
            else:  # BE
                qoe = self.calculate_be_qoe(flow)

            total_qoe += qoe

        return total_qoe / total_flows if total_flows > 0 else 0

    def calculate_ef_qoe(self, flow):
        """计算EF流量QoE（基于延迟）"""
        if flow.actual_delay <= flow.max_latency:
            qoe = 5.0 - (flow.actual_delay / flow.max_latency) * 2.0
        else:
            qoe = 1.0  # 延迟超标，QoE很低
        return max(1.0, min(5.0, qoe))

    def calculate_af_qoe(self, flow):
        """计算AF流量QoE（基于丢包率）"""
        if flow.packet_loss_rate <= 0.01:  # 1%丢包率阈值
            qoe = 5.0 - flow.packet_loss_rate * 200
        else:
            qoe = 3.0 - flow.packet_loss_rate * 100
        return max(1.0, min(5.0, qoe))

    def calculate_be_qoe(self, flow):
        """计算BE流量QoE（基于吞吐量）"""
        throughput_ratio = flow.actual_throughput / flow.requested_bandwidth
        if throughput_ratio >= 0.8:
            qoe = 4.0 + throughput_ratio
        else:
            qoe = throughput_ratio * 5.0
        return max(1.0, min(5.0, qoe))

    def calculate_qoe_fairness(self, flow_records):
        """计算QoE公平性（Jain公平性指数）"""
        qoe_values = [self.get_flow_qoe(flow) for flow in flow_records]
        if not qoe_values:
            return 0

        numerator = (sum(qoe_values)) ** 2
        denominator = len(qoe_values) * sum(x**2 for x in qoe_values)
        return numerator / denominator if denominator > 0 else 0
```

### 3.2 准入控制指标

```python
class AdmissionMetrics:
    """准入控制评估指标"""

    def calculate_admission_rate(self, decisions):
        """计算准入率"""
        total_requests = len(decisions)
        accepted_requests = sum(1 for d in decisions if d in ['ACCEPT', 'DEGRADED_ACCEPT', 'PARTIAL_ACCEPT'])
        return accepted_requests / total_requests if total_requests > 0 else 0

    def calculate_rejection_rate(self, decisions):
        """计算拒绝率"""
        total_requests = len(decisions)
        rejected_requests = sum(1 for d in decisions if d == 'REJECT')
        return rejected_requests / total_requests if total_requests > 0 else 0

    def calculate_degradation_rate(self, decisions):
        """计算降级率"""
        total_requests = len(decisions)
        degraded_requests = sum(1 for d in decisions if d == 'DEGRADED_ACCEPT')
        return degraded_requests / total_requests if total_requests > 0 else 0

    def calculate_type_specific_admission_rate(self, decisions, flow_types):
        """计算不同类型流量的准入率"""
        type_stats = {'EF': {'total': 0, 'accepted': 0},
                     'AF': {'total': 0, 'accepted': 0},
                     'BE': {'total': 0, 'accepted': 0}}

        for decision, flow_type in zip(decisions, flow_types):
            type_stats[flow_type]['total'] += 1
            if decision in ['ACCEPT', 'DEGRADED_ACCEPT', 'PARTIAL_ACCEPT']:
                type_stats[flow_type]['accepted'] += 1

        admission_rates = {}
        for flow_type in type_stats:
            total = type_stats[flow_type]['total']
            accepted = type_stats[flow_type]['accepted']
            admission_rates[flow_type] = accepted / total if total > 0 else 0

        return admission_rates
```

### 3.3 网络性能指标

```python
class NetworkMetrics:
    """网络性能评估指标"""

    def calculate_network_utilization(self, link_utilizations):
        """计算网络利用率"""
        return {
            'average': np.mean(link_utilizations),
            'maximum': np.max(link_utilizations),
            'minimum': np.min(link_utilizations),
            'std': np.std(link_utilizations)
        }

    def calculate_end_to_end_delay(self, flow_records):
        """计算端到端延迟"""
        delays = [flow.actual_delay for flow in flow_records if flow.completed]
        return {
            'average': np.mean(delays) if delays else 0,
            'p95': np.percentile(delays, 95) if delays else 0,
            'p99': np.percentile(delays, 99) if delays else 0
        }

    def calculate_throughput(self, flow_records):
        """计算吞吐量"""
        total_data = sum(flow.data_transmitted for flow in flow_records)
        total_time = max(flow.end_time for flow in flow_records) - min(flow.start_time for flow in flow_records)
        return total_data / total_time if total_time > 0 else 0

    def calculate_packet_loss_rate(self, flow_records):
        """计算丢包率"""
        total_packets = sum(flow.packets_sent for flow in flow_records)
        lost_packets = sum(flow.packets_lost for flow in flow_records)
        return lost_packets / total_packets if total_packets > 0 else 0
```

## 4. 实验场景设计

### 4.1 负载变化场景

```python
LOAD_SCENARIOS = {
    'light_load': {
        'arrival_rate': 0.1,  # 每秒0.1个请求
        'duration': 3600,     # 1小时
        'traffic_mix': {'EF': 0.2, 'AF': 0.3, 'BE': 0.5}
    },
    'medium_load': {
        'arrival_rate': 0.5,
        'duration': 3600,
        'traffic_mix': {'EF': 0.3, 'AF': 0.4, 'BE': 0.3}
    },
    'heavy_load': {
        'arrival_rate': 1.0,
        'duration': 3600,
        'traffic_mix': {'EF': 0.4, 'AF': 0.4, 'BE': 0.2}
    },
    'dynamic_load': {
        'arrival_pattern': 'sinusoidal',  # 正弦波变化
        'base_rate': 0.5,
        'amplitude': 0.4,
        'period': 600,  # 10分钟周期
        'duration': 3600
    }
}
```

### 4.2 故障场景

```python
FAILURE_SCENARIOS = {
    'satellite_failure': {
        'failure_type': 'satellite',
        'failure_time': 1800,  # 30分钟后故障
        'failure_duration': 300,  # 故障持续5分钟
        'affected_satellites': [100, 101, 102]  # 故障卫星ID
    },
    'ground_station_failure': {
        'failure_type': 'ground_station',
        'failure_time': 1200,
        'failure_duration': 600,
        'affected_stations': ['Beijing', 'Tokyo']
    },
    'link_congestion': {
        'failure_type': 'link_congestion',
        'congestion_start': 900,
        'congestion_duration': 1200,
        'congestion_factor': 0.5  # 带宽减少50%
    }
}
```

## 5. 消融实验设计

### 5.1 状态空间消融

```python
ABLATION_STATE_CONFIGS = {
    'full_state': 'all_features',
    'no_time_info': 'remove_temporal_features',
    'no_history': 'remove_historical_features',
    'no_prediction': 'remove_prediction_features',
    'basic_state': 'only_basic_network_features'
}
```

### 5.2 奖励函数消融

```python
ABLATION_REWARD_CONFIGS = {
    'full_reward': 'qoe + fairness + efficiency + stability',
    'qoe_only': 'only_qoe_change',
    'no_fairness': 'qoe + efficiency + stability',
    'no_efficiency': 'qoe + fairness + stability',
    'no_stability': 'qoe + fairness + efficiency'
}
```

### 5.3 动作空间消融

```python
ABLATION_ACTION_CONFIGS = {
    'full_actions': ['ACCEPT', 'REJECT', 'DEGRADED_ACCEPT', 'DELAYED_ACCEPT', 'PARTIAL_ACCEPT'],
    'binary_actions': ['ACCEPT', 'REJECT'],
    'three_actions': ['ACCEPT', 'REJECT', 'DEGRADED_ACCEPT'],
    'no_delay': ['ACCEPT', 'REJECT', 'DEGRADED_ACCEPT', 'PARTIAL_ACCEPT']
}
```

---

## 6. 统计检验与可视化示例

### 6.1 统计检验
- 置信区间：均值±t乘标准误；多次运行取n≥10
- 显著性检验：两方法t检验，多方法ANOVA＋事后检验（Holm–Bonferroni校正）
- 稳定性：报告均值±标准差，提供箱线图/小提琴图

### 6.2 可视化示例
- 折线/柱状：QoE、准入/拒绝/降级/延迟率、Util/Delay/PLR/Thr
- CDF/箱线图：QoE分布与时延分布
- 热力图：特征重要性与敏感性
- 雷达图：多指标综合对比
