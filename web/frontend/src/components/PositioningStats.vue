<template>
  <div class="positioning-stats">
    <div v-if="loading" class="stats-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else class="stats-content">
      <!-- 关键指标 -->
      <div class="metrics-grid">
        <div class="metric-item">
          <div class="metric-icon">
            <el-icon><Location /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ formatAccuracy(stats.averageAccuracy || 0) }}</div>
            <div class="metric-label">平均精度</div>
          </div>
        </div>
        
        <div class="metric-item">
          <div class="metric-icon">
            <el-icon><View /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ formatPercentage(stats.coverageRatio || 0) }}</div>
            <div class="metric-label">覆盖率</div>
          </div>
        </div>
        
        <div class="metric-item">
          <div class="metric-icon">
            <el-icon><DataAnalysis /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ formatGdop(stats.averageGdop || 0) }}</div>
            <div class="metric-label">平均GDOP</div>
          </div>
        </div>
        
        <div class="metric-item">
          <div class="metric-icon">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ stats.visibleSatellitesCount || 0 }}</div>
            <div class="metric-label">可见卫星</div>
          </div>
        </div>
      </div>

      <!-- 质量评估 -->
      <div class="quality-section">
        <h4>定位质量评估</h4>
        <div class="quality-bars">
          <div class="quality-item">
            <span class="quality-label">精度等级</span>
            <div class="quality-bar">
              <el-progress
                :percentage="getAccuracyScore(stats.averageAccuracy || 0)"
                :stroke-width="12"
                :show-text="false"
                :color="getQualityColor(getAccuracyScore(stats.averageAccuracy || 0))"
              />
              <span class="quality-text">{{ getAccuracyGrade(stats.averageAccuracy || 0) }}</span>
            </div>
          </div>
          
          <div class="quality-item">
            <span class="quality-label">GDOP等级</span>
            <div class="quality-bar">
              <el-progress
                :percentage="getGdopScore(stats.averageGdop || 0)"
                :stroke-width="12"
                :show-text="false"
                :color="getQualityColor(getGdopScore(stats.averageGdop || 0))"
              />
              <span class="quality-text">{{ getGdopGrade(stats.averageGdop || 0) }}</span>
            </div>
          </div>
          
          <div class="quality-item">
            <span class="quality-label">覆盖等级</span>
            <div class="quality-bar">
              <el-progress
                :percentage="(stats.coverageRatio || 0) * 100"
                :stroke-width="12"
                :show-text="false"
                :color="getQualityColor((stats.coverageRatio || 0) * 100)"
              />
              <span class="quality-text">{{ getCoverageGrade(stats.coverageRatio || 0) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史趋势 -->
      <div class="trend-section">
        <h4>精度趋势</h4>
        <div ref="trendChartRef" class="trend-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { 
  Loading, 
  Location, 
  View, 
  DataAnalysis, 
  Connection 
} from '@element-plus/icons-vue'
import { positioningApi } from '@/api/admission'

interface Props {
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const trendChartRef = ref<HTMLElement>()
const stats = ref<any>({})
let trendChart: echarts.ECharts | null = null

// 方法
const loadStats = async () => {
  try {
    stats.value = await positioningApi.getStatistics()
    updateTrendChart()
  } catch (error) {
    console.error('加载定位统计失败:', error)
  }
}

const formatAccuracy = (accuracy: number) => {
  if (accuracy < 1) {
    return `${(accuracy * 1000).toFixed(0)}mm`
  } else if (accuracy < 1000) {
    return `${accuracy.toFixed(1)}m`
  } else {
    return `${(accuracy / 1000).toFixed(1)}km`
  }
}

const formatPercentage = (value: number) => {
  return `${(value * 100).toFixed(1)}%`
}

const formatGdop = (gdop: number) => {
  return gdop.toFixed(2)
}

const getAccuracyScore = (accuracy: number) => {
  // 精度越小越好，转换为分数
  if (accuracy <= 1) return 100
  if (accuracy <= 5) return 80
  if (accuracy <= 10) return 60
  if (accuracy <= 50) return 40
  return 20
}

const getGdopScore = (gdop: number) => {
  // GDOP越小越好
  if (gdop <= 2) return 100
  if (gdop <= 5) return 80
  if (gdop <= 10) return 60
  if (gdop <= 20) return 40
  return 20
}

const getQualityColor = (score: number) => {
  if (score >= 80) return '#67C23A'
  if (score >= 60) return '#E6A23C'
  return '#F56C6C'
}

const getAccuracyGrade = (accuracy: number) => {
  if (accuracy <= 1) return '优秀'
  if (accuracy <= 5) return '良好'
  if (accuracy <= 10) return '一般'
  if (accuracy <= 50) return '较差'
  return '很差'
}

const getGdopGrade = (gdop: number) => {
  if (gdop <= 2) return '优秀'
  if (gdop <= 5) return '良好'
  if (gdop <= 10) return '一般'
  if (gdop <= 20) return '较差'
  return '很差'
}

const getCoverageGrade = (coverage: number) => {
  if (coverage >= 0.9) return '优秀'
  if (coverage >= 0.8) return '良好'
  if (coverage >= 0.7) return '一般'
  if (coverage >= 0.5) return '较差'
  return '很差'
}

const initTrendChart = () => {
  if (!trendChartRef.value) return

  trendChart = echarts.init(trendChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const time = new Date(params[0].axisValue).toLocaleTimeString()
        return `${time}<br/>精度: ${params[0].value.toFixed(2)}m`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'time',
      axisLabel: {
        formatter: (value: number) => {
          return new Date(value).toLocaleTimeString()
        },
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: '精度 (m)',
      axisLabel: {
        formatter: '{value}',
        fontSize: 10
      }
    },
    series: [
      {
        name: '定位精度',
        type: 'line',
        data: [],
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#409EFF'
        },
        areaStyle: {
          opacity: 0.1,
          color: '#409EFF'
        }
      }
    ]
  }
  
  trendChart.setOption(option)
}

const updateTrendChart = () => {
  if (!trendChart) return

  // 生成模拟趋势数据
  const now = Date.now()
  const data = []
  for (let i = 29; i >= 0; i--) {
    const time = now - i * 60000 // 每分钟一个点
    const accuracy = 2 + Math.random() * 3 // 2-5米的随机精度
    data.push([time, accuracy])
  }

  trendChart.setOption({
    series: [{
      data: data
    }]
  })
}

const resizeChart = () => {
  if (trendChart) {
    trendChart.resize()
  }
}

// 生命周期
onMounted(() => {
  loadStats()
  
  nextTick(() => {
    initTrendChart()
    updateTrendChart()
  })
  
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  if (trendChart) {
    trendChart.dispose()
  }
  window.removeEventListener('resize', resizeChart)
})

// 定期刷新数据
const refreshTimer = setInterval(loadStats, 15000) // 每15秒刷新

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style scoped>
.positioning-stats {
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
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
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.metric-info {
  flex: 1;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 2px;
}

.metric-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.quality-section h4,
.trend-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.quality-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quality-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quality-label {
  width: 80px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.quality-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.quality-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  min-width: 40px;
}

.trend-chart {
  height: 120px;
  width: 100%;
}
</style>
