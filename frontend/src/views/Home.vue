<template>
  <div class="home">
    <!-- Category Tabs -->
    <div class="category-tabs">
      <el-radio-group v-model="selectedCategory" @change="handleCategoryChange">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button
          v-for="cat in categories"
          :key="cat.id"
          :label="cat.id"
        >
          {{ cat.name }} ({{ cat.count }})
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- Search and Filter -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索项目名称或描述..."
        clearable
        @input="handleSearch"
        style="max-width: 400px;"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-checkbox v-model="showNeedsUrl" @change="fetchProjects">
        仅显示需要补全地址的项目
      </el-checkbox>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- Empty State -->
    <el-empty
      v-else-if="!loading && projects.length === 0"
      description="暂无项目数据，点击右上角「更新数据」按钮获取最新推荐"
    />

    <!-- Project Grid -->
    <div v-else class="project-grid">
      <ProjectCard
        v-for="project in projects"
        :key="project._id"
        :project="project"
        @delete="handleDelete"
        @analyze="handleAnalyze"
        @view-readme="handleViewReadme"
      />
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchProjects"
      />
    </div>

    <!-- README Dialog -->
    <el-dialog
      v-model="readmeDialogVisible"
      :title="readmeProject?.name"
      width="80%"
      top="5vh"
    >
      <div v-if="readmeLoading" class="readme-loading">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>加载 README...</p>
      </div>
      <div v-else-if="readmeContent" class="readme-content" v-html="renderedReadme"></div>
      <el-empty v-else description="无法加载 README" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import ProjectCard from '../components/ProjectCard.vue'
import { getProjects, getCategories, deleteProject, analyzeProject, getProjectReadme } from '../api/projects'

const loading = ref(false)
const projects = ref([])
const categories = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const selectedCategory = ref('')
const showNeedsUrl = ref(false)
let searchTimeout = null

// README dialog
const readmeDialogVisible = ref(false)
const readmeLoading = ref(false)
const readmeContent = ref('')
const readmeProject = ref(null)

const renderedReadme = computed(() => {
  if (!readmeContent.value) return ''
  return marked(readmeContent.value)
})

const fetchCategories = async () => {
  try {
    categories.value = await getCategories()
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

const fetchProjects = async () => {
  loading.value = true
  try {
    const data = await getProjects({
      page: currentPage.value,
      pageSize: pageSize.value,
      search: searchQuery.value || undefined,
      category: selectedCategory.value || undefined,
      needsUrl: showNeedsUrl.value || undefined,
    })
    projects.value = data.projects
    total.value = data.total
  } catch (error) {
    ElMessage.error('获取项目列表失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleCategoryChange = () => {
  currentPage.value = 1
  fetchProjects()
}

const handleSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    fetchProjects()
  }, 300)
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个项目吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProject(id)
    ElMessage.success('删除成功')
    fetchProjects()
    fetchCategories()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + error.message)
    }
  }
}

const handleAnalyze = async (id) => {
  try {
    ElMessage.info('正在分析项目...')
    const result = await analyzeProject(id, false)
    if (result.success) {
      ElMessage.success(`分析完成: ${result.category}`)
      fetchProjects()
    }
  } catch (error) {
    ElMessage.error('分析失败: ' + error.message)
  }
}

const handleViewReadme = async (project) => {
  readmeProject.value = project
  readmeDialogVisible.value = true
  readmeLoading.value = true
  readmeContent.value = ''

  try {
    const data = await getProjectReadme(project._id)
    readmeContent.value = data.readme
  } catch (error) {
    ElMessage.error('加载 README 失败: ' + error.message)
  } finally {
    readmeLoading.value = false
  }
}

onMounted(() => {
  fetchCategories()
  fetchProjects()
})
</script>

<style scoped>
.home {
  padding: 0;
}

.category-tabs {
  margin-bottom: 20px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.category-tabs :deep(.el-radio-button__inner) {
  padding: 8px 16px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #666;
}

.loading-container .el-icon {
  margin-bottom: 16px;
  color: #409eff;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.readme-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  color: #666;
}

.readme-content {
  max-height: 70vh;
  overflow-y: auto;
  padding: 20px;
  background: #f6f8fa;
  border-radius: 8px;
}

.readme-content :deep(h1) {
  font-size: 24px;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 8px;
}

.readme-content :deep(h2) {
  font-size: 20px;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 8px;
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
}

.readme-content :deep(pre code) {
  background: none;
  padding: 0;
}

@media (max-width: 768px) {
  .project-grid {
    grid-template-columns: 1fr;
  }

  .search-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-bar .el-input {
    max-width: 100% !important;
  }
}
</style>