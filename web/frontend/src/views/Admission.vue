<template>
  <div class="admission">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="24">
        <h1 class="page-title">
          <el-icon><Key /></el-icon>
          准入控制
        </h1>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 控制面板 -->
      <el-col :xs="24" :lg="8">
        <el-card class="control-panel">
          <template #header>
            <span>准入控制配置</span>
          </template>
          
          <!-- 算法选择 -->
          <div class="config-section">
            <h4>算法配置</h4>
            <el-form :model="config" label-width="120px" size="small">
              <el-form-item label="准入算法">
                <el-select v-model="config.algorithm" style="width: 100%">
                  <el-option
                    v-for="algo in algorithms"
                    :key="algo.name"
                    :label="algo.displayName"
                    :value="algo.name"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item label="最大用户数">
                <el-input-number
                  v-model="config.maxUsersPerSatellite"
                  :min="1"
                  :max="1000"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="信号强度阈值">
                <el-input-number
                  v-model="config.minSignalStrengthDbm"
                  :min="-150"
                  :max="-50"
                  :step="1"
                  style="width: 100%"
                />
                <span class="unit">dBm</span>
              </el-form-item>
              
              <el-form-item label="定位权重">
                <el-slider
                  v-model="config.positioningWeight"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  show-input
                />
              </el-form-item>
            </el-form>
            
            <div class="config-actions">
              <el-button type="primary" @click="updateConfig" :loading="configLoading">
                应用配置
              </el-button>
              <el-button @click="resetConfig">
                重置
              </el-button>
            </div>
          </div>

          <!-- 测试请求 -->
          <div class="config-section">
            <h4>测试准入请求</h4>
            <el-form :model="testRequest" label-width="120px" size="small">
              <el-form-item label="用户ID">
                <el-input v-model="testRequest.userId" />
              </el-form-item>
              
              <el-form-item label="服务类型">
                <el-select v-model="testRequest.serviceType" style="width: 100%">
                  <el-option label="数据传输" value="data" />
                  <el-option label="语音通话" value="voice" />
                  <el-option label="视频通话" value="video" />
                  <el-option label="紧急服务" value="emergency" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="带宽需求">
                <el-input-number
                  v-model="testRequest.bandwidthMbps"
                  :min="0.1"
                  :max="1000"
                  :step="0.1"
                  style="width: 100%"
                />
                <span class="unit">Mbps</span>
              </el-form-item>
              
              <el-form-item label="延迟要求">
                <el-input-number
                  v-model="testRequest.maxLatencyMs"
                  :min="1"
                  :max="1000"
                  style="width: 100%"
                />
                <span class="unit">ms</span>
              </el-form-item>
              
              <el-form-item label="用户位置">
                <el-row :gutter="10">
                  <el-col :span="12">
                    <el-input-number
                      v-model="testRequest.userLat"
                      :min="-90"
                      :max="90"
                      :step="0.1"
                      placeholder="纬度"
                      style="width: 100%"
                    />
                  </el-col>
                  <el-col :span="12">
                    <el-input-number
                      v-model="testRequest.userLon"
                      :min="-180"
                      :max="180"
                      :step="0.1"
                      placeholder="经度"
                      style="width: 100%"
                    />
                  </el-col>
                </el-row>
              </el-form-item>
              
              <el-form-item label="优先级">
                <el-slider
                  v-model="testRequest.priority"
                  :min="1"
                  :max="10"
                  show-input
                />
              </el-form-item>
            </el-form>
            
            <div class="config-actions">
              <el-button type="success" @click="submitTestRequest" :loading="testLoading">
                提交测试
              </el-button>
              <el-button @click="generateRandomRequest">
                随机生成
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 统计和结果 -->
      <el-col :xs="24" :lg="16">
        <!-- 统计信息 -->
        <el-card class="mb-4">
          <template #header>
            <span>准入统计</span>
          </template>
          <AdmissionStats :loading="statsLoading" />
        </el-card>

        <!-- 测试结果 -->
        <el-card v-if="testResult" class="mb-4">
          <template #header>
            <span>测试结果</span>
          </template>
          <div class="test-result">
            <div class="result-header">
              <el-tag :type="getResultType(testResult.decision)" size="large">
                {{ getDecisionText(testResult.decision) }}
              </el-tag>
              <span class="confidence">置信度: {{ (testResult.confidence * 100).toFixed(1) }}%</span>
            </div>
            <div class="result-details">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="分配卫星">
                  {{ testResult.allocatedSatellite || '无' }}
                </el-descriptions-item>
                <el-descriptions-item label="分配带宽">
                  {{ testResult.allocatedBandwidth ? `${testResult.allocatedBandwidth} Mbps` : '无' }}
                </el-descriptions-item>
                <el-descriptions-item label="决策原因" :span="2">
                  {{ testResult.reason }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </el-card>

        <!-- 历史记录 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>准入历史</span>
              <el-button size="small" @click="refreshHistory" :icon="Refresh">
                刷新
              </el-button>
            </div>
          </template>
          <el-table
            :data="history"
            :loading="historyLoading"
            stripe
            style="width: 100%"
            max-height="300"
          >
            <el-table-column prop="timestamp" label="时间" width="120">
              <template #default="{ row }">
                {{ formatTime(row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column prop="userId" label="用户ID" width="100" />
            <el-table-column prop="serviceType" label="服务类型" width="100" />
            <el-table-column prop="decision" label="决策结果" width="100">
              <template #default="{ row }">
                <el-tag :type="getResultType(row.decision)" size="small">
                  {{ getDecisionText(row.decision) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="80">
              <template #default="{ row }">
                {{ (row.confidence * 100).toFixed(0) }}%
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { admissionApi } from '@/api/admission'
import AdmissionStats from '@/components/AdmissionStats.vue'
import { Key, Refresh } from '@element-plus/icons-vue'
import type { UserRequest, AdmissionResult } from '@/types'

// 状态管理
const appStore = useAppStore()

// 响应式数据
const config = ref({
  algorithm: 'threshold',
  maxUsersPerSatellite: 100,
  minSignalStrengthDbm: -120,
  positioningWeight: 0.3
})

const testRequest = ref<Partial<UserRequest>>({
  userId: 'test_user_001',
  serviceType: 'data',
  bandwidthMbps: 10,
  maxLatencyMs: 100,
  minReliability: 0.95,
  priority: 5,
  userLat: 39.9,
  userLon: 116.4,
  durationSeconds: 300
})

const algorithms = ref<any[]>([])
const testResult = ref<AdmissionResult | null>(null)
const history = ref<any[]>([])

const configLoading = ref(false)
const testLoading = ref(false)
const statsLoading = ref(false)
const historyLoading = ref(false)

// 方法
const loadConfig = async () => {
  try {
    const result = await admissionApi.getConfig()
    Object.assign(config.value, result)
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const loadAlgorithms = async () => {
  try {
    algorithms.value = await admissionApi.getAvailableAlgorithms()
  } catch (error) {
    console.error('加载算法列表失败:', error)
  }
}

const updateConfig = async () => {
  configLoading.value = true
  try {
    await admissionApi.updateConfig(config.value)
    appStore.addNotification({
      type: 'success',
      title: '配置更新',
      message: '准入控制配置已更新'
    })
  } catch (error) {
    console.error('更新配置失败:', error)
  } finally {
    configLoading.value = false
  }
}

const resetConfig = () => {
  loadConfig()
}

const submitTestRequest = async () => {
  testLoading.value = true
  try {
    testResult.value = await admissionApi.processRequest(testRequest.value as UserRequest)
    refreshHistory()
  } catch (error) {
    console.error('提交测试请求失败:', error)
  } finally {
    testLoading.value = false
  }
}

const generateRandomRequest = () => {
  testRequest.value = {
    userId: `test_user_${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`,
    serviceType: ['data', 'voice', 'video', 'emergency'][Math.floor(Math.random() * 4)],
    bandwidthMbps: Math.round((Math.random() * 100 + 1) * 10) / 10,
    maxLatencyMs: Math.floor(Math.random() * 500 + 50),
    minReliability: Math.round((Math.random() * 0.3 + 0.7) * 100) / 100,
    priority: Math.floor(Math.random() * 10 + 1),
    userLat: Math.round((Math.random() * 180 - 90) * 10) / 10,
    userLon: Math.round((Math.random() * 360 - 180) * 10) / 10,
    durationSeconds: Math.floor(Math.random() * 600 + 60)
  }
}

const refreshHistory = async () => {
  historyLoading.value = true
  try {
    const result = await admissionApi.getHistory(20, 0)
    history.value = result.records || []
  } catch (error) {
    console.error('加载历史记录失败:', error)
  } finally {
    historyLoading.value = false
  }
}

const getResultType = (decision: string) => {
  const typeMap: Record<string, string> = {
    'accept': 'success',
    'reject': 'danger',
    'degraded_accept': 'warning',
    'delayed_accept': 'info',
    'partial_accept': 'warning'
  }
  return typeMap[decision] || 'info'
}

const getDecisionText = (decision: string) => {
  const textMap: Record<string, string> = {
    'accept': '接受',
    'reject': '拒绝',
    'degraded_accept': '降级接受',
    'delayed_accept': '延迟接受',
    'partial_accept': '部分接受'
  }
  return textMap[decision] || decision
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleTimeString()
}

// 生命周期
onMounted(async () => {
  await Promise.all([
    loadConfig(),
    loadAlgorithms(),
    refreshHistory()
  ])
})
</script>

<style scoped>
.admission {
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

.control-panel {
  height: fit-content;
}

.config-section {
  margin-bottom: 24px;
}

.config-section h4 {
  margin: 0 0 12px 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.unit {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.config-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.test-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.confidence {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
