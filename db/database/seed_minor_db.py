import sqlite3
import json
import os
import re
import glob

DB_PATH = os.path.join(os.path.dirname(__file__), "curriculum.db")
DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "輔系")


def _parse_credits(val):
    if isinstance(val, dict):
        return int(val.get("min", 0))
    if isinstance(val, (int, float)):
        return int(val)
    return 0


def _is_course_code(s):
    return bool(re.fullmatch(r"\d{9}", str(s).strip()))


def _normalize_alternatives(alts):
    """
    alternative_courses 有三種格式：
    - []
    - [{course_name, credits}]   ← 主流
    - ["課名" or "9位數課號"]    ← 少數，過濾掉課號
    回傳純課名 list[str]
    """
    result = []
    for alt in alts:
        if isinstance(alt, dict):
            name = alt.get("course_name", "").strip()
            if name:
                result.append(name)
        elif isinstance(alt, str):
            name = alt.strip()
            if name and not _is_course_code(name):
                result.append(name)
    return result


def _normalize(data):
    cs = data.get("course_structure", {})
    summary = data.get("credit_summary", {})
    breakdown = summary.get("breakdown", {})

    # required_courses
    required_courses = []
    for c in cs.get("required_courses", []):
        name = c.get("course_name", "").strip()
        if not name:
            continue
        required_courses.append({
            "course_name": name,
            "credits": _parse_credits(c.get("credits", 0)),
            "alternatives": _normalize_alternatives(c.get("alternative_courses", [])),
        })

    # elective_groups（foundation_courses / elective_courses / general_electives 忽略）
    elective_groups = []
    for group in cs.get("group_electives", {}).get("groups", []):
        courses = []
        for c in group.get("courses", []):
            name = c.get("course_name", "").strip()
            if not name:
                continue
            courses.append({
                "course_name": name,
                "credits": _parse_credits(c.get("credits", 0)),
            })
        elective_groups.append({
            "group_name": group.get("group_name", ""),
            "min_credits": int(group.get("min_credits_required", 0)),
            "courses": courses,
        })

    # group_elective_credits：創國用 a+b，東南亞語系用 elective，其餘用 group_elective
    if "group_elective" in breakdown:
        group_elective_credits = int(breakdown["group_elective"])
    elif "group_elective_a" in breakdown:
        group_elective_credits = int(breakdown.get("group_elective_a", 0)) + int(breakdown.get("group_elective_b", 0))
    else:
        group_elective_credits = int(breakdown.get("elective", 0))

    return {
        "total_credits_required": int(summary.get("total_credits_required", 0)),
        "required_credits": int(breakdown.get("required", 0)),
        "group_elective_credits": group_elective_credits,
        "required_courses": required_courses,
        "elective_groups": elective_groups,
        "special_regulations": data.get("special_regulations", []),
    }


def seed_minor_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    json_files = sorted(glob.glob(os.path.join(DATA_ROOT, "*/result/*.json")))
    print(f"📂 找到 {len(json_files)} 個輔系 JSON 檔案，開始匯入...")

    imported = 0
    warned = 0

    for filepath in json_files:
        parts = filepath.replace("\\", "/").split("/")
        applicable_year = parts[-3]
        dept_name = os.path.splitext(parts[-1])[0]

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        norm = _normalize(data)

        if not norm["required_courses"] and not norm["elective_groups"]:
            print(f"  ⚠️  {dept_name} ({applicable_year})：required_courses 與 elective_groups 均為空")
            warned += 1

        for c in norm["required_courses"]:
            if c["credits"] == 0:
                print(f"  ⚠️  {dept_name} ({applicable_year})：必修「{c['course_name']}」credits=0")
                warned += 1

        for g in norm["elective_groups"]:
            if g["min_credits"] == 0:
                print(f"  ⚠️  {dept_name} ({applicable_year})：選修群組「{g['group_name']}」min_credits=0，請參閱 special_regulations")
                warned += 1

        cursor.execute(
            """
            INSERT OR REPLACE INTO minor_departments
                (dept_name, applicable_year, total_credits_required,
                 required_credits, group_elective_credits,
                 required_courses, elective_groups, special_regulations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dept_name,
                applicable_year,
                norm["total_credits_required"],
                norm["required_credits"],
                norm["group_elective_credits"],
                json.dumps(norm["required_courses"], ensure_ascii=False),
                json.dumps(norm["elective_groups"], ensure_ascii=False),
                json.dumps(norm["special_regulations"], ensure_ascii=False),
            ),
        )

        imported += 1
        print(f"  ✅ {dept_name} ({applicable_year})")

    conn.commit()
    conn.close()
    print(f"\n🎉 輔系資料匯入完成！共 {imported} 筆，{warned} 筆有警告")


if __name__ == "__main__":
    seed_minor_db()
