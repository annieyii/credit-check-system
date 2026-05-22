"""
輔系分析模組 - Group 1
負責系所：風保系、韓文系、阿語系、金融系、越文系、資訊系、資管系、財管系、財政系財政管理組、財政系稅務組、財政系公共經濟組、西文系

此模組擴展了基礎的 minor.py 分析邏輯，針對特定系所的特殊需求進行客製化處理。
"""

import json
import sqlite3
from typing import Optional, Dict, List, Set

from backend.database import get_db
from backend.minor import _collect_all_passed_courses, _get_minor_row, _is_passing


# ── 系所特殊比對邏輯 ──────────────────────────────────────────────────────────────

# 金融系選課群組特殊處理
# 金融系有多個選修領域，需要特殊處理 min_credits=0 的情況
_FINANCIAL_AREAS = {
    "基礎學科領域",
    "金融市場領域", 
    "金融商品及投資領域",
    "數量方法領域",
    "程式設計領域",
    "其他領域"
}

def _handle_financial_electives(elective_groups: List[Dict], passed_courses: Dict[str, float]) -> List[str]:
    """
    處理金融系選修課程，從各領域中選擇課程直到滿足學分要求
    """
    passed_electives: List[str] = []
    used_courses: Set[str] = set()
    
    # 金融系需要從各個領域中選課，總學分要求由 group_elective_credits 決定
    for group in elective_groups:
        group_name = group.get("group_name", "")
        if group_name not in _FINANCIAL_AREAS:
            continue
            
        courses = group.get("courses", [])
        for course in courses:
            course_name = course.get("course_name", "").strip()
            if course_name in passed_courses and course_name not in used_courses:
                passed_electives.append(course_name)
                used_courses.add(course_name)
    
    return passed_electives


def _handle_general_electives(
    elective_groups: List[Dict],
    passed_courses: Dict[str, float],
    session_data: List = None,
    dept_name: str = ""
) -> List[str]:
    """一般選修群組處理，支援課程代碼篩選"""
    passed_electives: List[str] = []
    used_courses: Set[str] = set()
    
    # 收集所有課程的詳細資訊（包含課程代碼）
    course_details = _collect_course_details(session_data) if session_data else {}
    
    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        if min_credits <= 0:
            continue
            
        courses = group.get("courses", [])
        earned_credits = 0.0
        
        # 先處理指定的選修課程
        for course in courses:
            if earned_credits >= min_credits:
                break
                
            course_name = course.get("course_name", "").strip()
            if course_name in passed_courses and course_name not in used_courses:
                student_credit = passed_courses[course_name]
                earned_credits += student_credit
                passed_electives.append(course_name)
                used_courses.add(course_name)
        
        # 韓文系特殊處理：如果學分不足，尋找507開頭的課程
        if "韓文" in dept_name and earned_credits < min_credits:
            additional_credits = min_credits - earned_credits
            
            # 尋找韓文系開的選修課程（課程代碼507開頭）
            for course_name, details in course_details.items():
                if course_name in passed_courses and course_name not in used_courses:
                    course_code = details.get("course_code", "")
                    if course_code.startswith("507"):
                        student_credit = passed_courses[course_name]
                        if additional_credits > 0:
                            earned_credits += student_credit
                            passed_electives.append(course_name)
                            used_courses.add(course_name)
                            additional_credits -= student_credit
                            if additional_credits <= 0:
                                break
    
    return passed_electives


