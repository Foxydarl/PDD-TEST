<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  assignTestToUser,
  createAdminQuestion,
  createAdminTest,
  deleteAdminQuestion,
  fetchAdminAssignments,
  fetchAdminAttemptDetails,
  fetchAdminCategories,
  fetchAdminQuestions,
  fetchAdminTestDetails,
  fetchAdminTests,
  fetchAdminUserAnalytics,
  fetchAdminUsers,
  updateAdminQuestion,
  updateAdminTest
} from '../api/pdd'

const props = defineProps({
  session: {
    type: Object,
    required: true
  },
  language: {
    type: String,
    required: true
  },
  t: {
    type: Function,
    required: true
  }
})

const token = computed(() => props.session.token)
const languageTick = computed(() => props.language)

const activeTab = ref('assignments')
const loading = ref(false)
const saving = ref(false)
const flashType = ref('')
const flashText = ref('')

const users = ref([])
const tests = ref([])
const assignments = ref([])
const categories = ref([])
const questions = ref([])

const userSearch = ref('')
let searchTimer = null

const selectedUserAnalytics = ref(null)
const selectedUserAnalyticsData = ref(null)
const analyticsLoading = ref(false)
const attemptDetailsLoading = ref(false)
const selectedAttempt = ref(null)

const assignConfigByUser = ref({})
const assigningUserId = ref('')

const CONTENT_LANGUAGES = ['ru', 'en', 'kk']

const testFilterQuery = ref('')
const testFilterCategory = ref('all')
const testFilterLanguage = ref('all')

const testEditor = ref({
  id: null,
  title: '',
  description: '',
  language: 'ru',
  question_limit: 20,
  randomize_questions: true,
  randomize_answers: false,
  pass_score: 70,
  question_ids: []
})

const questionFilterQuery = ref('')
const questionFilterCategory = ref('all')
const questionFilterLanguage = ref('all')

const questionEditor = ref({
  id: null,
  question_text: '',
  category: '',
  language: 'ru',
  image_url: '',
  answers: [
    { answer_text: '', is_correct: true, explanation: '' },
    { answer_text: '', is_correct: false, explanation: '' }
  ]
})

function showFlash(type, text) {
  flashType.value = type
  flashText.value = text
  setTimeout(() => {
    if (flashText.value === text) {
      flashType.value = ''
      flashText.value = ''
    }
  }, 3800)
}

function getErrorText(error) {
  return error?.response?.data?.detail || error?.message || props.t('common.unknownError')
}

function modeLabel(mode) {
  return mode === 'training' ? props.t('mode.training') : props.t('mode.exam')
}

function contentLanguageLabel(language) {
  const normalized = (language || 'ru').toString().toLowerCase()
  return props.t(`contentLanguage.${normalized}`)
}

function resetTestEditor() {
  testEditor.value = {
    id: null,
    title: '',
    description: '',
    language: 'ru',
    question_limit: 20,
    randomize_questions: true,
    randomize_answers: false,
    pass_score: 70,
    question_ids: []
  }
}

function resetQuestionEditor() {
  questionEditor.value = {
    id: null,
    question_text: '',
    category: '',
    language: 'ru',
    image_url: '',
    answers: [
      { answer_text: '', is_correct: true, explanation: '' },
      { answer_text: '', is_correct: false, explanation: '' }
    ]
  }
}

function ensureAssignConfig(userId) {
  if (!assignConfigByUser.value[userId]) {
    assignConfigByUser.value[userId] = {
      testId: '',
      mode: 'exam'
    }
  }
}

const availableCategories = computed(() => {
  const set = new Set(categories.value)
  questions.value.forEach((question) => set.add(question.category))
  return Array.from(set).filter(Boolean)
})

const contentLanguageOptions = computed(() =>
  CONTENT_LANGUAGES.map((value) => ({
    value,
    label: contentLanguageLabel(value)
  }))
)

const filteredQuestionsForTest = computed(() => {
  const q = testFilterQuery.value.trim().toLowerCase()
  return questions.value.filter((question) => {
    const matchesTestLanguage = (question.language || 'ru') === testEditor.value.language
    const languageOk =
      testFilterLanguage.value === 'all' || (question.language || 'ru') === testFilterLanguage.value
    const categoryOk =
      testFilterCategory.value === 'all' || question.category === testFilterCategory.value
    const queryOk =
      q.length === 0 ||
      question.question_text.toLowerCase().includes(q) ||
      String(question.id).includes(q)
    return matchesTestLanguage && languageOk && categoryOk && queryOk
  })
})

