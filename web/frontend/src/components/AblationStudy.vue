<template>
  <div class="ablation-study">
    <!-- 实验配置 -->
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>消融实验配置</span>
          <el-button-group size="small">
            <el-button :icon="Setting" @click="showConfigDialog = true">配置</el-button>
            <el-button :icon="VideoPlay" type="primary" @click="startAblationStudy" :loading="starting">
              启动实验
            </el-button>
          </el-button-group>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="config-section">
            <h4>消融维度</h4>
            <el-checkbox-group v-model="selectedDimensions">
              <el-checkbox label="state">状态空间</el-checkbox>
              <el-checkbox label="action">动作空间</el-checkbox>
              <el-checkbox label="reward">奖励函数</el-checkbox>
              <el-checkbox label="algorithm">算法对比</el-checkbox>
              <el-checkbox label="load">负载变化</el-checkbox>
              <el-checkbox label="constellation">星座配置</el-checkbox>
            </el-checkbox-group>
          </div>
        </el-col>
        
        <el-col :span="8">
          <div class="config-section">
            <h4>实验参数</h4>
            <el-form :model="experimentConfig" label-width="100px" size="small">
              <el-form-item label="重复次数">
                <el-input-number v-model="experimentConfig.numRuns" :min="1" :max="20" />
              </el-form-item>
              <el-form-item label="并行数">
                <el-input-number v-model="experimentConfig.parallelWorkers" :min="1" :max="8" />
              </el-form-item>
              <el-form-item label="显著性水平">
                <el-select v-model="experimentConfig.significanceLevel">
                  <el-option label="0.05" value="0.05" />
                  <el-option label="0.01" value="0.01" />
                  <el-option label="0.001" value="0.001" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </el-col>
        
        <el-col :span="8">
          <div class="config-section">
            <h4>评估指标</h4>
            <el-checkbox-group v-model="selectedMetrics">
              <el-checkbox label="qoe">QoE得分</el-checkbox>
              <el-checkbox label="admission_rate">准入率</el-checkbox>
              <el-checkbox label="fairness">公平性</el-checkbox>
              <el-checkbox label="efficiency">效率</el-checkbox>
              <el-checkbox label="positioning">定位质量</el-checkbox>
              <el-checkbox label="stability">稳定性</el-checkbox>
            </el-checkbox-group>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 实验结果 -->
    <el-card v-if="hasResults">
      <template #header>
        <div class="card-header">
          <span>消融实验结果</span>
          <el-button-group size="small">
            <el-button :icon="Refresh" @click="loadResults">刷新</el-button>
            <el-button :icon="Download" @click="exportResults">导出结果</el-button>
            <el-button :icon="PictureRounded" @click="generateCharts">生成图表</el-button>
          </el-button-group>
        </div>
      </template>
      
      <!-- 维度切换 -->
      <div class="dimension-tabs mb-4">
        <el-tabs v-model="activeDimension" @tab-change="updateResultsView">
          <el-tab-pane 
            v-for="dim in availableDimensions" 
            :key="dim.key"
            :label="dim.label" 
            :name="dim.key"
          >
            <!-- 对比图表 -->
            <div class="comparison-charts mb-4">
              <el-row :gutter="16">
                <el-col :span="12">
                  <div class="chart-container">
                    <h5>性能对比</h5>
                    <div ref="performanceChartRef" class="chart-placeholder">
                      性能对比图表
                    </div>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="chart-container">
                    <h5>统计显著性</h5>
                    <div ref="significanceChartRef" class="chart-placeholder">
                      显著性检验图表
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
            
            <!-- 结果表格 -->
            <div class="results-table">
              <h5>详细结果 ({{ dim.label }})</h5>
              <el-table 
                :data="currentResults" 
                stripe 
                border
                style="width: 100%"
                :default-sort="{prop: 'mean_qoe', order: 'descending'}"
              >
                <el-table-column prop="config_name" label="配置" width="150" fixed="left" />
                <el-table-column 
                  v-for="metric in selectedMetrics" 
                  :key="metric"
                  :label="getMetricDisplayName(metric)"
                  align="center"
                >
                  <template #default="{ row }">
                    <div class="metric-cell">
                      <div class="metric-value">
                        {{ formatMetricValue(row[`mean_${metric}`]) }}
                        <span class="metric-std">±{{ formatMetricValue(row[`std_${metric}`]) }}</span>
                      </div>
                      <div class="significance-indicator" v-if="row[`${metric}_significance`]">
                        <el-tag 
                          :type="getSignificanceType(row[`${metric}_significance`])"
                          size="small"
                        >
                          {{ row[`${metric}_significance`] }}
                        </el-tag>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" fixed="right">
                  <template #default="{ row }">
                    <el-button-group size="small">
                      <el-button :icon="View" @click="viewDetails(row)" />
                      <el-button :icon="Download" @click="exportConfig(row)" />
                    </el-button-group>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Setting, 
  VideoPlay, 
  Refresh, 
  Download, 
  PictureRounded,
  View 
} from '@element-plus/icons-vue'

