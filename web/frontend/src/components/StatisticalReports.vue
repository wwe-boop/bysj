<template>
  <div class="statistical-reports">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>统计报告</span>
          <el-button-group size="small">
            <el-button @click="generateReport">生成报告</el-button>
            <el-button @click="exportReport">导出PDF</el-button>
            <el-button @click="scheduleReport">定时报告</el-button>
          </el-button-group>
        </div>
      </template>
      
      <!-- 报告配置 -->
      <div class="report-config mb-4">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="报告类型">
              <el-select v-model="reportConfig.type" placeholder="选择报告类型">
                <el-option label="性能分析报告" value="performance" />
                <el-option label="实验对比报告" value="comparison" />
                <el-option label="趋势分析报告" value="trend" />
                <el-option label="综合评估报告" value="comprehensive" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="reportConfig.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                size="small"
              />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="包含指标">
              <el-select v-model="reportConfig.metrics" multiple placeholder="选择指标">
                <el-option label="QoE得分" value="qoe" />
                <el-option label="准入率" value="admission_rate" />
                <el-option label="公平性" value="fairness" />
                <el-option label="效率" value="efficiency" />
                <el-option label="稳定性" value="stability" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="报告格式">
              <el-select v-model="reportConfig.format" placeholder="选择格式">
                <el-option label="PDF" value="pdf" />
                <el-option label="Excel" value="excel" />
                <el-option label="Word" value="word" />
                <el-option label="HTML" value="html" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>
      
      <!-- 报告预览 -->
      <div class="report-preview">
        <h4>报告预览</h4>
        
        <!-- 执行摘要 -->
        <div class="report-section">
          <h5>执行摘要</h5>
          <div class="summary-content">
            <p>本报告分析了{{ reportPeriod }}期间的系统性能表现。主要发现包括：</p>
            <ul>
              <li>平均QoE得分达到{{ summaryStats.avgQoE }}，较上期提升{{ summaryStats.qoeImprovement }}%</li>
              <li>准入成功率为{{ summaryStats.admissionRate }}%，保持在高水平</li>
              <li>系统公平性指数为{{ summaryStats.fairnessIndex }}，表现良好</li>
              <li>共完成{{ summaryStats.totalExperiments }}个实验，成功率{{ summaryStats.successRate }}%</li>
            </ul>
          </div>
        </div>
        
        <!-- 关键指标 -->
        <div class="report-section">
          <h5>关键指标统计</h5>
          <el-table :data="keyMetrics" stripe border size="small">
            <el-table-column prop="metric" label="指标" width="150" />
            <el-table-column prop="current" label="当前值" width="100" />
            <el-table-column prop="previous" label="上期值" width="100" />
            <el-table-column prop="change" label="变化" width="100">
              <template #default="{ row }">
                <span :class="getChangeClass(row.change)">
                  {{ row.change > 0 ? '+' : '' }}{{ row.change }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="trend" label="趋势" width="100">
              <template #default="{ row }">
                <el-icon :class="getTrendClass(row.change)">
                  <component :is="getTrendIcon(row.change)" />
                </el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="target" label="目标值" width="100" />
            <el-table-column prop="status" label="达成状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <!-- 性能图表 -->
        <div class="report-section">
          <h5>性能趋势图表</h5>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="chart-container">
                <h6>QoE趋势</h6>
                <div class="chart-placeholder">QoE性能趋势图</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="chart-container">
                <h6>准入率趋势</h6>
                <div class="chart-placeholder">准入率趋势图</div>
              </div>
            </el-col>
          </el-row>
        </div>
        
        <!-- 实验分析 -->
        <div class="report-section">
          <h5>实验分析</h5>
          <div class="experiment-analysis">
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="analysis-item">
                  <h6>最佳实验配置</h6>
                  <el-descriptions :column="1" size="small" border>
                    <el-descriptions-item label="学习率">0.001</el-descriptions-item>
                    <el-descriptions-item label="批大小">32</el-descriptions-item>
                    <el-descriptions-item label="网络层数">3</el-descriptions-item>
                    <el-descriptions-item label="QoE得分">4.456</el-descriptions-item>
                  </el-descriptions>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="analysis-item">
                  <h6>参数敏感性分析</h6>
                  <ul class="sensitivity-list">
                    <li>学习率: 高敏感性 (影响度: 85%)</li>
                    <li>批大小: 中等敏感性 (影响度: 45%)</li>
                    <li>网络层数: 低敏感性 (影响度: 25%)</li>
                    <li>隐藏单元: 低敏感性 (影响度: 20%)</li>
                  </ul>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="analysis-item">
                  <h6>改进建议</h6>
                  <ul class="recommendations-list">
                    <li>优化学习率调度策略</li>
                    <li>探索自适应批大小方法</li>
                    <li>考虑引入注意力机制</li>
                    <li>增强奖励函数设计</li>
                  </ul>
                </div>
              </el-col>
            </el-row>
          </div>
        </div>
        
        <!-- 结论与建议 -->
        <div class="report-section">
          <h5>结论与建议</h5>
          <div class="conclusions">
            <h6>主要结论</h6>
            <ol>
              <li>DRL算法在LEO卫星网络准入控制中表现出色，QoE得分稳定在4.0以上</li>
              <li>系统在高负载情况下仍能保持较高的准入成功率和公平性</li>
              <li>参数优化对性能提升有显著影响，特别是学习率的选择</li>
            </ol>
            
            <h6>改进建议</h6>
            <ol>
              <li>建议采用自适应学习率策略，根据训练进度动态调整</li>
              <li>考虑引入多目标优化方法，平衡QoE和公平性</li>
              <li>增加更多场景下的测试，验证算法的泛化能力</li>
            </ol>
          </div>
        </div>
      </div>
    </el-card>
    
    <!-- 定时报告配置对话框 -->
    <el-dialog v-model="showScheduleDialog" title="定时报告配置" width="500px">
      <el-form :model="scheduleConfig" label-width="100px">
        <el-form-item label="报告名称">
          <el-input v-model="scheduleConfig.name" placeholder="输入报告名称" />
        </el-form-item>
        <el-form-item label="生成频率">
          <el-select v-model="scheduleConfig.frequency" placeholder="选择频率">
            <el-option label="每日" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="发送邮箱">
          <el-input v-model="scheduleConfig.email" placeholder="输入邮箱地址" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="scheduleConfig.enabled" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showScheduleDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSchedule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { TrendCharts, ArrowUp, ArrowDown, Minus } from '@element-plus/icons-vue'

// 响应式数据
const showScheduleDialog = ref(false)

const reportConfig = reactive({
  type: 'performance',
  dateRange: [],
  metrics: ['qoe', 'admission_rate', 'fairness'],
  format: 'pdf'
})

const scheduleConfig = reactive({
  name: '',
  frequency: 'weekly',
  email: '',
  enabled: true
})

const summaryStats = reactive({
  avgQoE: 4.23,
  qoeImprovement: 8.5,
  admissionRate: 94.2,
  fairnessIndex: 0.856,
  totalExperiments: 48,
  successRate: 95.8
})

const keyMetrics = ref([
  {
    metric: 'QoE得分',
    current: 4.23,
    previous: 3.89,
    change: 8.7,
    target: 4.0,
    status: '已达成'
  },
  {
    metric: '准入率',
    current: 94.2,
    previous: 92.1,
    change: 2.3,
    target: 90.0,
    status: '已达成'
  },
  {
    metric: '公平性指数',
    current: 0.856,
    previous: 0.834,
    change: 2.6,
    target: 0.8,
    status: '已达成'
  },
  {
    metric: '系统效率',
    current: 87.3,
    previous: 89.1,
    change: -2.0,
    target: 85.0,
    status: '已达成'
  }
])

// 计算属性
const reportPeriod = computed(() => {
  return '2024年1月1日至1月31日'
})

// 方法
const generateReport = () => {
  ElMessage.success('报告生成成功')
}

const exportReport = () => {
  ElMessage.success('报告导出成功')
}

const scheduleReport = () => {
  showScheduleDialog.value = true
}

const saveSchedule = () => {
  ElMessage.success('定时报告配置已保存')
  showScheduleDialog.value = false
}

const getChangeClass = (change: number) => {
  if (change > 0) return 'change-positive'
  if (change < 0) return 'change-negative'
  return 'change-neutral'
}

const getTrendClass = (change: number) => {
  if (change > 0) return 'trend-up'
  if (change < 0) return 'trend-down'
  return 'trend-neutral'
}

const getTrendIcon = (change: number) => {
  if (change > 0) return ArrowUp
  if (change < 0) return ArrowDown
  return Minus
}

const getStatusType = (status: string) => {
  if (status === '已达成') return 'success'
  if (status === '未达成') return 'danger'
  return 'warning'
}
</script>

<style scoped>
.statistical-reports {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-config {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 4px;
}

.report-preview {
  margin-top: 20px;
}

.report-preview h4 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #333;
}

.report-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.report-section h5 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
  border-bottom: 2px solid #409eff;
  padding-bottom: 8px;
}

.report-section h6 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #666;
}

.summary-content p {
  margin-bottom: 10px;
  line-height: 1.6;
}

.summary-content ul {
  margin: 0;
  padding-left: 20px;
}

.summary-content li {
  margin-bottom: 8px;
  line-height: 1.5;
}

.change-positive {
  color: #67c23a;
  font-weight: bold;
}

.change-negative {
  color: #f56c6c;
  font-weight: bold;
}

.change-neutral {
  color: #909399;
}

.trend-up {
  color: #67c23a;
}

.trend-down {
  color: #f56c6c;
}

.trend-neutral {
  color: #909399;
}

.chart-container {
  margin-bottom: 20px;
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

.analysis-item {
  padding: 15px;
  background: #f9f9f9;
  border-radius: 4px;
  height: 100%;
}

.sensitivity-list,
.recommendations-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
}

.sensitivity-list li,
.recommendations-list li {
  margin-bottom: 8px;
  line-height: 1.4;
}

.conclusions h6 {
  margin: 15px 0 10px 0;
  font-size: 14px;
  color: #333;
}

.conclusions ol {
  margin: 0;
  padding-left: 20px;
}

.conclusions li {
  margin-bottom: 8px;
  line-height: 1.5;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
