import sqlite3
import os
from pathlib import Path

print("=" * 50)
print("🧹 ПОЛНАЯ ОЧИСТКА ДАННЫХ")
print("=" * 50)

# 1. Очищаем базу данных
DB_PATH = r'C:\Users\andrei\queryquest\backend\sqlite_query_service\pdd_questions.db'

if os.path.exists(DB_PATH):
    print(f"📁 Найдена база данных: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Удаляем все данные
    cursor.execute("DELETE FROM answers")
    cursor.execute("DELETE FROM questions")
    cursor.execute("DELETE FROM test_results")
    
    # Сбрасываем счетчики автоинкремента
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='questions'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='answers'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='test_results'")
    
    conn.commit()
    conn.close()
    print("✅ База данных очищена")
else:
    print("⚠️ База данных не найдена, будет создана новая")

# 2. Удаляем старые JSON файлы (оставляем только нужные)
json_files = ["pdd_questions_auto.json", "pdd_questions_good.json", "good_questions_pdd.json"]
for json_file in json_files:
    json_path = Path(json_file)
    if json_path.exists():
        json_path.unlink()
        print(f"✅ Удалён: {json_file}")

print("\n✨ Очистка завершена! Теперь можно запускать умный парсер.")