# Task Plan: GitHub 项目推荐系统 - ITcoffee爬虫模块

## Goal
从B站「ITcoffee」合集中自动爬取GitHub项目名称，存储到SQLite数据库，通过GitHub API补全GitHub URL。

## Current Phase
Phase 5 - 完成 ✅

## Phases

### Phase 1: 研究与数据结构分析 ✅
- [x] 访问示例视频页面，分析数据结构
- [x] 找到合集视频列表获取方式（从视频页面HTML提取BV号）
- [x] 分析简介中的项目名称提取方式
- [x] 设计数据模型
- **Status:** complete

### Phase 2: 数据爬取功能开发 ✅
- [x] 实现合集视频列表爬取
- [x] 实现视频简介提取
- [x] 实现项目名称解析
- [x] 实现去重保存
- **Status:** complete

### Phase 3: 数据库与API开发 ✅
- [x] 创建 ITcoffee 数据表
- [x] 实现 SQLAlchemy 模型
- [x] 创建 FastAPI 路由
- [x] 实现统计和查询接口
- **Status:** complete

### Phase 4: 测试与完善 ✅
- [x] 爬取全部视频
- [x] 验证数据完整性
- [x] 清理测试代码
- **Status:** complete

### Phase 5: GitHub URL补全 ✅
- [x] 实现GitHub API搜索（按星标排序取第一个）
- [x] 实现批量URL补全
- [x] 实现单个项目URL补全
- **Status:** complete

## Key Questions
1. ✅ 如何获取合集所有视频列表？→ 从视频页面HTML中匹配BV号和标题
2. ✅ 简介中的项目名称格式是什么？→ `数字、项目名称：{name} – {desc}`
3. ✅ 如何解析多种格式的项目名称？→ 正则匹配 `\S+` 捕获项目名
4. ✅ 数据模型需要哪些字段？→ id, project_name, description, bilibili_url, video_title, episode_number, github_url(url_verified)
5. ✅ 如何补全GitHub URL？→ 使用GitHub API搜索，按星标排序取第一个结果

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用静态爬虫（httpx） | 与玄离199模块一致，速度快 |
| 只存储项目名称 | 简介中无完整URL，需后续补全 |
| 正则提取项目名称 | 格式固定：`项目名称：xxx – xxx` |
| 从视频页面HTML提取合集列表 | 复用xuanli199的方法，稳定可靠 |
| 使用GitHub API搜索补全URL | 按星标排序，取最热门的匹配结果 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 正则匹配项目名含空格 | 1 | 使用 `\S+` 匹配非空格字符 |
| GitHub搜索页面超时 | 1 | 改用GitHub API接口 |

## Notes
- 与玄离199模块不同，ITcoffee的项目在简介而非评论区
- 项目只有名称，需要后续GitHub API补全URL
- 参考玄离199的架构设计
- 爬取结果：270个项目，51期
- URL补全成功率：100%（270/270）

## Test Results
| Test | Result |
|------|--------|
| 视频列表提取 | ✅ 112个视频 |
| 项目名称解析 | ✅ 正确提取 |
| 完整爬取 | ✅ 270个项目 |
| API接口 | ✅ 正常工作 |
| GitHub URL补全 | ✅ 270个全部成功 (100%) |

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/itcoffee/stats | 获取统计信息 |
| GET | /api/itcoffee/projects | 获取项目列表 |
| GET | /api/itcoffee/status | 获取爬取状态 |
| POST | /api/itcoffee/update | 触发增量更新 |
| POST | /api/itcoffee/crawl-full | 触发完整爬取 |
| POST | /api/itcoffee/url-fill | 批量补全GitHub URL |
| POST | /api/itcoffee/projects/{id}/fill-url | 补全单个项目URL |
| PATCH | /api/itcoffee/projects/{id}/url | 手动更新URL |