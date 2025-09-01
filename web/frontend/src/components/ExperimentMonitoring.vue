<template>
  <div class="experiment-monitoring">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>实验监控</span>
          <el-button-group size="small">
            <el-button :type="autoRefresh ? 'primary' : ''" @click="toggleAutoRefresh">
              {{ autoRefresh ? '停止自动刷新' : '自动刷新' }}
            </el-button>
            <el-button @click="refreshData">手动刷新</el-button>
          </el-button-group>
        </div>
      </template>
      
      <!-- 实时状态 -->
      <el-row :gutter="20" class="status-overview">
        <el-col :span="6">
          <div class="status-card">
            <div class="status-value">{{ runningExperiments }}</div>
            <div class="status-label">运行中实验</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-card">
            <div class="status-value">{{ queuedJobs }}</div>
            <div class="status-label">排队任务</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-card">
            <div class="status-value">{{ completedToday }}</div>
            <div class="status-label">今日完成</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="status-card">
            <div class="status-value">{{ systemLoad }}%</div>
            <div class="status-label">系统负载</div>
          </div>
        </el-col>
      </el-row>
      
      <!-- 实时图表 -->
      <el-row :gutter="20" class="mt-4">
        <el-col :span="12">
          <div class="chart-section">
            <h4>实时性能指标</h4>
            <div ref="performanceChartRef" class="chart-container">
              实时性能监控图表
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-section">
            <h4>资源使用情况</h4>
            <div ref="resourceChartRef" class="chart-container">
              资源使用监控图表
            </div>
          </div>
        </el-col>
      </el-row>
      
      <!-- 活跃实验列表 -->
      <div class="active-experiments mt-4">
        <h4>活跃实验</h4>
        <el-table :data="activeExperiments" stripe>
          <el-table-column prop="name" label="实验名称" width="200" />
          <el-table-column prop="progress" label="进度" width="150">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :status="getProgressStatus(row.progress)" />
            </template>
          </el-table-column>
          <el-table-column prop="currentMetric" label="当前指标" width="120">
            <template #default="{ row }">
              <span :class="getMetricClass(row.currentMetric)">
                {{ row.currentMetric.toFixed(3) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="eta" label="预计完成" width="120" />
          <el-table-column prop="worker" label="工作节点" width="120" />
          <el-table-column prop="startTime" label="开始时间" width="150" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button-group size="small">
                <el-button @click="viewExperimentDetails(row)">详情</el-button>
                <el-button type="warning" @click="pauseExperiment(row)">暂停</el-button>
                <el-button type="danger" @click="stopExperiment(row)">停止</el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 系统日志 -->
      <div class="system-logs mt-4">
        <h4>系统日志</h4>
        <div class="log-container">
          <div 
            v-for="log in recentLogs" 
            :key="log.id"
            :class="['log-entry', `log-${log.level}`]"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </el-card>
    
    <!-- 实验详情对话框 -->
    <el-dialog v-model="showDetailsDialog" title="实验详情" width="70%">
      <div v-if="selectedExperiment">
        <h3>{{ selectedExperiment.name }}</h3>
        
        <!-- 详细进度 -->
        <el-row :gutter="20" class="mb-4">
          <el-col :span="8">
            <el-statistic title="当前轮次" :value="selectedExperiment.currentEpoch" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="总轮次" :value="selectedExperiment.totalEpochs" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="最佳指标" :value="selectedExperiment.bestMetric" :precision="3" />
          </el-col>
        </el-row>
        
        <!-- 训练曲线 -->
        <div class="training-curves">
          <h4>训练曲线</h4>
          <div ref="trainingCurveRef" class="chart-container">
            训练损失和指标曲线
          </div>
        </div>
        
        <!-- 参数配置 -->
        <div class="experiment-config mt-4">
          <h4>参数配置</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="学习率">{{ selectedExperiment.config.learningRate }}</el-descriptions-item>
            <el-descriptions-item label="批大小">{{ selectedExperiment.config.batchSize }}</el-descriptions-item>
            <el-descriptions-item label="网络层数">{{ selectedExperiment.config.numLayers }}</el-descriptions-item>
            <el-descriptions-item label="隐藏单元">{{ selectedExperiment.config.hiddenUnits }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 响应式数据
const autoRefresh = ref(true)
const showDetailsDialog = ref(false)
const selectedExperiment = ref(null)
const refreshInterval = ref(null)

const runningExperiments = ref(3)
const queuedJobs = ref(7)
const completedToday = ref(12)
const systemLoad = ref(68)

const activeExperiments = ref([
  {
    id: 1,
    name: 'DRL训练实验-001',
    progress: 75,
    currentMetric: 4.235,
    eta: '15分钟',
    worker: 'Worker-01',
    startTime: '14:30:25',
    currentEpoch: 750,
    totalEpochs: 1000,
    bestMetric: 4.456,
    config: {
      learningRate: 0.001,
      batchSize: 32,
      numLayers: 3,
      hiddenUnits: 128
    }
  },
  {
    id: 2,
    name: '消融实验-状态空间',
    progress: 45,
    currentMetric: 3.892,
    eta: '32分钟',
    worker: 'Worker-02',
    startTime: '14:15:10',
    currentEpoch: 450,
    totalEpochs: 1000,
    bestMetric: 4.123,
    config: {
      learningRate: 0.01,
      batchSize: 64,
      numLayers: 2,
      hiddenUnits: 64
    }
  }
])

const recentLogs = ref([
  {
    id: 1,
    timestamp: Date.now() - 5000,
    level: 'info',
    message: '实验 DRL训练实验-001 达到第750轮'
  },
  {
    id: 2,
    timestamp: Date.now() - 10000,
    level: 'warning',
    message: 'Worker-03 内存使用率达到85%'
  },
  {
    id: 3,
    timestamp: Date.now() - 15000,
    level: 'info',
    message: '实验 消融实验-状态空间 开始第450轮训练'
  }
])

// 方法
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

const startAutoRefresh = () => {
  refreshInterval.value = setInterval(() => {
    refreshData()
  }, 5000)
}

const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

const refreshData = () => {
  // 模拟数据更新
  activeExperiments.value.forEach(exp => {
    if (exp.progress < 100) {
      exp.progress = Math.min(100, exp.progress + Math.random() * 2)
      exp.currentMetric += (Math.random() - 0.5) * 0.1
    }
  })
  
  // 添加新日志
  if (Math.random() > 0.7) {
    recentLogs.value.unshift({
      id: Date.now(),
      timestamp: Date.now(),
      level: ['info', 'warning', 'error'][Math.floor(Math.random() * 3)],
      message: `系统状态更新: ${new Date().toLocaleTimeString()}`
    })
    
    // 保持最近20条日志
    if (recentLogs.value.length > 20) {
      recentLogs.value = recentLogs.value.slice(0, 20)
    }
  }
}

const getProgressStatus = (progress: number) => {
  if (progress >= 100) return 'success'
  if (progress >= 80) return undefined
  return undefined
}

const getMetricClass = (metric: number) => {
  if (metric >= 4.0) return 'metric-good'
  if (metric >= 3.5) return 'metric-medium'
  return 'metric-poor'
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString()
}

const viewExperimentDetails = (experiment: any) => {
  selectedExperiment.value = experiment
  showDetailsDialog.value = true
}

const pauseExperiment = async (experiment: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要暂停实验 "${experiment.name}" 吗？`,
      '确认暂停',
      {
        confirmButtonText: '暂停',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success(`实验 "${experiment.name}" 已暂停`)
  } catch {
    // 用户取消
  }
}

const stopExperiment = async (experiment: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要停止实验 "${experiment.name}" 吗？此操作不可恢复。`,
      '确认停止',
      {
        confirmButtonText: '停止',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const index = activeExperiments.value.findIndex(e => e.id === experiment.id)
    if (index > -1) {
      activeExperiments.value.splice(index, 1)
      ElMessage.success(`实验 "${experiment.name}" 已停止`)
    }
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.experiment-monitoring {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-overview {
  margin-bottom: 20px;
}

.status-card {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.status-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.status-label {
  font-size: 14px;
  color: #666;
}

.chart-section h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.chart-container {
  height: 200px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.active-experiments h4,
.system-logs h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.metric-good {
  color: #67c23a;
  font-weight: bold;
}

.metric-medium {
  color: #e6a23c;
  font-weight: bold;
}

.metric-poor {
  color: #f56c6c;
  font-weight: bold;
}

.log-container {
  height: 200px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 10px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.log-entry {
  margin-bottom: 4px;
  color: #d4d4d4;
}

.log-time {
  color: #569cd6;
  margin-right: 8px;
}

.log-level {
  margin-right: 8px;
  font-weight: bold;
}

.log-info .log-level {
  color: #4fc1ff;
}

.log-warning .log-level {
  color: #ffcc02;
}

.log-error .log-level {
  color: #f44747;
}

.training-curves h4,
.experiment-config h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.mt-4 {
  margin-top: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