// 响应式数据
const showConfigDialog = ref(false)
const starting = ref(false)
const hasResults = ref(true) // 模拟有结果
const activeDimension = ref('state')

const selectedDimensions = ref(['state', 'action', 'reward'])
const selectedMetrics = ref(['qoe', 'admission_rate', 'fairness'])

const experimentConfig = reactive({
  numRuns: 10,
  parallelWorkers: 4,
  significanceLevel: '0.05'
})

const availableDimensions = computed(() => [
  { key: 'state', label: '状态空间' },
  { key: 'action', label: '动作空间' },
  { key: 'reward', label: '奖励函数' },
  { key: 'algorithm', label: '算法对比' }
].filter(dim => selectedDimensions.value.includes(dim.key)))

const currentResults = ref([
  {
    config_name: '完整配置',
    mean_qoe: 4.2,
    std_qoe: 0.3,
    mean_admission_rate: 0.94,
    std_admission_rate: 0.02,
    mean_fairness: 0.85,
    std_fairness: 0.05,
    qoe_significance: '***',
    admission_rate_significance: '**',
    fairness_significance: '*'
  },
  {
    config_name: '无状态特征',
    mean_qoe: 3.8,
    std_qoe: 0.4,
    mean_admission_rate: 0.89,
    std_admission_rate: 0.03,
    mean_fairness: 0.78,
    std_fairness: 0.06,
    qoe_significance: '**',
    admission_rate_significance: '*',
    fairness_significance: 'ns'
  }
])

// 方法
const startAblationStudy = async () => {
  starting.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 2000))
    ElMessage.success('消融实验启动成功')
    hasResults.value = true
  } finally {
    starting.value = false
  }
}

const loadResults = () => {
  ElMessage.success('结果已刷新')
}

const exportResults = () => {
  ElMessage.success('结果导出成功')
}

const generateCharts = () => {
  ElMessage.success('图表生成成功')
}

const updateResultsView = (dimension: string) => {
  console.log('切换到维度:', dimension)
}

const getMetricDisplayName = (metric: string) => {
  const names = {
    'qoe': 'QoE得分',
    'admission_rate': '准入率',
    'fairness': '公平性',
    'efficiency': '效率',
    'positioning': '定位质量',
    'stability': '稳定性'
  }
  return names[metric] || metric
}

const formatMetricValue = (value: number) => {
  return value?.toFixed(3) || '0.000'
}

const getSignificanceType = (significance: string) => {
  if (significance === '***') return 'danger'
  if (significance === '**') return 'warning'
  if (significance === '*') return 'info'
  return ''
}

const viewDetails = (row: any) => {
  ElMessage.info(`查看配置详情: ${row.config_name}`)
}

const exportConfig = (row: any) => {
  ElMessage.success(`导出配置: ${row.config_name}`)
}
</script>

<style scoped>
.ablation-study {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-section h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.dimension-tabs {
  margin-top: 20px;
}

.comparison-charts {
  margin-bottom: 20px;
}

.chart-container h5 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.chart-placeholder {
  height: 200px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.results-table h5 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.metric-cell {
  text-align: center;
}

.metric-value {
  font-weight: bold;
  margin-bottom: 4px;
}

.metric-std {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.significance-indicator {
  margin-top: 4px;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
