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
      <div class="search-bar-left">
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
        <span class="total-count">共 {{ total }} 个项目</span>
      </div>

      <div class="search-bar-right">
        <!-- Tag Search -->
        <el-select
          v-model="selectedTag"
          placeholder="按标签筛选"
          clearable
          filterable
          allow-create
          @change="handleTagChange"
          style="width: 200px;"
        >
          <el-option
            v-for="tag in popularTags"
            :key="tag.name"
            :label="`${tag.name} (${tag.count})`"
            :value="tag.name"
          />
        </el-select>

        <el-checkbox v-model="showNeedsUrl" @change="fetchProjects">
          仅显示需要补全地址的项目
        </el-checkbox>

        <!-- View Toggle -->
        <el-radio-group v-model="viewMode" size="small" class="view-toggle">
          <el-radio-button label="grid">
            <el-icon><Grid /></el-icon>
          </el-radio-button>
          <el-radio-button label="list">
            <el-icon><List /></el-icon>
          </el-radio-button>
        </el-radio-group>
      </div>
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

    <!-- Project Grid/List -->
    <div v-else :class="viewMode === 'grid' ? 'project-grid' : 'project-list'">
      <ProjectCard
        v-for="project in projects"
        :key="project._id"
        :project="project"
        :view-mode="viewMode"
        @delete="handleDelete"
        @analyze="handleAnalyze"
        @click="handleProjectClick"
      />
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        :pager-count="7"
        size="large"
        layout="prev, pager, next"
        @current-change="fetchProjects"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProjectCard from '../components/ProjectCard.vue'
import { getProjects, getCategories, deleteProject, analyzeProject, getPopularTags } from '../api/projects'

const router = useRouter()
const loading = ref(false)
const projects = ref([])
const categories = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedTag = ref('')
const showNeedsUrl = ref(false)
const viewMode = ref('grid') // 'grid' or 'list'
const popularTags = ref([])
let searchTimeout = null

const fetchCategories = async () => {
  try {
    categories.value = await getCategories()
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

const fetchPopularTags = async () => {
  try {
    const data = await getPopularTags(50)
    popularTags.value = data.tags || []
  } catch (error) {
    console.error('Failed to fetch popular tags:', error)
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
      tag: selectedTag.value || undefined,
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

const handleTagChange = () => {
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

const handleProjectClick = (project) => {
  router.push({ name: 'ProjectDetail', params: { id: project._id } })
}

onMounted(() => {
  fetchCategories()
  fetchPopularTags()
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
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.search-bar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-count {
  color: #606266;
  font-size: 14px;
  white-space: nowrap;
}

.search-bar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.view-toggle {
  margin-left: 8px;
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

.project-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding: 16px 0;
}

.pagination :deep(.el-pagination) {
  --el-pagination-button-width: 40px;
  --el-pagination-button-height: 40px;
  --el-pagination-font-size: 16px;
}

.pagination :deep(.el-pager li) {
  font-size: 16px;
  min-width: 40px;
  height: 40px;
  line-height: 40px;
}

.pagination :deep(.btn-prev),
.pagination :deep(.btn-next) {
  width: 40px;
  height: 40px;
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

  .search-bar-left {
    flex-direction: column;
    align-items: stretch;
  }

  .search-bar-right {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>