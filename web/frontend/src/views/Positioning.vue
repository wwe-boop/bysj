<template>
  <div class="positioning">
    <el-row :gutter="20" class="mb-4">
      <el-col :span="24">
        <h1 class="page-title">
          <el-icon><Location /></el-icon>
          定位服务
        </h1>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 控制面板 -->
      <el-col :xs="24" :lg="8">
        <el-card class="control-panel">
          <template #header>
            <span>定位配置</span>
          </template>
          
          <!-- 定位参数 -->
          <div class="config-section">
            <h4>定位参数</h4>
            <el-form :model="config" label-width="120px" size="small">
              <el-form-item label="仰角掩码">
                <el-input-number
                  v-model="config.elevationMaskDeg"
                  :min="0"
                  :max="90"
                  :step="1"
                  style="width: 100%"
                />
                <span class="unit">度</span>
              </el-form-item>
              
              <el-form-item label="GDOP阈值">
                <el-input-number
                  v-model="config.maxGdopThreshold"
                  :min="1"
                  :max="50"
                  :step="0.1"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="最少卫星数">
                <el-input-number
                  v-model="config.minVisibleSatellites"
                  :min="3"
                  :max="20"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="信噪比">
                <el-input-number
                  v-model="config.signalNoiseRatio"
                  :min="10"
                  :max="50"
                  :step="0.1"
                  style="width: 100%"
                />
                <span class="unit">dB</span>
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

          <!-- 定位测试 -->
          <div class="config-section">
            <h4>定位测试</h4>
            <el-form :model="testRequest" label-width="120px" size="small">
              <el-form-item label="用户ID">
                <el-input v-model="testRequest.userId" />
              </el-form-item>
              
              <el-form-item label="纬度">
                <el-input-number
                  v-model="testRequest.lat"
                  :min="-90"
                  :max="90"
                  :step="0.001"
                  :precision="3"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="经度">
                <el-input-number
                  v-model="testRequest.lon"
                  :min="-180"
                  :max="180"
                  :step="0.001"
                  :precision="3"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="精度要求">
                <el-input-number
                  v-model="testRequest.accuracy"
                  :min="0.1"
                  :max="1000"
                  :step="0.1"
                  style="width: 100%"
                />
                <span class="unit">米</span>
              </el-form-item>
            </el-form>
            
            <div class="config-actions">
              <el-button type="success" @click="submitTestRequest" :loading="testLoading">
                测试定位
              </el-button>
              <el-button @click="generateRandomLocation">
                随机位置
              </el-button>
            </div>
          </div>

          <!-- 质量查询 -->
          <div class="config-section">
            <h4>定位质量查询</h4>
            <el-form :model="qualityQuery" label-width="120px" size="small">
              <el-form-item label="查询纬度">
                <el-input-number
                  v-model="qualityQuery.lat"
                  :min="-90"
                  :max="90"
                  :step="0.1"
                  style="width: 100%"
                />
              </el-form-item>
              
              <el-form-item label="查询经度">
                <el-input-number
                  v-model="qualityQuery.lon"
                  :min="-180"
                  :max="180"
                  :step="0.1"
                  style="width: 100%"
                />
              </el-form-item>
            </el-form>
            
            <div class="config-actions">
              <el-button type="info" @click="queryQuality" :loading="qualityLoading">
                查询质量
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 结果和统计 -->
      <el-col :xs="24" :lg="16">
        <!-- 定位结果 -->
        <el-card v-if="testResult" class="mb-4">
          <template #header>
            <span>定位结果</span>
          </template>
          <div class="positioning-result">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-descriptions title="定位信息" :column="1" border>
                  <el-descriptions-item label="用户ID">
                    {{ testResult.userId }}
                  </el-descriptions-item>
                  <el-descriptions-item label="估计纬度">
                    {{ testResult.estimatedLat.toFixed(6) }}°
                  </el-descriptions-item>
                  <el-descriptions-item label="估计经度">
                    {{ testResult.estimatedLon.toFixed(6) }}°
                  </el-descriptions-item>
                  <el-descriptions-item label="定位精度">
                    {{ testResult.accuracy.toFixed(2) }} 米
                  </el-descriptions-item>
                  <el-descriptions-item label="GDOP值">
                    {{ testResult.gdop.toFixed(2) }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>
              <el-col :span="12">
                <el-descriptions title="卫星信息" :column="1" border>
                  <el-descriptions-item label="可见卫星数">
                    {{ testResult.visibleSatellites.length }}
                  </el-descriptions-item>
                  <el-descriptions-item label="平均信号强度">
                    {{ getAverageSignalStrength(testResult.signalStrength).toFixed(1) }} dBm
                  </el-descriptions-item>
                  <el-descriptions-item label="定位时间">
                    {{ formatTime(testResult.timestamp) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="质量等级">
                    <el-tag :type="getQualityType(testResult.gdop)">
                      {{ getQualityText(testResult.gdop) }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>
            </el-row>
          </div>
        </el-card>

        <!-- 质量查询结果 -->
        <el-card v-if="qualityResult" class="mb-4">
          <template #header>
            <span>定位质量</span>
          </template>
          <div class="quality-result">
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="quality-metric">
                  <div class="metric-value">{{ qualityResult.gdop.toFixed(2) }}</div>
                  <div class="metric-label">GDOP值</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="quality-metric">
                  <div class="metric-value">{{ qualityResult.accuracy.toFixed(1) }}m</div>
                  <div class="metric-label">预期精度</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="quality-metric">
                  <div class="metric-value">{{ qualityResult.visibleSatellitesCount }}</div>
                  <div class="metric-label">可见卫星</div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>

        <!-- 统计信息 -->
        <el-card class="mb-4">
          <template #header>
            <span>定位统计</span>
          </template>
          <PositioningStats :loading="statsLoading" />
        </el-card>

        <!-- 覆盖范围 -->
        <el-card>
          <template #header>
            <div class="card-header">
              <span>覆盖范围</span>
              <el-button-group size="small">
                <el-button @click="loadCoverage" :loading="coverageLoading">
                  刷新覆盖
                </el-button>
                <el-button @click="exportCoverage">
                  导出数据
                </el-button>
              </el-button-group>
            </div>
          </template>
          <div class="coverage-container">
            <div v-if="coverageLoading" class="coverage-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>加载覆盖数据中...</span>
            </div>
            <div v-else-if="!coverage.length" class="coverage-empty">
              <el-icon><DocumentRemove /></el-icon>
              <span>暂无覆盖数据</span>
            </div>
            <div v-else ref="coverageMapRef" class="coverage-map">
              <!-- 占位地图容器，可替换为Cesium/Three渲染 -->
              <span>覆盖热力渲染占位</span>
            </div>
          </div>
        </el-card>

        <!-- Beam Hint 可视化 -->
        <el-card class="mb-4">
          <template #header>
            <div class="card-header">
              <span>Beam Hint 可视化</span>
              <el-button-group size="small">
                <el-button @click="requestBeamHint" :loading="beamHintLoading">获取推荐</el-button>
                <el-button @click="exportBeamHintCSV" :disabled="!beamHint.assignments?.length">导出CSV</el-button>
              </el-button-group>
            </div>
          </template>
          <div class="coverage-container">
            <div v-if="beamHintLoading" class="coverage-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>计算推荐中...</span>
            </div>
            <div v-else-if="!beamHint.assignments?.length" class="coverage-empty">
              <el-icon><DocumentRemove /></el-icon>
              <span>暂无推荐</span>
            </div>
            <div v-else class="coverage-map">
              <span>Beam Hint 叠加层占位（用户与推荐卫星连线）</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { positioningApi } from '@/api/admission'
import PositioningStats from '@/components/PositioningStats.vue'
import { Location, Loading, DocumentRemove } from '@element-plus/icons-vue'

// 状态管理
const appStore = useAppStore()

// 响应式数据
const config = ref({
  elevationMaskDeg: 10,
  maxGdopThreshold: 10,
  minVisibleSatellites: 4,
  signalNoiseRatio: 30
})

const testRequest = ref({
  userId: 'test_user_001',
  lat: 39.9042,
  lon: 116.4074,
  accuracy: 10
})

const qualityQuery = ref({
  lat: 39.9,
  lon: 116.4
})

const testResult = ref<any>(null)
const qualityResult = ref<any>(null)
const coverage = ref<any[]>([])

const configLoading = ref(false)
const testLoading = ref(false)
const qualityLoading = ref(false)
const statsLoading = ref(false)
const coverageLoading = ref(false)

const coverageMapRef = ref<HTMLElement>()

// Beam Hint
const beamHint = ref<any>({ policy: '', assignments: [] })
const beamHintLoading = ref(false)

// 方法
const loadConfig = async () => {
  try {
    const result = await positioningApi.getConfig()
    Object.assign(config.value, result)
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const updateConfig = async () => {
  configLoading.value = true
  try {
    await positioningApi.updateConfig(config.value)
    appStore.addNotification({
      type: 'success',
      title: '配置更新',
      message: '定位服务配置已更新'
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
    testResult.value = await positioningApi.processRequest(testRequest.value)
  } catch (error) {
    console.error('定位测试失败:', error)
  } finally {
    testLoading.value = false
  }
}

const generateRandomLocation = () => {
  testRequest.value.lat = Math.round((Math.random() * 180 - 90) * 1000) / 1000
  testRequest.value.lon = Math.round((Math.random() * 360 - 180) * 1000) / 1000
}

const queryQuality = async () => {
  qualityLoading.value = true
  try {
    qualityResult.value = await positioningApi.getQuality(
      qualityQuery.value.lat,
      qualityQuery.value.lon
    )
  } catch (error) {
    console.error('查询定位质量失败:', error)
  } finally {
    qualityLoading.value = false
  }
}

const loadCoverage = async () => {
  coverageLoading.value = true
  try {
    const result = await positioningApi.getCoverage({
      resolution: 10,
      lat_min: -60,
      lat_max: 60,
      lon_min: -180,
      lon_max: 180
    })
    coverage.value = result.coverage || []
  } catch (error) {
    console.error('加载覆盖数据失败:', error)
  } finally {
    coverageLoading.value = false
  }
}

const exportCoverage = () => {
  const data = {
    coverage: coverage.value,
    timestamp: new Date().toISOString()
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `positioning_coverage_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const requestBeamHint = async () => {
  beamHintLoading.value = true
  try {
    const users = [
      { id: testRequest.value.userId, lat: testRequest.value.lat, lon: testRequest.value.lon }
    ]
    const result = await positioningApi.getBeamHint({ users, budget: { beams_per_user: 2 } })
    beamHint.value = result
    appStore.addNotification({ type: 'success', title: 'Beam Hint', message: '已生成推荐' })
  } catch (e) {
    ElMessage.error('获取 Beam Hint 失败')
  } finally {
    beamHintLoading.value = false
  }
}

const exportBeamHintCSV = () => {
  if (!beamHint.value.assignments?.length) return
  const rows = beamHint.value.assignments.flatMap((a: any) => (
    a.recommendations.map((r: any) => ({ user_id: a.user?.id, sat_id: r.sat_id, score: r.score }))
  ))
  const header = 'user_id,sat_id,score\n'
  const csv = header + rows.map((r: any) => `${r.user_id},${r.sat_id},${r.score}`).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `beam_hint_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const getAverageSignalStrength = (signals: number[]) => {
  if (!signals.length) return 0
  return signals.reduce((sum, signal) => sum + signal, 0) / signals.length
}

const getQualityType = (gdop: number) => {
  if (gdop <= 2) return 'success'
  if (gdop <= 5) return 'warning'
  return 'danger'
}

const getQualityText = (gdop: number) => {
  if (gdop <= 2) return '优秀'
  if (gdop <= 5) return '良好'
  if (gdop <= 10) return '一般'
  return '较差'
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleString()
}

// 生命周期
onMounted(async () => {
  await loadConfig()
  await loadCoverage()
})
</script>

<style scoped>
.positioning {
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

.positioning-result,
.quality-result {
  padding: 16px 0;
}

.quality-metric {
  text-align: center;
  padding: 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.coverage-container {
  height: 300px;
  position: relative;
}

.coverage-loading,
.coverage-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.coverage-loading .el-icon,
.coverage-empty .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.coverage-map {
  width: 100%;
  height: 100%;
  background: var(--el-bg-color-page);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
