<template>
  <div class="drl-environment-state">
    <div v-if="loading" class="state-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载环境状态中...</span>
    </div>
    <div v-else class="state-content">
      <!-- 网络状态 -->
      <div class="state-section">
        <h4>网络状态</h4>
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="state-metric">
              <div class="metric-value">{{ state.networkState?.satelliteCount || 0 }}</div>
              <div class="metric-label">卫星数量</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="state-metric">
              <div class="metric-value">{{ state.networkState?.activeFlows || 0 }}</div>
              <div class="metric-label">活跃流量</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="state-metric">
              <div class="metric-value">{{ formatTime(state.networkState?.timestamp) }}</div>
              <div class="metric-label">时间戳</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 资源利用率 -->
      <div class="state-section">
        <h4>资源利用率</h4>
        <div class="utilization-display">
          <div class="utilization-item">
            <span class="label">总容量:</span>
            <span class="value">{{ formatCapacity(state.resourceUtilization?.totalCapacity) }}</span>
          </div>
          <div class="utilization-item">
            <span class="label">已用容量:</span>
            <span class="value">{{ formatCapacity(state.resourceUtilization?.usedCapacity) }}</span>
          </div>
          <div class="utilization-item">
            <span class="label">利用率:</span>
            <el-progress
              :percentage="(state.resourceUtilization?.utilizationRate || 0) * 100"
              :stroke-width="8"
              :show-text="false"
              :color="getUtilizationColor(state.resourceUtilization?.utilizationRate || 0)"
            />
            <span class="percentage-text">
              {{ formatPercentage(state.resourceUtilization?.utilizationRate) }}
            </span>
          </div>
        </div>
      </div>

      <!-- 定位质量 -->
      <div class="state-section">
        <h4>定位质量</h4>
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="quality-metric">
              <div class="metric-icon">
                <el-icon><Location /></el-icon>
              </div>
              <div class="metric-info">
                <div class="metric-value">{{ formatGdop(state.positioningQuality?.averageGdop) }}</div>
                <div class="metric-label">平均GDOP</div>
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="quality-metric">
              <div class="metric-icon">
                <el-icon><View /></el-icon>
              </div>
              <div class="metric-info">
                <div class="metric-value">{{ formatPercentage(state.positioningQuality?.coverageRatio) }}</div>
                <div class="metric-label">覆盖率</div>
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="quality-metric">
              <div class="metric-icon">
                <el-icon><Aim /></el-icon>
              </div>
              <div class="metric-info">
                <div class="metric-value">{{ formatAccuracy(state.positioningQuality?.averageAccuracy) }}</div>
                <div class="metric-label">平均精度</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 历史指标趋势 -->
      <div class="state-section">
        <h4>历史指标趋势</h4>
        <div class="trend-charts">
          <div class="trend-item">
            <div class="trend-title">QoE趋势</div>
            <div ref="qoeTrendRef" class="trend-chart"></div>
          </div>
          <div class="trend-item">
            <div class="trend-title">准入率趋势</div>
            <div ref="admissionTrendRef" class="trend-chart"></div>
          </div>
          <div class="trend-item">
            <div class="trend-title">吞吐量趋势</div>
            <div ref="throughputTrendRef" class="trend-chart"></div>
          </div>
        </div>
      </div>

      <!-- 状态向量 -->
      <div class="state-section">
        <h4>状态向量 (DRL输入)</h4>
        <div class="state-vector">
          <el-table
            :data="stateVectorData"
            size="small"
            stripe
            style="width: 100%"
            max-height="200"
          >
            <el-table-column prop="name" label="特征名称" width="200" />
            <el-table-column prop="value" label="当前值" width="120">
              <template #default="{ row }">
                <span :class="getValueClass(row.type)">{{ formatValue(row.value, row.type) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="normalized" label="归一化值" width="120">
              <template #default="{ row }">
                {{ row.normalized?.toFixed(4) || 'N/A' }}
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { Loading, Location, View, Aim } from '@element-plus/icons-vue'

interface Props {
  state: any
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const qoeTrendRef = ref<HTMLElement>()
const admissionTrendRef = ref<HTMLElement>()
const throughputTrendRef = ref<HTMLElement>()

let qoeTrendChart: echarts.ECharts | null = null
let admissionTrendChart: echarts.ECharts | null = null
let throughputTrendChart: echarts.ECharts | null = null

// 计算属性
const stateVectorData = computed(() => {
  const networkState = props.state.networkState || {}
  const resourceUtil = props.state.resourceUtilization || {}
  const positioningQuality = props.state.positioningQuality || {}
  
  return [
    {
      name: '卫星数量',
      value: networkState.satelliteCount || 0,
      normalized: (networkState.satelliteCount || 0) / 100,
      type: 'integer',
      description: '当前可见卫星数量'
    },
    {
      name: '活跃流量数',
      value: networkState.activeFlows || 0,
      normalized: (networkState.activeFlows || 0) / 1000,
      type: 'integer',
      description: '当前活跃的数据流数量'
    },
    {
      name: '资源利用率',
      value: resourceUtil.utilizationRate || 0,
      normalized: resourceUtil.utilizationRate || 0,
      type: 'percentage',
      description: '系统资源利用率'
    },
    {
      name: '平均GDOP',
      value: positioningQuality.averageGdop || 0,
      normalized: Math.min((positioningQuality.averageGdop || 0) / 10, 1),
      type: 'float',
      description: '几何精度因子'
    },
    {
      name: '覆盖率',
      value: positioningQuality.coverageRatio || 0,
      normalized: positioningQuality.coverageRatio || 0,
      type: 'percentage',
      description: '定位服务覆盖率'
    },
    {
      name: '平均精度',
      value: positioningQuality.averageAccuracy || 0,
      normalized: Math.max(1 - (positioningQuality.averageAccuracy || 0) / 100, 0),
      type: 'float',
      description: '定位精度(米)'
    }
  ]
})

// 方法
const formatTime = (timestamp: number) => {
  if (!timestamp) return 'N/A'
  return new Date(timestamp * 1000).toLocaleTimeString()
}

const formatCapacity = (capacity: number) => {
  if (!capacity) return '0 Mbps'
  if (capacity >= 1000) {
    return `${(capacity / 1000).toFixed(1)} Gbps`
  }
  return `${capacity.toFixed(0)} Mbps`
}

const formatPercentage = (value: number) => {
  if (value === undefined || value === null) return '0%'
  return `${(value * 100).toFixed(1)}%`
}

const formatGdop = (gdop: number) => {
  return gdop?.toFixed(2) || '0.00'
}

const formatAccuracy = (accuracy: number) => {
  if (!accuracy) return '0m'
  return `${accuracy.toFixed(1)}m`
}

const formatValue = (value: any, type: string) => {
  if (value === undefined || value === null) return 'N/A'
  
  switch (type) {
    case 'integer':
      return value.toString()
    case 'float':
      return value.toFixed(2)
    case 'percentage':
      return `${(value * 100).toFixed(1)}%`
    default:
      return value.toString()
  }
}

const getValueClass = (type: string) => {
  return {
    'value-integer': type === 'integer',
    'value-float': type === 'float',
    'value-percentage': type === 'percentage'
  }
}

const getUtilizationColor = (rate: number) => {
  if (rate < 0.6) return '#67C23A'
  if (rate < 0.8) return '#E6A23C'
  return '#F56C6C'
}

const initTrendCharts = () => {
  const historicalMetrics = props.state.historicalMetrics || {}
  
  // QoE趋势图
  if (qoeTrendRef.value && historicalMetrics.recentQoE) {
    qoeTrendChart = echarts.init(qoeTrendRef.value)
    qoeTrendChart.setOption({
      grid: { left: 10, right: 10, top: 10, bottom: 20 },
      xAxis: { type: 'category', show: false },
      yAxis: { type: 'value', show: false, min: 0, max: 1 },
      series: [{
        type: 'line',
        data: historicalMetrics.recentQoE,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#409EFF', width: 2 },
        areaStyle: { color: 'rgba(64, 158, 255, 0.1)' }
      }]
    })
  }
  
  // 准入率趋势图
  if (admissionTrendRef.value && historicalMetrics.recentAdmissionRate) {
    admissionTrendChart = echarts.init(admissionTrendRef.value)
    admissionTrendChart.setOption({
      grid: { left: 10, right: 10, top: 10, bottom: 20 },
      xAxis: { type: 'category', show: false },
      yAxis: { type: 'value', show: false, min: 0, max: 1 },
      series: [{
        type: 'line',
        data: historicalMetrics.recentAdmissionRate,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#67C23A', width: 2 },
        areaStyle: { color: 'rgba(103, 194, 58, 0.1)' }
      }]
    })
  }
  
  // 吞吐量趋势图
  if (throughputTrendRef.value && historicalMetrics.recentThroughput) {
    throughputTrendChart = echarts.init(throughputTrendRef.value)
    throughputTrendChart.setOption({
      grid: { left: 10, right: 10, top: 10, bottom: 20 },
      xAxis: { type: 'category', show: false },
      yAxis: { type: 'value', show: false },
      series: [{
        type: 'line',
        data: historicalMetrics.recentThroughput,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#E6A23C', width: 2 },
        areaStyle: { color: 'rgba(230, 162, 60, 0.1)' }
      }]
    })
  }
}

const resizeCharts = () => {
  if (qoeTrendChart) qoeTrendChart.resize()
  if (admissionTrendChart) admissionTrendChart.resize()
  if (throughputTrendChart) throughputTrendChart.resize()
}

// 监听状态变化
watch(() => props.state, () => {
  if (!props.loading && props.state.historicalMetrics) {
    nextTick(() => {
      initTrendCharts()
    })
  }
}, { deep: true })

// 生命周期
onMounted(() => {
  if (!props.loading && props.state.historicalMetrics) {
    nextTick(() => {
      initTrendCharts()
    })
  }
  
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  if (qoeTrendChart) qoeTrendChart.dispose()
  if (admissionTrendChart) admissionTrendChart.dispose()
  if (throughputTrendChart) throughputTrendChart.dispose()
  window.removeEventListener('resize', resizeCharts)
})
</script>

<style scoped>
.drl-environment-state {
  height: 100%;
}

.state-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.state-loading .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
  color: var(--el-color-primary);
}

.state-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.state-section h4 {
  margin: 0 0 12px 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding-bottom: 8px;
}

.state-metric {
  text-align: center;
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.utilization-display {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.utilization-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.utilization-item .label {
  width: 80px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.utilization-item .value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.percentage-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  min-width: 40px;
}

.quality-metric {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.metric-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.metric-info {
  flex: 1;
}

.trend-charts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.trend-item {
  background: var(--el-bg-color-page);
  border-radius: 8px;
  padding: 12px;
}

.trend-title {
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
  text-align: center;
}

.trend-chart {
  height: 60px;
  width: 100%;
}

.state-vector {
  background: var(--el-bg-color-page);
  border-radius: 8px;
  padding: 12px;
}

.value-integer {
  color: var(--el-color-primary);
  font-weight: 500;
}

.value-float {
  color: var(--el-color-success);
  font-weight: 500;
}

.value-percentage {
  color: var(--el-color-warning);
  font-weight: 500;
}
</style>
