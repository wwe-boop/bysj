<template>
  <div class="visualization-view">
    <div class="page-header">
      <h1>可视化</h1>
      <p>LEO卫星网络3D可视化与Beam Hint展示</p>
    </div>

    <!-- 控制面板 -->
    <el-card class="control-panel">
      <template #header>
        <span>可视化控制</span>
        <el-button-group style="float: right;">
          <el-button size="small" :type="viewMode === '3d' ? 'primary' : ''" @click="setViewMode('3d')">
            3D视图
          </el-button>
          <el-button size="small" :type="viewMode === 'map' ? 'primary' : ''" @click="setViewMode('map')">
            地图视图
          </el-button>
        </el-button-group>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="control-group">
            <h4>显示选项</h4>
            <el-checkbox-group v-model="displayOptions">
              <el-checkbox label="satellites">卫星</el-checkbox>
              <el-checkbox label="orbits">轨道</el-checkbox>
              <el-checkbox label="links">链路</el-checkbox>
              <el-checkbox label="beams">波束</el-checkbox>
              <el-checkbox label="coverage">覆盖区域</el-checkbox>
              <el-checkbox label="users">用户</el-checkbox>
            </el-checkbox-group>
          </div>
        </el-col>
        
        <el-col :span="6">
          <div class="control-group">
            <h4>Beam Hint</h4>
            <el-switch
              v-model="beamHintEnabled"
              active-text="启用"
              inactive-text="禁用"
            />
            <div class="mt-2">
              <el-select v-model="selectedBeamType" placeholder="选择波束类型" size="small">
                <el-option label="推荐波束" value="recommended" />
                <el-option label="可见波束" value="visible" />
                <el-option label="所有波束" value="all" />
              </el-select>
            </div>
          </div>
        </el-col>
        
        <el-col :span="6">
          <div class="control-group">
            <h4>时间控制</h4>
            <el-button-group size="small">
              <el-button :icon="VideoPlay" @click="toggleAnimation">
                {{ isAnimating ? '暂停' : '播放' }}
              </el-button>
              <el-button :icon="Refresh" @click="resetTime">重置</el-button>
            </el-button-group>
            <div class="mt-2">
              <el-slider
                v-model="timeProgress"
                :min="0"
                :max="100"
                @change="onTimeChange"
              />
            </div>
          </div>
        </el-col>
        
        <el-col :span="6">
          <div class="control-group">
            <h4>导出</h4>
            <el-button-group size="small">
              <el-button @click="exportScreenshot">截图</el-button>
              <el-button @click="exportVideo">录制</el-button>
              <el-button @click="exportData">数据</el-button>
            </el-button-group>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 主可视化区域 -->
    <el-row :gutter="20" class="mt-4">
      <el-col :span="18">
        <el-card class="visualization-container">
          <div ref="visualizationRef" class="visualization-canvas">
            <!-- 3D/地图可视化画布 -->
            <div class="canvas-placeholder">
              <el-icon size="64"><View /></el-icon>
              <p>{{ viewMode === '3d' ? '3D卫星网络可视化' : '地图视图' }}</p>
              <p class="text-muted">
                显示: {{ displayOptions.join(', ') || '无' }}
              </p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <!-- 信息面板 -->
        <el-card title="实时信息">
          <div class="info-item">
            <span>当前时间:</span>
            <span>{{ currentTime }}</span>
          </div>
          <div class="info-item">
            <span>可见卫星:</span>
            <span>{{ visibleSatellites }}</span>
          </div>
          <div class="info-item">
            <span>活跃波束:</span>
            <span>{{ activeBeams }}</span>
          </div>
          <div class="info-item">
            <span>覆盖用户:</span>
            <span>{{ coveredUsers }}</span>
          </div>
        </el-card>

        <!-- Beam Hint详情 -->
        <el-card title="Beam Hint详情" class="mt-4" v-if="beamHintEnabled">
          <div v-if="selectedBeam">
            <div class="beam-info">
              <h5>波束 {{ selectedBeam.id }}</h5>
              <div class="info-item">
                <span>卫星:</span>
                <span>{{ selectedBeam.satellite }}</span>
              </div>
              <div class="info-item">
                <span>方向:</span>
                <span>{{ selectedBeam.direction }}</span>
              </div>
              <div class="info-item">
                <span>增益:</span>
                <span>{{ selectedBeam.gain }} dB</span>
              </div>
              <div class="info-item">
                <span>覆盖半径:</span>
                <span>{{ selectedBeam.radius }} km</span>
              </div>
              <div class="info-item">
                <span>推荐度:</span>
                <el-rate v-model="selectedBeam.recommendation" disabled />
              </div>
            </div>
          </div>
          <div v-else class="text-muted">
            点击波束查看详情
          </div>
        </el-card>

        <!-- 图例 -->
        <el-card title="图例" class="mt-4">
          <div class="legend-item">
            <div class="legend-color satellite"></div>
            <span>卫星</span>
          </div>
          <div class="legend-item">
            <div class="legend-color orbit"></div>
            <span>轨道</span>
          </div>
          <div class="legend-item">
            <div class="legend-color link"></div>
            <span>链路</span>
          </div>
          <div class="legend-item">
            <div class="legend-color beam-recommended"></div>
            <span>推荐波束</span>
          </div>
          <div class="legend-item">
            <div class="legend-color beam-visible"></div>
            <span>可见波束</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Refresh, View } from '@element-plus/icons-vue'

