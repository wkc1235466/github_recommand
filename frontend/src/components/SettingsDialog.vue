<template>
  <el-dialog
    v-model="visible"
    title="API 配置"
    width="550px"
    :close-on-click-modal="false"
  >
    <el-form label-width="120px" label-position="left">
      <!-- README 代理配置 -->
      <el-divider content-position="left">README 代理</el-divider>

      <el-form-item label="Worker URL">
        <el-input
          v-model="localSettings.workerUrl"
          placeholder="https://your-worker.workers.dev"
          clearable
        />
        <template #extra>
          <span class="form-hint">Cloudflare Worker 代理地址，用于加载 README</span>
        </template>
      </el-form-item>

      <!-- AI 模型配置 -->
      <el-divider content-position="left">AI 模型配置</el-divider>

      <el-form-item label="API URL">
        <el-input
          v-model="localSettings.apiUrl"
          placeholder="https://open.bigmodel.cn/api/paas/v4/chat/completions"
          clearable
        />
        <template #extra>
          <span class="form-hint">兼容 OpenAI 格式的 API 地址</span>
        </template>
      </el-form-item>

      <el-form-item label="API Key">
        <el-input
          v-model="localSettings.apiKey"
          type="password"
          placeholder="请输入 API Key"
          show-password
          clearable
        />
        <template #extra>
          <span class="form-hint">用于 AI 标签生成和项目分类</span>
        </template>
      </el-form-item>

      <el-form-item label="模型">
        <el-select
          v-model="localSettings.model"
          placeholder="选择模型"
          allow-create
          filterable
          style="width: 100%"
        >
          <el-option-group label="智谱 AI">
            <el-option label="GLM-4-Flash (推荐)" value="glm-4-flash" />
            <el-option label="GLM-4" value="glm-4" />
            <el-option label="GLM-4-Plus" value="glm-4-plus" />
          </el-option-group>
          <el-option-group label="阿里云">
            <el-option label="Qwen-Turbo" value="qwen-turbo" />
            <el-option label="Qwen-Plus" value="qwen-plus" />
            <el-option label="Qwen-Max" value="qwen-max" />
          </el-option-group>
          <el-option-group label="DeepSeek">
            <el-option label="DeepSeek-Chat" value="deepseek-chat" />
            <el-option label="DeepSeek-Coder" value="deepseek-coder" />
          </el-option-group>
          <el-option-group label="OpenAI">
            <el-option label="GPT-4o" value="gpt-4o" />
            <el-option label="GPT-4o-mini" value="gpt-4o-mini" />
            <el-option label="GPT-4-Turbo" value="gpt-4-turbo" />
          </el-option-group>
        </el-select>
        <template #extra>
          <span class="form-hint">可输入自定义模型名称</span>
        </template>
      </el-form-item>

      <!-- GitHub 配置 -->
      <el-divider content-position="left">GitHub 配置</el-divider>

      <el-form-item label="GitHub Token">
        <el-input
          v-model="localSettings.githubToken"
          type="password"
          placeholder="可选，提高 GitHub API 限制"
          show-password
          clearable
        />
        <template #extra>
          <span class="form-hint">可选，提高 GitHub API 请求限制</span>
        </template>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const localSettings = reactive({
  workerUrl: '',
  apiUrl: '',
  apiKey: '',
  model: '',
  githubToken: '',
})

// 默认值
const DEFAULTS = {
  apiUrl: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
  model: 'glm-4-flash',
}

// Sync visibility
watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    loadSettings()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// Load settings from localStorage
const loadSettings = () => {
  localSettings.workerUrl = localStorage.getItem('workerUrl') || ''
  localSettings.apiUrl = localStorage.getItem('apiUrl') || DEFAULTS.apiUrl
  localSettings.apiKey = localStorage.getItem('apiKey') || localStorage.getItem('glmApiKey') || ''
  localSettings.model = localStorage.getItem('model') || DEFAULTS.model
  localSettings.githubToken = localStorage.getItem('githubToken') || ''
}

// Save settings
const handleSave = () => {
  localStorage.setItem('workerUrl', localSettings.workerUrl)
  localStorage.setItem('apiUrl', localSettings.apiUrl)
  localStorage.setItem('apiKey', localSettings.apiKey)
  localStorage.setItem('model', localSettings.model)
  localStorage.setItem('githubToken', localSettings.githubToken)

  // 兼容旧字段名
  localStorage.setItem('glmApiKey', localSettings.apiKey)

  ElMessage.success('配置已保存')
  visible.value = false
}

// Cancel
const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #8b949e;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

:deep(.el-divider__text) {
  font-size: 13px;
  color: #57606a;
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}
</style>