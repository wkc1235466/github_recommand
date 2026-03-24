<template>
  <el-dialog
    v-model="visible"
    title="API 配置"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form label-width="100px" label-position="left">
      <!-- Worker URL -->
      <el-form-item label="Worker URL">
        <el-input
          v-model="settings.workerUrl"
          placeholder="https://your-worker.workers.dev"
          clearable
        />
        <template #extra>
          <div class="form-hint-with-link">
            <span>GitHub README 代理地址，用于访问 GitHub</span>
            <el-link
              href="https://workers.cloudflare.com/"
              target="_blank"
              type="primary"
              style="margin-left: 8px"
            >
              Cloudflare 官网
            </el-link>
          </div>
        </template>
      </el-form-item>

      <!-- Worker 代码说明 -->
      <el-form-item>
        <el-button
          type="info"
          link
          @click="showWorkerCode = true"
          style="padding: 0"
        >
          <el-icon><Document /></el-icon>
          查看 Worker 部署代码
        </el-button>
      </el-form-item>

      <!-- API 基础 URL -->
      <el-form-item label="API 基础 URL">
        <el-input
          v-model="settings.apiUrl"
          placeholder="https://api.anthropic.com/v1/messages"
          clearable
        />
        <template #extra>
          <span class="form-hint">Claude 兼容 API 地址</span>
        </template>
      </el-form-item>

      <!-- API 密钥 -->
      <el-form-item label="API 密钥">
        <el-input
          v-model="settings.apiKey"
          type="password"
          placeholder="请输入 API Key"
          show-password
          clearable
        />
      </el-form-item>

      <!-- 模型列表 -->
      <el-form-item label="API 基础 URL">
        <div class="models-container">
          <div
            v-for="model in availableModels"
            :key="model.id"
            class="model-row"
            :class="{ selected: settings.model === model.id }"
            @click="selectModel(model.id)"
          >
            <div class="model-info">
              <div class="model-name">{{ model.name }}</div>
              <div class="model-id">{{ model.id }}</div>
            </div>
            <div class="model-actions">
              <el-button
                size="small"
                circle
                :loading="modelTestStatus[model.id] === 'testing'"
                @click.stop="testModel(model)"
                title="测试连接"
              >
                <el-icon v-if="modelTestStatus[model.id] !== 'testing'">
                  <CircleCheck v-if="modelTestStatus[model.id] === 'success'" />
                  <CircleClose v-else-if="modelTestStatus[model.id] === 'error'" />
                  <Connection v-else />
                </el-icon>
              </el-button>
              <el-button
                size="small"
                circle
                type="danger"
                @click.stop="removeModel(model)"
                title="删除模型"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <el-button
            type="primary"
            link
            class="add-model-btn"
            @click="showAddModel = true"
          >
            <el-icon><Plus /></el-icon>
            添加模型
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </div>
    </template>
  </el-dialog>

  <!-- 添加模型对话框 -->
  <el-dialog
    v-model="showAddModel"
    title="添加自定义模型"
    width="400px"
    :close-on-click-modal="false"
    append-to-body
  >
    <el-form label-width="80px">
      <el-form-item label="模型名称">
        <el-input v-model="newModel.name" placeholder="如：Claude Sonnet 4.5" />
      </el-form-item>
      <el-form-item label="模型 ID">
        <el-input v-model="newModel.id" placeholder="如：claude-sonnet-4-5-20251001" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAddModel = false">取消</el-button>
      <el-button type="primary" @click="addModel" :disabled="!newModel.name || !newModel.id">
        添加
      </el-button>
    </template>
  </el-dialog>

  <!-- Worker 代码对话框 -->
  <el-dialog
    v-model="showWorkerCode"
    title="GitHub README 代理 Worker 代码"
    width="800px"
    :close-on-click-modal="false"
    append-to-body
  >
    <div class="worker-code-content">
      <el-alert
        title="部署步骤"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      >
        <ol style="margin: 8px 0; padding-left: 20px;">
          <li>登录 <el-link href="https://workers.cloudflare.com/" target="_blank" type="primary">Cloudflare Dashboard</el-link></li>
          <li>进入 Workers & Pages -> Create application -> Create Worker</li>
          <li>复制下方代码到编辑器中</li>
          <li>Save and deploy</li>
          <li>复制 Worker URL 到上方配置框</li>
        </ol>
      </el-alert>

      <el-input
        :model-value="workerCode"
        type="textarea"
        :rows="20"
        readonly
        placeholder="Worker 代码"
        class="worker-code-textarea"
      />

      <el-button
        type="primary"
        @click="copyWorkerCode"
        style="margin-top: 12px"
      >
        <el-icon><DocumentCopy /></el-icon>
        复制代码
      </el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  CircleCheck,
  CircleClose,
  Connection,
  Delete,
  Document,
  DocumentCopy
} from '@element-plus/icons-vue'
import { testModelConnection } from '../api/ai'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

