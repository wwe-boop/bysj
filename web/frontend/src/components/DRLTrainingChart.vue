<template>
  <div class="drl-training-chart" :style="{ height }">
    <div v-if="loading" class="chart-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else-if="!hasData" class="chart-empty">
      <el-icon><DocumentRemove /></el-icon>
      <span>暂无训练数据</span>
    </div>
    <div v-else class="chart-tabs">
      <el-tabs v-model="activeTab" @tab-change="updateChart">
        <el-tab-pane label="奖励曲线" name="rewards">
          <div ref="rewardChartRef" class="chart-container"></div>
        </el-tab-pane>
        <el-tab-pane label="损失曲线" name="losses">
          <div ref="lossChartRef" class="chart-container"></div>
        </el-tab-pane>
        <el-tab-pane label="性能指标" name="metrics">
          <div ref="metricsChartRef" class="chart-container"></div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { Loading, DocumentRemove } from '@element-plus/icons-vue'

interface TrainingData {
  episodes: number[]
  rewards: number[]
  losses: number[]
  qoeScores: number[]
  fairnessScores: number[]
  efficiencyScores: number[]
}

interface Props {
  data: TrainingData
  loading?: boolean
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  height: '400px'
})

const activeTab = ref('rewards')
const rewardChartRef = ref<HTMLElement>()
const lossChartRef = ref<HTMLElement>()
const metricsChartRef = ref<HTMLElement>()

let rewardChart: echarts.ECharts | null = null
let lossChart: echarts.ECharts | null = null
let metricsChart: echarts.ECharts | null = null

// 计算属性
const hasData = computed(() => {
  return props.data.episodes && props.data.episodes.length > 0
})

// 方法
const initRewardChart = () => {
  if (!rewardChartRef.value) return

  rewardChart = echarts.init(rewardChartRef.value)
  
  const option = {
    title: {
      text: '训练奖励曲线',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        const episode = params[0].axisValue
        let html = `<div><strong>Episode ${episode}</strong></div>`
        
        params.forEach((param: any) => {
          const color = param.color
          const name = param.seriesName
          const value = param.value
          
          html += `<div style="margin: 2px 0;">
            <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>
            ${name}: <strong>${value.toFixed(4)}</strong>
          </div>`
        })
        
        return html
      }
    },
    legend: {
      data: ['当前奖励', '平均奖励'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: 'Episode',
      data: props.data.episodes
    },
    yAxis: {
      type: 'value',
      name: 'Reward'
    },
    series: [
      {
        name: '当前奖励',
        type: 'line',
        data: props.data.rewards,
        smooth: false,
        symbol: 'circle',
        symbolSize: 3,
        lineStyle: {
          width: 1,
          color: '#409EFF'
        },
        itemStyle: {
          color: '#409EFF'
        }
      },
      {
        name: '平均奖励',
        type: 'line',
        data: calculateMovingAverage(props.data.rewards, 10),
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#67C23A'
        },
        itemStyle: {
          color: '#67C23A'
        }
      }
    ]
  }
  
  rewardChart.setOption(option)
}

const initLossChart = () => {
  if (!lossChartRef.value) return

  lossChart = echarts.init(lossChartRef.value)
  
  const option = {
    title: {
      text: '训练损失曲线',
      left: 'center',
      textStyle: {
        fontSize: 16,
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
      data: ['损失值', '平均损失'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: 'Episode',
      data: props.data.episodes
    },
    yAxis: {
      type: 'value',
      name: 'Loss',
      scale: true
    },
    series: [
      {
        name: '损失值',
        type: 'line',
        data: props.data.losses,
        smooth: false,
        symbol: 'circle',
        symbolSize: 3,
        lineStyle: {
          width: 1,
          color: '#F56C6C'
        },
        itemStyle: {
          color: '#F56C6C'
        }
      },
      {
        name: '平均损失',
        type: 'line',
        data: calculateMovingAverage(props.data.losses, 10),
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#E6A23C'
        },
        itemStyle: {
          color: '#E6A23C'
        }
      }
    ]
  }
  
  lossChart.setOption(option)
}

const initMetricsChart = () => {
  if (!metricsChartRef.value) return

  metricsChart = echarts.init(metricsChartRef.value)
  
  const option = {
    title: {
      text: '性能指标趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
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
      data: ['QoE评分', '公平性评分', '效率评分'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: 'Episode',
      data: props.data.episodes
    },
    yAxis: {
      type: 'value',
      name: 'Score',
      min: 0,
      max: 1
    },
    series: [
      {
        name: 'QoE评分',
        type: 'line',
        data: props.data.qoeScores,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#409EFF'
        }
      },
      {
        name: '公平性评分',
        type: 'line',
        data: props.data.fairnessScores,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#67C23A'
        }
      },
      {
        name: '效率评分',
        type: 'line',
        data: props.data.efficiencyScores,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: '#E6A23C'
        }
      }
    ]
  }
  
  metricsChart.setOption(option)
}

const calculateMovingAverage = (data: number[], window: number) => {
  const result = []
  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - window + 1)
    const end = i + 1
    const slice = data.slice(start, end)
    const average = slice.reduce((sum, val) => sum + val, 0) / slice.length
    result.push(average)
  }
  return result
}

const updateChart = () => {
  nextTick(() => {
    if (activeTab.value === 'rewards' && !rewardChart) {
      initRewardChart()
    } else if (activeTab.value === 'losses' && !lossChart) {
      initLossChart()
    } else if (activeTab.value === 'metrics' && !metricsChart) {
      initMetricsChart()
    }
  })
}

const resizeCharts = () => {
  if (rewardChart) rewardChart.resize()
  if (lossChart) lossChart.resize()
  if (metricsChart) metricsChart.resize()
}

// 监听数据变化
watch(() => props.data, () => {
  if (hasData.value) {
    if (rewardChart) {
      rewardChart.setOption({
        xAxis: { data: props.data.episodes },
        series: [
          { data: props.data.rewards },
          { data: calculateMovingAverage(props.data.rewards, 10) }
        ]
      })
    }
    if (lossChart) {
      lossChart.setOption({
        xAxis: { data: props.data.episodes },
        series: [
          { data: props.data.losses },
          { data: calculateMovingAverage(props.data.losses, 10) }
        ]
      })
    }
    if (metricsChart) {
      metricsChart.setOption({
        xAxis: { data: props.data.episodes },
        series: [
          { data: props.data.qoeScores },
          { data: props.data.fairnessScores },
          { data: props.data.efficiencyScores }
        ]
      })
    }
  }
}, { deep: true })

// 生命周期
onMounted(() => {
  nextTick(() => {
    if (hasData.value) {
      initRewardChart()
    }
  })
  
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  if (rewardChart) rewardChart.dispose()
  if (lossChart) lossChart.dispose()
  if (metricsChart) metricsChart.dispose()
  window.removeEventListener('resize', resizeCharts)
})
</script>

<style scoped>
.drl-training-chart {
  width: 100%;
  position: relative;
}

.chart-loading,
.chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.chart-loading .el-icon,
.chart-empty .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.chart-loading .el-icon {
  color: var(--el-color-primary);
}

.chart-empty .el-icon {
  color: var(--el-text-color-placeholder);
}

.chart-tabs {
  height: 100%;
}

.chart-container {
  width: 100%;
  height: 350px;
}

:deep(.el-tabs__content) {
  height: calc(100% - 40px);
}

:deep(.el-tab-pane) {
  height: 100%;
}
</style>
