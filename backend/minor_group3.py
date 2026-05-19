import json
import sqlite3
from typing import Optional

from backend.database import get_db


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
        if name:
            passed[name] = credit

    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)
            if name and _is_passing(score):
                passed[name] = credit

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


# ── 共用工具 ──────────────────────────────────────────────────────────────────

def _course_credits(course: dict) -> float:
    """course dict → DB 規定學分

    支援 credits 為數字或 {"min": ..., "max": ..., "display": ...} 的格式。
    """
    credits = course.get("credits", 0)

    if isinstance(credits, dict):
        return float(credits.get("min") or credits.get("max") or 0)

    return float(credits or 0)


def _course_alternatives(course: dict) -> list[str]:
    """course dict → 替代課名清單

    支援 alternatives 與 alternative_courses 兩種欄位名稱。
    """
    return course.get("alternatives") or course.get("alternative_courses") or []


def _flatten_elective_groups(elective_groups) -> list[dict]:
    """elective_groups → group list

    支援 DB 內可能存成 list 或 {"groups": [...]} 的格式。
    """
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
        db_credits = _course_credits(course)

        if _match_course(course, passed_courses):
            passed_names.append(name)
            credits_earned += db_credits
        else:
            missing_names.append(name)

    # 選修比對（elective_groups）
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

    # 必修：所有 required_courses 都必須通過
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 110：只有一般「選修」邏輯，選修至少 12 學分
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

    # 111 起：群修至少 6，總學分滿 30 即可
    else:
        group_courses = groups[0].get("courses", []) if len(groups) >= 1 else []
        elective_courses: list[dict] = []

        for group in groups[1:]:
            elective_courses.extend(group.get("courses", []))

        group_credits = 0.0

        # 群修課程：至少 6 學分，超過的部分也可繼續計入總學分
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

        # 指定選修：補足總學分用
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


# ── 斯語系系輔系專用判斷 ────────────────────────────────────────────────────────

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

    special_regulations：
    - 俄語(二)有擋修規定，但若成績單已有俄語(二)，代表已修過，不額外檢查先修。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 選修至少 9 學分
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

# ── 教育系系輔系專用判斷 ────────────────────────────────────────────────────────

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
    - 其餘 12 學分不限定在此表列課程中；但目前只能依 DB 表列課程與成績單可辨識課程採計

    special_regulations：
    - 教育概論 85 分續修門檻不額外檢查；
      若成績單上已有教育哲學、輔導原理與實務、學習評量，視為已可採計。
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

    # 基礎必修課程：表列基礎科目的一部分，但不是每一科都硬性必修
    for course in basic_required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name and cname not in counted_courses:
            counted_courses.add(cname)
            passed_names.append(cname)

            credit = passed_courses.get(matched_name, 0) or _course_credits(course)
            basic_credits += credit
            credits_earned += credit

    # 基礎群修課程：8 選 5
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
    - 必修 18 學分：政治學、中華民國憲法與政府、比較政府與政治
    - 三個學門中任選兩學門
    - 每個採計學門至少 6 學分
    - 總學分 30 學分

    special_regulations：
    - 抵免後不足 30 學分者由本系指定其他科目補足，無法僅從成績單自動判斷指定補足課。
    - 公行、外交系學生抵免上限 10 學分，需要主系資訊才可判斷，這裡不額外處理。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修 18 學分
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 三學門中任選兩學門，每學門至少 6 學分
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

    # 選出學分最高的兩個已達標學門
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
    - 至少 16 學分需在本系修習：目前成績單若無開課單位，無法自動嚴格判斷
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            passed_names.append(cname)
            counted_courses.add(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 選修：依 DB 的 min_credits_required 判斷
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

    special_regulations：
    - 選課資格、人工選課、名額限制等行政規則不影響成績單通過判斷。
    - prerequisites_internal 皆不額外檢查；若成績單上已有該課且及格，即視為可採計。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修
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
    - 必修 16 學分：
      初級德文閱讀、初級德文語法、初級德文聽力會話、初級德文應用
    - 全校選修 3 學分：
      與歐洲、歐盟、德文、德語系國家相關課程
    - 若選修課僅 2 學分，可用 2 科共 4 學分折抵
    - 總學分 19 學分

    注意：
    - 全學年課程不得跳修屬於選課流程規則；若成績單已有且及格，不額外檢查。
    - 成績單若沒有課程類別或開課單位，無法自動排除通識課。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修 16 學分
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 德文系選修沒有固定課名，需從成績單課名推測是否相關
    german_keywords = [
        "歐洲",
        "歐盟",
        "德文",
        "德語",
        "德國",
    ]

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

    # 一門 3 學分，或兩門 2 學分共 4 學分，皆視為通過
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
    - 必修 15 學分：
      傳播概論、靜態影像設計、基礎影音製作、媒介創新與商業模式、媒體企劃
    - 表一：傳播學院基礎選修，3 選 1，至少 3 學分
    - 表二：廣電系專業選修，至少 6 學分
    - 總學分 24 學分

    special_regulations：
    - 限修媒體企劃與創新學程已由 DB 課表反映。
    - 不適用灌檔、自行選課屬行政規則，不影響成績單通過判斷。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修 15 學分
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

    # 表一：3 選 1，至少 3 學分
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

    # 表二：專業選修至少 6 學分
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
    - 院必修 9 學分：
      傳播概論、傳播與社會、資料分析基礎與策略
    - 廣告系選修 12 學分：
      110 為 6 選 4
      111–114 為 7 選 4
    - 總學分 21 學分

    special_regulations：
    - 灌檔、自行選課屬行政規則，不影響成績單通過判斷。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修 9 學分
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 廣告系選修：至少 12 學分，通常等同 4 門
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
    - 必修：
      國際關係 3 學分
      國際公法 4–6 學分
      國際組織 3 學分
    - 外交史群修：
      西洋外交史、中國外交史至少修習一門，至少 3 學分
    - 一般選修：
      補足總學分至 30 學分
    - 區域研究與國際經貿事務各類別，各至多採計 2 門
    - 外交學系選修最多採計 6 學分

    不處理：
    - 專班、學分費、是否為外交系班級等行政規則
    - 先修規則；若成績單已有且及格，視為可採計
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)

            # 國際公法 113–114 可能為 4–6 學分，優先採成績單實際學分
            student_credit = passed_courses.get(matched_name, 0)
            db_credit = _course_credits(course)
            credits_earned += student_credit if student_credit > 0 else db_credit
        else:
            missing_names.append(cname)

    groups = _flatten_elective_groups(elective_groups)

    # 外交史群修：西洋外交史 / 中國外交史至少一門，至少 3 學分
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

                # 至少一門即可；多修的外交史若要當一般選修，下面不會重複採計
                break

    if history_credits < 3:
        missing_names.append(f"外交史群修不足 {3 - history_credits:g} 學分")

    # 一般選修：補足總學分
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

            # 區域研究最多採計 2 門
            if cname == "區域研究":
                if regional_count >= 2:
                    continue
                regional_count += 1

            # 國際經貿事務最多採計 2 門
            if cname == "國際經貿事務":
                if trade_count >= 2:
                    continue
                trade_count += 1

            # 外交學系選修最多採計 6 學分
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

