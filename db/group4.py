import sqlite3
import json
import os

DB_PATH = r"db/database/curriculum.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f" 找不到資料庫檔案：{DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    # 讓查詢結果可以像字典一樣用名稱存取
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()

    # 建立 PM 要求的資料表 (如果不存在)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS minor_departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT,
            applicable_year TEXT,
            required_courses TEXT, -- 存必修課 JSON
            elective_groups TEXT,  -- 存選修群組 JSON
            total_credits_required INTEGER
        )
    """)

    #  定義Group4的 11 個系所
    years = ["110", "111", "112", "113", "114"]
    group4_depts = [
        "地政學系土地管理組", "地政學系土地測量與資訊組", "土耳其語文學系", 
        "國際經營與貿易學系", "哲學系", "東南亞語言與文化學士學位學程印尼文組", 
        "創新國際學院學士班", "公共行政學系", "傳播學院大一大二不分系", 
        "企業管理學系", "中國文學系"
    ]

    for year in years:
        for dept in group4_depts:
            # 這裡會去舊表找對應年份的資料
            cursor.execute("""
                SELECT rc.name, rc.credits
                FROM required_courses rc
                JOIN departments d ON rc.department_id = d.id
                WHERE d.dept_name = ? AND d.applicable_year = ?
            """, (dept, year))
            
            rows = cursor.fetchall()
            
            # 如果該年份沒資料，暫時用 110 年的資料 (或者選擇跳過)
            if not rows:
                # print(f"  {dept} ({year}) 查無資料，跳過。")
                continue

            required_list = [{"course_name": r["name"], "credits": r["credits"], "alternatives": []} for r in rows]
            total_credits = sum(r["credits"] for r in rows)

            # 寫入新表 minor_departments
            cursor.execute("DELETE FROM minor_departments WHERE dept_name = ? AND applicable_year = ?", (dept, year))
            cursor.execute("""
                INSERT INTO minor_departments 
                (dept_name, applicable_year, required_courses, elective_groups, total_credits_required)
                VALUES (?, ?, ?, ?, ?)
            """, (dept, year, json.dumps(required_list, ensure_ascii=False), "[]", total_credits))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()