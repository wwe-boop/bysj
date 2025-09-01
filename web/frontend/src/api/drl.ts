import { request } from './index'

// DRL训练相关API
export const drlApi = {
  // 启动DRL训练
  startTraining(config: any): Promise<any> {
    return request.post('/admission/drl/training/start', config)
      .then(res => res.data!)
  },

  // 停止DRL训练
  stopTraining(trainingId?: string): Promise<any> {
    return request.post('/admission/drl/training/stop', { trainingId })
      .then(res => res.data!)
  },

  // 获取训练状态
  getTrainingStatus(): Promise<any> {
    return request.get('/admission/drl/training/status')
      .then(res => res.data!)
  },

  // 获取训练指标
  getTrainingMetrics(trainingId?: string, limit = 1000): Promise<any> {
    return request.get('/admission/drl/training/metrics', {
      params: { trainingId, limit }
    }).then(res => res.data!)
  },

  // 获取环境状态
  getEnvironmentState(): Promise<any> {
    return request.get('/admission/drl/environment/state')
      .then(res => res.data!)
  },

  // 获取奖励函数配置
  getRewardConfig(): Promise<any> {
    return request.get('/admission/drl/reward/config')
      .then(res => res.data!)
  },

  // 更新奖励函数配置
  updateRewardConfig(config: any): Promise<void> {
    return request.put('/admission/drl/reward/config', config)
      .then(() => {})
  },

  // 评估模型性能
  evaluateModel(modelId: string, episodes = 10): Promise<any> {
    return request.post('/admission/drl/model/evaluate', {
      modelId,
      episodes
    }).then(res => res.data!)
  },

  // 获取模型列表
  getModels(): Promise<any[]> {
    return request.get('/admission/drl/models')
      .then(res => res.data!)
  },

  // 保存训练模型
  saveModel(name: string, description?: string): Promise<any> {
    return request.post('/admission/drl/model/save', {
      name,
      description
    }).then(res => res.data!)
  },

  // 加载训练模型
  loadModel(modelId: string): Promise<any> {
    return request.post('/admission/drl/model/load', {
      modelId
    }).then(res => res.data!)
  },

  // 获取训练日志
  getTrainingLogs(trainingId?: string, limit = 100): Promise<any> {
    return request.get('/admission/drl/training/logs', {
      params: { trainingId, limit }
    }).then(res => res.data!)
  },

  // 导出训练数据
  exportTrainingData(trainingId?: string): Promise<Blob> {
    return request.get('/admission/drl/training/export', {
      params: { trainingId },
      responseType: 'blob'
    }).then(res => res.data!)
  }
}
