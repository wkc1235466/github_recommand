# GitHub 项目推荐系统

一个基于 AI 的智能 GitHub 项目推荐系统，从 B站科技UP主（玄离199、IT咖啡馆）视频中提取项目推荐，提供现代化前端界面和智能分析功能。

## ✨ 核心特性

### 📊 数据采集
- **统一更新服务** - 一键检查两个UP主新视频，自动爬取并AI分析
- **智能增量更新** - 快速检测新视频，只爬取新增内容（秒级响应）
- **智能URL补全** - 通过 GitHub API 自动补全项目 URL
- **高成功率** - URL 验证率 100%

### 🤖 AI 能力
- **多模型支持** - 支持 Claude、GLM、Kimi 等多种 AI 模型
- **用户配置驱动** - 前端配置 AI 模型，后端使用用户配置进行分析
- **智能分析** - 自动分析项目并生成摘要和标签
- **模型管理** - 可视化模型管理，支持自定义模型添加
- **连接测试** - 实时测试模型连接状态
- **AI 智能搜索** - 两阶段语义搜索，智能识别分类并匹配项目

### 💻 现代化界面
- **Vue 3 + Element Plus** - 现代化响应式设计
- **快速切换** - 顶部模型快速切换下拉菜单
- **网格/列表视图** - 灵活的项目展示方式
- **实时更新** - 支持后台任务和实时进度反馈

### 🛠️ 技术优势
- **本地存储** - SQLite 数据库，无需额外配置
- **静态爬虫** - 纯 API 爬取，无需浏览器，速度快
- **性能优化** - 智能检测新视频，避免全量爬取
- **RESTful API** - 完整的后端接口，支持后台任务
- **跨标签页同步** - 模型配置跨标签页/窗口实时同步

---

## 📋 技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | Latest | 高性能 Python Web 框架 |
| SQLAlchemy | 2.x | ORM 框架（异步支持） |
| aiosqlite | Latest | SQLite 异步驱动 |
| httpx | Latest | 异步 HTTP 客户端 |
| Pydantic | 2.x | 数据验证和设置管理 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 渐进式前端框架（Composition API） |
| Vite | 5.x | 下一代构建工具 |
| Element Plus | Latest | UI 组件库 |
| Vue Router | 4.x | 路由管理 |
| Axios | Latest | HTTP 客户端 |

### 数据库
| 技术 | 用途 |
|------|------|
| SQLite | 轻量级数据库，开箱即用 |

---

## 🏗️ 项目架构

```
github_demo_recommend/
├── backend/                          # 后端服务
│   └── app/
│       ├── main.py                   # FastAPI 入口
│       ├── config.py                 # 配置管理（Pydantic Settings）
│       ├── database.py               # SQLite 连接池
│       ├── logger.py                 # 日志模块
│       │
│       ├── models/                   # 数据模型层（SQLAlchemy）
│       │   ├── project.py            # 通用项目模型
│       │   ├── xuanli199.py          # 玄离199项目模型
│       │   └── itcoffee.py           # IT咖啡馆项目模型
│       │
│       ├── routers/                  # API 路由层
│       │   ├── projects.py           # 通用项目接口 + AI 分析 + 统一更新
│       │   ├── xuanli199.py          # 玄离199接口
│       │   └── itcoffee.py           # IT咖啡馆接口
│       │
│       ├── services/                 # 业务服务层
│       │   ├── update_service.py     # 统一更新服务（核心）
│       │   ├── ai_provider_service.py  # AI 提供商服务
│       │   ├── ai_analyzer.py        # AI 分析服务
│       │   ├── ai_search_service.py  # AI 智能搜索服务
│       │   └── github_service.py     # GitHub API 服务
│       │
│       ├── xuanli199/                # 玄离199模块
│       │   └── service.py            # 爬虫服务（智能增量更新）
│       │
│       ├── itcoffee/                 # IT咖啡馆模块
│       │   └── service.py            # 爬虫服务（智能增量更新）
│       │
│       ├── crawler/                  # 爬虫核心
│       │   └── static_crawler.py     # 静态爬虫（B站API）
│       │
│       └── schemas/                  # Pydantic 模式
│           └── project.py            # 请求/响应模型
│
├── frontend/                         # 前端服务
│   └── src/
│       ├── main.js                   # 入口文件
│       ├── App.vue                   # 根组件（模型切换器 + 更新按钮）
│       │
│       ├── views/                    # 页面视图
│       │   ├── Home.vue              # 首页（项目列表）
│       │   └── ProjectDetail.vue     # 项目详情页
│       │
│       ├── components/               # 可复用组件
│       │   ├── ProjectCard.vue       # 项目卡片
│       │   └── SettingsDialog.vue    # 设置对话框（模型管理）
│       │
│       └── api/                      # API 调用层
│           ├── projects.js           # 项目相关 API
│           └── ai.js                 # AI 相关 API
│
├── data/                             # 数据目录
│   └── github_recommend.db           # SQLite 数据库
│
└── pyproject.toml                    # 项目配置
```

