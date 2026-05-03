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

function isNotFound(error) {
  return error?.response?.status === 404
}

function normalizeQuestion(question) {
  const normalizedAnswers = (question.answers || []).map((answer) => ({
    ...answer,
    explanation: answer.explanation || ''
  }))

  return {
    ...question,
    language: (question.language || 'ru').toString().toLowerCase(),
    image_url: question.image_url || '',
    answers_count:
      question.answers_count !== undefined
        ? Number(question.answers_count || 0)
        : normalizedAnswers.length,
    answers: normalizedAnswers
  }
}

function normalizeAssignment(item) {
  const assignmentId = item.assignment_id || item.id || null
  const mode = item.mode || 'exam'
  const attempts = Number(item.attempts || 0)
  const maxAttempts =
    item.max_attempts === null || item.max_attempts === undefined
      ? mode === 'exam'
        ? 1
        : null
      : Number(item.max_attempts)

  return {
    ...item,
    assignment_id: assignmentId,
    language: (item.language || item.test_language || 'ru').toString().toLowerCase(),
    mode,
    attempts,
    max_attempts: maxAttempts,
    pass_score: Number(item.pass_score || 70),
    question_limit: Number(item.question_limit || 20),
    randomize_questions: Boolean(item.randomize_questions),
    randomize_answers: Boolean(item.randomize_answers)
  }
}

