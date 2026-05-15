import json
import os
import tempfile

from backend.database import get_db
from db.database.seed_db import load_records, reset_department_data


# --- get_db() ---

def test_get_db_returns_connection():
    """get_db() 應回傳可用的 SQLite 連線"""
    conn = get_db()
    assert conn is not None
    conn.close()


def test_get_db_row_factory():
    """get_db() 回傳的連線應支援欄位名稱存取"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
    row = cursor.fetchone()
    assert row is not None
    assert "name" in row.keys()
    conn.close()


# --- Schema ---

def test_all_tables_exist(temp_db):
    """資料庫應包含五張核心資料表"""
    cursor = temp_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall() if not row["name"].startswith("sqlite_")}
    expected = {"departments", "required_courses", "course_schedules", "special_rules",
                "general_education_requirements", "general_courses"}
    assert expected == tables


# --- load_records() ---

def test_load_records_with_dict():
    """JSON 為單一 dict 時應包裝成 list 回傳"""
    data = {"metadata": {"dept_name": "資訊科學系"}, "required_courses": []}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    try:
        result = load_records(path)
        assert len(result) == 1
        assert result[0]["metadata"]["dept_name"] == "資訊科學系"
    finally:
        os.unlink(path)


def test_load_records_with_list():
    """JSON 為 list 時應回傳所有 dict 項目"""
    data = [
        {"metadata": {"dept_name": "A系"}, "required_courses": []},
        {"metadata": {"dept_name": "B系"}, "required_courses": []},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    try:
        result = load_records(path)
        assert len(result) == 2
    finally:
        os.unlink(path)


def test_load_records_filters_non_dict():
    """list 中非 dict 的項目應被過濾掉"""
    data = [{"metadata": {}}, "not a dict", 123]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    try:
        result = load_records(path)
        assert len(result) == 1
    finally:
        os.unlink(path)


# --- reset_department_data() ---

def test_reset_department_data_clears_courses(temp_db):
    """reset_department_data() 應清除該系的必修課與開課學期資料"""
    cursor = temp_db.cursor()
    cursor.execute(
        "INSERT INTO departments (dept_name, applicable_year) VALUES ('測試系', '114')"
    )
    dept_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO required_courses (department_id, name, credits) VALUES (?, '測試課', 3)",
        (dept_id,),
    )
    course_id = cursor.lastrowid
    cursor.execute("INSERT INTO course_schedules (course_id) VALUES (?)", (course_id,))
    temp_db.commit()

    reset_department_data(cursor, dept_id)
    temp_db.commit()

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM required_courses WHERE department_id = ?", (dept_id,)
    )
    assert cursor.fetchone()["cnt"] == 0
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM course_schedules WHERE course_id = ?", (course_id,)
    )
    assert cursor.fetchone()["cnt"] == 0


def test_reset_department_data_clears_special_rules(temp_db):
    """reset_department_data() 應清除該系的特殊規則"""
    cursor = temp_db.cursor()
    cursor.execute(
        "INSERT INTO departments (dept_name, applicable_year) VALUES ('測試系', '115')"
    )
    dept_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO special_rules (department_id, rule_order, rule_text) VALUES (?, 1, '測試規則')",
        (dept_id,),
    )
    temp_db.commit()

    reset_department_data(cursor, dept_id)
    temp_db.commit()

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM special_rules WHERE department_id = ?", (dept_id,)
    )
    assert cursor.fetchone()["cnt"] == 0