---

## 🔄 架构设计

### 后端分层架构

```
┌─────────────────────────────────────────────────────────┐
│                  API Layer (Routers)                    │
│   接收HTTP请求，参数验证，调用Service层                   │
│   - /api/projects (项目CRUD + AI分析 + 统一更新)         │
│   - /api/xuanli199                                      │
│   - /api/itcoffee                                       │
├─────────────────────────────────────────────────────────┤
│                  Service Layer                          │
│   业务逻辑处理                                            │
│   - UpdateService (统一更新，核心服务)                   │
│   - AIProviderService (AI 连接测试)                      │
│   - AIAnalyzer (项目分析)                                │
│   - GitHubService (URL 补全)                            │
│   - Xuanli199Service / ITcoffeeService (数据爬取)       │
├─────────────────────────────────────────────────────────┤
│               Model Layer (SQLAlchemy)                   │
│   数据模型定义，数据库操作                                  │
│   - Project, Xuanli199Project, ITCoffeeProject          │
├─────────────────────────────────────────────────────────┤
│                 Database (SQLite)                       │
│   数据持久化存储                                          │
│   - github_recommend.db                                 │
└─────────────────────────────────────────────────────────┘
```

### 统一更新流程

```
用户点击"更新数据"
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  POST /api/projects/crawl                               │
│  参数: { api_url, api_key, model }                      │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  UpdateService.crawl_and_save()                         │
│                                                         │
│  1. check_for_new_videos()                              │
│     ├─ Xuanli199Service.get_video_list_with_episodes()  │
│     │   (快速获取视频列表和期数，不进入视频详情)           │
│     └─ ITcoffeeService.get_video_list_with_episodes()   │
│                                                         │
│  2. 筛选新视频（期数 > 已爬取最大期数）                    │
│                                                         │
│  3. 只爬取新视频                                         │
│     ├─ 提取GitHub URL / 项目名称                         │
│     └─ 调用 GitHub API 补全 URL（IT咖啡馆）              │
│                                                         │
│  4. analyze_project_with_config()                       │
│     └─ 使用用户配置的 AI 模型分析每个项目                 │
│                                                         │
│  5. save_project_to_db()                                │
│     └─ 保存到统一的 projects 表                          │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   返回结果: { has_new, message, total_count, ... }
```

### 前端组件架构

```
App.vue (主应用)
├── ModelSelector (模型快速切换)
│   ├── 下拉菜单展示
│   ├── 当前模型高亮
│   └── 跨标签页同步
│
├── 更新按钮
│   ├── 读取 localStorage 中的 AI 配置
│   ├── 调用 /api/projects/crawl
│   └── 显示更新结果
│
├── Router View
│   ├── Home.vue (项目列表)
│   │   ├── 分类标签
│   │   ├── 搜索栏
│   │   ├── 视图切换（网格/列表）
│   │   └── ProjectCard 列表
│   │
│   └── ProjectDetail.vue (项目详情)
│       ├── 项目信息
│       ├── AI 分析结果
│       └── README 展示
│
└── SettingsDialog.vue (设置对话框)
    ├── Worker URL 配置
    ├── API 配置
    └── 模型管理
        ├── 模型列表
        ├── 添加模型
        ├── 删除模型
        └── 测试连接
```

### 数据流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  B站视频源   │────▶│  爬虫模块    │────▶│  SQLite     │
│  (玄离199)   │     │  (评论区)    │     │  存储        │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
┌──────────────┐     ┌──────────────┐         │
│  前端展示    │◀────│  API 层     │◀────────┘
│  (Vue 3)     │     │  (FastAPI)  │
└──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  AI 服务     │
                     │  (多模型)    │
                     └──────────────┘
