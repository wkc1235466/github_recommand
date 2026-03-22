# GitHub 项目推荐系统

一个自动化的 GitHub 项目推荐系统，从 B站 GitHub 热点 UP主处抓取推荐项目，提供友好的前端界面展示。

## 技术栈

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **Motor** - MongoDB 异步驱动
- **Playwright** - 浏览器自动化爬虫
- **Pydantic** - 数据验证

### 前端
- **Vue 3** - 渐进式前端框架
- **Vite** - 下一代构建工具
- **Element Plus** - UI 组件库
- **Axios** - HTTP 客户端

### 基础设施
- **MongoDB** - 文档数据库
- **Docker** - 容器化部署

## 项目结构

```
github_demo_recommend/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # MongoDB 连接
│   │   ├── models/            # 数据模型
│   │   ├── routers/           # API 路由
│   │   ├── schemas/           # Pydantic 模型
│   │   └── crawler/           # 爬虫模块
│   └── requirements.txt
├── frontend/                   # 前端服务
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── components/
│   │   ├── views/
│   │   └── api/
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── Dockerfile.backend
└── .env.example
```

## 快速开始

### 方式一: Docker 部署 (推荐)

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 启动服务
docker-compose up -d

# 3. 访问
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 方式二: 本地开发

#### 后端设置

```bash
# 1. 安装依赖
pip install -e .

# 2. 安装 Playwright 浏览器
playwright install chromium

# 3. 启动 MongoDB (需要本地安装或使用 Docker)
docker run -d -p 27017:27017 mongo:7.0

# 4. 复制环境变量配置
cp .env.example .env

# 5. 启动后端服务
uvicorn backend.app.main:app --reload --port 8000
```

#### 前端设置

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

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/projects` | 获取项目列表 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects/{id}` | 获取单个项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/crawl` | 触发爬虫更新 |
| GET | `/health` | 健康检查 |

完整 API 文档: http://localhost:8000/docs

## 配置说明

编辑 `.env` 文件进行配置:

```env
# MongoDB 配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=github_recommend

# 爬虫配置
CRAWLER_HEADLESS=true
CRAWLER_TIMEOUT=30000
```

## 配置爬虫目标

编辑 `backend/app/crawler/bilibili.py` 中的 `DEFAULT_UP_OWNERS` 列表，添加要爬取的 B站 UP主空间链接:

```python
DEFAULT_UP_OWNERS = [
    "https://space.bilibili.com/UP主ID",
    # 添加更多 UP主...
]
```

## 开发状态

- [x] 后端基础架构
- [x] MongoDB 数据模型
- [x] RESTful API
- [x] 爬虫模块框架
- [x] 前端界面
- [x] Docker 部署
- [ ] 完善爬虫逻辑
- [ ] 测试覆盖

## License

MIT