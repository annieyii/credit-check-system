## 資料庫說明

### 如何初始化資料庫
cd database
python init_db.py   # 建立資料表
python seed_db.py   # 匯入所有必修課程資料

### 資料庫檔案位置
database/curriculum.db

### 資料表說明
- `departments`：所有系所基本資訊（系名、學年、最低畢業學分）
- `required_courses`：各系各年度課程清單（含修別、學分、科目代碼等）
- `course_schedules`：每門課的開課學期（Y1S1～Y4S2，與 required_courses 1對1）
- `special_rules`：各系修課特殊規定
- `student_records`：學生上傳的修課紀錄（由 upload API 寫入）

### 後端查詢範例（Python）
```python
import sqlite3
conn = sqlite3.connect("database/curriculum.db")
cursor = conn.cursor()

# 查某系某學年的必修課（含開課學期）
cursor.execute("""
    SELECT rc.name, rc.credits, rc.type, rc.suggested_year,
           cs.Y1S1, cs.Y1S2, cs.Y2S1, cs.Y2S2,
           cs.Y3S1, cs.Y3S2, cs.Y4S1, cs.Y4S2
    FROM required_courses rc
    JOIN departments d ON rc.department_id = d.id
    JOIN course_schedules cs ON cs.course_id = rc.id
    WHERE d.dept_name LIKE '資訊科學系%'
      AND d.applicable_year = '114'
      AND rc.type = '必修'
    ORDER BY rc.suggested_year
""")

# 查某系的特殊規定
# dept_name 可能包含「學士班/表名」等附加文字，建議使用 LIKE '系名%' 查詢。
cursor.execute("""
    SELECT rule_text FROM special_rules
    WHERE department_id = (
        SELECT id FROM departments
        WHERE dept_name LIKE '資訊科學系%' AND applicable_year = '114'
    )
    ORDER BY rule_order
""")
```
