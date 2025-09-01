<template>
  <div class="drl-training">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="24">
        <h1 class="page-title">
          <el-icon><BrainFilled /></el-icon>
          DRL准入控制训练
        </h1>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 训练控制面板 -->
      <el-col :xs="24" :lg="8">
        <el-card class="control-panel">
          <template #header>
            <span>训练配置</span>
          </template>
          
          <!-- 算法配置 -->
          <div class="config-section">
            <h4>算法参数</h4>
            <el-form :model="trainingConfig" label-width="120px" size="small">
              <el-form-item label="算法类型">
                <el-select v-model="trainingConfig.algorithm" style="width: 100%">
                  <el-option label="PPO" value="PPO" />
                  <el-option label="A2C" value="A2C" />
                  <el-option label="SAC" value="SAC" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="学习率">
                <el-input-number
                  v-model="trainingConfig.learningRate"
                  :min="1e-6"
                  :max="1e-2"
                  :step="1e-5"
                  :precision="6"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="批次大小">
                <el-input-number
                  v-model="trainingConfig.batchSize"
                  :min="16"
                  :max="512"
                  :step="16"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="训练步数">
                <el-input-number
                  v-model="trainingConfig.nSteps"
                  :min="256"
                  :max="8192"
                  :step="256"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="训练轮数">
                <el-input-number
                  v-model="trainingConfig.nEpochs"
                  :min="1"
                  :max="50"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="折扣因子">
                <el-slider
                  v-model="trainingConfig.gamma"
                  :min="0.9"
                  :max="0.999"
                  :step="0.001"
                  show-input
                />
              </el-form-item>
            </el-form>
          </div>

          <!-- 奖励函数配置 -->
          <div class="config-section">
            <h4>奖励函数权重</h4>
            <el-form label-width="120px" size="small">
              <el-form-item label="QoE权重">
                <el-slider
                  v-model="rewardWeights.qoe_weight"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  show-input
                  @change="normalizeWeights"
                />
              </el-form-item>
              
              <el-form-item label="公平性权重">
                <el-slider
                  v-model="rewardWeights.fairness_weight"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  show-input
                  @change="normalizeWeights"
                />
              </el-form-item>
              
              <el-form-item label="效率权重">
                <el-slider
                  v-model="rewardWeights.efficiency_weight"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  show-input
                  @change="normalizeWeights"
                />
              </el-form-item>
              
              <el-form-item label="稳定性权重">
                <el-slider
                  v-model="rewardWeights.stability_weight"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  show-input
                  @change="normalizeWeights"
                />
              </el-form-item>
              
              <el-form-item label="定位权重">
                <el-slider
                  v-model="rewardWeights.positioning_weight"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  show-input
                  @change="normalizeWeights"
                />
              </el-form-item>
              
              <div class="weight-sum">
                权重总和: {{ weightSum.toFixed(3) }}
                <el-tag :type="weightSum === 1 ? 'success' : 'warning'" size="small">
                  {{ weightSum === 1 ? '正确' : '需调整' }}
                </el-tag>
              </div>
            </el-form>
          </div>

          <!-- 训练控制 -->
          <div class="config-section">
            <h4>训练控制</h4>
            <div class="control-buttons">
              <el-button
                type="success"
                :icon="VideoPlay"
                @click="startTraining"
                :disabled="trainingStatus.isTraining || weightSum !== 1"
                :loading="startLoading"
                style="width: 100%"
              >
                开始训练
              </el-button>
              <el-button
                type="danger"
                :icon="VideoPause"
                @click="stopTraining"
                :disabled="!trainingStatus.isTraining"
                :loading="stopLoading"
                style="width: 100%"
              >
                停止训练
              </el-button>
              <el-button
                type="info"
                :icon="Refresh"
                @click="loadTrainingStatus"
                :loading="statusLoading"
                style="width: 100%"
              >
                刷新状态
              </el-button>
            </div>
          </div>

          <!-- 训练状态 -->
          <div class="config-section">
            <h4>训练状态</h4>
            <div class="status-display">
              <div class="status-item">
                <span class="label">状态:</span>
                <el-tag :type="trainingStatus.isTraining ? 'success' : 'info'" size="small">
                  {{ trainingStatus.isTraining ? '训练中' : '未训练' }}
                </el-tag>
              </div>
              <div class="status-item">
                <span class="label">当前轮次:</span>
                <span class="value">{{ trainingStatus.episode || 0 }}</span>
              </div>
              <div class="status-item">
                <span class="label">总轮次:</span>
                <span class="value">{{ trainingStatus.totalEpisodes || 0 }}</span>
              </div>
              <div class="status-item">
                <span class="label">当前奖励:</span>
                <span class="value">{{ formatReward(trainingStatus.currentReward) }}</span>
              </div>
              <div class="status-item">
                <span class="label">平均奖励:</span>
                <span class="value">{{ formatReward(trainingStatus.averageReward) }}</span>
              </div>
              <div class="status-item">
                <span class="label">探索率:</span>
                <span class="value">{{ formatPercentage(trainingStatus.explorationRate) }}</span>
              </div>
            </div>
            <el-progress
              v-if="trainingStatus.totalEpisodes > 0"
              :percentage="(trainingStatus.episode / trainingStatus.totalEpisodes) * 100"
              :stroke-width="12"
              :show-text="false"
              class="progress-bar"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 训练监控 -->
      <el-col :xs="24" :lg="16">
        <!-- 训练指标 -->
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>训练指标</span>
              <el-button-group size="small">
                <el-button :icon="Refresh" @click="loadTrainingMetrics">刷新</el-button>
                <el-button :icon="Download" @click="exportMetrics">导出</el-button>
              </el-button-group>
            </div>
          </template>
          <DRLTrainingChart
            :data="trainingMetrics"
            :loading="metricsLoading"
            height="300px"
          />
        </el-card>

        <!-- 环境状态 -->
        <el-card class="mb-4">
          <template #header>
            <span>环境状态</span>
          </template>
          <DRLEnvironmentState
            :state="environmentState"
            :loading="envLoading"
          />
        </el-card>

        <!-- 奖励分解 -->
        <el-card>
          <template #header>
            <span>奖励函数分解</span>
          </template>
          <RewardBreakdown
            :weights="rewardWeights"
            :components="rewardComponents"
            :loading="rewardLoading"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { drlApi } from '@/api/drl'
