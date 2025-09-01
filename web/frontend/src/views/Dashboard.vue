<template>
  <div class="dashboard">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="24">
        <h1 class="page-title">
          <el-icon><DataBoard /></el-icon>
          系统仪表板
        </h1>
      </el-col>
    </el-row>

    <!-- 关键指标卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :xs="24" :sm="12" :md="6">
        <MetricCard
          title="仿真状态"
          :value="simulationStatusText"
          :type="simulationStatusType"
          icon="VideoPlay"
          :loading="simulationStore.loading"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <MetricCard
          title="平均吞吐量"
          :value="formatThroughput(averageMetrics?.averageThroughput || 0)"
          type="primary"
          icon="TrendCharts"
          :loading="simulationStore.loading"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <MetricCard
          title="平均延迟"
          :value="formatLatency(averageMetrics?.averageLatency || 0)"
          type="warning"
          icon="Timer"
          :loading="simulationStore.loading"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <MetricCard
          title="QoE评分"
          :value="formatQoE(averageMetrics?.qoeScore || 0)"
          type="success"
          icon="Star"
          :loading="simulationStore.loading"
        />
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="mb-4">
      <!-- 性能趋势图 -->
      <el-col :xs="24" :lg="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>性能趋势</span>
              <div class="header-actions">
                <el-button-group size="small">
                  <el-button 
                    :type="timeRange === '1h' ? 'primary' : ''"
                    @click="setTimeRange('1h')"
                  >
                    1小时
                  </el-button>
                  <el-button 
                    :type="timeRange === '6h' ? 'primary' : ''"
                    @click="setTimeRange('6h')"
                  >
                    6小时
                  </el-button>
                  <el-button 
                    :type="timeRange === '24h' ? 'primary' : ''"
                    @click="setTimeRange('24h')"
                  >
                    24小时
                  </el-button>
                </el-button-group>
                <el-button 
                  :icon="Refresh" 
                  size="small" 
                  @click="refreshCharts"
                  :loading="chartLoading"
                />
              </div>
            </div>
          </template>
          <PerformanceChart 
            :data="chartData" 
            :loading="chartLoading"
            height="300px"
          />
        </el-card>
      </el-col>

      <!-- 系统状态 -->
      <el-col :xs="24" :lg="8">
        <el-card class="status-card">
          <template #header>
            <span>系统状态</span>
          </template>
          <div class="status-content">
            <div class="status-item">
              <div class="status-label">连接状态</div>
              <div class="status-value">
                <el-tag :type="connectionStatusType" size="small">
                  {{ connectionStatusText }}
                </el-tag>
              </div>
            </div>
            <div class="status-item">
              <div class="status-label">仿真时间</div>
              <div class="status-value">{{ formatTime(simulationStore.currentTime) }}</div>
            </div>
            <div class="status-item">
              <div class="status-label">仿真进度</div>
              <div class="status-value">
                <el-progress 
                  :percentage="simulationStore.progress" 
                  :stroke-width="8"
                  :show-text="false"
                />
                <span class="progress-text">{{ simulationStore.progress.toFixed(1) }}%</span>
              </div>
            </div>
            <div class="status-item">
              <div class="status-label">剩余时间</div>
              <div class="status-value">{{ formatTime(simulationStore.remainingTime) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细统计 -->
    <el-row :gutter="20">
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <span>准入控制统计</span>
          </template>
          <AdmissionStats :loading="statsLoading" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <span>定位服务统计</span>
          </template>
          <PositioningStats :loading="statsLoading" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时日志 -->
    <el-row :gutter="20" class="mt-4">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>实时日志</span>
              <el-button 
                size="small" 
                @click="clearLogs"
                :icon="Delete"
              >
                清空
              </el-button>
            </div>
          </template>
          <LogViewer 
            :logs="logs" 
            :max-lines="100"
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
import MetricCard from '@/components/MetricCard.vue'
import PerformanceChart from '@/components/PerformanceChart.vue'
import AdmissionStats from '@/components/AdmissionStats.vue'
import PositioningStats from '@/components/PositioningStats.vue'
import LogViewer from '@/components/LogViewer.vue'
import { DataBoard, Refresh, Delete } from '@element-plus/icons-vue'

// 状态管理
const simulationStore = useSimulationStore()
const websocketStore = useWebSocketStore()
const appStore = useAppStore()

// 响应式数据
const timeRange = ref('1h')
const chartLoading = ref(false)
const statsLoading = ref(false)
const logs = ref<Array<{ timestamp: number; level: string; message: string }>>([])

// 计算属性
const simulationStatusText = computed(() => {
  if (simulationStore.isRunning) return '运行中'
  return '未运行'
})

const simulationStatusType = computed(() => {
  if (simulationStore.isRunning) return 'success'
  return 'info'
})

const connectionStatusType = computed(() => {
  if (websocketStore.isConnected) return 'success'
  return 'danger'
})

const connectionStatusText = computed(() => {
  if (websocketStore.isConnected) return '已连接'
  return '未连接'
})

const averageMetrics = computed(() => simulationStore.averageMetrics)

const chartData = computed(() => {
  const history = simulationStore.performanceHistory
  if (!history.length) return []
  
  return history.map(metrics => ({
    timestamp: metrics.timeStep,
    throughput: metrics.averageThroughput,
    latency: metrics.averageLatency,
    qoe: metrics.qoeScore,
    admissionRate: metrics.admissionRate
  }))
})

// 方法
const formatThroughput = (value: number) => {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)} Gbps`
  }
  return `${value.toFixed(1)} Mbps`
}

const formatLatency = (value: number) => {
  return `${value.toFixed(1)} ms`
}

const formatQoE = (value: number) => {
  return value.toFixed(2)
}

const formatTime = (seconds: number) => {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }
}

const setTimeRange = (range: string) => {
  timeRange.value = range
  refreshCharts()
}

const refreshCharts = async () => {
  chartLoading.value = true
  try {
    await simulationStore.fetchPerformanceMetrics()
  } finally {
    chartLoading.value = false
  }
}

const clearLogs = () => {
  logs.value = []
}

const addLog = (level: string, message: string) => {
  logs.value.unshift({
    timestamp: Date.now(),
    level,
    message
  })
  
  // 限制日志数量
  if (logs.value.length > 100) {
    logs.value = logs.value.slice(0, 100)
  }
}

// 生命周期
onMounted(async () => {
  // 获取初始数据
  await simulationStore.fetchStatus()
  await simulationStore.fetchPerformanceMetrics()
  
  // 订阅WebSocket事件
  if (websocketStore.isConnected) {
    websocketStore.subscribe('simulation')
  }
  
  // 监听WebSocket连接状态
  watch(() => websocketStore.isConnected, (connected) => {
    if (connected) {
      websocketStore.subscribe('simulation')
      addLog('info', 'WebSocket连接已建立')
    } else {
      addLog('warning', 'WebSocket连接已断开')
    }
  })
  
  // 监听仿真状态变化
  watch(() => simulationStore.isRunning, (running) => {
    if (running) {
      addLog('success', '仿真已启动')
    } else {
      addLog('info', '仿真已停止')
    }
  })
  
  // 定期刷新数据
  const refreshTimer = setInterval(() => {
    if (simulationStore.isRunning) {
      simulationStore.fetchPerformanceMetrics()
    }
  }, 5000)
  
  onUnmounted(() => {
    clearInterval(refreshTimer)
  })
})
</script>

<style scoped>
.dashboard {
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

.chart-card {
  height: 400px;
}

.status-card {
  height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.status-value {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.progress-text {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 20px;
}
</style>
