<template>
  <div class="performance-chart" :style="{ height }">
    <div v-if="loading" class="chart-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else-if="!data.length" class="chart-empty">
      <el-icon><DocumentRemove /></el-icon>
      <span>暂无数据</span>
    </div>
    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { Loading, DocumentRemove } from '@element-plus/icons-vue'

interface ChartDataPoint {
  timestamp: number
  throughput: number
  latency: number
  qoe: number
  admissionRate: number
}

interface Props {
  data: ChartDataPoint[]
  loading?: boolean
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  height: '400px'
})

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)
  
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
      },
      formatter: (params: any) => {
        const time = new Date(params[0].axisValue).toLocaleTimeString()
        let html = `<div><strong>${time}</strong></div>`
        
        params.forEach((param: any) => {
          const color = param.color
          const name = param.seriesName
          const value = param.value
          let unit = ''
          
          if (name === '吞吐量') unit = ' Mbps'
          else if (name === '延迟') unit = ' ms'
          else if (name === '准入率') unit = '%'
          
          html += `<div style="margin: 2px 0;">
            <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>
            ${name}: <strong>${value}${unit}</strong>
          </div>`
        })
        
        return html
      }
    },
    legend: {
      data: ['吞吐量', '延迟', 'QoE评分', '准入率'],
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
      type: 'time',
      boundaryGap: false,
      axisLabel: {
        formatter: (value: number) => {
          return new Date(value).toLocaleTimeString()
        }
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '吞吐量 (Mbps)',
        position: 'left',
        axisLabel: {
          formatter: '{value}'
        }
      },
      {
        type: 'value',
        name: '延迟 (ms)',
        position: 'right',
        axisLabel: {
          formatter: '{value}'
        }
      }
    ],
    series: [
      {
        name: '吞吐量',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: '#409EFF'
        }
      },
      {
        name: '延迟',
        type: 'line',
        yAxisIndex: 1,
        data: [],
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: '#F56C6C'
        }
      },
      {
        name: 'QoE评分',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: '#67C23A'
        }
      },
      {
        name: '准入率',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: '#E6A23C'
        }
      }
    ],
    animation: true,
    animationDuration: 1000,
    animationEasing: 'cubicOut'
  }
  
  chart.setOption(option)
}

const updateChart = () => {
  if (!chart || !props.data.length) return

  const timestamps = props.data.map(d => d.timestamp * 1000) // 转换为毫秒
  const throughputData = props.data.map((d, i) => [timestamps[i], d.throughput])
  const latencyData = props.data.map((d, i) => [timestamps[i], d.latency])
  const qoeData = props.data.map((d, i) => [timestamps[i], d.qoe * 100]) // 转换为百分比
  const admissionData = props.data.map((d, i) => [timestamps[i], d.admissionRate * 100]) // 转换为百分比

  chart.setOption({
    series: [
      { data: throughputData },
      { data: latencyData },
      { data: qoeData },
      { data: admissionData }
    ]
  })
}

const resizeChart = () => {
  if (chart) {
    chart.resize()
  }
}

// 监听数据变化
watch(() => props.data, updateChart, { deep: true })

// 监听窗口大小变化
onMounted(() => {
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
</script>

<style scoped>
.performance-chart {
  width: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  height: 100%;
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
</style>