// 响应式数据
const visualizationRef = ref()
const viewMode = ref('3d')
const isAnimating = ref(false)
const timeProgress = ref(0)
const beamHintEnabled = ref(true)
const selectedBeamType = ref('recommended')

const displayOptions = ref(['satellites', 'orbits', 'links'])

const selectedBeam = ref({
  id: 'B001',
  satellite: 'SAT-001',
  direction: '北纬45°, 东经120°',
  gain: 35,
  radius: 500,
  recommendation: 4
})

// 计算属性
const currentTime = computed(() => {
  const now = new Date()
  return now.toLocaleTimeString()
})

const visibleSatellites = computed(() => 12)
const activeBeams = computed(() => 24)
const coveredUsers = computed(() => 156)

// 方法
const setViewMode = (mode: string) => {
  viewMode.value = mode
  ElMessage.success(`切换到${mode === '3d' ? '3D' : '地图'}视图`)
}

const toggleAnimation = () => {
  isAnimating.value = !isAnimating.value
  ElMessage.info(isAnimating.value ? '开始动画' : '暂停动画')
}

const resetTime = () => {
  timeProgress.value = 0
  ElMessage.success('时间已重置')
}

const onTimeChange = (value: number) => {
  // 时间变化处理
}

const exportScreenshot = () => {
  ElMessage.success('截图已保存')
}

const exportVideo = () => {
  ElMessage.success('开始录制视频')
}

const exportData = () => {
  ElMessage.success('数据导出成功')
}

onMounted(() => {
  // 初始化可视化引擎
})
</script>

<style scoped>
.visualization-view {
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

.control-panel {
  margin-bottom: 20px;
}

.control-group h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.visualization-container {
  height: 600px;
}

.visualization-canvas {
  height: 100%;
  position: relative;
}

.canvas-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  background: #f5f7fa;
  border-radius: 4px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.beam-info h5 {
  margin: 0 0 10px 0;
  color: #333;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  margin-right: 8px;
}

.legend-color.satellite {
  background: #409eff;
}

.legend-color.orbit {
  background: #67c23a;
}

.legend-color.link {
  background: #e6a23c;
}

.legend-color.beam-recommended {
  background: #f56c6c;
}

.legend-color.beam-visible {
  background: #909399;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}

.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 20px;
}
</style>
