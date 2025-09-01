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
        <div class="ablation-panel">
          <el-row :gutter="16">
            <el-col :xs="24" :lg="8">
              <el-card>
                <template #header>
                  <span>多维切换</span>
                </template>
                <el-form label-width="98px" size="small">
                  <el-form-item label="状态消融">
                    <el-select v-model="ablationConfig.state_ablations" multiple filterable collapse-tags collapse-tags-tooltip style="width:100%">
                      <el-option v-for="item in stateDims" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="奖励消融">
                    <el-select v-model="ablationConfig.reward_ablations" multiple filterable collapse-tags collapse-tags-tooltip style="width:100%">
                      <el-option v-for="item in rewardDims" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="动作消融">
                    <el-select v-model="ablationConfig.action_ablations" multiple filterable collapse-tags collapse-tags-tooltip style="width:100%">
                      <el-option v-for="item in actionDims" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="负载维度">
                    <el-select v-model="ablationConfig.load_ablations" multiple filterable collapse-tags collapse-tags-tooltip style="width:100%">
                      <el-option v-for="item in loadDims" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="星座维度">
                    <el-select v-model="ablationConfig.constellation_ablations" multiple filterable collapse-tags collapse-tags-tooltip style="width:100%">
                      <el-option v-for="item in constellationDims" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="失败场景">
                    <el-select v-model="ablationConfig.failure_ablations" multiple filterable collapse-tags collapse-tags-tooltip style="width:100%">
                      <el-option v-for="item in failureDims" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                  <div class="config-actions">
                    <el-button type="primary" :loading="ablationRunning" @click="startAblation">启动消融</el-button>
                    <el-button :disabled="!currentAblationId" @click="loadAblationResults">刷新结果</el-button>
                  </div>
                </el-form>
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="16">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>显著性统计与导出</span>
                    <div class="card-actions">
                      <el-button size="small" @click="exportResults('csv')">导出CSV</el-button>
                      <el-button size="small" @click="exportResults('json')">导出JSON</el-button>
                      <el-button size="small" type="success" @click="generateChartsPNG">导出PNG</el-button>
                    </div>
                  </div>
                </template>
                <div v-if="ablationLoading" class="loading-container">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>生成与载入中...</span>
                </div>
                <div v-else>
                  <div v-if="significanceSummary.length" class="sig-table">
                    <el-table :data="significanceSummary" size="small" border>
                      <el-table-column prop="metric" label="指标" width="160" />
                      <el-table-column prop="test" label="检验方法" width="160" />
                      <el-table-column prop="p" label="p值" width="120" />
                      <el-table-column prop="effect" label="效应量" width="120" />
                      <el-table-column prop="ci" label="置信区间" />
                      <el-table-column prop="significant" label="显著" width="100">
                        <template #default="{ row }">
                          <el-tag :type="row.significant ? 'success' : 'info'">{{ row.significant ? '是' : '否' }}</el-tag>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                  <div v-else class="empty-container">
                    <el-icon><DocumentRemove /></el-icon>
                    <div class="empty-text">暂无统计结果</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
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
import { DataAnalysis, Loading, DocumentRemove } from '@element-plus/icons-vue'

// 状态管理
const appStore = useAppStore()

// 响应式数据
const activeTab = ref('batch')
const experiments = ref([])
const loading = ref(false)

// 消融配置与结果状态
const ablationConfig = reactive({
  state_ablations: [] as string[],
  reward_ablations: [] as string[],
  action_ablations: [] as string[],
  load_ablations: [] as (number|string)[],
  constellation_ablations: [] as string[],
  failure_ablations: [] as string[]
})
const stateDims = ['pos_quality', 'traffic_state', 'link_utilization', 'routing_metrics']
const rewardDims = ['qoe', 'fairness', 'stability', 'positioning', 'efficiency']
const actionDims = ['admission_binary', 'bandwidth_alloc', 'routing_choice']
const loadDims = ['0.5x', '1x', '1.5x', '2x']
const constellationDims = ['walker_66_6_66', 'walker_72_6_72']
const failureDims = ['isl_failure_1%', 'gsl_degrade_10%']

const currentAblationId = ref<string>('')
const ablationLoading = ref(false)
const ablationRunning = ref(false)
const significanceSummary = ref<any[]>([])

