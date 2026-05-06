import random
import sqlite3
from pathlib import Path
from typing import Dict, List


DB_PATH = Path(__file__).resolve().parents[1] / "backend" / "sqlite_query_service" / "pdd_questions.db"
TARGET_PER_LANGUAGE = 150
RNG = random.Random(20260506)


CONTEXTS = {
    "ru": [
        "на регулируемом перекрестке в городе",
        "перед стоп-линией в плотном потоке",
        "при ухудшении видимости из-за дождя",
        "в темное время суток на загородной дороге",
        "в зоне дорожных работ",
        "при интенсивном движении в центре города",
        "на участке с ограниченной видимостью",
        "при приближении к остановке общественного транспорта",
        "на дороге с несколькими полосами в одном направлении",
        "на узком участке дороги с встречным разъездом",
        "при появлении пешеходов у края проезжей части",
        "при необходимости срочно снизить скорость",
        "при подъезде к железнодорожному переезду",
        "в условиях скользкого дорожного покрытия",
        "при выполнении маневра в транспортном потоке",
    ],
    "en": [
        "at a signal-controlled city intersection",
        "before the stop line in dense traffic",
        "when visibility is reduced by rain",
        "at night on an out-of-town road",
        "in a road works area",
        "during heavy traffic in the city center",
        "on a section with limited visibility",
        "when approaching a public transport stop",
        "on a road with multiple lanes in one direction",
        "on a narrow section with oncoming vehicles",
        "when pedestrians appear near the edge of the roadway",
        "when urgent speed reduction is required",
        "when approaching a railway crossing",
        "on a slippery road surface",
        "while performing a maneuver in traffic flow",
    ],
    "kk": [
        "қаладағы реттелетін қиылыста",
        "тығыз ағын кезінде стоп-сызық алдында",
        "жаңбырдан көріну нашарлағанда",
        "елді мекеннен тыс жолда түнгі уақытта",
        "жол жөндеу аймағында",
        "қала ортасындағы қарқынды қозғалыста",
        "көрінуі шектеулі учаскеде",
        "қоғамдық көлік аялдамасына жақындағанда",
        "бір бағытта бірнеше жолағы бар жолда",
        "қарсы көлікпен тар учаскеде",
        "жаяу жүргіншілер жол жиегінде пайда болғанда",
        "жылдамдықты шұғыл азайту қажет болғанда",
        "теміржол өткеліне жақындағанда",
        "жол беті тайғақ болғанда",
        "көлік ағынында маневр жасағанда",
    ],
}


QUESTION_PATTERNS = {
    "ru": [
        "В ситуации {context} какое действие водителя является правильным?",
        "Что должен сделать водитель {context}?",
        "Как следует действовать {context}?",
    ],
    "en": [
        "In a situation {context}, what is the correct driver action?",
        "What should the driver do {context}?",
        "How should the driver act {context}?",
    ],
    "kk": [
        "{context} жағдайда жүргізуші қандай әрекет жасауы керек?",
        "Жүргізуші {context} не істеуі тиіс?",
        "{context} кезде қалай дұрыс әрекет ету керек?",
    ],
}


