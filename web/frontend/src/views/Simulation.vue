<template>
  <div class="simulation">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="24">
        <h1 class="page-title">
          <el-icon><VideoPlay /></el-icon>
          仿真控制
        </h1>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 控制面板 -->
      <el-col :xs="24" :lg="8">
        <el-card class="control-panel">
          <template #header>
            <span>控制面板</span>
          </template>
          
          <!-- 场景选择 -->
          <div class="control-section">
            <h4>场景选择</h4>
            <el-select
              v-model="selectedScenario"
              placeholder="请选择仿真场景"
              style="width: 100%"
              @change="onScenarioChange"
              :disabled="simulationStore.isRunning"
            >
              <el-option
                v-for="scenario in scenarios"
                :key="scenario.name"
                :label="scenario.name"
                :value="scenario.name"
              >
                <div class="scenario-option">
                  <div class="scenario-name">{{ scenario.name }}</div>
                  <div class="scenario-desc">{{ scenario.description }}</div>
                </div>
              </el-option>
            </el-select>
          </div>

          <!-- 场景信息 -->
          <div v-if="currentScenario" class="control-section">
            <h4>场景信息</h4>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="名称">
                {{ currentScenario.name }}
              </el-descriptions-item>
              <el-descriptions-item label="描述">
                {{ currentScenario.description }}
              </el-descriptions-item>
              <el-descriptions-item label="持续时间">
                {{ formatDuration(currentScenario.durationSeconds) }}
              </el-descriptions-item>
              <el-descriptions-item label="流量模式">
                {{ currentScenario.trafficPattern }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 仿真参数 -->
          <div class="control-section">
            <h4>仿真参数</h4>
            <el-form :model="simulationConfig" label-width="80px" size="small">
              <el-form-item label="持续时间">
                <el-input-number
                  v-model="simulationConfig.duration"
                  :min="60"
                  :max="3600"
                  :step="60"
                  :disabled="simulationStore.isRunning"
                  style="width: 100%"
                />
                <span class="unit">秒</span>
              </el-form-item>
            </el-form>
          </div>

          <!-- 控制按钮 -->
          <div class="control-section">
            <h4>仿真控制</h4>
            <div class="control-buttons">
              <el-button
                type="success"
                :icon="VideoPlay"
                @click="startSimulation"
                :disabled="!selectedScenario || simulationStore.isRunning"
                :loading="simulationStore.loading"
                style="width: 100%"
              >
                启动仿真
              </el-button>
              <el-button
                type="danger"
                :icon="VideoPause"
                @click="stopSimulation"
                :disabled="!simulationStore.isRunning"
                :loading="simulationStore.loading"
                style="width: 100%"
              >
                停止仿真
              </el-button>
              <el-button
                type="info"
                :icon="Refresh"
                @click="resetSimulation"
                :disabled="simulationStore.isRunning"
                :loading="simulationStore.loading"
                style="width: 100%"
              >
                重置仿真
              </el-button>
            </div>
          </div>

          <!-- 仿真状态 -->
          <div class="control-section">
            <h4>仿真状态</h4>
            <div class="status-display">
              <div class="status-item">
                <span class="label">状态:</span>
                <el-tag :type="statusType" size="small">
                  {{ statusText }}
                </el-tag>
              </div>
              <div class="status-item">
                <span class="label">进度:</span>
                <span class="value">{{ simulationStore.progress.toFixed(1) }}%</span>
              </div>
              <div class="status-item">
                <span class="label">时间:</span>
                <span class="value">{{ formatTime(simulationStore.currentTime) }}</span>
              </div>
              <div class="status-item">
                <span class="label">剩余:</span>
                <span class="value">{{ formatTime(simulationStore.remainingTime) }}</span>
              </div>
            </div>
            <el-progress
              :percentage="simulationStore.progress"
              :stroke-width="12"
              :show-text="false"
              class="progress-bar"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 实时监控 -->
      <el-col :xs="24" :lg="16">
        <el-card class="monitor-panel">
          <template #header>
            <div class="card-header">
              <span>实时监控</span>
              <el-button-group size="small">
                <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
                <el-button :icon="Download" @click="exportData">导出</el-button>
              </el-button-group>
            </div>
          </template>

          <!-- 关键指标 -->
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ formatThroughput(currentMetrics?.averageThroughput || 0) }}</div>
              <div class="metric-label">平均吞吐量</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ formatLatency(currentMetrics?.averageLatency || 0) }}</div>
              <div class="metric-label">平均延迟</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ formatPercentage(currentMetrics?.admissionRate || 0) }}</div>
              <div class="metric-label">准入成功率</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ formatQoE(currentMetrics?.qoeScore || 0) }}</div>
              <div class="metric-label">QoE评分</div>
            </div>
          </div>

          <!-- 实时图表 -->
          <div class="chart-container">
            <RealTimeChart
              :data="chartData"
              :loading="chartLoading"
              height="300px"
            />
          </div>
        </el-card>

        <!-- 事件日志 -->
        <el-card class="mt-4">
          <template #header>
            <div class="card-header">
              <span>事件日志</span>
              <el-button size="small" @click="clearLogs" :icon="Delete">
                清空
              </el-button>
            </div>
          </template>
          <EventLog
            :events="events"
            :max-events="50"
            height="200px"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useSimulationStore } from '@/stores/simulation'