const filteredQuestionsForBank = computed(() => {
  const q = questionFilterQuery.value.trim().toLowerCase()
  return questions.value.filter((question) => {
    const languageOk =
      questionFilterLanguage.value === 'all' || (question.language || 'ru') === questionFilterLanguage.value
    const categoryOk =
      questionFilterCategory.value === 'all' || question.category === questionFilterCategory.value
    const queryOk =
      q.length === 0 ||
      question.question_text.toLowerCase().includes(q) ||
      String(question.id).includes(q)
    return languageOk && categoryOk && queryOk
  })
})

const selectedQuestionCount = computed(() => testEditor.value.question_ids.length)

function isQuestionSelected(questionId) {
  return testEditor.value.question_ids.includes(questionId)
}

function toggleQuestionForTest(questionId) {
  if (isQuestionSelected(questionId)) {
    testEditor.value.question_ids = testEditor.value.question_ids.filter((id) => id !== questionId)
  } else {
    testEditor.value.question_ids = [...testEditor.value.question_ids, questionId]
  }
}

function addAnswerOption() {
  questionEditor.value.answers.push({
    answer_text: '',
    is_correct: false,
    explanation: ''
  })
}

function removeAnswerOption(index) {
  if (questionEditor.value.answers.length <= 2) return
  questionEditor.value.answers.splice(index, 1)
  if (!questionEditor.value.answers.some((answer) => answer.is_correct)) {
    questionEditor.value.answers[0].is_correct = true
  }
}

function setCorrectAnswer(index) {
  questionEditor.value.answers = questionEditor.value.answers.map((answer, answerIndex) => ({
    ...answer,
    is_correct: answerIndex === index
  }))
}

async function loadUsers() {
  users.value = await fetchAdminUsers(token.value, userSearch.value)
  users.value.forEach((user) => ensureAssignConfig(user.id))
}

async function loadAllData() {
  loading.value = true
  try {
    const [testsResult, usersResult, assignmentsResult, questionsResult, categoriesResult] =
      await Promise.allSettled([
        fetchAdminTests(token.value),
        fetchAdminUsers(token.value, userSearch.value),
        fetchAdminAssignments(token.value),
        fetchAdminQuestions(token.value, { include_answers: true }),
        fetchAdminCategories(token.value)
      ])

    const errors = []

    if (testsResult.status === 'fulfilled') {
      tests.value = testsResult.value
    } else {
      errors.push(`${props.t('admin.tab.tests')}: ${getErrorText(testsResult.reason)}`)
    }

    if (usersResult.status === 'fulfilled') {
      users.value = usersResult.value
    } else {
      errors.push(`${props.t('admin.assign.user')}: ${getErrorText(usersResult.reason)}`)
    }

    if (assignmentsResult.status === 'fulfilled') {
      assignments.value = assignmentsResult.value
    } else {
      errors.push(`${props.t('admin.tab.assignments')}: ${getErrorText(assignmentsResult.reason)}`)
    }

    if (questionsResult.status === 'fulfilled') {
      questions.value = questionsResult.value
    } else {
      errors.push(`${props.t('admin.tab.questions')}: ${getErrorText(questionsResult.reason)}`)
    }

    if (categoriesResult.status === 'fulfilled') {
      categories.value = categoriesResult.value
    } else {
      errors.push(`${props.t('user.training.general.categories')}: ${getErrorText(categoriesResult.reason)}`)
    }

    users.value.forEach((user) => ensureAssignConfig(user.id))

    if (errors.length) {
      showFlash('error', props.t('admin.flash.backendHint', { errors: errors.join(' | ') }))
    }
  } finally {
    loading.value = false
  }
}

async function openTestForEdit(testId) {
  try {
    const test = await fetchAdminTestDetails(token.value, testId)
    testEditor.value = {
      id: test.id,
      title: test.title,
      description: test.description || '',
      language: test.language || 'ru',
      question_limit: test.question_limit,
      randomize_questions: test.randomize_questions,
      randomize_answers: test.randomize_answers,
      pass_score: test.pass_score,
      question_ids: test.question_ids || []
    }
    activeTab.value = 'tests'
    showFlash('success', props.t('admin.flash.testsLoaded', { title: test.title }))
  } catch (error) {
    showFlash('error', getErrorText(error))
  }
}

async function saveTest() {
  if (!testEditor.value.title.trim()) {
    showFlash('error', props.t('admin.flash.testNameRequired'))
    return
  }

  if (testEditor.value.question_ids.length < 2) {
    showFlash('error', props.t('admin.flash.minQuestions'))
    return
  }

  saving.value = true
  try {
    const payload = {
      title: testEditor.value.title.trim(),
      description: testEditor.value.description.trim(),
      language: testEditor.value.language,
      question_ids: testEditor.value.question_ids,
      question_limit: Number(testEditor.value.question_limit),
      randomize_questions: Boolean(testEditor.value.randomize_questions),
      randomize_answers: Boolean(testEditor.value.randomize_answers),
      pass_score: Number(testEditor.value.pass_score)
    }

    if (testEditor.value.id) {
      await updateAdminTest(token.value, testEditor.value.id, payload)
      showFlash('success', props.t('admin.flash.testUpdated'))
    } else {
      await createAdminTest(token.value, payload)
      showFlash('success', props.t('admin.flash.testCreated'))
    }

    resetTestEditor()
    await loadAllData()
  } catch (error) {
    showFlash('error', getErrorText(error))
  } finally {
    saving.value = false
  }
}

