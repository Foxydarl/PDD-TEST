<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { updateProfileName } from '../api/auth'
import {
  fetchAssignedQuestions,
  fetchGeneralTrainingQuestions,
  fetchMyAnalytics,
  fetchMyTests,
  fetchPublicCategories,
  submitAssignedTest
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

const emit = defineEmits(['profile-updated'])
const CONTENT_LANGUAGES = ['ru', 'en', 'kk']

const loading = ref(false)
const loadingQuestions = ref(false)
const submitting = ref(false)
const savingProfile = ref(false)
const loadingGeneralCategories = ref(false)
const startingGeneralTraining = ref(false)

const assignedTests = ref([])
const analytics = ref(null)
const activeAssignment = ref(null)
const generalTrainingActive = ref(false)
const activeTestTitle = ref('')
const activeTestMode = ref('exam')
const activeTestLanguage = ref('ru')
const activePassScore = ref(70)
const questions = ref([])
const servedQuestionIds = ref([])
const answers = ref({})
const currentIndex = ref(0)
const result = ref(null)

const generalCategories = ref([])
const generalConfig = ref({
  questionLimit: 20,
  useAllCategories: true,
  selectedCategories: [],
  language: props.language || 'ru'
})
const instantFeedbackByQuestion = ref({})

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
const activeFeedback = computed(() => {
  const questionId = activeQuestion.value?.id
  if (!questionId) return null
  return instantFeedbackByQuestion.value[questionId] || null
})

const hasActiveRunner = computed(() => Boolean(activeAssignment.value) || generalTrainingActive.value)
const languageTick = computed(() => props.language)
const contentLanguageOptions = computed(() =>
  CONTENT_LANGUAGES.map((value) => ({
    value,
    label: contentLanguageLabel(value)
  }))
)

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
  return error?.response?.data?.detail || error?.message || props.t('common.unknownError')
}

function modeLabel(mode) {
  return mode === 'training' ? props.t('mode.training') : props.t('mode.exam')
}

function contentLanguageLabel(language) {
  const normalized = (language || 'ru').toString().toLowerCase()
  return props.t(`contentLanguage.${normalized}`)
}

function resetRunnerState() {
  activeAssignment.value = null
  generalTrainingActive.value = false
  activeTestTitle.value = ''
  activeTestMode.value = 'exam'
  activeTestLanguage.value = 'ru'
  activePassScore.value = 70
  questions.value = []
  servedQuestionIds.value = []
  answers.value = {}
  instantFeedbackByQuestion.value = {}
  currentIndex.value = 0
}

function buildCategoryStats(rows) {
  const grouped = {}
  rows.forEach((row) => {
    if (!grouped[row.category]) {
      grouped[row.category] = { category: row.category, total: 0, correct: 0, wrong: 0 }
    }

    grouped[row.category].total += 1
    if (row.is_correct) {
      grouped[row.category].correct += 1
    } else {
      grouped[row.category].wrong += 1
    }
  })

  return Object.values(grouped)
    .map((item) => ({
      ...item,
      error_rate: item.total ? Number(((item.wrong / item.total) * 100).toFixed(1)) : 0
    }))
    .sort((a, b) => b.wrong - a.wrong)
}

function buildTrainingRecommendations(categoryStats, wrongQuestions) {
  if (!wrongQuestions.length) {
    return [props.t('user.result.noErrors')]
  }

  const tips = []
  const worst = categoryStats.filter((item) => item.wrong > 0)
  if (worst.length > 0) {
    tips.push(`${modeLabel('training')}: ${worst[0].category} (${worst[0].wrong})`)
  }
  if (worst.length > 1) {
    tips.push(`${modeLabel('training')}: ${worst[1].category} (${worst[1].wrong})`)
  }

  return tips
}

function resolveAnswerVisual(answer) {
  const question = activeQuestion.value
  if (!question) return {}

  const selectedAnswerId = answers.value[question.id]
  const isSelected = selectedAnswerId === answer.id

  if (!generalTrainingActive.value) {
    return { selected: isSelected }
  }

  if (!selectedAnswerId) {
    return { selected: isSelected }
  }

  const feedback = instantFeedbackByQuestion.value[question.id]
  return {
    selected: isSelected,
    correctHighlight: Boolean(answer.is_correct),
    wrongHighlight: isSelected && feedback && !feedback.isCorrect
  }
}

