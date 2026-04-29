<script setup>
import { computed, onMounted, ref } from 'vue'
import { updateProfileName } from '../api/auth'
import {
  fetchAssignedQuestions,
  fetchMyAnalytics,
  fetchMyTests,
  submitAssignedTest
} from '../api/pdd'

const props = defineProps({
  session: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['profile-updated'])

const loading = ref(false)
const loadingQuestions = ref(false)
const submitting = ref(false)
const savingProfile = ref(false)

const assignedTests = ref([])
const analytics = ref(null)
const activeAssignment = ref(null)
const activeTestTitle = ref('')
const activeTestMode = ref('exam')
const activePassScore = ref(70)
const questions = ref([])
const servedQuestionIds = ref([])
const answers = ref({})
const currentIndex = ref(0)
const result = ref(null)

const profileName = ref(props.session.userName || '')

const flashType = ref('')
const flashText = ref('')

const answeredCount = computed(() => Object.keys(answers.value).length)
const totalQuestions = computed(() => questions.value.length)
const progress = computed(() => {
  if (!totalQuestions.value) return 0
  return Math.round((answeredCount.value / totalQuestions.value) * 100)
})

const activeQuestion = computed(() => questions.value[currentIndex.value] || null)

function showFlash(type, text) {
  flashType.value = type
  flashText.value = text
  setTimeout(() => {
    if (flashText.value === text) {
      flashType.value = ''
      flashText.value = ''
    }
  }, 3200)
}

function errorText(error) {
  return error?.response?.data?.detail || error?.message || 'Неизвестная ошибка'
}

async function loadAssignedTests() {
  loading.value = true
  try {
    assignedTests.value = await fetchMyTests(props.session.userId)
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    loading.value = false
  }
}

async function loadAnalytics() {
  try {
    analytics.value = await fetchMyAnalytics(props.session.userId, 100)
  } catch (error) {
    showFlash('error', errorText(error))
  }
}

async function saveProfile() {
  if (!profileName.value.trim()) {
    showFlash('error', 'Имя не может быть пустым')
    return
  }

  savingProfile.value = true
  try {
    const updated = await updateProfileName(profileName.value)
    emit('profile-updated', updated.name || '')
    showFlash('success', 'Имя сохранено')
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    savingProfile.value = false
  }
}

async function startAssignedTest(assignment) {
  loadingQuestions.value = true
  try {
    const payload = await fetchAssignedQuestions(assignment.assignment_id, props.session.userId)
    activeAssignment.value = assignment
    activeTestTitle.value = payload.test_title
    activeTestMode.value = payload.mode || assignment.mode || 'exam'
    activePassScore.value = payload.pass_score || assignment.pass_score || 70
    questions.value = payload.questions
    servedQuestionIds.value = payload.questions.map((question) => question.id)
    answers.value = {}
    currentIndex.value = 0
    result.value = null
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    loadingQuestions.value = false
  }
}

function selectAnswer(questionId, answerId) {
  answers.value = {
    ...answers.value,
    [questionId]: answerId
  }
}

function goNext() {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value += 1
  }
}

function goPrev() {
  if (currentIndex.value > 0) {
    currentIndex.value -= 1
  }
}

function exitTest() {
  activeAssignment.value = null
  activeTestTitle.value = ''
  activeTestMode.value = 'exam'
  questions.value = []
  servedQuestionIds.value = []
  answers.value = {}
  currentIndex.value = 0
}

async function submitCurrentTest() {
  if (!activeAssignment.value) return

  if (answeredCount.value !== totalQuestions.value) {
    showFlash('error', 'Ответь на все вопросы перед отправкой')
    return
  }

  submitting.value = true

  try {
    result.value = await submitAssignedTest(activeAssignment.value.assignment_id, {
      user_id: props.session.userId,
      question_ids: servedQuestionIds.value,
      answers: answers.value
    })

    showFlash('success', 'Тест успешно отправлен')
    await Promise.all([loadAssignedTests(), loadAnalytics()])
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    submitting.value = false
  }
}

function closeResult() {
  result.value = null
  exitTest()
}

onMounted(async () => {
  await Promise.all([loadAssignedTests(), loadAnalytics()])
})
</script>

