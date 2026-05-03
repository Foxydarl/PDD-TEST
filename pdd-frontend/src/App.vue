<script setup>
import { computed, onMounted, ref } from 'vue'
import { login, register } from './api/auth'
import { API_BASE, adminLogin } from './api/pdd'
import { pb } from './lib/pocketbase'
import { DEFAULT_LANGUAGE, LANGUAGE_OPTIONS, getAccountLanguage, setAccountLanguage, translate } from './i18n'
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

const language = ref(DEFAULT_LANGUAGE)
const settingsOpen = ref(false)

const isAuthenticated = computed(() => Boolean(session.value))
const roleLabel = computed(() => (session.value?.role === 'admin' ? t('app.role.admin') : t('app.role.user')))
const languageOptions = computed(() =>
  LANGUAGE_OPTIONS.map((item) => ({
    value: item.value,
    label: t(item.labelKey)
  }))
)

function t(key, params = {}) {
  return translate(language.value, key, params)
}

function getAccountIdBySession(nextSession) {
  if (!nextSession) return ''
  if (nextSession.role === 'admin') return 'admin'
  return nextSession.userId || ''
}

function applyLanguageForSession(nextSession) {
  const accountId = getAccountIdBySession(nextSession)
  language.value = accountId ? getAccountLanguage(accountId) : DEFAULT_LANGUAGE
}

function setLanguage(nextLanguage) {
  language.value = nextLanguage
  const accountId = getAccountIdBySession(session.value)
  if (accountId) {
    setAccountLanguage(accountId, nextLanguage)
  }
}

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
      applyLanguageForSession(session.value)
      return
    } catch (error) {
      localStorage.removeItem(ADMIN_STORAGE_KEY)
    }
  }

  session.value = createUserSession()
  applyLanguageForSession(session.value)
}

function extractErrorMessage(error, fallback) {
  return (
    error?.response?.data?.message ||
    error?.response?.data?.detail ||
    error?.message ||
    fallback
  )
}

function getBaseOrigin(url) {
  try {
    return new URL(url).origin
  } catch (error) {
    return url
  }
}

async function handleAuth() {
  authError.value = ''
  loading.value = true

  try {
    if (authMode.value === 'register') {
      if (!name.value.trim()) {
        authError.value = t('app.auth.registerNameRequired')
        return
      }

      await register(email.value.trim(), password.value, name.value)
      await login(email.value.trim(), password.value)
      session.value = createUserSession()
      applyLanguageForSession(session.value)
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
      applyLanguageForSession(session.value)
      email.value = ''
      password.value = ''
      return
    } catch (adminError) {
      const adminStatus = adminError?.response?.status
      if (![401, 403].includes(adminStatus)) {
        throw new Error(t('app.adminUnavailable', { origin: getBaseOrigin(API_BASE) }))
      }

      await login(email.value.trim(), password.value)
      session.value = createUserSession()
      applyLanguageForSession(session.value)
      name.value = ''
      email.value = ''
      password.value = ''
    }
  } catch (error) {
    authError.value = extractErrorMessage(error, t('app.auth.failed'))
  } finally {
    loading.value = false
  }
}

function logout() {
  localStorage.removeItem(ADMIN_STORAGE_KEY)
  settingsOpen.value = false

  if (session.value?.role !== 'admin') {
    pb.authStore.clear()
  }

  session.value = null
  applyLanguageForSession(null)
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
      <p class="eyebrow">{{ t('app.platform') }}</p>
      <h1>{{ t('app.auth.title') }}</h1>
      <p>
        {{ t('app.auth.subtitle') }}
      </p>
      <ul>
        <li>{{ t('app.auth.feature1') }}</li>
        <li>{{ t('app.auth.feature2') }}</li>
        <li>{{ t('app.auth.feature3') }}</li>
      </ul>
    </article>

    <article class="auth-card">
      <div class="auth-switch">
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">{{ t('app.auth.login') }}</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">{{ t('app.auth.register') }}</button>
      </div>

      <h2>{{ authMode === 'login' ? t('app.auth.loginTitle') : t('app.auth.registerTitle') }}</h2>

      <label v-if="authMode === 'register'">
        <span>{{ t('app.auth.name') }}</span>
        <input v-model="name" type="text" :placeholder="t('app.auth.namePlaceholder')" autocomplete="name" />
      </label>

      <label>
        <span>Email</span>
        <input v-model="email" type="email" placeholder="you@example.com" autocomplete="email" />
      </label>

      <label>
        <span>{{ t('app.auth.password') }}</span>
        <input v-model="password" type="password" placeholder="********" autocomplete="current-password" />
      </label>

      <p v-if="authError" class="auth-error">{{ authError }}</p>

      <button class="auth-submit" :disabled="loading" @click="handleAuth">
        {{ loading ? t('app.auth.wait') : authMode === 'login' ? t('app.auth.signIn') : t('app.auth.signUp') }}
      </button>
    </article>
  </section>

  <section v-else class="app-shell">
    <header class="shell-header">
      <div>
        <p class="eyebrow">{{ t('app.dashboard') }}</p>
        <h1>{{ roleLabel }}</h1>
      </div>

      <div class="shell-user">
        <p>{{ session.userName ? `${session.userName} — ${session.email}` : session.email }}</p>

        <div class="shell-actions">
          <button class="settings-btn" @click="settingsOpen = !settingsOpen">
            {{ t('app.settings.open') }}
          </button>
          <button class="logout-btn" @click="logout">{{ t('app.logout') }}</button>
        </div>

        <div v-if="settingsOpen" class="settings-popover">
          <strong>{{ t('app.settings.title') }}</strong>
          <label>
            <span>{{ t('app.settings.language') }}</span>
            <select :value="language" @change="setLanguage($event.target.value)">
              <option v-for="option in languageOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
      </div>
    </header>

    <main class="shell-content">
      <AdminDashboard
        v-if="session.role === 'admin'"
        :session="session"
        :language="language"
        :t="t"
      />
      <UserDashboard
        v-else
        :session="session"
        :language="language"
        :t="t"
        @profile-updated="handleProfileUpdated"
      />
    </main>
  </section>
</template>

<style scoped>
.root-bg {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 14% 16%, rgba(11, 126, 139, 0.24), transparent 32%),
    radial-gradient(circle at 83% 10%, rgba(12, 160, 132, 0.2), transparent 34%),
    radial-gradient(circle at 78% 84%, rgba(30, 113, 129, 0.16), transparent 40%),
    linear-gradient(132deg, #f4fbfd 0%, #e8f3f5 50%, #edf8f5 100%);
  z-index: -2;
}

.root-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.45) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.45) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.42), transparent 88%);
  z-index: -1;
}

