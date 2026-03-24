<template>
  <el-card
    class="project-card"
    :class="{ 'list-mode': viewMode === 'list' }"
    shadow="hover"
    @click="handleClick"
  >
    <div :class="viewMode === 'list' ? 'list-layout' : 'grid-layout'">
      <!-- Project Name -->
      <div class="project-header">
        <span class="project-name" @click.stop>
          <el-icon><Folder /></el-icon>
          {{ displayName }}
        </span>
        <el-tag v-if="project.category" size="small" type="primary">
          {{ project.category }}
        </el-tag>
      </div>

      <!-- Description -->
      <p class="description">
        {{ truncateDescription(project.ai_analysis?.summary || project.description || '暂无描述') }}
      </p>

      <!-- Tags -->
      <div v-if="displayTags.length" class="tags">
        <el-tag
          v-for="tag in displayTags.slice(0, 5)"
          :key="tag"
          size="small"
          :type="isUserTag(tag) ? 'success' : 'info'"
        >
          {{ tag }}
        </el-tag>
      </div>

      <!-- Source Info -->
      <div v-if="allSources.length > 0" class="source-info">
        <span class="up-name">{{ firstSource?.up_name || '未知UP主' }}</span>
        <span class="episode" v-if="firstSource?.episode_number">
          第{{ firstSource.episode_number }}期
        </span>
      </div>

      <!-- Actions (shown on hover) -->
      <div class="card-actions" @click.stop>
        <el-button
          type="danger"
          size="small"
          text
          @click="$emit('delete', project._id)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button
          v-if="!project.ai_analysis"
          size="small"
          type="primary"
          text
          @click="$emit('analyze', project._id)"
        >
          <el-icon><MagicStick /></el-icon>
          AI分析
        </el-button>
        <a
          v-if="project.github_url"
          :href="project.github_url"
          target="_blank"
          class="action-link"
        >
          <el-icon><Link /></el-icon>
          GitHub
        </a>
        <a
          v-if="firstSource?.bilibili_url"
          :href="firstSource.bilibili_url"
          target="_blank"
          class="action-link"
        >
          <el-icon><VideoPlay /></el-icon>
          视频
        </a>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  viewMode: {
    type: String,
    default: 'grid',
  },
})

const emit = defineEmits(['delete', 'analyze', 'click'])
const router = useRouter()

const allSources = computed(() => {
  if (props.project.sources) {
    return props.project.sources
  }
  if (props.project.source) {
    return [props.project.source]
  }
  return []
})

const firstSource = computed(() => {
  return allSources.value[0] || null
})

const displayTags = computed(() => {
  // 合并 AI 标签和用户标签
  const aiTags = props.project.ai_analysis?.suggested_tags || props.project.tags || []
  const userTags = props.project.user_tags || []
  // 去重合并，最多显示5个
  const allTags = [...new Set([...aiTags, ...userTags])]
  return allTags.slice(0, 5)
})

// 判断标签是否为用户标签
const isUserTag = (tag) => {
  const userTags = props.project.user_tags || []
  return userTags.includes(tag)
}

// 显示简化的项目名称（去掉 owner/）
const displayName = computed(() => {
  const name = props.project.name || ''
  if (name.includes('/')) {
    return name.split('/').pop()
  }
  return name
})

// 截断描述，保持卡片高度一致
const truncateDescription = (text) => {
  if (!text) return '暂无描述'
  const maxLen = 60
  if (text.length > maxLen) {
    return text.slice(0, maxLen) + '...'
  }
  return text
}

const handleClick = () => {
  emit('click', props.project)
  router.push({ name: 'ProjectDetail', params: { id: props.project._id } })
}
</script>

<style scoped>
.project-card {
  border-radius: 8px;
  border: 1px solid #d0d7de;
  transition: all 0.2s ease;
  cursor: pointer;
  width: 100%;
  height: 100%;
  min-height: 180px;
  display: flex;
  flex-direction: column;
}

.project-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.project-card:hover {
  border-color: #0969da;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.project-card:hover .card-actions {
  opacity: 1;
}

/* Grid Layout */
.grid-layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* List Layout */
.list-mode .list-layout {
  display: grid;
  grid-template-columns: 1fr 2fr auto auto auto;
  align-items: center;
  gap: 16px;
}

.list-mode .description {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-mode .tags {
  flex-wrap: nowrap;
}

.list-mode :deep(.el-card__body) {
  padding: 12px 16px;
}

/* Common Styles */
.project-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-name {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0969da;
  font-weight: 600;
  font-size: 15px;
}

.description {
  color: #57606a;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
  min-height: 40px;
  max-height: 40px;
  overflow: hidden;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
}

.source-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #8b949e;
}

.up-name {
  font-weight: 500;
  color: #57606a;
}

.episode {
  padding: 2px 6px;
  background: #f6f8fa;
  border-radius: 4px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.action-link {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #57606a;
  text-decoration: none;
  border-radius: 4px;
}

.action-link:hover {
  background: #f6f8fa;
  color: #0969da;
}

@media (max-width: 768px) {
  .list-mode .list-layout {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .list-mode .description {
    max-width: 100%;
    white-space: normal;
  }

  .card-actions {
    opacity: 1;
  }
}
</style>