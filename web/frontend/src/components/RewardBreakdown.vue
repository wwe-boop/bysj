<template>
  <div class="reward-breakdown">
    <div v-if="loading" class="breakdown-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载奖励分解中...</span>
    </div>
    <div v-else class="breakdown-content">
      <!-- 权重配置 -->
      <div class="weights-section">
        <h4>奖励权重配置</h4>
        <div class="weights-grid">
          <div
            v-for="(weight, key) in weights"
            :key="key"
            class="weight-item"
            :class="getWeightClass(weight)"
          >
            <div class="weight-header">
              <span class="weight-name">{{ getWeightDisplayName(key) }}</span>
              <span class="weight-value">{{ (weight * 100).toFixed(1) }}%</span>
            </div>
            <el-progress
              :percentage="weight * 100"
              :stroke-width="8"
              :show-text="false"
              :color="getWeightColor(key)"
            />
          </div>
        </div>
      </div>

      <!-- 奖励组件详情 -->
      <div class="components-section">
        <h4>奖励组件详情</h4>
        <div class="components-list">
          <div
            v-for="(component, key) in components"
            :key="key"
            class="component-item"
            :class="{ disabled: !component.enabled }"
          >
            <div class="component-header">
              <div class="component-title">
                <el-icon>
                  <component :is="getComponentIcon(key)" />
                </el-icon>
                <span class="component-name">{{ component.description || getWeightDisplayName(key) }}</span>
                <el-tag
                  :type="component.enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ component.enabled ? '启用' : '禁用' }}
                </el-tag>
              </div>
              <div class="component-weight">
                权重: {{ (weights[key] * 100).toFixed(1) }}%
              </div>
            </div>
            <div class="component-formula">
              <span class="formula-label">计算公式:</span>
              <code class="formula-code">{{ component.formula || 'N/A' }}</code>
            </div>
            <div class="component-metrics">
              <div class="metric-item">
                <span class="metric-label">当前值:</span>
                <span class="metric-value">{{ formatMetricValue(key, getCurrentValue(key)) }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">贡献度:</span>
                <span class="metric-value">{{ formatContribution(key) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 奖励趋势 -->
      <div class="trend-section">
        <h4>奖励组件趋势</h4>
        <div ref="rewardTrendRef" class="reward-trend-chart"></div>
      </div>

      <!-- 奖励统计 -->
      <div class="stats-section">
        <h4>奖励统计</h4>
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-value">{{ formatReward(totalReward) }}</div>
              <div class="stat-label">总奖励</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-value">{{ formatReward(averageReward) }}</div>
              <div class="stat-label">平均奖励</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-value">{{ formatReward(maxReward) }}</div>
              <div class="stat-label">最大奖励</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-value">{{ formatReward(minReward) }}</div>
              <div class="stat-label">最小奖励</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import {
  Loading,
  TrendCharts,
  Balance,
  Odometer,
  Connection,
  Location
} from '@element-plus/icons-vue'

interface Props {
  weights: Record<string, number>
  components: Record<string, any>
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const rewardTrendRef = ref<HTMLElement>()
let rewardTrendChart: echarts.ECharts | null = null

// 模拟当前值和历史数据
const currentValues = ref({
  qoe_weight: 0.75,
  fairness_weight: 0.68,
  efficiency_weight: 0.82,
  stability_weight: 0.71,
  positioning_weight: 0.79
})

const rewardHistory = ref({
  episodes: Array.from({ length: 50 }, (_, i) => i + 1),
  qoe: Array.from({ length: 50 }, () => Math.random() * 0.4 + 0.1),
  fairness: Array.from({ length: 50 }, () => Math.random() * 0.3 + 0.1),
  efficiency: Array.from({ length: 50 }, () => Math.random() * 0.3 + 0.1),
  stability: Array.from({ length: 50 }, () => Math.random() * 0.2 + 0.05),
  positioning: Array.from({ length: 50 }, () => Math.random() * 0.2 + 0.05)
})

// 计算属性
const totalReward = computed(() => {
  return Object.keys(props.weights).reduce((sum, key) => {
    const weight = props.weights[key] || 0
    const value = currentValues.value[key as keyof typeof currentValues.value] || 0
    return sum + weight * value
  }, 0)
})

const averageReward = computed(() => {
  const history = rewardHistory.value
  const totalEpisodes = history.episodes.length
  if (totalEpisodes === 0) return 0
  
  let sum = 0
  for (let i = 0; i < totalEpisodes; i++) {
    sum += Object.keys(props.weights).reduce((episodeSum, key) => {
      const weight = props.weights[key] || 0
      const historyKey = key.replace('_weight', '') as keyof typeof history
      const value = history[historyKey]?.[i] || 0
      return episodeSum + weight * value
    }, 0)
  }
  
  return sum / totalEpisodes
})

const maxReward = computed(() => {
  return Math.max(...rewardHistory.value.episodes.map((_, i) => {
    return Object.keys(props.weights).reduce((sum, key) => {
      const weight = props.weights[key] || 0
      const historyKey = key.replace('_weight', '') as keyof typeof rewardHistory.value
      const value = rewardHistory.value[historyKey]?.[i] || 0
      return sum + weight * value
    }, 0)
  }))
})

const minReward = computed(() => {
  return Math.min(...rewardHistory.value.episodes.map((_, i) => {
    return Object.keys(props.weights).reduce((sum, key) => {
      const weight = props.weights[key] || 0
      const historyKey = key.replace('_weight', '') as keyof typeof rewardHistory.value
      const value = rewardHistory.value[historyKey]?.[i] || 0
      return sum + weight * value
    }, 0)
  }))
})

// 方法
const getWeightDisplayName = (key: string) => {
  const nameMap: Record<string, string> = {
    'qoe_weight': 'QoE质量',
    'fairness_weight': '公平性',
    'efficiency_weight': '效率',
    'stability_weight': '稳定性',
    'positioning_weight': '定位质量'
  }
  return nameMap[key] || key
}

const getWeightClass = (weight: number) => {
  if (weight >= 0.3) return 'weight-high'
  if (weight >= 0.15) return 'weight-medium'
  return 'weight-low'
}

const getWeightColor = (key: string) => {
  const colorMap: Record<string, string> = {
    'qoe_weight': '#409EFF',
    'fairness_weight': '#67C23A',
    'efficiency_weight': '#E6A23C',
    'stability_weight': '#F56C6C',
    'positioning_weight': '#909399'
  }
  return colorMap[key] || '#409EFF'
}

const getComponentIcon = (key: string) => {
  const iconMap: Record<string, any> = {
    'qoe_weight': TrendCharts,
    'fairness_weight': Balance,
    'efficiency_weight': Odometer,
    'stability_weight': Connection,
    'positioning_weight': Location
  }
  return iconMap[key] || TrendCharts
}

const getCurrentValue = (key: string) => {
  return currentValues.value[key as keyof typeof currentValues.value] || 0
}

const formatMetricValue = (key: string, value: number) => {
  return value.toFixed(3)
}

const formatContribution = (key: string) => {
  const weight = props.weights[key] || 0
  const value = getCurrentValue(key)
  const contribution = weight * value
  return `${contribution.toFixed(4)} (${((contribution / totalReward.value) * 100).toFixed(1)}%)`
}

const formatReward = (reward: number) => {
  return reward.toFixed(4)
}

const initRewardTrendChart = () => {
  if (!rewardTrendRef.value) return

  rewardTrendChart = echarts.init(rewardTrendRef.value)
  
  const option = {
    title: {
      text: '奖励组件贡献趋势',
      left: 'center',
      textStyle: {
        fontSize: 14,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['QoE', '公平性', '效率', '稳定性', '定位'],
      top: 25,
      textStyle: {
        fontSize: 12
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: 'Episode',
      data: rewardHistory.value.episodes,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: 'Reward Contribution',
      axisLabel: {
        fontSize: 10
      }
    },
    series: [
      {
        name: 'QoE',
        type: 'line',
        data: rewardHistory.value.qoe.map((v, i) => v * (props.weights.qoe_weight || 0)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#409EFF' }
      },
      {
        name: '公平性',
        type: 'line',
        data: rewardHistory.value.fairness.map((v, i) => v * (props.weights.fairness_weight || 0)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#67C23A' }
      },
      {
        name: '效率',
        type: 'line',
        data: rewardHistory.value.efficiency.map((v, i) => v * (props.weights.efficiency_weight || 0)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#E6A23C' }
      },
      {
        name: '稳定性',
        type: 'line',
        data: rewardHistory.value.stability.map((v, i) => v * (props.weights.stability_weight || 0)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#F56C6C' }
      },
      {
        name: '定位',
        type: 'line',
        data: rewardHistory.value.positioning.map((v, i) => v * (props.weights.positioning_weight || 0)),
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#909399' }
      }
    ]
  }
  
  rewardTrendChart.setOption(option)
}

const resizeChart = () => {
  if (rewardTrendChart) {
    rewardTrendChart.resize()
  }
}

// 监听权重变化
watch(() => props.weights, () => {
  if (rewardTrendChart) {
    // 更新图表数据
    const series = [
      { data: rewardHistory.value.qoe.map(v => v * (props.weights.qoe_weight || 0)) },
      { data: rewardHistory.value.fairness.map(v => v * (props.weights.fairness_weight || 0)) },
      { data: rewardHistory.value.efficiency.map(v => v * (props.weights.efficiency_weight || 0)) },
      { data: rewardHistory.value.stability.map(v => v * (props.weights.stability_weight || 0)) },
      { data: rewardHistory.value.positioning.map(v => v * (props.weights.positioning_weight || 0)) }
    ]
    rewardTrendChart.setOption({ series })
  }
}, { deep: true })

// 生命周期
onMounted(() => {
  nextTick(() => {
    initRewardTrendChart()
  })
  
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  if (rewardTrendChart) {
    rewardTrendChart.dispose()
  }
  window.removeEventListener('resize', resizeChart)
})
</script>

<style scoped>
.reward-breakdown {
  height: 100%;
}

.breakdown-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.breakdown-loading .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
  color: var(--el-color-primary);
}

.breakdown-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.weights-section h4,
.components-section h4,
.trend-section h4,
.stats-section h4 {
  margin: 0 0 12px 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding-bottom: 8px;
}

.weights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.weight-item {
  padding: 12px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  border-left: 4px solid var(--el-color-primary);
}

.weight-item.weight-high {
  border-left-color: var(--el-color-success);
}

.weight-item.weight-medium {
  border-left-color: var(--el-color-warning);
}

.weight-item.weight-low {
  border-left-color: var(--el-color-info);
}

.weight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.weight-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.weight-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.components-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.component-item {
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
}

.component-item.disabled {
  opacity: 0.6;
}

.component-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.component-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.component-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.component-weight {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.component-formula {
  margin-bottom: 8px;
}

.formula-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-right: 8px;
}

.formula-code {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--el-color-primary);
}

.component-metrics {
  display: flex;
  gap: 20px;
}

.metric-item {
  display: flex;
  gap: 8px;
}

.metric-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.metric-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.reward-trend-chart {
  height: 300px;
  width: 100%;
}

.stat-card {
  text-align: center;
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
</style>
