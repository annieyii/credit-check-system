import sqlite3
import os

# 取得目前這個 general.py 所在的絕對路徑
current_dir = os.path.dirname(os.path.abspath(__file__))

# 正確指向專案中的資料庫位置 (向上跳一層到根目錄，再進到 db/database)
DB_PATH = os.path.abspath(os.path.join(current_dir, "..", "db", "database", "curriculum.db"))

def analyze_general(session_data, dept_name, year):
    if hasattr(session_data, "dict"):
        session_data = session_data.dict()
    elif hasattr(session_data, "model_dump"): # 支援 Pydantic v2
        session_data = session_data.model_dump()

    # 2. 處理 NCCU 匯出的 List 格式
    # 包含字典的列表
    if isinstance(session_data, list) and len(session_data) > 0:
        session_data = session_data[0]

    # 3. 如果 session_data 裡面還有一層 "data" (視 Payload 結構而定)
    # 根據提供的 payload，資料可能藏在 data 鍵值中
    actual_data = session_data.get("data") if isinstance(session_data, dict) else None
    if isinstance(actual_data, list) and len(actual_data) > 0:
        session_data = actual_data[0]

    # 4. 定位到「課業學習」
    study_data = session_data.get("課業學習")
    if not study_data:
        return {"error": "JSON 結構錯誤：找不到 '課業學習' 欄位"}

    # --- 1. 新增：從資料庫撈取通識門檻 ---
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 根據系名與入學年搜尋門檻 (例如: 資科系 111)
    cursor.execute("""
        SELECT ger.total_required, ger.compulsory_lang, ger.min_humanities,
               ger.min_social, ger.min_natural
        FROM general_education_requirements ger
        JOIN departments d ON ger.department_id = d.id
        WHERE d.dept_name LIKE ? AND d.applicable_year = ?
    """, (f"{dept_name}%", year))

    threshold = cursor.fetchone()

    # 門檻預設值 (避免查不到時程式崩潰)
    req_total, req_lang, req_hum, req_soc, req_nat = (threshold if threshold else (28, 12, 3, 3, 3))

    # --- 2. 初始化統計學分 ---
    humanities = 0
    social_sciences = 0
    natural_sciences = 0
    college_general_course = 0
    english = 0
    chinese = 0
    info_literacy = 0  # 資訊通識學分
    others = 0 # 存放無法分類但屬於通識的學分

    # 核心通識追蹤：記錄已修過核心通識的領域（人文/社會/自然）
    core_domains_taken = set()
    # 核心通識課程清單（供前端顯示）
    core_courses = []
    # 資訊通識課程清單（供前端顯示）
    info_literacy_courses = []

    # 判斷是否為資科系（資訊科學系）
    is_info_dept = ("資科" in (dept_name or "")) or ("資訊科學" in (dept_name or ""))

    # 修正：直接存取字典鍵值，移除 .data
    try:
        # 正確提取清單
        course_data = study_data["gradeRecordList"]
        waived_data = study_data["waivedCourseList"]
    except KeyError as e:
        return {"error": f"JSON 結構缺少關鍵欄位: {str(e)}"}

    # 3.單一領域通識計算
    for year_data in course_data:
        for course in year_data["GradeRecords"]:
            credit = float(course.get("credit", 0))
            remark = course.get("remark", "")

            # 關鍵修正點：在這裡定義 score_raw
            score_raw = course.get("score", "")
            course_name = course.get("courseName", "")

            # 修正：碩班資料會有 "成績未到或無成績"，需安全轉換
            try:
                score = float(score_raw)
                if score < 60:
                    continue
            except (ValueError, TypeError):
                # 如果是「成績未到」，在畢業判定中通常不計入
                continue

            cursor.execute("SELECT type, is_core FROM general_courses WHERE course_name = ?", (course_name,))
            db_row = cursor.fetchone()

            # 判斷是否為核心通識
            db_type = db_row[0] if db_row else ""
            # 修正原代碼變數命名衝突：將資料庫讀取的值存為 db_is_core
            db_is_core = (str(db_row[1]).lower() == 'yes') if db_row else False

            # 檢查是否為資訊通識（資科系可計入0-3學分）
            if is_info_dept and ("資訊通" in remark or db_type == "資訊"):
                info_literacy_courses.append({
                    "courseCode": course.get("courseCode", ""),
                    "courseName": course_name,
                    "credits": credit,
                    "category": "資訊通識",
                })
                info_literacy += credit
                continue  # 資科系修資訊通識，計入資訊通識學分

            # 如果是核心通識，直接根據 DB 裡的 type 累加
            if db_is_core:
                if db_type == "人文":
                    humanities += credit
                    core_domains_taken.add("人文")
                elif db_type == "社會":
                    social_sciences += credit
                    core_domains_taken.add("社會")
                elif db_type == "自然":
                    natural_sciences += credit
                    core_domains_taken.add("自然")
                if db_type in ("人文", "社會", "自然"):
                    core_courses.append({
                        "courseCode": course.get("courseCode", ""),
                        "courseName": course_name,
                        "credits": credit,
                        "category": db_type,
                        "source": "regular",
                    })
                # 如果有其他核心類別可在這裡擴充
                continue # 已處理完核心通識，跳過後面的非核心判斷

            if course_name.startswith("大學英文"):
                english += credit

            elif course_name.startswith("國文") or course_name.startswith("進階國文"):
                chinese += credit

            elif remark == "人文通":
                humanities += credit

            elif remark == "社會通":
                social_sciences += credit

            elif remark == "自然通":
                natural_sciences += credit

            elif remark == "書院通":
                college_general_course += credit

            else:
                course_code = course.get("courseCode", "")
                cursor.execute("SELECT type FROM general_courses WHERE code = ?", (course_code,))
                code_row = cursor.fetchone()

                if code_row:
                    code_type = code_row[0]
                    if code_type == "人文":
                        humanities += credit
                    elif code_type == "社會":
                        social_sciences += credit
                    elif code_type == "自然":
                        natural_sciences += credit
                    elif code_type == "書院":
                        college_general_course += credit

    # 4. 單一領域抵免通識計算
    for course in waived_data:
        credit = float(course.get("credit", 0))
        course_name = course.get("courseName", "")
        course_code = course.get("courseCode", "")
        remark = course.get("remark", "") # 抵免資料若有備註也可利用

        print(f"處理抵免課程: {course_code} {course_name}, 學分: {credit}")

        # 優先查詢資料庫判斷類別與核心通識
        cursor.execute("SELECT type, is_core FROM general_courses WHERE course_name = ?", (course_name,))
        db_row = cursor.fetchone()

        db_type = db_row[0] if db_row else ""
        db_is_core = (str(db_row[1]).lower() == 'yes') if db_row else False

        # --- 邏輯 A：資訊通識 (資科系專用) ---
        if is_info_dept and ("資訊通" in remark or db_type == "資訊"):
            info_literacy_courses.append({
                "courseCode": course_code,
                "courseName": course_name,
                "credits": credit,
                "category": "資訊通識",
                "source": "waived",
            })
            info_literacy += credit
            continue

        # --- 邏輯 B：核心通識 (優先判定) ---
        if db_is_core:
            if db_type == "人文":
                humanities += credit
                core_domains_taken.add("人文")
            elif db_type == "社會":
                social_sciences += credit
                core_domains_taken.add("社會")
            elif db_type == "自然":
                natural_sciences += credit
                core_domains_taken.add("自然")
            if db_type in ("人文", "社會", "自然"):
                core_courses.append({
                    "courseCode": course_code,
                    "courseName": course_name,
                    "credits": credit,
                    "category": db_type,
                    "source": "waived",
                })
            continue

        # --- 邏輯 B：語文通識 ---
        if course_name.startswith("大學英文"):
            english += credit
            continue

        elif course_name.startswith("國文") or course_name.startswith("進階國文"):
            chinese += credit
            continue

        # --- 邏輯 C：根據 Remark 判定 ---
        if remark == "人文通":
            humanities += credit
        elif remark == "社會通":
            social_sciences += credit
        elif remark == "自然通":
            natural_sciences += credit
        elif remark == "書院通":
            college_general_course += credit

        # --- 邏輯 D：根據課號或資料庫 Type 判定 ---
        else:
            # 如果資料庫有資料但不是核心，則參考其 type
            if db_row:
                target_type = db_type
            else:
                # 若資料庫查無此課程名稱，嘗試用課號查詢
                cursor.execute("SELECT type FROM general_courses WHERE code = ?", (course_code,))
                code_row = cursor.fetchone()
                target_type = code_row[0] if code_row else ""

            # 根據最終取得的 type 或課號開頭分配學分
            if target_type == "人文" or course_code.startswith("041"):
                humanities += credit
            elif target_type == "社會" or course_code.startswith("042"):
                social_sciences += credit
            elif target_type == "自然" or course_code.startswith("043"):
                natural_sciences += credit
            elif target_type == "書院" or course_code.startswith("045"):
                college_general_course += credit

    # 跨領域通識計算
    for year_data in course_data:
        for course in year_data["GradeRecords"]:
            credit = float(course.get("credit", 0))
            remark = course.get("remark", "")

            # 關鍵修正點：在這裡定義 score_raw
            score_raw = course.get("score", "")
            course_name = course.get("courseName", "")

            # 修正：碩班資料會有 "成績未到或無成績"，需安全轉換
            try:
                score = float(score_raw)
                if score < 60:
                    continue
            except (ValueError, TypeError):
                # 如果是「成績未到」，在畢業判定中通常不計入
                continue

            # 1. 狀態初始化 (假設門檻都是 8)
            current_credits = {
                "人文": humanities,
                "社會": social_sciences,
                "自然": natural_sciences
            }
            MAX_VAL = 7.0

            if len(remark.split("、")) >= 2:
                # 提取領域，例如 ["人文", "社會", "自然"]
                possible_fields = [r.replace("通", "") for r in remark.split("、")]
                # 過濾掉 current_credits 不認識的領域（資訊、書院、語言等不參與跨領域分配）
                possible_fields = [f for f in possible_fields if f in current_credits]
                if not possible_fields:
                    continue

                # 剩餘可分配的學分
                remaining_credit = credit

                # --- 策略：循環分配直到學分用完或領域全滿 ---
                # 按照「目前最低分」的領域優先填補，直到該領域滿 8 或學分用完
                while remaining_credit > 0:
                    # 找出還沒滿 8 分的相關領域
                    incomplete_fields = [f for f in possible_fields if f in current_credits and current_credits[f] < MAX_VAL]

                    if not incomplete_fields:
                        # 如果通通都滿 8 分了，剩下的學分不再計入這三個領域
                        # 可以選擇跳出，或存入一個「通識超修」變數
                        # excess_credits += remaining_credit
                        break

                    # 挑選目前學分最少的領域來補
                    target_field = min(incomplete_fields, key=lambda f: current_credits[f])

                    # 計算該領域還差多少才滿 8
                    gap = MAX_VAL - current_credits[target_field]

                    # 實際能填入的學分 (取「剩下的學分」與「缺口」的最小值)
                    fill = min(remaining_credit, gap)

                    current_credits[target_field] += fill
                    remaining_credit -= fill

            # --- 更新回原始變數 ---
            humanities = current_credits["人文"]
            social_sciences = current_credits["社會"]
            natural_sciences = current_credits["自然"]

            # --- 跨領域抵免通識計算 ---
    for course in waived_data:
        credit = float(course.get("credit", 0))
        course_name = course.get("courseName", "")
        course_code = course.get("courseCode", "")

        # 1. 從資料庫取得該課號的 type
        cursor.execute("SELECT type FROM general_courses WHERE code = ?", (course_code,))
        db_row = cursor.fetchone()
        db_type = db_row[0] if db_row else ""

        # 2. 判斷是否為跨領域 (字串中包含 "、")
        if "、" in db_type:
            print(f"處理跨領域抵免: {course_code} {course_name}, 類別: {db_type}, 學分: {credit}")

            # 提取領域列表，例如 ["人文", "社會"]
            possible_fields = [f.strip() for f in db_type.split("、")]

            # 當前狀態快照
            current_credits = {
                "人文": humanities,
                "社會": social_sciences,
                "自然": natural_sciences
            }
            MAX_VAL = 7.0
            remaining_credit = credit

            # 3. 循環分配邏輯：優先填補學分最低的領域
            while remaining_credit > 0:
                # 僅考慮此課程涵蓋、且尚未達標 (8學分) 的領域
                incomplete_fields = [f for f in possible_fields if f in current_credits and current_credits[f] < MAX_VAL]

                if not incomplete_fields:
                    # 所有對應領域都已滿 8 學分，剩餘學分跳出（或依需求計入超修）
                    break

                # 找到目前學分最少的目標領域
                target_field = min(incomplete_fields, key=lambda f: current_credits[f])

                # 計算該領域缺口與實際可分配學分
                gap = MAX_VAL - current_credits[target_field]
                fill = min(remaining_credit, gap)

                current_credits[target_field] += fill
                remaining_credit -= fill

            # 4. 將計算結果更新回全域變數
            humanities = current_credits["人文"]
            social_sciences = current_credits["社會"]
            natural_sciences = current_credits["自然"]

    # --- 5. 最終判定邏輯（依據通識規則套用上下限） ---
    # 規則上限：中文 6、英文 6、人/社/自 各 7、書院 3、資訊通識 3、總學分 28
    MAX_CHINESE = 6
    MAX_ENGLISH = 6
    MAX_DOMAIN = 7
    MAX_COLLEGE = 3
    MAX_INFO_LITERACY = 3  # 資訊通識上限
    TOTAL_REQUIRED = 28
    MIN_CHINESE = 3
    MIN_ENGLISH = 6
    MIN_DOMAIN = 3
    CORE_REQUIRED = 2  # 核心通識需至少 2 個不同領域

    # 對每個領域套用上限（超過部分不採計）
    counted_chinese = min(chinese, MAX_CHINESE)
    counted_english = min(english, MAX_ENGLISH)
    counted_humanities = min(humanities, MAX_DOMAIN)
    counted_social = min(social_sciences, MAX_DOMAIN)
    counted_natural = min(natural_sciences, MAX_DOMAIN)
    counted_college = min(college_general_course, MAX_COLLEGE)
    counted_info_literacy = min(info_literacy, MAX_INFO_LITERACY) if is_info_dept else 0
    total_lang = counted_chinese + counted_english

    # 加總後再套用總上限 28
    total_earned_raw = (counted_chinese + counted_english + counted_humanities +
                       counted_social + counted_natural + counted_college + counted_info_literacy)
    total_earned = min(total_earned_raw, TOTAL_REQUIRED)

    # 收集違規／不足項目（供前端顯示）
    violations = []
    if counted_chinese < MIN_CHINESE:
        violations.append(f"中國語文不足（{counted_chinese}/{MIN_CHINESE} 學分）")
    if counted_english < MIN_ENGLISH:
        violations.append(f"外國語文不足（{counted_english}/{MIN_ENGLISH} 學分）")
    if counted_humanities < MIN_DOMAIN:
        violations.append(f"人文領域不足（{counted_humanities}/{MIN_DOMAIN} 學分）")
    if counted_social < MIN_DOMAIN:
        violations.append(f"社會領域不足（{counted_social}/{MIN_DOMAIN} 學分）")
    if counted_natural < MIN_DOMAIN:
        violations.append(f"自然領域不足（{counted_natural}/{MIN_DOMAIN} 學分）")
    if len(core_domains_taken) < CORE_REQUIRED:
        violations.append(
            f"核心通識領域不足（{len(core_domains_taken)}/{CORE_REQUIRED} 個不同領域；"
            f"已修：{'、'.join(core_domains_taken) if core_domains_taken else '無'}）"
        )
    if total_earned_raw < TOTAL_REQUIRED:
        violations.append(f"通識總學分不足（{total_earned_raw}/{TOTAL_REQUIRED} 學分）")

    # 判定是否合格
    passed = (total_earned >= TOTAL_REQUIRED and
              counted_chinese >= MIN_CHINESE and
              counted_english >= MIN_ENGLISH and
              counted_humanities >= MIN_DOMAIN and
              counted_social >= MIN_DOMAIN and
              counted_natural >= MIN_DOMAIN and
              len(core_domains_taken) >= CORE_REQUIRED)

    # --- 6. 收集已修通識課程（僅供前端展示，不影響上方計分） ---
    def _classify(course_name: str, course_code: str, remark: str) -> str:
        """回傳該課程的通識類別標籤；非通識則回傳空字串"""
        if course_name.startswith("大學英文"):
            return "英文"
        if course_name.startswith("國文") or course_name.startswith("進階國文"):
            return "國文"
        # 跨領域 remark（含「、」）
        if "、" in remark and "通" in remark:
            fields = [r.replace("通", "") for r in remark.split("、")]
            return "/".join(fields)
        if remark == "人文通":
            return "人文"
        if remark == "社會通":
            return "社會"
        if remark == "自然通":
            return "自然"
        if remark == "書院通":
            return "書院"
        # 資訊通識
        if remark == "資訊通":
            return "資訊通識"
        # 查資料庫
        cursor.execute("SELECT type FROM general_courses WHERE course_name = ? OR code = ?",
                       (course_name, course_code))
        row = cursor.fetchone()
        if row and row[0]:
            db_type = row[0]
            # 如果資料庫顯示為資訊相關類型，回傳資訊通識
            if db_type == "資訊":
                return "資訊通識"
            return db_type
        # 課號開頭 fallback
        if course_code.startswith("041"): return "人文"
        if course_code.startswith("042"): return "社會"
        if course_code.startswith("043"): return "自然"
        if course_code.startswith("045"): return "書院"
        return ""

    taken_courses = []
    seen = set()
    # 一般成績單
    for year_data in course_data:
        for course in year_data.get("GradeRecords", []):
            score_raw = course.get("score", "")
            try:
                if float(score_raw) < 60:
                    continue
            except (ValueError, TypeError):
                if score_raw != "通過":
                    continue
            name = course.get("courseName", "")
            code = course.get("courseCode", "")
            cat = _classify(name, code, course.get("remark", ""))
            if not cat:
                continue
            key = (code, name)
            if key in seen:
                continue
            seen.add(key)
            taken_courses.append({
                "courseCode": code,
                "courseName": name,
                "credits": course.get("credit", "0.0"),
                "category": cat,
                "source": "regular",
            })
    # 抵免
    for course in waived_data:
        name = course.get("courseName", "")
        code = course.get("courseCode", "")
        cat = _classify(name, code, course.get("remark", ""))
        if not cat:
            continue
        key = (code, name)
        if key in seen:
            continue
        seen.add(key)
        taken_courses.append({
            "courseCode": code,
            "courseName": name,
            "credits": course.get("credit", "0.0"),
            "category": cat,
            "source": "waived",
        })

    conn.close()

    return {
        "credits_earned": total_earned,
        "credits_needed": TOTAL_REQUIRED,
        "passed": passed,
        "by_category": {
            "中文": counted_chinese,
            "英文": counted_english,
            "人文": counted_humanities,
            "社會": counted_social,
            "自然": counted_natural,
            "書院": counted_college,
            "資訊通識": counted_info_literacy,
        },
        "raw_by_category": {
            "人文": humanities,
            "社會": social_sciences,
            "自然": natural_sciences,
            "書院": college_general_course,
            "中文": chinese,
            "英文": english,
            "資訊通識": info_literacy,
        },
        "limits": {
            "中文": [MIN_CHINESE, MAX_CHINESE],
            "英文": [MIN_ENGLISH, MAX_ENGLISH],
            "人文": [MIN_DOMAIN, MAX_DOMAIN],
            "社會": [MIN_DOMAIN, MAX_DOMAIN],
            "自然": [MIN_DOMAIN, MAX_DOMAIN],
            "書院": [0, MAX_COLLEGE],
            "資訊通識": [0, MAX_INFO_LITERACY],
        },
        "core_count": len(core_domains_taken),
        "core_required": CORE_REQUIRED,
        "core_domains_taken": sorted(core_domains_taken),
        "core_courses": core_courses,
        "is_info_dept": is_info_dept,
        "info_literacy_courses": info_literacy_courses,
        "violations": violations,
        "taken_courses": taken_courses,
    }
