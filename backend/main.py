from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.database import get_db
from backend.general import analyze_general
from backend.pe_elective import analyze_pe, analyze_elective
from backend.required import analyze_required
from backend.waiver import analyze_waiver

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


# --- 3. 上傳並分析全人成績單 ---
class AnalyzeRequest(BaseModel):
    role: str
    data: Any


@app.post("/api/v1/analyze")
def analyze(payload: AnalyzeRequest):
    if not payload.data:
        raise HTTPException(status_code=422, detail="資料不可為空")

    session_data = payload.data
    if not isinstance(session_data, list) or len(session_data) == 0:
        raise HTTPException(status_code=422, detail="資料格式錯誤：應為陣列")

    about = session_data[0].get("課業學習", {}).get("aboutMe", {})
    dept_name = about.get("registerMajor", "").strip()
    student_number = about.get("studentNumber", "")
    year = student_number[:3] if student_number else ""

    if not dept_name or not year:
        raise HTTPException(status_code=422, detail="無法從資料中取得系所或入學年度")

    conn = get_db()
    try:
        required = analyze_required(session_data, dept_name, year, conn)
        general = analyze_general(session_data, dept_name, year)
        pe = analyze_pe(session_data, dept_name, year)
        elective = analyze_elective(session_data, dept_name, year)
    finally:
        conn.close()

    waiver = analyze_waiver(session_data)

    required_credits_earned = required.get("credits_earned", 0)
    required_credits_needed = required.get("credits_needed", 0)
    pe_credits_earned = pe.get("credits_earned", 0)
    pe_credits_needed = pe.get("credits_needed", 0)
    general_credits_earned = general.get("credits_earned", 0)
    general_credits_needed = general.get("credits_needed", 0)
    elective_credits_earned = elective.get("credits_earned", 0)
    elective_credits_needed = elective.get("credits_needed", 0)
    total_credits_earned = (
        required_credits_earned + pe_credits_earned +
        general_credits_earned + elective_credits_earned
    )

    is_eligible_to_graduate = (
        len(required.get("missing", [])) == 0 and
        pe.get("passed", False) and
        general.get("passed", False) and
        elective.get("passed", False)
    )

    return {
        "dept_name": dept_name,
        "applicable_year": year,
        "summary": {
            "total_credits_earned": total_credits_earned,
            "required_credits_earned": required_credits_earned,
            "required_credits_needed": required_credits_needed,
            "pe_credits_earned": pe_credits_earned,
            "pe_credits_needed": pe_credits_needed,
            "general_credits_earned": general_credits_earned,
            "general_credits_needed": general_credits_needed,
            "elective_credits_earned": elective_credits_earned,
            "elective_credits_needed": elective_credits_needed,
        },
        "required_courses": {
            "passed": required.get("passed", []),
            "missing": required.get("missing", []),
        },
        "general_education": general,
        "physical_education": pe,
        "elective": elective,
        "waiver": waiver,
        "is_eligible_to_graduate": is_eligible_to_graduate,
    }


# --- 4. 健康檢查 ---
@app.get("/")
def root():
    return {"status": "ok", "message": "畢業學分計算系統 API 運作中"}