// 设置数据
const settings = reactive({
  workerUrl: 'https://github1recommand.2834390326.workers.dev',
  githubToken: '',
  apiUrl: 'https://api.anthropic.com/v1/messages',
  apiKey: '',
  apiType: 'claude',
  model: 'claude-sonnet-4-5-20251001',
})

// 对话框状态
const visible = ref(props.modelValue)
const showAddModel = ref(false)
const showWorkerCode = ref(false)

// 模型测试状态
const modelTestStatus = reactive({})

// 已删除的模型 ID 列表（用于阻止重新加载）
const deletedModelIds = ref(new Set())

// 新模型数据
const newModel = reactive({
  name: '',
  id: '',
})

// 默认模型列表（Claude 兼容）
const DEFAULT_MODELS = [
  {
    id: 'claude-sonnet-4-5-20251001',
    name: 'Claude Sonnet 4.5',
    provider: 'anthropic'
  },
  {
    id: 'claude-opus-4-5-20251001',
    name: 'Claude Opus 4.5',
    provider: 'anthropic'
  },
  {
    id: 'glm-4-flash',
    name: 'GLM-4-Flash',
    provider: 'bigmodel'
  },
  {
    id: 'glm-4.7',
    name: 'GLM-4.7',
    provider: 'bigmodel'
  },
  {
    id: 'glm-5',
    name: 'GLM-5',
    provider: 'bigmodel'
  },
  {
    id: 'glm-5-turbo',
    name: 'GLM-5-Turbo',
    provider: 'bigmodel'
  },
  {
    id: 'kimi-k2.5',
    name: 'Kimi K2.5',
    provider: 'moonshot'
  },
  {
    id: 'kimi-k2-turbo-preview',
    name: 'Kimi K2 Turbo',
    provider: 'moonshot'
  },
]

// 可用模型列表
const availableModels = ref([])

// 选择模型
const selectModel = (modelId) => {
  settings.model = modelId
}

// 添加模型
const addModel = () => {
  availableModels.value.push({
    id: newModel.id,
    name: newModel.name,
    provider: 'custom'
  })

  // 选择新添加的模型
  settings.model = newModel.id

  // 重置表单
  newModel.name = ''
  newModel.id = ''
  showAddModel.value = false

  ElMessage.success('模型已添加')
}

// 测试模型
const testModel = async (model) => {
  if (!settings.apiKey) {
    ElMessage.warning('请先配置 API Key')
    return
  }

  modelTestStatus[model.id] = 'testing'

  const result = await testModelConnection(
    model.id,
    settings.apiUrl,
    settings.apiKey,
    settings.apiType
  )

  modelTestStatus[model.id] = result.success ? 'success' : 'error'

  if (result.success) {
    ElMessage.success(`${model.name} 连接成功`)
  } else {
    ElMessage.error(`${model.name} 连接失败: ${result.message}`)
  }
}

