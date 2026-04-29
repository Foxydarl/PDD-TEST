<template>
  <div class="home-page">
    <div class="container">
      <div class="header">
        <h1>🚗 Тест ПДД Республики Казахстан</h1>
        <p>Проверьте свои знания правил дорожного движения</p>
      </div>

      <!-- Выбор категории -->
      <CategorySelector 
        v-if="!testStarted"
        :categories="categories"
        @start-test="startTest"
      />

      <!-- Процесс тестирования -->
      <div v-else>
        <!-- Прогресс -->
        <div class="progress-card">
          <div class="progress-info">
            <span>Прогресс: {{ Object.keys(userAnswers).length }} из {{ questions.length }} вопросов</span>
            <span>{{ Math.round((Object.keys(userAnswers).length / questions.length) * 100) }}%</span>
          </div>
          <div class="progress-bar">
            <div 
              class="progress-fill"
              :style="{ width: (Object.keys(userAnswers).length / questions.length) * 100 + '%' }"
            ></div>
          </div>
        </div>

        <!-- Вопросы -->
        <PDDQuestion
          v-for="(question, idx) in questions"
          :key="question.id"
          :question="question"
          :index="idx"
          :total="questions.length"
          :selected-answer="userAnswers[question.id]"
          :show-results="testCompleted"
          @select-answer="handleSelectAnswer"
        />

        <!-- Кнопки -->
        <div class="text-center">
          <button 
            v-if="!testCompleted"
            class="submit-btn"
            @click="submitTest"
            :disabled="submitting"
          >
            {{ submitting ? 'Проверка...' : 'Завершить тест' }}
          </button>
          
          <button 
            v-else
            class="retry-btn"
            @click="resetTest"
          >
            Пройти еще раз
          </button>
        </div>
      </div>

      <!-- Модальное окно с результатами -->
      <div v-if="showResults" class="modal-overlay" @click.self="showResults = false">
        <div class="modal-content">
          <h2 :class="testResult?.passed ? 'text-green' : 'text-red'">
            {{ testResult?.passed ? '🎉 Поздравляем!' : '😞 К сожалению...' }}
          </h2>
          
          <div class="score-circle">
            <span>{{ testResult?.score }}%</span>
          </div>
          
          <div class="result-details">
            <p>Правильных ответов: {{ testResult?.correct }} из {{ testResult?.total }}</p>
            <p>Проходной балл: 70%</p>
          </div>
          
          <div class="modal-buttons">
            <button class="close-btn" @click="showResults = false">Закрыть</button>
            <button class="retry-modal-btn" @click="resetTest">Пройти еще раз</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import CategorySelector from '../components/PDD/CategorySelector.vue'
import PDDQuestion from '../components/PDD/PDDQuestion.vue'

const API_BASE = 'http://localhost:8080/api/pdd'

const loading = ref(false)
const submitting = ref(false)
const categories = ref([])
const testStarted = ref(false)
const testCompleted = ref(false)
const questions = ref([])
const userAnswers = ref({})
const testResult = ref(null)
const showResults = ref(false)

const loadCategories = async () => {
  try {
    const response = await axios.get(`${API_BASE}/categories`)
    categories.value = ['all', ...response.data.categories]
  } catch (error) {
    console.error('Ошибка загрузки категорий:', error)
    categories.value = ['all', 'общие положения', 'скоростной режим', 'обгон и опережение']
  }
}

const startTest = async (category) => {
  loading.value = true
  testStarted.value = true
  userAnswers.value = {}
  testCompleted.value = false
  
  try {
    const response = await axios.get(`${API_BASE}/questions/${category}?limit=20`)
    questions.value = response.data.questions
    console.log('Загружено вопросов:', questions.value.length)
  } catch (error) {
    console.error('Ошибка загрузки вопросов:', error)
    alert('Не удалось загрузить вопросы. Убедитесь, что бэкенд запущен.')
    testStarted.value = false
  } finally {
    loading.value = false
  }
}

const handleSelectAnswer = (questionId, answerId) => {
  userAnswers.value = { ...userAnswers.value, [questionId]: answerId }
}

const submitTest = async () => {
  if (Object.keys(userAnswers.value).length !== questions.value.length) {
    alert(`Вы ответили только на ${Object.keys(userAnswers.value).length} из ${questions.value.length} вопросов. Ответьте на все вопросы!`)
    return
  }
  
  submitting.value = true
  
  try {
    const userId = localStorage.getItem('userId') || 'anonymous'
    const submission = {
      user_id: userId,
      category: 'all',
      answers: userAnswers.value
    }
    
    const response = await axios.post(`${API_BASE}/test/submit`, submission)
    testResult.value = response.data
    testCompleted.value = true
    showResults.value = true
  } catch (error) {
    console.error('Ошибка при проверке теста:', error)
    alert('Ошибка при проверке теста')
  } finally {
    submitting.value = false
  }
}

const resetTest = () => {
  testStarted.value = false
  testCompleted.value = false
  questions.value = []
  userAnswers.value = {}
  testResult.value = null
  showResults.value = false
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
  padding: 24px;
}

.header {
  text-align: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 8px;
}

.header p {
  color: #666;
}

.progress-card {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-bar {
  background-color: #e0e0e0;
  border-radius: 10px;
  height: 10px;
  overflow: hidden;
}

.progress-fill {
  background-color: #1976d2;
  height: 100%;
  transition: width 0.3s;
  border-radius: 10px;
}

.submit-btn, .retry-btn {
  background-color: #1976d2;
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover, .retry-btn:hover {
  background-color: #1565c0;
}

.submit-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.text-center {
  text-align: center;
  margin-top: 24px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 16px;
  padding: 32px;
  max-width: 400px;
  text-align: center;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 20px auto;
}

.score-circle span {
  font-size: 32px;
  font-weight: bold;
}

.result-details {
  margin: 20px 0;
}

.modal-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 20px;
}

.close-btn, .retry-modal-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.close-btn {
  background-color: #ccc;
}

.retry-modal-btn {
  background-color: #1976d2;
  color: white;
}

.text-green {
  color: #2e7d32;
}

.text-red {
  color: #c62828;
}
</style>