<template>
  <div class="scenarios-view">
    <div class="page-header">
      <h1>场景管理</h1>
      <p>仿真场景配置与管理</p>
    </div>

    <!-- 场景列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>仿真场景</span>
          <el-button type="primary" @click="showCreateDialog">
            创建场景
          </el-button>
        </div>
      </template>
      
      <el-table :data="scenarios" stripe>
        <el-table-column prop="name" label="场景名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="constellation" label="星座配置" width="150" />
        <el-table-column prop="users" label="用户数量" width="100" />
        <el-table-column prop="duration" label="仿真时长" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created" label="创建时间" width="150" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="editScenario(row)">编辑</el-button>
            <el-button size="small" type="success" @click="runScenario(row)">运行</el-button>
            <el-button size="small" type="danger" @click="deleteScenario(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑场景对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEditing ? '编辑场景' : '创建场景'" 
      width="800px"
    >
      <el-form :model="scenarioForm" :rules="scenarioRules" ref="scenarioFormRef" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="场景名称" prop="name">
              <el-input v-model="scenarioForm.name" placeholder="输入场景名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="仿真时长" prop="duration">
              <el-input-number v-model="scenarioForm.duration" :min="1" :max="24" /> 小时
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="场景描述" prop="description">
          <el-input 
            v-model="scenarioForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="输入场景描述"
          />
        </el-form-item>
        
        <el-form-item label="星座配置">
          <el-select v-model="scenarioForm.constellation" placeholder="选择星座配置">
            <el-option label="Starlink (66颗卫星)" value="starlink" />
            <el-option label="OneWeb (48颗卫星)" value="oneweb" />
            <el-option label="自定义配置" value="custom" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="用户分布">
          <el-row :gutter="10">
            <el-col :span="8">
              <el-input-number v-model="scenarioForm.users.count" :min="1" :max="10000" />
            </el-col>
            <el-col :span="16">
              <el-select v-model="scenarioForm.users.distribution" placeholder="选择分布模式">
                <el-option label="随机分布" value="random" />
                <el-option label="城市集中" value="urban" />
                <el-option label="均匀分布" value="uniform" />
              </el-select>
            </el-col>
          </el-row>
        </el-form-item>
        
        <el-form-item label="网络配置">
          <el-checkbox-group v-model="scenarioForm.networkFeatures">
            <el-checkbox label="admission">准入控制</el-checkbox>
            <el-checkbox label="positioning">定位服务</el-checkbox>
            <el-checkbox label="handover">切换管理</el-checkbox>
            <el-checkbox label="qos">QoS保障</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="环境参数">
          <el-row :gutter="10">
            <el-col :span="8">
              <div class="param-item">
                <label>天气条件:</label>
                <el-select v-model="scenarioForm.environment.weather" size="small">
                  <el-option label="晴朗" value="clear" />
                  <el-option label="多云" value="cloudy" />
                  <el-option label="雨天" value="rainy" />
                </el-select>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="param-item">
                <label>干扰水平:</label>
                <el-select v-model="scenarioForm.environment.interference" size="small">
                  <el-option label="低" value="low" />
                  <el-option label="中" value="medium" />
                  <el-option label="高" value="high" />
                </el-select>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="param-item">
                <label>负载水平:</label>
                <el-select v-model="scenarioForm.environment.load" size="small">
                  <el-option label="轻载" value="light" />
                  <el-option label="中载" value="medium" />
                  <el-option label="重载" value="heavy" />
                </el-select>
              </div>
            </el-col>
          </el-row>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveScenario">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 响应式数据
const dialogVisible = ref(false)
const isEditing = ref(false)
const scenarioFormRef = ref()

const scenarios = ref([
  {
    id: 1,
    name: '城市高密度场景',
    description: '模拟城市环境下的高密度用户接入',
    constellation: 'starlink',
    users: 5000,
    duration: 2,
    status: 'ready',
    created: '2024-01-15 10:30'
  },
  {
    id: 2,
    name: '海洋覆盖测试',
    description: '测试海洋区域的卫星覆盖能力',
    constellation: 'oneweb',
    users: 1000,
    duration: 4,
    status: 'running',
    created: '2024-01-14 14:20'
  }
])

const scenarioForm = reactive({
  name: '',
  description: '',
  constellation: '',
  duration: 1,
  users: {
    count: 1000,
    distribution: 'random'
  },
  networkFeatures: ['admission', 'positioning'],
  environment: {
    weather: 'clear',
    interference: 'low',
    load: 'medium'
  }
})

const scenarioRules = {
  name: [
    { required: true, message: '请输入场景名称', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入场景描述', trigger: 'blur' }
  ],
  duration: [
    { required: true, message: '请设置仿真时长', trigger: 'blur' }
  ]
}

// 方法
const getStatusType = (status: string) => {
  const types = {
    'ready': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts = {
    'ready': '就绪',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败'
  }
  return texts[status] || '未知'
}

const showCreateDialog = () => {
  isEditing.value = false
  resetForm()
  dialogVisible.value = true
}

const editScenario = (scenario: any) => {
  isEditing.value = true
  // 填充表单数据
  Object.assign(scenarioForm, scenario)
  dialogVisible.value = true
}

const runScenario = async (scenario: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要运行场景 "${scenario.name}" 吗？`,
      '确认运行',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    ElMessage.success(`场景 "${scenario.name}" 开始运行`)
    scenario.status = 'running'
  } catch {
    // 用户取消
  }
}

const deleteScenario = async (scenario: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除场景 "${scenario.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const index = scenarios.value.findIndex(s => s.id === scenario.id)
    if (index > -1) {
      scenarios.value.splice(index, 1)
      ElMessage.success('场景删除成功')
    }
  } catch {
    // 用户取消
  }
}

const saveScenario = async () => {
  if (!scenarioFormRef.value) return
  
  try {
    await scenarioFormRef.value.validate()
    
    if (isEditing.value) {
      ElMessage.success('场景更新成功')
    } else {
      // 添加新场景
      const newScenario = {
        id: Date.now(),
        ...scenarioForm,
        users: scenarioForm.users.count,
        status: 'ready',
        created: new Date().toLocaleString()
      }
      scenarios.value.push(newScenario)
      ElMessage.success('场景创建成功')
    }
    
    dialogVisible.value = false
  } catch (error) {
    console.error('保存失败:', error)
  }
}

const resetForm = () => {
  Object.assign(scenarioForm, {
    name: '',
    description: '',
    constellation: '',
    duration: 1,
    users: {
      count: 1000,
      distribution: 'random'
    },
    networkFeatures: ['admission', 'positioning'],
    environment: {
      weather: 'clear',
      interference: 'low',
      load: 'medium'
    }
  })
}
</script>

<style scoped>
.scenarios-view {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-item {
  margin-bottom: 10px;
}

.param-item label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #666;
}
</style>
