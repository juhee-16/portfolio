import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

DB_PATH = "nuri_town.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS play_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            child_age TEXT NOT NULL,
            theme TEXT NOT NULL,
            region TEXT NOT NULL,
            visit_day TEXT NOT NULL,
            budget INTEGER NOT NULL,
            total_cost INTEGER NOT NULL,
            plan_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_plan(
    title: str,
    child_age: str,
    theme: str,
    region: str,
    visit_day: str,
    budget: int,
    total_cost: int,
    plan_data: Dict[str, Any],
) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO play_plans (title, child_age, theme, region, visit_day, budget, total_cost, plan_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, child_age, theme, region, visit_day, budget, total_cost, json.dumps(plan_data, ensure_ascii=False), now),
    )
    plan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return get_plan_by_id(plan_id)


def get_all_plans() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM play_plans ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_plan_by_id(plan_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM play_plans WHERE id = ?", (plan_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def update_plan(
    plan_id: int,
    title: str,
    child_age: str,
    theme: str,
    region: str,
    visit_day: str,
    budget: int,
    total_cost: int,
    plan_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE play_plans
        SET title = ?, child_age = ?, theme = ?, region = ?, visit_day = ?, budget = ?, total_cost = ?, plan_json = ?
        WHERE id = ?
        """,
        (title, child_age, theme, region, visit_day, budget, total_cost, json.dumps(plan_data, ensure_ascii=False), plan_id),
    )
    conn.commit()
    conn.close()
    return get_plan_by_id(plan_id)


def delete_plan(plan_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM play_plans WHERE id = ?", (plan_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "child_age": row["child_age"],
        "theme": row["theme"],
        "region": row["region"],
        "visit_day": row["visit_day"],
        "budget": row["budget"],
        "total_cost": row["total_cost"],
        "plan_data": json.loads(row["plan_json"]),
        "created_at": row["created_at"],
    }

# ==================== 원아(유아) 관리 테이블 & CRUD ====================
def init_student_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age TEXT NOT NULL,
            avatar TEXT NOT NULL,
            memo TEXT DEFAULT '',
            stamps INTEGER DEFAULT 0
        )
    """)
    # 처음 실행 시 샘플 원아 3명 자동 등록 (테스트 편의용)
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        sample_students = [
            ("김하준", "만 4세", "🐶", "공룡과 자동차를 좋아해요"),
            ("이서윤", "만 4세", "🐰", "그림 그리기와 동화책을 좋아해요"),
            ("박도윤", "만 5세", "🐻", "곤충 채집과 블록 놀이를 좋아해요"),
        ]
        cursor.executemany(
            "INSERT INTO students (name, age, avatar, memo) VALUES (?, ?, ?, ?)",
            sample_students
        )
    conn.commit()
    conn.close()

init_student_table()

def get_all_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_student(name: str, age: str, avatar: str, memo: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO students (name, age, avatar, memo) VALUES (?, ?, ?, ?)",
        (name, age, avatar, memo)
    )
    new_id = cursor.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)

def update_student(student_id: int, name: str, age: str, avatar: str, memo: str = ""):
    conn = get_connection()
    conn.execute(
        "UPDATE students SET name = ?, age = ?, avatar = ?, memo = ? WHERE id = ?",
        (name, age, avatar, memo, student_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_student_stamp(student_id: int):
    conn = get_connection()
    conn.execute("UPDATE students SET stamps = stamps + 1 WHERE id = ?", (student_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_student(student_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

def init_community_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artworks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            avatar TEXT NOT NULL,
            theme TEXT NOT NULL,
            image_data TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guestbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            avatar TEXT NOT NULL,
            emoji TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_community_tables()

def save_artwork(student_name: str, avatar: str, theme: str, image_data: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO artworks (student_name, avatar, theme, image_data) VALUES (?, ?, ?, ?)",
        (student_name, avatar, theme, image_data)
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}

def get_all_artworks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM artworks ORDER BY id DESC LIMIT 12").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_guestbook(student_name: str, avatar: str, emoji: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO guestbooks (student_name, avatar, emoji, message) VALUES (?, ?, ?, ?)",
        (student_name, avatar, emoji, message)
    )
    conn.commit()
    conn.close()
    return {"status": "saved"}

def get_all_guestbooks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM guestbooks ORDER BY id DESC LIMIT 15").fetchall()
    conn.close()
    return [dict(r) for r in rows]