# Task Plan: GitHub 项目推荐系统 - 玄离199爬虫模块

## Goal
实现从B站「科技补全」系列视频中自动爬取GitHub项目链接，支持增量更新，存储到SQLite数据库。

## Current Phase
Phase 5 - 完成（系统已正常运行）

## Phases

### Phase 1: 数据爬取功能开发 ✅
- [x] 实现静态爬虫（httpx + wbi签名）
- [x] 从视频页面提取 aid
- [x] 获取置顶评论和二级评论
- [x] 从UP主评论中提取GitHub链接
- **Status:** complete

### Phase 2: 数据库设计与实现 ✅
- [x] 设计 xuanli199 表结构
- [x] 实现 SQLAlchemy 模型
- [x] 创建索引优化查询
- **Status:** complete

### Phase 3: 服务层开发 ✅
- [x] 实现完整爬取功能 (crawl_full)
- [x] 实现增量更新逻辑 (crawl_new_episodes)
- [x] 实现去重保存
- **Status:** complete

### Phase 4: API接口开发 ✅
- [x] 创建 FastAPI 路由
- [x] 实现统计接口 GET /stats
- [x] 实现项目列表 GET /projects
- [x] 实现增量更新 POST /update
- [x] 实现完整爬取 POST /crawl-full
- **Status:** complete

### Phase 5: 测试与清理 ✅
- [x] 爬取全部92个视频
- [x] 提取269个GitHub项目
- [x] 清理测试文件
- **Status:** complete

## Key Questions
1. ✅ 如何绕过B站wbi签名？→ 按固定顺序拼接参数后MD5加密
2. ✅ 如何提取合集所有视频？→ 从视频页面HTML中匹配BV号和标题
3. ✅ 如何实现增量更新？→ 查询最大期数，只爬取新视频
4. ✅ 如何避免重复项目？→ github_url 设置 unique 约束

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用静态爬虫而非Playwright | 速度快，无需浏览器，API稳定 |
| SQLite替代MongoDB | 轻量级，适合个人项目，已集成到项目中 |
| 分层架构（models/routers/service） | 关注点分离，便于维护 |
| wbi签名使用固定密钥 | 简单有效，避免频繁获取密钥 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| API返回权限不足 | 1 | 检查签名顺序，修正参数拼接 |
| httpx双重URL编码 | 2 | 直接拼接URL而非使用params |
| func未导入 | 1 | 在routers中添加 from sqlalchemy import func |
| async_session_maker为None | 1 | 延迟导入，使用 get_session_maker() 函数 |

## Notes
- 更新期状态：pending → in_progress → complete
- 重大决策前重新阅读此计划
- 记录所有错误以避免重复