<template>
  <div class="event-log" :style="{ height }">
    <div v-if="!events.length" class="log-empty">
      <el-icon><DocumentRemove /></el-icon>
      <span>暂无事件日志</span>
    </div>
    <div v-else class="log-container" ref="logContainer">
      <div
        v-for="event in displayEvents"
        :key="event.id || event.timestamp"
        class="log-entry"
        :class="getEventClass(event.type)"
      >
        <div class="log-time">
          {{ formatTime(event.timestamp) }}
        </div>
        <div class="log-type">
          <el-icon>
            <component :is="getEventIcon(event.type)" />
          </el-icon>
          <span>{{ getEventTypeText(event.type) }}</span>
        </div>
        <div class="log-message">
          {{ event.message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  DocumentRemove,
  SuccessFilled,
  WarningFilled,
  CircleCloseFilled,
  InfoFilled
} from '@element-plus/icons-vue'

interface LogEvent {
  id?: string
  timestamp: number
  type: string
  message: string
}

interface Props {
  events: LogEvent[]
  height?: string
  maxEvents?: number
  autoScroll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
  maxEvents: 100,
  autoScroll: true
})

const logContainer = ref<HTMLElement>()

// 计算属性
const displayEvents = computed(() => {
  const events = props.events.slice(0, props.maxEvents)
  return events.map((event, index) => ({
    ...event,
    id: event.id || `${event.timestamp}-${index}`
  }))
})

// 方法
const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString()
}

const getEventClass = (type: string) => {
  const classMap: Record<string, string> = {
    'success': 'log-success',
    'error': 'log-error',
    'warning': 'log-warning',
    'info': 'log-info'
  }
  return classMap[type] || 'log-info'
}

const getEventIcon = (type: string) => {
  const iconMap: Record<string, any> = {
    'success': SuccessFilled,
    'error': CircleCloseFilled,
    'warning': WarningFilled,
    'info': InfoFilled
  }
  return iconMap[type] || InfoFilled
}

const getEventTypeText = (type: string) => {
  const textMap: Record<string, string> = {
    'success': '成功',
    'error': '错误',
    'warning': '警告',
    'info': '信息'
  }
  return textMap[type] || '信息'
}

const scrollToBottom = () => {
  if (logContainer.value && props.autoScroll) {
    nextTick(() => {
      logContainer.value!.scrollTop = logContainer.value!.scrollHeight
    })
  }
}

// 监听事件变化，自动滚动到底部
watch(() => props.events.length, scrollToBottom)

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.event-log {
  width: 100%;
  position: relative;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background-color: var(--el-bg-color);
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-placeholder);
  font-size: 14px;
}

.log-empty .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.log-container {
  height: 100%;
  overflow-y: auto;
  padding: 8px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
}

.log-entry {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 8px;
  margin-bottom: 2px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.log-entry:hover {
  background-color: var(--el-fill-color-light);
}

.log-time {
  flex-shrink: 0;
  width: 80px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.log-type {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  width: 60px;
  font-size: 11px;
  font-weight: 500;
}

.log-message {
  flex: 1;
  word-break: break-word;
  color: var(--el-text-color-primary);
}

/* 不同类型的样式 */
.log-success {
  border-left: 3px solid var(--el-color-success);
}

.log-success .log-type {
  color: var(--el-color-success);
}

.log-error {
  border-left: 3px solid var(--el-color-danger);
}

.log-error .log-type {
  color: var(--el-color-danger);
}

.log-warning {
  border-left: 3px solid var(--el-color-warning);
}

.log-warning .log-type {
  color: var(--el-color-warning);
}

.log-info {
  border-left: 3px solid var(--el-color-info);
}

.log-info .log-type {
  color: var(--el-color-info);
}

/* 滚动条样式 */
.log-container::-webkit-scrollbar {
  width: 6px;
}

.log-container::-webkit-scrollbar-track {
  background: var(--el-fill-color-lighter);
  border-radius: 3px;
}

.log-container::-webkit-scrollbar-thumb {
  background: var(--el-border-color-darker);
  border-radius: 3px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: var(--el-border-color-dark);
}
</style>
