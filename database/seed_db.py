import sqlite3
import json
import os
import glob

DB_PATH = os.path.join(os.path.dirname(__file__), "curriculum.db")
DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "必修")


def load_records(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def reset_department_data(cursor, dept_id):
    cursor.execute(
        """
        DELETE FROM course_schedules
        WHERE course_id IN (
            SELECT id FROM required_courses WHERE department_id = ?
        )
        """,
        (dept_id,),
    )
    cursor.execute("DELETE FROM required_courses WHERE department_id = ?", (dept_id,))
    cursor.execute("DELETE FROM special_rules WHERE department_id = ?", (dept_id,))


def seed_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 找所有年度的 result/*.json
    json_files = sorted(glob.glob(os.path.join(DATA_ROOT, "*", "result", "*.json")))
    print(f"📂 找到 {len(json_files)} 個 JSON 檔案，開始匯入...")

    imported_count = 0

    for filepath in json_files:
        records = load_records(filepath)
        if not records:
            print(f"  ⚠️ 略過無效 JSON：{os.path.basename(filepath)}")
            continue

        for data in records:
            meta = data.get("metadata", {})
            dept_name = str(meta.get("dept_name", "")).strip()
            applicable_year = str(meta.get("applicable_year", "")).strip()

            if not dept_name or not applicable_year:
                print(f"  ⚠️ 略過缺少 metadata 的資料：{os.path.basename(filepath)}")
                continue

            # --- 1. 插入/更新 departments ---
            cursor.execute(
                """
                INSERT OR IGNORE INTO departments
                    (source_file, dept_name, applicable_year,
                     min_graduation_credits, compulsory_credits_required)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    meta.get("source_file", ""),
                    dept_name,
                    applicable_year,
                    meta.get("min_graduation_credits", 0),
                    meta.get("compulsory_credits_required", 0),
                ),
            )

            cursor.execute(
                """
                UPDATE departments
                SET source_file = ?,
                    min_graduation_credits = ?,
                    compulsory_credits_required = ?
                WHERE dept_name = ? AND applicable_year = ?
                """,
                (
                    meta.get("source_file", ""),
                    meta.get("min_graduation_credits", 0),
                    meta.get("compulsory_credits_required", 0),
                    dept_name,
                    applicable_year,
                ),
            )

            # 取得這筆 department 的 id
            cursor.execute(
                """
                SELECT id FROM departments
                WHERE dept_name = ? AND applicable_year = ?
                """,
                (dept_name, applicable_year),
            )
            dept_id = cursor.fetchone()[0]

            # 先清除該系該年度舊資料，確保重跑不重複
            reset_department_data(cursor, dept_id)

            # --- 2. 插入 required_courses + course_schedules ---
            for course in data.get("required_courses", []):
                cursor.execute(
                    """
                    INSERT INTO required_courses
                        (department_id, name, type, credits, semesters,
                         suggested_year, recognition, course_code,
                         dual_major_recognition, dual_major_course_code, remarks)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dept_id,
                        course.get("name", ""),
                        course.get("type", ""),
                        course.get("credits", 0),
                        course.get("semesters", 1),
                        course.get("suggested_year", None),
                        course.get("recognition", ""),
                        course.get("course_code", None),
                        course.get("dual_major_recognition", ""),
                        course.get("dual_major_course_code", None),
                        course.get("remarks", None),
                    ),
                )

                course_id = cursor.lastrowid
                schedule = course.get("schedule", {})

                # --- 3. 插入 course_schedules ---
                cursor.execute(
                    """
                    INSERT INTO course_schedules
                        (course_id, Y1S1, Y1S2, Y2S1, Y2S2,
                         Y3S1, Y3S2, Y4S1, Y4S2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        course_id,
                        int(schedule.get("Y1S1", False)),
                        int(schedule.get("Y1S2", False)),
                        int(schedule.get("Y2S1", False)),
                        int(schedule.get("Y2S2", False)),
                        int(schedule.get("Y3S1", False)),
                        int(schedule.get("Y3S2", False)),
                        int(schedule.get("Y4S1", False)),
                        int(schedule.get("Y4S2", False)),
                    ),
                )

            # --- 4. 插入 special_rules ---
            for order, rule_text in enumerate(data.get("special_rules", []), start=1):
                cursor.execute(
                    """
                    INSERT INTO special_rules (department_id, rule_order, rule_text)
                    VALUES (?, ?, ?)
                    """,
                    (dept_id, order, rule_text),
                )

            imported_count += 1
            print(f"  ✅ {dept_name} ({applicable_year})")

    conn.commit()
    conn.close()
    print(f"\n🎉 所有資料匯入完成！共匯入 {imported_count} 筆系所年度資料")

if __name__ == "__main__":
    seed_db()