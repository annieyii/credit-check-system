"""
使用方式（從專案根目錄執行）：
    python3 tests/required_double_test.py tests/test_data/112cs_fake.json
    python3 tests/required_double_test.py tests/test_data/111cs輔日抵免資料.json
    python3 tests/required_double_test.py tests/test_data/113cs雙主修電子電物輔系日文哲學.json
"""
import json
import sys
import os

# 確保專案根目錄在 sys.path，無論從哪裡執行
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.database import get_db
from backend.general import analyze_general
from backend.pe_elective import analyze_pe, analyze_elective
from backend.required import analyze_required
from backend.waiver import analyze_waiver


SEP  = "─" * 50
SEP2 = "═" * 50


def _check(earned, needed):
    return "✅ 通過" if earned >= needed else f"❌ 不足（差 {needed - earned:.1f} 學分）"


def print_required(r: dict):
    print(f"\n{'必修課程':═<20}")
    print(f"  已修：{r['credits_earned']} / {r['credits_needed']} 學分  {_check(r['credits_earned'], r['credits_needed'])}")
    print(f"  已修課程（{len(r['passed'])} 門）：")
    for c in r["passed"]:
        print(f"    ✓ {c}")
    if r["missing"]:
        print(f"  尚未修（{len(r['missing'])} 門）：")
        for c in r["missing"]:
            print(f"    ✗ {c}")
    else:
        print("  尚未修：（無）")


def print_general(g: dict):
    total = g["credits_earned"] + g["credits_needed"]
    status = "✅ 通過" if g["passed"] else f"❌ 不足（差 {g['credits_needed']:.1f} 學分）"
    print(f"\n{'通識課程':═<20}")
    print(f"  已修：{g['credits_earned']} / {total:.0f} 學分  {status}")
    print(f"  各領域：")
    for field, credit in g["by_category"].items():
        print(f"    {field}：{credit} 學分")


def print_pe(p: dict):
    print(f"\n{'體育':═<20}")
    print(f"  已修：{p['credits_earned']} / {p['credits_needed']} 學分  {_check(p['credits_earned'], p['credits_needed'])}")
    print(f"  課程：")
    for c in p["courses"]:
        print(f"    ✓ {c}")


def print_elective(e: dict):
    print(f"\n{'選修課程':═<20}")
    print(f"  已修：{e['credits_earned']} / {e['credits_needed']} 學分  {_check(e['credits_earned'], e['credits_needed'])}")
    print(f"  系內選修：{e['in_dept_credits']} 學分")
    print(f"  系外選修：{e['out_dept_credits']} 學分")


def print_waiver(w: dict):
    print(f"\n{'抵免課程':═<20}")
    print(f"  總抵免：{w['total_credits']} 學分（共 {w['course_count']} 門）")
    if w["by_category"]:
        print(f"  各類別：")
        for cat, credit in w["by_category"].items():
            print(f"    {cat}：{credit} 學分")
        print(f"  明細：")
        for c in w["courses"]:
            print(f"    [{c['category']}] {c['courseName']}  {c['credits']} 學分")
    else:
        print("  （無抵免課程）")


def main():
    if len(sys.argv) < 2:
        print("用法：python3 tests/show_analysis.py <json路徑>")
        print("範例：python3 tests/show_analysis.py tests/test_data/112cs_fake.json")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        session_data = json.load(f)

    about = session_data[0].get("課業學習", {}).get("aboutMe", {})
    dept_name = about.get("registerMajor", "").strip()
    student_number = about.get("studentNumber", "")
    year = student_number[:3] if student_number else ""
    student_name = about.get("chineseName", "")

    print(SEP2)
    print(f"  學生：{student_name}　系所：{dept_name}　入學年度：{year}")
    print(SEP2)

    conn = get_db()
    try:
        required = analyze_required(session_data, dept_name, year, conn)
        general  = analyze_general(session_data, dept_name, year)
        pe       = analyze_pe(session_data, dept_name, year)
        elective = analyze_elective(session_data, dept_name, year)
    finally:
        conn.close()

    waiver = analyze_waiver(session_data)

    print_required(required)
    print_general(general)
    print_pe(pe)
    print_elective(elective)
    print_waiver(waiver)
    print(f"\n{SEP2}")


if __name__ == "__main__":
    main()