<template>
  <section class="user-dashboard">
    <div v-if="flashText" class="flash" :class="flashType">
      {{ flashText }}
    </div>

    <div class="profile-panel">
      <div>
        <p class="eyebrow">Profile</p>
        <h3>{{ props.session.email }}</h3>
      </div>
      <div class="profile-controls">
        <input v-model="profileName" type="text" placeholder="Твое имя" />
        <button class="primary-btn" :disabled="savingProfile" @click="saveProfile">
          {{ savingProfile ? 'Сохранение...' : 'Сохранить имя' }}
        </button>
      </div>
    </div>

    <template v-if="!activeAssignment">
      <div class="dashboard-head">
        <div>
          <p class="eyebrow">My Tests</p>
          <h2>Назначенные тебе тесты</h2>
          <p class="subtext">Тут отображаются задания, которые тебе выдал администратор.</p>
        </div>
        <button class="secondary-btn" :disabled="loading" @click="loadAssignedTests">
          {{ loading ? 'Загрузка...' : 'Обновить' }}
        </button>
      </div>

      <div v-if="assignedTests.length === 0" class="empty-card">
        <h3>Пока нет назначенных тестов</h3>
        <p>Когда админ закрепит тест, он появится здесь автоматически.</p>
      </div>

      <div v-else class="tests-grid">
        <article v-for="assignment in assignedTests" :key="assignment.assignment_id" class="test-card">
          <div class="test-top">
            <h3>{{ assignment.title }}</h3>
            <span class="mode-badge">{{ assignment.mode === 'training' ? 'Обучение' : 'Экзамен' }}</span>
          </div>

          <p>{{ assignment.description || 'Без описания' }}</p>

          <div class="meta-grid">
            <div>
              <span>Вопросов</span>
              <strong>{{ assignment.question_limit }}</strong>
            </div>
            <div>
              <span>Попыток</span>
              <strong>
                {{ assignment.max_attempts === null ? assignment.attempts : `${assignment.attempts}/${assignment.max_attempts}` }}
              </strong>
            </div>
            <div>
              <span>Последний результат</span>
              <strong>{{ assignment.last_score === null ? '—' : assignment.last_score + '%' }}</strong>
            </div>
          </div>

          <button class="primary-btn" :disabled="loadingQuestions" @click="startAssignedTest(assignment)">
            {{ loadingQuestions ? 'Загрузка...' : 'Начать тест' }}
          </button>
        </article>
      </div>

      <article class="analytics-card" v-if="analytics">
        <h3>Моя аналитика</h3>
        <div class="analytics-kpi">
          <div>
            <span>Всего попыток</span>
            <strong>{{ analytics.summary.total_attempts }}</strong>
          </div>
          <div>
            <span>Средний балл</span>
            <strong>{{ analytics.summary.average_score }}%</strong>
          </div>
          <div>
            <span>Лучший балл</span>
            <strong>{{ analytics.summary.best_score }}%</strong>
          </div>
        </div>

        <div class="history-list">
          <div v-for="attempt in analytics.attempts.slice(0, 10)" :key="attempt.attempt_id" class="history-item">
            <div>
              <strong>{{ attempt.test_title || `Тест #${attempt.test_id}` }}</strong>
              <p>{{ attempt.mode === 'training' ? 'Обучение' : 'Экзамен' }} · попытка {{ attempt.attempt_number }}</p>
            </div>
            <div class="history-score">
              <span>{{ attempt.score }}%</span>
              <small>{{ attempt.created_at }}</small>
            </div>
          </div>
        </div>
      </article>
    </template>

    <template v-else>
      <div class="runner-head">
        <div>
          <p class="eyebrow">{{ activeTestMode === 'training' ? 'Training Mode' : 'Exam Mode' }}</p>
          <h2>{{ activeTestTitle }}</h2>
          <p class="subtext">Проходной балл: {{ activePassScore }}%</p>
        </div>
        <button class="secondary-btn" @click="exitTest">Выйти</button>
      </div>

      <div class="progress-box">
        <div class="progress-text">
          <span>Вопрос {{ currentIndex + 1 }} из {{ totalQuestions }}</span>
          <span>Отвечено {{ answeredCount }} / {{ totalQuestions }} ({{ progress }}%)</span>
        </div>
        <div class="progress-line">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
      </div>

      <article v-if="activeQuestion" class="question-card">
        <p class="question-category">{{ activeQuestion.category }}</p>
        <h3>{{ activeQuestion.question_text }}</h3>
        <img v-if="activeQuestion.image_url" :src="activeQuestion.image_url" alt="question" class="question-image" />

        <div class="answers-list">
          <button
            v-for="answer in activeQuestion.answers"
            :key="answer.id"
            class="answer-btn"
            :class="{ selected: answers[activeQuestion.id] === answer.id }"
            @click="selectAnswer(activeQuestion.id, answer.id)"
          >
            {{ answer.answer_text }}
          </button>
        </div>
      </article>

      <div class="runner-actions">
        <button class="secondary-btn" :disabled="currentIndex === 0" @click="goPrev">Назад</button>
        <button class="secondary-btn" :disabled="currentIndex === totalQuestions - 1" @click="goNext">Вперед</button>
        <button class="primary-btn" :disabled="submitting" @click="submitCurrentTest">
          {{ submitting ? 'Отправка...' : 'Завершить тест' }}
        </button>
      </div>
    </template>

    <div v-if="result" class="result-overlay" @click.self="closeResult">
      <div class="result-modal">
        <h3 :class="{ ok: result.passed, fail: !result.passed }">
          {{ result.passed ? 'Тест пройден' : 'Тест не пройден' }}
        </h3>
        <p class="score">{{ result.score }}%</p>
        <p>Правильных ответов: {{ result.correct }} из {{ result.total }}</p>
        <p>Проходной балл: {{ result.pass_score }}%</p>

        <div v-if="result.mode === 'training'" class="training-feedback">
          <h4>Разбор ошибок</h4>
          <div v-if="result.wrong_questions?.length">
            <article v-for="item in result.wrong_questions.slice(0, 6)" :key="item.question_id" class="wrong-item">
              <strong>{{ item.category }} · Вопрос #{{ item.question_id }}</strong>
              <p>{{ item.question_text }}</p>
              <p>Твой ответ: {{ item.selected_answer }}</p>
              <p>Правильный ответ: {{ item.correct_answer }}</p>
              <p v-if="item.explanation">Пояснение: {{ item.explanation }}</p>
            </article>
          </div>
          <div v-else>
            <p>Ошибок нет, отличный результат.</p>
          </div>

          <h4>Рекомендации</h4>
          <ul>
            <li v-for="(rec, index) in result.recommendations || []" :key="index">{{ rec }}</li>
          </ul>
        </div>

        <button class="primary-btn" @click="closeResult">Вернуться к тестам</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.user-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.flash {
  border-radius: 14px;
  padding: 11px 14px;
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

.profile-panel {
  border: 1px solid #dbe8eb;
  border-radius: 16px;
  padding: 14px;
  background: #ffffffde;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.profile-panel h3 {
  margin: 4px 0 0;
}

.profile-controls {
  display: flex;
  gap: 8px;
}

.profile-controls input {
  min-width: 240px;
}

.dashboard-head,
.runner-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.78rem;
  color: #0e7a85;
}