```

---

## 🔌 API 接口

### 通用项目接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/projects` | 获取项目列表（分页、筛选、搜索） |
| POST | `/api/projects` | 手动创建项目 |
| GET | `/api/projects/{id}` | 获取单个项目详情 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/{id}/analyze` | 触发 AI 分析项目 |
| GET | `/api/projects/{id}/readme` | 获取项目 README |
| POST | `/api/projects/test-model` | 测试 AI 模型连接 |
| POST | `/api/projects/crawl` | **统一更新** - 检查新视频并爬取 |
| GET | `/api/projects/categories` | 获取分类列表 |
| GET | `/api/projects/tags/popular` | 获取热门标签 |
| POST | `/api/projects/ai-search` | **AI 智能搜索** - 语义搜索项目 |
| GET/POST/PUT/DELETE | `/api/projects/{id}/user-tags` | 用户标签管理 |

### 统一更新接口详情

**POST `/api/projects/crawl`**

请求体：
```json
{
  "api_url": "https://api.example.com",
  "api_key": "your-api-key",
  "model": "claude-sonnet-4-5-20251001"
}
```

响应：
```json
{
  "success": true,
  "message": "玄离199 新增 5 个项目，IT咖啡馆 新增 3 个项目，AI 分析成功 8 个",
  "has_new": true,
  "xuanli_count": 5,
  "itcoffee_count": 3,
  "total_count": 8,
  "ai_analyzed_count": 8,
  "ai_failed_count": 0,
  "new_episodes": {
    "xuanli199": [93, 94],
    "itcoffee": [108]
  }
}
```

### AI 智能搜索接口详情

**POST `/api/projects/ai-search`**

请求体：
```json
{
  "query": "我需要一个图片压缩工具",
  "use_cache": true
}
```

响应：
```json
{
  "query": "我需要一个图片压缩工具",
  "projects": [...],
  "detected_categories": ["媒体处理", "效率工具", "开发工具"],
  "search_summary": "根据搜索「我需要一个图片压缩工具」，AI 在「媒体处理、效率工具、开发工具」分类中为您找到以下最相关的项目：...",
  "from_cache": false,
  "total_matches": 3
}
```

**搜索特点**：
- 两阶段搜索：先识别相关分类，再匹配项目
- 智能缓存：7天缓存期，提升响应速度
- 语义匹配：理解用户意图，非简单关键词匹配

### 玄离199接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/xuanli199/stats` | 获取统计信息 |
| GET | `/api/xuanli199/projects` | 获取项目列表（支持按期数筛选） |
| GET | `/api/xuanli199/status` | 获取爬取状态 |
| POST | `/api/xuanli199/update` | 触发增量更新 |
| POST | `/api/xuanli199/crawl-full` | 触发完整爬取 |

### IT咖啡馆接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/itcoffee/stats` | 获取统计信息 |
| GET | `/api/itcoffee/projects` | 获取项目列表 |
| GET | `/api/itcoffee/status` | 获取爬取状态 |
| POST | `/api/itcoffee/update` | 触发增量更新 |
| POST | `/api/itcoffee/crawl-full` | 触发完整爬取 |
| POST | `/api/itcoffee/url-fill` | 批量补全 GitHub URL |
| POST | `/api/itcoffee/projects/{id}/fill-url` | 补全单个项目 URL |
| PATCH | `/api/itcoffee/projects/{id}/url` | 手动更新 URL |

---

## 💾 数据库结构

### projects 表（通用项目表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 项目名称 |
| github_url | TEXT | GitHub 项目 URL（唯一） |
| description | TEXT | 项目描述 |
| category | TEXT | 项目分类 |
| recommend_reason | TEXT | 推荐理由 |
| tags | TEXT | 标签（JSON 数组） |
| stars | INTEGER | GitHub 星标数 |
| needs_url | BOOLEAN | 是否需要补全 URL |
| ai_summary | TEXT | AI 生成的摘要 |
| ai_tags | TEXT | AI 生成的标签（JSON 数组） |
| ai_confidence | FLOAT | AI 分析置信度 |
| ai_analyzed_at | DATETIME | AI 分析时间 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### search_cache 表（AI 搜索缓存）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| query | TEXT | 搜索查询 |
| detected_categories | TEXT | 检测到的分类（JSON 数组） |
| matched_project_ids | TEXT | 匹配的项目 ID（JSON 数组） |
| search_summary | TEXT | 搜索结果摘要 |
| hit_count | INTEGER | 缓存命中次数 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### xuanli199 表（玄离199项目）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| github_url | TEXT | GitHub 项目 URL（唯一） |
| project_name | TEXT | 项目名称（owner/repo） |
| bilibili_url | TEXT | B站视频来源 URL |
| video_title | TEXT | 视频标题 |
| video_publish_time | DATETIME | 视频发布时间 |
| episode_number | INTEGER | 期数 |
| up_name | TEXT | UP主名字 |
| crawled_at | DATETIME | 爬取时间 |

### itcoffee 表（IT咖啡馆项目）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| project_name | TEXT | 项目名称 |
| description | TEXT | 项目描述 |
| github_url | TEXT | GitHub URL |
| url_verified | BOOLEAN | URL 是否已验证 |
| bilibili_url | TEXT | B站视频来源 URL |
| video_title | TEXT | 视频标题 |
| video_publish_time | DATETIME | 视频发布时间 |
| episode_number | INTEGER | 期数 |
| up_name | TEXT | UP主名字 |
| crawled_at | DATETIME | 爬取时间 |

---

## 🤖 AI 功能说明

### 支持的 AI 模型

