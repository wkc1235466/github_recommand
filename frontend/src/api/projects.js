import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // Increased for crawler
})

/**
 * Get paginated list of projects
 */
export const getProjects = async (params = {}) => {
  const { page = 1, pageSize = 20, category, tag, search, needsUrl } = params
  const response = await api.get('/projects', {
    params: { page, page_size: pageSize, category, tag, search, needs_url: needsUrl },
  })
  return response.data
}

/**
 * Get list of categories
 */
export const getCategories = async () => {
  const response = await api.get('/projects/categories')
  return response.data
}

/**
 * Get a single project by ID
 */
export const getProject = async (id) => {
  const response = await api.get(`/projects/${id}`)
  return response.data
}

/**
 * Get README content for a project
 */
export const getProjectReadme = async (id) => {
  const response = await api.get(`/projects/${id}/readme`)
  return response.data
}

/**
 * Create a new project
 */
export const createProject = async (project) => {
  const response = await api.post('/projects', project)
  return response.data
}

/**
 * Delete a project
 */
export const deleteProject = async (id) => {
  await api.delete(`/projects/${id}`)
}

/**
 * Trigger crawler to fetch new projects
 */
export const triggerCrawl = async (sources = null) => {
  const params = sources ? { sources: sources.join(',') } : {}
  const response = await api.post('/projects/crawl', null, { params })
  return response.data
}

/**
 * Trigger AI analysis for a project
 */
export const analyzeProject = async (id, force = false) => {
  const response = await api.post(`/projects/${id}/analyze`, { force })
  return response.data
}