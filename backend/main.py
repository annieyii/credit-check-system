import traceback
import re
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.database import get_db
from backend.general import analyze_general
from backend.minor import analyze_minor
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


# 全域例外處理：確保 500 錯誤回應也帶 CORS headers，避免前端顯示為 Network Error
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"伺服器內部錯誤：{type(exc).__name__}: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": "*"},
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


def _extract_minor_targets(about: dict) -> list[tuple[str, str]]:
    register_minor_raw = about.get("registerMinor", "").strip()
    register_minor_names = [name.strip() for name in register_minor_raw.split("、") if name.strip()]

    fallback_minor_names: list[str] = []
    fallback_minor_years: list[str] = []
    for key in ("minor1", "minor2"):
        raw_minor = about.get(key, "").strip()
        if raw_minor:
            fallback_minor_names.append(re.sub(r"（\d+）", "", raw_minor).strip())
            year_match = re.search(r"（(\d+)）", raw_minor)
            fallback_minor_years.append(year_match.group(1) if year_match else "")
        else:
            fallback_minor_years.append("")

    if not register_minor_names:
        register_minor_names = [name for name in fallback_minor_names if name]

    student_year = about.get("studentNumber", "")[:3]

    minor_targets: list[tuple[str, str]] = []
    for index, minor_name in enumerate(register_minor_names):
        if not minor_name:
            continue
        minor_year = fallback_minor_years[index] if index < len(fallback_minor_years) else ""
        minor_targets.append((minor_name, minor_year or student_year))

    return minor_targets


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

    minor_targets = _extract_minor_targets(about)

    conn = get_db()
    try:
        required = analyze_required(session_data, dept_name, year, conn)
        general = analyze_general(session_data, dept_name, year)
        pe = analyze_pe(session_data, dept_name, year)
        elective = analyze_elective(
            session_data, dept_name, year,
            total_required_credits=required.get("credits_needed"),
        )
        minor_results = []
        for minor_dept, minor_year in minor_targets:
            try:
                minor_result = analyze_minor(session_data, minor_dept, minor_year, conn)
            except ValueError:
                minor_result = None
            minor_results.append({
                "dept_name": minor_dept,
                "applicable_year": minor_year,
                "result": minor_result,
            })
        minor = minor_results[0]["result"] if minor_results else None
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
            "main_major": required.get("main_major"),
            "double_major": required.get("double_major"),
        },
        "general_education": general,
        "physical_education": pe,
        "elective": elective,
        "waiver": waiver,
        "minor": minor,
        "minor_details": minor_results,
        "is_eligible_to_graduate": is_eligible_to_graduate,
    }


# --- 4. 健康檢查 ---
@app.get("/")
def root():
    return {"status": "ok", "message": "畢業學分計算系統 API 運作中"}