# ── 地政系土地資源規劃組輔系專用判斷 ────────────────────────────────────────────────────────

def _analyze_land_resource_planning_minor(
    required_courses: list,
    elective_groups: list,
    passed_courses: dict[str, float],
    credits_needed: int,
) -> tuple[list[str], list[str], float]:
    """
    地政學系土地資源規劃組輔系專用判斷。

    規則：
    - 必修 12 學分：
      測量學及實習、土地法(一)、土地政策、民法(一)
    - 群修至少 19 學分
    - 總學分 31 學分

    special_regulations：
    - 群修科目為相對必修，應全學年修習完畢始能採認。
      目前依成績單上是否已有及格課程採計，不額外檢查全學年上下學期流程。
    - prerequisites_internal 不額外檢查；若成績單已有該課且及格，視為可採計。
    """
    passed_names: list[str] = []
    missing_names: list[str] = []
    counted_courses: set[str] = set()
    credits_earned: float = 0.0

    # 必修 12 學分
    for course in required_courses:
        cname = course["course_name"]
        matched_name = _match_course(course, passed_courses)

        if matched_name:
            counted_courses.add(cname)
            passed_names.append(cname)
            credits_earned += _course_credits(course)
        else:
            missing_names.append(cname)

    # 群修至少 19 學分
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

        # 新聞系輔系專用判斷
        if dept_name == "新聞系":
            passed, missing, credits_earned = _analyze_journalism_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
                year,
            )

        elif dept_name == "斯語系":
            passed, missing, credits_earned = _analyze_slavic_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )
        
        elif dept_name == "教育系":
            passed, missing, credits_earned = _analyze_education_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "政治系":
            passed, missing, credits_earned = _analyze_politics_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "應數系":
            passed, missing, credits_earned = _analyze_applied_math_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "心理系":
            passed, missing, credits_earned = _analyze_psychology_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
                year,
            )

        elif dept_name == "德文系":
            passed, missing, credits_earned = _analyze_german_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "廣電系":
            passed, missing, credits_earned = _analyze_broadcasting_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "廣告系":
            passed, missing, credits_earned = _analyze_advertising_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "外交系":
            passed, missing, credits_earned = _analyze_diplomacy_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        elif dept_name == "地政系土地資源規劃組":
            passed, missing, credits_earned = _analyze_land_resource_planning_minor(
                required_courses,
                elective_groups,
                passed_courses,
                credits_needed,
            )

        else:
            passed, missing, credits_earned = _match_minor(
                required_courses,
                elective_groups,
                passed_courses,
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