TOPICS = [
    {
        "id": "traffic_lights",
        "category": {"ru": "Сигналы светофора", "en": "Traffic lights", "kk": "Бағдаршам сигналдары"},
        "correct": {
            "ru": "Ориентироваться на сигналы светофора и выполнять их требования.",
            "en": "Follow traffic light signals and obey their requirements.",
            "kk": "Бағдаршам сигналдарын басшылыққа алып, олардың талабын орындау.",
        },
        "wrong": {
            "ru": [
                "Игнорировать сигнал, если дорога визуально свободна.",
                "Продолжать движение без снижения внимания.",
                "Выполнять маневр только по сигналам других водителей.",
                "Руководствоваться только скоростью потока, а не сигналом.",
                "Проезжать перекресток без оценки обстановки.",
            ],
            "en": [
                "Ignore the signal if the road looks empty.",
                "Keep driving without increasing attention.",
                "Perform maneuvers only by other drivers' gestures.",
                "Follow only traffic flow speed, not the signal.",
                "Cross the intersection without evaluating the situation.",
            ],
            "kk": [
                "Жол бос көрінсе, сигналды елемеу.",
                "Назарды күшейтпей қозғалысты жалғастыру.",
                "Маневрді тек басқа жүргізушілердің ымымен орындау.",
                "Сигналды емес, тек ағын жылдамдығын басшылыққа алу.",
                "Жағдайды бағаламай қиылыстан өту.",
            ],
        },
    },
    {
        "id": "road_signs",
        "category": {"ru": "Дорожные знаки и разметка", "en": "Road signs and markings", "kk": "Жол белгілері мен таңбалары"},
        "correct": {
            "ru": "Соблюдать требования знаков и разметки на конкретном участке дороги.",
            "en": "Comply with road signs and markings on the specific road section.",
            "kk": "Жолдың нақты учаскесіндегі белгілер мен таңбалардың талабын сақтау.",
        },
        "wrong": {
            "ru": [
                "Оценивать ситуацию только по поведению впереди идущих автомобилей.",
                "Считать разметку рекомендательной и необязательной.",
                "Игнорировать временные знаки при наличии постоянных.",
                "Ориентироваться только на навигатор, не глядя на знаки.",
                "Выбирать направление без учета предписаний разметки.",
            ],
            "en": [
                "Evaluate the situation only by the behavior of cars ahead.",
                "Treat road markings as optional recommendations.",
                "Ignore temporary signs when permanent signs exist.",
                "Rely only on navigation without checking signs.",
                "Choose direction without considering lane markings.",
            ],
            "kk": [
                "Жағдайды тек алдыңғы көліктердің әрекетіне қарап бағалау.",
                "Жол таңбасын міндетті емес ұсыным деп санау.",
                "Тұрақты белгі барда уақытша белгіні елемеу.",
                "Белгілерге қарамай тек навигаторға сүйену.",
                "Таңба талабын ескермей бағыт таңдау.",
            ],
        },
    },
    {
        "id": "maneuvering",
        "category": {"ru": "Маневрирование", "en": "Maneuvering", "kk": "Маневр жасау"},
        "correct": {
            "ru": "Заблаговременно подать сигнал и убедиться в безопасности маневра.",
            "en": "Signal in advance and make sure the maneuver is safe.",
            "kk": "Алдын ала белгі беріп, маневрдің қауіпсіз екеніне көз жеткізу.",
        },
        "wrong": {
            "ru": [
                "Начинать маневр без подачи сигнала поворота.",
                "Подавать сигнал уже после начала перестроения.",
                "Считать, что сигнал автоматически дает преимущество.",
                "Резко перестраиваться без проверки зеркал и «слепой зоны».",
                "Выполнять разворот без оценки встречного движения.",
            ],
            "en": [
                "Start the maneuver without using turn signals.",
                "Turn on the signal only after lane change begins.",
                "Assume signaling gives automatic right of way.",
                "Change lanes sharply without mirror and blind spot checks.",
                "Make a U-turn without assessing oncoming traffic.",
            ],
            "kk": [
                "Бұрылыс белгісін қоспай маневрді бастау.",
                "Жолақ ауыстыруды бастап кеткен соң ғана белгі беру.",
                "Белгі беру автоматты артықшылық береді деп ойлау.",
                "Айна мен «соқыр аймақты» тексермей күрт жолақ ауыстыру.",
                "Қарсы ағынды бағаламай кері бұрылу.",
            ],
        },
    },
    {
        "id": "speed_distance",
        "category": {"ru": "Скоростной режим", "en": "Speed management", "kk": "Жылдамдық режимі"},
        "correct": {
            "ru": "Выбирать безопасную скорость и дистанцию с учетом условий движения.",
            "en": "Choose safe speed and following distance according to road conditions.",
            "kk": "Жол жағдайына сай қауіпсіз жылдамдық пен арақашықтықты таңдау.",
        },
        "wrong": {
            "ru": [
                "Ориентироваться только на максимально допустимую скорость.",
                "Сокращать дистанцию для движения плотнее потока.",
                "Не снижать скорость при ухудшении видимости.",
                "Игнорировать состояние покрытия при выборе скорости.",
                "Резко ускоряться перед участками повышенной опасности.",
            ],
            "en": [
                "Rely only on the maximum legal speed value.",
                "Shorten distance to stay tighter in traffic flow.",
                "Avoid reducing speed when visibility gets worse.",
                "Ignore road surface condition when choosing speed.",
                "Accelerate sharply before high-risk sections.",
            ],
            "kk": [
                "Тек рұқсат етілген ең жоғары жылдамдыққа сүйену.",
                "Ағынға тығыз кіру үшін арақашықтықты қысқарту.",
                "Көріну нашарлағанда жылдамдықты азайтпау.",
                "Жылдамдық таңдауда жол жабынын елемеу.",
                "Қауіпті учаске алдында күрт үдеу.",
            ],
        },
    },
    {
        "id": "overtaking",
        "category": {"ru": "Обгон и опережение", "en": "Overtaking and passing", "kk": "Озу және басып өту"},
        "correct": {
            "ru": "Начинать обгон только при полной уверенности в его безопасности и разрешенности.",
            "en": "Start overtaking only when it is clearly safe and permitted.",
            "kk": "Озуды тек қауіпсіз әрі рұқсат етілгеніне толық сенімді болғанда бастау.",
        },
        "wrong": {
            "ru": [
                "Начинать обгон при ограниченной видимости дороги.",
                "Ускоряться и мешать автомобилю, который вас обгоняет.",
                "Выезжать на встречную полосу без оценки расстояния.",
                "Продолжать обгон при возникновении риска столкновения.",
                "Считать обгон допустимым в любом месте при высокой мощности авто.",
            ],
            "en": [
                "Begin overtaking when road visibility is limited.",
                "Accelerate and block a vehicle that is overtaking you.",
                "Move into oncoming lane without distance assessment.",
                "Continue overtaking even when collision risk appears.",
                "Assume overtaking is allowed everywhere with a powerful car.",
            ],
            "kk": [
                "Көріну шектеулі кезде озуды бастау.",
                "Сізді озған көлікке кедергі келтіру үшін үдеу.",
                "Қашықтықты бағаламай қарсы жолаққа шығу.",
                "Соқтығысу қаупі туса да озуды жалғастыру.",
                "Қозғалтқышы қуатты болса, кез келген жерде озуға болады деп санау.",
            ],
        },
    },
    {
        "id": "stopping_parking",
        "category": {"ru": "Остановка и стоянка", "en": "Stopping and parking", "kk": "Тоқтау және тұрақ"},
        "correct": {
            "ru": "Выбирать место остановки и стоянки так, чтобы не создавать помех и опасности.",
            "en": "Choose stopping and parking places without creating danger or obstruction.",
            "kk": "Тоқтау мен тұрақ орнын кедергі және қауіп тудырмайтындай таңдау.",
        },
        "wrong": {
            "ru": [
                "Останавливаться в местах с ограниченной обзорностью для других водителей.",
                "Парковаться так, чтобы перекрывать движение пешеходов.",
                "Игнорировать запрещающие знаки при краткой стоянке.",
                "Оставлять автомобиль на проезжей части без необходимости.",
                "Останавливаться на участках, где маневр затрудняет разъезд.",
            ],
            "en": [
                "Stop where other drivers have reduced visibility.",
                "Park in a way that blocks pedestrian movement.",
                "Ignore prohibitory signs during a short stop.",
                "Leave the vehicle on the roadway without necessity.",
                "Stop where your position blocks passing movement.",
            ],
            "kk": [
                "Басқа жүргізушілердің көрінуін шектейтін жерде тоқтау.",
                "Жаяу жүргіншілер жолын бөгейтіндей тұрақтау.",
                "Қысқа тоқтау кезінде тыйым салу белгілерін елемеу.",
                "Қажетсіз жағдайда көлікті жүріс бөлігінде қалдыру.",
                "Қарсы разъезді қиындататын жерде тоқтау.",
            ],
        },
    },
    {
        "id": "pedestrians_passengers",
        "category": {"ru": "Пешеходы и пассажиры", "en": "Pedestrians and passengers", "kk": "Жаяу жүргіншілер мен жолаушылар"},
        "correct": {
            "ru": "Обеспечить безопасность пешеходов и пассажиров, при необходимости уступив дорогу.",
            "en": "Ensure pedestrian and passenger safety, yielding when required.",
            "kk": "Қажет болғанда жол беріп, жаяу жүргінші мен жолаушы қауіпсіздігін қамтамасыз ету.",
        },
        "wrong": {
            "ru": [
                "Ускоряться перед пешеходным переходом для «быстрого проезда».",
                "Открывать двери со стороны проезжей части без проверки обстановки.",
                "Игнорировать посадку и высадку пассажиров у остановок.",
                "Считать, что пешеход обязан всегда уступать автомобилю.",
                "Продолжать движение при риске для уязвимых участников.",
            ],
            "en": [
                "Accelerate before a crosswalk to pass quickly.",
                "Open doors toward traffic without checking surroundings.",
                "Ignore passenger boarding and alighting near stops.",
                "Assume pedestrians must always yield to vehicles.",
                "Keep moving despite risk for vulnerable road users.",
            ],
            "kk": [
                "Жаяу өткел алдында «тез өту» үшін үдеу.",
                "Жағдайды тексермей есікті жол жағына ашу.",
                "Аялдама маңындағы отырғызу-түсіруді елемеу.",
                "Жаяу жүргінші әрқашан көлікке жол беруі тиіс деп санау.",
                "Әлсіз қатысушыларға қауіп туса да қозғалысты жалғастыру.",
            ],
        },
    },
    {
        "id": "railway_crossing",
        "category": {"ru": "Железнодорожные переезды", "en": "Railway crossings", "kk": "Теміржол өткелдері"},
        "correct": {
            "ru": "Подъезжать к переезду с повышенной осторожностью и строго выполнять требования сигналов.",
            "en": "Approach railway crossings with extra caution and obey all crossing signals.",
            "kk": "Өткелге жоғары сақтықпен жақындап, барлық сигнал талаптарын қатаң орындау.",
        },
        "wrong": {
            "ru": [
                "Объезжать закрытый шлагбаум при отсутствии поезда в поле зрения.",
                "Продолжать движение на запрещающий сигнал переезда.",
                "Останавливаться на переезде в ожидании свободного потока.",
                "Игнорировать звуковую сигнализацию переезда.",
                "Начинать обгон непосредственно перед переездом.",
            ],
            "en": [
                "Drive around a closed barrier if no train is visible.",
                "Continue driving on a prohibitory crossing signal.",
                "Stop on the crossing while waiting for traffic to move.",
                "Ignore audible signals at the crossing.",
                "Start overtaking immediately before the crossing.",
            ],
            "kk": [
                "Поезд көрінбесе, жабық шлагбаумды айналып өту.",
                "Өткелдің тыйым сигналына қарамай жүруді жалғастыру.",
                "Ағын босауын күтіп, өткел үстінде тоқтап тұру.",
                "Өткелдің дыбыстық белгісін елемеу.",
                "Өткелдің дәл алдында озуды бастау.",
            ],
        },
    },
    {
        "id": "emergency_actions",
        "category": {"ru": "Аварийные ситуации", "en": "Emergency situations", "kk": "Апаттық жағдайлар"},
        "correct": {
            "ru": "Снизить скорость, обеспечить безопасность и принять меры для предупреждения других участников.",
            "en": "Reduce speed, secure safety, and warn other road users.",
            "kk": "Жылдамдықты азайтып, қауіпсіздікті қамтамасыз етіп, басқаларды алдын ала ескерту.",
        },
        "wrong": {
            "ru": [
                "Игнорировать опасность в надежде, что ситуация решится сама.",
                "Резко менять траекторию без оценки окружающего трафика.",
                "Оставлять неисправный автомобиль без обозначения.",
                "Продолжать движение при явной технической неисправности.",
                "Отказываться от использования предупредительных сигналов.",
            ],
            "en": [
                "Ignore danger hoping the situation resolves itself.",
                "Change trajectory abruptly without checking surrounding traffic.",
                "Leave a disabled vehicle without warning signs.",
                "Keep driving with an obvious technical failure.",
                "Refuse to use warning signals.",
            ],
            "kk": [
                "Қауіпті елемей, мәселе өздігінен шешіледі деп үміттену.",
                "Айналадағы ағынды бағаламай күрт траектория өзгерту.",
                "Ақаулы көлікті белгілемей қалдыру.",
                "Айқын техникалық ақаумен жүрісті жалғастыру.",
                "Ескерту сигналдарын қолданбау.",
            ],
        },
    },
    {
        "id": "driver_duty",
        "category": {"ru": "Ответственность водителя", "en": "Driver responsibilities", "kk": "Жүргізуші жауапкершілігі"},
        "correct": {
            "ru": "Соблюдать требования ПДД, контролировать состояние автомобиля и действовать ответственно.",
            "en": "Comply with traffic rules, monitor vehicle condition, and act responsibly.",
            "kk": "ЖҚЕ талаптарын сақтау, көлік жағдайын бақылау және жауапкершілікпен әрекет ету.",
        },
        "wrong": {
            "ru": [
                "Управлять автомобилем, если состояние водителя снижает безопасность.",
                "Выезжать в путь, не проверив исправность основных систем автомобиля.",
                "Игнорировать законные требования уполномоченных сотрудников.",
                "Считать, что осторожность необязательна при небольшом маршруте.",
                "Перекладывать ответственность за маневры на других участников.",
            ],
            "en": [
                "Drive when the driver's condition reduces safety.",
                "Start a trip without checking key vehicle systems.",
                "Ignore lawful requirements of authorized officers.",
                "Assume caution is unnecessary on a short route.",
                "Shift maneuver responsibility to other road users.",
            ],
            "kk": [
                "Жүргізуші жағдайы қауіпсіздікті төмендетсе де көлік басқару.",
                "Көліктің негізгі жүйелерін тексермей жолға шығу.",
                "Уәкілетті қызметкерлердің заңды талабын елемеу.",
                "Маршрут қысқа болса, сақтық қажет емес деп санау.",
                "Маневр үшін жауапкершілікті басқа қатысушыларға аудару.",
            ],
        },
    },
]