// 计算属性
const completedExperiments = computed(() => {
  return experiments.value.filter((exp: any) => exp.status === 'completed')
})

const runningExperiments = computed(() => {
  return experiments.value.filter((exp: any) => exp.status === 'running')
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

const startAblation = async () => {
  ablationRunning.value = true
  try {
    const payload = {
      base_config: { experiment_name: 'ablation', scenario_name: 'default' },
      ablation_config: { ...ablationConfig },
      num_runs: 10
    }
    const res = await experimentsApi.startAblationStudy(payload)
    currentAblationId.value = res.experiment_id
    appStore.addNotification({ type: 'success', title: '消融启动', message: `ID: ${res.experiment_id}` })
  } catch (e) {
    ElMessage.error('启动消融失败')
  } finally {
    ablationRunning.value = false
  }
}

const loadAblationResults = async () => {
  if (!currentAblationId.value) return
  ablationLoading.value = true
  try {
    const analysis = await experimentsApi.getStatisticalAnalysis(currentAblationId.value)
    const comp = analysis || {}
    const compTests = comp.comparison_tests || {}
    const effect = comp.effect_sizes || {}
    const ci = comp.confidence_intervals || {}
    const desc = comp.descriptive_stats || {}

    // 汇总显著性表格数据（若后端提供的字段名不同可调整）
    const rows: any[] = []
    Object.keys(ci).forEach((metric) => {
      const pval = compTests[metric]?.p_value ?? null
      const es = effect[metric] ?? null
      const ciTuple = ci[metric] ?? null
      rows.push({
        metric,
        test: compTests[metric]?.test_name || '—',
        p: pval == null ? '—' : Number(pval).toExponential(2),
        effect: es == null ? '—' : Number(es).toFixed(4),
        ci: ciTuple ? `[${ciTuple[0].toFixed(3)}, ${ciTuple[1].toFixed(3)}]` : '—',
        significant: pval != null && pval < 0.05
      })
    })
    significanceSummary.value = rows
  } catch (e) {
    ElMessage.error('加载统计结果失败')
  } finally {
    ablationLoading.value = false
  }
}

const exportResults = async (format: 'csv' | 'json') => {
  if (!currentAblationId.value) return
  try {
    const blob = await experimentsApi.exportResults(currentAblationId.value, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ablation_${currentAblationId.value}.${format}`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

const generateChartsPNG = async () => {
  if (!currentAblationId.value) return
  try {
    const files = await experimentsApi.generateCharts(currentAblationId.value, ['algorithm_comparison', 'performance_trend', 'correlation_heatmap'])
    appStore.addNotification({ type: 'success', title: '图表生成', message: `生成 ${files.total_charts} 个文件` })
  } catch (e) {
    ElMessage.error('生成图表失败')
  }
}

const handleExperimentStarted = (experimentData: any) => {
  appStore.addNotification({
    type: 'success',
    title: '实验启动',
    message: `实验 ${experimentData.experiment_id} 已启动`
  })
  experiments.value.unshift({
    experiment_id: experimentData.experiment_id,
    status: 'running',
    progress: 0,
    start_time: Date.now() / 1000,
    has_results: false
  })
  activeTab.value = 'monitoring'
}

const handleExperimentCompleted = (experimentId: string) => {
  appStore.addNotification({ type: 'success', title: '实验完成', message: `实验 ${experimentId} 已完成` })
  const experiment: any = experiments.value.find((exp: any) => exp.experiment_id === experimentId)
  if (experiment) {
    experiment.status = 'completed'
    experiment.progress = 100
    experiment.has_results = true
  }
  loadExperiments()
}

const handleGenerateCharts = async (experimentId: string, chartTypes: string[]) => {
  try {
    const response = await experimentsApi.generateCharts(experimentId, chartTypes)
    appStore.addNotification({ type: 'success', title: '图表生成', message: `已生成 ${response.total_charts} 个图表` })
    return response.generated_files
  } catch (error) {
    console.error('生成图表失败:', error)
    ElMessage.error('生成图表失败')
    return []
  }
}

// 定期刷新运行中的实验状态
const refreshInterval = ref<any>(null)
const startPeriodicRefresh = () => {
  refreshInterval.value = setInterval(() => {
    if (runningExperiments.value.length > 0) {
      loadExperiments()
    }
  }, 5000)
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

.ablation-panel {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sig-table {
  margin-top: 8px;
}
</style>