// 保存已删除模型列表到 localStorage
const saveDeletedModels = () => {
  const deleted = Array.from(deletedModelIds.value)
  localStorage.setItem('deletedModels', JSON.stringify(deleted))
}

// 从 localStorage 加载已删除模型列表
const loadDeletedModels = () => {
  const deleted = localStorage.getItem('deletedModels')
  if (deleted) {
    try {
      const deletedArray = JSON.parse(deleted)
      deletedModelIds.value = new Set(deletedArray)
    } catch {
      deletedModelIds.value = new Set()
    }
  }
}

// 删除模型
const removeModel = async (model) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${model.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const index = availableModels.value.findIndex(m => m.id === model.id)
    if (index > -1) {
      availableModels.value.splice(index, 1)

      // 记录已删除的模型 ID 并持久化
      deletedModelIds.value.add(model.id)
      saveDeletedModels()

      // 如果删除的是当前选中的模型，切换到第一个模型
      if (settings.model === model.id && availableModels.value.length > 0) {
        settings.model = availableModels.value[0].id
      }

      delete modelTestStatus[model.id]
      ElMessage.success('模型已删除')
    }
  } catch {
    // 用户取消删除
  }
}

// 加载设置
const loadSettings = () => {
  // 从 localStorage 加载（支持旧格式）
  settings.workerUrl = localStorage.getItem('workerUrl') || 'https://github1recommand.2834390326.workers.dev'
  settings.githubToken = localStorage.getItem('githubToken') || ''
  settings.apiUrl = localStorage.getItem('apiUrl') || 'https://api.anthropic.com/v1/messages'
  settings.apiKey = localStorage.getItem('apiKey') || localStorage.getItem('glmApiKey') || ''
  settings.apiType = localStorage.getItem('apiType') || 'claude'
  settings.model = localStorage.getItem('model') || 'claude-sonnet-4-5-20251001'

  // 加载已删除模型列表
  loadDeletedModels()

  // 加载自定义模型
  const customModels = localStorage.getItem('customModels')
  if (customModels) {
    try {
      const custom = JSON.parse(customModels)
      availableModels.value = [...DEFAULT_MODELS, ...custom]
    } catch {
      availableModels.value = [...DEFAULT_MODELS]
    }
  } else {
    availableModels.value = [...DEFAULT_MODELS]
  }

  // 过滤已删除的模型
  availableModels.value = availableModels.value.filter(m => !deletedModelIds.value.has(m.id))

  // 如果当前模型不在列表中，添加它（兼容旧配置）
  const currentModelExists = availableModels.value.find(m => m.id === settings.model)
  if (!currentModelExists && settings.model) {
    availableModels.value.unshift({
      id: settings.model,
      name: settings.model,
      provider: 'legacy'
    })
  }
}

// 保存设置
const handleSave = () => {
  // 保存到 localStorage
  localStorage.setItem('workerUrl', settings.workerUrl)
  localStorage.setItem('githubToken', settings.githubToken)
  localStorage.setItem('apiUrl', settings.apiUrl)
  localStorage.setItem('apiKey', settings.apiKey)
  localStorage.setItem('apiType', settings.apiType)
  localStorage.setItem('model', settings.model)

  // 保存自定义模型
  const customModels = availableModels.value.filter(m => m.provider === 'custom')
  localStorage.setItem('customModels', JSON.stringify(customModels))

  // 通知其他窗口/标签页
  window.dispatchEvent(new Event('storage'))

  ElMessage.success('配置已保存')
  visible.value = false
}

// 取消
const handleCancel = () => {
  visible.value = false
}

// 组件挂载时加载删除记录
onMounted(() => {
  loadDeletedModels()
})

