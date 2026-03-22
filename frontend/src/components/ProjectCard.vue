<template>
  <el-card class="project-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <a
            v-if="project.github_url"
            :href="project.github_url"
            target="_blank"
            class="project-name"
          >
            <el-icon><Link /></el-icon>
            {{ project.name }}
          </a>
          <span v-else class="project-name no-url">
            <el-icon><Document /></el-icon>
            {{ project.name }}
            <el-tag size="small" type="warning">待补全地址</el-tag>
          </span>
        </div>
        <div class="header-right">
          <el-tag v-if="project.category" size="small" type="primary">
            {{ project.category }}
          </el-tag>
          <el-button
            type="danger"
            size="small"
            text
            @click="$emit('delete', project._id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </template>

    <div class="project-content">
      <!-- Stars -->
      <div class="project-stats">
        <span class="stars">
          <el-icon><Star /></el-icon>
          {{ formatStars(project.stars) }}
        </span>
      </div>

      <!-- Description (AI generated or original) -->
      <p class="description">
        {{ project.ai_analysis?.summary || project.description || '暂无描述' }}
      </p>
      <el-tag v-if="project.ai_analysis?.summary" size="small" type="success">
        AI 生成简介
      </el-tag>

      <!-- Recommend Reason -->
      <div v-if="project.recommend_reason" class="recommend-reason">
        <el-icon><ChatDotSquare /></el-icon>
        <span>{{ project.recommend_reason }}</span>
      </div>

      <!-- AI Suggested Tags -->
      <div v-if="project.ai_analysis?.suggested_tags?.length" class="tags">
        <el-tag
          v-for="tag in project.ai_analysis.suggested_tags"
          :key="tag"
          size="small"
          type="info"
        >
          {{ tag }}
        </el-tag>
      </div>
      <!-- Original Tags fallback -->
      <div v-else-if="project.tags && project.tags.length > 0" class="tags">
        <el-tag
          v-for="tag in project.tags"
          :key="tag"
          size="small"
          type="info"
        >
          {{ tag }}
        </el-tag>
      </div>

      <!-- Source Info (multiple sources) -->
      <div v-if="allSources.length > 0" class="source-info">
        <el-icon><VideoCamera /></el-icon>
        <div class="sources-list">
          <div v-for="(src, idx) in allSources" :key="idx" class="source-item">
            <span v-if="src.up_name" class="up-name">{{ src.up_name }}</span>
            <span v-if="src.video_title" class="video-title">
              {{ src.video_title }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="card-footer">
        <!-- View README -->
        <el-button
          v-if="project.github_url"
          size="small"
          @click="$emit('view-readme', project)"
        >
          <el-icon><Document /></el-icon>
          README
        </el-button>

        <!-- AI Analyze Button -->
        <el-button
          v-if="!project.ai_analysis"
          size="small"
          type="primary"
          plain
          @click="$emit('analyze', project._id)"
        >
          <el-icon><MagicStick /></el-icon>
          AI 分析
        </el-button>

        <!-- Source Link -->
        <a
          v-if="firstSource?.bilibili_url"
          :href="firstSource.bilibili_url"
          target="_blank"
          class="source-link"
        >
          <el-icon><VideoPlay /></el-icon>
          观看视频
        </a>

        <!-- GitHub Link -->
        <a
          v-if="project.github_url"
          :href="project.github_url"
          target="_blank"
          class="github-link"
        >
          <el-icon><Platform /></el-icon>
          GitHub
        </a>
      </div>
    </template>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
})

defineEmits(['delete', 'analyze', 'view-readme'])

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

const formatStars = (stars) => {
  if (!stars) return 'N/A'
  if (stars >= 1000) {
    return (stars / 1000).toFixed(1) + 'k'
  }
  return stars.toLocaleString()
}
</script>

<style scoped>
.project-card {
  border-radius: 8px;
  border: 1px solid #d0d7de;
  transition: all 0.2s ease;
}

.project-card:hover {
  border-color: #0969da;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.header-left {
  flex: 1;
  min-width: 0;
}

.header-right {
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
  font-size: 16px;
  text-decoration: none;
  word-break: break-all;
}

.project-name:hover {
  text-decoration: underline;
}

.project-name.no-url {
  color: #57606a;
}

.project-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-stats {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: #57606a;
}

.stars {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stars .el-icon {
  color: #f0c14b;
}

.description {
  color: #24292f;
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}

.recommend-reason {
  background-color: #fff8c5;
  border: 1px solid #f0c14b;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  color: #57606a;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.recommend-reason .el-icon {
  color: #f0c14b;
  flex-shrink: 0;
  margin-top: 2px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-info {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #57606a;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.up-name {
  font-weight: 500;
}

.video-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.card-footer {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.source-link,
.github-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #57606a;
  text-decoration: none;
  transition: color 0.2s;
}

.source-link:hover,
.github-link:hover {
  color: #0969da;
}

.github-link {
  margin-left: auto;
}

:deep(.el-card__header) {
  padding: 16px;
  border-bottom: 1px solid #d0d7de;
  background-color: #f6f8fa;
}

:deep(.el-card__body) {
  padding: 16px;
}

:deep(.el-card__footer) {
  padding: 12px 16px;
  border-top: 1px solid #d0d7de;
  background-color: #f6f8fa;
}
</style>