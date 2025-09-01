import { request } from './index'
import type { 
  SimulationStatus, 
  SimulationConfig, 
  SimulationScenario,
  NetworkState,
  PerformanceMetrics 
} from '@/types'

// 仿真控制API
export const simulationApi = {
  // 获取仿真状态
  getStatus(): Promise<SimulationStatus> {
    return request.get<SimulationStatus>('/simulation/status').then(res => res.data!)
  },

  // 启动仿真
  start(config: SimulationConfig): Promise<void> {
    return request.post('/simulation/start', config).then(() => {})
  },

  // 停止仿真
  stop(): Promise<void> {
    return request.post('/simulation/stop').then(() => {})
  },

  // 暂停仿真
  pause(): Promise<void> {
    return request.post('/simulation/pause').then(() => {})
  },

  // 恢复仿真
  resume(): Promise<void> {
    return request.post('/simulation/resume').then(() => {})
  },

  // 重置仿真
  reset(): Promise<void> {
    return request.post('/simulation/reset').then(() => {})
  },

  // 获取仿真配置
  getConfig(): Promise<SimulationConfig> {
    return request.get<SimulationConfig>('/simulation/config').then(res => res.data!)
  },

  // 更新仿真配置
  updateConfig(config: Partial<SimulationConfig>): Promise<void> {
    return request.put('/simulation/config', config).then(() => {})
  }
}

// 场景管理API
export const scenarioApi = {
  // 获取所有场景
  getAll(): Promise<SimulationScenario[]> {
    return request.get<SimulationScenario[]>('/scenarios').then(res => res.data!)
  },

  // 获取特定场景
  getById(name: string): Promise<SimulationScenario> {
    return request.get<SimulationScenario>(`/scenarios/${name}`).then(res => res.data!)
  },

  // 创建场景
  create(scenario: SimulationScenario): Promise<void> {
    return request.post('/scenarios', scenario).then(() => {})
  },

  // 更新场景
  update(name: string, scenario: Partial<SimulationScenario>): Promise<void> {
    return request.put(`/scenarios/${name}`, scenario).then(() => {})
  },

  // 删除场景
  delete(name: string): Promise<void> {
    return request.delete(`/scenarios/${name}`).then(() => {})
  },

  // 验证场景
  validate(scenario: SimulationScenario): Promise<{ valid: boolean; errors: string[] }> {
    return request.post<{ valid: boolean; errors: string[] }>('/scenarios/validate', scenario)
      .then(res => res.data!)
  }
}

// 网络状态API
export const networkApi = {
  // 获取当前网络状态
  getCurrentState(): Promise<NetworkState> {
    return request.get<NetworkState>('/network/state').then(res => res.data!)
  },

  // 获取网络拓扑
  getTopology(): Promise<{ satellites: any[]; links: any[] }> {
    return request.get<{ satellites: any[]; links: any[] }>('/network/topology')
      .then(res => res.data!)
  },

  // 获取链路信息
  getLinks(): Promise<any[]> {
    return request.get<any[]>('/network/links').then(res => res.data!)
  },

  // 获取卫星信息
  getSatellites(): Promise<any[]> {
    return request.get<any[]>('/network/satellites').then(res => res.data!)
  },

  // 获取流量信息
  getFlows(): Promise<any[]> {
    return request.get<any[]>('/network/flows').then(res => res.data!)
  }
}

// 性能监控API
export const performanceApi = {
  // 获取当前性能指标
  getCurrentMetrics(): Promise<PerformanceMetrics> {
    return request.get<PerformanceMetrics>('/performance/metrics').then(res => res.data!)
  },

  // 获取历史性能数据
  getHistoryMetrics(timeRange: [number, number]): Promise<PerformanceMetrics[]> {
    return request.get<PerformanceMetrics[]>('/performance/history', {
      params: {
        startTime: timeRange[0],
        endTime: timeRange[1]
      }
    }).then(res => res.data!)
  },

  // 获取性能统计
  getStatistics(): Promise<any> {
    return request.get('/performance/statistics').then(res => res.data!)
  },

  // 导出性能数据
  exportData(format: 'json' | 'csv' | 'excel', timeRange?: [number, number]): Promise<Blob> {
    return request.get('/performance/export', {
      params: {
        format,
        startTime: timeRange?.[0],
        endTime: timeRange?.[1]
      },
      responseType: 'blob'
    }).then(res => res.data!)
  }
}
