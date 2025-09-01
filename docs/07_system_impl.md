# 第7章 系统实现与部署

## 7.1 后端核心实现

- Hypatia封装与统一接口：状态提取、拓扑/链路查询、仿真控制。
- DRL Agent：PPO实现、训练/推理接口与并行评估。
- DSROQ适配：MCTS路由、李雅普诺夫调度的触发与数据结构。
- API：Flask REST，仿真控制、状态查询与决策下发。

## 7.2 前端可视化

- Cesium 3D：星座与链路、拓扑变化动画、决策可视化。
- 指标看板：QoE、准入统计、网络性能与训练曲线（ECharts）。

## 7.3 部署与运维

- Docker/K8s：镜像、编排与资源限制。
- 监控与日志：Prometheus/Grafana、结构化日志、追踪与告警。

## 7.4 测试与性能

- 单元/集成/性能测试用例与覆盖。
- 压测：并发请求、场景回放与最坏情况导致的退化分析。

## 7.5 本章小结

展示系统工程落地与可维护性，保证实验与演示的稳定可靠。

---

## 附：实现伪代码

```python
# Flask API 示例
@app.post('/api/admission/decision')
def decide():
    req = parse_request(request.json)
    s = env.extract_state(req)
    a = agent.predict(s)
    result = dsroq_interface.execute_admission(a, req, env.time())
    return jsonify(result.to_dict())

# 训练入口
def train(total_steps):
    for _ in range(total_steps):
        s = env.reset_episode()
        done = False
        while not done:
            a = agent.sample_action(s)
            s2, r, done, info = env.step(a)
            agent.buffer.add(s, a, r, s2, done)
            s = s2
        agent.update()
```

## 附：图表清单（建议）
- 系统组件与调用关系图
- API 接口列表与时序
- 训练/推理性能曲线与资源占用图

---

## 附：定位API示例（Flask）

```python
@app.get('/api/positioning/metrics')
def get_positioning_metrics():
    t = int(request.args.get('time', env.time()))
    users = request.args.get('users', '[]')  # JSON list of user ids/locations
    users = json.loads(users)
    metrics = pos_module.metrics(t, users)
    # metrics: { 'crlb': {'mean':..., 'p95':...}, 'gdop': {...},
    #            'visible_beams': avg, 'coop_sats': avg, 'beam_hint': {...} }
    return jsonify(metrics)

@app.post('/api/positioning/beam_hint')
def get_beam_hint():
    payload = request.json  # { 'time': t, 'users': [...], 'budget': {...} }
    hint = pos_module.beam_schedule_hint(payload)
    # hint: per-user recommended beams/sat set to support positioning
    return jsonify(hint)
```

---

## 附：前端联动示例（Vue风格伪代码）

```vue
<template>
  <div class="dashboard">
    <div ref="cesiumContainer" class="cesium" />
    <charts-panel :qoe="qoe" :pos="pos" :rates="rates" />
  </div>
</template>
<script>
export default {
  data(){ return { qoe:{}, pos:{}, rates:{} } },
  mounted(){ this.tick() },
  methods:{
    async tick(){
      setInterval(async()=>{
        const t = Date.now()/1000|0;
        const pos = await fetch(`/api/positioning/metrics?time=${t}`).then(r=>r.json())
        const rates = await fetch('/api/stats/admission').then(r=>r.json())
        const qoe = await fetch('/api/stats/qoe').then(r=>r.json())
        this.pos = pos; this.rates = rates; this.qoe = qoe;
        // 可选：依据 beam_hint 更新Cesium图层
        const hint = await fetch('/api/positioning/beam_hint',{method:'POST',body:JSON.stringify({time:t, users:this.users})}).then(r=>r.json())
        this.updateCesiumLayers(hint)
      }, 1000)
    },
    updateCesiumLayers(hint){ /* 渲染推荐波束/协作卫星 */ }
  }
}
</script>
```

---

## 参考公式对齐
详见 `docs/reference/formula_alignment.md`。
