# Findings & Decisions

## Project Overview
GitHub 项目推荐系统 - 从 B站科技UP主视频中提取 GitHub 项目，使用 AI 分析并展示。

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite + aiosqlite | 轻量级，无需额外配置，异步支持 |
| FastAPI | 高性能，自动文档，异步支持 |
| Vue 3 + Element Plus | 现代化前端，组件丰富 |
| 静态爬虫（httpx） | 无需浏览器，速度快，资源占用低 |
| 分层架构 | models/routers/services 职责分离 |

---

## B站爬虫技术

### API 结构
- 视频页面包含 `aid`，用于获取评论
- 评论API: `https://api.bilibili.com/x/v2/reply/wbi/main` 需要 wbi 签名
- 二级评论API: `https://api.bilibili.com/x/v2/reply/reply` 不需要签名
- wbi签名密钥: `ea1db124af3c7062474693fa704f4ff8`

### 爬取流程
**玄离199（评论区提取）：**
```
视频URL → 提取 aid → 获取置顶评论 → 获取二级评论
→ 匹配UP主评论 → 正则提取GitHub URL → 保存到数据库
```

**IT咖啡馆（简介提取）：**
```
视频URL → 提取合集列表 → 遍历视频简介 → 正则提取项目名称
→ GitHub API 补全 URL → 保存到数据库
```

### 智能增量更新
```
1. get_video_list_with_episodes() - 快速获取视频列表和期数（只解析一个页面）
2. 筛选新视频（期数 > 已爬取最大期数）
3. 只爬取新视频，不爬取已爬取的视频
```

### wbi签名算法
```python
# 1. 按固定顺序拼接参数
params_str = f"mode={mode}&oid={oid}&pagination_str={encoded}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}"

# 2. 加上密钥
sign_str = params_str + "ea1db124af3c7062474693fa704f4ff8"

# 3. MD5加密
w_rid = hashlib.md5(sign_str.encode()).hexdigest()
```

### httpx 双重编码问题
- 使用 `params=` 参数时，httpx会自动URL编码
- 解决方案：直接拼接完整URL，不使用params参数

---

## AI 集成

### Claude 兼容 API
- 支持多种提供商：Anthropic、BigModel、Moonshot
- 统一使用 Claude Messages API 格式
- 端点格式：`{api_url}/v1/messages`

### 模型管理
- 默认模型列表：Claude、GLM、Kimi 系列
- 支持添加自定义模型
- 模型配置存储在 localStorage
- 跨标签页同步通过 storage 事件实现

### 错误处理
- 解析多种错误格式（Claude、BigModel、通用）
- BigModel 权限错误特殊处理
- 连接测试返回详细错误信息

---

## Database Schema

### projects 表（主表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 项目名称 |
| github_url | TEXT | GitHub URL（唯一） |
| description | TEXT | 描述 |
| category | TEXT | 分类 |
| tags | TEXT | AI标签（JSON） |
| user_tags | TEXT | 用户标签（JSON） |
| ai_summary | TEXT | AI摘要 |
| needs_url | BOOLEAN | 是否需要补全URL |

### project_sources 表
| 字段 | 类型 | 说明 |
|------|------|------|
| project_id | INTEGER | 关联项目 |
| bilibili_url | TEXT | B站视频URL |
| up_name | TEXT | UP主名称 |
| video_title | TEXT | 视频标题 |

---

## Performance Optimizations

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 无新视频检测 | 爬取全部视频（~2分钟） | 只获取列表（<1秒） |
| 有1个新视频 | 爬取全部视频 | 只爬取1个新视频 |
| 前端模型切换 | 需要打开设置 | 顶部下拉菜单直接切换 |

---

## Issues Resolved

| Issue | Resolution |
|-------|------------|
| httpx params双重编码 | 直接拼接URL字符串 |
| func变量未定义 | 添加正确的import语句 |
| async_session_maker初始化时机 | 使用延迟导入函数 |
| SQLAlchemy异步延迟加载 | 使用selectinload预加载 |
| 跨标签页配置不同步 | 监听storage事件 |

---

## Resources

- B站评论API: `https://api.bilibili.com/x/v2/reply/wbi/main`
- B站二级评论API: `https://api.bilibili.com/x/v2/reply/reply`
- GitHub搜索API: `https://api.github.com/search/repositories`
- Claude Messages API: `{api_url}/v1/messages`

---
*Last updated: 2026-03-24*