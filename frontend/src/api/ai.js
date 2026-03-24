/**
 * AI 分析服务 - 只支持 Claude 兼容 API
 */

/**
 * 获取当前配置
 */
function getConfig() {
  return {
    apiUrl: localStorage.getItem('apiUrl') || 'https://api.anthropic.com/v1/messages',
    apiKey: localStorage.getItem('apiKey') || localStorage.getItem('glmApiKey') || '',
    apiType: localStorage.getItem('apiType') || 'claude',
    model: localStorage.getItem('model') || 'claude-sonnet-4-5-20251001',
  }
}

/**
 * 调用 AI API
 */
export async function callAI(prompt, systemPrompt = null) {
  const config = getConfig()

  if (!config.apiKey) {
    throw new Error('请先在设置中配置 API Key')
  }

  return callClaudeAPI(config.apiUrl, config.apiKey, config.model, prompt, systemPrompt)
}

/**
 * 调用 Claude API
 */
async function callClaudeAPI(apiUrl, apiKey, model, prompt, systemPrompt) {
  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: model,
      max_tokens: 2048,
      system: systemPrompt || undefined,
      messages: [
        { role: 'user', content: prompt }
      ],
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.error?.message || `API 请求失败: ${response.status}`)
  }

  const data = await response.json()
  return data.content[0]?.text || ''
}

/**
 * 分析 GitHub 项目
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
 * 测试模型连通性（通过后端代理）
 */
export async function testModelConnection(modelId, apiUrl, apiKey, apiType = 'claude') {
  if (!apiKey) {
    return { success: false, message: '请先配置 API Key' }
  }

  try {
    const response = await fetch('/api/projects/test-model', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        api_url: apiUrl,
        api_key: apiKey,
        model: modelId,
        api_type: apiType,
      }),
    })

    const data = await response.json()
    return data
  } catch (error) {
    console.error('测试连接失败:', error)
    return { success: false, message: error.message || '网络请求失败' }
  }
}