.auth-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 450px;
  gap: 24px;
  align-items: center;
  max-width: 1140px;
  margin: 0 auto;
  padding: 30px;
}

.auth-side {
  background: linear-gradient(145deg, rgba(5, 67, 76, 0.96), rgba(8, 111, 93, 0.9));
  color: #effffd;
  border-radius: 30px;
  padding: 38px;
  box-shadow: var(--shadow-strong);
  border: 1px solid rgba(207, 241, 245, 0.24);
}

.eyebrow {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.17em;
  font-size: 0.76rem;
  font-weight: 800;
}

.auth-side h1 {
  margin: 14px 0;
  font-size: clamp(2.1rem, 4.2vw, 3.1rem);
  line-height: 1.08;
}

.auth-side p {
  margin: 0;
  color: #d6f7f3;
  font-size: 1.03rem;
  max-width: 560px;
  line-height: 1.45;
}

.auth-side ul {
  margin: 22px 0 0;
  padding-left: 18px;
  display: grid;
  gap: 9px;
}

.auth-card {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid #d6e7ea;
  border-radius: 26px;
  padding: 24px;
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.auth-switch {
  background: #e8f2f4;
  border-radius: 14px;
  padding: 4px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.auth-switch button {
  border: none;
  background: transparent;
  padding: 9px 10px;
  border-radius: 10px;
  font: inherit;
  font-weight: 700;
  color: #365762;
  cursor: pointer;
}

.auth-switch button.active {
  background: white;
  color: #0e4d59;
  box-shadow: 0 6px 14px rgba(6, 51, 63, 0.08);
}

.auth-card h2 {
  margin: 18px 0;
  font-size: 1.4rem;
}

.auth-card label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
}

.auth-card label span {
  font-size: 0.84rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #2f5159;
  text-transform: uppercase;
}

.auth-card input {
  border: 1px solid #c8dce1;
  border-radius: 13px;
  padding: 11px 12px;
  font: inherit;
  background: #fcfeff;
}

.auth-card input:focus-visible {
  border-color: #0b7f8c;
  box-shadow: 0 0 0 3px rgba(11, 127, 140, 0.14);
}

.auth-error {
  margin: 12px 0 0;
  color: #9f2632;
  font-weight: 700;
}

.auth-submit,
.logout-btn,
.settings-btn {
  margin-top: 16px;
  border: none;
  border-radius: 13px;
  padding: 11px 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.auth-submit {
  width: 100%;
  background: linear-gradient(135deg, #0a7480, #0d9f77);
  color: #f5fffe;
  box-shadow: 0 10px 18px rgba(11, 116, 128, 0.22);
}

.auth-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(11, 116, 128, 0.28);
}

.auth-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
  max-width: 1260px;
  margin: 0 auto;
  position: relative;
  isolation: isolate;
}

.shell-header {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #d6e8eb;
  border-radius: 22px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft);
  position: relative;
  z-index: 30;
  overflow: visible;
}

.shell-header h1 {
  margin: 6px 0 0;
  font-size: clamp(1.35rem, 2.2vw, 2.05rem);
}

.shell-user {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}

.shell-user p {
  margin: 0;
  font-weight: 700;
  color: #244652;
}

.shell-actions {
  display: flex;
  gap: 8px;
}

.logout-btn,
.settings-btn {
  margin-top: 0;
  background: #e7f4f6;
  color: #0d4f5d;
}

.logout-btn:hover,
.settings-btn:hover {
  transform: translateY(-1px);
}

.settings-popover {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 280px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #cfe2e7;
  border-radius: 14px;
  box-shadow: 0 18px 28px rgba(14, 46, 58, 0.14);
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 40;
}

.settings-popover strong {
  color: #1d4854;
}

.settings-popover label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.settings-popover span {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #41626f;
  font-weight: 700;
}

.settings-popover select {
  border: 1px solid #c4d9de;
  border-radius: 10px;
  padding: 8px 10px;
  font: inherit;
  background: #fcfeff;
}

.shell-content {
  margin-top: 16px;
  position: relative;
  z-index: 1;
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

  .settings-popover {
    position: static;
    width: 100%;
  }

  .auth-side,
  .auth-card {
    border-radius: 20px;
    padding: 20px;
  }
}
</style>
