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


def analyze_pe(session_data, dept_name,year):
    data = session_data
    kl = data[0].get("課業學習", {})
    pe_require = kl.get("coursePlan", {}).get("commonPhysicalCount", "") or "4"

    pe_classes = []
    pass_count = 0

    # 抵免體育課（courseCode 以 "002" 開頭，或課名含「體育」）
    for course in kl.get("waivedCourseList", []):
        code = course.get("courseCode", "")
        name = course.get("courseName", "").strip()
        if code.startswith("002") or "體育" in name:
            credit = float(course.get("credit") or 1)  # 體育通常無 credit 欄位，預設 1 學期
            pass_count += 1
            pe_classes.append({
                "courseCode": code,
                "courseName": name,
                "credits": credit,
                "grade": "抵免"
            })

    graderecords = kl.get("gradeRecordList", [])
    for semester in graderecords:
        for course in semester.get("GradeRecords", []):
            classnumber= course.get("courseCode", "")
            classcategory= course.get("requiredOrElectiveCourse", "")
            if classnumber.startswith("002"):
                if course.get("score") == "成績未到或無成績":
                    continue
                if classcategory != "必":
                    continue
                if(course.get("score", "") != "停修"):
                  getpass = 0
                  if(course.get("score", "") == "通過"):
                    getpass = 1
                  if (getpass or float(course.get("score", "")) >= 60.0):
                    pass_count += 1
                    pe_classes.append({
                       "courseCode": classnumber,
                       "courseName": course.get("courseName", ""),
                       "credits": course.get("credit", "0.0"),
                       "grade": course.get("score", "")
                    })
    nowcount = pass_count
    result = True if nowcount >= int(pe_require) else False
    return {
        "credits_earned": nowcount,
        "credits_needed": int(pe_require),
        "passed": result,
        "courses": [course["courseName"] for course in pe_classes]
    }

def analyze_elective(session_data, dept_name,year):
    required_courses = get_required_courses(dept_name, year)
    required_course_names = {course["name"] for course in required_courses}
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
                if(course.get("score", "") != "停修"):
                  getpass = 0
                  if(course.get("score", "") == "通過"):
                    getpass = 1
                  if (getpass or float(course.get("score", "")) >= 60.0):
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
                if course.get("courseName","") not in required_course_names:
                    if(course.get("score", "") != "停修"):
                      getpass = 0
                      if(course.get("score", "") == "通過"):
                         getpass = 1
                      if (getpass or float(course.get("score", "")) >= 60.0):
                        pass_credit_count_outdept += int(float(course.get("credit", "0.0")))
                        ele_classes.append({
                           "courseCode": course.get("courseCode", ""),
                           "courseName": course.get("courseName", ""),
                           "credits": course.get("credit", "0.0"),
                           "grade": course.get("grade", "")
                        })
    pass_credit_count = pass_credit_count_indept + pass_credit_count_outdept

    cursor.execute("""
        SELECT compulsory_credits_required
        FROM departments
        WHERE id = ?
    """, (dept["id"],))
    required_credits = cursor.fetchone()["compulsory_credits_required"]
    required_ele_credits = 128-required_credits-28-4
    result = True if pass_credit_count >= required_ele_credits else False
    return {
        "credits_earned": pass_credit_count,
        "credits_needed": required_ele_credits,
        "passed": result,
        "in_dept_credits": pass_credit_count_indept,
        "out_dept_credits": pass_credit_count_outdept
    }
