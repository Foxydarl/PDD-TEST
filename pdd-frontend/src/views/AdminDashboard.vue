<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  assignTestToUser,
  createAdminQuestion,
  createAdminTest,
  deleteAdminQuestion,
  fetchAdminAssignments,
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
  }
})

const token = computed(() => props.session.token)

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

const assignConfigByUser = ref({})
const assigningUserId = ref('')

const testFilterQuery = ref('')
const testFilterCategory = ref('all')

const testEditor = ref({
  id: null,
  title: '',
  description: '',
  question_limit: 20,
  randomize_questions: true,
  randomize_answers: false,
  pass_score: 70,
  question_ids: []
})

const questionFilterQuery = ref('')
const questionFilterCategory = ref('all')

const questionEditor = ref({
  id: null,
  question_text: '',
  category: '',
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
  return error?.response?.data?.detail || error?.message || 'Неизвестная ошибка'
}

function resetTestEditor() {
  testEditor.value = {
    id: null,
    title: '',
    description: '',
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

const filteredQuestionsForTest = computed(() => {
  const q = testFilterQuery.value.trim().toLowerCase()
  return questions.value.filter((question) => {
    const categoryOk =
      testFilterCategory.value === 'all' || question.category === testFilterCategory.value
    const queryOk =
      q.length === 0 ||
      question.question_text.toLowerCase().includes(q) ||
      String(question.id).includes(q)
    return categoryOk && queryOk
  })
})

const filteredQuestionsForBank = computed(() => {
  const q = questionFilterQuery.value.trim().toLowerCase()
  return questions.value.filter((question) => {
    const categoryOk =
      questionFilterCategory.value === 'all' || question.category === questionFilterCategory.value
    const queryOk =
      q.length === 0 ||
      question.question_text.toLowerCase().includes(q) ||
      String(question.id).includes(q)
    return categoryOk && queryOk
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
    const [testsData, usersData, assignmentsData, questionsData, categoriesData] = await Promise.all([
      fetchAdminTests(token.value),
      fetchAdminUsers(token.value, userSearch.value),
      fetchAdminAssignments(token.value),
      fetchAdminQuestions(token.value, { include_answers: true }),
      fetchAdminCategories(token.value)
    ])

    tests.value = testsData
    users.value = usersData
    assignments.value = assignmentsData
    questions.value = questionsData
    categories.value = categoriesData

    users.value.forEach((user) => ensureAssignConfig(user.id))
  } catch (error) {
    showFlash('error', getErrorText(error))
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
      question_limit: test.question_limit,
      randomize_questions: test.randomize_questions,
      randomize_answers: test.randomize_answers,
      pass_score: test.pass_score,
      question_ids: test.question_ids || []
    }
    activeTab.value = 'tests'
    showFlash('success', `Тест "${test.title}" загружен для редактирования`)
  } catch (error) {
    showFlash('error', getErrorText(error))
  }
}

async function saveTest() {
  if (!testEditor.value.title.trim()) {
    showFlash('error', 'Укажи название теста')
    return
  }

  if (testEditor.value.question_ids.length < 2) {
    showFlash('error', 'Выбери минимум 2 вопроса')
    return
  }

  saving.value = true
  try {
    const payload = {
      title: testEditor.value.title.trim(),
      description: testEditor.value.description.trim(),
      question_ids: testEditor.value.question_ids,
      question_limit: Number(testEditor.value.question_limit),
      randomize_questions: Boolean(testEditor.value.randomize_questions),
      randomize_answers: Boolean(testEditor.value.randomize_answers),
      pass_score: Number(testEditor.value.pass_score)
    }

    if (testEditor.value.id) {
      await updateAdminTest(token.value, testEditor.value.id, payload)
      showFlash('success', 'Тест обновлен')
    } else {
      await createAdminTest(token.value, payload)
      showFlash('success', 'Тест создан')
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
    showFlash('error', 'Введите текст вопроса')
    return
  }

  if (!questionEditor.value.category.trim()) {
    showFlash('error', 'Укажите категорию')
    return
  }

  const validAnswers = questionEditor.value.answers.filter((answer) => answer.answer_text.trim())
  if (validAnswers.length < 2) {
    showFlash('error', 'Добавьте минимум 2 варианта ответа')
    return
  }

  if (validAnswers.filter((answer) => answer.is_correct).length !== 1) {
    showFlash('error', 'Должен быть ровно один правильный ответ')
    return
  }

  saving.value = true
  try {
    const payload = {
      question_text: questionEditor.value.question_text.trim(),
      category: questionEditor.value.category.trim(),
      image_url: questionEditor.value.image_url.trim(),
      answers: validAnswers.map((answer) => ({
        answer_text: answer.answer_text.trim(),
        is_correct: Boolean(answer.is_correct),
        explanation: (answer.explanation || '').trim()
      }))
    }

    if (questionEditor.value.id) {
      await updateAdminQuestion(token.value, questionEditor.value.id, payload)
      showFlash('success', 'Вопрос обновлен')
    } else {
      await createAdminQuestion(token.value, payload)
      showFlash('success', 'Вопрос создан')
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
  const confirmed = window.confirm('Удалить этот вопрос? Он будет убран и из связанных тестов.')
  if (!confirmed) return

  try {
    await deleteAdminQuestion(token.value, questionId)
    showFlash('success', 'Вопрос удален')
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
    showFlash('error', 'Выбери тест перед назначением')
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
    showFlash('success', `Тест назначен пользователю ${user.email}`)
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

onMounted(async () => {
  await loadAllData()
})
</script>

<template>
  <section class="admin-root">
    <header class="page-head">
      <div>
        <p class="eyebrow">Admin Workspace</p>
        <h2>Управление тестами, вопросами и аналитикой</h2>
      </div>
      <button class="ghost-btn" :disabled="loading" @click="loadAllData">
        {{ loading ? 'Загрузка...' : 'Обновить данные' }}
      </button>
    </header>

    <div v-if="flashText" class="flash" :class="flashType">
      {{ flashText }}
    </div>

    <nav class="tabs">
      <button :class="{ active: activeTab === 'assignments' }" @click="activeTab = 'assignments'">Назначения</button>
      <button :class="{ active: activeTab === 'tests' }" @click="activeTab = 'tests'">Тесты</button>
      <button :class="{ active: activeTab === 'questions' }" @click="activeTab = 'questions'">Вопросы</button>
    </nav>

    <section v-if="activeTab === 'assignments'" class="panel">
      <div class="panel-head">
        <h3>Назначение тестов и режимов</h3>
        <input v-model="userSearch" type="text" placeholder="Поиск по email или имени" />
      </div>

      <div class="users-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Пользователь</th>
              <th>ID</th>
              <th>Тест</th>
              <th>Режим</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>
                <strong>{{ user.name || 'Без имени' }}</strong>
                <div>{{ user.email }}</div>
              </td>
              <td class="mono">{{ user.id }}</td>
              <td>
                <select v-model="assignConfigByUser[user.id].testId" @focus="ensureAssignConfig(user.id)">
                  <option disabled value="">Выбери тест</option>
                  <option v-for="test in tests" :key="test.id" :value="test.id">
                    {{ test.title }}
                  </option>
                </select>
              </td>
              <td>
                <select v-model="assignConfigByUser[user.id].mode" @focus="ensureAssignConfig(user.id)">
                  <option value="exam">Экзамен (1 попытка)</option>
                  <option value="training">Обучение (с аналитикой)</option>
                </select>
              </td>
              <td>
                <div class="inline-actions">
                  <button class="solid-btn" :disabled="assigningUserId === user.id" @click="assignForUser(user)">
                    {{ assigningUserId === user.id ? '...' : 'Назначить' }}
                  </button>
                  <button class="ghost-btn" @click="openUserAnalytics(user)">Аналитика</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="sub-grid">
        <article class="sub-card">
          <h4>Последние назначения</h4>
          <div class="assignments-list">
            <div v-for="assignment in assignments.slice(0, 12)" :key="assignment.id" class="assignment-item">
              <div>
                <strong>{{ assignment.user_email }}</strong>
                <p>{{ assignment.test_title }} · {{ assignment.mode === 'training' ? 'Обучение' : 'Экзамен' }}</p>
              </div>
              <div class="assignment-score">
                <span>{{ assignment.last_score === null ? '—' : `${assignment.last_score}%` }}</span>
                <small>попыток: {{ assignment.attempts }}</small>
              </div>
            </div>
          </div>
        </article>

        <article class="sub-card">
          <h4>Аналитика пользователя</h4>
          <p v-if="!selectedUserAnalytics">Выбери пользователя в таблице, чтобы посмотреть историю прохождений.</p>
          <p v-else-if="analyticsLoading">Загрузка аналитики...</p>
          <template v-else-if="selectedUserAnalyticsData">
            <div class="analytics-head">
              <strong>{{ selectedUserAnalytics.name || selectedUserAnalytics.email }}</strong>
              <small>{{ selectedUserAnalytics.email }}</small>
            </div>
            <div class="analytics-kpi">
              <div>
                <span>Попыток</span>
                <strong>{{ selectedUserAnalyticsData.summary.total_attempts }}</strong>
              </div>
              <div>
                <span>Средний балл</span>
                <strong>{{ selectedUserAnalyticsData.summary.average_score }}%</strong>
              </div>
              <div>
                <span>Лучший балл</span>
                <strong>{{ selectedUserAnalyticsData.summary.best_score }}%</strong>
              </div>
            </div>
            <div class="attempts-history">
              <div v-for="attempt in selectedUserAnalyticsData.attempts.slice(0, 8)" :key="attempt.attempt_id" class="attempt-item">
                <div>
                  <strong>{{ attempt.test_title || `Тест #${attempt.test_id}` }}</strong>
                  <p>{{ attempt.mode === 'training' ? 'Обучение' : 'Экзамен' }} · попытка {{ attempt.attempt_number }}</p>
                </div>
                <div class="attempt-score">
                  <span>{{ attempt.score }}%</span>
                  <small>{{ attempt.created_at }}</small>
                </div>
              </div>
            </div>
          </template>
        </article>
      </div>
    </section>

    <section v-if="activeTab === 'tests'" class="panel">
      <div class="panel-head">
        <h3>{{ testEditor.id ? 'Редактирование теста' : 'Создание теста' }}</h3>
        <button class="ghost-btn" @click="resetTestEditor">Новый тест</button>
      </div>

      <div class="editor-grid">
        <article class="editor-card">
          <label>
            <span>Название</span>
            <input v-model="testEditor.title" type="text" placeholder="Например: Экзамен по знакам" />
          </label>

          <label>
            <span>Описание</span>
            <textarea v-model="testEditor.description" rows="2" placeholder="Коротко опиши цель теста"></textarea>
          </label>

          <div class="inline-fields">
            <label>
              <span>Лимит вопросов</span>
              <input v-model.number="testEditor.question_limit" type="number" min="1" />
            </label>
            <label>
              <span>Проходной балл (%)</span>
              <input v-model.number="testEditor.pass_score" type="number" min="0" max="100" />
            </label>
          </div>

          <label class="checkbox">
            <input v-model="testEditor.randomize_questions" type="checkbox" />
            <span>Рандомизировать порядок вопросов</span>
          </label>

          <label class="checkbox">
            <input v-model="testEditor.randomize_answers" type="checkbox" />
            <span>Рандомизировать варианты ответов</span>
          </label>

          <p>Выбрано вопросов: <strong>{{ selectedQuestionCount }}</strong></p>
          <button class="solid-btn" :disabled="saving" @click="saveTest">
            {{ saving ? 'Сохранение...' : testEditor.id ? 'Сохранить изменения' : 'Создать тест' }}
          </button>
        </article>

        <article class="editor-card">
          <div class="panel-head compact">
            <h4>Банк вопросов для теста</h4>
          </div>
          <div class="filters">
            <select v-model="testFilterCategory">
              <option value="all">Все категории</option>
              <option v-for="category in availableCategories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <input v-model="testFilterQuery" type="text" placeholder="Поиск вопроса" />
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
              <small>{{ question.category }}</small>
            </button>
          </div>
        </article>
      </div>

      <article class="tests-list-card">
        <h4>Существующие тесты</h4>
        <div class="tests-list">
          <div v-for="test in tests" :key="test.id" class="test-item">
            <div>
              <strong>{{ test.title }}</strong>
              <p>{{ test.description || 'Без описания' }}</p>
              <small>
                {{ test.is_legacy ? 'Системный' : 'Кастомный' }} ·
                {{ test.question_count }} вопросов ·
                проходной {{ test.pass_score }}%
              </small>
            </div>
            <button class="ghost-btn" @click="openTestForEdit(test.id)">Редактировать</button>
          </div>
        </div>
      </article>
    </section>

    <section v-if="activeTab === 'questions'" class="panel">
      <div class="panel-head">
        <h3>{{ questionEditor.id ? 'Редактирование вопроса' : 'Создание вопроса' }}</h3>
        <button class="ghost-btn" @click="resetQuestionEditor">Новый вопрос</button>
      </div>

      <div class="editor-grid">
        <article class="editor-card">
          <label>
            <span>Текст вопроса</span>
            <textarea v-model="questionEditor.question_text" rows="3" placeholder="Введите вопрос"></textarea>
          </label>

          <label>
            <span>Категория</span>
            <input v-model="questionEditor.category" type="text" placeholder="Например: дорожные знаки" list="categories-list" />
            <datalist id="categories-list">
              <option v-for="category in availableCategories" :key="category" :value="category"></option>
            </datalist>
          </label>

          <label>
            <span>Ссылка на изображение (опционально)</span>
            <input v-model="questionEditor.image_url" type="text" placeholder="https://..." />
          </label>

          <div class="answers-editor">
            <div v-for="(answer, index) in questionEditor.answers" :key="index" class="answer-row">
              <input type="radio" name="correct-answer" :checked="answer.is_correct" @change="setCorrectAnswer(index)" />
              <input v-model="answer.answer_text" type="text" placeholder="Вариант ответа" />
              <input v-model="answer.explanation" type="text" placeholder="Пояснение (опционально)" />
              <button class="danger-btn" type="button" @click="removeAnswerOption(index)">×</button>
            </div>
          </div>

          <div class="inline-actions">
            <button class="ghost-btn" type="button" @click="addAnswerOption">Добавить ответ</button>
            <button class="solid-btn" type="button" :disabled="saving" @click="saveQuestion">
              {{ saving ? 'Сохранение...' : questionEditor.id ? 'Сохранить вопрос' : 'Создать вопрос' }}
            </button>
          </div>
        </article>

        <article class="editor-card">
          <div class="filters">
            <select v-model="questionFilterCategory">
              <option value="all">Все категории</option>
              <option v-for="category in availableCategories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <input v-model="questionFilterQuery" type="text" placeholder="Поиск вопроса" />
          </div>

          <div class="question-list">
            <div v-for="question in filteredQuestionsForBank" :key="question.id" class="question-item">
              <div>
                <strong>#{{ question.id }} · {{ question.category }}</strong>
                <p>{{ question.question_text }}</p>
                <small>{{ question.answers?.length || 0 }} вариантов ответа</small>
              </div>
              <div class="inline-actions">
                <button class="ghost-btn" @click="editQuestion(question)">Изменить</button>
                <button class="danger-btn" @click="removeQuestion(question.id)">Удалить</button>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.admin-root {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.page-head h2 {
  margin: 6px 0 0;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-size: 0.78rem;
  color: #0f6c78;
}

.flash {
  border-radius: 12px;
  padding: 10px 14px;
  font-weight: 700;
}

.flash.success {
  background: #dff7e7;
  color: #0d6735;
}

.flash.error {
  background: #ffe3e3;
  color: #9f1f2d;
}

.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tabs button {
  border: none;
  border-radius: 12px;
  padding: 9px 14px;
  cursor: pointer;
  background: #eaf5f7;
  color: #1e4752;
  font-weight: 700;
}

.tabs button.active {
  background: linear-gradient(135deg, #0b7581, #0a9d75);
  color: #f2fffc;
}

.panel {
  background: #ffffffd9;
  border: 1px solid #d7e6e8;
  border-radius: 20px;
  padding: 18px;
  box-shadow: 0 8px 20px rgba(16, 24, 40, 0.06);
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
  border: 1px solid #dce8ea;
  border-radius: 16px;
  padding: 14px;
  background: #fcffff;
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
  font-weight: 600;
  color: #1a3c47;
}

input,
textarea,
select {
  border: 1px solid #c9dce0;
  border-radius: 10px;
  padding: 9px 10px;
  font: inherit;
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
  grid-template-columns: 0.8fr 1.2fr;
  gap: 8px;
  margin-bottom: 10px;
}

.question-list {
  max-height: 360px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.question-chip {
  border: 1px solid #d3e7ea;
  border-radius: 12px;
  background: #f6fcfd;
  text-align: left;
  padding: 9px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  cursor: pointer;
}

.question-chip.selected {
  border-color: #117b88;
  background: #def6f8;
}

.users-table-wrap {
  margin-top: 12px;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid #ddeaec;
  text-align: left;
  padding: 10px 8px;
  vertical-align: middle;
}

th {
  font-size: 0.82rem;
  color: #35535f;
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
  border-radius: 12px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
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
  border: 1px solid #dce7ea;
  border-radius: 10px;
  padding: 8px;
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
  border-radius: 10px;
  padding: 8px 12px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.solid-btn {
  background: linear-gradient(135deg, #0b7581, #0a9d75);
  color: #f2fffc;
}

.ghost-btn {
  background: #eaf6f7;
  color: #1e4954;
}

.danger-btn {
  background: #ffdfe3;
  color: #8f2130;
}

.solid-btn:disabled,
.ghost-btn:disabled,
.danger-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 1100px) {
  .editor-grid,
  .sub-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 740px) {
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
}
</style>