import { useWebSocketStore } from '@/stores/websocket'
import { useAppStore } from '@/stores/app'
import { scenarioApi } from '@/api/simulation'
import RealTimeChart from '@/components/RealTimeChart.vue'
import EventLog from '@/components/EventLog.vue'
import type { SimulationScenario, SimulationConfig } from '@/types'
import {
  VideoPlay,
  VideoPause,
  Refresh,
  Download,
  Delete
} from '@element-plus/icons-vue'

// 状态管理
const simulationStore = useSimulationStore()
const websocketStore = useWebSocketStore()
const appStore = useAppStore()

// 响应式数据
const selectedScenario = ref('')
const scenarios = ref<SimulationScenario[]>([])
const currentScenario = ref<SimulationScenario | null>(null)
const simulationConfig = ref<SimulationConfig>({
  scenario: '',
  duration: 300,
  parameters: {}
})
const chartLoading = ref(false)
const events = ref<Array<{ timestamp: number; type: string; message: string }>>([])

// 计算属性
const statusType = computed(() => {
  if (simulationStore.isRunning) return 'success'
  return 'info'
})

const statusText = computed(() => {
  if (simulationStore.isRunning) return '运行中'
  return '未运行'
})

const currentMetrics = computed(() => simulationStore.latestMetrics)

const chartData = computed(() => {
  const history = simulationStore.performanceHistory.slice(-50) // 最近50个数据点
  return history.map(metrics => ({
    timestamp: metrics.timeStep,
    throughput: metrics.averageThroughput,
    latency: metrics.averageLatency,
    qoe: metrics.qoeScore,
    admissionRate: metrics.admissionRate
  }))
})

// 方法
const loadScenarios = async () => {
  try {
    scenarios.value = await scenarioApi.getAll()
  } catch (error) {
    console.error('加载场景失败:', error)
    appStore.addNotification({
      type: 'error',
      title: '加载失败',
      message: '无法加载仿真场景'
    })
  }
}

const onScenarioChange = async () => {
  if (!selectedScenario.value) {
    currentScenario.value = null
    return
  }

  try {
    currentScenario.value = await scenarioApi.getById(selectedScenario.value)
    simulationConfig.value.scenario = selectedScenario.value
    simulationConfig.value.duration = currentScenario.value.durationSeconds
  } catch (error) {
    console.error('获取场景详情失败:', error)
  }
}

const startSimulation = async () => {
  if (!selectedScenario.value) {
    ElMessage.warning('请先选择仿真场景')
    return
  }

  try {
    await simulationStore.startSimulation(simulationConfig.value)
    addEvent('success', `仿真已启动: ${selectedScenario.value}`)
  } catch (error) {
    console.error('启动仿真失败:', error)
    addEvent('error', `启动仿真失败: ${error}`)
  }
}

const stopSimulation = async () => {
  try {
    await simulationStore.stopSimulation()
    addEvent('warning', '仿真已停止')
  } catch (error) {
    console.error('停止仿真失败:', error)
    addEvent('error', `停止仿真失败: ${error}`)
  }
}

const resetSimulation = async () => {
  try {
    await simulationStore.resetSimulation()
    addEvent('info', '仿真已重置')
  } catch (error) {
    console.error('重置仿真失败:', error)
    addEvent('error', `重置仿真失败: ${error}`)
  }
}

const refreshData = async () => {
  chartLoading.value = true
  try {
    await simulationStore.fetchPerformanceMetrics()
  } finally {
    chartLoading.value = false
  }
}

const exportData = () => {
  // 导出仿真数据
  const data = {
    scenario: selectedScenario.value,
    config: simulationConfig.value,
    metrics: simulationStore.performanceHistory,
    timestamp: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `simulation_data_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const clearLogs = () => {
  events.value = []
}

const addEvent = (type: string, message: string) => {
  events.value.unshift({
    timestamp: Date.now(),
    type,
    message
  })
  
  if (events.value.length > 100) {
    events.value = events.value.slice(0, 100)
  }
}

// 格式化函数
const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  return `${minutes} 分钟`
}

const formatTime = (seconds: number) => {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}

const formatThroughput = (value: number) => {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)} Gbps`
  }
  return `${value.toFixed(1)} Mbps`
}

const formatLatency = (value: number) => {
  return `${value.toFixed(1)} ms`
}

const formatPercentage = (value: number) => {
  return `${(value * 100).toFixed(1)}%`
}

const formatQoE = (value: number) => {
  return value.toFixed(2)
}

// 生命周期
onMounted(async () => {
  await loadScenarios()
  await simulationStore.fetchStatus()
  
  // 订阅WebSocket事件
  if (websocketStore.isConnected) {
    websocketStore.subscribe('simulation')
  }
  
  // 监听仿真事件
  watch(() => simulationStore.isRunning, (running) => {
    if (running) {
      addEvent('success', '仿真已启动')
    } else {
      addEvent('info', '仿真已停止')
    }
  })
})
</script>

<style scoped>
.simulation {
  padding: 0;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 20px 0;
  color: var(--el-text-color-primary);
  font-size: 24px;
  font-weight: 600;
}

.control-panel {
  height: fit-content;
}

.monitor-panel {
  height: fit-content;
}

.control-section {
  margin-bottom: 24px;
}

.control-section h4 {
  margin: 0 0 12px 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.scenario-option {
  display: flex;
  flex-direction: column;
}

.scenario-name {
  font-weight: 500;
}

.scenario-desc {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.unit {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.control-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-display {
  margin-bottom: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.status-item .label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.status-item .value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.progress-bar {
  margin-top: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-item {
  text-align: center;
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.chart-container {
  margin-top: 16px;
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 20px;
}
</style>
