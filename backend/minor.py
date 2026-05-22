import json
import re
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


def _collect_course_details(session_data: list) -> dict[str, dict]:
    """全人 JSON → {課名: {course_code, credit, type, score?, remark?}}"""
    course_details: dict[str, dict] = {}
    kl = session_data[0]["課業學習"]

    for c in kl.get("waivedCourseList", []):
        name = c.get("courseName", "").strip()
        if name:
            course_details[name] = {
                "course_code": c.get("courseCode", ""),
                "credit": float(c.get("credit") or 0),
                "type": "waived",
            }

    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)
            if name and _is_passing(score) and credit > 0:
                course_details[name] = {
                    "course_code": c.get("courseCode", ""),
                    "credit": credit,
                    "type": "grade",
                    "score": score,
                    "remark": c.get("remark", ""),
                }

    return course_details


# ── 資料庫查詢 ────────────────────────────────────────────────────────────────

def _get_minor_row(conn: sqlite3.Connection, dept_name: str, year: str):
    """(輔系名稱, 學年度) → minor_departments row 或 None"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM minor_departments WHERE dept_name = ? AND applicable_year = ?",
        (dept_name, year),
    )
    return cursor.fetchone()


# ── 共用工具 ──────────────────────────────────────────────────────────────────

def _course_credits(course: dict) -> float:
    """course dict → DB 規定學分；支援 credits 為數字或 {"min":…,"max":…} 格式"""
    credits = course.get("credits", 0)
    if isinstance(credits, dict):
        return float(credits.get("min") or credits.get("max") or 0)
    return float(credits or 0)


def _course_alternatives(course: dict) -> list[str]:
    """course dict → 替代課名清單；支援 alternatives 與 alternative_courses 兩種欄位"""
    return course.get("alternatives") or course.get("alternative_courses") or []


def _flatten_elective_groups(elective_groups) -> list[dict]:
    """elective_groups → group list；支援 list 或 {"groups": […]} 兩種格式"""
    if isinstance(elective_groups, dict):
        return elective_groups.get("groups", [])
    return elective_groups or []


def _match_course(course: dict, passed_courses: dict[str, float]) -> str | None:
    """單一課程 × passed_courses → 實際命中的課名或 None"""
    name = course["course_name"]
    if name in passed_courses:
        return name
    for alt in _course_alternatives(course):
        if alt in passed_courses:
            return alt
    return None


def _format_credits(n: float) -> int | float:
    """學分顯示：整數就回傳 int，否則回傳 float"""
    return int(n) if n == int(n) else n


# ── 基礎比對邏輯 ──────────────────────────────────────────────────────────────

def _match_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict,
) -> tuple[list[str], list[str], float]:
    """
    輔系必修 + 選修 × 已修課程 → (passed_names, missing_names, credits_earned)

    必修：課名直接相符，或 alternatives 中任一課名相符即通過，以 DB 規定學分計入。
    選修：逐群組比對課名，以學生成績單實際學分計入。
          elective_groups 為空時直接略過。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    credits_earned: float = 0.0

    for course in required_courses:
        name = course["course_name"]
        db_credits = _course_credits(course)

        if _match_course(course, passed_courses):
            passed_names.append(name)
            credits_earned += db_credits
        else:
            missing_names.append(name)

    seen_elective: set[str] = set()
    for group in _flatten_elective_groups(elective_groups):
        for course in group.get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in seen_elective:
                seen_elective.add(cname)
                passed_names.append(cname)

                student_credit = passed_courses.get(matched_name, 0)
                db_credit = _course_credits(course)
                credits_earned += student_credit if student_credit > 0 else db_credit

    return passed_names, missing_names, credits_earned


