from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import hashlib
import json
import os
import random
import sqlite3
from datetime import datetime

router = APIRouter()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdd_questions.db")
PB_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "backend_service",
    "pb_data",
    "data.db",
)

ADMIN_EMAIL = "admin@pdd.local"
ADMIN_PASSWORD = "AdminPDD2026!"
ADMIN_TOKEN = hashlib.sha256(
    f"{ADMIN_EMAIL}:{ADMIN_PASSWORD}:pdd-admin-secret".encode("utf-8")
).hexdigest()


class Answer(BaseModel):
    id: int
    answer_text: str
    is_correct: bool
    explanation: Optional[str] = None


class Question(BaseModel):
    id: int
    question_text: str
    category: str
    image_url: Optional[str] = None
    answers: List[Answer] = []


class TestSubmission(BaseModel):
    user_id: str
    category: str
    answers: Dict[str, int]


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminQuestionAnswerInput(BaseModel):
    answer_text: str
    is_correct: bool = False
    explanation: Optional[str] = ""


class AdminQuestionPayload(BaseModel):
    question_text: str
    category: str
    image_url: Optional[str] = ""
    answers: List[AdminQuestionAnswerInput] = Field(default_factory=list)


class CreateAdminTestRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    question_ids: List[int] = Field(default_factory=list)
    question_limit: Optional[int] = None
    randomize_questions: bool = True
    randomize_answers: bool = False
    pass_score: int = 70


class UpdateAdminTestRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    question_ids: Optional[List[int]] = None
    question_limit: Optional[int] = None
    randomize_questions: Optional[bool] = None
    randomize_answers: Optional[bool] = None
    pass_score: Optional[int] = None


class AssignTestRequest(BaseModel):
    test_id: int
    user_id: str
    user_email: str
    mode: str = "exam"
    question_limit: Optional[int] = None
    randomize_questions: Optional[bool] = None
    randomize_answers: Optional[bool] = None
    pass_score: Optional[int] = None


class AssignedTestSubmission(BaseModel):
    user_id: str
    question_ids: List[int] = Field(default_factory=list)
    answers: Dict[str, int]
    duration_seconds: Optional[int] = None


