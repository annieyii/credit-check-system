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

def _collect_passed_courses(session_data: list) -> dict:
    """全人 JSON → {課名: 學分}，只含修別為「必」或「群」且及格的課（抵免課一律視為通過）"""
    passed: dict[str, float] = {}
    kl = session_data[0]["課業學習"]

    for c in kl.get("waivedCourseList", []):
        name = c.get("courseName", "").strip()
        credit = float(c.get("credit") or 0)
        if name:
            passed[name] = credit
            passed[normalize_name(name)] = credit

    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            if c.get("requiredOrElectiveCourse") not in ("必", "群"):
                continue
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)
            if name and _is_passing(score):
                passed[name] = credit
                passed[normalize_name(name)] = credit

    return passed


def _count_group_course_semesters(session_data: list) -> dict[str, int]:
    """全人 JSON → {群修課名: 及格學期數}（同名課出現多次時分別計算，用於群A多學期判定）"""
    counts: dict[str, int] = {}
    kl = session_data[0]["課業學習"]
    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            if c.get("requiredOrElectiveCourse") != "群":
                continue
            name = c.get("courseName", "").strip()
            if name and _is_passing(c.get("score", "")):
                counts[name] = counts.get(name, 0) + 1
    return counts


# ── 雙主修解析 ────────────────────────────────────────────────────────────────

def _parse_double_major(about: dict, fallback_year: str) -> Optional[tuple]:
    """aboutMe dict → (系所名稱, 學年度) 或 None；系所名取 registerDoubleMajor，學年從括號解析"""
    dept_name = about.get("registerDoubleMajor", "").strip()
    if not dept_name:
        return None
    raw = about.get("doubleMajor", "")
    m = re.search(r'（(\d+)）', raw)
    year = m.group(1) if m else fallback_year
    return dept_name, year


# ── 資料庫查詢 ────────────────────────────────────────────────────────────────