h2 {
  margin: 6px 0;
  font-size: clamp(1.3rem, 2.2vw, 2rem);
}

.subtext {
  margin: 0;
  color: #3f5e69;
}

.empty-card,
.test-card,
.question-card,
.progress-box,
.analytics-card {
  background: #ffffffde;
  border: 1px solid #dbe8eb;
  border-radius: 20px;
  padding: 18px;
}

.tests-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}

.test-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.mode-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: #e6f6f8;
  color: #10515d;
  font-size: 0.76rem;
  font-weight: 700;
}

.test-card h3 {
  margin: 0;
  font-size: 1.05rem;
}

.test-card p {
  color: #3f5c67;
  margin: 10px 0;
  min-height: 40px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.meta-grid span {
  display: block;
  font-size: 0.78rem;
  color: #4f6b75;
}

.meta-grid strong {
  font-size: 1.1rem;
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

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  border: 1px solid #dce9ec;
  border-radius: 12px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.history-item p {
  margin: 4px 0 0;
}

.history-score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.progress-text {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-weight: 600;
  color: #274955;
}

.progress-line {
  margin-top: 10px;
  height: 10px;
  border-radius: 999px;
  background: #ddebee;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #0b7480, #0a9c75);
}

.question-category {
  margin: 0;
  font-size: 0.85rem;
  color: #477884;
  font-weight: 700;
}

.question-card h3 {
  margin: 8px 0 14px;
  font-size: 1.2rem;
  line-height: 1.35;
}

.question-image {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  border: 1px solid #dae8eb;
  border-radius: 12px;
  margin-bottom: 12px;
  background: #f7fbfc;
}

.answers-list {
  display: grid;
  gap: 10px;
}

.answer-btn {
  border: 1px solid #d4e7ea;
  background: #f7fcfd;
  border-radius: 12px;
  padding: 11px 12px;
  text-align: left;
  cursor: pointer;
  font: inherit;
}

.answer-btn.selected {
  border-color: #0d7f8b;
  background: linear-gradient(140deg, #d6f7fa, #eefefd);
}

.runner-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.primary-btn,
.secondary-btn {
  border: none;
  border-radius: 12px;
  padding: 10px 14px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.primary-btn {
  background: linear-gradient(135deg, #047857, #0f9a73);
  color: white;
}

.secondary-btn {
  background: #ecf8f9;
  color: #10515d;
}

.primary-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 24, 27, 0.42);
  display: grid;
  place-items: center;
  z-index: 40;
}

.result-modal {
  width: min(760px, calc(100vw - 32px));
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: white;
  border-radius: 18px;
  padding: 22px;
}

.result-modal h3 {
  margin: 0;
}

.result-modal h3.ok {
  color: #166a3e;
}

.result-modal h3.fail {
  color: #9f2632;
}

.score {
  font-size: 2.2rem;
  margin: 10px 0;
  font-weight: 800;
}

.training-feedback {
  border: 1px solid #dce7ea;
  border-radius: 12px;
  padding: 12px;
  margin: 12px 0;
}

.wrong-item {
  border: 1px solid #e2ebed;
  border-radius: 10px;
  padding: 8px;
  margin-bottom: 8px;
}

.wrong-item p {
  margin: 4px 0;
}

@media (max-width: 768px) {
  .profile-panel,
  .profile-controls,
  .dashboard-head,
  .runner-head,
  .progress-text,
  .runner-actions {
    flex-direction: column;
  }

  .profile-controls input {
    min-width: 0;
    width: 100%;
  }

  .meta-grid,
  .analytics-kpi {
    grid-template-columns: 1fr;
  }
}
</style>
