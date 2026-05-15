from backend.database import get_db


def _classify(name: str, cursor) -> str:
    """課名 → 類別標籤（純名稱判斷）"""
    if "體育" in name:
        return "體育"
    if "國防" in name:
        return "國防"
    if "國文" in name:
        return "語言通識（中文）"
    if "英文" in name:
        return "語言通識（英文）"

    # 查詢通識課程資料庫（以課名比對）
    cursor.execute(
        "SELECT type FROM general_courses WHERE course_name = ?", (name,)
    )
    row = cursor.fetchone()
    if row:
        return f"通識（{row['type']}）"

    # 課名含「通識」視為通識抵免
    if "通識" in name:
        return "通識"

    return "其他必修"


def analyze_waiver(session_data: list) -> dict:
    """
    全人 JSON → 抵免課程彙整
    回傳：已抵免課程清單、總抵免學分、依類別分類統計
    """
    kl = session_data[0].get("課業學習", {})
    waived_list = kl.get("waivedCourseList", [])

    conn = get_db()
    cursor = conn.cursor()

    courses = []
    total_credits = 0.0
    by_category: dict[str, float] = {}

    for c in waived_list:
        name = c.get("courseName", "").strip()
        code = c.get("courseCode", "")
        credit = float(c.get("credit") or 0)
        remark = c.get("remark", "")
        category = _classify(name, cursor)

        courses.append({
            "courseCode": code,
            "courseName": name,
            "credits": credit,
            "category": category,
            "remark": remark,
        })
        total_credits += credit
        by_category[category] = by_category.get(category, 0.0) + credit

    conn.close()

    return {
        "total_credits": total_credits,
        "course_count": len(courses),
        "by_category": by_category,
        "courses": courses,
    }
