# Findings & Decisions

## Requirements
- 从B站「科技补全」系列视频（玄离199）提取GitHub项目链接
- 数据库存储：github_url, project_name, bilibili_url, video_title, video_publish_time, episode_number, up_name
- 支持增量更新：只爬取新发布的视频
- 清理测试代码，保持代码整洁

## Research Findings

### B站API结构
- 视频页面包含 `aid`，可用于获取评论
- 评论API: `https://api.bilibili.com/x/v2/reply/wbi/main` 需要 wbi 签名
- 二级评论API: `https://api.bilibili.com/x/v2/reply/reply` 不需要签名
- wbi签名密钥: `ea1db124af3c7062474693fa704f4ff8`

### 爬取流程
```
视频URL → 提取 aid → 获取置顶评论 → 获取二级评论 → 匹配UP主评论 → 正则提取GitHub URL
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

### 合集视频提取
- 合集页面是动态加载，API需要复杂签名
- 简单方案：从视频页面HTML中匹配包含「科技补全」标题的BV号

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| httpx + 正则表达式 | 轻量级静态爬取，速度快 |
| SQLite | 项目已集成，无需额外配置 |
| 分层架构 | models/routers/service 职责分离 |
| 后台任务爬取 | BackgroundTasks避免阻塞API |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| httpx params双重编码 | 直接拼接URL字符串 |
| func变量未定义 | 添加正确的import语句 |
| async_session_maker初始化时机 | 使用延迟导入函数 |

## Resources
- B站评论API: `https://api.bilibili.com/x/v2/reply/wbi/main`
- B站二级评论API: `https://api.bilibili.com/x/v2/reply/reply`
- wbi签名密钥: `ea1db124af3c7062474693fa704f4ff8`
- 合集视频列表: 通过视频页面HTML提取

## Visual/Browser Findings
- 置顶评论在 `data.top` 中，包含 upper/admin/vote 类型
- UP主评论在二级评论中，需遍历查找 uname 包含"玄离"的评论
- 视频发布时间在 HTML 中为 `pubdate` 时间戳

---
*Update this file after every 2 view/browser/search operations*