"""批量更新项目描述 - 最终版"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "github_recommend.db"

# 完整的项目描述映射
DESCRIPTIONS = {
    # 1-70 (已更新的保留)
    "promptfoo": "promptfoo是一个AI安全测试框架，用于评估大语言模型的提示词安全性。支持自动化测试流程、多模型对比和漏洞检测，帮助开发者构建更安全的AI应用。",
    "agency-agents": "一个完整的AI代理事务所框架，包含多种专业化代理。从前端开发到社区运营，每个代理都有独特的技能和交付能力，适合构建复杂的AI工作流。",
    "awesome-openclaw-skills": "OpenClaw技能宝库，收录了5400多个经过筛选和分类的技能。来自官方OpenClaw技能注册表，涵盖开发、运维、数据分析等多个领域。",
    "claude-hud": "Claude Code插件，实时显示上下文使用量、活跃工具、运行中的代理和待办事项进度。帮助开发者更好地管理和监控Claude的工作状态。",
    "OpenViking": "火山引擎开源的上下文数据库，专为AI代理设计。通过文件系统范式统一管理代理所需的内存、资源和技能，支持层次化上下文交付。",
    "CoPaw": "1Panel现代化Linux服务器运维面板，支持一键部署OpenClaw。提供可视化的服务器管理界面，简化Docker、网站和数据库管理。",
    "RuView": "WiFi人体感知系统，利用普通WiFi信号实现实时人体姿态估计、生命体征监测和存在检测。无需摄像头，保护隐私的同时实现智能感知。",
    "worldmonitor": "实时全球情报监控仪表盘，集成AI驱动的新闻聚合、地缘政治监测和基础设施追踪功能。提供统一的态势感知界面。",
    "GitNexus": "浏览器端代码知识图谱生成器，支持GitHub仓库和ZIP文件导入。内置Graph RAG代理进行代码探索，帮助理解复杂代码库。",
    "deer-flow": "字节跳动开源的多智能体框架DeerFlow，支持研究、编程和创作任务。配备沙箱、记忆、工具和子代理系统，可处理分钟到小时级别的复杂任务。",
    "zeroclaw": "轻量级自主AI助手基础设施，使用Rust编写。支持跨平台部署，可用于构建个人AI助理，强调快速、小巧和完全自主。",
    "voicebox": "开源语音合成工作室，提供语音克隆和语音合成功能。支持本地部署，可用于创建自定义语音模型和语音内容生成。",
    "Qwen3.5": "MS-Swift模型微调框架，支持600+大语言模型和300+多模态模型的训练。兼容Qwen、DeepSeek、GLM等主流模型，获AAAI 2025收录。",
    "pentagi": "自主AI渗透测试系统，能够自动执行复杂的Web应用和API安全测试任务。识别漏洞、生成报告，提高安全测试效率。",
    "carbon": "精美的源代码图片生成工具Carbon，支持多种编程语言和主题配色。可用于创建和分享美观的代码截图，适合技术文章和社交媒体。",
    "GLM-5": "Ollama本地模型运行工具，支持Kimi、GLM-5、DeepSeek、Qwen等主流大语言模型的本地部署。提供简洁的命令行界面，方便模型管理。",
    "cc-switch": "跨平台桌面助手工具，统一管理Claude Code、Codex、OpenCode、OpenClaw和Gemini CLI。简化AI编程助手的切换和配置管理。",
    "shannon": "自主白盒AI渗透测试工具，分析源代码识别攻击向量。执行真实漏洞利用来验证安全问题，帮助在代码上线前发现并修复漏洞。",
    "monty": "用Rust编写的轻量级安全Python解释器，专为AI代码执行场景设计。提供沙箱隔离，防止恶意代码执行，确保AI系统的安全性。",
    "dexter": "深度金融研究AI代理Dexter，自主分析金融市场数据。生成投资研究报告，支持多数据源整合和量化分析。",
    "nanobot": "港大数据智能实验室开发的超轻量级OpenClaw实现。专为资源受限环境设计，核心功能完整且易于部署，适合边缘计算场景。",
    "beads": "编码代理的记忆增强模块，为AI编程助手提供持久化记忆能力。支持上下文保持和代码模式学习，提高代码生成质量。",
    "ChatLab": "本地化聊天记录分析工具，通过AI代理回顾和分析社交记忆。支持微信、QQ等多种聊天平台数据导入，生成社交行为洞察报告。",
    "Vision-Agents": "微软OmniParser屏幕解析工具，基于纯视觉的GUI代理。支持屏幕内容理解和自动化操作，让AI能够像人类一样使用电脑界面。",
    "keyStats": "键盘鼠标统计工具，支持macOS和Windows。记录键鼠使用数据并提供分析报告，帮助了解工作习惯和提高效率。",
    "openclaw": "OpenClaw是一个开源的个人AI助手框架，支持任意操作系统和平台。提供工具调用、记忆管理和多代理协作能力，让AI真正成为你的助手。",
    "remotion": "RustDesk远程桌面应用，开源的TeamViewer替代方案。支持自建服务器和中继，提供端到端加密，确保远程访问的安全性。",
    "PageIndex": "基于推理的文档索引系统PageIndex，支持无向量检索的RAG方案。通过文档结构理解提供精准的问答能力，降低幻觉风险。",
    "langextract": "Google开源的语言特征提取库，从非结构化文本中提取结构化信息。支持多种语言，适用于信息抽取和知识图谱构建。",
    "Githubweekly": "GitHub一周热点汇总工具，自动抓取和整理GitHub热门项目。帮助开发者发现优质开源项目和开发者动态。",
    "Eigent": "开源AI协作工作平台Eigent，支持多代理协同完成任务。提供任务管理、结果整合和团队协作功能。",
    "data-engineering-zoomcamp": "数据工程实战课程Data Engineering Zoomcamp，涵盖数据管道、数据仓库、批处理和流处理的完整学习路径。由DataTalks.club出品。",
    "chrome-devtools-mcp": "Chrome开发者工具MCP服务器，允许AI代理与浏览器开发者工具交互。支持自动化测试、页面分析和性能监控。",
    "ui-ux-pro-max-skill": "专业UI/UX设计技能库，为AI代理提供设计系统参考。包含组件库、设计模式和最佳实践，提升AI辅助设计能力。",
    "VoidNovelEngine": "无代码Galgame引擎VoidNovelEngine，支持可视化剧本编辑。提供角色立绘管理、分支剧情设计和多结局支持，让创作视觉小说更简单。",
    "opencode": "开源AI编程代理OpenCode，提供代码生成、重构和调试功能。支持多种编程语言，可作为IDE插件使用。",
    "Superpowers": "AI开发技能框架Superpowers，为大语言模型提供额外的工具和能力扩展。支持自定义技能开发和工作流编排。",
    "TARS": "字节跳动UI-TARS桌面应用，让AI能够操作电脑完成复杂任务。支持GUI自动化，可通过自然语言控制电脑操作。",
    "MiroThinker": "开源深度研究代理MiroThinker，支持文献检索、信息整合和研究报告生成。适用于学术研究和市场分析场景。",
    "icloud_photos_downloader": "iCloud照片下载工具，批量下载iCloud中的照片和视频到本地存储。支持增量同步和元数据保留，方便备份管理。",
    "wechat-article-exporter": "微信公众号文章导出工具，支持批量导出文章。可将文章转换为Markdown或PDF格式，方便离线阅读和归档。",
    "vibe-kanban": "极简看板管理工具Vibe Kanban，支持任务拖拽、标签分类和团队协作。提供直观的项目管理界面，适合敏捷开发团队。",
    "skills": "OpenClaw技能集合，包含多种实用工具和功能模块。扩展AI代理的能力范围，支持自定义技能开发。",
    "A2UI": "AI到用户界面转换工具A2UI，自动将AI能力映射为可交互的UI组件。加速AI应用的前端开发流程。",
    "Mole": "数据挖掘工具Mole，从大规模数据集中发现隐藏的模式和关联规则。支持多种数据格式和可视化分析。",
    "fresh": "前端热更新工具Fresh，自动检测代码变更并实时刷新页面。提高前端开发效率，支持多种框架。",
    "rendercv": "简历渲染工具RenderCV，将YAML或JSON格式的简历数据转换为精美的PDF文档。支持多种模板和自定义样式。",
    "WeKnora": "知识图谱构建平台WeKnora，支持从非结构化文本中抽取实体和关系。提供图谱可视化和查询接口。",
    "VibeVoice": "语音AI工具集VibeVoice，支持语音识别、语音合成和语音情感分析。可用于构建语音交互应用。",
    "claude-mem": "Claude记忆增强插件，为Claude对话提供持久化记忆能力。支持上下文保持，让Claude记住之前的对话内容。",
    "zerobyte": "轻量级字节码虚拟机ZeroByte，用于沙箱执行不受信任的代码。提供安全隔离，防止恶意代码影响宿主系统。",
    "jellyfin-desktop": "Jellyfin媒体服务器桌面客户端，支持本地媒体播放和远程访问。开源免费的媒体中心解决方案。",
    "cosmic": "System76开发的跨平台桌面环境Cosmic，基于Rust编写。提供现代化的Linux桌面体验，注重性能和用户体验。",
    "Open-AutoGLM": "智谱AI开源的GLM模型工具链Open-AutoGLM，支持模型的训练、微调和部署。降低大模型应用门槛。",
    "next-ai-draw-io": "AI绘图工具，基于Next.js构建。支持文生图和图像编辑，提供在线绘图界面。",
    "agents.md": "AI代理开发文档集合Agents.md，收录代理架构、工具使用和最佳实践指南。帮助开发者快速入门AI代理开发。",
    "fizzy": "轻量级测试框架Fizzy，支持快照测试和行为驱动开发。适用于前端项目的单元测试和集成测试。",
    "kaiju": "大规模数据处理框架Kaiju，支持分布式计算和数据管道构建。可用于处理TB级别的数据集。",
    "Embodied-AI-Guide": "具身AI指南Embodied-AI-Guide，涵盖机器人感知、控制和学习的综合教程。帮助开发者入门具身智能领域。",
    "Flux2": "Black Forest Labs的图像生成模型Flux，支持高质量文生图和图像编辑。提供开源模型权重，支持本地部署。",
    "HunyuanVideo": "腾讯混元视频生成模型HunyuanVideo，支持文本生成视频和视频编辑任务。可用于内容创作和视频制作。",
    "Cognee": "认知AI框架Cognee，支持知识图谱构建和多跳推理。增强AI的认知能力，提高复杂问题的回答质量。",
    "LaunchNext": "Next.js项目启动器LaunchNext，提供预配置的项目模板和开发工具链。加速Next.js应用开发。",
    "NoteDiscovery": "笔记发现工具NoteDiscovery，支持跨平台笔记搜索和知识管理。帮助整理分散在多平台的笔记内容。",
    "nginx-proxy-manager": "Nginx代理管理器NPM，提供Web界面管理反向代理和SSL证书。简化Nginx配置，适合家庭服务器和小型团队。",
    "Strix": "高性能搜索引擎Strix，支持全文检索和语义搜索。适用于大规模文档检索场景，提供REST API接口。",
    # 71-150 新增项目
    "MagicMirror²": "MagicMirror²是一个开源的模块化智能镜子平台。支持显示天气、日历、新闻等信息，可自定义模块扩展功能。",
    "DeepCode": "开源的AI编程助手，提供代码生成、重构和调试功能。支持多种编程语言，可作为VSCode插件使用。",
    "TrendRadar": "多平台热点聚合与AI分析工具，自动抓取微博、知乎、抖音等平台的热门话题。提供趋势分析和舆情监控功能。",
    "iptv-org/iptv": "全球公开IPTV频道集合，收录来自世界各地的免费电视直播源。支持m3u格式，可直接用于播放器。",
    "open-source-games": "开源游戏合集，收录各类开源游戏项目。涵盖RPG、策略、射击等多种游戏类型，适合游戏开发学习。",
    "BitNet": "微软开源的原生1-bit大语言模型，通过二值化权重大幅降低推理成本。支持CPU运行，适合边缘设备部署。",
    "SkyReels-V2": "快手开源的无限长度视频生成模型。支持文本生成视频，可生成任意时长的视频内容。",
    "HowToCook": "程序员在家做饭方法指南，以代码风格编写的菜谱集合。涵盖各种家常菜做法，帮助程序员学会做饭。",
    "code-server": "在浏览器中运行的VSCode，支持远程开发。可部署在任何服务器上，随时随地编写代码。",
    "yt-dlp": "强大的命令行视频下载工具，支持YouTube、B站等数千个网站。可下载视频、音频和字幕，支持格式转换。",
    "openai-agents-python": "OpenAI官方的Agent开发工具包，简化AI代理开发流程。支持工具调用、多代理协作和状态管理。",
    "open-sora": "开源的视频生成模型Open-Sora，对标OpenAI Sora。支持文本生成视频，提供完整的训练和推理代码。",
    "awesome-mcp-servers": "MCP服务器合集，收录各种实用的MCP服务器。支持Claude、GPT等AI模型的工具扩展。",
    "xpipe": "跨平台Shell连接中心，统一管理SSH、Docker等远程连接。支持密码加密存储，提高运维效率。",
    "ai-hedge-fund": "多智能体量化交易系统，使用AI分析市场数据。支持策略回测、风险管理和自动交易。",
    "OpenManus": "Manus AI代理的开源实现，支持复杂任务自动化。提供网页浏览、文件操作和API调用能力。",
    "composio": "AI Agent的工具集平台，提供100+集成工具。支持Gmail、Slack、Notion等常用应用的自动化操作。",
    "clay": "高性能2D UI布局库，使用C语言编写。支持Flexbox布局，适用于游戏和嵌入式GUI开发。",
    "SpacetimeDB": "高性能实时数据库，支持游戏和协作应用。将数据库逻辑移至服务端，简化后端开发。",
    "CnC_Red_Alert": "红警系列游戏开源资源，包含游戏数据和工具。适合经典游戏爱好者和游戏开发学习。",
    "open-infra-index": "DeepSeek开源周项目索引，收录DeepSeek开源的各类基础设施项目。涵盖推理引擎、训练框架等。",
    "wan2.1": "阿里巴巴万象2.1视频生成模型，性能超越Sora。支持文生视频和图生视频，生成高质量视频内容。",
    "pandas-ai": "AI数据分析库，支持用自然语言查询数据。基于Pandas构建，简化数据分析和可视化流程。",
    "docmost": "开源的Notion替代品Docmost，支持协作文档和知识库。提供富文本编辑、实时协作和权限管理。",
    "cherry-studio": "跨平台AI助手客户端Cherry Studio，支持多模型切换。集成代码编辑、文档处理等功能。",
    "awesome-deepseek-integration": "DeepSeek实用集成指南，收录各类DeepSeek模型的集成案例。涵盖API调用、本地部署和工具集成。",
    "Step-Video-T2V": "阶跃星辰开源的多模态视频生成模型。支持文本生成视频，提供高质量视频生成能力。",
    "markitdown": "Markdown换行和格式化工具，支持多种Markdown风格。帮助规范化Markdown文档格式。",
    "source-sdk-2013": "Valve开源的游戏SDK，用于开发Source引擎游戏。包含Half-Life 2等游戏的源代码。",
    "ktransformers": "大模型推理加速框架，支持多种优化技术。可大幅提升大模型在消费级GPU上的推理速度。",
    "unsloth": "大模型微调工具Unsloth，支持LoRA等高效微调方法。显著降低显存需求，适合个人开发者。",
    "data-formulator": "微软开源的AI数据可视化工具，支持自然语言创建图表。自动推荐最佳可视化方案。",
    "hoppscotch": "开源的API调试工具Hoppscotch，Postman的轻量级替代品。支持REST、GraphQL、WebSocket等协议。",
    "lucide": "开源图标库Lucide，提供千余个精美的SVG图标。支持React、Vue等前端框架，易于集成使用。",
    "oumi": "端到端的基础模型平台Oumi，支持训练、微调和评估。简化大模型开发全流程。",
    "Janus-Pro": "DeepSeek开源的多模态模型Janus-Pro，支持图像理解和生成。统一视觉编码，降低模型复杂度。",
    "Qwen2.5-VL": "阿里Qwen2.5视觉语言模型，支持图像理解和文档解析。在多个视觉任务上达到SOTA水平。",
    "browser-use": "AI控制浏览器的Python库，支持网页自动化操作。可用于数据抓取、表单填写和测试自动化。",
}

def update_all_descriptions():
    """更新所有项目描述"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated = 0
    for name, desc in DESCRIPTIONS.items():
        try:
            cursor.execute(
                "UPDATE projects SET description = ? WHERE name = ?",
                (desc, name)
            )
            if cursor.rowcount > 0:
                updated += 1
        except Exception as e:
            print(f"Error updating {name}: {e}")

    conn.commit()
    conn.close()

    print(f"Updated {updated} projects")
    return updated

if __name__ == "__main__":
    update_all_descriptions()