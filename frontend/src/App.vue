<template>
  <div id="app">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <div class="logo">
            <el-icon :size="28"><Star /></el-icon>
            <span>GitHub 项目推荐</span>
          </div>
          <el-button
            type="primary"
            :loading="crawling"
            @click="triggerCrawl"
          >
            <el-icon><Refresh /></el-icon>
            {{ crawling ? '更新中...' : '更新数据' }}
          </el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { triggerCrawl as crawlApi } from './api/projects'

const crawling = ref(false)

const triggerCrawl = async () => {
  crawling.value = true
  try {
    const result = await crawlApi()
    ElMessage.success(result.message || '更新成功')
  } catch (error) {
    ElMessage.error('更新失败: ' + error.message)
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

.el-main {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}
</style>