import DRLTrainingChart from '@/components/DRLTrainingChart.vue'
import DRLEnvironmentState from '@/components/DRLEnvironmentState.vue'
import RewardBreakdown from '@/components/RewardBreakdown.vue'
import {
  BrainFilled,
  VideoPlay,
  VideoPause,
  Refresh,
  Download
} from '@element-plus/icons-vue'

// 状态管理
const appStore = useAppStore()

// 响应式数据
const trainingConfig = ref({
  algorithm: 'PPO',
  learningRate: 3e-4,
  batchSize: 64,
  nSteps: 2048,
  nEpochs: 10,
  gamma: 0.99,
  clipRange: 0.2,
  useRealEnvironment: true,
  maxEpisodeSteps: 1000,
  evaluationFreq: 10
})

const rewardWeights = ref({
  qoe_weight: 0.4,
  fairness_weight: 0.2,
  efficiency_weight: 0.2,
  stability_weight: 0.1,
  positioning_weight: 0.1
})

const trainingStatus = ref({
  isTraining: false,
  trainingId: null,
  episode: 0,
  totalEpisodes: 0,
  currentReward: 0.0,
  averageReward: 0.0,
  loss: 0.0,
  explorationRate: 0.1,
  trainingTime: 0.0
})

const trainingMetrics = ref({
  episodes: [],
  rewards: [],
  losses: [],
  qoeScores: [],
  fairnessScores: [],
  efficiencyScores: []
})

const environmentState = ref({})
const rewardComponents = ref({})

const startLoading = ref(false)
const stopLoading = ref(false)
const statusLoading = ref(false)
const metricsLoading = ref(false)
const envLoading = ref(false)
const rewardLoading = ref(false)

