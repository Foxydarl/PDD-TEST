# PDD Testing Platform (Vue + FastAPI + PocketBase)

Полная инструкция по запуску проекта на Windows: что установить, как запустить сервисы и что делать при типичных ошибках.

## Что внутри проекта

- `pdd-frontend` - фронтенд на Vue 3 + Vite.
- `backend/sqlite_query_service` - основной FastAPI API для тестов ПДД (порт `8080`).
- `backend/ai_service` - FastAPI сервис генерации SQL-вопросов (порт `8081`).
- `backend/backend_service` - PocketBase (порт `8090`).
- `data` - скрипты и датасеты для подготовки базы вопросов.

## Что нужно установить

1. `Python 3.11+`
2. `Node.js 20+` (вместе с `npm`)
3. (Опционально) `Graphviz`, если будете использовать ER-диаграммы (`/api/diagram/er-diagram`)

Проверка:

```powershell
python --version
node --version
npm --version
```

## Установка зависимостей

Из корня проекта (`Bekzhan1-main`):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\sqlite_query_service\requirements.txt
pip install -r backend\ai_service\requirements.txt
cd pdd-frontend
npm install
cd ..
```

## Быстрый запуск (все сервисы сразу)

```powershell
start.bat
```

Скрипт откроет 4 окна:

1. `sqlite_query_service` (`http://localhost:8080`)
2. `ai_service` (`http://localhost:8081`)
3. `pocketbase` (`http://127.0.0.1:8090`)
4. `vite frontend` (обычно `http://localhost:5173`)

## Ручной запуск (если удобнее по отдельности)

Откройте 4 терминала в корне проекта:

1. Основной backend:

```powershell
.\.venv\Scripts\activate
cd backend\sqlite_query_service
python main.py
```

2. AI backend:

```powershell
.\.venv\Scripts\activate
cd backend\ai_service
python main.py
```

3. PocketBase:

```powershell
cd backend\backend_service
.\pocketbase.exe serve
```

4. Frontend:

```powershell
cd pdd-frontend
npm run dev
```

## Полезные адреса после запуска

- Frontend: `http://localhost:5173`
- API docs (PDD backend): `http://localhost:8080/docs`
- API docs (AI backend): `http://localhost:8081/docs`
- PocketBase Admin UI: `http://127.0.0.1:8090/_/`

## Важные замечания по текущему состоянию

1. База ПДД уже лежит в репозитории:
   - `backend/sqlite_query_service/pdd_questions.db`
   - В базе есть вопросы и ответы, поэтому для первого запуска ничего импортировать не нужно.

2. AI модель не хранится в репозитории:
   - для эндпоинта `/create_question` нужен файл  
     `backend/ai_service/utils/ggml-gpt4all-j-v1.3-groovy.bin`
   - без него сервис стартует, но генерация вопроса выдаст ошибку.

3. Текущий `pdd-frontend/src/App.vue` использует PocketBase-авторизацию и импортирует `src/lib/pocketbase`, которого нет в репозитории.
   - если нужна авторизация: создайте файл `pdd-frontend/src/lib/pocketbase.js`:

```js
import PocketBase from 'pocketbase'

export const pb = new PocketBase('http://127.0.0.1:8090')
```

   - если хотите сразу открыть экран теста ПДД из `HomePage.vue`, замените содержимое `pdd-frontend/src/App.vue` на:

```vue
<script setup>
import HomePage from './views/HomePage.vue'
</script>

<template>
  <HomePage />
</template>
```

## Основные PDD API-эндпоинты (`8080`)

- `GET /api/pdd/categories` - список категорий
- `GET /api/pdd/questions/{category}?limit=20` - вопросы по категории
- `POST /api/pdd/test/submit` - проверка теста и сохранение результата
- `GET /api/pdd/results/{user_id}` - история попыток пользователя
- `GET /api/pdd/stats/{user_id}` - статистика по категориям

## Скрипты из `data/`

В папке `data` есть скрипты импорта/генерации вопросов, но часть из них содержит абсолютные пути автора (`C:\Users\andrei\...`).  
Перед использованием обновите пути в скриптах на локальные.

## Типичные проблемы

1. `npm` не найден:
   - установите Node.js, закройте/откройте терминал, проверьте `npm --version`.

2. Frontend не стартует с ошибкой про `./lib/pocketbase`:
   - создайте `pdd-frontend/src/lib/pocketbase.js` (см. выше), либо временно переключите `App.vue` на `HomePage.vue`.

3. Frontend не может получить данные:
   - проверьте, что `backend/sqlite_query_service` запущен на `8080`.

4. Ошибка AI генерации:
   - проверьте наличие файла модели `ggml-gpt4all-j-v1.3-groovy.bin` в `backend/ai_service/utils`.


## Admin Functionality (Added)

### Admin credentials

- Login: `admin@pdd.local`
- Password: `AdminPDD2026!`

### What admin can do

- View all registered users from PocketBase.
- Search users by email.
- View all available tests.
- Create custom tests from question bank.
- Assign any test to any user.
- See recent assignments and completion status.

### Existing test

The current system PDD test is automatically added as a pre-created admin test:

- `Общий тест ПДД` (legacy/system test, random 20 questions from DB)

### User flow

1. User logs in with regular account (PocketBase).
2. User sees only tests assigned by admin.
3. User starts test, answers questions, submits.
4. Score is stored and visible for admin in assignment status.

### Admin login troubleshooting

If admin login returns `404 Not Found`, it means old API instance is still running on `8080`.
This project now starts PDD API on `8082` via `start.bat`.

- PDD API: `http://localhost:8082`
- Admin login endpoint: `POST http://localhost:8082/api/pdd/admin/login`
