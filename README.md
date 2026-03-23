# GitHub 项目推荐系统

一个自动化的 GitHub 项目推荐系统，从 B站视频（玄离199、IT咖啡馆等UP主）中提取 GitHub 项目推荐，提供友好的前端界面展示和增量更新功能。

## 功能特性

- **多数据源爬取** - 支持玄离199、IT咖啡馆等UP主的视频爬取
- **智能URL补全** - 通过GitHub API自动补全项目URL
- **增量更新** - 智能识别新视频，只爬取新增内容
- **本地存储** - SQLite 数据库，无需额外配置
- **静态爬虫** - 纯 API 爬取，无需浏览器，速度快
- **RESTful API** - 完整的后端接口，支持后台任务
- **前端界面** - Vue 3 + Element Plus 现代化界面

## 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| FastAPI | 高性能 Python Web 框架 |
| SQLAlchemy | ORM 框架（异步支持） |
| aiosqlite | SQLite 异步驱动 |
| httpx | HTTP 客户端（爬虫） |
| Pydantic | 数据验证 |

### 前端
| 技术 | 用途 |
|------|------|
| Vue 3 | 渐进式前端框架 |
| Vite | 下一代构建工具 |
| Element Plus | UI 组件库 |
| Axios | HTTP 客户端 |

### 数据库
| 技术 | 用途 |
|------|------|
| SQLite | 轻量级数据库，开箱即用 |

## 项目架构

```
github_demo_recommend/
├── backend/                          # 后端服务
│   └── app/
│       ├── main.py                   # FastAPI 入口
│       ├── config.py                 # 配置管理
│       ├── database.py               # SQLite 连接
│       ├── logger.py                 # 日志模块
│       │
│       ├── models/                   # 数据模型层
│       │   ├── project.py            # 通用项目模型
│       │   ├── xuanli199.py          # 玄离199项目模型
│       │   └── itcoffee.py           # IT咖啡馆项目模型
│       │
│       ├── routers/                  # API 路由层
│       │   ├── projects.py           # 通用项目接口
│       │   ├── xuanli199.py          # 玄离199接口
│       │   └── itcoffee.py           # IT咖啡馆接口
│       │
│       ├── xuanli199/                # 玄离199模块
│       │   ├── __init__.py
│       │   └── service.py            # 爬虫服务
│       │
│       ├── itcoffee/                 # IT咖啡馆模块
│       │   ├── __init__.py
│       │   └── service.py            # 爬虫服务
│       │
│       ├── crawler/                  # 爬虫核心模块
│       │   ├── base.py               # 爬虫基类
│       │   ├── bilibili.py           # B站爬虫
│       │   └── static_crawler.py     # 静态爬虫（wbi签名）
│       │
│       ├── services/                 # 通用服务层
│       │   ├── github_service.py     # GitHub API 服务
│       │   └── ai_analyzer.py        # AI 分析服务
│       │
│       └── schemas/                  # Pydantic 模式
│           └── project.py
│
├── frontend/                         # 前端服务
│   └── src/
│       ├── main.js                   # 入口文件
│       ├── App.vue                   # 根组件
│       ├── api/
│       │   └── projects.js           # API 调用
│       ├── views/
│       │   └── Home.vue              # 首页
│       └── components/
│           └── ProjectCard.vue       # 项目卡片组件
│
├── data/                             # 数据目录
│   └── github_recommend.db           # SQLite 数据库
│
├── task_plan.md                      # 任务规划
├── findings.md                       # 研究发现
├── progress.md                       # 进度日志
└── pyproject.toml                    # 项目配置
```

## 架构说明

### 后端架构

采用**分层架构**设计，职责清晰：

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (Routers)                  │
│   接收HTTP请求，参数验证，调用Service层                    │
├─────────────────────────────────────────────────────────┤
│                   Service Layer                         │
│   业务逻辑处理：爬取、解析、保存、URL补全                   │
├─────────────────────────────────────────────────────────┤
│                   Model Layer (SQLAlchemy)              │
│   数据模型定义，数据库操作                                │
├─────────────────────────────────────────────────────────┤
│                   Database (SQLite)                     │
│   数据持久化存储                                         │
└─────────────────────────────────────────────────────────┘
```

### 爬虫模块

每个UP主有独立的爬虫模块，结构一致：

| 模块 | 数据来源 | 项目位置 | URL来源 |
|------|----------|----------|---------|
| xuanli199 | B站评论区 | UP主评论 | 直接提取 |
| itcoffee | B站视频简介 | 项目名称列表 | GitHub API补全 |

### 数据流程

```
B站视频 → 提取项目信息 → 存储到SQLite → GitHub API补全URL → 前端展示
```

## API 接口

### 通用项目接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/projects` | 获取项目列表 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects/{id}` | 获取单个项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/crawl` | 触发爬虫更新 |
| GET | `/health` | 健康检查 |

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
| POST | `/api/itcoffee/url-fill` | 触发URL补全 |
| PATCH | `/api/itcoffee/projects/{id}/url` | 手动更新URL |

## 数据库结构

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
| github_url | TEXT | GitHub URL（API补全） |
| url_verified | BOOLEAN | URL是否已验证 |
| bilibili_url | TEXT | B站视频来源 URL |
| video_title | TEXT | 视频标题 |
| video_publish_time | DATETIME | 视频发布时间 |
| episode_number | INTEGER | 期数 |
| up_name | TEXT | UP主名字 |
| crawled_at | DATETIME | 爬取时间 |

## 爬虫实现

### 技术要点

1. **wbi 签名** - 绕过 B站 API 反爬机制
2. **静态爬取** - 使用 httpx 直接请求 API，无需浏览器
3. **增量更新** - 查询最大期数，只爬取新视频
4. **去重保存** - github_url 设置唯一约束
5. **URL补全** - 通过GitHub API搜索项目名称

### 爬取流程

**玄离199（评论区提取）：**
```
视频URL → 提取aid → 获取置顶评论 → 获取二级评论 → 匹配UP主评论 → 提取GitHub URL
```

**IT咖啡馆（简介提取）：**
```
视频URL → 提取合集列表 → 遍历视频简介 → 正则提取项目名称 → GitHub API补全URL
```

## 数据统计

| 数据源 | 项目数 | 期数 | URL验证率 |
|--------|--------|------|-----------|
| 玄离199 | 269 | 92 | 100% |
| IT咖啡馆 | 270 | 51 | 100% |
| **合计** | **539** | - | **100%** |

## 快速开始

### 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 启动服务

```bash
# 启动后端服务
uv run uvicorn backend.app.main:app --reload --port 8000

# 访问
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
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

## 配置说明

编辑 `.env` 文件进行配置：

```env
# 应用配置
APP_NAME=GitHub Project Recommendation System
DEBUG=false

# 爬虫配置
CRAWLER_HEADLESS=true
CRAWLER_TIMEOUT=30000
```

## 开发状态

- [x] 后端基础架构
- [x] SQLite 数据库
- [x] RESTful API
- [x] 静态爬虫模块
- [x] 增量更新功能
- [x] 玄离199模块完整实现
- [x] IT咖啡馆模块完整实现
- [x] GitHub URL自动补全
- [x] 前端界面框架
- [ ] 前端完善
- [ ] 测试覆盖

## License

MIT