// 基础类型定义

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
  code?: number
}

// 仿真相关类型
export interface SimulationStatus {
  isRunning: boolean
  currentTime: number
  progress: number
  scenario?: string
  startTime?: number
  duration?: number
}

export interface SimulationConfig {
  scenario: string
  duration: number
  parameters?: Record<string, any>
}

// 网络状态类型
export interface SatelliteInfo {
  id: number
  name: string
  lat: number
  lon: number
  alt: number
  x: number
  y: number
  z: number
  active: boolean
  connections: number[]
}

export interface NetworkState {
  timeStep: number
  satellites: SatelliteInfo[]
  links: LinkInfo[]
  topology: number[][]
  linkUtilization: Record<string, number>
  linkCapacity: Record<string, number>
  activeFlows: FlowInfo[]
  queueLengths: Record<number, number>
}

export interface LinkInfo {
  id: string
  source: number
  target: number
  capacity: number
  utilization: number
  latency: number
  active: boolean
}

export interface FlowInfo {
  id: string
  source: number
  destination: number
  bandwidth: number
  latency: number
  qosClass: string
  route: number[]
}

// 性能指标类型
export interface PerformanceMetrics {
  timeStep: number
  averageThroughput: number
  averageLatency: number
  packetLossRate: number
  jitter: number
  averagePositioningAccuracy: number
  positioningCoverage: number
  averageGdop: number
  averageCrlb: number
  admissionRate: number
  resourceUtilization: number
  energyConsumption: number
  qoeScore: number
  positioningScore: number
  jointObjective: number
}

// 准入控制类型
export interface UserRequest {
  userId: string
  serviceType: string
  bandwidthMbps: number
  maxLatencyMs: number
  minReliability: number
  priority: number
  userLat: number
  userLon: number
  durationSeconds: number
  timestamp: number
}

export interface AdmissionResult {
  decision: 'accept' | 'reject' | 'degraded_accept' | 'delayed_accept' | 'partial_accept'
  allocatedSatellite?: number
  allocatedBandwidth?: number
  confidence: number
  reason: string
  timestamp: number
}

export interface AdmissionStatistics {
  totalRequests: number
  acceptedRequests: number
  rejectedRequests: number
  degradedRequests: number
  delayedRequests: number
  partialRequests: number
  acceptanceRate: number
  averageDecisionTime: number
  qosViolations: number
}

// 定位服务类型
export interface PositioningRequest {
  userId: string
  lat: number
  lon: number
  accuracy: number
  timestamp: number
}

export interface PositioningResult {
  userId: string
  estimatedLat: number
  estimatedLon: number
  accuracy: number
  gdop: number
  visibleSatellites: number[]
  signalStrength: number[]
  timestamp: number
}

export interface PositioningMetrics {
  timeStep: number
  gdopValues: number[]
  positioningAccuracy: number[]
  coverageRatio: number
  visibleSatellitesCount: number[]
  avgSignalStrength: number[]
}

// 场景管理类型
export interface SimulationScenario {
  name: string
  description: string
  durationSeconds: number
  trafficPattern: string
  constellationConfig: Record<string, any>
  admissionConfig: Record<string, any>
  dsroqConfig: Record<string, any>
  positioningConfig: Record<string, any>
  simulationConfig: Record<string, any>
  expectedResults?: Record<string, any>
  tags?: string[]
}

// 统计分析类型
export interface StatisticsData {
  timeRange: [number, number]
  metrics: PerformanceMetrics[]
  admissionStats: AdmissionStatistics
  positioningStats: PositioningMetrics
  networkStats: {
    averageUtilization: number
    peakUtilization: number
    activeLinks: number
    totalCapacity: number
  }
}

// 图表数据类型
export interface ChartDataPoint {
  timestamp: number
  value: number
  label?: string
}

export interface ChartSeries {
  name: string
  data: ChartDataPoint[]
  color?: string
  type?: 'line' | 'bar' | 'area'
}

// WebSocket消息类型
export interface WebSocketMessage {
  type: string
  data: any
  timestamp: number
}

// 用户界面状态类型
export interface UIState {
  sidebarCollapsed: boolean
  theme: 'light' | 'dark'
  language: 'zh-CN' | 'en-US'
  notifications: Notification[]
}

export interface Notification {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  timestamp: number
  duration?: number
  actions?: NotificationAction[]
}

export interface NotificationAction {
  label: string
  action: () => void
  type?: 'primary' | 'success' | 'warning' | 'danger'
}

// 表格相关类型
export interface TableColumn {
  prop: string
  label: string
  width?: number
  minWidth?: number
  sortable?: boolean
  formatter?: (row: any, column: any, cellValue: any) => string
}

export interface TablePagination {
  currentPage: number
  pageSize: number
  total: number
}

// 表单相关类型
export interface FormRule {
  required?: boolean
  message?: string
  trigger?: 'blur' | 'change'
  validator?: (rule: any, value: any, callback: any) => void
}

export interface FormRules {
  [key: string]: FormRule[]
}
