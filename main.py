from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_db

app = FastAPI()

# 允許前端跨域存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. 查所有系所清單 ---
@app.get("/departments")
def get_departments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT dept_name, applicable_year, 
               min_graduation_credits, compulsory_credits_required
        FROM departments
        ORDER BY applicable_year, dept_name
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# --- 2. 查某系某學年的必修課清單 ---
@app.get("/departments/{dept_name}/courses")
def get_required_courses(dept_name: str, year: str = "114"):
    conn = get_db()
    cursor = conn.cursor()

    # 先確認系所存在
    cursor.execute("""
        SELECT id FROM departments
        WHERE dept_name LIKE ? AND applicable_year = ?
    """, (f"%{dept_name}%", year))
    dept = cursor.fetchone()

    if not dept:
        raise HTTPException(status_code=404, detail="找不到該系所或學年度")

    # 查必修課程（含開課學期）
    cursor.execute("""
        SELECT rc.name, rc.type, rc.credits, rc.suggested_year,
               rc.course_code, rc.remarks,
               cs.Y1S1, cs.Y1S2, cs.Y2S1, cs.Y2S2,
               cs.Y3S1, cs.Y3S2, cs.Y4S1, cs.Y4S2
        FROM required_courses rc
        JOIN departments d ON rc.department_id = d.id
        JOIN course_schedules cs ON cs.course_id = rc.id
        WHERE d.id = ?
        ORDER BY rc.suggested_year, rc.name
    """, (dept["id"],))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# --- 3. 健康檢查 ---
@app.get("/")
def root():
    return {"status": "ok", "message": "畢業學分計算系統 API 運作中"}