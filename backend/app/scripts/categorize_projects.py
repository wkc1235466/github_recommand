"""自动分类项目和生成标签"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "github_recommend.db"

# 分类规则：关键词 -> 分类
CATEGORY_RULES = {
    "AI/机器学习": [
        "AI", "模型", "Agent", "代理", "LLM", "大语言模型", "机器学习",
        "语音", "图像生成", "视频生成", "ChatGPT", "GPT", "Claude",
        "OpenAI", "DeepSeek", "Qwen", "GLM", "智谱", "Ollama",
        "RAG", "NLP", "自然语言", "TensorFlow", "PyTorch",
        "AI助手", "智能体", "多模态", "推理", "微调"
    ],
    "开发工具": [
        "开发", "编程", "代码", "框架", "编辑器", "IDE", "API",
        "前端", "后端", "Vue", "React", "Python", "JavaScript",
        "Git", "GitHub", "调试", "编译", "构建", "包管理",
        "SDK", "库", "CLI", "命令行", "VSCode", "IntelliJ"
    ],
    "系统运维": [
        "服务器", "运维", "Docker", "Kubernetes", "K8s", "监控",
        "部署", "数据库", "MySQL", "PostgreSQL", "Redis",
        "Nginx", "Linux", "容器", "云", "DevOps",
        "负载均衡", "日志", "备份", "CI/CD"
    ],
    "安全工具": [
        "安全", "渗透", "漏洞", "攻击", "防护", "加密",
        "密码", "认证", "权限", "扫描", "入侵", "CVE"
    ],
    "媒体处理": [
        "视频", "音频", "图片", "图像", "媒体", "播放器",
        "截图", "录屏", "字幕", "转码", "压缩", "格式转换",
        "剪辑", "渲染", "FFmpeg"
    ],
    "效率工具": [
        "笔记", "文档", "阅读", "翻译", "下载", "搜索",
        "书签", "剪贴板", "待办", "日历", "提醒",
        "知识库", "思维导图", "Markdown"
    ],
    "桌面应用": [
        "桌面", "窗口", "托盘", "远程", "桌面应用",
        "系统工具", "壁纸", "主题", "快捷键", "启动器",
        "文件管理", "任务栏", "macOS", "Windows"
    ],
    "游戏娱乐": [
        "游戏", "Game", "娱乐", "模拟器", "作弊",
        "存档", "Mod", "Minecraft", "Steam"
    ],
}

# 标签生成规则
TAG_RULES = {
    # AI相关标签
    "AI安全": ["安全测试", "提示词", "promptfoo"],
    "AI代理": ["Agent", "代理", "自动化", "多智能体"],
    "大语言模型": ["LLM", "GPT", "Claude", "大模型", "ChatGPT"],
    "语音合成": ["语音", "TTS", "语音克隆", "声音"],
    "图像生成": ["图像生成", "文生图", "Stable Diffusion", "Flux"],
    "视频生成": ["视频生成", "文生视频", "Sora"],
    "模型训练": ["训练", "微调", "fine-tuning", "LoRA"],

    # 开发工具标签
    "前端框架": ["Vue", "React", "Angular", "前端"],
    "后端框架": ["Django", "Flask", "FastAPI", "Spring"],
    "代码编辑器": ["编辑器", "IDE", "VSCode", "Vim"],
    "API工具": ["API", "REST", "GraphQL", "接口"],

    # 系统运维标签
    "容器化": ["Docker", "容器", "Kubernetes"],
    "数据库": ["数据库", "MySQL", "PostgreSQL", "Redis"],
    "监控系统": ["监控", "告警", "仪表盘"],

    # 媒体处理标签
    "视频处理": ["视频", "剪辑", "转码"],
    "音频处理": ["音频", "音乐", "音效"],
    "图像处理": ["图片", "图像", "照片"],

    # 效率工具标签
    "笔记工具": ["笔记", "文档", "Notion"],
    "翻译工具": ["翻译", "多语言"],
    "下载工具": ["下载", "离线"],

    # 安全工具标签
    "渗透测试": ["渗透", "漏洞利用", "安全测试"],
    "安全扫描": ["扫描", "漏洞检测"],
}


def classify_project(name: str, description: str) -> str:
    """根据项目名称和描述分类"""
    text = f"{name} {description}".lower()

    scores = {}
    for category, keywords in CATEGORY_RULES.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)

    return "其他"


def generate_tags(name: str, description: str, max_tags: int = 3) -> list:
    """根据项目名称和描述生成标签"""
    text = f"{name} {description}".lower()

    matched_tags = []
    for tag, keywords in TAG_RULES.items():
        for kw in keywords:
            if kw.lower() in text:
                matched_tags.append(tag)
                break

    # 去重并限制数量
    unique_tags = list(dict.fromkeys(matched_tags))
    return unique_tags[:max_tags]


def categorize_all_projects():
    """分类所有项目并生成标签"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 添加 user_tags 列（如果不存在）
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN user_tags TEXT")
    except:
        pass  # 列已存在

    # 获取所有项目
    cursor.execute("SELECT id, name, description FROM projects")
    projects = cursor.fetchall()

    updated = 0
    for project_id, name, description in projects:
        # 分类
        category = classify_project(name or "", description or "")

        # 生成标签
        tags = generate_tags(name or "", description or "")
        tags_json = json.dumps(tags, ensure_ascii=False) if tags else None

        # 更新数据库
        cursor.execute(
            "UPDATE projects SET category = ?, tags = ? WHERE id = ?",
            (category, tags_json, project_id)
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"Updated {updated} projects")

    # 统计结果
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) FROM projects GROUP BY category ORDER BY COUNT(*) DESC")
    results = cursor.fetchall()
    conn.close()

    print("\n分类统计:")
    for cat, cnt in results:
        print(f"  {cat}: {cnt}")

    return updated


if __name__ == "__main__":
    categorize_all_projects()