def _match_minor_group1(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    dept_name: str,
    year: str,
    session_data: List = None
) -> tuple[List[str], List[str], float, Dict]:
    """
    Group 1 系所專用比對邏輯
    
    處理特殊選修群組邏輯（如金融系的領域選修）
    
    Returns:
        (passed_names, missing_names, credits_earned, detailed_report)
    """
    passed_names: List[str] = []
    missing_names: List[str] = []
    credits_earned: float = 0.0
    
    # 詳細報告結構
    detailed_report = {
        "required": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0
        },
        "group_electives": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "group_details": []
        }
    }
    
    # 必修比對 - 需要檢查學分數是否足夠
    required_credits_needed = 0.0
    for course in required_courses:
        name = course["course_name"]
        db_credits = course["credits"]
        alternatives: List[str] = course.get("alternatives", [])
        required_credits_needed += db_credits

        # 檢查課程名稱和學分數
        course_credits_earned = 0.0
        course_fully_completed = False
        
        # 檢查主課程
        if name in passed_courses:
            course_credits_earned = passed_courses[name]
            if course_credits_earned >= db_credits:
                # 學分數足夠
                passed_names.append(name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": name,
                    "credits": db_credits,
                    "earned_credits": course_credits_earned
                })
                detailed_report["required"]["credits_earned"] += db_credits
                course_fully_completed = True
            else:
                # 學分數不足
                deficit = db_credits - course_credits_earned
                detailed_report["required"]["missing"].append({
                    "name": name,
                    "credits": db_credits,
                    "earned_credits": course_credits_earned,
                    "deficit": deficit,
                    "partial": True
                })
        else:
            # 檢查替代課程（包含特殊抵免）
            matched_alt = None
            course_credits_earned = 0.0
            
            # 財政系特殊抵免：稅務會計學 → 稅務會計
            if "財政" in dept_name and name == "稅務會計":
                if "稅務會計學" in passed_courses:
                    matched_alt = "稅務會計學"
                    course_credits_earned = passed_courses["稅務會計學"]
            
            # 越文系特殊抵免：大學外文抵免邏輯（僅限110-111年度）
            elif "越文" in dept_name and year in ["110", "111"]:
                if name == "初級越語":
                    # 計算大學外文(一):越南文 和 大學外文(二):越南文的學分
                    viet_univ_credits = 0.0
                    used_courses = []
                    
                    if "大學外文(一):越南文" in passed_courses:
                        viet_univ_credits += passed_courses["大學外文(一):越南文"]
                        used_courses.append("大學外文(一):越南文")
                    
                    if "大學外文(二):越南文" in passed_courses:
                        viet_univ_credits += passed_courses["大學外文(二):越南文"]
                        used_courses.append("大學外文(二):越南文")
                    
                    if viet_univ_credits > 0:
                        matched_alt = " + ".join(used_courses)
                        course_credits_earned = viet_univ_credits
                
                elif name == "中級越語":
                    # 計算大學外文(三):越南文 和 大學外文(四):越南文的學分
                    viet_univ_credits = 0.0
                    used_courses = []
                    
                    if "大學外文(三):越南文" in passed_courses:
                        viet_univ_credits += passed_courses["大學外文(三):越南文"]
                        used_courses.append("大學外文(三):越南文")
                    
                    if "大學外文(四):越南文" in passed_courses:
                        viet_univ_credits += passed_courses["大學外文(四):越南文"]
                        used_courses.append("大學外文(四):越南文")
                    
                    if viet_univ_credits > 0:
                        matched_alt = " + ".join(used_courses)
                        course_credits_earned = viet_univ_credits
            
            # 金融系特殊抵免：計量經濟學 → 金融計量（僅限110-112年度）
            elif "金融" in dept_name and year in ["110", "111", "112"] and name == "金融計量":
                if "計量經濟學" in passed_courses:
                    matched_alt = "計量經濟學"
                    course_credits_earned = passed_courses["計量經濟學"]
            
            # 檢查一般替代課程
            if not matched_alt:
                for alt in alternatives:
                    if alt in passed_courses:
                        matched_alt = alt
                        course_credits_earned = passed_courses[alt]
                        break
            
            if matched_alt and course_credits_earned >= db_credits:
                # 透過替代課程完成，學分數足夠
                passed_names.append(name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": name,
                    "credits": db_credits,
                    "earned_credits": course_credits_earned,
                    "via_alternative": matched_alt
                })
                detailed_report["required"]["credits_earned"] += db_credits
                course_fully_completed = True
            elif matched_alt:
                # 透過替代課程但學分數不足
                deficit = db_credits - course_credits_earned
                detailed_report["required"]["missing"].append({
                    "name": name,
                    "credits": db_credits,
                    "earned_credits": course_credits_earned,
                    "deficit": deficit,
                    "partial": True,
                    "via_alternative": matched_alt
                })
            else:
                # 完全沒修過
                detailed_report["required"]["missing"].append({
                    "name": name,
                    "credits": db_credits,
                    "earned_credits": 0.0,
                    "deficit": db_credits,
                    "partial": False
                })
        
        # 如果課程未完全完成，加入 missing_names
        if not course_fully_completed:
            missing_names.append(name)
    
    detailed_report["required"]["credits_needed"] = required_credits_needed
    
    # 群修比對
    group_credits_needed = 0.0
    
    # 金融系113-114年度特殊處理：六個領域，每個領域至少一門課，總共14學分
    if "金融" in dept_name and year in ["113", "114"]:
        return _handle_finance_group_electives_113_114(session_data, elective_groups, passed_courses, passed_names, credits_earned, detailed_report)
    
    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        courses = group.get("courses", [])
        
        group_credits_needed += min_credits
        
        group_detail = {
            "group_name": group_name,
            "min_credits": min_credits,
            "passed_courses": [],
            "missing_courses": [],
            "credits_earned": 0.0
        }
        
        # 處理群修課程
        group_earned = 0.0
        used_courses_in_group = set()
        
        # 先處理指定的選修課程
        for course in courses:
            course_name = course.get("course_name", "").strip()
            course_credits = course.get("credits", 0)
            
            # 特殊抵免邏輯
            matched_course = None
            student_credit = 0.0
            
            if course_name in passed_courses and course_name not in used_courses_in_group:
                matched_course = course_name
                student_credit = passed_courses[course_name]
            elif "財政" in dept_name and course_name == "稅務會計":
                if "稅務會計學" in passed_courses and "稅務會計學" not in used_courses_in_group:
                    matched_course = "稅務會計學"
                    student_credit = passed_courses["稅務會計學"]
            elif "金融" in dept_name and year in ["110", "111", "112"] and course_name == "金融計量":
                if "計量經濟學" in passed_courses and "計量經濟學" not in used_courses_in_group:
                    matched_course = "計量經濟學"
                    student_credit = passed_courses["計量經濟學"]
            
            if matched_course:
                passed_names.append(matched_course)
                credits_earned += student_credit
                group_earned += student_credit
                used_courses_in_group.add(matched_course)
                
                group_detail["passed_courses"].append({
                    "name": course_name,
                    "credits": student_credit,
                    "via_alternative": matched_course if matched_course != course_name else None
                })
                detailed_report["group_electives"]["passed"].append({
                    "name": course_name,
                    "credits": student_credit,
                    "group": group_name,
                    "via_alternative": matched_course if matched_course != course_name else None
                })
            else:
                group_detail["missing_courses"].append({
                    "name": course_name,
                    "credits": course_credits
                })
        
        # 韓文系特殊處理：如果學分不足，尋找507開頭的課程
        if "韓文" in dept_name and group_earned < min_credits and session_data:
            additional_credits = min_credits - group_earned
            
            # 收集課程詳細資訊
            course_details = _collect_course_details(session_data)
            
            # 尋找韓文系開的選修課程（課程代碼507開頭）
            for course_name, details in course_details.items():
                if (course_name in passed_courses and 
                    course_name not in used_courses_in_group and
                    course_name not in [c.get("course_name", "").strip() for c in courses]):
                    
                    course_code = details.get("course_code", "")
                    if course_code.startswith("507"):
                        student_credit = passed_courses[course_name]
                        if additional_credits > 0:
                            group_earned += student_credit
                            passed_names.append(course_name)
                            credits_earned += student_credit
                            used_courses_in_group.add(course_name)
                            additional_credits -= student_credit
                            
                            group_detail["passed_courses"].append({
                                "name": course_name,
                                "credits": student_credit,
                                "via_course_code": True
                            })
                            detailed_report["group_electives"]["passed"].append({
                                "name": course_name,
                                "credits": student_credit,
                                "group": group_name,
                                "via_course_code": True
                            })
                            
                            if additional_credits <= 0:
                                break
        
        # 西文系特殊處理：如果學分不足，尋找符合條件的選修課
        if "西文" in dept_name and group_earned < min_credits and session_data:
            additional_credits = min_credits - group_earned
            
            # 收集課程詳細資訊以檢查通識類別
            course_details = _collect_course_details(session_data)
            
            # 尋找符合條件的課程
            eligible_courses = []
            for course_name in passed_courses:
                if (course_name not in used_courses_in_group and
                    course_name not in [c.get("course_name", "").strip() for c in courses]):
                    
                    # 檢查是否為通識課程（排除）
                    course_info = course_details.get(course_name, {})
                    remark = course_info.get("remark", "")
                    if ("通" in remark):
                        continue
                    
                    # 檢查課程名稱是否包含相關關鍵字
                    if ("歐洲" in course_name or "歐盟" in course_name or 
                        "西班牙" in course_name or "西班牙文" in course_name or
                        "西語" in course_name or "拉美" in course_name or
                        "拉丁美洲" in course_name or "墨西哥" in course_name or
                        "阿根廷" in course_name or "智利" in course_name or
                        "秘魯" in course_name or "哥倫比亞" in course_name or
                        "委內瑞拉" in course_name or "古巴" in course_name):
                        
                        eligible_courses.append({
                            "name": course_name,
                            "credits": passed_courses[course_name],
                            "info": course_info
                        })
            
            # 處理2學分課程折抵邏輯
            two_credit_courses = [c for c in eligible_courses if c["credits"] == 2.0]
            other_courses = [c for c in eligible_courses if c["credits"] != 2.0]
            
            # 優先使用非2學分課程
            for course in other_courses:
                if additional_credits <= 0:
                    break
                student_credit = course["credits"]
                if additional_credits >= student_credit:
                    group_earned += student_credit
                    passed_names.append(course["name"])
                    credits_earned += student_credit
                    used_courses_in_group.add(course["name"])
                    additional_credits -= student_credit
                    
                    group_detail["passed_courses"].append({
                        "name": course["name"],
                        "credits": student_credit,
                        "via_keyword": True
                    })
                    detailed_report["group_electives"]["passed"].append({
                        "name": course["name"],
                        "credits": student_credit,
                        "group": group_name,
                        "via_keyword": True
                    })
            
            # 如果還需要學分，使用2學分課程折抵
            if additional_credits > 0 and len(two_credit_courses) >= 2:
                # 使用2科2學分課程折抵1門3學分課程
                for i in range(0, min(len(two_credit_courses) // 2, (additional_credits + 2) // 3)):
                    course1 = two_credit_courses[i * 2]
                    course2 = two_credit_courses[i * 2 + 1]
                    
                    # 2科2學分課程折抵為1門3學分
                    group_earned += 3.0
                    passed_names.append(course1["name"])
                    passed_names.append(course2["name"])
                    credits_earned += 3.0
                    used_courses_in_group.add(course1["name"])
                    used_courses_in_group.add(course2["name"])
                    additional_credits -= 3.0
                    
                    group_detail["passed_courses"].extend([
                        {
                            "name": course1["name"],
                            "credits": 2.0,
                            "via_keyword": True,
                            "combined_with": course2["name"]
                        },
                        {
                            "name": course2["name"],
                            "credits": 2.0,
                            "via_keyword": True,
                            "combined_with": course1["name"]
                        }
                    ])
                    detailed_report["group_electives"]["passed"].extend([
                        {
                            "name": f"{course1['name']} + {course2['name']}",
                            "credits": 3.0,
                            "group": group_name,
                            "via_keyword": True,
                            "combined": True
                        }
                    ])
                    
                    if additional_credits <= 0:
                        break
        
        # 越文系特殊處理：如果學分不足，尋找510開頭且包含"越"字的課程
        if "越文" in dept_name and group_earned < min_credits and session_data:
            additional_credits = min_credits - group_earned
            
            # 收集課程詳細資訊
            course_details = _collect_course_details(session_data)
            
            # 尋找越文系開的選修課程（課程代碼510開頭且課程名稱包含"越"字）
            for course_name, details in course_details.items():
                if (course_name in passed_courses and 
                    course_name not in used_courses_in_group and
                    course_name not in [c.get("course_name", "").strip() for c in courses]):
                    
                    course_code = details.get("course_code", "")
                    if course_code.startswith("510") and "越" in course_name:
                        student_credit = passed_courses[course_name]
                        if additional_credits > 0:
                            group_earned += student_credit
                            passed_names.append(course_name)
                            credits_earned += student_credit
                            used_courses_in_group.add(course_name)
                            additional_credits -= student_credit
                            
                            group_detail["passed_courses"].append({
                                "name": course_name,
                                "credits": student_credit,
                                "via_course_code": True
                            })
                            detailed_report["group_electives"]["passed"].append({
                                "name": course_name,
                                "credits": student_credit,
                                "group": group_name,
                                "via_course_code": True
                            })
                            
                            if additional_credits <= 0:
                                break
        
        group_detail["credits_earned"] = group_earned
        detailed_report["group_electives"]["group_details"].append(group_detail)
        detailed_report["group_electives"]["credits_earned"] += group_earned
    
    detailed_report["group_electives"]["credits_needed"] = group_credits_needed
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 輔系偵測 ────────────────────────────────────────────────────────────────

def _detect_minor_info(session_data: List) -> Optional[tuple]:
    """
    從 session_data 中偵測輔系資訊
    
    Returns:
        tuple: (輔系名稱, 入學年度) 或 None
    """
    about = session_data[0]["課業學習"].get("aboutMe", {})
    
    # 優先使用 registerMinor（註冊輔系）
    register_minor = about.get("registerMinor", "").strip()
    if register_minor:
        # 從 minor1 或學號推斷入學年度
        minor1 = about.get("minor1", "")
        student_number = about.get("studentNumber", "")
        
        if minor1 and "（" in minor1:
            # 從 minor1 提取年度，如 "日文系（113）" → 113
            import re
            match = re.search(r'（(\d+)）', minor1)
            if match:
                return register_minor, match.group(1)
        
        if student_number and len(student_number) >= 3:
            # 從學號前3位推斷入學年度
            return register_minor, student_number[:3]
    
    return None


def _parse_minor_courses(session_data: List, target_minor: str) -> Dict[str, float]:
    """
    專門收集輔系相關課程（更精確的輔系課程辨識）
    
    Args:
        session_data: 全人 JSON 資料
        target_minor: 目標輔系名稱
        
    Returns:
        {課名: 學分} 的字典
    """
    passed: Dict[str, float] = {}
    kl = session_data[0]["課業學習"]
    
    # 輔系課程關鍵字（根據不同輔系類型）
    minor_keywords = {
        "日本語文學系": ["日語", "日本", "日文"],
        "韓國語文學系": ["韓語", "韓國", "韓文"],
        "阿拉伯語文學系": ["阿語", "阿拉伯"],
        "越南語文學系": ["越語", "越南"],
        "西班牙語文學系": ["西語", "西班牙"],
        "金融系": ["金融", "投資", "保險", "銀行", "期貨"],
        "資訊系": ["計算機", "程式", "資料", "演算法", "物件導向"],
        "資管系": ["資訊", "管理", "系統"],
        "財管系": ["財務", "管理", "會計", "稅務"],
        "風險管理與保險學系": ["風險", "保險", "風保"]
    }
    
    keywords = minor_keywords.get(target_minor, [])
    
    # 處理抵免課程
    for c in kl.get("waivedCourseList", []):
        name = c.get("courseName", "").strip()
        credit = float(c.get("credit") or 0)
        if name and credit > 0:
            # 檢查是否為輔系相關課程
            if any(keyword in name for keyword in keywords):
                passed[name] = credit
    
    # 處理成績記錄
    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)
            
            if name and _is_passing(score) and credit > 0:
                # 檢查是否為輔系相關課程
                if any(keyword in name for keyword in keywords):
                    passed[name] = credit
    
    return passed


# ── 公開介面 ──────────────────────────────────────────────────────────────────

def _handle_finance_group_electives_113_114(session_data: List, elective_groups: List[Dict], passed_courses: Dict[str, float], passed_names: List[str], credits_earned: float, detailed_report: Dict) -> tuple:
    """
    處理金融系113-114年度群修課程的特殊邏輯
    
    規則：
    1. 六個領域，每個領域至少修一門課
    2. 總共需要14學分
    3. 必須修科目代碼一樣的課程
    
    Args:
        session_data: 學生資料
        elective_groups: 群修課程群組
        passed_courses: 已修課程
        passed_names: 已修課程名稱列表
        credits_earned: 已獲得學分
        detailed_report: 詳細報告
        
    Returns:
        tuple: (passed_names, missing_names, credits_earned, detailed_report)
    """
    from backend.minor import _is_passing
    
    missing_names = []
    total_credits_needed = 14.0
    total_credits_earned = 0.0
    
    # 收集課程詳細資訊（包含科目代碼）
    course_details = _collect_course_details(session_data)
    
    # 處理每個領域
    area_results = []
    for group in elective_groups:
        group_name = group.get("group_name", "")
        courses = group.get("courses", [])
        
        area_result = {
            "group_name": group_name,
            "min_credits": 0,  # 每個領域至少一門課
            "passed_courses": [],
            "missing_courses": [],
            "credits_earned": 0.0,
            "has_course": False
        }
        
        # 尋找該領域中符合科目代碼的課程
        for course in courses:
            course_name = course.get("course_name", "").strip()
            db_course_code = course.get("course_code", "")
            
            # 檢查學生是否修了這門課（科目代碼必須匹配）
            if course_name in passed_courses:
                student_course_info = course_details.get(course_name, {})
                student_course_code = student_course_info.get("course_code", "")
                
                # 科目代碼匹配邏輯
                if db_course_code and student_course_code:
                    # 如果資料庫有科目代碼，檢查是否匹配
                    db_codes = [code.strip() for code in db_course_code.split(",")]
                    student_codes = [code.strip() for code in student_course_code.split(",")]
                    
                    code_match = any(db_code in student_codes for db_code in db_codes)
                else:
                    # 如果沒有科目代碼，使用課程名稱匹配
                    code_match = True
                
                if code_match and course_name not in [c["name"] for c in area_result["passed_courses"]]:
                    student_credit = passed_courses[course_name]
                    area_result["passed_courses"].append({
                        "name": course_name,
                        "credits": student_credit,
                        "course_code": student_course_code
                    })
                    area_result["credits_earned"] += student_credit
                    area_result["has_course"] = True
                    
                    # 加入總計
                    if course_name not in passed_names:
                        passed_names.append(course_name)
                        total_credits_earned += student_credit
        
        # 如果該領域沒有修課，加入缺失列表
        if not area_result["has_course"]:
            area_result["missing_courses"].append(group_name)
        
        area_results.append(area_result)
    
    # 檢查是否滿足每個領域至少一門課的要求
    areas_with_course = sum(1 for area in area_results if area["has_course"])
    areas_needed = len(area_results)
    
    # 檢查總學分是否足夠
    if total_credits_earned >= total_credits_needed and areas_with_course >= areas_needed:
        # 符合要求
        detailed_report["group_electives"]["credits_needed"] = total_credits_needed
        detailed_report["group_electives"]["credits_earned"] = total_credits_earned
        detailed_report["group_electives"]["group_details"] = area_results
        
        for area in area_results:
            for course in area["passed_courses"]:
                detailed_report["group_electives"]["passed"].append({
                    "name": course["name"],
                    "credits": course["credits"],
                    "group": area["group_name"],
                    "course_code": course["course_code"]
                })
    else:
        # 不符合要求
        detailed_report["group_electives"]["credits_needed"] = total_credits_needed
        detailed_report["group_electives"]["credits_earned"] = total_credits_earned
        detailed_report["group_electives"]["group_details"] = area_results
        
        # 記錄缺失的領域
        for area in area_results:
            if not area["has_course"]:
                detailed_report["group_electives"]["missing"].append({
                    "group": area["group_name"],
                    "reason": "該領域未修課"
                })
        
        # 記錄已修的課程
        for area in area_results:
            for course in area["passed_courses"]:
                detailed_report["group_electives"]["passed"].append({
                    "name": course["name"],
                    "credits": course["credits"],
                    "group": area["group_name"],
                    "course_code": course["course_code"]
                })
    
    return passed_names, missing_names, total_credits_earned, detailed_report


def _collect_course_details(session_data: List) -> Dict[str, Dict]:
    """收集課程詳細資訊（包含課程代碼）"""
    from backend.minor import _is_passing
    
    course_details: Dict[str, Dict] = {}
    kl = session_data[0]["課業學習"]
    
    # 處理抵免課程
    for c in kl.get("waivedCourseList", []):
        name = c.get("courseName", "").strip()
        if name:
            course_details[name] = {
                "course_code": c.get("courseCode", ""),
                "credit": float(c.get("credit") or 0),
                "type": "waived"
            }
    
    # 處理成績記錄
    for yr in kl.get("gradeRecordList", []):
        for c in yr.get("GradeRecords", []):
            name = c.get("courseName", "").strip()
            score = c.get("score", "")
            credit = float(c.get("credit") or 0)
            remark = c.get("remark", "")
            if name and _is_passing(score) and credit > 0:
                course_details[name] = {
                    "course_code": c.get("courseCode", ""),
                    "credit": credit,
                    "type": "grade",
                    "score": score,
                    "remark": remark
                }
    
    return course_details


# ── 公開介面 ──────────────────────────────────────────────────────────────────

def analyze_minor_group1(
    session_data: List,
    dept_name: str,
    year: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict:
    """
    Group 1 系所專用輔系分析函數
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱
        year: 學年度
        conn: 資料庫連線（可選）
    
    Returns:
        {
            "passed": ["通過課程名稱", ...],
            "missing": ["未通過課程名稱", ...], 
            "credits_earned": 已修學分數,
            "credits_needed": 應修學分數
        }
    """
    should_close = conn is None
    if conn is None:
        conn = get_db()

    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            raise ValueError(f"找不到輔系：{dept_name}（{year}）")

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        elective_groups: List[Dict] = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        # 使用 Group 1 專用比對邏輯
        passed, missing, credits_earned, detailed_report = _match_minor_group1(
            required_courses,
            elective_groups,
            passed_courses,
            dept_name,
            year,
            session_data
        )

        return {
            "passed": passed,
            "missing": missing,
            "credits_earned": int(credits_earned) if credits_earned == int(credits_earned) else credits_earned,
            "credits_needed": credits_needed,
            "detailed_report": detailed_report,
        }

    finally:
        if should_close:
            conn.close()


# ── 系所名稱對應表 ──────────────────────────────────────────────────────────────
# 確保系所名稱與資料庫中的名稱一致

GROUP1_DEPT_MAPPING = {
    "風保系": "風險管理與保險學系",
    "韓文系": "韓國語文學系", 
    "阿語系": "阿拉伯語文學系",
    "金融系": "金融系",
    "越文系": "越南語文學系",
    "資訊系": "資訊系",
    "資管系": "資管系",
    "財管系": "財管系",
    "財政系財政管理組": "財政系財政管理組",
    "財政系稅務組": "財政系稅務組", 
    "財政系公共經濟組": "財政系公共經濟組",
    "西文系": "西班牙語文學系"
}


def get_standard_dept_name(dept_name: str) -> str:
    """
    將常見簡稱轉換為資料庫中的標準名稱
    """
    return GROUP1_DEPT_MAPPING.get(dept_name, dept_name)


if __name__ == "__main__":
    # 測試範例
    import json
    import pprint
    
    # 這裡可以加入測試程式碼
    print("Group 1 輔系分析模組已載入")
    print(f"負責系所：{', '.join(GROUP1_DEPT_MAPPING.keys())}")
