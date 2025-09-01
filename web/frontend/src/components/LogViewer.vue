<template>
  <div class="log-viewer">
    <div class="log-header">
      <div class="log-controls">
        <el-select v-model="selectedLevel" placeholder="日志级别" size="small" style="width: 120px;">
          <el-option label="全部" value="all" />
          <el-option label="错误" value="error" />
          <el-option label="警告" value="warning" />
          <el-option label="信息" value="info" />
          <el-option label="调试" value="debug" />
        </el-select>
        
        <el-select v-model="selectedSource" placeholder="日志源" size="small" style="width: 150px;">
          <el-option label="全部" value="all" />
          <el-option label="仿真引擎" value="simulation" />
          <el-option label="准入控制" value="admission" />
          <el-option label="定位服务" value="positioning" />
          <el-option label="网络管理" value="network" />
        </el-select>
        
        <el-button size="small" @click="clearLogs">清空</el-button>
        <el-button size="small" @click="exportLogs">导出</el-button>
        <el-button size="small" :type="autoScroll ? 'primary' : ''" @click="toggleAutoScroll">
          {{ autoScroll ? '停止滚动' : '自动滚动' }}
        </el-button>
      </div>
      
      <div class="log-search">
        <el-input
          v-model="searchText"
          placeholder="搜索日志..."
          size="small"
          style="width: 200px;"
          :prefix-icon="Search"
          clearable
        />
      </div>
    </div>
    
    <div class="log-content" ref="logContentRef">
      <div 
        v-for="log in filteredLogs" 
        :key="log.id"
        :class="['log-entry', `log-${log.level}`]"
      >
        <span class="log-time">{{ formatTime(log.timestamp) }}</span>
        <span class="log-level">{{ log.level.toUpperCase() }}</span>
        <span class="log-source">[{{ log.source }}]</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
      
      <div v-if="filteredLogs.length === 0" class="no-logs">
        暂无日志数据
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

interface LogEntry {
  id: number
  timestamp: number
  level: 'error' | 'warning' | 'info' | 'debug'
  source: string
  message: string
}

// 响应式数据
const logContentRef = ref()
const selectedLevel = ref('all')
const selectedSource = ref('all')
const searchText = ref('')
const autoScroll = ref(true)

const logs = ref<LogEntry[]>([
  {
    id: 1,
    timestamp: Date.now() - 5000,
    level: 'info',
    source: 'simulation',
    message: '仿真引擎启动成功'
  },
  {
    id: 2,
    timestamp: Date.now() - 4000,
    level: 'info',
    source: 'network',
    message: '网络拓扑初始化完成'
  },
  {
    id: 3,
    timestamp: Date.now() - 3000,
    level: 'warning',
    source: 'admission',
    message: '用户准入请求队列达到80%'
  },
  {
    id: 4,
    timestamp: Date.now() - 2000,
    level: 'error',
    source: 'positioning',
    message: '定位服务连接超时'
  },
  {
    id: 5,
    timestamp: Date.now() - 1000,
    level: 'debug',
    source: 'simulation',
    message: '卫星位置更新: SAT-001 (45.123, 120.456)'
  }
])

// 计算属性
const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    // 级别过滤
    if (selectedLevel.value !== 'all' && log.level !== selectedLevel.value) {
      return false
    }
    
    // 源过滤
    if (selectedSource.value !== 'all' && log.source !== selectedSource.value) {
      return false
    }
    
    // 搜索过滤
    if (searchText.value && !log.message.toLowerCase().includes(searchText.value.toLowerCase())) {
      return false
    }
    
    return true
  }).sort((a, b) => b.timestamp - a.timestamp)
})

// 监听自动滚动
watch(filteredLogs, () => {
  if (autoScroll.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})

// 方法
const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString()
}

const clearLogs = () => {
  logs.value = []
  ElMessage.success('日志已清空')
}

const exportLogs = () => {
  const logText = filteredLogs.value
    .map(log => `${formatTime(log.timestamp)} [${log.level.toUpperCase()}] [${log.source}] ${log.message}`)
    .join('\n')
  
  const blob = new Blob([logText], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('日志导出成功')
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  if (logContentRef.value) {
    logContentRef.value.scrollTop = logContentRef.value.scrollHeight
  }
}

// 模拟新日志添加
const addLog = (level: LogEntry['level'], source: string, message: string) => {
  logs.value.push({
    id: Date.now(),
    timestamp: Date.now(),
    level,
    source,
    message
  })
}

// 模拟日志生成
setInterval(() => {
  const messages = [
    { level: 'info', source: 'simulation', message: '仿真步骤执行完成' },
    { level: 'debug', source: 'network', message: '链路状态更新' },
    { level: 'warning', source: 'admission', message: '准入请求处理延迟' },
    { level: 'info', source: 'positioning', message: '定位精度: 2.3m' }
  ]
  
  const randomMessage = messages[Math.floor(Math.random() * messages.length)]
  addLog(randomMessage.level as LogEntry['level'], randomMessage.source, randomMessage.message)
}, 3000)
</script>

<style scoped>
.log-viewer {
  height: 400px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #e4e7ed;
  background: #f5f7fa;
}

.log-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  background: #1e1e1e;
  color: #d4d4d4;
}

.log-entry {
  margin-bottom: 2px;
  padding: 2px 0;
  word-wrap: break-word;
}

.log-time {
  color: #569cd6;
  margin-right: 8px;
}

.log-level {
  display: inline-block;
  width: 60px;
  margin-right: 8px;
  font-weight: bold;
}

.log-source {
  color: #4ec9b0;
  margin-right: 8px;
}

.log-message {
  color: #d4d4d4;
}

.log-error .log-level {
  color: #f44747;
}

.log-warning .log-level {
  color: #ffcc02;
}

.log-info .log-level {
  color: #4fc1ff;
}

.log-debug .log-level {
  color: #b5cea8;
}

.no-logs {
  text-align: center;
  color: #909399;
  padding: 20px;
}

/* 滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 8px;
}

.log-content::-webkit-scrollbar-track {
  background: #2d2d30;
}

.log-content::-webkit-scrollbar-thumb {
  background: #464647;
  border-radius: 4px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: #5a5a5c;
}
</style>
