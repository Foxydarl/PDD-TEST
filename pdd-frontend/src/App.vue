<script setup>
import { computed, onMounted, ref } from 'vue'
import { login, register } from './api/auth'
import { adminLogin } from './api/pdd'
import { pb } from './lib/pocketbase'
import AdminDashboard from './views/AdminDashboard.vue'
import UserDashboard from './views/UserDashboard.vue'

const ADMIN_STORAGE_KEY = 'pdd_admin_session'

const authMode = ref('login')
const name = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const authError = ref('')

const session = ref(null)

const isAuthenticated = computed(() => Boolean(session.value))
const roleLabel = computed(() => (session.value?.role === 'admin' ? 'Администратор' : 'Пользователь'))

function createUserSession() {
  if (!pb.authStore.isValid || !pb.authStore.model) {
    return null
  }

  return {
    role: 'user',
    userId: pb.authStore.model.id,
    email: pb.authStore.model.email,
    userName: pb.authStore.model.name || '',
    token: null
  }
}

function hydrateSession() {
  const savedAdmin = localStorage.getItem(ADMIN_STORAGE_KEY)
  if (savedAdmin) {
    try {
      session.value = JSON.parse(savedAdmin)
      return
    } catch (error) {
      localStorage.removeItem(ADMIN_STORAGE_KEY)
    }
  }

  session.value = createUserSession()
}

function extractErrorMessage(error, fallback) {
  return (
    error?.response?.data?.message ||
    error?.response?.data?.detail ||
    error?.message ||
    fallback
  )
}

async function handleAuth() {
  authError.value = ''
  loading.value = true

  try {
    if (authMode.value === 'register') {
      if (!name.value.trim()) {
        authError.value = 'Введите имя для регистрации'
        return
      }

      await register(email.value.trim(), password.value, name.value)
      await login(email.value.trim(), password.value)
      session.value = createUserSession()
      name.value = ''
      email.value = ''
      password.value = ''
      return
    }

    try {
      const admin = await adminLogin(email.value.trim(), password.value)
      session.value = {
        role: 'admin',
        userId: 'admin',
        email: admin.email,
        token: admin.token
      }
      localStorage.setItem(ADMIN_STORAGE_KEY, JSON.stringify(session.value))
      email.value = ''
      password.value = ''
      return
    } catch (adminError) {
      await login(email.value.trim(), password.value)
      session.value = createUserSession()
      name.value = ''
      email.value = ''
      password.value = ''
    }
  } catch (error) {
    authError.value = extractErrorMessage(error, 'Ошибка авторизации')
  } finally {
    loading.value = false
  }
}

function logout() {
  localStorage.removeItem(ADMIN_STORAGE_KEY)

  if (session.value?.role !== 'admin') {
    pb.authStore.clear()
  }

  session.value = null
}

function handleProfileUpdated(newName) {
  if (!session.value) return
  session.value = {
    ...session.value,
    userName: newName
  }
}

onMounted(() => {
  hydrateSession()
})
</script>

<template>
  <div class="root-bg"></div>

  <section v-if="!isAuthenticated" class="auth-layout">
    <article class="auth-side">
      <p class="eyebrow">PDD Platform</p>
      <h1>Интеллектуальная система тестов</h1>
      <p>
        Удобное пространство, где администратор создает персональные тесты, а пользователи проходят только назначенные задания.
      </p>
      <ul>
        <li>Кастомные наборы вопросов</li>
        <li>Назначение тестов по пользователям</li>
        <li>Контроль прохождения и результатов</li>
      </ul>
    </article>

    <article class="auth-card">
      <div class="auth-switch">
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">Вход</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">Регистрация</button>
      </div>

      <h2>{{ authMode === 'login' ? 'Вход в систему' : 'Создание аккаунта' }}</h2>

      <label v-if="authMode === 'register'">
        <span>Имя</span>
        <input v-model="name" type="text" placeholder="Твое имя" autocomplete="name" />
      </label>

      <label>
        <span>Email</span>
        <input v-model="email" type="email" placeholder="you@example.com" autocomplete="email" />
      </label>

      <label>
        <span>Пароль</span>
        <input v-model="password" type="password" placeholder="********" autocomplete="current-password" />
      </label>

      <p v-if="authError" class="auth-error">{{ authError }}</p>

      <button class="auth-submit" :disabled="loading" @click="handleAuth">
        {{ loading ? 'Подожди...' : authMode === 'login' ? 'Войти' : 'Зарегистрироваться' }}
      </button>
    </article>
  </section>

  <section v-else class="app-shell">
    <header class="shell-header">
      <div>
        <p class="eyebrow">PDD Dashboard</p>
        <h1>{{ roleLabel }}</h1>
      </div>

      <div class="shell-user">
        <p>{{ session.userName ? `${session.userName} — ${session.email}` : session.email }}</p>
        <button class="logout-btn" @click="logout">Выйти</button>
      </div>
    </header>

    <main class="shell-content">
      <AdminDashboard v-if="session.role === 'admin'" :session="session" />
      <UserDashboard v-else :session="session" @profile-updated="handleProfileUpdated" />
    </main>
  </section>
