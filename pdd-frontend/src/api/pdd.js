import axios from 'axios'

export const API_BASE = import.meta.env.VITE_PDD_API_BASE || 'http://localhost:8082/api/pdd'

const api = axios.create({
  baseURL: API_BASE
})

const adminHeaders = (token) => ({
  headers: {
    'X-Admin-Token': token
  }
})

export async function adminLogin(email, password) {
  const { data } = await api.post('/admin/login', { email, password })
  return data
}

export async function fetchAdminUsers(token, search = '') {
  const { data } = await api.get('/admin/users', {
    ...adminHeaders(token),
    params: search ? { search } : {}
  })
  return data.users
}

export async function fetchAdminCategories(token) {
  const { data } = await api.get('/admin/categories', adminHeaders(token))
  return data.categories
}

export async function fetchAdminQuestions(token, params = {}) {
  const { data } = await api.get('/admin/questions', {
    ...adminHeaders(token),
    params
  })
  return data.questions
}

export async function createAdminQuestion(token, payload) {
  const { data } = await api.post('/admin/questions', payload, adminHeaders(token))
  return data
}

export async function updateAdminQuestion(token, questionId, payload) {
  const { data } = await api.put(`/admin/questions/${questionId}`, payload, adminHeaders(token))
  return data
}

export async function deleteAdminQuestion(token, questionId) {
  const { data } = await api.delete(`/admin/questions/${questionId}`, adminHeaders(token))
  return data
}

export async function fetchAdminTests(token) {
  const { data } = await api.get('/admin/tests', adminHeaders(token))
  return data.tests
}

export async function fetchAdminTestDetails(token, testId) {
  const { data } = await api.get(`/admin/tests/${testId}`, adminHeaders(token))
  return data.test
}

export async function createAdminTest(token, payload) {
  const { data } = await api.post('/admin/tests', payload, adminHeaders(token))
  return data
}

export async function updateAdminTest(token, testId, payload) {
  const { data } = await api.put(`/admin/tests/${testId}`, payload, adminHeaders(token))
  return data
}

export async function assignTestToUser(token, payload) {
  const { data } = await api.post('/admin/assign', payload, adminHeaders(token))
  return data
}

export async function fetchAdminAssignments(token, userId = '') {
  const { data } = await api.get('/admin/assignments', {
    ...adminHeaders(token),
    params: userId ? { user_id: userId } : {}
  })
  return data.assignments
}

export async function fetchAdminUserAnalytics(token, userId, limit = 50) {
  const { data } = await api.get(`/admin/users/${userId}/analytics`, {
    ...adminHeaders(token),
    params: { limit }
  })
  return data
}

export async function fetchMyTests(userId) {
  const { data } = await api.get(`/my/tests/${userId}`)
  return data.tests
}

export async function fetchAssignedQuestions(assignmentId, userId) {
  const { data } = await api.get(`/my/tests/${assignmentId}/questions`, {
    params: { user_id: userId }
  })
  return data
}

export async function submitAssignedTest(assignmentId, payload) {
  const { data } = await api.post(`/my/tests/${assignmentId}/submit`, payload)
  return data
}

export async function fetchMyAnalytics(userId, limit = 50) {
  const { data } = await api.get(`/my/analytics/${userId}`, {
    params: { limit }
  })
  return data
}
