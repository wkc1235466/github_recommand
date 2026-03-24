# Progress Log

## Session: 2026-03-24 统一更新功能与文档完善

### Phase 1: 统一更新服务开发
- **Status:** complete
- **Started:** 2026-03-24

**Actions taken:**
- 创建 `update_service.py` 统一更新服务
- 添加 `fetch_new_projects()` 方法到两个爬虫服务
- 添加 `get_video_list_with_episodes()` 快速获取视频列表
- 实现 POST `/api/projects/crawl` 路由
- 前端传递 AI 配置到后端

**Commit:** `672b86c feat: 实现统一更新功能，优化爬虫性能`

### Phase 2: 性能优化
- **Status:** complete

**Actions taken:**
- 优化 `fetch_new_projects()` 只爬取新视频
- 添加 `get_video_list_with_episodes()` 快速检测
- 无新视频时秒级响应

### Phase 3: 代码清理
- **Status:** complete

**Actions taken:**
- 删除测试文件（test_projects_api*.py 等）
- 删除临时文档（findings_settings.md 等）

### Phase 4: 文档更新
- **Status:** complete

**Actions taken:**
- 更新 README.md 反映统一更新功能
- 添加统一更新流程图
- 添加性能优化对比表
- 添加 API 接口文档

**Commit:** `0d93d8a docs: 更新 README 文档，反映统一更新功能`

---

## Session: 2026-03-24 标签系统与分类功能

### Phase 1: 后端实现
- **Status:** complete

**Actions taken:**
- 添加分类系统（9个分类）
- 添加 AI 标签生成
- 添加用户标签管理 API
- 添加热门标签 API

**Commit:** `d409b99 feat: 实现项目分类和标签系统`

### Phase 2: 前端实现
- **Status:** complete

**Actions taken:**
- 更新 ProjectCard.vue 显示标签
- 更新 Home.vue 添加分类/标签筛选
- 更新 ProjectDetail.vue 添加标签管理 UI

### Phase 3: 描述生成
- **Status:** complete

**Actions taken:**
- 创建描述生成脚本
- 为516个项目生成中文描述

**Commit:** `4cfaf6b feat: 添加项目描述生成脚本和数据库迁移脚本`

---

## Session: 2026-03-23 ITcoffee爬虫模块开发

### Phase 1: 研究与数据结构分析
- **Status:** complete

**Actions taken:**
- 分析示例视频页面结构
- 研究合集视频列表获取方式
- 分析简介中的项目名称格式

### Phase 2: 模块开发
- **Status:** complete

**Actions taken:**
- 创建 ITcoffeeProject 数据模型
- 实现 get_collection_videos() 方法
- 实现 _parse_project_names() 项目名称解析
- 实现 crawl_full() 完整爬取
- 实现 GitHub URL 自动补全

**Files created:**
- backend/app/models/itcoffee.py
- backend/app/itcoffee/service.py
- backend/app/routers/itcoffee.py

**Commit:** `09d9d12 feat: 添加IT咖啡馆爬虫模块和GitHub URL自动补全功能`

### Phase 3: 完整爬取测试
- **Status:** complete

**Test Results:**
| Test | Result |
|------|--------|
| 视频列表提取 | ✅ 111个视频 |
| 项目名称解析 | ✅ 正确提取 |
| 完整爬取 | ✅ 270个项目 |
| URL补全 | ✅ 100%验证率 |

---

## Session: 2026-03-22 玄离199爬虫模块完成

### Phase 1: 爬虫功能开发
- **Status:** complete

**Actions taken:**
- 实现静态爬虫 static_crawler.py（wbi签名、评论提取）
- 测试单个视频爬取成功
- 提取26个GitHub项目（前5个视频）

**Commit:** `27e571b feat: 实现静态爬虫从B站评论区提取GitHub项目`

### Phase 2: 数据库与服务开发
- **Status:** complete

**Actions taken:**
- 创建 Xuanli199Project 数据模型
- 实现 crawl_all_videos() 方法
- 实现 crawl_new_episodes() 增量更新
- 实现 save_projects() 去重保存

**Commit:** `b04a218 feat: 添加玄离199爬虫服务和API`

### Phase 3: API接口开发
- **Status:** complete

**Actions taken:**
- 创建 5 个 API 端点
- 实现 BackgroundTasks 后台爬取
- 修复 func 导入问题
- 修复 httpx 双重编码问题

**Commit:** `e6ed17c fix: 修复 xuanli199 API 路由中 func 导入问题`

### Phase 4: 完整爬取测试
- **Status:** complete

**Actions taken:**
- 启动完整爬取任务
- 爬取 92 个视频
- 提取 269 个 GitHub 项目
- 验证增量更新逻辑

---

## Session: 2026-03-22 前端开发

### Phase 1: 基础框架
- **Status:** complete

**Actions taken:**
- Vue 3 + Vite + Element Plus 集成
- 项目列表页面
- 项目详情页
- 设置对话框

**Commit:** `84bd9b6 feat: 添加项目详情页、设置对话框和视图切换功能`

### Phase 2: 模型管理
- **Status:** complete

**Actions taken:**
- 模型列表管理
- 自定义模型添加
- 模型连接测试
- 跨标签页同步

**Commit:** `0c07d27 feat: 完善设置对话框和模型管理功能`

---
*Last updated: 2026-03-24*