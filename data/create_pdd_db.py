import sqlite3
import json

print("Создание базы данных ПДД РК...")

# Путь к базе данных
db_path = r'C:\Users\andrei\queryquest\backend\sqlite_query_service\pdd_questions.db'

# Подключаемся к базе
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Создаем таблицы (если их нет)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        category TEXT NOT NULL,
        image_url TEXT,
        points INTEGER DEFAULT 1
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        answer_text TEXT NOT NULL,
        is_correct BOOLEAN DEFAULT 0,
        explanation TEXT,
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        category TEXT NOT NULL,
        total_questions INTEGER,
        correct_answers INTEGER,
        score INTEGER,
        test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

print("✅ Таблицы созданы")

# Добавляем несколько вопросов ПДД
questions_data = [
    {
        "question": "Какое значение имеет зеленый сигнал светофора?",
        "category": "Общие положения",
        "answers": [
            {"text": "Запрещает движение", "is_correct": False, "explanation": "Зеленый сигнал разрешает движение"},
            {"text": "Разрешает движение", "is_correct": True, "explanation": "Правильно! Зеленый сигнал разрешает движение"},
            {"text": "Предупреждает о смене сигнала", "is_correct": False, "explanation": "Желтый сигнал предупреждает о смене"}
        ]
    },
    {
        "question": "Максимальная скорость движения в населенном пункте?",
        "category": "Скоростной режим",
        "answers": [
            {"text": "40 км/ч", "is_correct": False, "explanation": "Это слишком низкая скорость"},
            {"text": "60 км/ч", "is_correct": True, "explanation": "Правильно! По ПДД РК - 60 км/ч"},
            {"text": "80 км/ч", "is_correct": False, "explanation": "80 км/ч разрешено только вне населенных пунктов"}
        ]
    },
    {
        "question": "Разрешается ли обгон на пешеходном переходе?",
        "category": "Обгон и опережение",
        "answers": [
            {"text": "Разрешается, если нет пешеходов", "is_correct": False, "explanation": "Обгон на переходах запрещен всегда"},
            {"text": "Запрещается", "is_correct": True, "explanation": "Правильно! Обгон на пешеходных переходах запрещен"},
            {"text": "Разрешается с включенным сигналом поворота", "is_correct": False, "explanation": "Сигнал поворота не отменяет запрет"}
        ]
    }
]

# Очищаем старые данные (опционально)
cursor.execute("DELETE FROM answers")
cursor.execute("DELETE FROM questions")
print("✅ Старые данные очищены")

# Загружаем новые вопросы
for q in questions_data:
    cursor.execute('''
        INSERT INTO questions (question_text, category)
        VALUES (?, ?)
    ''', (q['question'], q['category']))
    
    question_id = cursor.lastrowid
    
    for a in q['answers']:
        cursor.execute('''
            INSERT INTO answers (question_id, answer_text, is_correct, explanation)
            VALUES (?, ?, ?, ?)
        ''', (question_id, a['text'], a['is_correct'], a['explanation']))

conn.commit()
print(f"✅ Загружено {len(questions_data)} вопросов")

# Проверяем
cursor.execute("SELECT COUNT(*) FROM questions")
count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM answers")
answers_count = cursor.fetchone()[0]

print(f"\n📊 Статистика:")
print(f"   Вопросов: {count}")
print(f"   Ответов: {answers_count}")

conn.close()
print("\n🎉 База данных успешно создана!")