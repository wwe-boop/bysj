import { request } from './index'
import type { 
  UserRequest, 
  AdmissionResult, 
  AdmissionStatistics 
} from '@/types'

// 准入控制API
export const admissionApi = {
  // 处理准入请求
  processRequest(userRequest: UserRequest): Promise<AdmissionResult> {
    return request.post<AdmissionResult>('/admission/request', userRequest)
      .then(res => res.data!)
  },

  // 获取准入统计
  getStatistics(): Promise<AdmissionStatistics> {
    return request.get<AdmissionStatistics>('/admission/statistics')
      .then(res => res.data!)
  },

  // 获取准入配置
  getConfig(): Promise<any> {
    return request.get('/admission/config').then(res => res.data!)
  },

  // 更新准入配置
  updateConfig(config: any): Promise<void> {
    return request.put('/admission/config', config).then(() => {})
  },

  // 获取可用算法
  getAvailableAlgorithms(): Promise<any[]> {
    return request.get<any[]>('/admission/algorithms').then(res => res.data!)
  },

  // 获取准入历史
  getHistory(limit = 100, offset = 0): Promise<any> {
    return request.get('/admission/history', {
      params: { limit, offset }
    }).then(res => res.data!)
  }
}

// 定位服务API
export const positioningApi = {
  // 处理定位请求
  processRequest(request: any): Promise<any> {
    return request.post('/positioning/request', request).then(res => res.data!)
  },

  // 获取定位质量
  getQuality(lat: number, lon: number): Promise<any> {
    return request.get('/positioning/quality', {
      params: { lat, lon }
    }).then(res => res.data!)
  },

  // 获取定位覆盖
  getCoverage(params: any = {}): Promise<any> {
    return request.get('/positioning/coverage', { params }).then(res => res.data!)
  },

  // 获取定位统计
  getStatistics(): Promise<any> {
    return request.get('/positioning/statistics').then(res => res.data!)
  },

  // 获取定位配置
  getConfig(): Promise<any> {
    return request.get('/positioning/config').then(res => res.data!)
  },

  // 更新定位配置
  updateConfig(config: any): Promise<void> {
    return request.put('/positioning/config', config).then(() => {})
  }
}
