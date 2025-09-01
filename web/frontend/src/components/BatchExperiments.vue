<template>
  <div class="batch-experiments">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>批量实验管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            创建批量实验
          </el-button>
        </div>
      </template>
      
      <!-- 实验列表 -->
      <el-table :data="experiments" stripe>
        <el-table-column prop="name" label="实验名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="totalRuns" label="总运行数" width="100" />
        <el-table-column prop="completedRuns" label="已完成" width="100" />
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.round((row.completedRuns / row.totalRuns) * 100)"
              :status="getProgressStatus(row)"
            />
          </template>
        </el-table-column>
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
            <el-button size="small" @click="viewResults(row)">查看结果</el-button>
            <el-button 
              size="small" 
              :type="row.status === 'running' ? 'warning' : 'success'"
              @click="toggleExperiment(row)"
            >
              {{ row.status === 'running' ? '暂停' : '启动' }}
            </el-button>
            <el-button size="small" type="danger" @click="deleteExperiment(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建实验对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建批量实验" width="600px">
      <el-form :model="experimentForm" :rules="experimentRules" ref="experimentFormRef" label-width="120px">
        <el-form-item label="实验名称" prop="name">
          <el-input v-model="experimentForm.name" placeholder="输入实验名称" />
        </el-form-item>
        
        <el-form-item label="实验描述" prop="description">
          <el-input 
            v-model="experimentForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="输入实验描述"
          />
        </el-form-item>
        
        <el-form-item label="参数扫描">
          <div class="parameter-sweep">
            <div v-for="(param, index) in experimentForm.parameters" :key="index" class="param-row">
              <el-select v-model="param.name" placeholder="选择参数" style="width: 150px;">
                <el-option label="学习率" value="learning_rate" />
                <el-option label="批大小" value="batch_size" />
                <el-option label="网络层数" value="num_layers" />
                <el-option label="隐藏单元" value="hidden_units" />
              </el-select>
              
              <el-input 
                v-model="param.values" 
                placeholder="参数值 (逗号分隔)"
                style="width: 200px; margin: 0 10px;"
              />
              
              <el-button 
                size="small" 
                type="danger" 
                @click="removeParameter(index)"
                :disabled="experimentForm.parameters.length <= 1"
              >
                删除
              </el-button>
            </div>
            
            <el-button size="small" @click="addParameter">添加参数</el-button>
          </div>
        </el-form-item>
        
        <el-form-item label="重复次数">
          <el-input-number v-model="experimentForm.repeats" :min="1" :max="50" />
        </el-form-item>
        
        <el-form-item label="并行数">
          <el-input-number v-model="experimentForm.parallelJobs" :min="1" :max="16" />
        </el-form-item>
        
        <el-form-item label="评估指标">
          <el-checkbox-group v-model="experimentForm.metrics">
            <el-checkbox label="qoe">QoE得分</el-checkbox>
            <el-checkbox label="admission_rate">准入率</el-checkbox>
            <el-checkbox label="fairness">公平性</el-checkbox>
            <el-checkbox label="efficiency">效率</el-checkbox>
            <el-checkbox label="convergence">收敛性</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createExperiment">创建</el-button>
      </template>
    </el-dialog>

    <!-- 结果查看对话框 -->
    <el-dialog v-model="showResultsDialog" title="实验结果" width="80%">
      <div v-if="selectedExperiment">
        <h3>{{ selectedExperiment.name }}</h3>
        
        <!-- 结果统计 -->
        <el-row :gutter="20" class="mb-4">
          <el-col :span="6">
            <el-statistic title="总运行数" :value="selectedExperiment.totalRuns" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="已完成" :value="selectedExperiment.completedRuns" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="成功率" :value="95.2" suffix="%" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="平均用时" :value="12.5" suffix="分钟" />
          </el-col>
        </el-row>
        
        <!-- 结果图表 -->
        <div class="results-charts">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="chart-container">
                <h4>参数性能关系</h4>
                <div class="chart-placeholder">参数-性能散点图</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="chart-container">
                <h4>收敛曲线</h4>
                <div class="chart-placeholder">训练收敛曲线</div>
              </div>
            </el-col>
          </el-row>
        </div>
        
        <!-- 详细结果表格 -->
        <el-table :data="mockResults" stripe class="mt-4">
          <el-table-column prop="runId" label="运行ID" width="100" />
          <el-table-column prop="parameters" label="参数配置" />
          <el-table-column prop="qoe" label="QoE" width="100" />
          <el-table-column prop="admissionRate" label="准入率" width="100" />
          <el-table-column prop="fairness" label="公平性" width="100" />
          <el-table-column prop="duration" label="用时" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">
                {{ row.status === 'completed' ? '完成' : '运行中' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 响应式数据
const showCreateDialog = ref(false)
const showResultsDialog = ref(false)
const selectedExperiment = ref(null)
const experimentFormRef = ref()

const experiments = ref([
  {
    id: 1,
    name: '学习率扫描实验',
    description: '测试不同学习率对模型性能的影响',
    totalRuns: 50,
    completedRuns: 35,
    status: 'running',
    created: '2024-01-15 10:30'
  },
  {
    id: 2,
    name: '网络结构对比',
    description: '对比不同网络结构的性能表现',
    totalRuns: 24,
    completedRuns: 24,
    status: 'completed',
    created: '2024-01-14 14:20'
  }
])

const experimentForm = reactive({
  name: '',
  description: '',
  parameters: [
    { name: '', values: '' }
  ],
  repeats: 5,
  parallelJobs: 4,
  metrics: ['qoe', 'admission_rate']
})

const experimentRules = {
  name: [
    { required: true, message: '请输入实验名称', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入实验描述', trigger: 'blur' }
  ]
}

const mockResults = ref([
  {
    runId: 'R001',
    parameters: 'lr=0.001, batch=32',
    qoe: 4.2,
    admissionRate: 0.94,
    fairness: 0.85,
    duration: '12.3min',
    status: 'completed'
  },
  {
    runId: 'R002',
    parameters: 'lr=0.01, batch=32',
    qoe: 3.8,
    admissionRate: 0.91,
    fairness: 0.82,
    duration: '11.8min',
    status: 'completed'
  }
])

// 方法
const getProgressStatus = (experiment: any) => {
  if (experiment.status === 'completed') return 'success'
  if (experiment.status === 'failed') return 'exception'
  return undefined
}

const getStatusType = (status: string) => {
  const types = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'paused': 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts = {
    'pending': '等待中',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败',
    'paused': '已暂停'
  }
  return texts[status] || '未知'
}

const viewResults = (experiment: any) => {
  selectedExperiment.value = experiment
  showResultsDialog.value = true
}

const toggleExperiment = (experiment: any) => {
  if (experiment.status === 'running') {
    experiment.status = 'paused'
    ElMessage.success('实验已暂停')
  } else {
    experiment.status = 'running'
    ElMessage.success('实验已启动')
  }
}

const deleteExperiment = async (experiment: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除实验 "${experiment.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const index = experiments.value.findIndex(e => e.id === experiment.id)
    if (index > -1) {
      experiments.value.splice(index, 1)
      ElMessage.success('实验删除成功')
    }
  } catch {
    // 用户取消
  }
}

const addParameter = () => {
  experimentForm.parameters.push({ name: '', values: '' })
}

const removeParameter = (index: number) => {
  experimentForm.parameters.splice(index, 1)
}

const createExperiment = async () => {
  if (!experimentFormRef.value) return
  
  try {
    await experimentFormRef.value.validate()
    
    // 计算总运行数
    const totalCombinations = experimentForm.parameters.reduce((total, param) => {
      const values = param.values.split(',').filter(v => v.trim())
      return total * (values.length || 1)
    }, 1)
    
    const newExperiment = {
      id: Date.now(),
      name: experimentForm.name,
      description: experimentForm.description,
      totalRuns: totalCombinations * experimentForm.repeats,
      completedRuns: 0,
      status: 'pending',
      created: new Date().toLocaleString()
    }
    
    experiments.value.push(newExperiment)
    ElMessage.success('批量实验创建成功')
    showCreateDialog.value = false
    
    // 重置表单
    resetForm()
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const resetForm = () => {
  Object.assign(experimentForm, {
    name: '',
    description: '',
    parameters: [{ name: '', values: '' }],
    repeats: 5,
    parallelJobs: 4,
    metrics: ['qoe', 'admission_rate']
  })
}
</script>

<style scoped>
.batch-experiments {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.parameter-sweep {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 15px;
  background: #f9f9f9;
}

.param-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.param-row:last-child {
  margin-bottom: 0;
}

.results-charts {
  margin: 20px 0;
}

.chart-container h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #333;
}

.chart-placeholder {
  height: 200px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 20px;
}
</style>
