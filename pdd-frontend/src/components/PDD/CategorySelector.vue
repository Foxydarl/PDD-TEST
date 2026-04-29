<template>
  <div class="category-selector">
    <h2 class="title">Выберите категорию теста</h2>
    
    <div class="categories-grid">
      <div 
        v-for="cat in categories" 
        :key="cat"
        class="category-card"
        :class="{ 'selected': selectedCategory === cat }"
        @click="selectCategory(cat)"
      >
        <div class="category-icon">
          <span v-if="cat === 'all'">📚</span>
          <span v-else-if="cat === 'общие положения'">📖</span>
          <span v-else-if="cat === 'дорожные знаки'">🛑</span>
          <span v-else-if="cat === 'скоростной режим'">🏎️</span>
          <span v-else-if="cat === 'обгон и опережение'">🔄</span>
          <span v-else>🚗</span>
        </div>
        <div class="category-name">{{ cat === 'all' ? 'Все категории' : cat }}</div>
      </div>
    </div>

    <div class="text-center">
      <button 
        class="start-btn"
        :disabled="!selectedCategory"
        @click="startTest"
      >
        Начать тест (20 вопросов)
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  categories: {
    type: Array,
    default: () => ['all', 'общие положения', 'дорожные знаки', 'скоростной режим', 'обгон и опережение']
  }
})

const emit = defineEmits(['start-test'])

const selectedCategory = ref(null)

const selectCategory = (category) => {
  selectedCategory.value = category
}

const startTest = () => {
  if (selectedCategory.value) {
    emit('start-test', selectedCategory.value)
  }
}
</script>

<style scoped>
.category-selector {
  text-align: center;
}

.title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 24px;
  color: #333;
}

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  max-width: 800px;
  margin: 0 auto 32px;
}

.category-card {
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.category-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.category-card.selected {
  border-color: #1976d2;
  background-color: #e3f2fd;
}

.category-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.category-name {
  font-size: 16px;
  font-weight: 500;
}

.start-btn {
  background-color: #1976d2;
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.3s;
}

.start-btn:hover:not(:disabled) {
  background-color: #1565c0;
}

.start-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.text-center {
  text-align: center;
}
</style>