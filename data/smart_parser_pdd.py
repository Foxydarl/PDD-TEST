import requests
import re
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple
import urllib3
from collections import defaultdict

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== КОНФИГУРАЦИЯ ==========
URL_PDD = "https://adilet.zan.kz/rus/docs/V2300033003"
DB_PATH = r'C:\Users\andrei\queryquest\backend\sqlite_query_service\pdd_questions.db'
LOCAL_FILE = Path("pdd_text_raw.txt")

# ========== БАЗА ЗНАНИЙ ДЛЯ ГЕНЕРАЦИИ ВОПРОСОВ ==========
class SmartPDDParser:
    def __init__(self):
        self.questions = []
        self.question_id = 1
        
    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов"""
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        # Удаляем номера пунктов и подпунктов
        text = re.sub(r'\d+[\)\-]?\s*', '', text)
        # Нормализуем пробелы
        text = re.sub(r'\s+', ' ', text)
        # Удаляем спецсимволы
        text = re.sub(r'[;:,«»""\'\(\)]', '', text)
        return text.strip()
    
    def extract_short_definitions(self, text: str):
        """Извлекает короткие определения терминов"""
        print("   📖 Генерация вопросов по терминам...")
        
        # Ищем определения в формате "термин - определение" (короткие)
        patterns = [
            r'(\d+)\)\s*([а-яё][^\-\d]{3,30}?)\s*[-–]\s*([^\.]{10,100}?)[\.;]',
            r'([а-яё][а-яё\s]{3,30}?)\s*[-–]\s*([^\.]{10,100}?)[\.;]',
        ]
        
        definitions = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) >= 2:
                    term = self.clean_text(match[-2]) if len(match) > 1 else ""
                    definition = self.clean_text(match[-1]) if len(match) > 0 else ""
                    if 3 < len(term) < 50 and 10 < len(definition) < 150:
                        definitions.append((term, definition))
        
        # Убираем дубликаты
        seen = set()
        unique_defs = []
        for term, definition in definitions:
            if term not in seen and len(term) > 3:
                seen.add(term)
                unique_defs.append((term, definition))
        
        for term, definition in unique_defs[:25]:
            question = f"Что означает термин '{term}'?"
            
            # Генерируем правдоподобные неправильные ответы
            wrong_answers = [
                "Скоростной режим на данном участке дороги",
                "Техническое средство организации движения",
                "Документ на право управления транспортным средством",
                "Штрафная санкция за нарушение ПДД",
                "Дорожный знак особого предписания",
                "Транспортное средство специального назначения"
            ]
            
            answers = [
                {"text": definition[:100], "is_correct": True, 
                 "explanation": f"Это правильное определение термина '{term}'"},
            ]
            
            # Добавляем 3 неправильных ответа
            import random
            for wrong in random.sample(wrong_answers, 3):
                answers.append({"text": wrong, "is_correct": False, 
                               "explanation": f"Это не относится к термину '{term}'"})
            
            self.questions.append({
                "id": self.question_id,
                "question": question,
                "category": "Основные понятия и термины",
                "answers": answers
            })
            self.question_id += 1
    
    def extract_speed_limits(self, text: str):
        """Извлекает ограничения скорости"""
        print("   🏎️ Генерация вопросов о скорости...")
        
        speed_patterns = [
            (r'насел[её]нн[оы]м пункт[еа][^\.]{0,30}(\d+)\s*км/ч', "В населенном пункте", "60 км/ч"),
            (r'вне населенн[оы]х пунктов[^\.]{0,30}(\d+)\s*км/ч', "Вне населенного пункта", "90 км/ч"),
            (r'автомагистрал[иь][^\.]{0,30}(\d+)\s*км/ч', "На автомагистрали", "110 км/ч"),
            (r'жил[ао]й зон[еы][^\.]{0,30}(\d+)\s*км/ч', "В жилой зоне", "20 км/ч"),
            (r'буксировк[ае][^\.]{0,30}(\d+)\s*км/ч', "При буксировке", "50 км/ч"),
        ]
        
        speed_questions = [
            ("В населенном пункте", "60 км/ч", "В населенных пунктах максимальная скорость 60 км/ч"),
            ("Вне населенного пункта на легковом автомобиле", "90 км/ч", 
             "Вне населенных пунктов разрешено движение до 90 км/ч"),
            ("На автомагистрали", "110 км/ч", "На автомагистралях максимальная скорость 110 км/ч"),
            ("В жилой зоне", "20 км/ч", "В жилых зонах скорость ограничена 20 км/ч"),
            ("При буксировке другого ТС", "50 км/ч", "При буксировке максимальная скорость 50 км/ч"),
            ("При перевозке детей в организованной колонне", "60 км/ч", 
             "При перевозке детей скорость не должна превышать 60 км/ч"),
        ]
        
        for location, speed, explanation in speed_questions:
            question = f"Какая максимальная разрешенная скорость {location}?"
            
            wrong_speeds = ["40 км/ч", "70 км/ч", "80 км/ч", "100 км/ч", "120 км/ч", "30 км/ч"]
            wrong_speeds = [ws for ws in wrong_speeds if ws != speed][:3]
            
            answers = [
                {"text": speed, "is_correct": True, "explanation": explanation},
                {"text": wrong_speeds[0], "is_correct": False, 
                 "explanation": f"Правильная скорость - {speed}"},
                {"text": wrong_speeds[1], "is_correct": False, 
                 "explanation": f"Правильная скорость - {speed}"},
                {"text": wrong_speeds[2], "is_correct": False, 
                 "explanation": f"Правильная скорость - {speed}"},
            ]
            
            self.questions.append({
                "id": self.question_id,
                "question": question,
                "category": "Скоростной режим",
                "answers": answers
            })
            self.question_id += 1
    
    def extract_prohibitions(self, text: str):
        """Извлекает короткие запреты"""
        print("   🚫 Генерация вопросов о запретах...")
        
        # Поиск коротких запретов
        prohibition_patterns = [
            r'запрещает[сся]\s+([а-я][^\.]{15,80}?)[\.]',
            r'запреща[её]тс[яа]\s+([а-я][^\.]{15,80}?)[\.]',
            r'не допускается\s+([а-я][^\.]{15,80}?)[\.]',
        ]
        
        prohibitions = []
        for pattern in prohibition_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean = self.clean_text(match)
                if 20 < len(clean) < 100:
                    prohibitions.append(clean)
        
        # Убираем дубликаты
        prohibitions = list(dict.fromkeys(prohibitions))[:15]
        
        prohibition_categories = {
            "обгон": "Обгон и опережение",
            "остановк": "Остановка и стоянка",
            "парковк": "Остановка и стоянка",
            "скорост": "Скоростной режим",
            "знак": "Дорожные знаки",
            "разметк": "Дорожные знаки",
            "светофор": "Сигналы светофора"
        }
        
        for prohibition in prohibitions:
            question = "Что из перечисленного ЗАПРЕЩАЕТ ПДД РК?"
            
            # Определяем категорию
            category = "Запреты и ограничения"
            for key, cat in prohibition_categories.items():
                if key in prohibition.lower():
                    category = cat
                    break
            
            answers = [
                {"text": prohibition, "is_correct": True, 
                 "explanation": "Это действие прямо запрещено Правилами"},
                {"text": "Разрешается при наличии разрешения ГАИ", "is_correct": False, 
                 "explanation": "Данное действие запрещено ПДД"},
                {"text": "Разрешается только в экстренных случаях", "is_correct": False, 
                 "explanation": "Исключения не предусмотрены"},
                {"text": "Разрешается для оперативных служб", "is_correct": False, 
                 "explanation": "Это относится только к спецтранспорту"}
            ]
            
            self.questions.append({
                "id": self.question_id,
                "question": question,
                "category": category,
                "answers": answers
            })
            self.question_id += 1
    
    def extract_light_signals(self):
        """Генерирует вопросы о сигналах светофора"""
        print("   💡 Генерация вопросов о сигналах светофора...")
        
        light_questions = [
            {
                "question": "Что означает зеленый сигнал светофора?",
                "correct": "Разрешает движение",
                "wrong": ["Запрещает движение", "Требует остановки", "Предупреждает об опасности"],
                "explanation": "Зеленый сигнал светофора разрешает движение транспортных средств"
            },
            {
                "question": "Что означает желтый сигнал светофора?",
                "correct": "Предупреждает о смене сигнала",
                "wrong": ["Разрешает движение", "Запрещает движение", "Требует ускориться"],
                "explanation": "Желтый сигнал предупреждает о предстоящей смене сигнала"
            },
            {
                "question": "Что означает красный сигнал светофора?",
                "correct": "Запрещает движение",
                "wrong": ["Разрешает движение", "Предупреждает об опасности", "Требует осторожности"],
                "explanation": "Красный сигнал светофора запрещает движение"
            },
            {
                "question": "Что означает мигающий зеленый сигнал светофора?",
                "correct": "Скоро будет включен желтый сигнал",
                "wrong": ["Движение запрещено", "Разрешает движение пешеходам", "Требует остановки"],
                "explanation": "Мигающий зеленый предупреждает о скором включении желтого сигнала"
            }
        ]
        
        for q in light_questions:
            answers = [
                {"text": q["correct"], "is_correct": True, "explanation": q["explanation"]},
                {"text": q["wrong"][0], "is_correct": False, "explanation": f"Правильно: {q['correct']}"},
                {"text": q["wrong"][1], "is_correct": False, "explanation": f"Правильно: {q['correct']}"},
                {"text": q["wrong"][2], "is_correct": False, "explanation": f"Правильно: {q['correct']}"},
            ]
            
            self.questions.append({
                "id": self.question_id,
                "question": q["question"],
                "category": "Сигналы светофора",
                "answers": answers
            })
            self.question_id += 1
    
    def extract_sign_rules(self):
        """Генерирует вопросы о дорожных знаках"""
        print("   🛑 Генерация вопросов о дорожных знаках...")
        
        sign_questions = [
            {
                "question": "Что означает знак 'Уступите дорогу'?",
                "correct": "Должны уступить дорогу",
                "wrong": ["Имеете преимущество", "Обязаны остановиться", "Движение запрещено"],
                "explanation": "Знак 'Уступите дорогу' обязывает уступить дорогу ТС на пересекаемой дороге"
            },
            {
                "question": "Что означает знак 'Кирпич' (въезд запрещен)?",
                "correct": "Въезд запрещен",
                "wrong": ["Стоянка запрещена", "Обгон запрещен", "Движение прямо запрещено"],
                "explanation": "Знак 'Въезд запрещен' запрещает въезд всех транспортных средств"
            },
            {
                "question": "Что означает знак 'Главная дорога'?",
                "correct": "Имеете преимущество",
                "wrong": ["Нужно уступить дорогу", "Дорога закрыта", "Скоростная дорога"],
                "explanation": "Знак 'Главная дорога' дает преимущество перед второстепенной"
            },
            {
                "question": "Что означает знак 'Движение запрещено'?",
                "correct": "Запрещает движение всех ТС",
                "wrong": ["Запрещает только грузовым", "Запрещает только велосипедам", "Разрешает движение"],
                "explanation": "Знак 'Движение запрещено' запрещает движение всех ТС на данном участке"
            }
        ]
        
        for q in sign_questions:
            answers = [
                {"text": q["correct"], "is_correct": True, "explanation": q["explanation"]},
                {"text": q["wrong"][0], "is_correct": False, "explanation": f"Правильно: {q['correct']}"},
                {"text": q["wrong"][1], "is_correct": False, "explanation": f"Правильно: {q['correct']}"},
                {"text": q["wrong"][2], "is_correct": False, "explanation": f"Правильно: {q['correct']}"},
            ]
            
            self.questions.append({
                "id": self.question_id,
                "question": q["question"],
                "category": "Дорожные знаки и разметка",
                "answers": answers
            })
            self.question_id += 1
    
    def generate_all_questions(self, text: str) -> List[Dict]:
        """Генерирует все вопросы"""
        print("\n🔄 Генерация вопросов по ПДД РК:")
        
        self.extract_short_definitions(text)
        self.extract_speed_limits(text)
        self.extract_prohibitions(text)
        self.extract_light_signals()
        self.extract_sign_rules()
        
        return self.questions

# ========== ЗАГРУЗКА ТЕКСТА ПДД ==========
def get_pdd_text() -> str:
    """Получает текст ПДД с сайта или из локального файла"""
    
    # Пробуем прочитать из локального файла
    if LOCAL_FILE.exists():
        print(f"📁 Чтение из локального файла: {LOCAL_FILE}")
        with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
            text = f.read()
            if len(text) > 1000:
                print(f"   ✅ Загружено {len(text)} символов")
                return text
    
    # Пробуем скачать с сайта
    print(f"📥 Скачивание ПДД с {URL_PDD}...")
    try:
        response = requests.get(URL_PDD, verify=False, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            text = response.text
            
            # Сохраняем локально
            with open(LOCAL_FILE, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"   ✅ Скачано {len(text)} символов")
            return text
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("   ⚠️ Использую встроенные данные")
    return ""

# ========== ЗАГРУЗКА В БАЗУ ДАННЫХ ==========
def load_to_database(questions: List[Dict], db_path: str):
    """Загружает вопросы в базу данных"""
    print(f"\n🗄️ Загрузка в базу данных: {db_path}")
    
    # Создаем папку если нужно
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Создаем таблицы
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
    
    # Очищаем старые данные
    cursor.execute("DELETE FROM answers")
    cursor.execute("DELETE FROM questions")
    
    # Загружаем новые вопросы
    for q in questions:
        cursor.execute('''
            INSERT INTO questions (question_text, category, points)
            VALUES (?, ?, ?)
        ''', (q["question"], q["category"], 1))
        
        question_id = cursor.lastrowid
        
        for answer in q["answers"]:
            cursor.execute('''
                INSERT INTO answers (question_id, answer_text, is_correct, explanation)
                VALUES (?, ?, ?, ?)
            ''', (question_id, answer["text"], 1 if answer["is_correct"] else 0, answer["explanation"]))
    
    conn.commit()
    
    # Статистика
    cursor.execute("SELECT COUNT(*) FROM questions")
    q_count = cursor.fetchone()[0]
    cursor.execute("SELECT category, COUNT(*) FROM questions GROUP BY category")
    categories = cursor.fetchall()
    
    conn.close()
    
    print(f"   ✅ Загружено {q_count} вопросов")
    print("\n📊 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
    for cat, cnt in categories:
        print(f"   • {cat}: {cnt} вопросов")
    
    return q_count

# ========== ОСНОВНАЯ ФУНКЦИЯ ==========
def main():
    print("=" * 60)
    print("🤖 УМНЫЙ ПАРСЕР ПДД РК (автоматическая генерация вопросов)")
    print("=" * 60)
    
    # 1. Получаем текст ПДД
    text = get_pdd_text()
    
    if not text:
        print("❌ Не удалось получить текст ПДД")
        return
    
    # 2. Генерируем вопросы
    parser = SmartPDDParser()
    questions = parser.generate_all_questions(text)
    
    if not questions:
        print("❌ Не удалось сгенерировать вопросы")
        return
    
    # 3. Сохраняем JSON для резервной копии
    json_path = Path("pdd_questions_good.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Резервная копия сохранена: {json_path}")
    
    # 4. Загружаем в базу данных
    count = load_to_database(questions, DB_PATH)
    
    print("\n" + "=" * 60)
    print(f"🎉 ГОТОВО! Сгенерировано и загружено {count} вопросов!")
    print("=" * 60)
    print("\n📝 Теперь перезапустите бэкенд и фронтенд:")
    print("   Бэкенд: cd ../backend/sqlite_query_service && python main.py")
    print("   Фронтенд: cd ../pdd-frontend && npm run dev")

if __name__ == "__main__":
    main()