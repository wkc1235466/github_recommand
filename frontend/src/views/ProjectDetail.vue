<template>
  <div class="project-detail">
    <!-- Back Button -->
    <div class="back-nav">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- Content -->
    <template v-else-if="project">
      <!-- Header -->
      <div class="detail-header">
        <div class="header-main">
          <h1 class="project-title">{{ displayName }}</h1>
          <div class="project-meta">
            <span v-if="projectOwner" class="owner-info">
              <span class="owner-label">作者：</span>
              <a
                :href="ownerGithubUrl"
                target="_blank"
                class="owner-link"
              >
                {{ projectOwner }}
                <el-icon><ExternalLink /></el-icon>
              </a>
            </span>
            <a
              v-if="project.github_url"
              :href="project.github_url"
              target="_blank"
              class="github-link"
            >
              <el-icon><Link /></el-icon>
              {{ githubPath }}
            </a>
          </div>
        </div>
        <div class="header-stats">
          <span v-if="project.stars" class="stars">
            <el-icon><Star /></el-icon>
            {{ formatStars(project.stars) }}
          </span>
        </div>
      </div>

      <!-- Tags -->
      <div class="tags-section">
        <el-tag
          v-for="tag in displayTags"
          :key="tag"
          size="default"
          :type="isUserTag(tag) ? 'success' : 'info'"
          closable
          @close="handleRemoveTag(tag)"
        >
          {{ tag }}
          <el-icon v-if="isUserTag(tag)" style="margin-left: 4px;"><User /></el-icon>
        </el-tag>
        <el-tag v-if="project.category" size="default" type="primary">
          {{ project.category }}
        </el-tag>
        <!-- Add Tag Button -->
        <el-button
          size="small"
          @click="showTagInput = true"
          v-if="!showTagInput"
        >
          <el-icon><Plus /></el-icon>
          添加标签
        </el-button>
        <el-input
          v-if="showTagInput"
          v-model="newTag"
          placeholder="输入新标签"
          size="small"
          style="width: 120px;"
          @keyup.enter="handleAddTag"
          @blur="handleAddTagBlur"
        />
      </div>

      <!-- Info Cards -->
      <div class="info-cards">
        <!-- Description -->
        <el-card class="info-card">
          <template #header>
            <span class="card-title">项目描述</span>
          </template>
          <p class="description">
            {{ project.ai_analysis?.summary || project.description || '暂无描述' }}
          </p>
          <el-tag v-if="project.ai_analysis?.summary" size="small" type="success">
            AI 生成
          </el-tag>
        </el-card>

        <!-- Source Info -->
        <el-card class="info-card">
          <template #header>
            <span class="card-title">推荐来源</span>
          </template>
          <div v-if="allSources.length" class="sources-list">
            <div v-for="(src, idx) in allSources" :key="idx" class="source-item">
              <span class="up-name">{{ src.up_name || '未知UP主' }}</span>
              <span v-if="src.episode_number" class="episode">
                第{{ src.episode_number }}期
              </span>
              <a
                v-if="src.bilibili_url"
                :href="src.bilibili_url"
                target="_blank"
                class="video-link"
              >
                <el-icon><VideoPlay /></el-icon>
                观看视频
              </a>
            </div>
          </div>
          <p v-else class="no-data">暂无来源信息</p>
        </el-card>
      </div>

      <!-- Actions -->
      <div class="action-bar">
        <el-button
          v-if="!project.ai_analysis"
          type="primary"
          @click="handleAnalyze"
          :loading="analyzing"
        >
          <el-icon><MagicStick /></el-icon>
          AI 分析
        </el-button>
        <el-button
          v-if="project.github_url"
          type="default"
          @click="refreshReadme"
          :loading="readmeLoading"
        >
          <el-icon><Refresh /></el-icon>
          刷新 README
        </el-button>
        <el-button type="danger" text @click="handleDelete">
          <el-icon><Delete /></el-icon>
          删除项目
        </el-button>
      </div>

      <!-- README -->
      <el-card class="readme-card">
        <template #header>
          <div class="readme-header">
            <span class="card-title">README.md</span>
            <span v-if="readmeSource" class="readme-source">
              加载自: {{ readmeSource }}
            </span>
          </div>
        </template>

        <div v-if="readmeLoading" class="readme-loading">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <p>加载 README...</p>
        </div>

        <div v-else-if="readmeContent" class="readme-content" v-html="renderedReadme"></div>

        <el-empty v-else description="无法加载 README">
          <el-button type="primary" @click="refreshReadme">重试</el-button>
        </el-empty>
      </el-card>
    </template>

    <!-- Not Found -->
    <el-empty v-else description="项目不存在" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { getProject, deleteProject, analyzeProject, addUserTags, removeUserTag } from '../api/projects'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const project = ref(null)
