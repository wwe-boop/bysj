<template>
  <el-card class="metric-card" :class="cardClass">
    <div class="metric-content">
      <div class="metric-icon">
        <el-icon :size="32">
          <component :is="iconComponent" />
        </el-icon>
      </div>
      <div class="metric-info">
        <div class="metric-title">{{ title }}</div>
        <div class="metric-value" v-loading="loading">
          {{ displayValue }}
        </div>
        <div v-if="trend" class="metric-trend" :class="trendClass">
          <el-icon>
            <ArrowUp v-if="trend > 0" />
            <ArrowDown v-if="trend < 0" />
            <Minus v-if="trend === 0" />
          </el-icon>
          <span>{{ formatTrend(trend) }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { 
  ArrowUp, 
  ArrowDown, 
  Minus,
  VideoPlay,
  TrendCharts,
  Timer,
  Star,
  DataBoard
} from '@element-plus/icons-vue'

interface Props {
  title: string
  value: string | number
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  icon?: string
  trend?: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'primary',
  icon: 'DataBoard',
  loading: false
})

// 图标映射
const iconMap = {
  VideoPlay,
  TrendCharts,
  Timer,
  Star,
  DataBoard
}

const iconComponent = computed(() => {
  return iconMap[props.icon as keyof typeof iconMap] || DataBoard
})

const cardClass = computed(() => ({
  [`metric-card--${props.type}`]: true
}))

const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

const trendClass = computed(() => ({
  'trend-up': props.trend && props.trend > 0,
  'trend-down': props.trend && props.trend < 0,
  'trend-neutral': props.trend === 0
}))

const formatTrend = (trend: number) => {
  const abs = Math.abs(trend)
  if (abs >= 1) {
    return `${trend > 0 ? '+' : ''}${trend.toFixed(1)}%`
  }
  return `${trend > 0 ? '+' : ''}${(trend * 100).toFixed(1)}%`
}
</script>

<style scoped>
.metric-card {
  border: none;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
}

.metric-card--primary {
  border-left: 4px solid var(--el-color-primary);
}

.metric-card--success {
  border-left: 4px solid var(--el-color-success);
}

.metric-card--warning {
  border-left: 4px solid var(--el-color-warning);
}

.metric-card--danger {
  border-left: 4px solid var(--el-color-danger);
}

.metric-card--info {
  border-left: 4px solid var(--el-color-info);
}

.metric-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 12px;
  background: var(--el-bg-color-page);
  color: var(--el-color-primary);
}

.metric-card--success .metric-icon {
  color: var(--el-color-success);
}

.metric-card--warning .metric-icon {
  color: var(--el-color-warning);
}

.metric-card--danger .metric-icon {
  color: var(--el-color-danger);
}

.metric-card--info .metric-icon {
  color: var(--el-color-info);
}

.metric-info {
  flex: 1;
}

.metric-title {
  font-size: 14px;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
}

.trend-up {
  color: var(--el-color-success);
}

.trend-down {
  color: var(--el-color-danger);
}

.trend-neutral {
  color: var(--el-text-color-regular);
}
</style>