async function saveQuestion() {
  if (!questionEditor.value.question_text.trim()) {
    showFlash('error', props.t('admin.flash.questionTextRequired'))
    return
  }

  if (!questionEditor.value.category.trim()) {
    showFlash('error', props.t('admin.flash.questionCategoryRequired'))
    return
  }

  const validAnswers = questionEditor.value.answers.filter((answer) => answer.answer_text.trim())
  if (validAnswers.length < 2) {
    showFlash('error', props.t('admin.flash.minAnswers'))
    return
  }

  if (validAnswers.filter((answer) => answer.is_correct).length !== 1) {
    showFlash('error', props.t('admin.flash.oneCorrect'))
    return
  }

  saving.value = true
  try {
    const payload = {
      question_text: questionEditor.value.question_text.trim(),
      category: questionEditor.value.category.trim(),
      language: questionEditor.value.language,
      image_url: questionEditor.value.image_url.trim(),
      answers: validAnswers.map((answer) => ({
        answer_text: answer.answer_text.trim(),
        is_correct: Boolean(answer.is_correct),
        explanation: (answer.explanation || '').trim()
      }))
    }

    if (questionEditor.value.id) {
      await updateAdminQuestion(token.value, questionEditor.value.id, payload)
      showFlash('success', props.t('admin.flash.questionUpdated'))
    } else {
      await createAdminQuestion(token.value, payload)
      showFlash('success', props.t('admin.flash.questionCreated'))
    }

    resetQuestionEditor()
    await loadAllData()
  } catch (error) {
    showFlash('error', getErrorText(error))
  } finally {
    saving.value = false
  }
}

function editQuestion(question) {
  questionEditor.value = {
    id: question.id,
    question_text: question.question_text,
    category: question.category,
    language: question.language || 'ru',
    image_url: question.image_url || '',
    answers: (question.answers || []).map((answer) => ({
      answer_text: answer.answer_text,
      is_correct: Boolean(answer.is_correct),
      explanation: answer.explanation || ''
    }))
  }

  if (questionEditor.value.answers.length < 2) {
    questionEditor.value.answers.push({
      answer_text: '',
      is_correct: false,
      explanation: ''
    })
  }

  activeTab.value = 'questions'
}

async function removeQuestion(questionId) {
  const confirmed = window.confirm(props.t('admin.flash.deleteQuestionConfirm'))
  if (!confirmed) return

  try {
    await deleteAdminQuestion(token.value, questionId)
    showFlash('success', props.t('admin.flash.questionDeleted'))
    if (questionEditor.value.id === questionId) {
      resetQuestionEditor()
    }
    await loadAllData()
  } catch (error) {
    showFlash('error', getErrorText(error))
  }
}

async function assignForUser(user) {
  ensureAssignConfig(user.id)
  const config = assignConfigByUser.value[user.id]
  const testId = Number(config.testId)

  if (!testId) {
    showFlash('error', props.t('admin.flash.selectTestBeforeAssign'))
    return
  }

  assigningUserId.value = user.id
  try {
    await assignTestToUser(token.value, {
      test_id: testId,
      user_id: user.id,
      user_email: user.email,
      mode: config.mode
    })
    showFlash('success', props.t('admin.flash.testAssigned', { email: user.email }))
    await loadAllData()
  } catch (error) {
    showFlash('error', getErrorText(error))
  } finally {
    assigningUserId.value = ''
  }
}

async function openUserAnalytics(user) {
  selectedUserAnalytics.value = user
  selectedUserAnalyticsData.value = null
  analyticsLoading.value = true
  try {
    selectedUserAnalyticsData.value = await fetchAdminUserAnalytics(token.value, user.id, 100)
  } catch (error) {
    showFlash('error', getErrorText(error))
  } finally {
    analyticsLoading.value = false
  }
}

async function openAttemptDetails(attempt) {
  if (!attempt?.has_review_details) {
    showFlash('error', props.t('admin.flash.noAttemptDetails'))
    return
  }

  attemptDetailsLoading.value = true
  selectedAttempt.value = null
  try {
    selectedAttempt.value = await fetchAdminAttemptDetails(token.value, attempt.attempt_id)
  } catch (error) {
    showFlash('error', getErrorText(error))
  } finally {
    attemptDetailsLoading.value = false
  }
}

