<template>
  <div id="app">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <div class="logo">
            <el-icon :size="28"><Star /></el-icon>
            <span>GitHub 项目推荐</span>
          </div>
          <div class="header-actions">
            <!-- 模型选择器 -->
            <el-dropdown
              v-if="availableModels.length > 0"
              @command="handleModelChange"
              trigger="click"
              class="model-selector"
            >
              <el-button text class="model-select-btn">
                <el-icon><Cpu /></el-icon>
                <span class="model-name" :title="currentModelDisplay">{{ currentModelDisplay }}</span>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="model-dropdown-menu">
                  <el-dropdown-item
                    v-for="model in availableModels"
                    :key="model.value"
                    :command="model.value"
                    :class="{ active: currentModel === model.value }"
                  >
                    <div class="model-dropdown-item">
                      <span class="model-provider">{{ model.providerName }}</span>
                      <span class="model-divider">/</span>
                      <span class="model-model">{{ model.modelName }}</span>
                      <el-icon v-if="currentModel === model.value" class="check-icon"><Check /></el-icon>
                    </div>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>

            <el-button text @click="showSettings = true">
              <el-icon><Setting /></el-icon>
              设置
            </el-button>
            <el-button
              type="primary"
              :loading="crawling"
              @click="triggerCrawl"
            >
              <el-icon><Refresh /></el-icon>
              {{ crawling ? '更新中...' : '更新数据' }}
            </el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>

    <!-- Settings Dialog -->
    <SettingsDialog v-model="showSettings" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { triggerCrawl as crawlApi } from './api/projects'
import SettingsDialog from './components/SettingsDialog.vue'

const crawling = ref(false)
const showSettings = ref(false)

// 模型选择相关
const currentModel = ref('')
const allModels = ref([])
const deletedModelIds = ref(new Set())

// 默认模型列表（与 SettingsDialog 保持一致）
const DEFAULT_MODELS = [
  {
    id: 'claude-sonnet-4-5-20251001',
    name: 'Claude Sonnet 4.5',
    provider: 'Anthropic'
  },
  {
    id: 'claude-opus-4-5-20251001',
    name: 'Claude Opus 4.5',
    provider: 'Anthropic'
  },
  {
    id: 'glm-4-flash',
    name: 'GLM-4-Flash',
    provider: 'BigModel'
  },
  {
    id: 'glm-4.7',
    name: 'GLM-4.7',
    provider: 'BigModel'
  },
  {
    id: 'glm-5',
    name: 'GLM-5',
    provider: 'BigModel'
  },
  {
    id: 'glm-5-turbo',
    name: 'GLM-5-Turbo',
    provider: 'BigModel'
  },
  {
    id: 'kimi-k2.5',
    name: 'Kimi K2.5',
    provider: 'Moonshot'
  },
  {
    id: 'kimi-k2-turbo-preview',
    name: 'Kimi K2 Turbo',
    provider: 'Moonshot'
  },
]

// 计算所有可用模型
const availableModels = computed(() => {
  const models = []
  allModels.value.forEach(model => {
    models.push({
      value: model.id,
      label: `${model.provider} / ${model.name}`,
      providerName: model.provider,
      modelName: model.name
    })
  })
  return models
})

// 当前选中的模型显示文本
const currentModelDisplay = computed(() => {
  const model = availableModels.value.find(m => m.value === currentModel.value)
  if (model) {
    return `${model.providerName} / ${model.modelName}`
  }
  return '选择模型'
})

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

// 加载模型配置
const loadModelConfig = () => {
  // 加载当前选中的模型
  currentModel.value = localStorage.getItem('model') || 'claude-sonnet-4-5-20251001'

  // 加载已删除模型列表
  loadDeletedModels()

  // 加载模型列表
  const customModels = localStorage.getItem('customModels')
  if (customModels) {
    try {
      const custom = JSON.parse(customModels)
      allModels.value = [...DEFAULT_MODELS, ...custom.map(m => ({
        id: m.id,
        name: m.name,
        provider: '自定义'
      }))]
    } catch {
      allModels.value = [...DEFAULT_MODELS]
    }
  } else {
    allModels.value = [...DEFAULT_MODELS]
  }

  // 过滤已删除的模型
  allModels.value = allModels.value.filter(m => !deletedModelIds.value.has(m.id))

  // 如果当前模型不在列表中，添加它
  const currentModelExists = allModels.value.find(m => m.id === currentModel.value)
  if (!currentModelExists && currentModel.value) {
    allModels.value.unshift({
      id: currentModel.value,
      name: currentModel.value,
      provider: '历史'
    })
  }
}

// 切换模型
const handleModelChange = (modelId) => {
  currentModel.value = modelId
  localStorage.setItem('model', modelId)

  ElMessage.success(`已切换到: ${availableModels.value.find(m => m.value === modelId)?.label || modelId}`)
}

// 监听存储变化（当设置对话框保存时）
const handleStorageChange = (e) => {
  if (e.key === 'model' || e.key === 'customModels' || e.key === 'deletedModels') {
    loadModelConfig()
  }
}

onMounted(() => {
  loadModelConfig()
  window.addEventListener('storage', handleStorageChange)
})

onUnmounted(() => {
  window.removeEventListener('storage', handleStorageChange)
})

const triggerCrawl = async () => {
  crawling.value = true
  try {
    // 从 localStorage 读取 AI 配置
    const apiUrl = localStorage.getItem('apiUrl') || ''
    const apiKey = localStorage.getItem('apiKey') || ''
    const model = localStorage.getItem('model') || 'claude-sonnet-4-5-20251001'

    if (!apiUrl || !apiKey) {
      ElMessage.warning('请先在设置中配置 AI API')
      showSettings.value = true
      return
    }

    const result = await crawlApi({
      apiUrl,
      apiKey,
      model,
    })

    if (result.has_new) {
      ElMessage.success(result.message)
    } else {
      ElMessage.info(result.message || '数据已是最新的')
    }
  } catch (error) {
    ElMessage.error('更新失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    crawling.value = false
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  min-height: 100vh;
  background-color: #f6f8fa;
}

.el-container {
  min-height: 100vh;
}

.header {
  background-color: #24292f;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 64px !important;
}

.header-content {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
}

.logo .el-icon {
  color: #f0c14b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 模型选择器 */
.model-selector {
  margin-right: 8px;
}

.model-select-btn {
  color: #8b949e;
  max-width: 200px;
}

.model-select-btn:hover {
  color: white;
}

.model-select-btn .model-name {
  margin: 0 4px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-dropdown-menu {
  min-width: 220px;
  max-height: 400px;
  overflow-y: auto;
}

.model-dropdown-item {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
}

.model-provider {
  color: #0969da;
  font-weight: 500;
  font-size: 12px;
}

.model-divider {
  color: #8c959f;
  font-size: 12px;
}

.model-model {
  color: #24292f;
  flex: 1;
}

.model-dropdown-item .check-icon {
  color: #1a7f37;
  margin-left: 8px;
}

.el-dropdown-item.active {
  background-color: #f6f8fa;
}

.header-actions .el-button--text {
  color: #8b949e;
}

.header-actions .el-button--text:hover {
  color: white;
}

.el-main {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}
</style>