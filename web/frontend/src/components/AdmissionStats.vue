<template>
  <div class="admission-stats">
    <div v-if="loading" class="stats-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else class="stats-content">
      <!-- 统计卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ stats.totalRequests || 0 }}</div>
          <div class="stat-label">总请求数</div>
        </div>
        <div class="stat-card success">
          <div class="stat-value">{{ stats.acceptedRequests || 0 }}</div>
          <div class="stat-label">接受请求</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-value">{{ stats.rejectedRequests || 0 }}</div>
          <div class="stat-label">拒绝请求</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-value">{{ stats.degradedRequests || 0 }}</div>
          <div class="stat-label">降级请求</div>
        </div>
      </div>

      <!-- 成功率指标 -->
      <div class="rate-section">
        <div class="rate-item">
          <span class="rate-label">准入成功率</span>
          <div class="rate-progress">
            <el-progress
              :percentage="acceptanceRate"
              :stroke-width="8"
              :show-text="false"
              :color="getProgressColor(acceptanceRate)"
            />
            <span class="rate-text">{{ acceptanceRate.toFixed(1) }}%</span>
          </div>
        </div>
        <div class="rate-item">
          <span class="rate-label">平均决策时间</span>
          <div class="rate-value">
            {{ formatDecisionTime(stats.averageDecisionTime || 0) }}
          </div>
        </div>
      </div>

      <!-- 分布饼图 -->
      <div class="chart-section">
        <div ref="chartRef" class="pie-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'
import { admissionApi } from '@/api/admission'
import type { AdmissionStatistics } from '@/types'

interface Props {
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const chartRef = ref<HTMLElement>()
const stats = ref<Partial<AdmissionStatistics>>({})
let chart: echarts.ECharts | null = null

// 计算属性
const acceptanceRate = computed(() => {
  const total = stats.value.totalRequests || 0
  const accepted = stats.value.acceptedRequests || 0
  return total > 0 ? (accepted / total) * 100 : 0
})

// 方法
const loadStats = async () => {
  try {
    stats.value = await admissionApi.getStatistics()
    updateChart()
  } catch (error) {
    console.error('加载准入统计失败:', error)
  }
}

const formatDecisionTime = (time: number) => {
  if (time < 1) {
    return `${(time * 1000).toFixed(1)}ms`
  }
  return `${time.toFixed(2)}s`
}

const getProgressColor = (percentage: number) => {
  if (percentage >= 80) return '#67C23A'
  if (percentage >= 60) return '#E6A23C'
  return '#F56C6C'
}

const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)
  
  const option = {
    title: {
      text: '请求分布',
      left: 'center',
      textStyle: {
        fontSize: 14,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 10,
      textStyle: {
        fontSize: 12
      }
    },
    series: [
      {
        name: '准入请求',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '16',
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: []
      }
    ]
  }
  
  chart.setOption(option)
}

const updateChart = () => {
  if (!chart) return

  const data = [
    {
      value: stats.value.acceptedRequests || 0,
      name: '接受',
      itemStyle: { color: '#67C23A' }
    },
    {
      value: stats.value.rejectedRequests || 0,
      name: '拒绝',
      itemStyle: { color: '#F56C6C' }
    },
    {
      value: stats.value.degradedRequests || 0,
      name: '降级',
      itemStyle: { color: '#E6A23C' }
    }
  ]

  chart.setOption({
    series: [{
      data: data.filter(item => item.value > 0)
    }]
  })
}

const resizeChart = () => {
  if (chart) {
    chart.resize()
  }
}

// 生命周期
onMounted(() => {
  loadStats()
  
  nextTick(() => {
    initChart()
    updateChart()
  })
  
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
  }
  window.removeEventListener('resize', resizeChart)
})

// 定期刷新数据
const refreshTimer = setInterval(loadStats, 10000) // 每10秒刷新

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style scoped>
.admission-stats {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.stats-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.stats-loading .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
  color: var(--el-color-primary);
}

.stats-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-card {
  padding: 12px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  text-align: center;
  border-left: 4px solid var(--el-color-primary);
}

.stat-card.success {
  border-left-color: var(--el-color-success);
}

.stat-card.danger {
  border-left-color: var(--el-color-danger);
}

.stat-card.warning {
  border-left-color: var(--el-color-warning);
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.rate-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rate-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.rate-label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.rate-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  max-width: 150px;
}

.rate-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  min-width: 40px;
}

.rate-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.chart-section {
  flex: 1;
  min-height: 200px;
}

.pie-chart {
  width: 100%;
  height: 100%;
}
</style>