def build_questions_for_language(language: str) -> List[Dict]:
    if language not in ("ru", "en", "kk"):
        raise ValueError(f"Unsupported language: {language}")

    contexts = CONTEXTS[language]
    patterns = QUESTION_PATTERNS[language]
    questions: List[Dict] = []

    for topic_index, topic in enumerate(TOPICS):
        wrong_pool = topic["wrong"][language]
        topic_category = topic["category"][language]
        for context_index, context in enumerate(contexts):
            pattern = patterns[(topic_index + context_index) % len(patterns)]
            stem = pattern.format(context=context)
            if language == "ru":
                question_text = f"Тема «{topic_category}»: {stem}"
            elif language == "en":
                question_text = f"Topic \"{topic_category}\": {stem}"
            else:
                question_text = f"Тақырып «{topic_category}»: {stem}"

            # Rotate distractors to reduce repetitive ordering.
            start = (context_index * 2 + topic_index) % len(wrong_pool)
            distractors = [
                wrong_pool[start % len(wrong_pool)],
                wrong_pool[(start + 1) % len(wrong_pool)],
                wrong_pool[(start + 2) % len(wrong_pool)],
            ]

            answers = [
                {
                    "answer_text": topic["correct"][language],
                    "is_correct": True,
                    "explanation": {
                        "ru": "Верно: это базовое безопасное и правомерное действие в данной ситуации.",
                        "en": "Correct: this is the basic safe and lawful action in this situation.",
                        "kk": "Дұрыс: бұл жағдайда қауіпсіз және заңды негізгі әрекет осы.",
                    }[language],
                },
                {
                    "answer_text": distractors[0],
                    "is_correct": False,
                    "explanation": {
                        "ru": "Неверно: такое действие повышает риск и противоречит требованиям безопасного движения.",
                        "en": "Incorrect: this action increases risk and contradicts safe driving requirements.",
                        "kk": "Дұрыс емес: бұл әрекет қауіп-қатерді арттырып, қауіпсіз қозғалыс талаптарына қайшы келеді.",
                    }[language],
                },
                {
                    "answer_text": distractors[1],
                    "is_correct": False,
                    "explanation": {
                        "ru": "Неверно: это решение не обеспечивает безопасное выполнение требований ПДД.",
                        "en": "Incorrect: this decision does not ensure safe compliance with traffic rules.",
                        "kk": "Дұрыс емес: бұл шешім ЖҚЕ талаптарын қауіпсіз орындауды қамтамасыз етпейді.",
                    }[language],
                },
                {
                    "answer_text": distractors[2],
                    "is_correct": False,
                    "explanation": {
                        "ru": "Неверно: выбранный вариант не является приоритетным с точки зрения безопасности.",
                        "en": "Incorrect: this option is not the safety-priority behavior.",
                        "kk": "Дұрыс емес: бұл нұсқа қауіпсіздік тұрғысынан басым әрекет емес.",
                    }[language],
                },
            ]

            RNG.shuffle(answers)
            questions.append(
                {
                    "question_text": question_text,
                    "category": topic_category,
                    "language": language,
                    "answers": answers,
                }
            )

    if len(questions) != TARGET_PER_LANGUAGE:
        raise RuntimeError(f"Expected {TARGET_PER_LANGUAGE} questions for {language}, got {len(questions)}")

    return questions