function closeAttemptDetails() {
  selectedAttempt.value = null
}

watch(userSearch, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    try {
      await loadUsers()
    } catch (error) {
      showFlash('error', getErrorText(error))
    }
  }, 250)
})

watch(
  () => testEditor.value.language,
  (nextLanguage, prevLanguage) => {
    if (!prevLanguage || nextLanguage === prevLanguage) return
    testEditor.value.question_ids = testEditor.value.question_ids.filter((id) => {
      const question = questions.value.find((item) => item.id === id)
      return question && (question.language || 'ru') === nextLanguage
    })
  }
)

onMounted(async () => {
  await loadAllData()
})
</script>

<template>
  <section class="admin-root" :data-language="languageTick">
    <header class="page-head">
      <div>
        <p class="eyebrow">{{ props.t('admin.workspace') }}</p>
        <h2>{{ props.t('admin.title') }}</h2>
      </div>
      <button class="ghost-btn" :disabled="loading" @click="loadAllData">
        {{ loading ? props.t('common.loading') : props.t('admin.refresh') }}
      </button>
    </header>

    <div v-if="flashText" class="flash" :class="flashType">
      {{ flashText }}
    </div>

    <nav class="tabs">
      <button :class="{ active: activeTab === 'assignments' }" @click="activeTab = 'assignments'">{{ props.t('admin.tab.assignments') }}</button>
      <button :class="{ active: activeTab === 'tests' }" @click="activeTab = 'tests'">{{ props.t('admin.tab.tests') }}</button>
      <button :class="{ active: activeTab === 'questions' }" @click="activeTab = 'questions'">{{ props.t('admin.tab.questions') }}</button>
    </nav>

    <section v-if="activeTab === 'assignments'" class="panel">
      <div class="panel-head">
        <h3>{{ props.t('admin.assign.head') }}</h3>
        <input v-model="userSearch" type="text" :placeholder="props.t('admin.assign.search')" />
      </div>

      <div class="users-table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ props.t('admin.assign.user') }}</th>
              <th>{{ props.t('admin.assign.userId') }}</th>
              <th>{{ props.t('admin.assign.test') }}</th>
              <th>{{ props.t('admin.assign.mode') }}</th>
              <th>{{ props.t('admin.assign.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>
                <strong>{{ user.name || '-' }}</strong>
                <div>{{ user.email }}</div>
              </td>
              <td class="mono">{{ user.id }}</td>
              <td>
                <select v-model="assignConfigByUser[user.id].testId" @focus="ensureAssignConfig(user.id)">
                  <option disabled value="">{{ props.t('admin.assign.selectTest') }}</option>
                  <option v-for="test in tests" :key="test.id" :value="test.id">
                    {{ test.title }} ({{ contentLanguageLabel(test.language) }})
                  </option>
                </select>
              </td>
              <td>
                <select v-model="assignConfigByUser[user.id].mode" @focus="ensureAssignConfig(user.id)">
                  <option value="exam">{{ props.t('admin.assign.modeExam') }}</option>
                  <option value="training">{{ props.t('admin.assign.modeTraining') }}</option>
                </select>
              </td>
              <td>
                <div class="inline-actions">
                  <button class="solid-btn" :disabled="assigningUserId === user.id" @click="assignForUser(user)">
                    {{ assigningUserId === user.id ? '...' : props.t('admin.assign.assign') }}
                  </button>
                  <button class="ghost-btn" @click="openUserAnalytics(user)">{{ props.t('admin.assign.analytics') }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="sub-grid">
        <article class="sub-card">
          <h4>{{ props.t('admin.assign.latest') }}</h4>
          <div class="assignments-list">
            <div v-for="assignment in assignments.slice(0, 12)" :key="assignment.id" class="assignment-item">
              <div>
                <strong>{{ assignment.user_email }}</strong>
                <p>
                  {{ assignment.test_title }} · {{ contentLanguageLabel(assignment.test_language || assignment.language) }} ·
                  {{ modeLabel(assignment.mode) }}
                </p>
              </div>
              <div class="assignment-score">
                <span>{{ assignment.last_score === null ? '-' : `${assignment.last_score}%` }}</span>
                <small>{{ props.t('admin.assign.attempts') }}: {{ assignment.attempts }}</small>
              </div>
            </div>
          </div>
        </article>

        <article class="sub-card">
          <h4>{{ props.t('admin.assign.userAnalytics') }}</h4>
          <p v-if="!selectedUserAnalytics">{{ props.t('admin.assign.pickUserAnalytics') }}</p>
          <p v-else-if="analyticsLoading">{{ props.t('admin.assign.loadingAnalytics') }}</p>
          <template v-else-if="selectedUserAnalyticsData">
            <div class="analytics-head">
              <strong>{{ selectedUserAnalytics.name || selectedUserAnalytics.email }}</strong>
              <small>{{ selectedUserAnalytics.email }}</small>
            </div>
            <div class="analytics-kpi">
              <div>
                <span>{{ props.t('admin.assign.attempts') }}</span>
                <strong>{{ selectedUserAnalyticsData.summary.total_attempts }}</strong>
              </div>
              <div>
                <span>{{ props.t('admin.assign.average') }}</span>
                <strong>{{ selectedUserAnalyticsData.summary.average_score }}%</strong>
              </div>
              <div>
                <span>{{ props.t('admin.assign.best') }}</span>
                <strong>{{ selectedUserAnalyticsData.summary.best_score }}%</strong>
              </div>
            </div>
            <div class="attempts-history">
              <div v-for="attempt in selectedUserAnalyticsData.attempts.slice(0, 8)" :key="attempt.attempt_id" class="attempt-item">
                <div>
                  <strong>{{ attempt.test_title || `Test #${attempt.test_id}` }}</strong>
                  <p>{{ modeLabel(attempt.mode) }} · {{ props.t('admin.assign.attempt', { n: attempt.attempt_number }) }}</p>
                </div>
                <div class="attempt-score">
                  <span>{{ attempt.score }}%</span>
                  <small>{{ attempt.created_at }}</small>
                </div>
                <div class="attempt-actions">
                  <button
                    v-if="attempt.has_review_details"
                    class="ghost-btn"
                    :disabled="attemptDetailsLoading"
                    @click="openAttemptDetails(attempt)"
                  >
                    {{ attemptDetailsLoading ? props.t('common.loading') : props.t('admin.assign.analysis') }}
                  </button>
                  <button v-else class="ghost-btn" disabled>{{ props.t('admin.assign.noAnalysis') }}</button>
                </div>
              </div>
            </div>
          </template>
        </article>
      </div>
    </section>

    <section v-if="activeTab === 'tests'" class="panel">
      <div class="panel-head">
        <h3>{{ testEditor.id ? props.t('admin.tests.editing') : props.t('admin.tests.creating') }}</h3>
        <button class="ghost-btn" @click="resetTestEditor">{{ props.t('admin.tests.new') }}</button>
      </div>

      <div class="editor-grid">
        <article class="editor-card">
          <label>
            <span>{{ props.t('admin.tests.name') }}</span>
            <input v-model="testEditor.title" type="text" :placeholder="props.t('admin.tests.namePlaceholder')" />
          </label>

          <label>
            <span>{{ props.t('admin.tests.description') }}</span>
            <textarea v-model="testEditor.description" rows="2" :placeholder="props.t('admin.tests.descriptionPlaceholder')"></textarea>
          </label>

          <label>
            <span>{{ props.t('admin.tests.language') }}</span>
            <select v-model="testEditor.language">
              <option v-for="option in contentLanguageOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <small>{{ props.t('admin.tests.languageHint') }}</small>
          </label>

          <div class="inline-fields">
            <label>
              <span>{{ props.t('admin.tests.limit') }}</span>
              <input v-model.number="testEditor.question_limit" type="number" min="1" />
            </label>
            <label>
              <span>{{ props.t('admin.tests.passScore') }}</span>
              <input v-model.number="testEditor.pass_score" type="number" min="0" max="100" />
            </label>
          </div>

          <label class="checkbox">
            <input v-model="testEditor.randomize_questions" type="checkbox" />
            <span>{{ props.t('admin.tests.randomQuestions') }}</span>
          </label>

          <label class="checkbox">
            <input v-model="testEditor.randomize_answers" type="checkbox" />
            <span>{{ props.t('admin.tests.randomAnswers') }}</span>
          </label>

          <p>{{ props.t('admin.tests.selectedCount', { count: selectedQuestionCount }) }}</p>
          <button class="solid-btn" :disabled="saving" @click="saveTest">
            {{ saving ? props.t('common.loading') : testEditor.id ? props.t('admin.tests.save') : props.t('admin.tests.create') }}
          </button>
        </article>

        <article class="editor-card">
          <div class="panel-head compact">
            <h4>{{ props.t('admin.tests.bank') }}</h4>
          </div>
          <div class="filters">
            <select v-model="testFilterLanguage">
              <option value="all">{{ props.t('admin.filters.allLanguages') }}</option>
              <option v-for="option in contentLanguageOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <select v-model="testFilterCategory">
              <option value="all">{{ props.t('user.training.general.allCategories') }}</option>
              <option v-for="category in availableCategories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <input v-model="testFilterQuery" type="text" :placeholder="props.t('admin.tests.searchQuestion')" />
          </div>

          <div class="question-list">
            <button
              v-for="question in filteredQuestionsForTest"
              :key="question.id"
              type="button"
              class="question-chip"
              :class="{ selected: isQuestionSelected(question.id) }"
              @click="toggleQuestionForTest(question.id)"
            >
              <span>#{{ question.id }}</span>
              <span>{{ question.question_text }}</span>
              <small>{{ question.category }} · {{ contentLanguageLabel(question.language) }}</small>
            </button>
          </div>
        </article>
      </div>

      <article class="tests-list-card">
        <h4>{{ props.t('admin.tests.existing') }}</h4>
        <div class="tests-list">
          <div v-for="test in tests" :key="test.id" class="test-item">
            <div>
              <strong>{{ test.title }}</strong>
              <p>{{ test.description || props.t('user.tests.noDescription') }}</p>
              <small>
                {{ test.is_legacy ? props.t('admin.tests.system') : props.t('admin.tests.custom') }} ·
                {{ contentLanguageLabel(test.language) }} ·
                {{ props.t('admin.tests.questionsCount', { count: test.question_count }) }} ·
                {{ props.t('admin.tests.passPercent', { score: test.pass_score }) }}
              </small>
            </div>
            <button class="ghost-btn" @click="openTestForEdit(test.id)">{{ props.t('admin.tests.edit') }}</button>
          </div>
        </div>
      </article>
    </section>

    <section v-if="activeTab === 'questions'" class="panel">
      <div class="panel-head">
        <h3>{{ questionEditor.id ? props.t('admin.questions.editing') : props.t('admin.questions.creating') }}</h3>
        <button class="ghost-btn" @click="resetQuestionEditor">{{ props.t('admin.questions.new') }}</button>
      </div>

      <div class="editor-grid">
        <article class="editor-card">
          <label>
            <span>{{ props.t('admin.questions.text') }}</span>
            <textarea v-model="questionEditor.question_text" rows="3" :placeholder="props.t('admin.questions.textPlaceholder')"></textarea>
          </label>

          <label>
            <span>{{ props.t('admin.questions.category') }}</span>
            <input v-model="questionEditor.category" type="text" :placeholder="props.t('admin.questions.categoryPlaceholder')" list="categories-list" />
            <datalist id="categories-list">
              <option v-for="category in availableCategories" :key="category" :value="category"></option>
            </datalist>
          </label>

          <label>
            <span>{{ props.t('admin.questions.language') }}</span>
            <select v-model="questionEditor.language">
              <option v-for="option in contentLanguageOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label>
            <span>{{ props.t('admin.questions.image') }}</span>
            <input v-model="questionEditor.image_url" type="text" :placeholder="props.t('admin.questions.imagePlaceholder')" />
          </label>

          <div class="answers-editor">
            <div v-for="(answer, index) in questionEditor.answers" :key="index" class="answer-row">
              <input type="radio" name="correct-answer" :checked="answer.is_correct" @change="setCorrectAnswer(index)" />
              <input v-model="answer.answer_text" type="text" :placeholder="props.t('admin.questions.answerPlaceholder')" />
              <input v-model="answer.explanation" type="text" :placeholder="props.t('admin.questions.explanationPlaceholder')" />
              <button class="danger-btn" type="button" @click="removeAnswerOption(index)">×</button>
            </div>
          </div>

          <div class="inline-actions">
            <button class="ghost-btn" type="button" @click="addAnswerOption">{{ props.t('admin.questions.addAnswer') }}</button>
            <button class="solid-btn" type="button" :disabled="saving" @click="saveQuestion">
              {{ saving ? props.t('common.loading') : questionEditor.id ? props.t('admin.questions.save') : props.t('admin.questions.create') }}
            </button>
          </div>
        </article>

        <article class="editor-card">
          <div class="filters">
            <select v-model="questionFilterLanguage">
              <option value="all">{{ props.t('admin.filters.allLanguages') }}</option>
              <option v-for="option in contentLanguageOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <select v-model="questionFilterCategory">
              <option value="all">{{ props.t('user.training.general.allCategories') }}</option>
              <option v-for="category in availableCategories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <input v-model="questionFilterQuery" type="text" :placeholder="props.t('admin.tests.searchQuestion')" />
          </div>

          <div class="question-list">
            <div v-for="question in filteredQuestionsForBank" :key="question.id" class="question-item">
              <div>
                <strong>#{{ question.id }} · {{ question.category }} · {{ contentLanguageLabel(question.language) }}</strong>
                <p>{{ question.question_text }}</p>
                <small>{{ props.t('admin.questions.answersCount', { count: question.answers?.length || question.answers_count || 0 }) }}</small>
              </div>
              <div class="inline-actions">
                <button class="ghost-btn" @click="editQuestion(question)">{{ props.t('admin.questions.change') }}</button>
                <button class="danger-btn" @click="removeQuestion(question.id)">{{ props.t('admin.questions.delete') }}</button>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <div v-if="selectedAttempt" class="review-overlay" @click.self="closeAttemptDetails">
      <div class="review-modal">
        <div class="review-head">
          <div>
            <h3>{{ selectedAttempt.test_title || `Test #${selectedAttempt.test_id}` }}</h3>
            <p>
              {{ modeLabel(selectedAttempt.mode) }}
              · {{ props.t('admin.assign.attempt', { n: selectedAttempt.attempt_number }) }}
              · {{ selectedAttempt.score }}%
            </p>
          </div>
          <button class="ghost-btn" @click="closeAttemptDetails">{{ props.t('admin.review.close') }}</button>
        </div>

        <div class="review-summary">
          <div>
            <span>{{ props.t('admin.review.correct') }}</span>
            <strong>{{ selectedAttempt.correct_answers }} / {{ selectedAttempt.total_questions }}</strong>
          </div>
          <div>
            <span>{{ props.t('admin.review.wrong') }}</span>
            <strong>{{ selectedAttempt.wrong_answers }}</strong>
          </div>
          <div>
            <span>{{ props.t('admin.review.passScore') }}</span>
            <strong>{{ selectedAttempt.pass_score }}%</strong>
          </div>
        </div>

        <div class="review-list">
          <article
            v-for="item in selectedAttempt.questions"
            :key="item.question_id"
            class="review-item"
            :class="{ correct: item.is_correct, wrong: !item.is_correct }"
          >
            <p class="review-category">{{ item.category }}</p>
            <h4>#{{ item.question_id }} · {{ item.question_text }}</h4>
            <p><strong>{{ props.t('admin.review.userAnswer') }}</strong> {{ item.selected_answer_text }}</p>
            <p><strong>{{ props.t('admin.review.correctAnswer') }}</strong> {{ item.correct_answer_text }}</p>
            <p v-if="!item.is_correct" class="review-status">{{ props.t('admin.review.error') }}</p>
            <p v-else class="review-status success">{{ props.t('admin.review.success') }}</p>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.admin-root {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid #d7e7eb;
  border-radius: 22px;
  padding: 16px;
  backdrop-filter: blur(8px);
  box-shadow: 0 12px 28px rgba(11, 50, 63, 0.08);
}

.page-head h2 {
  margin: 6px 0 0;
  font-size: clamp(1.45rem, 2.2vw, 2.2rem);
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.76rem;
  color: #0f6c78;
  font-weight: 800;
}

.flash {
  border-radius: 14px;
  padding: 11px 14px;
  font-weight: 700;
  border: 1px solid transparent;
}

.flash.success {
  background: #def7e9;
  border-color: #bfe8cb;
  color: #0d6735;
}

.flash.error {
  background: #ffe3e3;
  border-color: #f2c3c9;
  color: #9f1f2d;
}

.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid #d5e5e9;
  width: fit-content;
}

.tabs button {
  border: none;
  border-radius: 12px;
  padding: 9px 14px;
  cursor: pointer;
  background: transparent;
  color: #1e4752;
  font-weight: 700;
}

.tabs button:hover {
  background: #eff7f9;
}

.tabs button.active {
  background: linear-gradient(135deg, #0b7581, #0a9d75);
  color: #f2fffc;
  box-shadow: 0 8px 18px rgba(11, 117, 129, 0.24);
}

.panel {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #d2e4e8;
  border-radius: 24px;
  padding: 20px;
  box-shadow: 0 16px 34px rgba(14, 38, 45, 0.08);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.panel-head input {
  min-width: 280px;
}

.panel-head.compact {
  margin-bottom: 8px;
}

.panel-head h3,
.panel-head h4 {
  margin: 0;
}

.editor-grid,
.sub-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.editor-card,
.sub-card,
.tests-list-card {
  border: 1px solid #d7e7eb;
  border-radius: 18px;
  padding: 15px;
  background: linear-gradient(180deg, #fbffff, #f8fcfd);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.tests-list-card {
  margin-top: 14px;
}

.editor-card label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.editor-card label span {
  font-weight: 700;
  color: #1a3c47;
}

.editor-card label small {
  color: #4a6874;
  font-size: 0.8rem;
}

input,
textarea,
select {
  border: 1px solid #c8dde2;
  border-radius: 11px;
  padding: 9px 10px;
  font: inherit;
  background: #fcffff;
}

input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  border-color: #0b7f8c;
  box-shadow: 0 0 0 3px rgba(11, 127, 140, 0.12);
}

.inline-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
}

.checkbox span {
  font-weight: 600;
}

.filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.question-list {
  max-height: 380px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 2px;
}

.question-chip {
  border: 1px solid #d1e5e9;
  border-radius: 13px;
  background: #f5fbfc;
  text-align: left;
  padding: 9px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  cursor: pointer;
}

.question-chip:hover {
  border-color: #93c5cd;
  transform: translateY(-1px);
}

.question-chip.selected {
  border-color: #117b88;
  background: linear-gradient(135deg, #def6f8, #f0fffd);
  box-shadow: 0 10px 20px rgba(17, 123, 136, 0.15);
}

.users-table-wrap {
  margin-top: 12px;
  overflow: auto;
  border: 1px solid #d9e8eb;
  border-radius: 14px;
  background: white;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid #e2edf0;
  text-align: left;
  padding: 11px 9px;
  vertical-align: middle;
}

tbody tr:hover {
  background: #f7fcfd;
}

th {
  font-size: 0.82rem;
  color: #35535f;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

.mono {
  font-family: 'Fira Code', monospace;
  font-size: 0.76rem;
}

.assignments-list,
.attempts-history,
.tests-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assignment-item,
.attempt-item,
.test-item,
.question-item {
  border: 1px solid #dce9ec;
  border-radius: 13px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  background: #fcffff;
}

.assignment-item p,
.attempt-item p,
.test-item p,
.question-item p {
  margin: 4px 0;
}

.assignment-score,
.attempt-score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.attempt-actions {
  display: flex;
  align-items: center;
}

.analytics-head {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}

.analytics-kpi {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.analytics-kpi div {
  border: 1px solid #d5e6ea;
  border-radius: 12px;
  padding: 9px;
  background: #f8fcfd;
}

.analytics-kpi span {
  display: block;
  color: #476774;
  font-size: 0.8rem;
}

.analytics-kpi strong {
  font-size: 1.1rem;
}

.answers-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.answer-row {
  display: grid;
  grid-template-columns: auto 1fr 1fr auto;
  gap: 8px;
  align-items: center;
}

.inline-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.solid-btn,
.ghost-btn,
.danger-btn {
  border: none;
  border-radius: 11px;
  padding: 9px 13px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.solid-btn {
  background: linear-gradient(135deg, #0b7581, #0a9d75);
  color: #f2fffc;
  box-shadow: 0 10px 20px rgba(11, 117, 129, 0.24);
}

.solid-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.ghost-btn {
  background: #eaf6f7;
  color: #1e4954;
}

.ghost-btn:hover:not(:disabled) {
  background: #dff0f3;
}

.danger-btn {
  background: #ffe1e5;
  color: #8f2130;
}

.danger-btn:hover:not(:disabled) {
  background: #ffd2d8;
}

.solid-btn:disabled,
.ghost-btn:disabled,
.danger-btn:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

.review-overlay {
  position: fixed;
  inset: 0;
  background: rgba(8, 26, 33, 0.5);
  display: grid;
  place-items: center;
  z-index: 60;
  backdrop-filter: blur(2px);
}

.review-modal {
  width: min(920px, calc(100vw - 30px));
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: white;
  border: 1px solid #d9e9ec;
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 24px 44px rgba(5, 31, 39, 0.28);
}

.review-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.review-head h3 {
  margin: 0;
}

.review-head p {
  margin: 6px 0 0;
  color: #476775;
}

.review-summary {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.review-summary div {
  border: 1px solid #d5e6ea;
  border-radius: 12px;
  padding: 8px;
  background: #f8fcfd;
}

.review-summary span {
  display: block;
  color: #466672;
  font-size: 0.8rem;
}

.review-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-item {
  border: 1px solid #dde9ec;
  border-radius: 12px;
  padding: 10px;
  background: #fcffff;
}

.review-item.correct {
  border-color: #bee4cb;
  background: #f3fcf6;
}

.review-item.wrong {
  border-color: #f0c7cd;
  background: #fff7f8;
}

.review-category {
  margin: 0;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #557784;
  font-weight: 700;
}

.review-item h4 {
  margin: 6px 0;
}

.review-item p {
  margin: 4px 0;
}

.review-status {
  font-weight: 700;
  color: #9f2632;
}

.review-status.success {
  color: #11683a;
}

@media (max-width: 1100px) {
  .editor-grid,
  .sub-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 740px) {
  .panel {
    padding: 14px;
    border-radius: 18px;
  }

  .panel-head {
    flex-direction: column;
    align-items: stretch;
  }

  .panel-head input {
    min-width: 0;
  }

  .inline-fields,
  .filters,
  .answer-row {
    grid-template-columns: 1fr;
  }

  .inline-actions {
    flex-wrap: wrap;
  }

  .review-summary {
    grid-template-columns: 1fr;
  }
}
</style>
