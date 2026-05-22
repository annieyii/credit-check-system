"""
輔系數字稽查工具 — PM 驗收用

用法：
  uv run python audit_minor.py <JSON檔> <輔系名稱> <學年度>

範例：
  uv run python audit_minor.py tests/test_data/cs_minor.json 財管系 112
  uv run python audit_minor.py tests/test_data/111cs輔日抵免資料.json 日文系 111
"""

import json
import sqlite3
import sys

from backend.database import get_db, normalize_name
from backend.minor import (
    _collect_all_passed_courses,
    _course_alternatives,
    _course_credits,
    _flatten_elective_groups,
    _get_minor_row,
)

SEP = "─" * 60


def audit(json_path: str, dept_name: str, year: str):
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    session = [raw] if isinstance(raw, dict) else raw

    conn = get_db()
    row = _get_minor_row(conn, dept_name, year)
    if row is None:
        print(f"[錯誤] 資料庫找不到：{dept_name} / {year} 學年")
        print("資料庫中現有系所：")
        for r in conn.execute("SELECT DISTINCT dept_name FROM minor_departments").fetchall():
            print(" ", r[0])
        return

    required_courses = json.loads(row["required_courses"])
    elective_groups  = json.loads(row["elective_groups"])
    credits_needed   = row["total_credits_required"]

    passed_courses = _collect_all_passed_courses(session)

    print(SEP)
    print(f"輔系：{dept_name}　學年：{year}")
    print(f"DB credits_needed = {credits_needed}")
    print(SEP)

    # ── 1. 學生所有及格課程 ──────────────────────────────────────
    print("\n【學生及格課程（來自 JSON）】")
    if not passed_courses:
        print("  （無）")
    for cname, credit in sorted(passed_courses.items()):
        print(f"  {cname}　{credit} 學分")

    # 正規化 lookup：全半形括號都能命中，value 是原始課名
    norm_to_orig = {normalize_name(k): k for k in passed_courses}

    def _hit(cname, alts):
        """回傳 passed_courses 裡命中的原始課名，或 None"""
        if normalize_name(cname) in norm_to_orig:
            return norm_to_orig[normalize_name(cname)]
        for a in alts:
            if normalize_name(a) in norm_to_orig:
                return norm_to_orig[normalize_name(a)]
        return None

    # ── 2. 必修比對 ──────────────────────────────────────────────
    print(f"\n【必修比對】共 {len(required_courses)} 門")
    req_credits_earned = 0.0
    for course in required_courses:
        cname      = course["course_name"]
        db_credit  = _course_credits(course)
        alts       = _course_alternatives(course)

        hit = _hit(cname, alts)

        if hit:
            req_credits_earned += db_credit
            alt_note = f"（透過替代課「{hit}」）" if hit != cname else ""
            print(f"  ✅ {cname}　DB學分={db_credit}　→ 計入 {db_credit} {alt_note}")
        else:
            alt_str = f"　備選={alts}" if alts else ""
            print(f"  ❌ {cname}　DB學分={db_credit}{alt_str}")

    print(f"  必修小計：{req_credits_earned} 學分")

    # ── 3. 選修比對 ──────────────────────────────────────────────
    groups = _flatten_elective_groups(elective_groups)
    elec_credits_earned = 0.0
    seen: set[str] = set()

    if not groups:
        print("\n【選修比對】無選修規則（elective_groups 為空）")
    else:
        print(f"\n【選修比對】共 {len(groups)} 個群組")
        for g in groups:
            gname       = g.get("group_name", "（無群組名）")
            min_credits = g.get("min_credits", "—")
            courses     = g.get("courses", [])
            g_earned    = 0.0

            print(f"\n  群組「{gname}」　最低應修={min_credits} 學分")
            for course in courses:
                cname     = course["course_name"]
                db_credit = _course_credits(course)
                alts      = _course_alternatives(course)

                hit = _hit(cname, alts)

                if hit and cname not in seen:
                    seen.add(cname)
                    student_credit = passed_courses.get(hit, 0)
                    counted = student_credit if student_credit > 0 else db_credit
                    g_earned += counted
                    elec_credits_earned += counted
                    alt_note = f"（透過「{hit}」）" if hit != cname else ""
                    print(f"    ✅ {cname}　DB={db_credit}　學生實際={student_credit}　→ 計入 {counted} {alt_note}")
                elif hit and cname in seen:
                    print(f"    ⚠️  {cname}　已在前群組計入，跳過")
                else:
                    alt_str = f"　備選={alts}" if alts else ""
                    print(f"    ❌ {cname}　DB={db_credit}{alt_str}")

            print(f"  群組小計：{g_earned} 學分")

    # ── 4. 彙總 ──────────────────────────────────────────────────
    total = req_credits_earned + elec_credits_earned
    print(f"\n{SEP}")
    print(f"必修計入：{req_credits_earned} 學分")
    print(f"選修計入：{elec_credits_earned} 學分")
    print(f"credits_earned 合計：{total} 學分")
    print(f"credits_needed（DB）：{credits_needed} 學分")
    gap = credits_needed - total
    if gap <= 0:
        print(f"結論：✅ 達標（多 {-gap} 學分）")
    else:
        print(f"結論：❌ 不足（差 {gap} 學分）")
    print(SEP)

    # ── 5. 與 analyze_minor 比較 ─────────────────────────────────
    print("\n【與 analyze_minor() 回傳值比較】")
    try:
        from backend.minor import analyze_minor
        result = analyze_minor(session, dept_name, year)
        fn_earned  = result["credits_earned"]
        fn_needed  = result["credits_needed"]
        fn_passed  = result["passed"]
        fn_missing = result["missing"]

        ok_earned = (fn_earned == int(total) if total == int(total) else fn_earned == total)
        print(f"  credits_earned： 稽查={total}　函式={fn_earned}　{'✅ 一致' if ok_earned else '❌ 不一致'}")
        print(f"  credits_needed： 稽查={credits_needed}　函式={fn_needed}　{'✅ 一致' if credits_needed == fn_needed else '❌ 不一致'}")
        print(f"  passed 課程（{len(fn_passed)} 門）：{fn_passed}")
        print(f"  missing 課程（{len(fn_missing)} 門）：{fn_missing}")
    except Exception as e:
        print(f"  ❌ analyze_minor() 執行失敗：{e}")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    audit(sys.argv[1], sys.argv[2], sys.argv[3])
