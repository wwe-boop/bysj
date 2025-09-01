<template>
  <div class="experiments">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="24">
        <h1 class="page-title">
          <el-icon><DataAnalysis /></el-icon>
          实验批跑与统计分析
        </h1>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab" class="experiment-tabs">
      <!-- 批量实验 -->
      <el-tab-pane label="批量实验" name="batch">
        <BatchExperiments 
          @experiment-started="handleExperimentStarted"
          @experiment-completed="handleExperimentCompleted"
        />
      </el-tab-pane>

      <!-- 消融实验 -->
      <el-tab-pane label="消融实验" name="ablation">
        <AblationStudy 
          @experiment-started="handleExperimentStarted"
          @experiment-completed="handleExperimentCompleted"
        />
      </el-tab-pane>

      <!-- 实验监控 -->
      <el-tab-pane label="实验监控" name="monitoring">
        <ExperimentMonitoring 
          :experiments="experiments"
          @refresh="loadExperiments"
        />
      </el-tab-pane>

      <!-- 结果分析 -->
      <el-tab-pane label="结果分析" name="analysis">
        <ResultsAnalysis 
          :experiments="completedExperiments"
          @generate-charts="handleGenerateCharts"
        />
      </el-tab-pane>

      <!-- 统计报告 -->
      <el-tab-pane label="统计报告" name="reports">
        <StatisticalReports 
          :experiments="completedExperiments"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { experimentsApi } from '@/api/experiments'
import BatchExperiments from '@/components/BatchExperiments.vue'
import AblationStudy from '@/components/AblationStudy.vue'
import ExperimentMonitoring from '@/components/ExperimentMonitoring.vue'
import ResultsAnalysis from '@/components/ResultsAnalysis.vue'
import StatisticalReports from '@/components/StatisticalReports.vue'
import { DataAnalysis } from '@element-plus/icons-vue'

// 状态管理
const appStore = useAppStore()

// 响应式数据
const activeTab = ref('batch')
const experiments = ref([])
const loading = ref(false)

// 计算属性
const completedExperiments = computed(() => {
  return experiments.value.filter(exp => exp.status === 'completed')
})

const runningExperiments = computed(() => {
  return experiments.value.filter(exp => exp.status === 'running')
})

// 方法
const loadExperiments = async () => {
  loading.value = true
  try {
    const response = await experimentsApi.listExperiments()
    experiments.value = response.experiments || []
  } catch (error) {
    console.error('加载实验列表失败:', error)
    ElMessage.error('加载实验列表失败')
  } finally {
    loading.value = false
  }
}

const handleExperimentStarted = (experimentData) => {
  appStore.addNotification({
    type: 'success',
    title: '实验启动',
    message: `实验 ${experimentData.experiment_id} 已启动`
  })
  
  // 添加到实验列表
  experiments.value.unshift({
    experiment_id: experimentData.experiment_id,
    status: 'running',
    progress: 0,
    start_time: Date.now() / 1000,
    has_results: false
  })
  
  // 切换到监控标签
  activeTab.value = 'monitoring'
}

const handleExperimentCompleted = (experimentId) => {
  appStore.addNotification({
    type: 'success',
    title: '实验完成',
    message: `实验 ${experimentId} 已完成`
  })
  
  // 更新实验状态
  const experiment = experiments.value.find(exp => exp.experiment_id === experimentId)
  if (experiment) {
    experiment.status = 'completed'
    experiment.progress = 100
    experiment.has_results = true
  }
  
  // 刷新实验列表
  loadExperiments()
}

const handleGenerateCharts = async (experimentId, chartTypes) => {
  try {
    const response = await experimentsApi.generateCharts(experimentId, chartTypes)
    
    appStore.addNotification({
      type: 'success',
      title: '图表生成',
      message: `已生成 ${response.total_charts} 个图表`
    })
    
    return response.generated_files
  } catch (error) {
    console.error('生成图表失败:', error)
    ElMessage.error('生成图表失败')
    return []
  }
}

// 定期刷新运行中的实验状态
const refreshInterval = ref(null)

const startPeriodicRefresh = () => {
  refreshInterval.value = setInterval(() => {
    if (runningExperiments.value.length > 0) {
      loadExperiments()
    }
  }, 5000) // 每5秒刷新一次
}

const stopPeriodicRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

// 生命周期
onMounted(async () => {
  await loadExperiments()
  startPeriodicRefresh()
})

onUnmounted(() => {
  stopPeriodicRefresh()
})

// 监听标签变化
watch(activeTab, (newTab) => {
  if (newTab === 'monitoring' && runningExperiments.value.length === 0) {
    // 如果切换到监控标签但没有运行中的实验，刷新列表
    loadExperiments()
  }
})
</script>

<style scoped>
.experiments {
  padding: 0;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 20px 0;
  color: var(--el-text-color-primary);
  font-size: 24px;
  font-weight: 600;
}

.experiment-tabs {
  height: calc(100vh - 120px);
}

:deep(.el-tabs__content) {
  height: calc(100% - 40px);
  overflow-y: auto;
}

:deep(.el-tab-pane) {
  height: 100%;
}

.mb-4 {
  margin-bottom: 20px;
}

/* 实验状态指示器 */
.experiment-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.experiment-status.running {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.experiment-status.completed {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.experiment-status.failed {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

/* 进度条样式 */
.experiment-progress {
  margin: 8px 0;
}

/* 实验卡片样式 */
.experiment-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background: var(--el-bg-color);
  transition: all 0.3s ease;
}

.experiment-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.experiment-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.experiment-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.experiment-card-meta {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
}

.experiment-card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* 统计卡片样式 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stats-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stats-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}

.stats-label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

/* 图表容器样式 */
.chart-container {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 16px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .experiment-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .experiment-card-meta {
    flex-direction: column;
    gap: 4px;
  }
  
  .experiment-card-actions {
    width: 100%;
    justify-content: stretch;
  }
  
  .experiment-card-actions .el-button {
    flex: 1;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--el-text-color-regular);
}

.loading-container .el-icon {
  font-size: 32px;
  margin-bottom: 16px;
  color: var(--el-color-primary);
}

/* 空状态 */
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--el-text-color-placeholder);
}

.empty-container .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-container .empty-text {
  font-size: 16px;
  margin-bottom: 8px;
}

.empty-container .empty-description {
  font-size: 14px;
  color: var(--el-text-color-regular);
}
</style>