def insert_questions(conn: sqlite3.Connection, language: str, questions: List[Dict]) -> Dict[str, int]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT question_text FROM questions WHERE COALESCE(NULLIF(language, ''), 'ru') = ?", (language,))
    existing_texts = {row["question_text"].strip() for row in cur.fetchall()}

    inserted = 0
    skipped = 0

    for payload in questions:
        key = payload["question_text"].strip()
        if key in existing_texts:
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO questions (question_text, category, language, image_url, points)
            VALUES (?, ?, ?, NULL, 1)
            """,
            (payload["question_text"], payload["category"], payload["language"]),
        )
        question_id = cur.lastrowid

        for answer in payload["answers"]:
            cur.execute(
                """
                INSERT INTO answers (question_id, answer_text, is_correct, explanation)
                VALUES (?, ?, ?, ?)
                """,
                (
                    question_id,
                    answer["answer_text"],
                    1 if answer["is_correct"] else 0,
                    answer["explanation"],
                ),
            )

        existing_texts.add(key)
        inserted += 1

    return {"inserted": inserted, "skipped": skipped}


def check_integrity(conn: sqlite3.Connection) -> int:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id, q.question_text,
               COUNT(a.id) AS answers_count,
               SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
        FROM questions q
        LEFT JOIN answers a ON a.question_id = q.id
        GROUP BY q.id
        HAVING answers_count <> 4 OR correct_count <> 1
        """
    )
    rows = cur.fetchall()
    return len(rows)


