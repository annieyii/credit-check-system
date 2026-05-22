import json
import sqlite3
from typing import Optional

from backend.database import get_db, normalize_name


# ── 成績判定 ──────────────────────────────────────────────────────────────────

_PASSING_STRINGS = {"通過"}
_FAILING_STRINGS = {"成績未到或無成績", "停修", "不及格", ""}


def _is_passing(score: str) -> bool:
    """score 字串 → 是否及格（數值 >= 60 或「通過」）"""
    s = str(score).strip()
    if s in _PASSING_STRINGS:
        return True
    if s in _FAILING_STRINGS:
        return False
    try:
        return float(s) >= 60
    except ValueError:
        return False


# ── Session 解析 ──────────────────────────────────────────────────────────────

def _collect_all_passed_courses(session_data: list) -> dict[str, float]:
    """全人 JSON → {課名: 學分}，含所有修別且及格的課（抵免課一律視為通過）

    不同於 required.py 只收「必/群」，輔系課程可以任何修別出現在成績單。
    """
    passed: dict[str, float] = {}
    kl = session_data[0]["課業學習"]

    for c in kl.get("waivedCourseList", []):
        name = c.get("courseName", "").strip()
        credit = float(c.get("credit") or 0)
        if name and credit > 0:
            passed[name] = passed.get(name, 0) + credit

    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)

            if name and _is_passing(score) and credit > 0:
                passed[name] = passed.get(name, 0) + credit

    return passed


# ── 資料庫查詢 ────────────────────────────────────────────────────────────────

def _get_minor_row(conn: sqlite3.Connection, dept_name: str, year: str):
    """(輔系名稱, 學年度) → minor_departments row 或 None"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM minor_departments WHERE dept_name = ? AND applicable_year = ?",
        (dept_name, year),
    )
    return cursor.fetchone()


# ── 比對邏輯 ──────────────────────────────────────────────────────────────────

def _match_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict,
) -> tuple[list[str], list[str], float]:
    """
    輔系必修 + 選修 × 已修課程 → (passed_names, missing_names, credits_earned)

    必修：課名直接相符，或 alternatives 中任一課名相符即通過，以 DB 規定學分計入。
    選修：逐群組比對課名，以學生成績單實際學分計入。
          elective_groups 為空時直接略過（各組在自己的分析模組補充比對邏輯）。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    credits_earned: float = 0.0

    # 必修比對
    for course in required_courses:
        name = course["course_name"]
        db_credits = course["credits"]
        alternatives: list[str] = course.get("alternatives", [])

        if name in passed_courses:
            passed_names.append(name)
            credits_earned += db_credits
        else:
            # 任一替代課名吻合即算通過；以必修的規定學分計入
            matched_alt = next((a for a in alternatives if a in passed_courses), None)
            if matched_alt:
                passed_names.append(name)
                credits_earned += db_credits
            else:
                missing_names.append(name)

    # 選修比對（elective_groups）
    seen_elective: set[str] = set()
    for group in elective_groups:
        for course in group["courses"]:
            cname = course["course_name"]
            if cname in passed_courses and cname not in seen_elective:
                seen_elective.add(cname)
                passed_names.append(cname)
                student_credit = passed_courses[cname]
                db_credit = course.get("credits", 0)
                credits_earned += student_credit if student_credit > 0 else db_credit

    return passed_names, missing_names, credits_earned


# ── 公開介面 ──────────────────────────────────────────────────────────────────

def analyze_minor(
    session_data: list,
    dept_name: str,
    year: str,
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """
    全人 JSON × 輔系/學年 → {"passed", "missing", "credits_earned", "credits_needed"}

    找不到輔系時拋 ValueError。
    """
    should_close = conn is None
    if conn is None:
        conn = get_db()

    try:
        passed_courses = _collect_all_passed_courses(session_data)

        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            raise ValueError(f"找不到輔系：{dept_name}（{year}）")

        required_courses: list = json.loads(row["required_courses"])
        elective_groups: list = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        passed, missing, credits_earned = _match_minor(
            required_courses,
            elective_groups,
            passed_courses,
        )

        return {
            "passed": passed,
            "missing": missing,
            "credits_earned": int(credits_earned) if credits_earned == int(credits_earned) else credits_earned,
            "credits_needed": credits_needed,
        }

    finally:
        if should_close:
            conn.close()