# ── 新聞系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_journalism_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
    year: str,
) -> tuple[list[str], list[str], float]:
    """
    新聞系輔系專用判斷。

    110：
    - 6 門必修共 18 學分
    - 指定選修至少 12 學分
    - 總學分 30

    111 起：
    - 不分系必修 4 門共 12 學分
    - 新聞系群修至少 6 學分
    - 其餘 12 學分可由指定選修或群修溢出補足
    - 總學分 30

    special_regulations 中的灌檔、洽助教、自行選課等行政規則，
    不影響成績單上的修畢判定；新聞媒體實驗(二)的先修限制也不額外驗證。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    groups = _flatten_elective_groups(elective_groups)

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    if year == "110":
        elective_credits = 0.0

        for group in groups:
            for course in group.get("courses", []):
                cname = course["course_name"]
                matched_name = _match_course(course, passed_courses)

                if matched_name and cname not in counted_courses:
                    counted_courses.add(cname)
                    passed_names.append(cname)

                    credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                    elective_credits += credit
                    credits_earned += credit

        if elective_credits < 12:
            missing_names.append(f"選修不足 {12 - elective_credits:g} 學分")

    else:
        group_courses = groups[0].get("courses", []) if len(groups) >= 1 else []
        elective_courses: list[dict] = []

        for group in groups[1:]:
            elective_courses.extend(group.get("courses", []))

        group_credits = 0.0

        for course in group_courses:
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                group_credits += credit
                credits_earned += credit

        if group_credits < 6:
            missing_names.append(f"群修不足 {6 - group_credits:g} 學分")

        for course in elective_courses:
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                credits_earned += credit

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 斯語系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_slavic_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    斯拉夫語文學系輔系專用判斷。

    規則：
    - 必修 15 學分：俄語(一)、俄語(二)、俄國史
    - 選修 9 學分：從系定選修科目中修習
    - 總學分 24 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    elective_credits = 0.0

    for group in _flatten_elective_groups(elective_groups):
        for course in group.get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                elective_credits += credit
                credits_earned += credit

    if elective_credits < 9:
        missing_names.append(f"選修不足 {9 - elective_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 教育系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_education_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    教育學系輔系專用判斷。

    規則：
    - 應修總學分 30 學分
    - 表列基礎科目至少 18 學分
    - 基礎群修課程為 8 選 5
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    groups = _flatten_elective_groups(elective_groups)

    basic_required_courses = groups[0].get("courses", []) if len(groups) >= 1 else []
    basic_group_courses = groups[1].get("courses", []) if len(groups) >= 2 else []

    basic_credits = 0.0
    group_count = 0

    for course in basic_required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name and cname not in counted_courses:
            counted_courses.add(cname)
            passed_names.append(cname)

            credit = passed_courses.get(matched_name, 0) or _course_credits(course)
            basic_credits += credit
            credits_earned += credit

    for course in basic_group_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name and cname not in counted_courses:
            counted_courses.add(cname)
            passed_names.append(cname)

            credit = passed_courses.get(matched_name, 0) or _course_credits(course)
            basic_credits += credit
            credits_earned += credit
            group_count += 1

    if group_count < 5:
        missing_names.append(f"基礎群修課程不足 {5 - group_count} 科")

    if basic_credits < 18:
        missing_names.append(f"表列基礎科目不足 {18 - basic_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 政治系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_politics_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    政治學系輔系專用判斷。

    規則：
    - 必修 18 學分
    - 三個學門中任選兩學門，每學門至少 6 學分
    - 總學分 30 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    group_results: list[tuple[str, float, list[str]]] = []

    for group in _flatten_elective_groups(elective_groups):
        group_name = group.get("group_name", "未命名學門")
        min_required = float(group.get("min_credits_required", 6) or 6)

        group_credits = 0.0
        group_passed: list[str] = []

        for course in group.get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name:
                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                group_credits += credit
                group_passed.append(cname)

        if group_credits >= min_required:
            group_results.append((group_name, group_credits, group_passed))

    selected_groups = sorted(
        group_results,
        key=lambda item: item[1],
        reverse=True,
    )[:2]

    for _, group_credits, group_passed in selected_groups:
        for cname in group_passed:
            if cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

        credits_earned += group_credits

    if len(selected_groups) < 2:
        missing_names.append(f"學門不足 {2 - len(selected_groups)} 個")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 應數系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_applied_math_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    應用數學系輔系專用判斷。

    規則：
    - 110–112：必修 16 學分，選修 12 學分，總 28 學分
    - 113–114：必修 14 學分，選修 14 學分，總 28 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    elective_credits = 0.0
    elective_required = 0.0

    for group in _flatten_elective_groups(elective_groups):
        elective_required += float(group.get("min_credits_required", 0) or 0)

        for course in group.get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                elective_credits += credit
                credits_earned += credit

    if elective_credits < elective_required:
        missing_names.append(f"選修不足 {elective_required - elective_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 心理系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_psychology_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
    year: str,
) -> tuple[list[str], list[str], float]:
    """
    心理學系輔系專用判斷。

    規則：
    - 110：必修普通心理學 6 學分，群修至少 3 門且至少 9 學分，總 30 學分
    - 111 起：必修 4 門共 19 學分，群修至少 4 門且至少 12 學分，總 31 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    groups = _flatten_elective_groups(elective_groups)
    group_courses = groups[0].get("courses", []) if groups else []

    group_credits = 0.0
    group_count = 0

    for course in group_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name and cname not in counted_courses:
            counted_courses.add(cname)
            passed_names.append(cname)

            credit = passed_courses.get(matched_name, 0) or _course_credits(course)
            group_credits += credit
            credits_earned += credit
            group_count += 1

    min_group_count = 3 if year == "110" else 4
    min_group_credits = 9 if year == "110" else 12

    if group_count < min_group_count:
        missing_names.append(f"群修不足 {min_group_count - group_count} 門")

    if group_credits < min_group_credits:
        missing_names.append(f"群修不足 {min_group_credits - group_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 德文系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_german_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    歐洲語文學系德文組輔系專用判斷。

    規則：
    - 必修 16 學分
    - 全校選修 3 學分：與歐洲、歐盟、德文、德語系國家相關課程
    - 若選修課僅 2 學分，可用 2 科共 4 學分折抵
    - 總學分 19 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    german_keywords = ["歐洲", "歐盟", "德文", "德語", "德國"]

    elective_candidates: list[tuple[str, float]] = []

    for cname, credit in passed_courses.items():
        if cname in counted_courses:
            continue
        if any(keyword in cname for keyword in german_keywords):
            elective_candidates.append((cname, float(credit or 0)))

    elective_candidates.sort(key=lambda item: item[1], reverse=True)

    elective_credits = 0.0
    elective_count = 0

    for cname, credit in elective_candidates:
        if elective_credits >= 3:
            break
        counted_courses.add(cname)
        passed_names.append(cname)
        elective_credits += credit
        elective_count += 1

    elective_passed = elective_credits >= 3 or (elective_count >= 2 and elective_credits >= 4)

    if not elective_passed:
        missing_names.append("歐洲／歐盟／德文／德語系國家相關選修不足")

    credits_earned += elective_credits

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 廣電系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_broadcasting_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    廣播電視學系（媒體企劃與創新學程）輔系專用判斷。

    規則：
    - 必修 15 學分
    - 表一：傳播學院基礎選修，3 選 1，至少 3 學分
    - 表二：廣電系專業選修，至少 6 學分
    - 總學分 24 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    groups = _flatten_elective_groups(elective_groups)

    table1_credits = 0.0
    if len(groups) >= 1:
        for course in groups[0].get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                table1_credits += credit
                credits_earned += credit
                break

    if table1_credits < 3:
        missing_names.append(f"表一基礎選修不足 {3 - table1_credits:g} 學分")

    table2_credits = 0.0
    if len(groups) >= 2:
        for course in groups[1].get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                table2_credits += credit
                credits_earned += credit

    if table2_credits < 6:
        missing_names.append(f"表二專業選修不足 {6 - table2_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 廣告系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_advertising_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    廣告學系輔系專用判斷。

    規則：
    - 院必修 9 學分
    - 廣告系選修 12 學分（110 為 6 選 4；111–114 為 7 選 4）
    - 總學分 21 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    elective_credits = 0.0
    elective_count = 0

    for group in _flatten_elective_groups(elective_groups):
        for course in group.get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                elective_credits += credit
                credits_earned += credit
                elective_count += 1

    if elective_count < 4:
        missing_names.append(f"廣告系選修不足 {4 - elective_count} 門")

    if elective_credits < 12:
        missing_names.append(f"廣告系選修不足 {12 - elective_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 外交系輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_diplomacy_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    外交學系輔系專用判斷。

    規則：
    - 必修：國際關係 3 學分、國際公法 4–6 學分、國際組織 3 學分
    - 外交史群修：西洋外交史 / 中國外交史至少一門，至少 3 學分
    - 一般選修：補足總學分至 30 學分
    - 區域研究與國際經貿事務各類別，各至多採計 2 門
    - 外交學系選修最多採計 6 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)

            student_credit = passed_courses.get(matched_name, 0)
            db_credit = _course_credits(course)
            credits_earned += student_credit if student_credit > 0 else db_credit
        else:
            missing_names.append(cname)

    groups = _flatten_elective_groups(elective_groups)

    history_credits = 0.0

    if len(groups) >= 1:
        for course in groups[0].get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                history_credits += credit
                credits_earned += credit
                break

    if history_credits < 3:
        missing_names.append(f"外交史群修不足 {3 - history_credits:g} 學分")

    regional_count = 0
    trade_count = 0
    department_elective_credits = 0.0

    if len(groups) >= 2:
        for course in groups[1].get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if not matched_name or cname in counted_courses:
                continue

            credit = passed_courses.get(matched_name, 0) or _course_credits(course)

            if cname == "區域研究":
                if regional_count >= 2:
                    continue
                regional_count += 1

            if cname == "國際經貿事務":
                if trade_count >= 2:
                    continue
                trade_count += 1

            if cname == "外交學系選修":
                remaining = 6 - department_elective_credits
                if remaining <= 0:
                    continue
                credit = min(credit, remaining)
                department_elective_credits += credit

            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += credit

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 地政系土地資源規劃組輔系專用判斷 ──────────────────────────────────────────

def _analyze_land_resource_planning_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    地政學系土地資源規劃組輔系專用判斷。

    規則：
    - 必修 12 學分
    - 群修至少 19 學分
    - 總學分 31 學分
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    group_credits = 0.0

    for group in _flatten_elective_groups(elective_groups):
        for course in group.get("courses", []):
            cname = course["course_name"]
            matched_name = _match_course(course, passed_courses)

            if matched_name and cname not in counted_courses:
                counted_courses.add(cname)
                passed_names.append(cname)

                credit = passed_courses.get(matched_name, 0) or _course_credits(course)
                group_credits += credit
                credits_earned += credit

    if group_credits < 19:
        missing_names.append(f"群修不足 {19 - group_credits:g} 學分")

    if credits_earned < credits_needed:
        missing_names.append(f"總學分不足 {credits_needed - credits_earned:g} 學分")

    return passed_names, missing_names, credits_earned


# ── 金融系 113–114 年度群修特殊邏輯 ──────────────────────────────────────────

def _handle_finance_group_electives_113_114(
    session_data: list,
    elective_groups: list,
    passed_courses: dict,
    passed_names: list,
    credits_earned: float,
    detailed_report: dict,
) -> tuple:
    """
    金融系 113–114 年度群修判斷。

    規則：六個領域各至少一門課，總計 14 學分，科目代碼需吻合。
    """
    missing_names: list[str] = []
    total_credits_needed = 14.0
    total_credits_earned = 0.0

    course_details = _collect_course_details(session_data)

    area_results = []
    for group in elective_groups:
        group_name = group.get("group_name", "")
        courses = group.get("courses", [])

        area_result = {
            "group_name": group_name,
            "min_credits": 0,
            "passed_courses": [],
            "missing_courses": [],
            "credits_earned": 0.0,
            "has_course": False,
        }

        for course in courses:
            course_name = course.get("course_name", "").strip()
            db_course_code = course.get("course_code", "")

            if course_name in passed_courses:
                student_course_info = course_details.get(course_name, {})
                student_course_code = student_course_info.get("course_code", "")

                if db_course_code and student_course_code:
                    db_codes = [code.strip() for code in db_course_code.split(",")]
                    student_codes = [code.strip() for code in student_course_code.split(",")]
                    code_match = any(db_code in student_codes for db_code in db_codes)
                else:
                    code_match = True

                if code_match and course_name not in [c["name"] for c in area_result["passed_courses"]]:
                    student_credit = passed_courses[course_name]
                    area_result["passed_courses"].append({
                        "name": course_name,
                        "credits": student_credit,
                        "course_code": student_course_code,
                    })
                    area_result["credits_earned"] += student_credit
                    area_result["has_course"] = True

                    if course_name not in passed_names:
                        passed_names.append(course_name)
                        total_credits_earned += student_credit

        if not area_result["has_course"]:
            area_result["missing_courses"].append(group_name)

        area_results.append(area_result)

    areas_with_course = sum(1 for area in area_results if area["has_course"])
    areas_needed = len(area_results)

    detailed_report["group_electives"]["credits_needed"] = total_credits_needed
    detailed_report["group_electives"]["credits_earned"] = total_credits_earned
    detailed_report["group_electives"]["group_details"] = area_results

    for area in area_results:
        for course in area["passed_courses"]:
            detailed_report["group_electives"]["passed"].append({
                "name": course["name"],
                "credits": course["credits"],
                "group": area["group_name"],
                "course_code": course["course_code"],
            })

    if not (total_credits_earned >= total_credits_needed and areas_with_course >= areas_needed):
        for area in area_results:
            if not area["has_course"]:
                detailed_report["group_electives"]["missing"].append({
                    "group": area["group_name"],
                    "reason": "該領域未修課",
                })

    return passed_names, missing_names, total_credits_earned, detailed_report


# ── Group 1 系所專用比對邏輯 ──────────────────────────────────────────────────

_GROUP1_DEPTS = {
    "風保系", "風險管理與保險學系",
    "韓文系", "韓國語文學系",
    "阿語系", "阿拉伯語文學系",
    "金融系",
    "越文系", "越南語文學系",
    "資訊系",
    "資管系",
    "財管系",
    "財政系財政管理組",
    "財政系稅務組",
    "財政系公共經濟組",
    "西文系", "西班牙語文學系",
}


def _match_minor_group1(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict,
    dept_name: str,
    year: str,
    session_data: list,
) -> tuple[list[str], list[str], float, dict]:
    """
    Group 1 系所專用比對邏輯（風保、韓文、阿語、金融、越文、資訊、資管、財管、財政系三組、西文）
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    credits_earned: float = 0.0

    detailed_report = {
        "required": {
            "passed": [], "missing": [],
            "credits_earned": 0.0, "credits_needed": 0.0,
        },
        "group_electives": {
            "passed": [], "missing": [],
            "credits_earned": 0.0, "credits_needed": 0.0,
            "group_details": [],
        },
    }

    # ── 必修比對 ──
    required_credits_needed = 0.0
    for course in required_courses:
        name = course["course_name"]
        db_credits = _course_credits(course)
        alternatives: list[str] = _course_alternatives(course)
        required_credits_needed += db_credits

        course_credits_earned = 0.0
        course_fully_completed = False

        if name in passed_courses:
            course_credits_earned = passed_courses[name]
            if course_credits_earned >= db_credits:
                passed_names.append(name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": name, "credits": db_credits,
                    "earned_credits": course_credits_earned,
                })
                detailed_report["required"]["credits_earned"] += db_credits
                course_fully_completed = True
            else:
                detailed_report["required"]["missing"].append({
                    "name": name, "credits": db_credits,
                    "earned_credits": course_credits_earned,
                    "deficit": db_credits - course_credits_earned, "partial": True,
                })
        else:
            matched_alt = None
            course_credits_earned = 0.0

            # 財政系特殊抵免：稅務會計學 → 稅務會計
            if "財政" in dept_name and name == "稅務會計":
                if "稅務會計學" in passed_courses:
                    matched_alt = "稅務會計學"
                    course_credits_earned = passed_courses["稅務會計學"]

            # 越文系特殊抵免：大學外文抵免（僅限 110–111 年度）
            elif "越文" in dept_name and year in ["110", "111"]:
                if name == "初級越語":
                    viet_courses = ["大學外文(一):越南文", "大學外文(二):越南文"]
                    used = [c for c in viet_courses if c in passed_courses]
                    viet_credits = sum(passed_courses[c] for c in used)
                    if viet_credits > 0:
                        matched_alt = " + ".join(used)
                        course_credits_earned = viet_credits
                elif name == "中級越語":
                    viet_courses = ["大學外文(三):越南文", "大學外文(四):越南文"]
                    used = [c for c in viet_courses if c in passed_courses]
                    viet_credits = sum(passed_courses[c] for c in used)
                    if viet_credits > 0:
                        matched_alt = " + ".join(used)
                        course_credits_earned = viet_credits

            # 金融系特殊抵免：計量經濟學 → 金融計量（僅限 110–112 年度）
            elif "金融" in dept_name and year in ["110", "111", "112"] and name == "金融計量":
                if "計量經濟學" in passed_courses:
                    matched_alt = "計量經濟學"
                    course_credits_earned = passed_courses["計量經濟學"]

            # 一般替代課程
            if not matched_alt:
                for alt in alternatives:
                    if alt in passed_courses:
                        matched_alt = alt
                        course_credits_earned = passed_courses[alt]
                        break

            if matched_alt and course_credits_earned >= db_credits:
                passed_names.append(name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": name, "credits": db_credits,
                    "earned_credits": course_credits_earned,
                    "via_alternative": matched_alt,
                })
                detailed_report["required"]["credits_earned"] += db_credits
                course_fully_completed = True
            elif matched_alt:
                detailed_report["required"]["missing"].append({
                    "name": name, "credits": db_credits,
                    "earned_credits": course_credits_earned,
                    "deficit": db_credits - course_credits_earned,
                    "partial": True, "via_alternative": matched_alt,
                })
            else:
                detailed_report["required"]["missing"].append({
                    "name": name, "credits": db_credits,
                    "earned_credits": 0.0,
                    "deficit": db_credits, "partial": False,
                })

        if not course_fully_completed:
            missing_names.append(name)

    detailed_report["required"]["credits_needed"] = required_credits_needed

    # ── 群修比對 ──
    # 金融系 113–114 特殊處理
    if "金融" in dept_name and year in ["113", "114"]:
        return _handle_finance_group_electives_113_114(
            session_data, elective_groups, passed_courses,
            passed_names, credits_earned, detailed_report,
        )

    group_credits_needed = 0.0

    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        courses = group.get("courses", [])
        group_credits_needed += min_credits

        group_detail = {
            "group_name": group_name, "min_credits": min_credits,
            "passed_courses": [], "missing_courses": [], "credits_earned": 0.0,
        }

        group_earned = 0.0
        used_courses_in_group: set[str] = set()

        for course in courses:
            course_name = course.get("course_name", "").strip()

            matched_course = None
            student_credit = 0.0

            if course_name in passed_courses and course_name not in used_courses_in_group:
                matched_course = course_name
                student_credit = passed_courses[course_name]
            elif "財政" in dept_name and course_name == "稅務會計":
                if "稅務會計學" in passed_courses and "稅務會計學" not in used_courses_in_group:
                    matched_course = "稅務會計學"
                    student_credit = passed_courses["稅務會計學"]
            elif "金融" in dept_name and year in ["110", "111", "112"] and course_name == "金融計量":
                if "計量經濟學" in passed_courses and "計量經濟學" not in used_courses_in_group:
                    matched_course = "計量經濟學"
                    student_credit = passed_courses["計量經濟學"]

            if matched_course:
                passed_names.append(matched_course)
                credits_earned += student_credit
                group_earned += student_credit
                used_courses_in_group.add(matched_course)

                group_detail["passed_courses"].append({
                    "name": course_name, "credits": student_credit,
                    "via_alternative": matched_course if matched_course != course_name else None,
                })
                detailed_report["group_electives"]["passed"].append({
                    "name": course_name, "credits": student_credit, "group": group_name,
                    "via_alternative": matched_course if matched_course != course_name else None,
                })
            else:
                group_detail["missing_courses"].append({
                    "name": course_name, "credits": course.get("credits", 0),
                })

        # 韓文系：學分不足時尋找 507 開頭課程
        if "韓文" in dept_name and group_earned < min_credits and session_data:
            additional_credits = min_credits - group_earned
            course_details = _collect_course_details(session_data)
            course_list_names = {c.get("course_name", "").strip() for c in courses}

            for cname, details in course_details.items():
                if (cname in passed_courses
                        and cname not in used_courses_in_group
                        and cname not in course_list_names
                        and details.get("course_code", "").startswith("507")):
                    student_credit = passed_courses[cname]
                    if additional_credits > 0:
                        group_earned += student_credit
                        passed_names.append(cname)
                        credits_earned += student_credit
                        used_courses_in_group.add(cname)
                        additional_credits -= student_credit
                        group_detail["passed_courses"].append({
                            "name": cname, "credits": student_credit, "via_course_code": True,
                        })
                        detailed_report["group_electives"]["passed"].append({
                            "name": cname, "credits": student_credit,
                            "group": group_name, "via_course_code": True,
                        })
                        if additional_credits <= 0:
                            break

        # 越文系：學分不足時尋找 510 開頭且含「越」字的課程
        if "越文" in dept_name and group_earned < min_credits and session_data:
            additional_credits = min_credits - group_earned
            course_details = _collect_course_details(session_data)
            course_list_names = {c.get("course_name", "").strip() for c in courses}

            for cname, details in course_details.items():
                if (cname in passed_courses
                        and cname not in used_courses_in_group
                        and cname not in course_list_names
                        and details.get("course_code", "").startswith("510")
                        and "越" in cname):
                    student_credit = passed_courses[cname]
                    if additional_credits > 0:
                        group_earned += student_credit
                        passed_names.append(cname)
                        credits_earned += student_credit
                        used_courses_in_group.add(cname)
                        additional_credits -= student_credit
                        group_detail["passed_courses"].append({
                            "name": cname, "credits": student_credit, "via_course_code": True,
                        })
                        detailed_report["group_electives"]["passed"].append({
                            "name": cname, "credits": student_credit,
                            "group": group_name, "via_course_code": True,
                        })
                        if additional_credits <= 0:
                            break

        # 西文系：學分不足時尋找關鍵字相符課程（支援 2 學分折抵）
        if "西文" in dept_name and group_earned < min_credits and session_data:
            additional_credits = min_credits - group_earned
            course_details = _collect_course_details(session_data)
            course_list_names = {c.get("course_name", "").strip() for c in courses}

            spanish_keywords = [
                "歐洲", "歐盟", "西班牙", "西班牙文", "西語",
                "拉美", "拉丁美洲", "墨西哥", "阿根廷", "智利",
                "秘魯", "哥倫比亞", "委內瑞拉", "古巴",
            ]

            eligible: list[dict] = []
            for cname in passed_courses:
                if (cname not in used_courses_in_group
                        and cname not in course_list_names
                        and any(kw in cname for kw in spanish_keywords)):
                    info = course_details.get(cname, {})
                    if "通" not in info.get("remark", ""):
                        eligible.append({"name": cname, "credits": passed_courses[cname]})

            two_cr = [c for c in eligible if c["credits"] == 2.0]
            others = [c for c in eligible if c["credits"] != 2.0]

            for c in others:
                if additional_credits <= 0:
                    break
                group_earned += c["credits"]
                passed_names.append(c["name"])
                credits_earned += c["credits"]
                used_courses_in_group.add(c["name"])
                additional_credits -= c["credits"]
                group_detail["passed_courses"].append({"name": c["name"], "credits": c["credits"], "via_keyword": True})
                detailed_report["group_electives"]["passed"].append({"name": c["name"], "credits": c["credits"], "group": group_name, "via_keyword": True})

            i = 0
            while additional_credits > 0 and i + 1 < len(two_cr):
                c1, c2 = two_cr[i], two_cr[i + 1]
                group_earned += 3.0
                passed_names.extend([c1["name"], c2["name"]])
                credits_earned += 3.0
                used_courses_in_group.update([c1["name"], c2["name"]])
                additional_credits -= 3.0
                group_detail["passed_courses"].extend([
                    {"name": c1["name"], "credits": 2.0, "via_keyword": True, "combined_with": c2["name"]},
                    {"name": c2["name"], "credits": 2.0, "via_keyword": True, "combined_with": c1["name"]},
                ])
                detailed_report["group_electives"]["passed"].append({
                    "name": f"{c1['name']} + {c2['name']}", "credits": 3.0,
                    "group": group_name, "via_keyword": True, "combined": True,
                })
                i += 2

        group_detail["credits_earned"] = group_earned
        detailed_report["group_electives"]["group_details"].append(group_detail)
        detailed_report["group_electives"]["credits_earned"] += group_earned

    detailed_report["group_electives"]["credits_needed"] = group_credits_needed

    return passed_names, missing_names, credits_earned, detailed_report


# ── 輔系偵測（供測試使用） ────────────────────────────────────────────────────

def _detect_minor_info(session_data: list) -> Optional[tuple]:
    """session_data → (輔系名稱, 入學年度) 或 None"""
    about = session_data[0]["課業學習"].get("aboutMe", {})

    register_minor = about.get("registerMinor", "").strip()
    if register_minor:
        minor1 = about.get("minor1", "")
        student_number = about.get("studentNumber", "")

        if minor1 and "（" in minor1:
            match = re.search(r"（(\d+)）", minor1)
            if match:
                return register_minor, match.group(1)

        if student_number and len(student_number) >= 3:
            return register_minor, student_number[:3]

    return None


def _parse_minor_courses(session_data: list, target_minor: str) -> dict[str, float]:
    """輔系相關課程關鍵字篩選 → {課名: 學分}（供測試使用）"""
    minor_keywords: dict[str, list[str]] = {
        "日本語文學系": ["日語", "日本", "日文"],
        "韓國語文學系": ["韓語", "韓國", "韓文"],
        "阿拉伯語文學系": ["阿語", "阿拉伯"],
        "越南語文學系": ["越語", "越南"],
        "西班牙語文學系": ["西語", "西班牙"],
        "金融系": ["金融", "投資", "保險", "銀行", "期貨"],
        "資訊系": ["計算機", "程式", "資料", "演算法", "物件導向"],
        "資管系": ["資訊", "管理", "系統"],
        "財管系": ["財務", "管理", "會計", "稅務"],
        "風險管理與保險學系": ["風險", "保險", "風保"],
    }

    keywords = minor_keywords.get(target_minor, [])
    passed: dict[str, float] = {}
    kl = session_data[0]["課業學習"]

    for c in kl.get("waivedCourseList", []):
        name = c.get("courseName", "").strip()
        credit = float(c.get("credit") or 0)
        if name and credit > 0 and any(kw in name for kw in keywords):
            passed[name] = credit

    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)
            if name and _is_passing(score) and credit > 0 and any(kw in name for kw in keywords):
                passed[name] = credit

    return passed


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

        # Group 1 系所
        if dept_name in _GROUP1_DEPTS:
            passed, missing, credits_earned, detailed_report = _match_minor_group1(
                required_courses, elective_groups, passed_courses,
                dept_name, year, session_data,
            )
            return {
                "passed": passed,
                "missing": missing,
                "credits_earned": _format_credits(credits_earned),
                "credits_needed": credits_needed,
                "detailed_report": detailed_report,
            }

        # 新聞系
        if dept_name == "新聞系":
            passed, missing, credits_earned = _analyze_journalism_minor(
                required_courses, elective_groups, passed_courses, credits_needed, year,
            )
        elif dept_name == "斯語系":
            passed, missing, credits_earned = _analyze_slavic_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "教育系":
            passed, missing, credits_earned = _analyze_education_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "政治系":
            passed, missing, credits_earned = _analyze_politics_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "應數系":
            passed, missing, credits_earned = _analyze_applied_math_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "心理系":
            passed, missing, credits_earned = _analyze_psychology_minor(
                required_courses, elective_groups, passed_courses, credits_needed, year,
            )
        elif dept_name == "德文系":
            passed, missing, credits_earned = _analyze_german_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "廣電系":
            passed, missing, credits_earned = _analyze_broadcasting_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "廣告系":
            passed, missing, credits_earned = _analyze_advertising_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "外交系":
            passed, missing, credits_earned = _analyze_diplomacy_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        elif dept_name == "地政系土地資源規劃組":
            passed, missing, credits_earned = _analyze_land_resource_planning_minor(
                required_courses, elective_groups, passed_courses, credits_needed,
            )
        else:
            # Group 2、Group 4 及其他系所使用基礎比對邏輯
            passed, missing, credits_earned = _match_minor(
                required_courses, elective_groups, passed_courses,
            )

        return {
            "passed": passed,
            "missing": missing,
            "credits_earned": _format_credits(credits_earned),
            "credits_needed": credits_needed,
        }

    finally:
        if should_close:
            conn.close()