const readmeContent = ref('')
const readmeLoading = ref(false)
const readmeSource = ref('')
const analyzing = ref(false)
const showTagInput = ref(false)
const newTag = ref('')

const displayTags = computed(() => {
  const aiTags = project.value?.ai_analysis?.suggested_tags || project.value?.tags || []
  const userTags = project.value?.user_tags || []
  // 去重合并
  return [...new Set([...aiTags, ...userTags])]
})

// 判断标签是否为用户标签
const isUserTag = (tag) => {
  const userTags = project.value?.user_tags || []
  return userTags.includes(tag)
}

const githubPath = computed(() => {
  if (!project.value?.github_url) return ''
  try {
    const url = new URL(project.value.github_url)
    return url.pathname.slice(1)
  } catch {
    return project.value.github_url
  }
})

// 从项目名称或URL提取作者
const projectOwner = computed(() => {
  const name = project.value?.name || ''
  const url = project.value?.github_url || ''

  // 从项目名称提取
  if (name.includes('/')) {
    return name.split('/')[0]
  }

  // 从URL提取
  if (url) {
    try {
      const urlObj = new URL(url)
      const parts = urlObj.pathname.slice(1).split('/')
      if (parts.length >= 1) {
        return parts[0]
      }
    } catch {}
  }

  return null
})

// 作者的GitHub主页链接
const ownerGithubUrl = computed(() => {
  if (projectOwner.value) {
    return `https://github.com/${projectOwner.value}`
  }
  return null
})

// 显示简化的项目名称（去掉 owner/）
const displayName = computed(() => {
  const name = project.value?.name || ''
  if (name.includes('/')) {
    return name.split('/').pop()
  }
  return name
})

const allSources = computed(() => {
  if (project.value?.sources) {
    return project.value.sources
  }
  if (project.value?.source) {
    return [project.value.source]
  }
  return []
})

const renderedReadme = computed(() => {
  if (!readmeContent.value) return ''
  return marked(readmeContent.value)
})

const fetchProject = async () => {
  loading.value = true
  try {
    const id = route.params.id
    project.value = await getProject(id)

    // 自动加载 README
    if (project.value?.github_url) {
      await fetchReadme()
    }
  } catch (error) {
    ElMessage.error('获取项目失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const fetchReadme = async () => {
  if (!project.value?.github_url) return

  readmeLoading.value = true
  readmeContent.value = ''

  try {
    // 从 GitHub URL 提取 owner/repo
    const url = new URL(project.value.github_url)
    const parts = url.pathname.slice(1).split('/')
    const owner = parts[0]
    const repo = parts[1]

    // 使用 Cloudflare Worker 代理
    const workerUrl = localStorage.getItem('workerUrl') || 'https://github-readme-proxy.your-name.workers.dev'
    const proxyUrl = `${workerUrl}?owner=${owner}&repo=${repo}`

    const response = await fetch(proxyUrl)
    if (response.ok) {
      readmeContent.value = await response.text()
      readmeSource.value = 'Cloudflare Worker'
    } else {
      throw new Error('Worker request failed')
    }
  } catch (error) {
    console.error('README load error:', error)
    ElMessage.warning('README 加载失败，请检查 Worker URL 配置')
  } finally {
    readmeLoading.value = false
  }
}

const refreshReadme = () => {
  fetchReadme()
}

const handleAnalyze = async () => {
  analyzing.value = true
  try {
        const aiConfig = {
      apiUrl: localStorage.getItem("apiUrl") || "",
      apiKey: localStorage.getItem("apiKey") || "",
      model: localStorage.getItem("model") || "glm-4-flash"
    }
    const result = await analyzeProject(project.value._id, true, aiConfig)
    if (result.success) {
      ElMessage.success('分析完成')
      await fetchProject()
    }
  } catch (error) {
    ElMessage.error('分析失败: ' + error.message)
  } finally {
    analyzing.value = false
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要删除这个项目吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProject(project.value._id)
    ElMessage.success('删除成功')
    router.push({ name: 'Home' })
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + error.message)
    }
  }
}

