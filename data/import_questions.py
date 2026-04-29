import sqlite3
import json
import os

print("=" * 50)
print("Импорт вопросов ПДД РК в базу данных")
print("=" * 50)

# Путь к базе данных
db_path = r'C:\Users\andrei\queryquest\backend\sqlite_query_service\pdd_questions.db'

# Путь к JSON файлу
json_path = r'C:\Users\andrei\queryquest\data\pdd_questions_full.json'

print(f"\n📁 База данных: {db_path}")
print(f"📁 Файл с вопросами: {json_path}")

# Проверяем существование файлов
if not os.path.exists(json_path):
    print(f"\n❌ Ошибка: Файл {json_path} не найден!")
    exit(1)

# Подключаемся к базе данных
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Очищаем старые данные
print("\n🔄 Очищаем старые данные...")
cursor.execute("DELETE FROM answers")
cursor.execute("DELETE FROM questions")
print("✅ Старые данные удалены")

# Загружаем вопросы из JSON
print("\n📖 Загружаем вопросы из JSON...")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

questions_count = 0
answers_count = 0

for q in data['questions']:
    # Вставляем вопрос
    cursor.execute('''
        INSERT INTO questions (question_text, category, image_url, points)
        VALUES (?, ?, ?, ?)
    ''', (q['question'], q['category'], q.get('image_url'), 1))
    
    question_id = cursor.lastrowid
    questions_count += 1
    
    # Вставляем ответы
    for a in q['answers']:
        cursor.execute('''
            INSERT INTO answers (question_id, answer_text, is_correct, explanation)
            VALUES (?, ?, ?, ?)
        ''', (question_id, a['text'], a['is_correct'], a.get('explanation', '')))
        answers_count += 1

# Сохраняем изменения
conn.commit()

# Проверяем результат
cursor.execute("SELECT COUNT(*) FROM questions")
total_questions = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM answers")
total_answers = cursor.fetchone()[0]

print("\n" + "=" * 50)
print("📊 РЕЗУЛЬТАТЫ ИМПОРТА:")
print("=" * 50)
print(f"✅ Загружено вопросов: {total_questions}")
print(f"✅ Загружено ответов: {total_answers}")
print(f"✅ Категории:")
print("-" * 50)

# Показываем количество вопросов по категориям
cursor.execute("""
    SELECT category, COUNT(*) as count 
    FROM questions 
    GROUP BY category 
    ORDER BY category
""")
categories = cursor.fetchall()
for cat in categories:
    print(f"   📚 {cat[0]}: {cat[1]} вопросов")

# Закрываем соединение
conn.close()

print("\n" + "=" * 50)
print("🎉 ИМПОРТ УСПЕШНО ЗАВЕРШЕН!")
print("=" * 50)
print("\n💡 Теперь в тесте доступно больше вопросов!")
print("   Перезагрузите страницу с тестом, чтобы увидеть изменения.")