/**
 * AI 分析服务
 * 支持多种兼容 OpenAI 格式的 API
 */

/**
 * 调用 AI API 进行分析
 */
export async function callAI(prompt, systemPrompt = null) {
  const apiUrl = localStorage.getItem('apiUrl') || 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
  const apiKey = localStorage.getItem('apiKey') || localStorage.getItem('glmApiKey')
  const model = localStorage.getItem('model') || 'glm-4-flash'

  if (!apiKey) {
    throw new Error('请先在设置中配置 API Key')
  }

  const messages = []
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt })
  }
  messages.push({ role: 'user', content: prompt })

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: model,
        messages: messages,
        temperature: 0.3,
      }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.error?.message || `API 请求失败: ${response.status}`)
    }

    const data = await response.json()
    return data.choices[0]?.message?.content || ''
  } catch (error) {
    console.error('AI API 调用失败:', error)
    throw error
  }
}

/**
 * 分析 GitHub 项目，生成标签和分类
 */
export async function analyzeProject(name, description, githubUrl = null) {
  const categories = [
    'AI/机器学习',
    'Web开发',
    '工具/效率',
    '安全',
    '数据库',
    '移动开发',
    '游戏开发',
    '其他',
  ]

  const systemPrompt = `你是一个GitHub项目分析专家。你的任务是分析GitHub项目并生成简洁的描述和分类。

你需要返回JSON格式的结果，包含以下字段：
- summary: 项目简介（50-100字）
- category: 项目分类，必须是以下之一: ${categories.join(', ')}
- suggested_tags: 建议的标签（最多3个）

只返回JSON，不要有其他内容。`

  let prompt = `项目名称: ${name}`
  if (description) {
    prompt += `\n描述: ${description}`
  }
  if (githubUrl) {
    prompt += `\nGitHub地址: ${githubUrl}`
  }
  prompt += '\n\n请分析这个项目并返回JSON格式的结果。'

  const content = await callAI(prompt, systemPrompt)

  // 解析 JSON
  try {
    // 尝试提取 JSON
    let jsonStr = content
    if (content.includes('```json')) {
      jsonStr = content.split('```json')[1].split('```')[0]
    } else if (content.includes('```')) {
      jsonStr = content.split('```')[1].split('```')[0]
    }

    const result = JSON.parse(jsonStr.trim())
    return {
      summary: result.summary || '',
      category: result.category || '其他',
      suggested_tags: result.suggested_tags || [],
    }
  } catch (e) {
    console.error('解析 AI 响应失败:', e)
    return {
      summary: content.slice(0, 200),
      category: '其他',
      suggested_tags: [],
    }
  }
}

/**
 * 获取配置状态
 */
export function getConfig() {
  return {
    apiUrl: localStorage.getItem('apiUrl') || 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    apiKey: localStorage.getItem('apiKey') || localStorage.getItem('glmApiKey') || '',
    model: localStorage.getItem('model') || 'glm-4-flash',
    workerUrl: localStorage.getItem('workerUrl') || '',
    githubToken: localStorage.getItem('githubToken') || '',
    isConfigured: !!(localStorage.getItem('apiKey') || localStorage.getItem('glmApiKey')),
  }
}