function toggleGeneralCategory(category) {
  if (!category) return

  if (generalConfig.value.useAllCategories) {
    return
  }

  if (generalConfig.value.selectedCategories.includes(category)) {
    generalConfig.value.selectedCategories = generalConfig.value.selectedCategories.filter((item) => item !== category)
  } else {
    generalConfig.value.selectedCategories = [...generalConfig.value.selectedCategories, category]
  }
}

function toggleAllCategories() {
  generalConfig.value.useAllCategories = !generalConfig.value.useAllCategories
  if (generalConfig.value.useAllCategories) {
    generalConfig.value.selectedCategories = []
  }
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

async function loadGeneralCategories() {
  loadingGeneralCategories.value = true
  try {
    generalCategories.value = await fetchPublicCategories(generalConfig.value.language)
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    loadingGeneralCategories.value = false
  }
}

async function saveProfile() {
  if (!profileName.value.trim()) {
    showFlash('error', props.t('user.nameEmpty'))
    return
  }

  savingProfile.value = true
  try {
    const updated = await updateProfileName(profileName.value)
    emit('profile-updated', updated.name || '')
    showFlash('success', props.t('user.nameSaved'))
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
    generalTrainingActive.value = false
    activeTestTitle.value = payload.test_title
    activeTestMode.value = payload.mode || assignment.mode || 'exam'
    activeTestLanguage.value = payload.language || assignment.language || 'ru'
    activePassScore.value = payload.pass_score || assignment.pass_score || 70
    questions.value = payload.questions
    servedQuestionIds.value = payload.questions.map((question) => question.id)
    answers.value = {}
    instantFeedbackByQuestion.value = {}
    currentIndex.value = 0
    result.value = null
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    loadingQuestions.value = false
  }
}

async function startGeneralTraining() {
  if (!generalConfig.value.useAllCategories && generalConfig.value.selectedCategories.length === 0) {
    showFlash('error', props.t('user.training.general.needCategory'))
    return
  }

  startingGeneralTraining.value = true

  try {
    const payload = await fetchGeneralTrainingQuestions({
      limit: Number(generalConfig.value.questionLimit) || 20,
      categories: generalConfig.value.useAllCategories ? [] : generalConfig.value.selectedCategories,
      language: generalConfig.value.language
    })

    const pickedQuestions = payload.questions || []
    if (pickedQuestions.length === 0) {
      showFlash('error', props.t('user.training.general.emptyQuestions'))
      return
    }

    activeAssignment.value = null
    generalTrainingActive.value = true
    activeTestTitle.value = props.t('user.training.general.title')
    activeTestMode.value = 'training'
    activeTestLanguage.value = generalConfig.value.language || 'ru'
    activePassScore.value = 70
    questions.value = pickedQuestions
    servedQuestionIds.value = pickedQuestions.map((question) => question.id)
    answers.value = {}
    instantFeedbackByQuestion.value = {}
    currentIndex.value = 0
    result.value = null
  } catch (error) {
    showFlash('error', errorText(error))
  } finally {
    startingGeneralTraining.value = false
  }
}

function selectAnswer(questionId, answerId) {
  answers.value = {
    ...answers.value,
    [questionId]: answerId
  }

  if (!generalTrainingActive.value) {
    return
  }

  const currentQuestion = questions.value.find((question) => question.id === questionId)
  if (!currentQuestion) return

  const selectedAnswer = currentQuestion.answers.find((answer) => answer.id === answerId)
  const correctAnswer = currentQuestion.answers.find((answer) => answer.is_correct)

  instantFeedbackByQuestion.value = {
    ...instantFeedbackByQuestion.value,
    [questionId]: {
      isCorrect: Boolean(selectedAnswer?.is_correct),
      correctAnswer: correctAnswer?.answer_text || '',
      explanation: correctAnswer?.explanation || ''
    }
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
  resetRunnerState()
}

async function submitCurrentTest() {
  if (answeredCount.value !== totalQuestions.value) {
    showFlash('error', props.t('user.tests.completeAll'))
    return
  }

  if (generalTrainingActive.value) {
    const rows = []
    const wrongQuestions = []
    let correctCount = 0

    questions.value.forEach((question) => {
      const selectedAnswerId = answers.value[question.id]
      const selectedAnswer = question.answers.find((answer) => answer.id === selectedAnswerId)
      const correctAnswer = question.answers.find((answer) => answer.is_correct)
      const isCorrect = Boolean(selectedAnswer?.is_correct)

      if (isCorrect) {
        correctCount += 1
      } else {
        wrongQuestions.push({
          question_id: question.id,
          question_text: question.question_text,
          category: question.category,
          selected_answer: selectedAnswer?.answer_text || props.t('user.training.general.chooseAnswer'),
          correct_answer: correctAnswer?.answer_text || '',
          explanation: correctAnswer?.explanation || ''
        })
      }

      rows.push({
        question_id: question.id,
        category: question.category,
        is_correct: isCorrect
      })
    })

    const total = rows.length
    const wrong = total - correctCount
    const score = total > 0 ? Math.round((correctCount / total) * 100) : 0
    const passScore = 70

    const categoryStats = buildCategoryStats(rows)
    const recommendations = buildTrainingRecommendations(categoryStats, wrongQuestions)

    result.value = {
      total,
      correct: correctCount,
      wrong,
      score,
      pass_score: passScore,
      passed: score >= passScore,
      mode: 'training',
      category_stats: categoryStats,
      wrong_questions: wrongQuestions,
      recommendations
    }
    return
  }

  if (!activeAssignment.value) return

  submitting.value = true

  try {
    result.value = await submitAssignedTest(activeAssignment.value.assignment_id, {
      user_id: props.session.userId,
      question_ids: servedQuestionIds.value,
      answers: answers.value
    })

    showFlash('success', props.t('user.tests.sent'))
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

watch(
  () => generalConfig.value.language,
  async (nextLanguage, prevLanguage) => {
    if (!nextLanguage || nextLanguage === prevLanguage) return
    generalConfig.value.selectedCategories = []
    await loadGeneralCategories()
  }
)

onMounted(async () => {
  await Promise.all([loadAssignedTests(), loadAnalytics(), loadGeneralCategories()])
})
</script>

<template>
  <section class="user-dashboard" :data-language="languageTick">
    <div v-if="flashText" class="flash" :class="flashType">
      {{ flashText }}
    </div>

    <div class="profile-panel">
      <div>
        <p class="eyebrow">{{ props.t('user.profile') }}</p>
        <h3>{{ props.session.email }}</h3>
      </div>
      <div class="profile-controls">
        <input v-model="profileName" type="text" :placeholder="props.t('user.namePlaceholder')" />
        <button class="primary-btn" :disabled="savingProfile" @click="saveProfile">
          {{ savingProfile ? props.t('user.nameSaving') : props.t('user.nameSave') }}
        </button>
      </div>
    </div>

    <template v-if="!hasActiveRunner">
      <article class="training-card">
        <div>
          <p class="eyebrow">{{ props.t('mode.training') }}</p>
          <h3>{{ props.t('user.training.general.title') }}</h3>
          <p class="subtext">{{ props.t('user.training.general.subtitle') }}</p>
        </div>

        <div class="training-config-grid">
          <div class="training-controls-column">
            <label>
              <span>{{ props.t('user.training.general.questionsCount') }}</span>
              <input v-model.number="generalConfig.questionLimit" type="number" min="5" max="100" />
            </label>

            <label>
              <span>{{ props.t('user.training.general.language') }}</span>
              <select v-model="generalConfig.language">
                <option v-for="option in contentLanguageOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>

          <div class="categories-box">
            <p>{{ props.t('user.training.general.categories') }}</p>

            <label class="inline-check">
              <input type="checkbox" :checked="generalConfig.useAllCategories" @change="toggleAllCategories" />
              <span>{{ props.t('user.training.general.allCategories') }}</span>
            </label>

            <p v-if="loadingGeneralCategories" class="subtext">{{ props.t('common.loading') }}</p>
            <p v-else-if="generalCategories.length === 0" class="subtext">{{ props.t('user.training.general.noCategories') }}</p>
            <div v-else class="category-list" :class="{ disabled: generalConfig.useAllCategories }">
              <label v-for="category in generalCategories" :key="category" class="inline-check">
                <input
                  type="checkbox"
                  :checked="generalConfig.selectedCategories.includes(category)"
                  :disabled="generalConfig.useAllCategories"
                  @change="toggleGeneralCategory(category)"
                />
                <span>{{ category }}</span>
              </label>
            </div>

            <small v-if="!generalConfig.useAllCategories">{{ props.t('user.training.general.pickCategories') }}</small>
          </div>
        </div>

        <button class="primary-btn" :disabled="startingGeneralTraining" @click="startGeneralTraining">
          {{ startingGeneralTraining ? props.t('user.training.general.starting') : props.t('user.training.general.start') }}
        </button>
      </article>

      <div class="dashboard-head">
        <div>
          <p class="eyebrow">{{ props.t('user.tests.my') }}</p>
          <h2>{{ props.t('user.tests.assignedTitle') }}</h2>
          <p class="subtext">{{ props.t('user.tests.assignedSubtitle') }}</p>
        </div>
        <button class="secondary-btn" :disabled="loading" @click="loadAssignedTests">
          {{ loading ? props.t('common.loading') : props.t('user.tests.refresh') }}
        </button>
      </div>

      <div v-if="assignedTests.length === 0" class="empty-card">
        <h3>{{ props.t('user.tests.noneTitle') }}</h3>
        <p>{{ props.t('user.tests.noneSubtitle') }}</p>
      </div>

      <div v-else class="tests-grid">
        <article v-for="assignment in assignedTests" :key="assignment.assignment_id" class="test-card">
          <div class="test-top">
            <h3>{{ assignment.title }}</h3>
            <div class="test-badges">
              <span class="mode-badge">{{ modeLabel(assignment.mode) }}</span>
              <span class="mode-badge language">{{ contentLanguageLabel(assignment.language) }}</span>
            </div>
          </div>

          <p>{{ assignment.description || props.t('user.tests.noDescription') }}</p>

          <div class="meta-grid">
            <div>
              <span>{{ props.t('user.tests.questions') }}</span>
              <strong>{{ assignment.question_limit }}</strong>
            </div>
            <div>
              <span>{{ props.t('user.tests.attempts') }}</span>
              <strong>
                {{ assignment.max_attempts === null ? assignment.attempts : `${assignment.attempts}/${assignment.max_attempts}` }}
              </strong>
            </div>
            <div>
              <span>{{ props.t('user.tests.lastScore') }}</span>
              <strong>{{ assignment.last_score === null ? '—' : assignment.last_score + '%' }}</strong>
            </div>
          </div>

          <button class="primary-btn" :disabled="loadingQuestions" @click="startAssignedTest(assignment)">
            {{ loadingQuestions ? props.t('common.loading') : props.t('user.tests.start') }}
          </button>
        </article>
      </div>

      <article class="analytics-card" v-if="analytics">
        <h3>{{ props.t('user.analytics.title') }}</h3>
        <div class="analytics-kpi">
          <div>
            <span>{{ props.t('user.analytics.totalAttempts') }}</span>
            <strong>{{ analytics.summary.total_attempts }}</strong>
          </div>
          <div>
            <span>{{ props.t('user.analytics.average') }}</span>
            <strong>{{ analytics.summary.average_score }}%</strong>
          </div>
          <div>
            <span>{{ props.t('user.analytics.best') }}</span>
            <strong>{{ analytics.summary.best_score }}%</strong>
          </div>
        </div>

        <div class="history-list">
          <div v-for="attempt in analytics.attempts.slice(0, 10)" :key="attempt.attempt_id" class="history-item">
            <div>
              <strong>{{ attempt.test_title || `#${attempt.test_id}` }}</strong>
              <p>{{ modeLabel(attempt.mode) }} · {{ props.t('admin.assign.attempt', { n: attempt.attempt_number }) }}</p>
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
          <p class="eyebrow">{{ modeLabel(activeTestMode) }}</p>
          <h2>{{ activeTestTitle }}</h2>
          <p class="subtext">{{ props.t('user.runner.testLanguage', { language: contentLanguageLabel(activeTestLanguage) }) }}</p>
          <p class="subtext">{{ props.t('user.runner.passScore', { score: activePassScore }) }}</p>
        </div>
        <button class="secondary-btn" @click="exitTest">{{ props.t('common.exit') }}</button>
      </div>

      <div class="progress-box">
        <div class="progress-text">
          <span>{{ props.t('user.runner.questionProgress', { current: currentIndex + 1, total: totalQuestions }) }}</span>
          <span>{{ props.t('user.runner.answerProgress', { answered: answeredCount, total: totalQuestions, progress }) }}</span>
        </div>
        <div class="progress-line">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
      </div>

      <article v-if="activeQuestion" class="question-card">
        <p class="question-category">{{ activeQuestion.category }} · {{ contentLanguageLabel(activeQuestion.language) }}</p>
        <h3>{{ activeQuestion.question_text }}</h3>
        <img v-if="activeQuestion.image_url" :src="activeQuestion.image_url" alt="question" class="question-image" />

        <div class="answers-list">
          <button
            v-for="answer in activeQuestion.answers"
            :key="answer.id"
            class="answer-btn"
            :class="resolveAnswerVisual(answer)"
            @click="selectAnswer(activeQuestion.id, answer.id)"
          >
            {{ answer.answer_text }}
          </button>
        </div>

        <div v-if="generalTrainingActive && activeFeedback" class="instant-feedback" :class="{ ok: activeFeedback.isCorrect, fail: !activeFeedback.isCorrect }">
          <strong>{{ activeFeedback.isCorrect ? props.t('user.training.general.correct') : props.t('user.training.general.wrong') }}</strong>
          <p v-if="!activeFeedback.isCorrect">{{ props.t('user.training.general.correctHint', { answer: activeFeedback.correctAnswer }) }}</p>
          <p v-if="!activeFeedback.isCorrect && activeFeedback.explanation">
            {{ props.t('user.result.explanation', { text: activeFeedback.explanation }) }}
          </p>
        </div>
      </article>

      <div class="runner-actions">
        <button class="secondary-btn" :disabled="currentIndex === 0" @click="goPrev">{{ props.t('common.back') }}</button>
        <button class="secondary-btn" :disabled="currentIndex === totalQuestions - 1" @click="goNext">{{ props.t('common.next') }}</button>
        <button class="primary-btn" :disabled="submitting" @click="submitCurrentTest">
          {{
            generalTrainingActive
              ? props.t('user.training.general.finish')
              : submitting
                ? props.t('user.runner.submitting')
                : props.t('user.runner.submit')
          }}
        </button>
      </div>
    </template>

    <div v-if="result" class="result-overlay" @click.self="closeResult">
      <div class="result-modal">
        <h3 :class="{ ok: result.passed, fail: !result.passed }">
          {{ generalTrainingActive ? props.t('user.training.general.resultTitle') : result.passed ? props.t('user.result.passed') : props.t('user.result.failed') }}
        </h3>
        <p class="score">{{ result.score }}%</p>
        <p>{{ props.t('user.result.correct', { correct: result.correct, total: result.total }) }}</p>
        <p>{{ props.t('user.result.passScore', { score: result.pass_score }) }}</p>

        <div v-if="result.mode === 'training'" class="training-feedback">
          <h4>{{ props.t('user.result.errorReview') }}</h4>
          <div v-if="result.wrong_questions?.length">
            <article v-for="item in result.wrong_questions.slice(0, 6)" :key="item.question_id" class="wrong-item">
              <strong>{{ props.t('user.result.questionLabel', { category: item.category, id: item.question_id }) }}</strong>
              <p>{{ item.question_text }}</p>
              <p>{{ props.t('user.result.yourAnswer', { answer: item.selected_answer }) }}</p>
              <p>{{ props.t('user.result.correctAnswer', { answer: item.correct_answer }) }}</p>
              <p v-if="item.explanation">{{ props.t('user.result.explanation', { text: item.explanation }) }}</p>
            </article>
          </div>
          <div v-else>
            <p>{{ props.t('user.result.noErrors') }}</p>
          </div>

          <h4>{{ props.t('user.result.recommendations') }}</h4>
          <ul>
            <li v-for="(rec, index) in result.recommendations || []" :key="index">{{ rec }}</li>
          </ul>
        </div>

        <button class="primary-btn" @click="closeResult">{{ props.t('user.result.backToTests') }}</button>
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
  border: 1px solid transparent;
}

.flash.success {
  background: #dff7e7;
  border-color: #bfe8cb;
  color: #0d6735;
}

.flash.error {
  background: #ffe3e3;
  border-color: #f2c3c9;
  color: #9f1f2d;
}

.profile-panel {
  border: 1px solid #d5e7eb;
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.84);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  box-shadow: 0 10px 24px rgba(12, 42, 51, 0.08);
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

.training-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #d4e7ea;
  border-radius: 20px;
  padding: 18px;
  box-shadow: 0 12px 28px rgba(11, 44, 53, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.training-card h3 {
  margin: 6px 0;
  font-size: 1.32rem;
}

.training-config-grid {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 12px;
}

.training-controls-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.training-config-grid label,
.categories-box {
  border: 1px solid #dbe8eb;
  border-radius: 12px;
  padding: 10px;
  background: #f8fcfd;
}

.training-config-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.training-config-grid span,
.categories-box p {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #2f5159;
  text-transform: uppercase;
}

.category-list {
  margin-top: 8px;
  max-height: 140px;
  overflow: auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 6px;
}

.category-list.disabled {
  opacity: 0.6;
}

.inline-check {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}

.categories-box small {
  display: block;
  margin-top: 8px;
  color: #4c6772;
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
  letter-spacing: 0.15em;
  font-size: 0.76rem;
  color: #0e7a85;
  font-weight: 800;
}

h2 {
  margin: 6px 0;
  font-size: clamp(1.35rem, 2.3vw, 2.15rem);
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
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #d4e6ea;
  border-radius: 20px;
  padding: 18px;
  box-shadow: 0 12px 28px rgba(11, 44, 53, 0.08);
}

.tests-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}

.test-card {
  transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
}

.test-card:hover {
  transform: translateY(-2px);
  border-color: #b9d7dd;
  box-shadow: 0 18px 28px rgba(13, 53, 62, 0.12);
}

.test-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.test-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.mode-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: #e6f6f8;
  color: #10515d;
  font-size: 0.76rem;
  font-weight: 700;
}

.mode-badge.language {
  background: #edf1ff;
  color: #31457d;
}

.test-card h3 {
  margin: 0;
  font-size: 1.07rem;
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

.meta-grid div {
  border: 1px solid #dbe8eb;
  border-radius: 11px;
  padding: 8px;
  background: #f8fcfd;
}

.meta-grid span {
  display: block;
  font-size: 0.76rem;
  color: #4f6b75;
}

.meta-grid strong {
  font-size: 1.08rem;
}

.analytics-kpi {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.analytics-kpi div {
  border: 1px solid #dce7ea;
  border-radius: 12px;
  padding: 8px;
  background: #f8fcfd;
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
  background: #fcffff;
}

.history-item p {
  margin: 4px 0 0;
}

.history-score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.progress-box {
  border-radius: 18px;
}

.progress-text {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-weight: 700;
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
  box-shadow: 0 0 18px rgba(12, 156, 117, 0.35);
}

.question-card {
  border-radius: 22px;
}

.question-category {
  margin: 0;
  font-size: 0.84rem;
  color: #477884;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.question-card h3 {
  margin: 8px 0 14px;
  font-size: 1.24rem;
  line-height: 1.35;
}

.question-image {
  width: 100%;
  max-height: 300px;
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
  border-radius: 13px;
  padding: 11px 12px;
  text-align: left;
  cursor: pointer;
  font: inherit;
}

.answer-btn:hover {
  border-color: #92c6ce;
  transform: translateY(-1px);
}

.answer-btn.selected {
  border-color: #0d7f8b;
  background: linear-gradient(140deg, #d6f7fa, #eefefd);
  box-shadow: 0 10px 20px rgba(13, 127, 139, 0.18);
}

.answer-btn.correctHighlight {
  border-color: #1f9e63;
  background: #edfdf4;
}

.answer-btn.wrongHighlight {
  border-color: #c14056;
  background: #fff1f3;
}

.instant-feedback {
  margin-top: 12px;
  border: 1px solid #d4e7ea;
  border-radius: 12px;
  padding: 10px;
}

.instant-feedback.ok {
  border-color: #bde4ca;
  background: #f1fbf5;
  color: #13663a;
}

.instant-feedback.fail {
  border-color: #f1c9d0;
  background: #fff7f8;
  color: #8f2231;
}

.instant-feedback p {
  margin: 6px 0 0;
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
  box-shadow: 0 10px 22px rgba(4, 120, 87, 0.24);
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.secondary-btn {
  background: #ecf8f9;
  color: #10515d;
}

.secondary-btn:hover:not(:disabled) {
  background: #def0f3;
}

.primary-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-overlay {
  position: fixed;
  inset: 0;
  background: rgba(9, 24, 27, 0.48);
  display: grid;
  place-items: center;
  z-index: 40;
  backdrop-filter: blur(2px);
}

.result-modal {
  width: min(760px, calc(100vw - 32px));
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: white;
  border-radius: 20px;
  padding: 22px;
  border: 1px solid #d8e8eb;
  box-shadow: 0 20px 38px rgba(8, 31, 39, 0.25);
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
  font-size: 2.25rem;
  margin: 10px 0;
  font-weight: 800;
}

.training-feedback {
  border: 1px solid #dce7ea;
  border-radius: 12px;
  padding: 12px;
  margin: 12px 0;
  background: #f9fcfd;
}

.wrong-item {
  border: 1px solid #e2ebed;
  border-radius: 10px;
  padding: 8px;
  margin-bottom: 8px;
  background: white;
}

.wrong-item p {
  margin: 4px 0;
}

@media (max-width: 900px) {
  .training-config-grid {
    grid-template-columns: 1fr;
  }

  .category-list {
    grid-template-columns: 1fr;
  }
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
