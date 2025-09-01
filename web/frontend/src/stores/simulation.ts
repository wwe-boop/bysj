import { defineStore } from 'pinia'
import { simulationApi, scenarioApi, performanceApi } from '@/api/simulation'
import type { 
  SimulationStatus, 
  SimulationConfig, 
  SimulationScenario,
  PerformanceMetrics 
} from '@/types'

interface SimulationState {
  status: SimulationStatus
  config: SimulationConfig | null
  scenarios: SimulationScenario[]
  currentScenario: SimulationScenario | null
  performanceMetrics: PerformanceMetrics | null
  performanceHistory: PerformanceMetrics[]
  loading: boolean
  error: string | null
}

export const useSimulationStore = defineStore('simulation', {
  state: (): SimulationState => ({
    status: {
      isRunning: false,
      currentTime: 0,
      progress: 0,
      scenario: undefined,
      startTime: undefined,
      duration: undefined
    },
    config: null,
    scenarios: [],
    currentScenario: null,
    performanceMetrics: null,
    performanceHistory: [],
    loading: false,
    error: null
  }),

  getters: {
    isRunning: (state) => state.status.isRunning,
    
    currentTime: (state) => state.status.currentTime,
    
    progress: (state) => state.status.progress,
    
    remainingTime: (state) => {
      if (!state.status.duration || !state.status.isRunning) return 0
      return Math.max(0, state.status.duration - state.status.currentTime)
    },

    estimatedEndTime: (state) => {
      if (!state.status.startTime || !state.status.duration) return null
      return state.status.startTime + state.status.duration * 1000
    },

    scenarioByName: (state) => (name: string) => 
      state.scenarios.find(s => s.name === name),

    latestMetrics: (state) => state.performanceMetrics,

    averageMetrics: (state) => {
      if (state.performanceHistory.length === 0) return null
      
      const sum = state.performanceHistory.reduce((acc, metrics) => ({
        averageThroughput: acc.averageThroughput + metrics.averageThroughput,
        averageLatency: acc.averageLatency + metrics.averageLatency,
        packetLossRate: acc.packetLossRate + metrics.packetLossRate,
        qoeScore: acc.qoeScore + metrics.qoeScore,
        admissionRate: acc.admissionRate + metrics.admissionRate,
        resourceUtilization: acc.resourceUtilization + metrics.resourceUtilization
      }), {
        averageThroughput: 0,
        averageLatency: 0,
        packetLossRate: 0,
        qoeScore: 0,
        admissionRate: 0,
        resourceUtilization: 0
      })

      const count = state.performanceHistory.length
      return {
        averageThroughput: sum.averageThroughput / count,
        averageLatency: sum.averageLatency / count,
        packetLossRate: sum.packetLossRate / count,
        qoeScore: sum.qoeScore / count,
        admissionRate: sum.admissionRate / count,
        resourceUtilization: sum.resourceUtilization / count
      }
    }
  },

  actions: {
    async fetchStatus() {
      try {
        this.loading = true
        this.error = null
        this.status = await simulationApi.getStatus()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '获取仿真状态失败'
        console.error('获取仿真状态失败:', error)
      } finally {
        this.loading = false
      }
    },

    async startSimulation(config: SimulationConfig) {
      try {
        this.loading = true
        this.error = null
        await simulationApi.start(config)
        this.config = config
        await this.fetchStatus()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '启动仿真失败'
        console.error('启动仿真失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async stopSimulation() {
      try {
        this.loading = true
        this.error = null
        await simulationApi.stop()
        await this.fetchStatus()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '停止仿真失败'
        console.error('停止仿真失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async pauseSimulation() {
      try {
        this.loading = true
        this.error = null
        await simulationApi.pause()
        await this.fetchStatus()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '暂停仿真失败'
        console.error('暂停仿真失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async resumeSimulation() {
      try {
        this.loading = true
        this.error = null
        await simulationApi.resume()
        await this.fetchStatus()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '恢复仿真失败'
        console.error('恢复仿真失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async resetSimulation() {
      try {
        this.loading = true
        this.error = null
        await simulationApi.reset()
        this.status = {
          isRunning: false,
          currentTime: 0,
          progress: 0,
          scenario: undefined,
          startTime: undefined,
          duration: undefined
        }
        this.config = null
        this.performanceMetrics = null
        this.performanceHistory = []
      } catch (error) {
        this.error = error instanceof Error ? error.message : '重置仿真失败'
        console.error('重置仿真失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchScenarios() {
      try {
        this.loading = true
        this.error = null
        this.scenarios = await scenarioApi.getAll()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '获取场景列表失败'
        console.error('获取场景列表失败:', error)
      } finally {
        this.loading = false
      }
    },

    async fetchScenario(name: string) {
      try {
        this.loading = true
        this.error = null
        this.currentScenario = await scenarioApi.getById(name)
        return this.currentScenario
      } catch (error) {
        this.error = error instanceof Error ? error.message : '获取场景失败'
        console.error('获取场景失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchPerformanceMetrics() {
      try {
        this.performanceMetrics = await performanceApi.getCurrentMetrics()
        
        // 添加到历史记录
        if (this.performanceMetrics) {
          this.performanceHistory.push(this.performanceMetrics)
          
          // 限制历史记录数量
          if (this.performanceHistory.length > 1000) {
            this.performanceHistory = this.performanceHistory.slice(-1000)
          }
        }
      } catch (error) {
        console.error('获取性能指标失败:', error)
      }
    },

    async fetchPerformanceHistory(timeRange: [number, number]) {
      try {
        this.loading = true
        this.error = null
        this.performanceHistory = await performanceApi.getHistoryMetrics(timeRange)
      } catch (error) {
        this.error = error instanceof Error ? error.message : '获取性能历史失败'
        console.error('获取性能历史失败:', error)
      } finally {
        this.loading = false
      }
    },

    // WebSocket事件处理
    updateStatus(status: Partial<SimulationStatus>) {
      this.status = { ...this.status, ...status }
    },

    updatePerformanceMetrics(metrics: PerformanceMetrics) {
      this.performanceMetrics = metrics
      this.performanceHistory.push(metrics)
      
      // 限制历史记录数量
      if (this.performanceHistory.length > 1000) {
        this.performanceHistory = this.performanceHistory.slice(-1000)
      }
    },

    clearError() {
      this.error = null
    },

    // 定期更新状态
    startStatusPolling(interval = 5000) {
      const timer = setInterval(async () => {
        if (this.isRunning) {
          await this.fetchStatus()
          await this.fetchPerformanceMetrics()
        }
      }, interval)

      // 返回清理函数
      return () => clearInterval(timer)
    }
  }
})