def print_language_stats(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(NULLIF(language, ''), 'ru') AS lang, COUNT(*) AS total
        FROM questions
        GROUP BY COALESCE(NULLIF(language, ''), 'ru')
        ORDER BY lang
        """
    )
    print("Questions by language:")
    for row in cur.fetchall():
        print(f"  - {row['lang']}: {row['total']}")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM questions")
    before_total_questions = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM answers")
    before_total_answers = int(cur.fetchone()[0])

    summary: Dict[str, Dict[str, int]] = {}
    for language in ("ru", "en", "kk"):
        questions = build_questions_for_language(language)
        result = insert_questions(conn, language, questions)
        summary[language] = result

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM questions")
    after_total_questions = int(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM answers")
    after_total_answers = int(cur.fetchone()[0])

    invalid_count = check_integrity(conn)
    print(f"Before questions: {before_total_questions}")
    print(f"After questions:  {after_total_questions}")
    print(f"Added questions:  {after_total_questions - before_total_questions}")
    print(f"Before answers:   {before_total_answers}")
    print(f"After answers:    {after_total_answers}")
    print(f"Added answers:    {after_total_answers - before_total_answers}")
    for language in ("ru", "en", "kk"):
        print(f"{language}: inserted={summary[language]['inserted']}, skipped={summary[language]['skipped']}")
    print(f"Integrity issues (must be 0): {invalid_count}")
    print_language_stats(conn)

    conn.close()


if __name__ == "__main__":
    main()
