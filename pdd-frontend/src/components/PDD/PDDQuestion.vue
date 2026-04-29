<template>
  <div class="question-card">
    <div class="question-header">
      <span class="question-number">Вопрос {{ index + 1 }} из {{ total }}</span>
      <span class="question-category">{{ question.category }}</span>
    </div>
    
    <div class="question-text">
      {{ question.question_text }}
    </div>
    
    <div class="answers-list">
      <div 
        v-for="answer in question.answers" 
        :key="answer.id"
        class="answer-item"
        :class="{ 
          'selected': selectedAnswer === answer.id,
          'correct': showResults && answer.is_correct,
          'incorrect': showResults && selectedAnswer === answer.id && !answer.is_correct
        }"
        @click="!showResults && selectAnswer(answer.id)"
      >
        <div class="answer-letter">{{ getAnswerLetter(answer.id) }}</div>
        <div class="answer-text">{{ answer.answer_text }}</div>
        <div v-if="showResults && !answer.is_correct && selectedAnswer === answer.id" class="answer-explanation">
          ❌ Неправильно
        </div>
        <div v-if="showResults && answer.is_correct && selectedAnswer === answer.id" class="answer-explanation">
          ✅ Правильно!
        </div>
        <div v-if="showResults && answer.explanation && answer.is_correct" class="answer-explanation-text">
          💡 {{ answer.explanation }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  question: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  total: {
    type: Number,
    required: true
  },
  selectedAnswer: {
    type: Number,
    default: null
  },
  showResults: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select-answer'])

const getAnswerLetter = (id) => {
  const letters = ['А', 'Б', 'В', 'Г', 'Д']
  const position = props.question.answers.findIndex(a => a.id === id)
  return letters[position] || '?'
}

const selectAnswer = (answerId) => {
  emit('select-answer', props.question.id, answerId)
}
</script>

<style scoped>
.question-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.question-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
}

.question-number {
  font-weight: bold;
  color: #1976d2;
}

.question-category {
  color: #666;
  font-size: 14px;
}

.question-text {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 20px;
  line-height: 1.4;
}

.answers-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.answer-item {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.answer-item:hover {
  background-color: #f5f5f5;
  border-color: #1976d2;
}

.answer-item.selected {
  background-color: #e3f2fd;
  border-color: #1976d2;
}

.answer-item.correct {
  background-color: #c8e6c9;
  border-color: #4caf50;
}

.answer-item.incorrect {
  background-color: #ffcdd2;
  border-color: #f44336;
}

.answer-letter {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f0f0;
  border-radius: 50%;
  font-weight: bold;
  margin-right: 12px;
  flex-shrink: 0;
}

.answer-text {
  flex: 1;
  line-height: 1.4;
}

.answer-explanation {
  width: 100%;
  margin-top: 8px;
  padding-top: 8px;
  font-size: 13px;
}

.answer-explanation-text {
  width: 100%;
  margin-top: 4px;
  padding-top: 4px;
  font-size: 12px;
  color: #666;
  border-top: 1px solid rgba(0,0,0,0.1);
}
</style>