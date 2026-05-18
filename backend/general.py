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
    others = 0 # 存放無法分類但屬於通識的學分

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

            # 如果是核心通識，直接根據 DB 裡的 type 累加
            if db_is_core:
                if db_type == "人文":
                    humanities += credit
                elif db_type == "社會":
                    social_sciences += credit
                elif db_type == "自然":
                    natural_sciences += credit
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

        # --- 邏輯 A：核心通識 (優先判定) ---
        if db_is_core:
            if db_type == "人文":
                humanities += credit
            elif db_type == "社會":
                social_sciences += credit
            elif db_type == "自然":
                natural_sciences += credit
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
            MAX_VAL = 8.0

            if len(remark.split("、")) >= 2:
                # 提取領域，例如 ["人文", "社會", "自然"]
                possible_fields = [r.replace("通", "") for r in remark.split("、")]

                # 剩餘可分配的學分
                remaining_credit = credit

                # --- 策略：循環分配直到學分用完或領域全滿 ---
                # 按照「目前最低分」的領域優先填補，直到該領域滿 8 或學分用完
                while remaining_credit > 0:
                    # 找出還沒滿 8 分的相關領域
                    incomplete_fields = [f for f in possible_fields if current_credits[f] < MAX_VAL]

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
            MAX_VAL = 8.0
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

    # --- 5. 新增：最終判定邏輯 ---
    total_lang = english + chinese
    # 總分計算包含所有向度與語言通識
    total_earned = humanities + social_sciences + natural_sciences + college_general_course + others + total_lang

    # 判定是否合格 (總學分達標且各向度皆達標)
    passed = (total_earned >= req_total and
              total_lang >= req_lang and
              humanities >= req_hum and
              social_sciences >= req_soc and
              natural_sciences >= req_nat)

    conn.close()

    return {
        "credits_earned": total_earned,
        "credits_needed": req_total,
        "passed": passed,
        "by_category": {
            "人文": humanities,
            "社會": social_sciences,
            "自然": natural_sciences,
            "書院": college_general_course,
            "國+英": total_lang
        }
    }