**默认模型**：
- Anthropic: Claude Sonnet 4.5, Claude Opus 4.5
- BigModel: GLM-4-Flash, GLM-4.7, GLM-5, GLM-5-Turbo
- Moonshot: Kimi K2.5, Kimi K2 Turbo

**自定义模型**：
- 支持添加任何 Claude 兼容 API 的模型
- 可视化模型管理界面
- 实时连接测试

### AI 功能

**项目分析**：
- 自动生成项目摘要
- 智能分类标签
- 置信度评估

**连接测试**：
- 实时测试模型可用性
- 详细的错误提示
- 响应时间统计
- 支持多种错误格式解析

**模型管理**：
- 添加自定义模型
- 删除不需要的模型
- 跨标签页同步
- 删除状态持久化

---

## 📊 数据统计

| 数据源 | 项目数 | 期数 | URL验证率 |
|--------|--------|------|-----------|
| 玄离199 | 269 | 92 | 100% |
| IT咖啡馆 | 270 | 51 | 100% |
| **合计** | **539** | **143** | **100%** |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- uv（推荐）或 pip

### 后端设置

```bash
# 1. 克隆项目
git clone <repository-url>
cd github_demo_recommend

# 2. 安装依赖
uv sync

# 3. 启动后端服务
uv run uvicorn backend.app.main:app --reload --port 8000

# 4. 访问 API 文档
# http://localhost:8000/docs
```

### 前端设置

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev

# 4. 访问前端
# http://localhost:5173
```

### 配置说明

#### 后端配置（.env）

```env
# 应用配置
APP_NAME=GitHub Project Recommendation System
DEBUG=false

# 数据库（自动创建 data/github_recommend.db）

# 爬虫配置
CRAWLER_HEADLESS=true
CRAWLER_TIMEOUT=30000
CRAWLER_MAX_VIDEOS=10
```

#### 前端配置（浏览器设置）

打开设置对话框配置：
1. **Worker URL** - Cloudflare Worker 地址（用于 README 代理）
2. **API 基础 URL** - AI API 端点
3. **API 密钥** - API Key
4. **模型选择** - 选择要使用的 AI 模型

---

## 🔧 爬虫实现

### 技术要点

1. **wbi 签名** - 绕过 B站 API 反爬机制
2. **静态爬取** - 使用 httpx 直接请求 API，无需浏览器
3. **智能增量更新** - 快速获取视频列表和期数，只爬取新视频
4. **并行爬取** - 两个UP主同时检测，提升效率
5. **去重保存** - github_url 设置唯一约束
6. **URL 补全** - 通过 GitHub API 搜索项目名称

### 爬取流程

**玄离199（评论区提取）：**
```
1. get_video_list_with_episodes() - 快速获取视频列表和期数
2. 筛选新视频（期数 > 已爬取最大期数）
3. 视频URL → 提取aid → 获取置顶评论 → 获取二级评论
   → 匹配UP主评论 → 提取GitHub URL → 保存到数据库
```

**IT咖啡馆（简介提取）：**
```
1. get_video_list_with_episodes() - 快速获取视频列表和期数
2. 筛选新视频（期数 > 已爬取最大期数）
3. 视频URL → 提取简介 → 正则提取项目名称
   → GitHub API 补全 URL → 保存到数据库
```

### 性能优化

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 无新视频 | 爬取全部视频（~2分钟） | 只获取列表（<1秒） |
| 有1个新视频 | 爬取全部视频 | 只爬取1个新视频 |

---

## 📈 开发状态

### 已完成功能

- ✅ 后端基础架构
- ✅ SQLite 数据库
- ✅ RESTful API
- ✅ 静态爬虫模块
- ✅ **统一更新服务** - 一键更新两个UP主新视频
- ✅ **智能增量更新** - 秒级检测新视频
- ✅ 玄离199模块完整实现
- ✅ IT咖啡馆模块完整实现
- ✅ GitHub URL 自动补全
- ✅ AI 项目分析功能
- ✅ AI 提供商服务
- ✅ 模型连接测试
- ✅ 前端框架搭建
- ✅ 项目列表展示
- ✅ 项目详情页
- ✅ 设置对话框优化
- ✅ 模型可视化管理
- ✅ 主页面模型快速切换
- ✅ 用户标签管理
- ✅ AI 智能搜索功能
- ✅ 搜索结果缓存

### 开发中功能

- ⏳ 前端 UI 优化
- ⏳ 模型使用统计
- ⏳ 配置导入/导出

### 计划功能

- 📋 更多 AI 提供商支持
- 📋 云端同步功能
- 📋 测试覆盖

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发规范

1. 遵循 PEP 8 代码风格
2. 提交前运行测试
3. 更新相关文档
4. 保持提交信息清晰

---

## 📄 License

MIT License

---

## 👥 作者

- WKC - [GitHub](https://github.com/yourusername)

---

**最后更新**: 2026-03-26
