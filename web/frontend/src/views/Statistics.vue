<template>
  <div class="statistics-view">
    <div class="page-header">
      <h1>统计分析</h1>
      <p>系统性能统计与数据分析</p>
    </div>

    <!-- 统计概览 -->
    <el-row :gutter="20" class="stats-overview">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ overviewStats.totalUsers }}</div>
            <div class="stat-label">总用户数</div>
            <div class="stat-change positive">+12.5%</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ overviewStats.avgQoE }}</div>
            <div class="stat-label">平均QoE</div>
            <div class="stat-change positive">+3.2%</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ overviewStats.admissionRate }}%</div>
            <div class="stat-label">准入成功率</div>
            <div class="stat-change negative">-1.8%</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ overviewStats.avgLatency }}ms</div>
            <div class="stat-label">平均延迟</div>
            <div class="stat-change positive">-5.3%</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="mt-4">
      <el-col :span="12">
        <el-card title="QoE趋势分析">
          <template #header>
            <div class="card-header">
              <span>QoE趋势分析</span>
              <el-select v-model="qoeTimeRange" size="small" style="width: 120px;">
                <el-option label="最近1小时" value="1h" />
                <el-option label="最近6小时" value="6h" />
                <el-option label="最近24小时" value="24h" />
                <el-option label="最近7天" value="7d" />
              </el-select>
            </div>
          </template>
          <div ref="qoeChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card title="准入统计">
          <template #header>
            <div class="card-header">
              <span>准入统计</span>
              <el-button-group size="small">
                <el-button :type="admissionView === 'rate' ? 'primary' : ''" @click="admissionView = 'rate'">
                  成功率
                </el-button>
                <el-button :type="admissionView === 'count' ? 'primary' : ''" @click="admissionView = 'count'">
                  数量
                </el-button>
              </el-button-group>
            </div>
          </template>
          <div ref="admissionChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-4">
      <el-col :span="8">
        <el-card title="用户分布">
          <div ref="userDistributionRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card title="网络性能">
          <div class="performance-metrics">
            <div class="metric-item">
              <span class="metric-label">吞吐量:</span>
              <span class="metric-value">1.2 Gbps</span>
              <el-progress :percentage="75" color="#67c23a" />
            </div>
            <div class="metric-item">
              <span class="metric-label">丢包率:</span>
              <span class="metric-value">0.02%</span>
              <el-progress :percentage="2" color="#f56c6c" />
            </div>
            <div class="metric-item">
              <span class="metric-label">延迟:</span>
              <span class="metric-value">45ms</span>
              <el-progress :percentage="30" color="#e6a23c" />
            </div>
            <div class="metric-item">
              <span class="metric-label">抖动:</span>
              <span class="metric-value">2.1ms</span>
              <el-progress :percentage="15" color="#409eff" />
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card title="系统状态">
          <div class="system-status">
            <div class="status-item">
              <el-icon class="status-icon online"><SuccessFilled /></el-icon>
              <span>在线卫星: 66/66</span>
            </div>
            <div class="status-item">
              <el-icon class="status-icon warning"><WarningFilled /></el-icon>
              <span>告警数量: 3</span>
            </div>
            <div class="status-item">
              <el-icon class="status-icon normal"><InfoFilled /></el-icon>
              <span>活跃连接: 1,234</span>
            </div>
            <div class="status-item">
              <el-icon class="status-icon normal"><CircleCheckFilled /></el-icon>
              <span>系统负载: 68%</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细统计表格 -->
    <el-card class="mt-4" title="详细统计">
      <template #header>
        <div class="card-header">
          <span>详细统计</span>
          <el-button-group size="small">
            <el-button @click="exportStats">导出数据</el-button>
            <el-button @click="refreshStats">刷新</el-button>
          </el-button-group>
        </div>
      </template>
      
      <el-table :data="detailedStats" stripe>
        <el-table-column prop="time" label="时间" width="150" />
        <el-table-column prop="users" label="用户数" width="100" />
        <el-table-column prop="qoe" label="平均QoE" width="100" />
        <el-table-column prop="admissionRate" label="准入率" width="100">
          <template #default="{ row }">
            {{ row.admissionRate }}%
          </template>
        </el-table-column>
        <el-table-column prop="latency" label="延迟(ms)" width="100" />
        <el-table-column prop="throughput" label="吞吐量(Mbps)" width="120" />
        <el-table-column prop="packetLoss" label="丢包率" width="100">
          <template #default="{ row }">
            {{ row.packetLoss }}%
          </template>
        </el-table-column>
        <el-table-column prop="fairness" label="公平性指数" width="120" />
        <el-table-column prop="efficiency" label="效率" width="100">
          <template #default="{ row }">
            {{ row.efficiency }}%
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  SuccessFilled, 
  WarningFilled, 
  InfoFilled, 
  CircleCheckFilled 
} from '@element-plus/icons-vue'

// 响应式数据
const qoeChartRef = ref()
const admissionChartRef = ref()
const userDistributionRef = ref()

const qoeTimeRange = ref('6h')
const admissionView = ref('rate')

const overviewStats = reactive({
  totalUsers: 8456,
  avgQoE: 4.2,
  admissionRate: 94.5,
  avgLatency: 45
})

const detailedStats = ref([
  {
    time: '14:00',
    users: 8456,
    qoe: 4.2,
    admissionRate: 94.5,
    latency: 45,
    throughput: 1200,
    packetLoss: 0.02,
    fairness: 0.85,
    efficiency: 92
  },
  {
    time: '13:00',
    users: 8234,
    qoe: 4.1,
    admissionRate: 93.8,
    latency: 48,
    throughput: 1150,
    packetLoss: 0.03,
    fairness: 0.83,
    efficiency: 90
  },
  {
    time: '12:00',
    users: 7892,
    qoe: 4.3,
    admissionRate: 95.2,
    latency: 42,
    throughput: 1180,
    packetLoss: 0.01,
    fairness: 0.87,
    efficiency: 94
  }
])

// 方法
const exportStats = () => {
  ElMessage.success('统计数据导出成功')
}

const refreshStats = () => {
  ElMessage.success('统计数据已刷新')
}

onMounted(() => {
  // 初始化图表
  initCharts()
})

const initCharts = () => {
  // 这里将集成ECharts或其他图表库
  console.log('初始化图表')
}
</script>

<style scoped>
.statistics-view {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  color: #333;
}

.page-header p {
  margin: 0;
  color: #666;
}

.stats-overview {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  padding: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.stat-change {
  font-size: 12px;
  font-weight: bold;
}

.stat-change.positive {
  color: #67c23a;
}

.stat-change.negative {
  color: #f56c6c;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 4px;
  color: #909399;
}

.performance-metrics {
  padding: 10px;
}

.metric-item {
  margin-bottom: 20px;
}

.metric-label {
  display: inline-block;
  width: 80px;
  font-size: 14px;
  color: #666;
}

.metric-value {
  display: inline-block;
  width: 80px;
  font-weight: bold;
  color: #333;
}

.system-status {
  padding: 10px;
}

.status-item {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  font-size: 14px;
}

.status-icon {
  margin-right: 8px;
  font-size: 16px;
}

.status-icon.online {
  color: #67c23a;
}

.status-icon.warning {
  color: #e6a23c;
}

.status-icon.normal {
  color: #409eff;
}

.mt-4 {
  margin-top: 20px;
}
</style>
