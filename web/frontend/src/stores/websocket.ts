import { defineStore } from 'pinia'
import { io, Socket } from 'socket.io-client'
import { useSimulationStore } from './simulation'
import { useAppStore } from './app'
import type { WebSocketMessage } from '@/types'

interface WebSocketState {
  socket: Socket | null
  isConnected: boolean
  isConnecting: boolean
  reconnectAttempts: number
  maxReconnectAttempts: number
  reconnectInterval: number
  subscriptions: Set<string>
  lastPingTime: number
  latency: number
}

export const useWebSocketStore = defineStore('websocket', {
  state: (): WebSocketState => ({
    socket: null,
    isConnected: false,
    isConnecting: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectInterval: 3000,
    subscriptions: new Set(),
    lastPingTime: 0,
    latency: 0
  }),

  getters: {
    connectionStatus: (state) => {
      if (state.isConnecting) return 'connecting'
      if (state.isConnected) return 'connected'
      return 'disconnected'
    },

    isSubscribed: (state) => (subscription: string) => 
      state.subscriptions.has(subscription)
  },

  actions: {
    connect(url = '/') {
      if (this.socket?.connected || this.isConnecting) {
        return
      }

      this.isConnecting = true
      
      try {
        this.socket = io(url, {
          transports: ['websocket', 'polling'],
          timeout: 10000,
          reconnection: true,
          reconnectionAttempts: this.maxReconnectAttempts,
          reconnectionDelay: this.reconnectInterval
        })

        this.setupEventHandlers()
        
      } catch (error) {
        console.error('WebSocket连接失败:', error)
        this.isConnecting = false
        this.handleConnectionError(error)
      }
    },

    disconnect() {
      if (this.socket) {
        this.socket.disconnect()
        this.socket = null
      }
      this.isConnected = false
      this.isConnecting = false
      this.subscriptions.clear()
    },

    setupEventHandlers() {
      if (!this.socket) return

      const simulationStore = useSimulationStore()
      const appStore = useAppStore()

      // 连接事件
      this.socket.on('connect', () => {
        console.log('WebSocket已连接')
        this.isConnected = true
        this.isConnecting = false
        this.reconnectAttempts = 0
        
        appStore.addNotification({
          type: 'success',
          title: '连接成功',
          message: '已连接到服务器'
        })

        // 重新订阅之前的订阅
        this.resubscribe()
      })

      // 断开连接事件
      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket已断开:', reason)
        this.isConnected = false
        this.subscriptions.clear()
        
        if (reason !== 'io client disconnect') {
          appStore.addNotification({
            type: 'warning',
            title: '连接断开',
            message: '与服务器的连接已断开'
          })
        }
      })

      // 连接错误事件
      this.socket.on('connect_error', (error) => {
        console.error('WebSocket连接错误:', error)
        this.isConnecting = false
        this.handleConnectionError(error)
      })

      // 重连事件
      this.socket.on('reconnect', (attemptNumber) => {
        console.log(`WebSocket重连成功 (尝试 ${attemptNumber})`)
        this.reconnectAttempts = 0
      })

      this.socket.on('reconnect_attempt', (attemptNumber) => {
        console.log(`WebSocket重连尝试 ${attemptNumber}`)
        this.reconnectAttempts = attemptNumber
      })

      this.socket.on('reconnect_failed', () => {
        console.error('WebSocket重连失败')
        appStore.addNotification({
          type: 'error',
          title: '重连失败',
          message: '无法重新连接到服务器'
        })
      })

      // 业务事件
      this.socket.on('connection_established', (data) => {
        console.log('连接确认:', data)
      })

      // 消融/批量实验实时事件
      this.socket.on('ablation_completed', (data) => {
        const appStore = useAppStore()
        appStore.addNotification({ type: 'success', title: '消融完成', message: `ID: ${data.experiment_id}` })
      })
      this.socket.on('batch_experiment_completed', (data) => {
        const appStore = useAppStore()
        appStore.addNotification({ type: 'success', title: '批量实验完成', message: `ID: ${data.experiment_id}` })
      })

      // Beam Hint 实时事件
      this.socket.on('beam_hint_update', (payload) => {
        // 可在此处分发到专用的 store 或事件总线
        console.log('Beam Hint 更新', payload)
      })

      this.socket.on('simulation_update', (data) => {
        simulationStore.updateStatus({
          currentTime: data.current_time,
          progress: data.progress,
          isRunning: true
        })
        
        if (data.performance_metrics) {
          simulationStore.updatePerformanceMetrics(data.performance_metrics)
        }
      })

      this.socket.on('simulation_started', (data) => {
        console.log('仿真已启动:', data)
        simulationStore.updateStatus({
          isRunning: true,
          scenario: data.scenario,
          startTime: data.timestamp
        })
        
        appStore.addNotification({
          type: 'success',
          title: '仿真启动',
          message: `场景 "${data.scenario}" 已开始运行`
        })
      })

      this.socket.on('simulation_completed', (data) => {
        console.log('仿真已完成:', data)
        simulationStore.updateStatus({
          isRunning: false,
          progress: 100
        })
        
        appStore.addNotification({
          type: 'info',
          title: '仿真完成',
          message: '仿真已成功完成'
        })
      })

      this.socket.on('simulation_stopped', (data) => {
        console.log('仿真已停止:', data)
        simulationStore.updateStatus({
          isRunning: false
        })
        
        appStore.addNotification({
          type: 'warning',
          title: '仿真停止',
          message: '仿真已被手动停止'
        })
      })

      this.socket.on('simulation_error', (data) => {
        console.error('仿真错误:', data)
        simulationStore.updateStatus({
          isRunning: false
        })
        
        appStore.addNotification({
          type: 'error',
          title: '仿真错误',
          message: data.error || '仿真过程中发生错误'
        })
      })

      // 订阅确认
      this.socket.on('subscription_confirmed', (data) => {
        console.log('订阅确认:', data)
        this.subscriptions.add(data.type)
      })

      this.socket.on('subscription_cancelled', (data) => {
        console.log('取消订阅:', data)
        this.subscriptions.delete(data.type)
      })

      // 心跳响应
      this.socket.on('pong', (data) => {
        if (this.lastPingTime > 0) {
          this.latency = Date.now() - this.lastPingTime
        }
      })

      // 错误处理
      this.socket.on('error', (data) => {
        console.error('WebSocket错误:', data)
        appStore.addNotification({
          type: 'error',
          title: '服务器错误',
          message: data.message || '服务器发生错误'
        })
      })
    },

    subscribe(type: string) {
      if (!this.socket?.connected) {
        console.warn('WebSocket未连接，无法订阅')
        return false
      }

      this.socket.emit(`subscribe_${type}`, {})
      return true
    },

    unsubscribe(type: string) {
      if (!this.socket?.connected) {
        return false
      }

      this.socket.emit(`unsubscribe_${type}`, {})
      this.subscriptions.delete(type)
      return true
    },

    resubscribe() {
      // 重新订阅之前的订阅
      const subscriptions = Array.from(this.subscriptions)
      this.subscriptions.clear()
      
      subscriptions.forEach(type => {
        this.subscribe(type)
      })
    },

    ping() {
      if (!this.socket?.connected) {
        return false
      }

      this.lastPingTime = Date.now()
      this.socket.emit('ping', { timestamp: this.lastPingTime })
      return true
    },

    emit(event: string, data?: any) {
      if (!this.socket?.connected) {
        console.warn('WebSocket未连接，无法发送消息')
        return false
      }

      this.socket.emit(event, data)
      return true
    },

    handleConnectionError(error: any) {
      const appStore = useAppStore()
      
      let message = '连接服务器失败'
      if (error.message) {
        message = error.message
      } else if (typeof error === 'string') {
        message = error
      }

      appStore.addNotification({
        type: 'error',
        title: '连接错误',
        message
      })
    },

    // 开始心跳检测
    startHeartbeat(interval = 30000) {
      const timer = setInterval(() => {
        if (this.isConnected) {
          this.ping()
        }
      }, interval)

      // 返回清理函数
      return () => clearInterval(timer)
    }
  }
})