</template>

<style scoped>
.root-bg {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 15% 15%, rgba(16, 159, 170, 0.24), transparent 35%),
    radial-gradient(circle at 85% 10%, rgba(17, 120, 91, 0.22), transparent 32%),
    radial-gradient(circle at 75% 80%, rgba(12, 110, 121, 0.18), transparent 42%),
    linear-gradient(130deg, #f2f9fb 0%, #e8f3f4 45%, #edf9f5 100%);
  z-index: -1;
}

.auth-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 440px;
  gap: 22px;
  align-items: center;
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px;
}

.auth-side {
  background: linear-gradient(145deg, rgba(4, 73, 83, 0.93), rgba(4, 99, 82, 0.9));
  color: #ecfffd;
  border-radius: 28px;
  padding: 34px;
  box-shadow: 0 14px 40px rgba(2, 34, 40, 0.22);
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.78rem;
  font-weight: 800;
}

.auth-side h1 {
  margin: 12px 0;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.1;
}

.auth-side p {
  margin: 0;
  color: #d6f7f6;
  font-size: 1rem;
  max-width: 560px;
}

.auth-side ul {
  margin: 20px 0 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.auth-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dce9ec;
  border-radius: 24px;
  padding: 24px;
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 28px rgba(20, 30, 43, 0.1);
}

.auth-switch {
  background: #edf6f7;
  border-radius: 12px;
  padding: 4px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.auth-switch button {
  border: none;
  background: transparent;
  padding: 8px 10px;
  border-radius: 9px;
  font: inherit;
  font-weight: 700;
  color: #33535b;
  cursor: pointer;
}

.auth-switch button.active {
  background: white;
  color: #0f4954;
  box-shadow: 0 4px 8px rgba(8, 45, 58, 0.08);
}

.auth-card h2 {
  margin: 18px 0;
  font-size: 1.35rem;
}

.auth-card label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
}

.auth-card label span {
  font-size: 0.86rem;
  font-weight: 700;
  color: #2a4a52;
}

.auth-card input {
  border: 1px solid #cbdde2;
  border-radius: 12px;
  padding: 11px 12px;
  font: inherit;
  background: #fcfeff;
}

.auth-error {
  margin: 12px 0 0;
  color: #9f2632;
  font-weight: 700;
}

.auth-submit,
.logout-btn {
  margin-top: 16px;
  border: none;
  border-radius: 12px;
  padding: 11px 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.auth-submit {
  width: 100%;
  background: linear-gradient(135deg, #0b7480, #0a9c75);
  color: #f5fffe;
}

.auth-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
  max-width: 1240px;
  margin: 0 auto;
}

.shell-header {
  background: rgba(255, 255, 255, 0.83);
  border: 1px solid #d9e7e9;
  border-radius: 20px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  backdrop-filter: blur(10px);
}

.shell-header h1 {
  margin: 6px 0 0;
  font-size: clamp(1.3rem, 2.1vw, 2rem);
}

.shell-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.shell-user p {
  margin: 0;
  font-weight: 700;
  color: #244652;
}

.logout-btn {
  margin-top: 0;
  background: #e8f6f7;
  color: #0d4f5d;
}

.shell-content {
  margin-top: 16px;
}

@media (max-width: 980px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .app-shell,
  .auth-layout {
    padding: 14px;
  }

  .shell-header,
  .shell-user {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