function shuffleArray(values) {
  const copy = [...values]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function normalizeAnalyticsPayload(payload = {}, fallbackUserId = '') {
  const attemptsRaw = payload?.attempts || []
  const attempts = attemptsRaw.map((attempt, index) => {
    const total = Number(attempt.total_questions || attempt.total || 0)
    const correct = Number(attempt.correct_answers || attempt.correct || 0)
    const wrong =
      attempt.wrong_answers !== undefined
        ? Number(attempt.wrong_answers || 0)
        : Math.max(0, total - correct)

    return {
      ...attempt,
      attempt_id: Number(attempt.attempt_id || attempt.id || index + 1),
      user_id: attempt.user_id || fallbackUserId || '',
      total_questions: total,
      correct_answers: correct,
      wrong_answers: wrong,
      score: Number(attempt.score || 0),
      pass_score: Number(attempt.pass_score || 70),
      mode: attempt.mode || 'exam',
      attempt_number: Number(attempt.attempt_number || 1),
      category_stats: attempt.category_stats || [],
      wrong_questions: attempt.wrong_questions || [],
      recommendations: attempt.recommendations || [],
      has_review_details:
        attempt.has_review_details !== undefined
          ? Boolean(attempt.has_review_details)
          : Array.isArray(attempt.wrong_questions) || Array.isArray(attempt.category_stats)
    }
  })

  const summary = payload?.summary || {}
  return {
    summary: {
      total_attempts: Number(summary.total_attempts || attempts.length),
      average_score: Number(summary.average_score || 0),
      best_score: Number(summary.best_score || 0),
      mode_counts: summary.mode_counts || {
        exam: attempts.filter((item) => item.mode === 'exam').length,
        training: attempts.filter((item) => item.mode === 'training').length
      },
      categories: summary.categories || []
    },
    attempts
  }
}

function buildLegacyAnalytics(userId, results = [], stats = []) {
  const normalizedResults = (results || []).map((item) => {
    const total = Number(item.total_questions || 0)
    const correct = Number(item.correct_answers || 0)
    const score = Number(item.score || 0)
    return {
      attempt_id: Number(item.id),
      assignment_id: null,
      test_id: null,
      test_title: item.category || 'Тест',
      mode: 'exam',
      attempt_number: 1,
      total_questions: total,
      correct_answers: correct,
      wrong_answers: Math.max(0, total - correct),
      score,
      passed: score >= 70,
      pass_score: 70,
      duration_seconds: null,
      created_at: item.test_date || '',
      category_stats: [],
      wrong_questions: [],
      recommendations: [],
      has_review_details: false,
      user_id: userId
    }
  })

  const sortedAttempts = normalizedResults.sort((a, b) => {
    const aTime = new Date(a.created_at || 0).getTime()
    const bTime = new Date(b.created_at || 0).getTime()
    return bTime - aTime
  })

  const scores = sortedAttempts.map((item) => item.score)
  const totalAttempts = sortedAttempts.length
  const averageScore = totalAttempts ? Number((scores.reduce((s, x) => s + x, 0) / totalAttempts).toFixed(1)) : 0
  const bestScore = scores.length ? Math.max(...scores) : 0

  const categories = (stats || []).map((item) => {
    const avg = Number(item.avg_score || 0)
    const testsCount = Number(item.tests_count || 0)
    const wrongEstimate = Math.max(0, Math.round((100 - avg) * testsCount / 100))
    return {
      category: item.category,
      total: testsCount,
      correct: testsCount - wrongEstimate,
      wrong: wrongEstimate,
      error_rate: Number((100 - avg).toFixed(1))
    }
  })

  return normalizeAnalyticsPayload(
    {
      summary: {
        total_attempts: totalAttempts,
        average_score: averageScore,
        best_score: bestScore,
        mode_counts: {
          exam: totalAttempts,
          training: 0
        },
        categories
      },
      attempts: sortedAttempts
    },
    userId
  )
}

async function fetchLegacyPublicQuestionBank() {
  const { data } = await api.get('/questions/all', {
    params: { limit: 1000 }
  })
  return (data.questions || []).map(normalizeQuestion)
}

export async function adminLogin(email, password) {
  const { data } = await api.post('/admin/login', { email, password })
  return data
}

export async function fetchAdminUsers(token, search = '') {
  const { data } = await api.get('/admin/users', {
    ...adminHeaders(token),
    params: search ? { search } : {}
  })
  return data.users || []
}

export async function fetchAdminCategories(token) {
  try {
    const { data } = await api.get('/admin/categories', adminHeaders(token))
    return data.categories || []
  } catch (error) {
    if (!isNotFound(error)) {
      throw error
    }

    const { data } = await api.get('/categories')
    return data.categories || []
  }
}

export async function fetchAdminQuestions(token, params = {}) {
  try {
    const { data } = await api.get('/admin/questions', {
      ...adminHeaders(token),
      params
    })
    return (data.questions || []).map(normalizeQuestion)
  } catch (error) {
    if (!isNotFound(error)) {
      throw error
    }

    let questions = []
    try {
      questions = await fetchLegacyPublicQuestionBank()
    } catch {
      const { data } = await api.get('/admin/question-bank', adminHeaders(token))
      questions = (data.questions || []).map((question) => ({
        ...question,
        image_url: question.image_url || '',
        answers: []
      }))
    }

    const rawSearch = (params.search || '').toString().trim().toLowerCase()
    const category = params.category || 'all'
    const language = (params.language || 'all').toString().toLowerCase()

    if (category !== 'all') {
      questions = questions.filter((item) => item.category === category)
    }

    if (language !== 'all') {
      questions = questions.filter((item) => (item.language || 'ru').toLowerCase() === language)
    }

    if (rawSearch) {
      questions = questions.filter(
        (item) =>
          (item.question_text || '').toLowerCase().includes(rawSearch) ||
          String(item.id).includes(rawSearch)
      )
    }

    return questions
  }
}

export async function createAdminQuestion(token, payload) {
  try {
    const { data } = await api.post('/admin/questions', payload, adminHeaders(token))
    return data
  } catch (error) {
    if (isNotFound(error)) {
      throw new Error('Этот backend не поддерживает создание вопросов через админ-панель')
    }
    throw error
  }
}

export async function updateAdminQuestion(token, questionId, payload) {
  try {
    const { data } = await api.put(`/admin/questions/${questionId}`, payload, adminHeaders(token))
    return data
  } catch (error) {
    if (isNotFound(error)) {
      throw new Error('Этот backend не поддерживает редактирование вопросов через админ-панель')
    }
    throw error
  }
}

export async function deleteAdminQuestion(token, questionId) {
  try {
    const { data } = await api.delete(`/admin/questions/${questionId}`, adminHeaders(token))
    return data
  } catch (error) {
    if (isNotFound(error)) {
      throw new Error('Этот backend не поддерживает удаление вопросов через админ-панель')
    }
    throw error
  }
}

export async function fetchAdminTests(token) {
  const { data } = await api.get('/admin/tests', adminHeaders(token))
  return (data.tests || []).map((item) => ({
    ...item,
    language: (item.language || 'ru').toString().toLowerCase(),
    pass_score: Number(item.pass_score || 70),
    randomize_questions: Boolean(item.randomize_questions),
    randomize_answers: Boolean(item.randomize_answers)
  }))
}

export async function fetchAdminTestDetails(token, testId) {
  try {
    const { data } = await api.get(`/admin/tests/${testId}`, adminHeaders(token))
    return data.test
  } catch (error) {
    if (!isNotFound(error)) {
      throw error
    }

    const tests = await fetchAdminTests(token)
    const fallback = tests.find((item) => Number(item.id) === Number(testId))
    if (!fallback) {
      throw error
    }

    return {
      ...fallback,
      language: (fallback.language || 'ru').toString().toLowerCase(),
      question_ids: [],
      questions: [],
      randomize_questions: Boolean(fallback.randomize_questions),
      randomize_answers: Boolean(fallback.randomize_answers),
      pass_score: Number(fallback.pass_score || 70)
    }
  }
}

export async function createAdminTest(token, payload) {
  const { data } = await api.post('/admin/tests', payload, adminHeaders(token))
  return data
}

export async function updateAdminTest(token, testId, payload) {
  try {
    const { data } = await api.put(`/admin/tests/${testId}`, payload, adminHeaders(token))
    return data
  } catch (error) {
    if (isNotFound(error)) {
      throw new Error('Этот backend не поддерживает изменение существующих тестов')
    }
    throw error
  }
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

  const assignments = (data.assignments || []).map(normalizeAssignment)
  return userId ? assignments.filter((item) => item.user_id === userId) : assignments
}

export async function fetchAdminUserAnalytics(token, userId, limit = 50) {
  try {
    const { data } = await api.get(`/admin/users/${userId}/analytics`, {
      ...adminHeaders(token),
      params: { limit }
    })
    return normalizeAnalyticsPayload(data, userId)
  } catch (error) {
    if (!isNotFound(error)) {
      throw error
    }

    const [resultsRes, statsRes] = await Promise.allSettled([
      api.get(`/results/${userId}`),
      api.get(`/stats/${userId}`)
    ])

    const results =
      resultsRes.status === 'fulfilled' ? resultsRes.value.data?.results || [] : []
    const stats = statsRes.status === 'fulfilled' ? statsRes.value.data?.stats || [] : []

    return buildLegacyAnalytics(userId, results, stats)
  }
}

export async function fetchAdminAttemptDetails(token, attemptId) {
  try {
    const { data } = await api.get(`/admin/attempts/${attemptId}`, adminHeaders(token))
    return data.attempt
  } catch (error) {
    if (isNotFound(error)) {
      throw new Error('Разбор попытки недоступен на текущем backend')
    }
    throw error
  }
}

export async function fetchMyTests(userId) {
  const { data } = await api.get(`/my/tests/${userId}`)
  return (data.tests || []).map(normalizeAssignment)
}

export async function fetchPublicCategories(language = 'all') {
  const parsedLanguage = (language || 'all').toString().toLowerCase()
  const { data } = await api.get('/categories', {
    params: { language: parsedLanguage }
  })
  return data.categories || []
}

export async function fetchGeneralTrainingQuestions({ limit = 20, categories = [], language = 'all' } = {}) {
  const parsedLimit = Math.max(1, Math.min(Number(limit) || 20, 100))
  const parsedLanguage = (language || 'all').toString().toLowerCase()
  const categoryList = Array.isArray(categories)
    ? categories
        .map((item) => (item || '').toString().trim())
        .filter(Boolean)
        .filter((item, index, arr) => arr.indexOf(item) === index)
    : []

  try {
    const { data } = await api.get('/training/questions', {
      params: {
        limit: parsedLimit,
        language: parsedLanguage,
        categories: categoryList
      }
    })

    return {
      ...data,
      questions: (data.questions || []).map(normalizeQuestion)
    }
  } catch (error) {
    if (!isNotFound(error)) {
      throw error
    }

    if (categoryList.length === 0 || categoryList.includes('all')) {
      const { data } = await api.get('/questions/all', {
        params: { limit: parsedLimit, language: parsedLanguage }
      })
      return {
        questions: (data.questions || []).map(normalizeQuestion)
      }
    }

    const perCategoryLimit = Math.max(1, Math.ceil(parsedLimit / categoryList.length))
    const batches = await Promise.all(
      categoryList.map(async (category) => {
        const { data } = await api.get(`/questions/${encodeURIComponent(category)}`, {
          params: { limit: perCategoryLimit, language: parsedLanguage }
        })
        return data.questions || []
      })
    )

    const flattened = shuffleArray(batches.flat().map(normalizeQuestion)).slice(0, parsedLimit)
    return { questions: flattened }
  }
}

export async function fetchAssignedQuestions(assignmentId, userId) {
  const { data } = await api.get(`/my/tests/${assignmentId}/questions`, {
    params: { user_id: userId }
  })

  return {
    ...data,
    mode: data.mode || 'exam',
    pass_score: Number(data.pass_score || 70),
    questions: (data.questions || []).map(normalizeQuestion)
  }
}

export async function submitAssignedTest(assignmentId, payload) {
  const { data } = await api.post(`/my/tests/${assignmentId}/submit`, payload)

  const total = Number(data.total || 0)
  const correct = Number(data.correct || 0)
  const wrong = data.wrong !== undefined ? Number(data.wrong) : Math.max(0, total - correct)

  return {
    ...data,
    total,
    correct,
    wrong,
    pass_score: Number(data.pass_score || 70),
    mode: data.mode || 'exam',
    attempt_number: Number(data.attempt_number || 1),
    category_stats: data.category_stats || [],
    wrong_questions: data.wrong_questions || [],
    recommendations: data.recommendations || []
  }
}

export async function fetchMyAnalytics(userId, limit = 50) {
  try {
    const { data } = await api.get(`/my/analytics/${userId}`, {
      params: { limit }
    })
    return normalizeAnalyticsPayload(data, userId)
  } catch (error) {
    if (!isNotFound(error)) {
      throw error
    }

    const [resultsRes, statsRes] = await Promise.allSettled([
      api.get(`/results/${userId}`),
      api.get(`/stats/${userId}`)
    ])

    const results =
      resultsRes.status === 'fulfilled' ? resultsRes.value.data?.results || [] : []
    const stats = statsRes.status === 'fulfilled' ? statsRes.value.data?.stats || [] : []

    return buildLegacyAnalytics(userId, results, stats)
  }
}
