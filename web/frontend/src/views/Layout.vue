<template>
  <div class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo">
        <el-icon><Satellite /></el-icon>
        <span v-show="!isCollapsed" class="logo-text">LEO仿真系统</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :unique-opened="true"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>仪表板</template>
        </el-menu-item>
        
        <el-menu-item index="/simulation">
          <el-icon><VideoPlay /></el-icon>
          <template #title>仿真控制</template>
        </el-menu-item>
        
        <el-menu-item index="/visualization">
          <el-icon><TrendCharts /></el-icon>
          <template #title>可视化</template>
        </el-menu-item>
        
        <el-menu-item index="/network">
          <el-icon><Share /></el-icon>
          <template #title>网络拓扑</template>
        </el-menu-item>
        
        <el-sub-menu index="algorithms">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>算法模块</span>
          </template>
          <el-menu-item index="/admission">
            <el-icon><Key /></el-icon>
            <template #title>准入控制</template>
          </el-menu-item>
          <el-menu-item index="/drl-training">
            <el-icon><BrainFilled /></el-icon>
            <template #title>DRL训练</template>
          </el-menu-item>
          <el-menu-item index="/positioning">
            <el-icon><Location /></el-icon>
            <template #title>定位服务</template>
          </el-menu-item>
        </el-sub-menu>
        
        <el-menu-item index="/scenarios">
          <el-icon><Files /></el-icon>
          <template #title>场景管理</template>
        </el-menu-item>
        
        <el-menu-item index="/statistics">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>统计分析</template>
        </el-menu-item>

        <el-menu-item index="/experiments">
          <el-icon><Operation /></el-icon>
          <template #title>实验批跑</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-button
            :icon="isCollapsed ? Expand : Fold"
            @click="toggleSidebar"
            text
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.meta?.title">
              {{ currentRoute.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 连接状态 -->
          <div class="connection-status">
            <el-icon :class="connectionStatusClass">
              <CircleCheck v-if="isConnected" />
              <CircleClose v-else />
            </el-icon>
            <span>{{ connectionText }}</span>
          </div>
          
          <!-- 仿真状态 -->
          <div class="simulation-status">
            <el-tag :type="simulationStatusType" size="small">
              {{ simulationStatusText }}
            </el-tag>
          </div>
          
          <!-- 主题切换 -->
          <el-button
            :icon="isDark ? Sunny : Moon"
            @click="toggleTheme"
            text
          />
          
          <!-- 设置 -->
          <el-dropdown>
            <el-button :icon="Setting" text />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showSettings">系统设置</el-dropdown-item>
                <el-dropdown-item @click="showAbout">关于系统</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主要内容 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 设置对话框 -->
    <el-dialog v-model="settingsVisible" title="系统设置" width="500px">
      <el-form label-width="100px">
        <el-form-item label="主题模式">
          <el-switch
            v-model="isDark"
            active-text="深色"
            inactive-text="浅色"
            @change="toggleTheme"
          />
        </el-form-item>
        <el-form-item label="自动刷新">
          <el-switch v-model="autoRefresh" />
        </el-form-item>
        <el-form-item label="刷新间隔">
          <el-select v-model="refreshInterval" :disabled="!autoRefresh">
            <el-option label="1秒" :value="1000" />
            <el-option label="5秒" :value="5000" />
            <el-option label="10秒" :value="10000" />
            <el-option label="30秒" :value="30000" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 关于对话框 -->
    <el-dialog v-model="aboutVisible" title="关于系统" width="600px">
      <div class="about-content">
        <h3>LEO卫星网络智能准入控制与资源分配系统</h3>
        <p>基于深度强化学习的LEO卫星网络实时准入控制与DSROQ资源分配算法研究平台</p>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="版本">v1.0.0</el-descriptions-item>
          <el-descriptions-item label="构建时间">2024-01-01</el-descriptions-item>
          <el-descriptions-item label="技术栈">Vue 3 + TypeScript</el-descriptions-item>
          <el-descriptions-item label="UI框架">Element Plus</el-descriptions-item>
          <el-descriptions-item label="后端">Flask + SocketIO</el-descriptions-item>
          <el-descriptions-item label="仿真引擎">Hypatia</el-descriptions-item>
        </el-descriptions>
        
        <div class="features">
          <h4>核心功能</h4>
          <ul>
            <li>智能准入控制算法 (DRL)</li>
            <li>DSROQ资源分配与调度</li>
            <li>MCTS路由优化</li>
            <li>定位感知服务质量</li>
            <li>实时性能监控</li>
            <li>3D网络可视化</li>
          </ul>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { useSimulationStore } from '@/stores/simulation'
import { useWebSocketStore } from '@/stores/websocket'

// 图标
import {
  Satellite,
  DataBoard,
  VideoPlay,
  TrendCharts,
  Share,
  Setting,
  Key,
  BrainFilled,
  Location,
  Files,
  DataAnalysis,
  Operation,
  Expand,
  Fold,
  CircleCheck,
  CircleClose,
  Sunny,
  Moon
} from '@element-plus/icons-vue'

// 状态管理
const appStore = useAppStore()
const simulationStore = useSimulationStore()
const websocketStore = useWebSocketStore()

// 响应式数据
const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const settingsVisible = ref(false)
const aboutVisible = ref(false)
const autoRefresh = ref(true)
const refreshInterval = ref(5000)

// 计算属性
const sidebarWidth = computed(() => isCollapsed.value ? '64px' : '200px')
const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)

const isDark = computed({
  get: () => appStore.isDark,
  set: (value) => appStore.setTheme(value ? 'dark' : 'light')
})

const isConnected = computed(() => websocketStore.isConnected)
const connectionStatusClass = computed(() => ({
  'connection-icon': true,
  'connected': isConnected.value,
  'disconnected': !isConnected.value
}))
const connectionText = computed(() => isConnected.value ? '已连接' : '未连接')

const simulationStatusType = computed(() => {
  if (simulationStore.isRunning) return 'success'
  return 'info'
})
const simulationStatusText = computed(() => {
  if (simulationStore.isRunning) return '仿真运行中'
  return '仿真未运行'
})

// 方法
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const toggleTheme = () => {
  appStore.toggleTheme()
}

const showSettings = () => {
  settingsVisible.value = true
}

const showAbout = () => {
  aboutVisible.value = true
}

// 生命周期
onMounted(() => {
  // 连接WebSocket
  websocketStore.connect()
  
  // 获取初始状态
  simulationStore.fetchStatus()
})

onUnmounted(() => {
  // 断开WebSocket连接
  websocketStore.disconnect()
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
  display: flex;
}

.sidebar {
  background-color: var(--el-bg-color-page);
  border-right: 1px solid var(--el-border-color);
  transition: width 0.3s;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--el-border-color);
  font-size: 18px;
  font-weight: bold;
  color: var(--el-color-primary);
}

.logo-text {
  margin-left: 10px;
  transition: opacity 0.3s;
}

.sidebar-menu {
  border: none;
  height: calc(100vh - 60px);
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
}

.connection-icon.connected {
  color: var(--el-color-success);
}

.connection-icon.disconnected {
  color: var(--el-color-danger);
}

.simulation-status {
  font-size: 12px;
}

.main-content {
  flex: 1;
  padding: 20px;
  background-color: var(--el-bg-color-page);
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.about-content h3 {
  color: var(--el-color-primary);
  margin-bottom: 10px;
}

.about-content p {
  color: var(--el-text-color-regular);
  margin-bottom: 20px;
}

.features {
  margin-top: 20px;
}

.features h4 {
  color: var(--el-color-primary);
  margin-bottom: 10px;
}

.features ul {
  list-style-type: disc;
  padding-left: 20px;
}

.features li {
  margin-bottom: 5px;
  color: var(--el-text-color-regular);
}
</style>
