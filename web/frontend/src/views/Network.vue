<template>
  <div class="network-view">
    <div class="page-header">
      <h1>网络管理</h1>
      <p>LEO卫星网络拓扑与连接管理</p>
    </div>

    <el-row :gutter="20">
      <!-- 网络状态 -->
      <el-col :span="8">
        <el-card title="网络状态">
          <template #header>
            <span>网络状态</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="refreshNetworkStatus">
              刷新
            </el-button>
          </template>
          
          <div class="status-item">
            <span>在线卫星数量:</span>
            <el-tag type="success">{{ networkStatus.onlineSatellites }}</el-tag>
          </div>
          
          <div class="status-item">
            <span>活跃链路数量:</span>
            <el-tag type="primary">{{ networkStatus.activeLinks }}</el-tag>
          </div>
          
          <div class="status-item">
            <span>网络延迟:</span>
            <el-tag :type="getLatencyType(networkStatus.averageLatency)">
              {{ networkStatus.averageLatency }}ms
            </el-tag>
          </div>
          
          <div class="status-item">
            <span>吞吐量:</span>
            <el-tag type="info">{{ networkStatus.throughput }} Mbps</el-tag>
          </div>
        </el-card>
      </el-col>

      <!-- 网络拓扑 -->
      <el-col :span="16">
        <el-card title="网络拓扑">
          <template #header>
            <span>网络拓扑</span>
            <el-button-group style="float: right;">
              <el-button size="small" @click="toggleTopologyView">
                {{ topologyView === '2d' ? '3D视图' : '2D视图' }}
              </el-button>
              <el-button size="small" @click="exportTopology">导出</el-button>
            </el-button-group>
          </template>
          
          <div class="topology-container" ref="topologyRef">
            <!-- 这里将集成网络拓扑可视化组件 -->
            <div class="topology-placeholder">
              <el-icon size="64"><Connection /></el-icon>
              <p>网络拓扑图</p>
              <p class="text-muted">{{ topologyView === '2d' ? '2D' : '3D' }}视图模式</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 链路管理 -->
    <el-card class="mt-4" title="链路管理">
      <template #header>
        <span>链路管理</span>
        <el-button style="float: right;" type="primary" size="small" @click="showAddLinkDialog">
          添加链路
        </el-button>
      </template>
      
      <el-table :data="linkData" stripe>
        <el-table-column prop="id" label="链路ID" width="100" />
        <el-table-column prop="source" label="源卫星" width="120" />
        <el-table-column prop="target" label="目标卫星" width="120" />
        <el-table-column prop="type" label="链路类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getLinkTypeColor(row.type)">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="bandwidth" label="带宽" width="100" />
        <el-table-column prop="latency" label="延迟" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '活跃' : '断开' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="editLink(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteLink(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加链路对话框 -->
    <el-dialog v-model="addLinkDialogVisible" title="添加链路" width="500px">
      <el-form :model="newLink" label-width="100px">
        <el-form-item label="源卫星">
          <el-select v-model="newLink.source" placeholder="选择源卫星">
            <el-option v-for="sat in satellites" :key="sat.id" :label="sat.name" :value="sat.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标卫星">
          <el-select v-model="newLink.target" placeholder="选择目标卫星">
            <el-option v-for="sat in satellites" :key="sat.id" :label="sat.name" :value="sat.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="链路类型">
          <el-select v-model="newLink.type" placeholder="选择链路类型">
            <el-option label="ISL" value="isl" />
            <el-option label="GSL" value="gsl" />
            <el-option label="UDL" value="udl" />
          </el-select>
        </el-form-item>
        <el-form-item label="带宽">
          <el-input v-model="newLink.bandwidth" placeholder="输入带宽" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="addLinkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addLink">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection } from '@element-plus/icons-vue'

// 响应式数据
const topologyRef = ref()
const topologyView = ref('2d')
const addLinkDialogVisible = ref(false)

const networkStatus = reactive({
  onlineSatellites: 66,
  activeLinks: 132,
  averageLatency: 45,
  throughput: 1250
})

const newLink = reactive({
  source: '',
  target: '',
  type: '',
  bandwidth: ''
})

const linkData = ref([
  {
    id: 'L001',
    source: 'SAT-001',
    target: 'SAT-002',
    type: 'ISL',
    bandwidth: '100 Mbps',
    latency: '12ms',
    status: 'active'
  },
  {
    id: 'L002',
    source: 'SAT-002',
    target: 'SAT-003',
    type: 'ISL',
    bandwidth: '100 Mbps',
    latency: '15ms',
    status: 'active'
  }
])

const satellites = ref([
  { id: 'SAT-001', name: '卫星-001' },
  { id: 'SAT-002', name: '卫星-002' },
  { id: 'SAT-003', name: '卫星-003' }
])

// 方法
const refreshNetworkStatus = () => {
  ElMessage.success('网络状态已刷新')
}

const toggleTopologyView = () => {
  topologyView.value = topologyView.value === '2d' ? '3d' : '2d'
}

const exportTopology = () => {
  ElMessage.success('拓扑图导出成功')
}

const getLatencyType = (latency: number) => {
  if (latency < 30) return 'success'
  if (latency < 60) return 'warning'
  return 'danger'
}

const getLinkTypeColor = (type: string) => {
  const colors = {
    'ISL': 'primary',
    'GSL': 'success',
    'UDL': 'warning'
  }
  return colors[type] || 'info'
}

const showAddLinkDialog = () => {
  addLinkDialogVisible.value = true
}

const addLink = () => {
  // 添加链路逻辑
  ElMessage.success('链路添加成功')
  addLinkDialogVisible.value = false
}

const editLink = (link: any) => {
  ElMessage.info(`编辑链路: ${link.id}`)
}

const deleteLink = (link: any) => {
  ElMessage.warning(`删除链路: ${link.id}`)
}

onMounted(() => {
  // 初始化网络拓扑
})
</script>

<style scoped>
.network-view {
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

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.topology-container {
  height: 400px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.topology-placeholder {
  text-align: center;
  color: #909399;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}

.mt-4 {
  margin-top: 20px;
}
</style>
