<template>
  <div class="results-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>结果分析</span>
          <el-button-group size="small">
            <el-button @click="refreshAnalysis">刷新分析</el-button>
            <el-button @click="exportAnalysis">导出报告</el-button>
            <el-button @click="compareResults">对比分析</el-button>
          </el-button-group>
        </div>
      </template>
      
      <!-- 分析概览 -->
      <el-row :gutter="20" class="analysis-overview">
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-value">{{ overallStats.bestQoE }}</div>
            <div class="metric-label">最佳QoE</div>
            <div class="metric-change positive">+8.5%</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-value">{{ overallStats.avgImprovement }}%</div>
            <div class="metric-label">平均提升</div>
            <div class="metric-change positive">+12.3%</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-value">{{ overallStats.convergenceRate }}%</div>
            <div class="metric-label">收敛成功率</div>
            <div class="metric-change positive">+5.2%</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-value">{{ overallStats.totalExperiments }}</div>
            <div class="metric-label">总实验数</div>
            <div class="metric-change neutral">--</div>
          </div>
        </el-col>
      </el-row>
      
      <!-- 分析图表 -->
      <el-row :gutter="20" class="mt-4">
        <el-col :span="12">
          <div class="chart-section">
            <h4>性能分布分析</h4>
            <div class="chart-controls mb-2">
              <el-select v-model="selectedMetric" size="small" style="width: 120px;">
                <el-option label="QoE得分" value="qoe" />
                <el-option label="准入率" value="admission_rate" />
                <el-option label="公平性" value="fairness" />
                <el-option label="效率" value="efficiency" />
              </el-select>
            </div>
            <div ref="distributionChartRef" class="chart-container">
              性能分布直方图
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-section">
            <h4>参数相关性分析</h4>
            <div class="chart-controls mb-2">
              <el-select v-model="selectedParameter" size="small" style="width: 120px;">
                <el-option label="学习率" value="learning_rate" />
                <el-option label="批大小" value="batch_size" />
                <el-option label="网络层数" value="num_layers" />
                <el-option label="隐藏单元" value="hidden_units" />
              </el-select>
            </div>
            <div ref="correlationChartRef" class="chart-container">
              参数-性能相关性图
            </div>
          </div>
        </el-col>
      </el-row>
      
      <el-row :gutter="20" class="mt-4">
        <el-col :span="12">
          <div class="chart-section">
            <h4>收敛性分析</h4>
            <div ref="convergenceChartRef" class="chart-container">
              收敛曲线对比
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-section">
            <h4>统计显著性检验</h4>
            <div ref="significanceChartRef" class="chart-container">
              显著性检验结果
            </div>
          </div>
        </el-col>
      </el-row>
      
      <!-- 详细分析表格 -->
      <div class="detailed-analysis mt-4">
        <h4>详细分析结果</h4>
        <el-table :data="analysisResults" stripe border>
          <el-table-column prop="experiment" label="实验名称" width="200" />
          <el-table-column prop="configuration" label="配置" width="150" />
          <el-table-column prop="qoe" label="QoE" width="100" align="center">
            <template #default="{ row }">
              <span :class="getPerformanceClass(row.qoe, 'qoe')">
                {{ row.qoe.toFixed(3) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="admissionRate" label="准入率" width="100" align="center">
            <template #default="{ row }">
              <span :class="getPerformanceClass(row.admissionRate, 'admission')">
                {{ (row.admissionRate * 100).toFixed(1) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="fairness" label="公平性" width="100" align="center">
            <template #default="{ row }">
              <span :class="getPerformanceClass(row.fairness, 'fairness')">
                {{ row.fairness.toFixed(3) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="convergenceTime" label="收敛时间" width="120" align="center" />
          <el-table-column prop="stability" label="稳定性" width="100" align="center">
            <template #default="{ row }">
              <el-rate v-model="row.stability" disabled show-score />
            </template>
          </el-table-column>
          <el-table-column prop="significance" label="显著性" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getSignificanceType(row.significance)">
                {{ row.significance }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="viewExperimentDetail(row)">详情</el-button>
              <el-button size="small" @click="rerunExperiment(row)">重跑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 统计摘要 -->
      <div class="statistical-summary mt-4">
        <h4>统计摘要</h4>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card class="summary-card">
              <h5>最佳配置</h5>
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="学习率">0.001</el-descriptions-item>
                <el-descriptions-item label="批大小">32</el-descriptions-item>
                <el-descriptions-item label="网络层数">3</el-descriptions-item>
                <el-descriptions-item label="QoE得分">4.456</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="summary-card">
              <h5>性能统计</h5>
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="平均QoE">4.123 ± 0.234</el-descriptions-item>
                <el-descriptions-item label="最大提升">+15.6%</el-descriptions-item>
                <el-descriptions-item label="收敛率">92.3%</el-descriptions-item>
                <el-descriptions-item label="稳定性">4.2/5.0</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="summary-card">
              <h5>建议</h5>
              <ul class="recommendations">
                <li>推荐使用学习率0.001进行训练</li>
                <li>批大小32在大多数情况下表现最佳</li>
                <li>3层网络结构提供了最好的性能平衡</li>
                <li>建议进一步优化奖励函数设计</li>
              </ul>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

// 响应式数据
const selectedMetric = ref('qoe')
const selectedParameter = ref('learning_rate')

const overallStats = reactive({
  bestQoE: 4.456,
  avgImprovement: 12.3,
  convergenceRate: 92.3,
  totalExperiments: 48
})

const analysisResults = ref([
  {
    experiment: 'DRL-基线实验',
    configuration: 'lr=0.001, bs=32',
    qoe: 4.456,
    admissionRate: 0.943,
    fairness: 0.856,
    convergenceTime: '12.3min',
    stability: 4.2,
    significance: '***'
  },
  {
    experiment: 'DRL-消融-状态',
    configuration: 'lr=0.01, bs=64',
    qoe: 3.892,
    admissionRate: 0.891,
    fairness: 0.782,
    convergenceTime: '15.7min',
    stability: 3.8,
    significance: '**'
  },
  {
    experiment: 'DRL-消融-动作',
    configuration: 'lr=0.001, bs=16',
    qoe: 4.123,
    admissionRate: 0.923,
    fairness: 0.834,
    convergenceTime: '11.2min',
    stability: 4.0,
    significance: '**'
  }
])

// 方法
const refreshAnalysis = () => {
  ElMessage.success('分析结果已刷新')
}

const exportAnalysis = () => {
  ElMessage.success('分析报告导出成功')
}

const compareResults = () => {
  ElMessage.info('打开结果对比界面')
}

const getPerformanceClass = (value: number, type: string) => {
  const thresholds = {
    qoe: { good: 4.0, medium: 3.5 },
    admission: { good: 0.9, medium: 0.8 },
    fairness: { good: 0.8, medium: 0.7 }
  }
  
  const threshold = thresholds[type]
  if (!threshold) return ''
  
  if (value >= threshold.good) return 'performance-good'
  if (value >= threshold.medium) return 'performance-medium'
  return 'performance-poor'
}

const getSignificanceType = (significance: string) => {
  if (significance === '***') return 'danger'
  if (significance === '**') return 'warning'
  if (significance === '*') return 'info'
  return ''
}

const viewExperimentDetail = (row: any) => {
  ElMessage.info(`查看实验详情: ${row.experiment}`)
}

const rerunExperiment = (row: any) => {
  ElMessage.success(`重新运行实验: ${row.experiment}`)
}
</script>

<style scoped>
.results-analysis {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.analysis-overview {
  margin-bottom: 20px;
}

.metric-card {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.metric-change {
  font-size: 12px;
  font-weight: bold;
}

.metric-change.positive {
  color: #67c23a;
}

.metric-change.negative {
  color: #f56c6c;
}

.metric-change.neutral {
  color: #909399;
}

.chart-section h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #333;
}

.chart-controls {
  margin-bottom: 10px;
}

.chart-container {
  height: 250px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.detailed-analysis h4,
.statistical-summary h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.performance-good {
  color: #67c23a;
  font-weight: bold;
}

.performance-medium {
  color: #e6a23c;
  font-weight: bold;
}

.performance-poor {
  color: #f56c6c;
  font-weight: bold;
}

.summary-card h5 {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #333;
}

.recommendations {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: #666;
}

.recommendations li {
  margin-bottom: 8px;
}

.mt-4 {
  margin-top: 20px;
}

.mb-2 {
  margin-bottom: 10px;
}
</style>