// 监听 visible 变化
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) {
      loadSettings()
    }
  }
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// Worker 代码
const workerCode = `/**
 * GitHub README 代理 Worker
 * 用于解决跨域和网络墙问题
 *
 * 部署步骤：
 * 1. 登录 Cloudflare -> Workers & Pages
 * 2. Create application -> Create Worker
 * 3. 复制此代码到编辑器中
 * 4. Save and deploy
 *
 * 使用方式：
 * GET https://your-worker.workers.dev/?owner=vuejs&repo=core
 */

export default {
  async fetch(request, env, ctx) {
    // 全局异常捕获，防止连接中断
    try {
      // 处理 OPTIONS 预检请求
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '86400',
          },
        });
      }

      // 只允许 GET 请求
      if (request.method !== 'GET') {
        return new Response(
          JSON.stringify({ error: 'Method not allowed, only GET' }),
          {
            status: 405,
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            },
          }
        );
      }

      const url = new URL(request.url);
      const owner = url.searchParams.get('owner');
      const repo = url.searchParams.get('repo');
      const branch = url.searchParams.get('branch') || 'main';
      const file = url.searchParams.get('file') || 'README.md';

      // 根路径返回使用说明
      if (!owner && !repo) {
        return new Response(
          JSON.stringify({
            message: 'GitHub README Proxy',
            usage: '?owner=OWNER&repo=REPO',
            example: '?owner=vuejs&repo=core',
          }),
          {
            status: 200,
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            },
          }
        );
      }

      // 参数校验
      if (!owner || !repo) {
        return new Response(
          JSON.stringify({ error: 'Missing required params: owner and repo' }),
          {
            status: 400,
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            },
          }
        );
      }

      // 尝试不同分支
      const branches = branch === 'main' ? ['main', 'master'] : [branch];
      let lastError = null;

      for (const b of branches) {
        const targetUrl = \`https://raw.githubusercontent.com/\${owner}/\${repo}/\${b}/\${file}\`;

        try {
          // 带超时的 fetch 请求，避免阻塞
          const response = await Promise.race([
            fetch(targetUrl, {
              headers: {
                // 更标准的 User-Agent，降低限流风险
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
              },
            }),
            // 5秒超时
            new Promise((_, reject) => setTimeout(() => reject(new Error('Request timeout')), 5000)
          ]);

          if (response.ok) {
            // 直接返回流，不加载到内存，适配大文件
            const headers = new Headers(response.headers);
            headers.set('Access-Control-Allow-Origin', '*');
            headers.set('Access-Control-Allow-Methods', 'GET, OPTIONS');
            headers.set('Cache-Control', 'public, max-age=3600');
            headers.set('Content-Type', 'text/plain; charset=utf-8');

            return new Response(response.body, {
              status: 200,
              headers,
            });
          }
          lastError = new Error(\`HTTP \${response.status}\`);
        } catch (e) {
          lastError = e;
          continue;
        }
      }

      // 所有分支尝试失败
      return new Response(
        JSON.stringify({
          error: 'README not found',
          tried: branches,
          reason: lastError?.message || 'Unknown error'
        }),
        {
          status: 404,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    } catch (globalErr) {
      // 全局异常兜底
      return new Response(
        JSON.stringify({
          error: 'Server internal error',
          message: globalErr.message
        }),
        {
          status: 500,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }
  },
};`

// 复制 Worker 代码
const copyWorkerCode = async () => {
  try {
    await navigator.clipboard.writeText(workerCode)
    ElMessage.success('代码已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
}

.form-hint-with-link {
  display: flex;
  align-items: center;
}

.form-hint-with-link .form-hint {
  flex: 1;
}

.models-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px;
  width: 100%;
  box-sizing: border-box;
}

.model-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  border-radius: 4px;
  transition: background-color 0.2s;
  cursor: pointer;
  min-height: 32px;
}

.model-row:hover {
  background-color: #f6f8fa;
}

.model-row.selected {
  background-color: #ecf5ff;
  border: 1px solid #409eff;
}

.model-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.model-id {
  font-size: 12px;
  color: #909399;
}

.model-actions {
  display: flex;
  gap: 8px;
}

.add-model-btn {
  margin-top: 8px;
  width: 100%;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.worker-code-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.worker-code-textarea {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
</style>