class TestResult(BaseModel):
    id: int
    user_id: str
    category: str
    total_questions: int
    correct_answers: int
    score: int
    test_date: str


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pb_db_connection():
    if not os.path.exists(PB_DB_PATH):
        raise HTTPException(status_code=500, detail="PocketBase database not found")
    conn = sqlite3.connect(PB_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def require_admin(x_admin_token: Optional[str]):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin access denied")


def _ensure_column(cursor, table_name: str, column_name: str, column_definition: str):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def _safe_json_load(raw_value: Optional[str], fallback: Any):
    if not raw_value:
        return fallback
    try:
        return json.loads(raw_value)
    except Exception:
        return fallback


def _normalize_bool(value: Optional[bool], default: bool) -> int:
    if value is None:
        return 1 if default else 0
    return 1 if bool(value) else 0


def _clean_mode(raw_mode: str) -> str:
    mode = (raw_mode or "exam").strip().lower()
    if mode not in {"exam", "training"}:
        raise HTTPException(status_code=400, detail="Mode must be 'exam' or 'training'")
    return mode


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _dedupe_int_list(values: List[int]) -> List[int]:
    result: List[int] = []
    seen = set()
    for value in values:
        try:
            parsed = int(value)
        except Exception:
            continue
        if parsed not in seen:
            result.append(parsed)
            seen.add(parsed)
    return result


def _normalize_answer_map(raw_answers: Dict[str, int]) -> Dict[int, int]:
    parsed_answers: Dict[int, int] = {}
    for key, value in raw_answers.items():
        try:
            question_id = int(key)
            answer_id = int(value)
        except Exception:
            continue
        parsed_answers[question_id] = answer_id
    return parsed_answers


def _validate_question_payload(payload: AdminQuestionPayload):
    if not payload.question_text.strip():
        raise HTTPException(status_code=400, detail="Question text is required")

    if not payload.category.strip():
        raise HTTPException(status_code=400, detail="Category is required")

    if len(payload.answers) < 2:
        raise HTTPException(status_code=400, detail="At least 2 answer options are required")

    correct_answers = [answer for answer in payload.answers if answer.is_correct]
    if len(correct_answers) != 1:
        raise HTTPException(status_code=400, detail="Exactly one answer must be correct")

    for answer in payload.answers:
        if not answer.answer_text.strip():
            raise HTTPException(status_code=400, detail="Answer text cannot be empty")


def _fetch_questions_by_ids(
    cursor,
    question_ids: List[int],
    include_correct: bool,
    randomize_answers: bool = False,
) -> List[dict]:
    if not question_ids:
        return []

    placeholders = ",".join(["?"] * len(question_ids))
    cursor.execute(
        f"""
        SELECT id, question_text, category, image_url
        FROM questions
        WHERE id IN ({placeholders})
        """,
        question_ids,
    )

    questions_map = {row["id"]: row for row in cursor.fetchall()}
    ordered_questions: List[dict] = []

    for question_id in question_ids:
        row = questions_map.get(question_id)
        if row is None:
            continue

        cursor.execute(
            """
            SELECT id, answer_text, is_correct, explanation
            FROM answers
            WHERE question_id = ?
            ORDER BY id
            """,
            (question_id,),
        )

        answers = []
        for answer in cursor.fetchall():
            answer_payload = {
                "id": answer["id"],
                "answer_text": answer["answer_text"],
            }
            if include_correct:
                answer_payload["is_correct"] = bool(answer["is_correct"])
                answer_payload["explanation"] = answer["explanation"]
            answers.append(answer_payload)

        if randomize_answers:
            random.shuffle(answers)

        ordered_questions.append(
            {
                "id": row["id"],
                "question_text": row["question_text"],
                "category": row["category"],
                "image_url": row["image_url"],
                "answers": answers,
            }
        )

    return ordered_questions


def _resolve_test_question_ids(cursor, test_id: int, is_legacy: bool) -> List[int]:
    if is_legacy:
        cursor.execute("SELECT id FROM questions ORDER BY id")
        return [row["id"] for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT question_id
        FROM admin_test_questions
        WHERE test_id = ?
        ORDER BY question_order ASC, id ASC
        """,
        (test_id,),
    )
    return [row["question_id"] for row in cursor.fetchall()]


def _build_category_stats(rows: List[dict]) -> List[dict]:
    stats_by_category: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        category = row["category"]
        if category not in stats_by_category:
            stats_by_category[category] = {"category": category, "total": 0, "correct": 0, "wrong": 0}

        stats_by_category[category]["total"] += 1
        if row["is_correct"]:
            stats_by_category[category]["correct"] += 1
        else:
            stats_by_category[category]["wrong"] += 1

    stats = []
    for payload in stats_by_category.values():
        total = payload["total"]
        wrong = payload["wrong"]
        payload["error_rate"] = round((wrong * 100 / total), 1) if total > 0 else 0
        stats.append(payload)

    stats.sort(key=lambda item: (item["wrong"], item["error_rate"]), reverse=True)
    return stats


def _build_recommendations(category_stats: List[dict], wrong_questions: List[dict]) -> List[str]:
    recommendations: List[str] = []

    if not wrong_questions:
        recommendations.append("Ошибок нет. Можно переходить к более сложным тестам.")
        return recommendations

    weak_categories = [item for item in category_stats if item["wrong"] > 0]
    if weak_categories:
        top = weak_categories[0]
        recommendations.append(
            f"Сфокусируйся на категории '{top['category']}' — здесь больше всего ошибок ({top['wrong']})."
        )

    if len(weak_categories) > 1:
        second = weak_categories[1]
        recommendations.append(
            f"После этого повтори категорию '{second['category']}' (ошибок: {second['wrong']})."
        )

    recommendations.append(
        "Разбери пояснения к ошибкам и пройди тест еще раз в режиме обучения для закрепления."
    )

    return recommendations


def _aggregate_attempts(rows: List[sqlite3.Row]) -> Dict[str, Any]:
    attempts = []
    category_totals: Dict[str, Dict[str, Any]] = {}
    scores: List[int] = []
    mode_counts = {"exam": 0, "training": 0}

    for row in rows:
        category_stats = _safe_json_load(row["category_stats"], [])
        wrong_questions = _safe_json_load(row["wrong_questions"], [])
        recommendations = _safe_json_load(row["recommendations"], [])

        attempt_payload = {
            "attempt_id": row["id"],
            "assignment_id": row["assignment_id"],
            "test_id": row["test_id"],
            "test_title": row["test_title"],
            "mode": row["mode"],
            "attempt_number": row["attempt_number"],
            "total_questions": row["total_questions"],
            "correct_answers": row["correct_answers"],
            "wrong_answers": row["wrong_answers"],
            "score": row["score"],
            "passed": bool(row["passed"]),
            "pass_score": row["pass_score"],
            "duration_seconds": row["duration_seconds"],
            "created_at": row["created_at"],
            "category_stats": category_stats,
            "wrong_questions": wrong_questions,
            "recommendations": recommendations,
        }
        attempts.append(attempt_payload)

        scores.append(row["score"])
        if row["mode"] in mode_counts:
            mode_counts[row["mode"]] += 1

        for item in category_stats:
            category = item["category"]
            if category not in category_totals:
                category_totals[category] = {
                    "category": category,
                    "total": 0,
                    "correct": 0,
                    "wrong": 0,
                }
            category_totals[category]["total"] += item.get("total", 0)
            category_totals[category]["correct"] += item.get("correct", 0)
            category_totals[category]["wrong"] += item.get("wrong", 0)

    summary_categories = []
    for item in category_totals.values():
        total = item["total"]
        wrong = item["wrong"]
        item["error_rate"] = round((wrong * 100 / total), 1) if total > 0 else 0
        summary_categories.append(item)

    summary_categories.sort(key=lambda payload: (payload["wrong"], payload["error_rate"]), reverse=True)

    total_attempts = len(attempts)
    avg_score = round(sum(scores) / total_attempts, 1) if total_attempts > 0 else 0
    best_score = max(scores) if scores else 0

    return {
        "summary": {
            "total_attempts": total_attempts,
            "average_score": avg_score,
            "best_score": best_score,
            "mode_counts": mode_counts,
            "categories": summary_categories,
        },
        "attempts": attempts,
    }


def _build_attempt_questions_review(cursor, question_ids: List[int], answer_map: Dict[int, int]) -> List[dict]:
    questions = _fetch_questions_by_ids(
        cursor,
        question_ids,
        include_correct=True,
        randomize_answers=False,
    )

    review_items: List[dict] = []
    for question in questions:
        question_id = int(question["id"])
        selected_answer_id = answer_map.get(question_id)

        selected_answer = None
        correct_answer = None
        answers_payload = []
        for answer in question["answers"]:
            is_selected = selected_answer_id is not None and int(answer["id"]) == int(selected_answer_id)
            answer_payload = {
                "id": answer["id"],
                "answer_text": answer["answer_text"],
                "is_correct": bool(answer.get("is_correct", False)),
                "is_selected": is_selected,
                "explanation": answer.get("explanation") or "",
            }
            answers_payload.append(answer_payload)

            if answer_payload["is_selected"]:
                selected_answer = answer_payload
            if answer_payload["is_correct"]:
                correct_answer = answer_payload

        review_items.append(
            {
                "question_id": question_id,
                "question_text": question["question_text"],
                "category": question["category"],
                "image_url": question.get("image_url"),
                "selected_answer_id": selected_answer_id,
                "selected_answer_text": selected_answer["answer_text"] if selected_answer else "Не выбран",
                "correct_answer_id": correct_answer["id"] if correct_answer else None,
                "correct_answer_text": correct_answer["answer_text"] if correct_answer else "",
                "is_correct": bool(selected_answer and selected_answer.get("is_correct")),
                "answers": answers_payload,
            }
        )

    return review_items


def _initialize_admin_schema():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_legacy INTEGER DEFAULT 0,
            question_limit INTEGER DEFAULT 20,
            randomize_questions INTEGER DEFAULT 1,
            randomize_answers INTEGER DEFAULT 0,
            pass_score INTEGER DEFAULT 70,
            created_by TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_test_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            question_order INTEGER DEFAULT 0,
            FOREIGN KEY (test_id) REFERENCES admin_tests(id),
            FOREIGN KEY (question_id) REFERENCES questions(id),
            UNIQUE(test_id, question_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            user_email TEXT NOT NULL,
            assigned_by TEXT NOT NULL,
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            last_score INTEGER,
            attempts INTEGER DEFAULT 0,
            mode TEXT DEFAULT 'exam',
            max_attempts INTEGER,
            question_limit INTEGER DEFAULT 20,
            randomize_questions INTEGER DEFAULT 1,
            randomize_answers INTEGER DEFAULT 0,
            pass_score INTEGER DEFAULT 70,
            allow_review INTEGER DEFAULT 1,
            FOREIGN KEY (test_id) REFERENCES admin_tests(id),
            UNIQUE(test_id, user_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS test_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            test_id INTEGER,
            user_id TEXT NOT NULL,
            user_email TEXT,
            mode TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            wrong_answers INTEGER NOT NULL,
            score INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            pass_score INTEGER NOT NULL,
            duration_seconds INTEGER,
            answers_snapshot TEXT,
            question_ids_snapshot TEXT,
            category_stats TEXT,
            wrong_questions TEXT,
            recommendations TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignment_id) REFERENCES admin_assignments(id),
            FOREIGN KEY (test_id) REFERENCES admin_tests(id)
        )
        """
    )

    _ensure_column(cur, "test_results", "assigned_test_id", "assigned_test_id INTEGER")
    _ensure_column(cur, "admin_tests", "randomize_questions", "randomize_questions INTEGER DEFAULT 1")
    _ensure_column(cur, "admin_tests", "randomize_answers", "randomize_answers INTEGER DEFAULT 0")
    _ensure_column(cur, "admin_tests", "pass_score", "pass_score INTEGER DEFAULT 70")

    _ensure_column(cur, "admin_assignments", "mode", "mode TEXT DEFAULT 'exam'")
    _ensure_column(cur, "admin_assignments", "max_attempts", "max_attempts INTEGER")
    _ensure_column(cur, "admin_assignments", "question_limit", "question_limit INTEGER DEFAULT 20")
    _ensure_column(cur, "admin_assignments", "randomize_questions", "randomize_questions INTEGER DEFAULT 1")
    _ensure_column(cur, "admin_assignments", "randomize_answers", "randomize_answers INTEGER DEFAULT 0")
    _ensure_column(cur, "admin_assignments", "pass_score", "pass_score INTEGER DEFAULT 70")
    _ensure_column(cur, "admin_assignments", "allow_review", "allow_review INTEGER DEFAULT 1")

    cur.execute("SELECT id FROM admin_tests WHERE is_legacy = 1 LIMIT 1")
    legacy_test = cur.fetchone()

    if legacy_test is None:
        cur.execute(
            """
            INSERT INTO admin_tests (
                title,
                description,
                is_legacy,
                question_limit,
                randomize_questions,
                randomize_answers,
                pass_score,
                created_by
            )
            VALUES (?, ?, 1, 20, 1, 0, 70, 'system')
            """,
            (
                "Общий тест ПДД",
                "Системный тест из существующей базы вопросов (случайные 20 вопросов).",
            ),
        )

    conn.commit()
    conn.close()


_initialize_admin_schema()


@router.post("/admin/login")
async def admin_login(payload: AdminLoginRequest):
    if payload.email != ADMIN_EMAIL or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль администратора")

    return {"role": "admin", "email": ADMIN_EMAIL, "token": ADMIN_TOKEN}


@router.get("/admin/users")
async def admin_get_users(
    search: str = "",
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_pb_db_connection()
    cur = conn.cursor()

    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        cur.execute(
            """
            SELECT id, email, name, created
            FROM users
            WHERE lower(email) LIKE ? OR lower(name) LIKE ?
            ORDER BY created DESC
            """,
            (pattern, pattern),
        )
    else:
        cur.execute(
            """
            SELECT id, email, name, created
            FROM users
            ORDER BY created DESC
            """
        )

    users = [
        {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "created": row["created"],
        }
        for row in cur.fetchall()
    ]

    conn.close()
    return {"users": users}


@router.get("/admin/categories")
async def admin_get_categories(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM questions ORDER BY category")
    categories = [row["category"] for row in cur.fetchall()]
    conn.close()
    return {"categories": categories}


@router.get("/admin/questions")
async def admin_get_questions(
    search: str = "",
    category: str = "all",
    include_answers: bool = True,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT id, question_text, category, image_url FROM questions WHERE 1=1"
    params: List[Any] = []

    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        query += " AND (lower(question_text) LIKE ? OR CAST(id AS TEXT) LIKE ?)"
        params.extend([pattern, pattern])

    if category.strip().lower() != "all":
        query += " AND category = ?"
        params.append(category.strip())

    query += " ORDER BY category, id"
    cur.execute(query, params)

    questions = []
    for row in cur.fetchall():
        payload = {
            "id": row["id"],
            "question_text": row["question_text"],
            "category": row["category"],
            "image_url": row["image_url"],
        }

        if include_answers:
            cur.execute(
                """
                SELECT id, answer_text, is_correct, explanation
                FROM answers
                WHERE question_id = ?
                ORDER BY id
                """,
                (row["id"],),
            )
            payload["answers"] = [
                {
                    "id": item["id"],
                    "answer_text": item["answer_text"],
                    "is_correct": bool(item["is_correct"]),
                    "explanation": item["explanation"],
                }
                for item in cur.fetchall()
            ]

        questions.append(payload)

    conn.close()
    return {"questions": questions}


@router.post("/admin/questions")
async def admin_create_question(
    payload: AdminQuestionPayload,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)
    _validate_question_payload(payload)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO questions (question_text, category, image_url, points)
        VALUES (?, ?, ?, 1)
        """,
        (payload.question_text.strip(), payload.category.strip(), (payload.image_url or "").strip() or None),
    )
    question_id = cur.lastrowid

    for answer in payload.answers:
        cur.execute(
            """
            INSERT INTO answers (question_id, answer_text, is_correct, explanation)
            VALUES (?, ?, ?, ?)
            """,
            (
                question_id,
                answer.answer_text.strip(),
                1 if answer.is_correct else 0,
                (answer.explanation or "").strip(),
            ),
        )

    conn.commit()
    conn.close()

    return {"ok": True, "question_id": question_id}


@router.put("/admin/questions/{question_id}")
async def admin_update_question(
    question_id: int,
    payload: AdminQuestionPayload,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)
    _validate_question_payload(payload)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM questions WHERE id = ?", (question_id,))
    if cur.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")

    cur.execute(
        """
        UPDATE questions
        SET question_text = ?, category = ?, image_url = ?
        WHERE id = ?
        """,
        (
            payload.question_text.strip(),
            payload.category.strip(),
            (payload.image_url or "").strip() or None,
            question_id,
        ),
    )

    cur.execute("DELETE FROM answers WHERE question_id = ?", (question_id,))

    for answer in payload.answers:
        cur.execute(
            """
            INSERT INTO answers (question_id, answer_text, is_correct, explanation)
            VALUES (?, ?, ?, ?)
            """,
            (
                question_id,
                answer.answer_text.strip(),
                1 if answer.is_correct else 0,
                (answer.explanation or "").strip(),
            ),
        )

    conn.commit()
    conn.close()
    return {"ok": True}


@router.delete("/admin/questions/{question_id}")
async def admin_delete_question(
    question_id: int,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM questions WHERE id = ?", (question_id,))
    if cur.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")

    cur.execute("DELETE FROM admin_test_questions WHERE question_id = ?", (question_id,))
    cur.execute("DELETE FROM answers WHERE question_id = ?", (question_id,))
    cur.execute("DELETE FROM questions WHERE id = ?", (question_id,))

    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/admin/tests")
async def admin_get_tests(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            t.id,
            t.title,
            t.description,
            t.is_legacy,
            t.question_limit,
            t.randomize_questions,
            t.randomize_answers,
            t.pass_score,
            t.created_by,
            t.created_at,
            COUNT(q.id) as custom_questions
        FROM admin_tests t
        LEFT JOIN admin_test_questions q ON q.test_id = t.id
        GROUP BY
            t.id,
            t.title,
            t.description,
            t.is_legacy,
            t.question_limit,
            t.randomize_questions,
            t.randomize_answers,
            t.pass_score,
            t.created_by,
            t.created_at
        ORDER BY t.created_at DESC, t.id DESC
        """
    )
    rows = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM questions")
    total_pool = cur.fetchone()[0]

    tests = []
    for row in rows:
        if row["is_legacy"]:
            question_count = min(row["question_limit"], total_pool)
        else:
            question_count = row["custom_questions"]

        tests.append(
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "is_legacy": bool(row["is_legacy"]),
                "question_limit": row["question_limit"],
                "randomize_questions": bool(row["randomize_questions"]),
                "randomize_answers": bool(row["randomize_answers"]),
                "pass_score": row["pass_score"],
                "question_count": question_count,
                "created_by": row["created_by"],
                "created_at": row["created_at"],
            }
        )

    conn.close()
    return {"tests": tests}


@router.get("/admin/tests/{test_id}")
async def admin_get_test_details(
    test_id: int,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM admin_tests WHERE id = ?", (test_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Test not found")

    question_ids = _resolve_test_question_ids(cur, test_id, bool(row["is_legacy"]))
    questions = _fetch_questions_by_ids(cur, question_ids, include_correct=True, randomize_answers=False)

    conn.close()

    return {
        "test": {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "is_legacy": bool(row["is_legacy"]),
            "question_limit": row["question_limit"],
            "randomize_questions": bool(row["randomize_questions"]),
            "randomize_answers": bool(row["randomize_answers"]),
            "pass_score": row["pass_score"],
            "question_ids": question_ids,
            "questions": questions,
        }
    }


@router.post("/admin/tests")
async def admin_create_test(
    payload: CreateAdminTestRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Test title is required")

    question_ids = _dedupe_int_list(payload.question_ids)
    if len(question_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 questions")

    conn = get_db_connection()
    cur = conn.cursor()

    placeholders = ",".join(["?"] * len(question_ids))
    cur.execute(f"SELECT COUNT(*) FROM questions WHERE id IN ({placeholders})", question_ids)
    found = cur.fetchone()[0]
    if found != len(question_ids):
        conn.close()
        raise HTTPException(status_code=400, detail="Some questions were not found")

    question_limit = payload.question_limit if payload.question_limit is not None else len(question_ids)
    question_limit = max(1, min(question_limit, len(question_ids)))
    pass_score = max(0, min(payload.pass_score, 100))

    cur.execute(
        """
        INSERT INTO admin_tests (
            title,
            description,
            is_legacy,
            question_limit,
            randomize_questions,
            randomize_answers,
            pass_score,
            created_by
        )
        VALUES (?, ?, 0, ?, ?, ?, ?, 'admin')
        """,
        (
            title,
            (payload.description or "").strip(),
            question_limit,
            _normalize_bool(payload.randomize_questions, True),
            _normalize_bool(payload.randomize_answers, False),
            pass_score,
        ),
    )
    test_id = cur.lastrowid

    for index, question_id in enumerate(question_ids):
        cur.execute(
            """
            INSERT INTO admin_test_questions (test_id, question_id, question_order)
            VALUES (?, ?, ?)
            """,
            (test_id, question_id, index),
        )

    conn.commit()
    conn.close()

    return {"ok": True, "test_id": test_id}


@router.put("/admin/tests/{test_id}")
async def admin_update_test(
    test_id: int,
    payload: UpdateAdminTestRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM admin_tests WHERE id = ?", (test_id,))
    test_row = cur.fetchone()
    if test_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Test not found")

    is_legacy = bool(test_row["is_legacy"])

    title = payload.title.strip() if payload.title is not None else test_row["title"]
    if not title:
        conn.close()
        raise HTTPException(status_code=400, detail="Test title is required")

    description = payload.description if payload.description is not None else test_row["description"]

    if is_legacy:
        question_ids = []
        cur.execute("SELECT COUNT(*) FROM questions")
        max_pool = cur.fetchone()[0]
    else:
        if payload.question_ids is None:
            cur.execute(
                """
                SELECT question_id
                FROM admin_test_questions
                WHERE test_id = ?
                ORDER BY question_order ASC, id ASC
                """,
                (test_id,),
            )
            question_ids = [row["question_id"] for row in cur.fetchall()]
        else:
            question_ids = _dedupe_int_list(payload.question_ids)

        if len(question_ids) < 2:
            conn.close()
            raise HTTPException(status_code=400, detail="Select at least 2 questions")

        placeholders = ",".join(["?"] * len(question_ids))
        cur.execute(f"SELECT COUNT(*) FROM questions WHERE id IN ({placeholders})", question_ids)
        found = cur.fetchone()[0]
        if found != len(question_ids):
            conn.close()
            raise HTTPException(status_code=400, detail="Some questions were not found")

        max_pool = len(question_ids)

    question_limit_candidate = payload.question_limit if payload.question_limit is not None else test_row["question_limit"]
    question_limit = max(1, min(int(question_limit_candidate), max_pool if max_pool > 0 else 1))

    randomize_questions = _normalize_bool(payload.randomize_questions, bool(test_row["randomize_questions"]))
    randomize_answers = _normalize_bool(payload.randomize_answers, bool(test_row["randomize_answers"]))

    pass_score_candidate = payload.pass_score if payload.pass_score is not None else test_row["pass_score"]
    pass_score = max(0, min(int(pass_score_candidate), 100))

    cur.execute(
        """
        UPDATE admin_tests
        SET title = ?,
            description = ?,
            question_limit = ?,
            randomize_questions = ?,
            randomize_answers = ?,
            pass_score = ?
        WHERE id = ?
        """,
        (
            title,
            (description or "").strip(),
            question_limit,
            randomize_questions,
            randomize_answers,
            pass_score,
            test_id,
        ),
    )

    if not is_legacy:
        cur.execute("DELETE FROM admin_test_questions WHERE test_id = ?", (test_id,))
        for index, question_id in enumerate(question_ids):
            cur.execute(
                """
                INSERT INTO admin_test_questions (test_id, question_id, question_order)
                VALUES (?, ?, ?)
                """,
                (test_id, question_id, index),
            )

    conn.commit()
    conn.close()

    return {"ok": True}


@router.post("/admin/assign")
async def admin_assign_test(
    payload: AssignTestRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)
    mode = _clean_mode(payload.mode)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM admin_tests WHERE id = ?", (payload.test_id,))
    test_row = cur.fetchone()
    if test_row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Test not found")

    question_ids = _resolve_test_question_ids(cur, payload.test_id, bool(test_row["is_legacy"]))

    if bool(test_row["is_legacy"]):
        cur.execute("SELECT COUNT(*) FROM questions")
        available_questions = cur.fetchone()[0]
    else:
        available_questions = len(question_ids)

    base_limit = payload.question_limit if payload.question_limit is not None else test_row["question_limit"]
    question_limit = max(1, min(int(base_limit), max(1, available_questions)))

    randomize_questions = _normalize_bool(payload.randomize_questions, bool(test_row["randomize_questions"]))
    randomize_answers = _normalize_bool(payload.randomize_answers, bool(test_row["randomize_answers"]))

    base_pass_score = payload.pass_score if payload.pass_score is not None else test_row["pass_score"]
    pass_score = max(0, min(int(base_pass_score), 100))

    max_attempts = 1 if mode == "exam" else None
    allow_review = 1 if mode == "training" else 0
    now = _now_iso()

    cur.execute(
        """
        INSERT INTO admin_assignments (
            test_id,
            user_id,
            user_email,
            assigned_by,
            assigned_at,
            completed_at,
            last_score,
            attempts,
            mode,
            max_attempts,
            question_limit,
            randomize_questions,
            randomize_answers,
            pass_score,
            allow_review
        )
        VALUES (?, ?, ?, 'admin', ?, NULL, NULL, 0, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(test_id, user_id) DO UPDATE SET
            user_email = excluded.user_email,
            assigned_by = excluded.assigned_by,
            assigned_at = excluded.assigned_at,
            completed_at = NULL,
            last_score = NULL,
            attempts = 0,
            mode = excluded.mode,
            max_attempts = excluded.max_attempts,
            question_limit = excluded.question_limit,
            randomize_questions = excluded.randomize_questions,
            randomize_answers = excluded.randomize_answers,
            pass_score = excluded.pass_score,
            allow_review = excluded.allow_review
        """,
        (
            payload.test_id,
            payload.user_id,
            payload.user_email,
            now,
            mode,
            max_attempts,
            question_limit,
            randomize_questions,
            randomize_answers,
            pass_score,
            allow_review,
        ),
    )

    conn.commit()
    conn.close()

    return {"ok": True}


@router.get("/admin/assignments")
async def admin_get_assignments(
    user_id: str = "",
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT
            a.id,
            a.user_id,
            a.user_email,
            a.assigned_at,
            a.completed_at,
            a.last_score,
            a.attempts,
            a.mode,
            a.max_attempts,
            a.question_limit,
            a.randomize_questions,
            a.randomize_answers,
            a.pass_score,
            t.id as test_id,
            t.title as test_title
        FROM admin_assignments a
        JOIN admin_tests t ON t.id = a.test_id
    """
    params: List[Any] = []

    if user_id.strip():
        query += " WHERE a.user_id = ? "
        params.append(user_id.strip())

    query += " ORDER BY a.assigned_at DESC, a.id DESC"

    cur.execute(query, params)
    rows = cur.fetchall()

    assignments = [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "user_email": row["user_email"],
            "assigned_at": row["assigned_at"],
            "completed_at": row["completed_at"],
            "last_score": row["last_score"],
            "attempts": row["attempts"],
            "mode": row["mode"],
            "max_attempts": row["max_attempts"],
            "question_limit": row["question_limit"],
            "randomize_questions": bool(row["randomize_questions"]),
            "randomize_answers": bool(row["randomize_answers"]),
            "pass_score": row["pass_score"],
            "test_id": row["test_id"],
            "test_title": row["test_title"],
        }
        for row in rows
    ]

    conn.close()
    return {"assignments": assignments}


@router.get("/admin/users/{user_id}/analytics")
async def admin_user_analytics(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ta.*,
            t.title as test_title
        FROM test_attempts ta
        LEFT JOIN admin_tests t ON t.id = ta.test_id
        WHERE ta.user_id = ?
        ORDER BY ta.created_at DESC, ta.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )

    rows = cur.fetchall()
    payload = _aggregate_attempts(rows)
    conn.close()
    return payload


@router.get("/admin/attempts/{attempt_id}")
async def admin_attempt_details(
    attempt_id: int,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    require_admin(x_admin_token)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ta.*,
            t.title AS test_title
        FROM test_attempts ta
        LEFT JOIN admin_tests t ON t.id = ta.test_id
        WHERE ta.id = ?
        LIMIT 1
        """,
        (attempt_id,),
    )
    row = cur.fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Attempt not found")

    raw_question_ids = _safe_json_load(row["question_ids_snapshot"], [])
    question_ids = _dedupe_int_list(raw_question_ids if isinstance(raw_question_ids, list) else [])

    raw_answer_map = _safe_json_load(row["answers_snapshot"], {})
    answer_map: Dict[int, int] = {}
    if isinstance(raw_answer_map, dict):
        answer_map = _normalize_answer_map(raw_answer_map)

    if not question_ids:
        question_ids = list(answer_map.keys())

    review_questions = _build_attempt_questions_review(cur, question_ids, answer_map)
    wrong_questions = _safe_json_load(row["wrong_questions"], [])
    recommendations = _safe_json_load(row["recommendations"], [])
    category_stats = _safe_json_load(row["category_stats"], [])

    conn.close()

    return {
        "attempt": {
            "attempt_id": row["id"],
            "assignment_id": row["assignment_id"],
            "test_id": row["test_id"],
            "test_title": row["test_title"],
            "user_id": row["user_id"],
            "user_email": row["user_email"],
            "mode": row["mode"],
            "attempt_number": row["attempt_number"],
            "total_questions": row["total_questions"],
            "correct_answers": row["correct_answers"],
            "wrong_answers": row["wrong_answers"],
            "score": row["score"],
            "pass_score": row["pass_score"],
            "passed": bool(row["passed"]),
            "duration_seconds": row["duration_seconds"],
            "created_at": row["created_at"],
            "category_stats": category_stats,
            "wrong_questions": wrong_questions,
            "recommendations": recommendations,
            "questions": review_questions,
        }
    }


@router.get("/my/tests/{user_id}")
async def get_my_tests(user_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.id as assignment_id,
            a.user_id,
            a.user_email,
            a.assigned_at,
            a.completed_at,
            a.last_score,
            a.attempts,
            a.mode,
            a.max_attempts,
            a.question_limit,
            a.randomize_questions,
            a.randomize_answers,
            a.pass_score,
            t.id as test_id,
            t.title,
            t.description,
            t.is_legacy
        FROM admin_assignments a
        JOIN admin_tests t ON t.id = a.test_id
        WHERE a.user_id = ?
        ORDER BY a.assigned_at DESC
        """,
        (user_id,),
    )

    assignments = [
        {
            "assignment_id": row["assignment_id"],
            "test_id": row["test_id"],
            "title": row["title"],
            "description": row["description"],
            "is_legacy": bool(row["is_legacy"]),
            "question_limit": row["question_limit"],
            "mode": row["mode"],
            "max_attempts": row["max_attempts"],
            "attempts": row["attempts"],
            "pass_score": row["pass_score"],
            "randomize_questions": bool(row["randomize_questions"]),
            "randomize_answers": bool(row["randomize_answers"]),
            "assigned_at": row["assigned_at"],
            "completed_at": row["completed_at"],
            "last_score": row["last_score"],
            "user_email": row["user_email"],
        }
        for row in cur.fetchall()
    ]

    conn.close()
    return {"tests": assignments}


@router.get("/my/tests/{assignment_id}/questions")
async def get_assigned_test_questions(assignment_id: int, user_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.*,
            t.title,
            t.is_legacy
        FROM admin_assignments a
        JOIN admin_tests t ON t.id = a.test_id
        WHERE a.id = ? AND a.user_id = ?
        """,
        (assignment_id, user_id),
    )
    assignment = cur.fetchone()

    if assignment is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Assigned test not found")

    max_attempts = assignment["max_attempts"]
    attempts_used = assignment["attempts"]
    if max_attempts is not None and attempts_used >= max_attempts:
        conn.close()
        raise HTTPException(status_code=403, detail="Exam attempt limit reached")

    question_ids = _resolve_test_question_ids(cur, assignment["test_id"], bool(assignment["is_legacy"]))
    if not question_ids:
        conn.close()
        raise HTTPException(status_code=400, detail="This test has no questions")

    if bool(assignment["randomize_questions"]):
        random.shuffle(question_ids)

    question_limit = max(1, min(int(assignment["question_limit"]), len(question_ids)))
    selected_ids = question_ids[:question_limit]

    questions = _fetch_questions_by_ids(
        cur,
        selected_ids,
        include_correct=False,
        randomize_answers=bool(assignment["randomize_answers"]),
    )

    conn.close()

    return {
        "assignment_id": assignment_id,
        "test_title": assignment["title"],
        "mode": assignment["mode"],
        "pass_score": assignment["pass_score"],
        "max_attempts": assignment["max_attempts"],
        "attempts_used": attempts_used,
        "questions": questions,
    }


@router.post("/my/tests/{assignment_id}/submit")
async def submit_assigned_test(assignment_id: int, payload: AssignedTestSubmission):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            a.*,
            t.title,
            t.is_legacy
        FROM admin_assignments a
        JOIN admin_tests t ON t.id = a.test_id
        WHERE a.id = ? AND a.user_id = ?
        """,
        (assignment_id, payload.user_id),
    )
    assignment = cur.fetchone()

    if assignment is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Assigned test not found")

    max_attempts = assignment["max_attempts"]
    attempts_used = assignment["attempts"]
    if max_attempts is not None and attempts_used >= max_attempts:
        conn.close()
        raise HTTPException(status_code=403, detail="Exam attempt limit reached")

    answer_map = _normalize_answer_map(payload.answers)
    question_ids = _dedupe_int_list(payload.question_ids)
    if not question_ids:
        question_ids = list(answer_map.keys())

    if not question_ids:
        conn.close()
        raise HTTPException(status_code=400, detail="No answered questions received")

    if bool(assignment["is_legacy"]):
        placeholders = ",".join(["?"] * len(question_ids))
        cur.execute(f"SELECT COUNT(*) FROM questions WHERE id IN ({placeholders})", question_ids)
        found = cur.fetchone()[0]
        if found != len(question_ids):
            conn.close()
            raise HTTPException(status_code=400, detail="Some submitted questions are invalid")
    else:
        allowed_ids = set(_resolve_test_question_ids(cur, assignment["test_id"], False))
        if not allowed_ids:
            conn.close()
            raise HTTPException(status_code=400, detail="This test has no questions")
        for question_id in question_ids:
            if question_id not in allowed_ids:
                conn.close()
                raise HTTPException(status_code=400, detail="Submitted question does not belong to this test")

    question_limit = int(assignment["question_limit"])
    if len(question_ids) > question_limit:
        question_ids = question_ids[:question_limit]

    correct_count = 0
    checked_rows = []
    wrong_questions = []

    for question_id in question_ids:
        cur.execute(
            """
            SELECT id, question_text, category
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        )
        question_row = cur.fetchone()
        if question_row is None:
            continue

        cur.execute(
            """
            SELECT id, answer_text, is_correct, explanation
            FROM answers
            WHERE question_id = ?
            ORDER BY id
            """,
            (question_id,),
        )
        answer_rows = cur.fetchall()

        selected_answer_id = answer_map.get(question_id)
        selected_answer_text = "Не выбран"
        selected_correct = False
        correct_answer_text = ""
        explanation = ""

        for answer_row in answer_rows:
            if answer_row["id"] == selected_answer_id:
                selected_answer_text = answer_row["answer_text"]
                selected_correct = bool(answer_row["is_correct"])

            if bool(answer_row["is_correct"]):
                correct_answer_text = answer_row["answer_text"]
                explanation = answer_row["explanation"] or ""

        if selected_correct:
            correct_count += 1
        else:
            wrong_questions.append(
                {
                    "question_id": question_id,
                    "question_text": question_row["question_text"],
                    "category": question_row["category"],
                    "selected_answer": selected_answer_text,
                    "correct_answer": correct_answer_text,
                    "explanation": explanation,
                }
            )

        checked_rows.append(
            {
                "question_id": question_id,
                "category": question_row["category"],
                "is_correct": selected_correct,
            }
        )

    if not checked_rows:
        conn.close()
        raise HTTPException(status_code=400, detail="Unable to evaluate submitted answers")

    total = len(checked_rows)
    wrong_count = total - correct_count
    score = int((correct_count / total) * 100) if total > 0 else 0

    pass_score = int(assignment["pass_score"])
    passed = score >= pass_score

    category_stats = _build_category_stats(checked_rows)
    recommendations = _build_recommendations(category_stats, wrong_questions)

    attempt_number = int(assignment["attempts"]) + 1
    now = _now_iso()

    cur.execute(
        """
        INSERT INTO test_attempts (
            assignment_id,
            test_id,
            user_id,
            user_email,
            mode,
            attempt_number,
            total_questions,
            correct_answers,
            wrong_answers,
            score,
            passed,
            pass_score,
            duration_seconds,
            answers_snapshot,
            question_ids_snapshot,
            category_stats,
            wrong_questions,
            recommendations,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assignment_id,
            assignment["test_id"],
            payload.user_id,
            assignment["user_email"],
            assignment["mode"],
            attempt_number,
            total,
            correct_count,
            wrong_count,
            score,
            1 if passed else 0,
            pass_score,
            payload.duration_seconds,
            json.dumps(answer_map, ensure_ascii=False),
            json.dumps(question_ids, ensure_ascii=False),
            json.dumps(category_stats, ensure_ascii=False),
            json.dumps(wrong_questions, ensure_ascii=False),
            json.dumps(recommendations, ensure_ascii=False),
            now,
        ),
    )
    attempt_id = cur.lastrowid

    cur.execute(
        """
        UPDATE admin_assignments
        SET completed_at = ?,
            last_score = ?,
            attempts = ?
        WHERE id = ?
        """,
        (now, score, attempt_number, assignment_id),
    )

    cur.execute(
        """
        INSERT INTO test_results (
            user_id,
            category,
            total_questions,
            correct_answers,
            score,
            test_date,
            assigned_test_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.user_id,
            assignment["title"],
            total,
            correct_count,
            score,
            now,
            assignment["test_id"],
        ),
    )

    conn.commit()
    conn.close()

    attempts_left = None
    if max_attempts is not None:
        attempts_left = max(0, int(max_attempts) - attempt_number)

    return {
        "attempt_id": attempt_id,
        "total": total,
        "correct": correct_count,
        "wrong": wrong_count,
        "score": score,
        "pass_score": pass_score,
        "passed": passed,
        "mode": assignment["mode"],
        "attempt_number": attempt_number,
        "attempts_left": attempts_left,
        "category_stats": category_stats,
        "wrong_questions": wrong_questions,
        "recommendations": recommendations,
    }


@router.get("/my/analytics/{user_id}")
async def my_analytics(user_id: str, limit: int = Query(50, ge=1, le=500)):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ta.*,
            t.title as test_title
        FROM test_attempts ta
        LEFT JOIN admin_tests t ON t.id = ta.test_id
        WHERE ta.user_id = ?
        ORDER BY ta.created_at DESC, ta.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )

    rows = cur.fetchall()
    payload = _aggregate_attempts(rows)
    conn.close()
    return payload


@router.get("/categories")
async def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT category FROM questions ORDER BY category")
    categories = [row["category"] for row in cursor.fetchall()]

    conn.close()
    return {"categories": categories}


@router.get("/questions/{category}")
async def get_questions(category: str, limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, question_text, category, image_url
        FROM questions
        WHERE category = ? OR ? = 'all'
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (category, category, limit),
    )

    questions = cursor.fetchall()
    result = []

    for q in questions:
        cursor.execute(
            """
            SELECT id, answer_text, is_correct, explanation
            FROM answers
            WHERE question_id = ?
            """,
            (q["id"],),
        )

        answers = [
            Answer(
                id=a["id"],
                answer_text=a["answer_text"],
                is_correct=bool(a["is_correct"]),
                explanation=a["explanation"],
            )
            for a in cursor.fetchall()
        ]

        result.append(
            Question(
                id=q["id"],
                question_text=q["question_text"],
                category=q["category"],
                image_url=q["image_url"],
                answers=answers,
            )
        )

    conn.close()
    return {"questions": result}


@router.post("/test/submit")
async def submit_test(submission: TestSubmission):
    conn = get_db_connection()
    cursor = conn.cursor()

    correct_count = 0
    total = len(submission.answers)

    for question_id, answer_id in submission.answers.items():
        cursor.execute(
            """
            SELECT is_correct
            FROM answers
            WHERE id = ? AND question_id = ?
            """,
            (answer_id, question_id),
        )

        result = cursor.fetchone()
        if result and result["is_correct"]:
            correct_count += 1

    score = int((correct_count / total) * 100) if total > 0 else 0

    cursor.execute(
        """
        INSERT INTO test_results (user_id, category, total_questions, correct_answers, score, test_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            submission.user_id,
            submission.category,
            total,
            correct_count,
            score,
            _now_iso(),
        ),
    )

    result_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "result_id": result_id,
        "total": total,
        "correct": correct_count,
        "score": score,
        "passed": score >= 70,
    }


@router.get("/results/{user_id}")
async def get_user_results(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, user_id, category, total_questions, correct_answers, score, test_date
        FROM test_results
        WHERE user_id = ?
        ORDER BY test_date DESC
        """,
        (user_id,),
    )

    results = []
    for row in cursor.fetchall():
        results.append(
            TestResult(
                id=row["id"],
                user_id=row["user_id"],
                category=row["category"],
                total_questions=row["total_questions"],
                correct_answers=row["correct_answers"],
                score=row["score"],
                test_date=row["test_date"],
            )
        )

    conn.close()
    return {"results": results}


@router.get("/stats/{user_id}")
async def get_user_stats(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            category,
            COUNT(*) as tests_count,
            AVG(score) as avg_score,
            MAX(score) as best_score
        FROM test_results
        WHERE user_id = ?
        GROUP BY category
        """,
        (user_id,),
    )

    stats = []
    for row in cursor.fetchall():
        stats.append(
            {
                "category": row["category"],
                "tests_count": row["tests_count"],
                "avg_score": round(row["avg_score"], 1),
                "best_score": row["best_score"],
            }
        )

    conn.close()
    return {"stats": stats}
