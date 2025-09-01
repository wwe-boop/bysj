import { request } from './index'

// 实验管理相关API
export const experimentsApi = {
  // 启动批量实验
  startBatchExperiments(config: any): Promise<any> {
    return request.post('/experiments/batch/start', config)
      .then(res => res.data!)
  },

  // 启动消融实验
  startAblationStudy(config: any): Promise<any> {
    return request.post('/experiments/ablation/start', config)
      .then(res => res.data!)
  },

  // 获取实验状态
  getExperimentStatus(experimentId: string): Promise<any> {
    return request.get(`/experiments/status/${experimentId}`)
      .then(res => res.data!)
  },

  // 获取实验结果
  getExperimentResults(experimentId: string): Promise<any> {
    return request.get(`/experiments/results/${experimentId}`)
      .then(res => res.data!)
  },

  // 获取统计分析
  getStatisticalAnalysis(experimentId: string): Promise<any> {
    return request.get(`/experiments/analysis/${experimentId}`)
      .then(res => res.data!)
  },

  // 生成图表
  generateCharts(experimentId: string, chartTypes: string[]): Promise<any> {
    return request.post(`/experiments/charts/${experimentId}`, {
      chart_types: chartTypes
    }).then(res => res.data!)
  },

  // 导出实验结果
  exportResults(experimentId: string, format: 'json' | 'csv' = 'json'): Promise<Blob> {
    return request.get(`/experiments/export/${experimentId}`, {
      params: { format },
      responseType: 'blob'
    }).then(res => res.data!)
  },

  // 列出所有实验
  listExperiments(): Promise<any> {
    return request.get('/experiments/list')
      .then(res => res.data!)
  },

  // 获取实验模板
  getExperimentTemplates(): Promise<any> {
    return request.get('/experiments/templates')
      .then(res => res.data!)
  },

  // 删除实验
  deleteExperiment(experimentId: string): Promise<void> {
    return request.delete(`/experiments/${experimentId}`)
      .then(() => {})
  },

  // 停止实验
  stopExperiment(experimentId: string): Promise<void> {
    return request.post(`/experiments/stop/${experimentId}`)
      .then(() => {})
  },

  // 获取实验配置验证
  validateExperimentConfig(config: any): Promise<any> {
    return request.post('/experiments/validate', config)
      .then(res => res.data!)
  },

  // 获取实验统计摘要
  getExperimentSummary(experimentIds: string[]): Promise<any> {
    return request.post('/experiments/summary', {
      experiment_ids: experimentIds
    }).then(res => res.data!)
  },

  // 比较实验结果
  compareExperiments(experimentIds: string[], metrics: string[]): Promise<any> {
    return request.post('/experiments/compare', {
      experiment_ids: experimentIds,
      metrics: metrics
    }).then(res => res.data!)
  },

  // 生成实验报告
  generateReport(experimentId: string, reportType: string = 'comprehensive'): Promise<any> {
    return request.post(`/experiments/report/${experimentId}`, {
      report_type: reportType
    }).then(res => res.data!)
  },

  // 获取实验日志
  getExperimentLogs(experimentId: string, limit: number = 100): Promise<any> {
    return request.get(`/experiments/logs/${experimentId}`, {
      params: { limit }
    }).then(res => res.data!)
  },

  // 克隆实验配置
  cloneExperiment(experimentId: string, newName: string): Promise<any> {
    return request.post(`/experiments/clone/${experimentId}`, {
      new_name: newName
    }).then(res => res.data!)
  },

  // 获取实验性能指标
  getExperimentMetrics(experimentId: string, metrics: string[]): Promise<any> {
    return request.post(`/experiments/metrics/${experimentId}`, {
      metrics: metrics
    }).then(res => res.data!)
  },

  // 批量删除实验
  batchDeleteExperiments(experimentIds: string[]): Promise<void> {
    return request.post('/experiments/batch/delete', {
      experiment_ids: experimentIds
    }).then(() => {})
  },

  // 获取实验进度详情
  getExperimentProgress(experimentId: string): Promise<any> {
    return request.get(`/experiments/progress/${experimentId}`)
      .then(res => res.data!)
  },

  // 暂停实验
  pauseExperiment(experimentId: string): Promise<void> {
    return request.post(`/experiments/pause/${experimentId}`)
      .then(() => {})
  },

  // 恢复实验
  resumeExperiment(experimentId: string): Promise<void> {
    return request.post(`/experiments/resume/${experimentId}`)
      .then(() => {})
  },

  // 获取实验资源使用情况
  getExperimentResources(experimentId: string): Promise<any> {
    return request.get(`/experiments/resources/${experimentId}`)
      .then(res => res.data!)
  },

  // 设置实验优先级
  setExperimentPriority(experimentId: string, priority: number): Promise<void> {
    return request.post(`/experiments/priority/${experimentId}`, {
      priority: priority
    }).then(() => {})
  },

  // 获取实验队列状态
  getExperimentQueue(): Promise<any> {
    return request.get('/experiments/queue')
      .then(res => res.data!)
  },

  // 清空实验队列
  clearExperimentQueue(): Promise<void> {
    return request.post('/experiments/queue/clear')
      .then(() => {})
  },

  // 获取系统资源状态
  getSystemResources(): Promise<any> {
    return request.get('/experiments/system/resources')
      .then(res => res.data!)
  },

  // 获取实验建议
  getExperimentSuggestions(baseConfig: any): Promise<any> {
    return request.post('/experiments/suggestions', baseConfig)
      .then(res => res.data!)
  },

  // 优化实验配置
  optimizeExperimentConfig(config: any, objectives: string[]): Promise<any> {
    return request.post('/experiments/optimize', {
      config: config,
      objectives: objectives
    }).then(res => res.data!)
  },

  // 获取实验历史
  getExperimentHistory(limit: number = 50, offset: number = 0): Promise<any> {
    return request.get('/experiments/history', {
      params: { limit, offset }
    }).then(res => res.data!)
  },

  // 搜索实验
  searchExperiments(query: string, filters: any = {}): Promise<any> {
    return request.post('/experiments/search', {
      query: query,
      filters: filters
    }).then(res => res.data!)
  },

  // 获取实验标签
  getExperimentTags(): Promise<string[]> {
    return request.get('/experiments/tags')
      .then(res => res.data!)
  },

  // 添加实验标签
  addExperimentTag(experimentId: string, tag: string): Promise<void> {
    return request.post(`/experiments/tags/${experimentId}`, {
      tag: tag
    }).then(() => {})
  },

  // 移除实验标签
  removeExperimentTag(experimentId: string, tag: string): Promise<void> {
    return request.delete(`/experiments/tags/${experimentId}/${tag}`)
      .then(() => {})
  },

  // 获取实验依赖关系
  getExperimentDependencies(experimentId: string): Promise<any> {
    return request.get(`/experiments/dependencies/${experimentId}`)
      .then(res => res.data!)
  },

  // 设置实验依赖
  setExperimentDependency(experimentId: string, dependsOn: string): Promise<void> {
    return request.post(`/experiments/dependencies/${experimentId}`, {
      depends_on: dependsOn
    }).then(() => {})
  },

  // 获取实验通知设置
  getExperimentNotifications(experimentId: string): Promise<any> {
    return request.get(`/experiments/notifications/${experimentId}`)
      .then(res => res.data!)
  },

  // 设置实验通知
  setExperimentNotifications(experimentId: string, settings: any): Promise<void> {
    return request.post(`/experiments/notifications/${experimentId}`, settings)
      .then(() => {})
  }
}