// 计算属性
const weightSum = computed(() => {
  return Object.values(rewardWeights.value).reduce((sum, weight) => sum + weight, 0)
})

// 方法
const normalizeWeights = () => {
  // 可选：自动归一化权重
  // const sum = weightSum.value
  // if (sum > 0) {
  //   Object.keys(rewardWeights.value).forEach(key => {
  //     rewardWeights.value[key] = rewardWeights.value[key] / sum
  //   })
  // }
}

const startTraining = async () => {
  if (weightSum.value !== 1) {
    ElMessage.warning('奖励权重总和必须为1.0')
    return
  }

  startLoading.value = true
  try {
    const config = {
      ...trainingConfig.value,
      rewardWeights: rewardWeights.value
    }
    
    await drlApi.startTraining(config)
    await loadTrainingStatus()
    
    appStore.addNotification({
      type: 'success',
      title: 'DRL训练',
      message: 'DRL训练已启动'
    })
  } catch (error) {
    console.error('启动训练失败:', error)
  } finally {
    startLoading.value = false
  }
}

const stopTraining = async () => {
  stopLoading.value = true
  try {
    await drlApi.stopTraining(trainingStatus.value.trainingId)
    await loadTrainingStatus()
    
    appStore.addNotification({
      type: 'warning',
      title: 'DRL训练',
      message: 'DRL训练已停止'
    })
  } catch (error) {
    console.error('停止训练失败:', error)
  } finally {
    stopLoading.value = false
  }
}

const loadTrainingStatus = async () => {
  statusLoading.value = true
  try {
    trainingStatus.value = await drlApi.getTrainingStatus()
  } catch (error) {
    console.error('获取训练状态失败:', error)
  } finally {
    statusLoading.value = false
  }
}

const loadTrainingMetrics = async () => {
  metricsLoading.value = true
  try {
    trainingMetrics.value = await drlApi.getTrainingMetrics()
  } catch (error) {
    console.error('获取训练指标失败:', error)
  } finally {
    metricsLoading.value = false
  }
}

const loadEnvironmentState = async () => {
  envLoading.value = true
  try {
    environmentState.value = await drlApi.getEnvironmentState()
  } catch (error) {
    console.error('获取环境状态失败:', error)
  } finally {
    envLoading.value = false
  }
}

const loadRewardConfig = async () => {
  rewardLoading.value = true
  try {
    const config = await drlApi.getRewardConfig()
    rewardWeights.value = config.rewardWeights
    rewardComponents.value = config.rewardComponents
  } catch (error) {
    console.error('获取奖励配置失败:', error)
  } finally {
    rewardLoading.value = false
  }
}

const exportMetrics = () => {
  const data = {
    trainingConfig: trainingConfig.value,
    rewardWeights: rewardWeights.value,
    trainingStatus: trainingStatus.value,
    trainingMetrics: trainingMetrics.value,
    timestamp: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `drl_training_metrics_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const formatReward = (reward: number) => {
  return reward?.toFixed(4) || '0.0000'
}

const formatPercentage = (value: number) => {
  return `${(value * 100).toFixed(1)}%`
}

// 生命周期
onMounted(async () => {
  await Promise.all([
    loadTrainingStatus(),
    loadTrainingMetrics(),
    loadEnvironmentState(),
    loadRewardConfig()
  ])
  
  // 定期刷新状态
  const statusTimer = setInterval(() => {
    if (trainingStatus.value.isTraining) {
      loadTrainingStatus()
      loadTrainingMetrics()
    }
  }, 5000)
  
  onUnmounted(() => {
    clearInterval(statusTimer)
  })
})
</script>

<style scoped>
.drl-training {
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

.control-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-display {
  margin-bottom: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.status-item .label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.status-item .value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.weight-sum {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding: 8px;
  background: var(--el-bg-color-page);
  border-radius: 4px;
  font-size: 14px;
}

.progress-bar {
  margin-top: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
