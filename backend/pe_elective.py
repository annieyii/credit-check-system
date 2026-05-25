from backend.database import get_db


def get_required_courses(dept_name: str, year: str) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM departments
        WHERE dept_name LIKE ? AND applicable_year = ?
    """, (f"%{dept_name}%", year))
    dept = cursor.fetchone()
    if not dept:
        conn.close()
        return []
    cursor.execute("""
        SELECT rc.name, rc.type, rc.credits, rc.suggested_year
        FROM required_courses rc
        WHERE rc.department_id = ?
        ORDER BY rc.suggested_year, rc.name
    """, (dept["id"],))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


#資訊系的群修清單 或許可移至資料庫
new_group_B = ["人工智慧概論", "資料庫系統", "資料科學", "機器學習概論", "電腦視覺"]
new_group_C = ["人機互動", "電腦圖學", "軟體開發環境應用設計", "虛擬實境與觸覺回饋互動", "視訊壓縮", "資訊視覺化"]
new_group_D = ["資訊安全", "資訊理論", "現代密碼學", "數位簽章", "工業物聯網與營運安全"]
new_group_E = ["計算機網路", "行動通訊網路", "網路與通訊概論", "分散式系統", "軟體工程概論", "等候理論"]


def _is_general_education(course: dict) -> bool:
    """判斷一門課是否為通識（語文 / 領域通識 / 書院），這些不應計入選修學分"""
    remark = (course.get("remark") or "").strip()
    name = (course.get("courseName") or "").strip()
    # 領域通識：人文通 / 社會通 / 自然通 / 資訊通 等（remark 含「通」）
    if "通" in remark:
        return True
    # 書院通識
    if remark == "書院":
        return True
    # 語文通識
    if name.startswith("大學英文") or name.startswith("國文") or name.startswith("進階國文"):
        return True
    return False


def analyze_pe(session_data, dept_name, year):
    """
    體育學分判定（109 學年度以後入學，每門 1 學分，共 4 門）

    規則：
    1. 同名體育課僅計第一次，其餘標記為「重複不計」
    2. 每學期上限 1 門；超出的標記為「超修不計」
    3. 大四（入學年 +3）每學期最多 2 門：若該學期偵測到 2 門，照計但設定 senior_warning，
       由前端提示「是否已申請大四加修體育」
    """
    data = session_data
    kl = data[0].get("課業學習", {})
    pe_require_raw = kl.get("coursePlan", {}).get("commonPhysicalCount", 4)
    try:
        pe_require = int(pe_require_raw)
    except (ValueError, TypeError):
        pe_require = 4

    try:
        entry_year = int(year)
    except (ValueError, TypeError):
        entry_year = 0
    senior_academic_year = entry_year + 3

    # --- 1. 收集所有及格/通過的必修體育課（含抵免）---
    collected = []

    for course in kl.get("waivedCourseList", []):
        code = course.get("courseCode", "")
        name = (course.get("courseName") or "").strip()
        if code.startswith("002") or "體育" in name:
            collected.append({
                "courseCode": code,
                "courseName": name,
                "credits": float(course.get("credit") or 1),
                "grade": "抵免",
                "semester": "waived",
                "academicYear": "",
            })

    for semester in kl.get("gradeRecordList", []):
        for course in semester.get("GradeRecords", []):
            code = course.get("courseCode", "")
            cat = course.get("requiredOrElectiveCourse", "")
            if not code.startswith("002"):
                continue
            if cat != "必":
                continue
            score_raw = course.get("score", "")
            if score_raw in ("成績未到或無成績", "停修"):
                continue
            getpass = (score_raw == "通過")
            if not getpass:
                try:
                    if float(score_raw) < 60:
                        continue
                except (ValueError, TypeError):
                    continue
            collected.append({
                "courseCode": code,
                "courseName": (course.get("courseName") or "").strip(),
                "credits": course.get("credit", "1.0"),
                "grade": score_raw,
                "semester": course.get("academicYearSemester", ""),
                "academicYear": course.get("academicYear", ""),
            })

    # --- 2. 規則判定：重複科目、每學期上限、大四特例 ---
    seen_names = set()
    semester_counts = {}
    senior_double_semesters = []

    def _sem_key(c):
        s = c.get("semester") or ""
        return (0, s) if s != "waived" else (-1, "")

    collected.sort(key=_sem_key)

    pe_classes = []
    pass_count = 0
    for c in collected:
        name = c["courseName"]
        sem = c.get("semester") or ""
        is_waived = (sem == "waived")
        ac_year_raw = c.get("academicYear") or (sem[:3] if len(sem) >= 3 else "")
        try:
            ac_year_int = int(ac_year_raw)
        except (ValueError, TypeError):
            ac_year_int = -1
        is_senior = (ac_year_int == senior_academic_year)
        limit = 2 if is_senior else 1

        # 規則 1：重複科目（抵免課程不適用，因抵免常以「體育」泛稱重複出現）
        if not is_waived and name and name in seen_names:
            status = "重複不計"
            pe_classes.append({**c, "status": status})
            continue

        # 規則 2 / 3：每學期上限（抵免課程沒有學期歸屬，不受限）
        if not is_waived and sem:
            count = semester_counts.get(sem, 0)
            if count >= limit:
                status = "超修不計"
                pe_classes.append({**c, "status": status})
                continue
            semester_counts[sem] = count + 1
            # 若大四該學期累計到 2 門，記錄供前端警示
            if is_senior and semester_counts[sem] == 2 and sem not in senior_double_semesters:
                senior_double_semesters.append(sem)

        # 抵免課程不加入 seen_names（避免之後同名正規課程被誤判為重複）
        if not is_waived and name:
            seen_names.add(name)
        pass_count += 1
        pe_classes.append({**c, "status": "通過"})

    passed = pass_count >= pe_require
    return {
        "credits_earned": pass_count,
        "credits_needed": pe_require,
        "passed": passed,
        "courses": [c["courseName"] for c in pe_classes if c.get("status") == "通過"],
        "course_details": pe_classes,  # 含 status 的完整清單，供前端顯示
        "senior_warning": bool(senior_double_semesters),
        "senior_warning_semesters": senior_double_semesters,
    }

def analyze_elective(session_data, dept_name, year, total_required_credits=None):
    required_courses = get_required_courses(dept_name, year)
    required_course_names = {course["name"] for course in required_courses}
    
    # 獲取已修必修課程清單（含雙主修），避免在選修中重複計算
    from backend.required import analyze_required
    conn = get_db()
    try:
        required_analysis = analyze_required(session_data, dept_name, year, conn)
        # 收集所有已通過的必修課程名稱（含雙主修）
        passed_required_courses = set(required_analysis.get("passed", []))
    finally:
        conn.close()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM departments
        WHERE dept_name LIKE ? AND applicable_year = ?
    """, (f"%{dept_name}%", year))
    dept = cursor.fetchone()
    cursor.execute("""
        SELECT rc.name
        FROM required_courses rc
        JOIN departments d ON rc.department_id = d.id
        JOIN course_schedules cs ON cs.course_id = rc.id
        WHERE d.id = ? AND rc.type = '群B'
        ORDER BY rc.suggested_year, rc.name
    """, (dept["id"],))
    group_result = cursor.fetchall()
    old_group_B = [course["name"] for course in group_result]
    cursor.execute("""
        SELECT rc.name
        FROM required_courses rc
        JOIN departments d ON rc.department_id = d.id
        JOIN course_schedules cs ON cs.course_id = rc.id
        WHERE d.id = ? AND rc.type = '群C'
        ORDER BY rc.suggested_year, rc.name
    """, (dept["id"],))
    group_result = cursor.fetchall()
    old_group_C = [course["name"] for course in group_result]

    data = session_data
    graderecords = data[0].get("課業學習", {}).get("gradeRecordList", [])
    pass_credit_count_indept = 0
    pass_credit_count_outdept = 0
    ele_classes = []
    old_group_b_threshold = 1
    old_group_c_threshold = 1
    group_b_threshold = 1
    group_c_threshold = 1
    group_d_threshold = 1
    group_e_threshold = 1
    group_threshold = 3
    for semester in graderecords:
        for course in semester.get("GradeRecords", []):
            classcategory= course.get("requiredOrElectiveCourse", "")
            code_prefix = course.get("courseCode", "") or ""
            # 體育(002) / 國防(003) 一律不計入選修
            if code_prefix.startswith("002") or code_prefix.startswith("003"):
                continue
            #處理資訊系群修的課
            if classcategory =="群":
                if course.get("score") == "成績未到或無成績":
                    continue
                if(course.get("score", "") != "停修"):
                  getpass = 0
                  if(course.get("score", "") == "通過"):
                    getpass = 1
                  if (getpass or float(course.get("score","")) >= 60.0):
                   if(year == "110" or year == "111"):
                    if course.get("courseName","") in old_group_B:
                        if(old_group_b_threshold > 0):
                            old_group_b_threshold -= 1
                        else:
                            pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                            ele_classes.append({
                                 "courseCode": course.get("courseCode", ""),
                                 "courseName": course.get("courseName", ""),
                                 "credits": course.get("credit", "0.0"),
                                "grade": course.get("score", "")
                            })
                    elif course.get("courseName","") in old_group_C:
                            if(old_group_c_threshold > 0):
                                old_group_c_threshold -= 1
                            else:
                                pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                ele_classes.append({
                                        "courseCode": course.get("courseCode", ""),
                                        "courseName": course.get("courseName", ""),
                                        "credits": course.get("credit", "0.0"),
                                        "grade": course.get("score", "")
                                })
                   else:
                    if course.get("courseName","") in new_group_B:
                        if(group_threshold > 0):
                            if(group_b_threshold > 0):
                               group_b_threshold -= 1
                            else:
                                pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                ele_classes.append({
                                     "courseCode": course.get("courseCode", ""),
                                     "courseName": course.get("courseName", ""),
                                     "credits": course.get("credit", "0.0"),
                                    "grade": course.get("score", "")
                                })
                        else:
                            if(course.get("courseCode","").startswith("student_dept")):
                               pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                               ele_classes.append({
                                 "courseCode": course.get("courseCode", ""),
                                 "courseName": course.get("courseName", ""),
                                 "credits": course.get("credit", "0.0"),
                                "grade": course.get("score", "")
                               })
                    elif course.get("courseName","") in new_group_C:
                            if(group_threshold > 0):
                                if(group_c_threshold > 0):
                                    group_c_threshold -= 1
                                else:
                                    pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                    ele_classes.append({
                                            "courseCode": course.get("courseCode", ""),
                                            "courseName": course.get("courseName", ""),
                                            "credits": course.get("credit", "0.0"),
                                            "grade": course.get("score", "")
                                    })
                            else:
                                if(course.get("courseCode","").startswith("student_dept")):
                                    pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                    ele_classes.append({
                                         "courseCode": course.get("courseCode", ""),
                                        "courseName": course.get("courseName", ""),
                                         "credits": course.get("credit", "0.0"),
                                        "grade": course.get("score", "")
                                    })
                    elif course.get("courseName","") in new_group_D:
                            if(group_threshold > 0):
                                if(group_d_threshold > 0):
                                    group_d_threshold -= 1
                                else:
                                    pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                    ele_classes.append({
                                                "courseCode": course.get("courseCode", ""),
                                                "courseName": course.get("courseName", ""),
                                                "credits": course.get("credit", "0.0"),
                                                "grade": course.get("score", "")
                                    })
                            else:
                                if(course.get("courseCode","").startswith("student_dept")):
                                    pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                    ele_classes.append({
                                        "courseCode": course.get("courseCode", ""),
                                        "courseName": course.get("courseName", ""),
                                        "credits": course.get("credit", "0.0"),
                                        "grade": course.get("score", "")
                                    })
                    elif course.get("courseName","") in new_group_E:
                           if(group_threshold > 0):
                               if(group_e_threshold > 0):
                                   group_e_threshold -= 1
                               else:
                                    pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                    ele_classes.append({
                                                "courseCode": course.get("courseCode", ""),
                                                "courseName": course.get("courseName", ""),
                                                "credits": course.get("credit", "0.0"),
                                                "grade": course.get("score", "")
                                    })
                           else:
                                if(course.get("courseCode","").startswith("student_dept")):
                                    pass_credit_count_indept += int(float(course.get("credit", "0.0")))
                                    ele_classes.append({
                                        "courseCode": course.get("courseCode", ""),
                                        "courseName": course.get("courseName", ""),
                                         "credits": course.get("credit", "0.0"),
                                        "grade": course.get("score", "")
                                    })
            #處理選修別的課
            if classcategory =="選":
                if course.get("score") == "成績未到或無成績":
                    continue
                if course.get("courseCode").startswith("003"): #國防不算
                    continue
                if course.get("courseCode").startswith("002"): #體育選修不算
                    continue
                if _is_general_education(course):  # 通識不算選修，由 general 模組處理
                    continue
                if(course.get("score", "") != "停修"):
                  getpass = 0
                  if(course.get("score", "") == "通過"):
                    getpass = 1
                  if (getpass or float(course.get("score", "")) >= 60.0):
                    # 檢查是否為已修的必修課程（含雙主修），避免重複計算
                    course_name = course.get("courseName", "")
                    if course_name in passed_required_courses:
                        continue  # 已在必修區域計算，跳過
                    if course.get("courseCode","").startswith("student_dept"):
                        pass_credit_count_indept += int(float(course.get("credit", 0)))
                    else:
                        pass_credit_count_outdept += int(float(course.get("credit", 0)))
                    ele_classes.append({
                    "courseCode": course.get("courseCode", ""),
                    "courseName": course.get("courseName", ""),
                    "credits": course.get("credit", "0.0"),
                    "grade": course.get("score", "")
                   })
            #處理必修別的課
            if classcategory =="必":
                if course.get("score") == "成績未到或無成績":
                    continue
                if _is_general_education(course):  # 通識不算選修，由 general 模組處理
                    continue
                if course.get("courseName","") not in required_course_names:
                    if(course.get("score", "") != "停修"):
                      getpass = 0
                      if(course.get("score", "") == "通過"):
                         getpass = 1
                      if (getpass or float(course.get("score", "")) >= 60.0):
                        # 檢查是否為已修的必修課程（含雙主修），避免重複計算
                        course_name = course.get("courseName", "")
                        if course_name in passed_required_courses:
                            continue  # 已在必修區域計算，跳過
                        pass_credit_count_outdept += int(float(course.get("credit", "0.0")))
                        ele_classes.append({
                           "courseCode": course.get("courseCode", ""),
                           "courseName": course.get("courseName", ""),
                           "credits": course.get("credit", "0.0"),
                           "grade": course.get("grade", "")
                        })
    pass_credit_count = pass_credit_count_indept + pass_credit_count_outdept

    in_dept_group_names = set(
        old_group_B + old_group_C + new_group_B + new_group_C + new_group_D + new_group_E
    )
    in_dept_courses = []
    out_dept_courses = []
    for c in ele_classes:
        code = c.get("courseCode", "") or ""
        name = c.get("courseName", "") or ""
        if code.startswith("student_dept") or name in in_dept_group_names:
            in_dept_courses.append(c)
        else:
            out_dept_courses.append(c)

    if total_required_credits is None:
        cursor.execute("""
            SELECT compulsory_credits_required
            FROM departments
            WHERE id = ?
        """, (dept["id"],))
        required_credits = cursor.fetchone()["compulsory_credits_required"]
    else:
        required_credits = total_required_credits
    required_ele_credits = max(0, 128 - required_credits - 28 - 4)
    result = True if pass_credit_count >= required_ele_credits else False
    return {
        "credits_earned": pass_credit_count,
        "credits_needed": required_ele_credits,
        "passed": result,
        "in_dept_credits": pass_credit_count_indept,
        "out_dept_credits": pass_credit_count_outdept,
        "in_dept_courses": in_dept_courses,
        "out_dept_courses": out_dept_courses,
    }