def _get_dept_row(conn: sqlite3.Connection, dept_name: str, year: str):
    """(系所名稱, 學年度) → departments row 或 None"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, compulsory_credits_required FROM departments "
        "WHERE dept_name = ? AND applicable_year = ?",
        (dept_name, year),
    )
    return cursor.fetchone()


def _get_required_courses(conn: sqlite3.Connection, dept_id: int) -> list:
    """dept_id → [{'name', 'type', 'credits'}, ...]，排除選修與通識"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, type, credits
        FROM required_courses
        WHERE department_id = ?
          AND type NOT IN ('選修', '通識')
        ORDER BY type, name
        """,
        (dept_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


# ── 群修課程對照表 ─────────────────────────────────────────────────────────────
# DB 的群修欄位存佔位符課名，無法直接與學生成績比對。
# 格式：{ (系所全名, 學年度): { 群組類型: {實際課名, ...} } }

_CS_GROUP_112_113_114 = {
    "群B": {"人工智慧概論", "資料庫系統", "資料科學", "機器學習概論", "電腦視覺"},
    "群C": {"人機互動", "電腦圖學", "軟體開發環境應用設計", "虛擬實境與觸覺回饋互動", "視訊壓縮", "資訊視覺化"},
    "群D": {"資訊安全", "資訊理論", "現代密碼學", "數位簽章", "工業物聯網與營運安全"},
    "群E": {"計算機網路", "行動通訊網路", "網路與通訊概論", "分散式系統", "軟體工程概論", "等候理論"},
}

_HISTORY_GROUP_ALL = {
    # 群B = 專史類（24 學分）；舊生修「歷史閱讀與書寫」可認抵專史（第六點第1條）
    "群B": {"中國歷史經典研讀", "口述歷史", "史學方法論", "中國傳統史學", "中國近代史學", "歷史書寫", "應用史學", "史學經典與史料",
            "中華人民共和國史", "中華民國憲政史", "中國政治制度史", "中國近代政治史", "臺灣現代史", "臺灣民主運動史",
            "近代東亞農業史", "台灣近代經濟史", "中國古代生活史", "宋元社會史", "中國近代社會生活史", "中國社會史",
            "唐宋元繪畫史", "元明清繪畫史", "中國古代醫療史", "希臘化文化", "中世紀基督宗教史", "台灣近代社會文化史",
            "性別與近代西方世界的形成", "東亞佛教文化史", "近代中國婦女史", "西洋藝術史", "歐洲的激進傳統（1750至今）",
            "南亞史", "日本史", "臺灣國際關係史", "美國史", "日本近現代史", "海洋東南亞史", "德國史、中古地中海歷史(400-1000)",
            "歷史閱讀與書寫"},
    # 群A = 專題類（9 學分）；舊生修「史學多元實踐」可認抵專題（第六點第1條）
    "群A": {"西洋史學史專題", "西洋史學名著選讀專題", "手稿史料專題", "歷史與記憶專題", "史蹟與文化資產專題", "德國史學與歷史知識專題",
            "中國政治制度史專題", "士人、鄉里與國家專題", "社會與國家專題", "古代中國的士人、唐代士人專題",
            "宋元社會史專題", "明清日常生活史專題", "清代通商制度專題", "清代海洋貿易史專題", "近現代歷史中的人群移動專題",
            "全球宗教改革專題", "博物館發展史專題", "藝術史方法論專題", "美術與近代中國專題",
            "中日關係史專題", "英國史專題", "帝國主義：個案討論專題", "希臘化文化專題", "東印度公司與近代亞洲專題",
            "史學多元實踐"},
}

_GROUP_COURSE_MAP: dict[tuple[str, str], dict[str, set[str]]] = {
    ("資訊科學系", "112"): _CS_GROUP_112_113_114,
    ("資訊科學系", "113"): _CS_GROUP_112_113_114,
    ("資訊科學系", "114"): _CS_GROUP_112_113_114,
    ("歷史學系", "110"): _HISTORY_GROUP_ALL,
    ("歷史學系", "111"): _HISTORY_GROUP_ALL,
    ("歷史學系", "112"): _HISTORY_GROUP_ALL,
    ("歷史學系", "113"): _HISTORY_GROUP_ALL,
    ("歷史學系", "114"): _HISTORY_GROUP_ALL,
}


# ── 必修替代對照表 ─────────────────────────────────────────────────────────────
# 格式：{ (系所全名, 學年度): { 必修課名: {可替代的課名, ...} } }
# 同一門替代課最多只能抵一門必修（_match_required 中 used_substitutes 追蹤）

# 本系所有專史/專題課名聯集，供第五點第4條「本系専史/専題任 1 科替代」使用
_HISTORY_ALL_SPEC_COURSES = _HISTORY_GROUP_ALL["群B"] | _HISTORY_GROUP_ALL["群A"]

# 113/114 新制：舊課抵新必修（過渡辦法第五點）
# 第5點第4條：史學導論只能抵歷思/歷閱其中一門；剩餘一門可用本系任 1 科專史/專題替代
_HISTORY_COMPULSORY_SUBSTITUTE_NEW = {
    "台灣、東亞與世界文明（一）": {"台灣史"},
    "台灣、東亞與世界文明（二）": {"中國通史（上）", "中國通史（下）"},
    "台灣、東亞與世界文明（三）": {"世界通史（上）", "世界通史（下）"},
    "歷史思惟與方法": {"史學導論"} | _HISTORY_ALL_SPEC_COURSES,
    "歷史閱讀與書寫": {"史學導論"} | _HISTORY_ALL_SPEC_COURSES,
}

# 110/111/112 舊制：新課抵舊必修（過渡辦法第四點）
# 台灣東亞（二/三）一門只能替代中通/世通各一門
# TODO 第四點（本系112學年以前入學生／雙主修生欄）：
# 台灣史：或任修本系台灣史相關領域之專史、專題 1 科 3 學分替代。
# 中通類：尚不足 3 學分任修本系亞洲史相關領域（排除台灣史）專史/專題 1 科 3 學分替代。
# 世通類：尚不足 3 學分任修本系世界史相關領域（排除亞洲或台灣史）專史/專題 1 科 3 學分替代。
# → 需歷史系提供各領域符合條件的課程清單，補充至下方各必修課的替代集合。
_HISTORY_COMPULSORY_SUBSTITUTE_OLD = {
    "台灣史":         {"台灣、東亞與世界文明（一）"},
    "史學導論":       {"歷史思惟與方法", "歷史閱讀與書寫"},
    "中國通史（上）": {"台灣、東亞與世界文明（二）"},
    "中國通史（下）": {"台灣、東亞與世界文明（二）"},
    "世界通史（上）": {"台灣、東亞與世界文明（三）"},
    "世界通史（下）": {"台灣、東亞與世界文明（三）"},
}

_COMPULSORY_SUBSTITUTE_MAP: dict[tuple[str, str], dict[str, set[str]]] = {
    ("歷史學系", "110"): _HISTORY_COMPULSORY_SUBSTITUTE_OLD,
    ("歷史學系", "111"): _HISTORY_COMPULSORY_SUBSTITUTE_OLD,
    ("歷史學系", "112"): _HISTORY_COMPULSORY_SUBSTITUTE_OLD,
    ("歷史學系", "113"): _HISTORY_COMPULSORY_SUBSTITUTE_NEW,
    ("歷史學系", "114"): _HISTORY_COMPULSORY_SUBSTITUTE_NEW,
}


# ── 比對邏輯 ──────────────────────────────────────────────────────────────────

def _match_required(
    required_courses: list,
    passed_courses: dict,
    dept_name: str = "",
    year: str = "",
    group_counts: dict = None,
) -> tuple:
    """必修清單 × 已修課程 → (passed_names, missing_names, credits_earned)"""
    passed_names: list[str] = []
    missing_names: list[str] = []
    credits_earned: int = 0
    group_counts = group_counts or {}

    plain = [c for c in required_courses if c["type"] == "必修"]
    groups: dict[str, list] = {}
    for c in required_courses:
        if c["type"] != "必修":
            groups.setdefault(c["type"], []).append(c)

    # used_substitutes 防止同一門替代課被重複使用（例如史學導論只能抵一門）
    dept_sub_map = _COMPULSORY_SUBSTITUTE_MAP.get((dept_name, year), {})
    used_substitutes: set[str] = set()
    for c in plain:
        name = c["name"]
        if name in passed_courses:
            passed_names.append(name)
            credits_earned += c["credits"]
        else:
            available = dept_sub_map.get(name, set()) & passed_courses.keys() - used_substitutes
            if available:
                used_substitutes.add(next(iter(available)))
                passed_names.append(name)
                credits_earned += c["credits"]
            else:
                missing_names.append(name)

    # 群修：每組只需一門通過，課名為佔位符時查 _GROUP_COURSE_MAP
    # group_counts 追蹤同名課修了幾學期（如資訊専題上下學期各3學分）
    dept_group_map = _GROUP_COURSE_MAP.get((dept_name, year), {})
    for group_type, courses in sorted(groups.items()):
        matched = [c for c in courses if c["name"] in passed_courses]
        if not matched:
            aliases = dept_group_map.get(group_type, set())
            if aliases & passed_courses.keys():
                matched = [courses[0]]
        if matched:
            course_name = matched[0]["name"]
            unit = matched[0]["credits"]
            semesters = group_counts.get(course_name, 1)
            passed_names.append(course_name)
            credits_earned += unit * semesters
        else:
            missing_names.append(courses[0]["name"])

    return passed_names, missing_names, credits_earned


# ── 公開介面 ──────────────────────────────────────────────────────────────────

def analyze_required(
    session_data: list,
    dept_name: str,
    year: str,
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """
    全人 JSON × 系所/學年 → {"passed", "missing", "credits_earned", "credits_needed"}
    含雙主修合併比對與去重。找不到系所時拋 ValueError。
    """
    should_close = conn is None
    if conn is None:
        conn = get_db()

    try:
        passed_courses = _collect_passed_courses(session_data)
        group_counts = _count_group_course_semesters(session_data)

        dept = _get_dept_row(conn, dept_name, year)
        if dept is None:
            raise ValueError(f"找不到系所：{dept_name}（{year}）")

        required = _get_required_courses(conn, dept["id"])
        main_passed, main_missing, main_credits_earned = _match_required(
            required, passed_courses, dept_name, year, group_counts
        )
        main_credits_needed = dept["compulsory_credits_required"]

        main_major = {
            "dept_name": dept_name,
            "year": year,
            "passed": main_passed,
            "missing": main_missing,
            "credits_earned": main_credits_earned,
            "credits_needed": main_credits_needed,
        }

        about = session_data[0]["課業學習"].get("aboutMe", {})
        double_major_info = _parse_double_major(about, fallback_year=year)
        double_major_block = None
        passed = list(main_passed)
        missing = list(main_missing)
        credits_earned = main_credits_earned
        credits_needed = main_credits_needed

        if double_major_info:
            double_major_dept_name, double_major_year = double_major_info
            double_major_dept = _get_dept_row(conn, double_major_dept_name, double_major_year)
            if double_major_dept is not None:
                double_major_required = _get_required_courses(conn, double_major_dept["id"])
                dm_passed, dm_missing, dm_credits_earned = _match_required(
                    double_major_required, passed_courses, double_major_dept_name, double_major_year, group_counts
                )
                dm_credits_needed = double_major_dept["compulsory_credits_required"]

                double_major_block = {
                    "dept_name": double_major_dept_name,
                    "year": double_major_year,
                    "passed": dm_passed,
                    "missing": dm_missing,
                    "credits_earned": dm_credits_earned,
                    "credits_needed": dm_credits_needed,
                }

                passed += dm_passed
                missing += dm_missing
                credits_earned += dm_credits_earned
                credits_needed += dm_credits_needed

        # 同一門課可能同時出現在主修與雙主修清單，去重後以 passed 優先
        seen_passed = set()
        deduped_passed = []
        for name in passed:
            if name not in seen_passed:
                seen_passed.add(name)
                deduped_passed.append(name)

        seen_missing = set()
        deduped_missing = []
        for name in missing:
            if name not in seen_passed and name not in seen_missing:
                seen_missing.add(name)
                deduped_missing.append(name)

        return {
            # 合計（向後相容）
            "passed": deduped_passed,
            "missing": deduped_missing,
            "credits_earned": credits_earned,
            "credits_needed": credits_needed,
            # 分項：主修必修
            "main_major": main_major,
            # 分項：雙主修必修（無雙主修時為 None）
            "double_major": double_major_block,
        }
    finally:
        if should_close:
            conn.close()


if __name__ == "__main__":
    import json
    import pprint

    for filename in [
        "tests/test_data/113cs雙主修電子電物輔系日文哲學.json",
        "tests/test_data/112cs_fake.json",
    ]:
        with open(filename, encoding="utf-8") as f:
            session = json.load(f)
        about = session[0]["課業學習"]["aboutMe"]
        print(f"=== {about['chineseName']}  主修：{about['registerMajor']}  雙主修：{repr(about['doubleMajor'])} ===")
        result = analyze_required(session, dept_name="資訊科學系", year="114")
        pprint.pprint(result)
        print()