const handleAddTag = async () => {
  if (!newTag.value.trim()) {
    showTagInput.value = false
    return
  }

  try {
    const result = await addUserTags(project.value._id, [newTag.value.trim()])
    project.value.user_tags = result.tags
    newTag.value = ''
    showTagInput.value = false
    ElMessage.success('标签已添加')
  } catch (error) {
    ElMessage.error('添加标签失败: ' + error.message)
  }
}

const handleAddTagBlur = () => {
  if (newTag.value.trim()) {
    handleAddTag()
  } else {
    showTagInput.value = false
  }
}

const handleRemoveTag = async (tag) => {
  if (!isUserTag(tag)) {
    return // 不能删除 AI 标签
  }

  try {
    const result = await removeUserTag(project.value._id, tag)
    project.value.user_tags = result.tags
    ElMessage.success('标签已删除')
  } catch (error) {
    ElMessage.error('删除标签失败: ' + error.message)
  }
}

const goBack = () => {
  router.push({ name: 'Home' })
}

const formatStars = (stars) => {
  if (!stars) return 'N/A'
  if (stars >= 1000) {
    return (stars / 1000).toFixed(1) + 'k'
  }
  return stars.toLocaleString()
}

onMounted(() => {
  fetchProject()
})
</script>

<style scoped>
.project-detail {
  max-width: 1000px;
  margin: 0 auto;
}

.back-nav {
  margin-bottom: 20px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 0;
  color: #666;
}

.loading-container .el-icon {
  margin-bottom: 16px;
  color: #409eff;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.project-title {
  font-size: 28px;
  font-weight: 600;
  color: #24292f;
  margin: 0 0 8px 0;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.owner-info {
  display: flex;
  align-items: center;
  gap: 4px;
}

.owner-label {
  color: #57606a;
  font-size: 14px;
}

.owner-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #0969da;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
}

.owner-link:hover {
  text-decoration: underline;
}

.github-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #0969da;
  text-decoration: none;
  font-size: 14px;
}

.github-link:hover {
  text-decoration: underline;
}

.header-stats {
  display: flex;
  gap: 16px;
}

.stars {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  color: #57606a;
}

.stars .el-icon {
  color: #f0c14b;
}

.tags-section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.info-card {
  border: 1px solid #d0d7de;
}

.card-title {
  font-weight: 600;
  color: #24292f;
}

.description {
  color: #57606a;
  line-height: 1.6;
  margin: 0 0 8px 0;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.up-name {
  font-weight: 500;
  color: #24292f;
}

.episode {
  padding: 2px 8px;
  background: #f6f8fa;
  border-radius: 4px;
  font-size: 13px;
  color: #57606a;
}

.video-link {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #0969da;
  text-decoration: none;
  font-size: 13px;
}

.video-link:hover {
  text-decoration: underline;
}

.no-data {
  color: #8b949e;
  margin: 0;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.readme-card {
  border: 1px solid #d0d7de;
}

.readme-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.readme-source {
  font-size: 12px;
  color: #8b949e;
}

.readme-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  color: #666;
}

.readme-content {
  max-height: 800px;
  overflow-y: auto;
  padding: 20px;
  background: #f6f8fa;
  border-radius: 8px;
}

.readme-content :deep(h1) {
  font-size: 24px;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 8px;
  margin-top: 0;
}

.readme-content :deep(h2) {
  font-size: 20px;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 8px;
}

.readme-content :deep(h3) {
  font-size: 18px;
}

.readme-content :deep(pre) {
  background: #24292f;
  color: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
}

.readme-content :deep(code) {
  background: #f6f8fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
}

.readme-content :deep(pre code) {
  background: none;
  padding: 0;
}

.readme-content :deep(img) {
  max-width: 100%;
}

.readme-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
}

.readme-content :deep(th),
.readme-content :deep(td) {
  border: 1px solid #d0d7de;
  padding: 8px 12px;
}

.readme-content :deep(th) {
  background: #f6f8fa;
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    gap: 12px;
  }

  .project-title {
    font-size: 22px;
  }

  .info-cards {
    grid-template-columns: 1fr;
  }

  .action-bar {
    flex-wrap: wrap;
  }
}
</style>