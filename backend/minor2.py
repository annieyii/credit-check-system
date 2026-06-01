"""
輔系分析模組 - Group 2
負責系所：英文系、經濟系、統計系、社會系、泰文系、法文系、法律系、民族系、歷史組、會計系、日文系、電物學程

此模組擴展了基礎的 minor.py 分析邏輯，針對特定系所的特殊需求進行客製化處理。
"""

import json
import sqlite3
from typing import Optional, Dict, List, Set

from backend.database import get_db, normalize_name
from backend.minor import _collect_all_passed_courses, _get_minor_row, _is_passing


# ── 共用工具函數 ──────────────────────────────────────────────────────────────────

def _course_credits(course: dict) -> float:
    """course dict → DB 規定學分；支援 credits 為數字或 {"min":…,"max":…} 格式"""
    credits = course.get("credits", 0)
    if isinstance(credits, dict):
        return float(credits.get("min") or credits.get("max") or 0)
    return float(credits or 0)


def _course_alternatives(course: dict) -> list[str]:
    """course dict → 替代課名清單；支援 alternatives 與 alternative_courses 兩種欄位"""
    return course.get("alternatives") or course.get("alternative_courses") or []


def _match_course(course: dict, passed_courses: dict[str, float]) -> str | None:
    """單一課程 × passed_courses → 實際命中的課名或 None（括號全半形皆可命中）"""
    norm_to_orig = {normalize_name(k): k for k in passed_courses}
    name = course["course_name"]
    if normalize_name(name) in norm_to_orig:
        return norm_to_orig[normalize_name(name)]
    for alt in _course_alternatives(course):
        if normalize_name(alt) in norm_to_orig:
            return norm_to_orig[normalize_name(alt)]
    return None


def _collect_course_details(session_data: List) -> Dict[str, Dict]:
    """收集課程詳細資訊（包含課程代碼）"""
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


# ── 統計系特殊處理 ──────────────────────────────────────────────────────────────

def _check_statistics_calculus_alternatives(course: dict, passed_courses: dict[str, float]) -> Dict:
    """
    檢查統計系微積分甲的可替代課程
    
    資料庫中的替代課程：
    - 微積分（全學年，兩門3學分課程共6學分）
    
    需要檢查學生是否修了兩門微積分課程，總學分至少6學分
    """
    required_course = "微積分甲"
    required_credits = 6
    
    # 檢查是否修了主課程
    if required_course in passed_courses:
        return {
            "completed": True,
            "course_name": required_course,
            "credits": passed_courses[required_course],
            "is_alternative": False,
            "alternative_used": None
        }
    
    # 檢查全學年微積分（需要兩門課程，總學分至少6學分）
    calculus_courses = []
    total_credits = 0.0
    
    # 尋找所有微積分相關課程
    for course_name, credits in passed_courses.items():
        if "微積分" in course_name and course_name != "微積分甲":
            calculus_courses.append(course_name)
            total_credits += credits
    
    # 檢查是否滿足學分要求
    if total_credits >= required_credits:
        # 選擇學分最高的課程組合
        selected_courses = sorted(calculus_courses, 
                                key=lambda x: passed_courses[x], 
                                reverse=True)[:2]
        
        return {
            "completed": True,
            "course_name": required_course,
            "credits": min(total_credits, required_credits),  # 最多只算6學分
            "is_alternative": True,
            "alternative_used": " + ".join(selected_courses),
            "alternative_courses": selected_courses,
            "total_alternative_credits": total_credits
        }
    
    return {
        "completed": False,
        "course_name": required_course,
        "credits": 0,
        "is_alternative": False,
        "alternative_used": None,
        "calculus_courses_found": calculus_courses,
        "total_credits_found": total_credits
    }


def _analyze_statistics_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int
) -> tuple[List[str], List[str], float, Dict]:
    """
    統計系輔系專用分析
    
    特殊處理：
    1. 微積分甲可用全學年微積分替代
    2. 無選修課程要求（全部為必修）
    3. 總學分27學分
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
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "group_details": []
        }
    }
    
    # 必修課程比對
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        
        if course_name == "微積分甲":
            # 特殊處理微積分甲
            result = _check_statistics_calculus_alternatives(course, passed_courses)
            
            if result["completed"]:
                passed_names.append(course_name)
                credits_earned += db_credits
                
                # 設定通過課程的詳細資訊
                passed_info = {
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": result["credits"],
                    "via_alternative": result["alternative_used"]
                }
                
                # 如果使用了替代課程，添加額外資訊
                if result["is_alternative"]:
                    passed_info.update({
                        "alternative_courses": result.get("alternative_courses", []),
                        "total_alternative_credits": result.get("total_alternative_credits", 0)
                    })
                    
                    detailed_report["required"]["alternatives_used"].append({
                        "required": course_name,
                        "completed": result["alternative_used"],
                        "credits": result["credits"],
                        "alternative_courses": result.get("alternative_courses", []),
                        "total_alternative_credits": result.get("total_alternative_credits", 0)
                    })
                
                detailed_report["required"]["passed"].append(passed_info)
                detailed_report["required"]["credits_earned"] += db_credits
            else:
                missing_names.append(course_name)
                missing_info = {
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": 0
                }
                
                # 如果找到部分微積分課程但學分不足，添加診斷資訊
                if "calculus_courses_found" in result:
                    missing_info.update({
                        "calculus_courses_found": result["calculus_courses_found"],
                        "total_credits_found": result["total_credits_found"],
                        "credits_needed": 6,
                        "credits_short": 6 - result["total_credits_found"]
                    })
                
                detailed_report["required"]["missing"].append(missing_info)
        else:
            # 一般必修課程處理
            matched_name = _match_course(course, passed_courses)
            
            if matched_name:
                passed_names.append(course_name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": passed_courses[matched_name],
                    "via_alternative": matched_name if matched_name != course_name else None
                })
                detailed_report["required"]["credits_earned"] += db_credits
            else:
                missing_names.append(course_name)
                detailed_report["required"]["missing"].append({
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": 0
                })
    
    detailed_report["required"]["credits_needed"] = credits_needed
    
    # 統計系無選修課程要求
    detailed_report["group_electives"]["credits_needed"] = 0
    detailed_report["group_electives"]["credits_earned"] = 0
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 社會系特殊處理 ──────────────────────────────────────────────────────────────

def _handle_sociology_group_electives(
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    year: str
) -> tuple[List[str], float, Dict]:
    """
    處理社會系113-114年度的群修和選修課程
    
    特殊處理：
    1. 群修課程：至少8學分，從指定課程中選修
    2. 選修課程：至少12學分，從指定課程中選修
    3. 課程不能重複計算
    
    Args:
        elective_groups: 選修群組列表
        passed_courses: 已修課程
        year: 學年度
        
    Returns:
        (passed_courses_list, total_credits, detailed_report)
    """
    passed_names: List[str] = []
    total_credits: float = 0.0
    used_courses: Set[str] = set()
    
    # 詳細報告結構
    detailed_report = {
        "group_electives": {
            "群修": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "選修": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            }
        }
    }
    
    # 處理群修和選修群組
    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        courses = group.get("courses", [])
        
        if group_name not in ["群修", "選修"]:
            continue
            
        group_report = detailed_report["group_electives"][group_name]
        group_report["min_credits"] = min_credits
        
        group_earned = 0.0
        
        for course in courses:
            course_name = course.get("course_name", "").strip()
            course_credits = course.get("credits", 0)
            
            if course_name in passed_courses and course_name not in used_courses:
                student_credit = passed_courses[course_name]
                group_earned += student_credit
                total_credits += student_credit
                passed_names.append(course_name)
                used_courses.add(course_name)
                
                group_report["passed_courses"].append({
                    "name": course_name,
                    "credits": student_credit
                })
            else:
                group_report["missing_courses"].append({
                    "name": course_name,
                    "credits": course_credits
                })
        
        group_report["credits_earned"] = group_earned
    
    return passed_names, total_credits, detailed_report


def _analyze_sociology_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int,
    year: str
) -> tuple[List[str], List[str], float, Dict]:
    """
    社會系輔系專用分析
    
    特殊處理：
    1. 110-112年度：純選修20學分
    2. 113-114年度：必修3學分 + 群修8學分 + 選修12學分
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
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "group_details": []
        }
    }
    
    # 必修課程比對
    required_credits_needed = 0.0
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        required_credits_needed += db_credits
        
        matched_name = _match_course(course, passed_courses)
        
        if matched_name:
            passed_names.append(course_name)
            credits_earned += db_credits
            detailed_report["required"]["passed"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": passed_courses[matched_name],
                "via_alternative": matched_name if matched_name != course_name else None
            })
            detailed_report["required"]["credits_earned"] += db_credits
        else:
            missing_names.append(course_name)
            detailed_report["required"]["missing"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": 0
            })
    
    detailed_report["required"]["credits_needed"] = required_credits_needed
    
    # 處理選修課程
    if year in ["110", "111", "112"]:
        # 110-112年度：單一選修群組20學分
        elective_credits_needed = 20
        elective_earned = 0.0
        used_courses: Set[str] = set()
        
        for group in elective_groups:
            group_name = group.get("group_name", "")
            courses = group.get("courses", [])
            
            for course in courses:
                course_name = course.get("course_name", "").strip()
                
                if course_name in passed_courses and course_name not in used_courses:
                    student_credit = passed_courses[course_name]
                    elective_earned += student_credit
                    passed_names.append(course_name)
                    credits_earned += student_credit
                    used_courses.add(course_name)
        
        detailed_report["group_electives"]["credits_needed"] = elective_credits_needed
        detailed_report["group_electives"]["credits_earned"] = elective_earned
        
    elif year in ["113", "114"]:
        # 113-114年度：群修8學分 + 選修12學分
        elective_passed, elective_credits, elective_report = _handle_sociology_group_electives(
            elective_groups, passed_courses, year
        )
        
        passed_names.extend(elective_passed)
        credits_earned += elective_credits
        
        detailed_report["group_electives"] = elective_report["group_electives"]
        detailed_report["group_electives"]["credits_needed"] = 20  # 群修8+選修12
        detailed_report["group_electives"]["credits_earned"] = elective_credits
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 法文系特殊處理 ──────────────────────────────────────────────────────────────

def _analyze_french_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int
) -> tuple[List[str], List[str], float, Dict]:
    """
    法文系輔系專用分析
    
    規則：
    - 必修 16 學分
    - 全校選修 3 學分：與歐洲、歐盟相關課程
    - 若選修課僅 2 學分，可用 2 科共 4 學分折抵
    - 總學分 19 學分
    """
    passed_names: List[str] = []
    missing_names: List[str] = []
    credits_earned: float = 0.0
    counted_courses: Set[str] = set()
    
    # 詳細報告結構
    detailed_report = {
        "required": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 3.0,
            "europe_courses_found": [],
            "elective_strategy": None
        }
    }
    
    # 必修課程比對
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        
        matched_name = _match_course(course, passed_courses)
        
        if matched_name:
            counted_courses.add(course_name)
            passed_names.append(course_name)
            credits_earned += db_credits
            detailed_report["required"]["passed"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": passed_courses[matched_name],
                "via_alternative": matched_name if matched_name != course_name else None
            })
            detailed_report["required"]["credits_earned"] += db_credits
        else:
            missing_names.append(course_name)
            detailed_report["required"]["missing"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": 0
            })
    
    detailed_report["required"]["credits_needed"] = sum(_course_credits(c) for c in required_courses)
    
    # 處理歐洲相關選修課程
    french_keywords = ["歐洲", "歐盟"]
    
    elective_candidates: List[tuple[str, float]] = []
    
    for cname, credit in passed_courses.items():
        if cname in counted_courses:
            continue
        if any(keyword in cname for keyword in french_keywords):
            elective_candidates.append((cname, float(credit or 0)))
            detailed_report["group_electives"]["europe_courses_found"].append({
                "name": cname,
                "credits": float(credit or 0)
            })
    
    # 按學分排序，優先選擇學分高的課程
    elective_candidates.sort(key=lambda item: item[1], reverse=True)
    
    elective_credits = 0.0
    elective_count = 0
    used_elective_courses: List[str] = []
    
    for cname, credit in elective_candidates:
        if elective_credits >= 3:
            break
        counted_courses.add(cname)
        passed_names.append(cname)
        credits_earned += credit
        elective_credits += credit
        elective_count += 1
        used_elective_courses.append(cname)
        
        detailed_report["group_electives"]["passed"].append({
            "name": cname,
            "credits": credit
        })
    
    # 判斷選修是否通過
    elective_passed = elective_credits >= 3 or (elective_count >= 2 and elective_credits >= 4)
    
    if elective_passed:
        if elective_credits >= 3:
            detailed_report["group_electives"]["elective_strategy"] = "single_course"
        else:
            detailed_report["group_electives"]["elective_strategy"] = "two_courses_combined"
    else:
        missing_names.append("歐洲／歐盟相關選修不足")
        detailed_report["group_electives"]["missing"].append({
            "reason": "歐洲／歐盟相關選修不足",
            "credits_needed": 3,
            "credits_earned": elective_credits,
            "courses_found": len(elective_candidates)
        })
    
    detailed_report["group_electives"]["credits_earned"] = elective_credits
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 民族系特殊處理 ──────────────────────────────────────────────────────────────

def _analyze_ethnic_studies_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int,
    year: str
) -> tuple[List[str], List[str], float, Dict]:
    """
    民族系輔系專用分析
    
    特殊處理：
    1. 110年度：純選修30學分（核心課程+語言課程+社會文化課程）
    2. 111-114年度：必修6學分 + 選修24學分（核心課程+語言課程+社會文化課程）
    3. 語言課程和社會文化課程有分別的學分要求
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
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "核心課程": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "語言課程": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "社會文化課程": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "credits_needed": 0.0,
            "credits_earned": 0.0
        }
    }
    
    # 必修課程比對
    required_credits_needed = 0.0
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        required_credits_needed += db_credits
        
        matched_name = _match_course(course, passed_courses)
        
        if matched_name:
            passed_names.append(course_name)
            credits_earned += db_credits
            detailed_report["required"]["passed"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": passed_courses[matched_name],
                "via_alternative": matched_name if matched_name != course_name else None
            })
            detailed_report["required"]["credits_earned"] += db_credits
        else:
            missing_names.append(course_name)
            detailed_report["required"]["missing"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": 0
            })
    
    detailed_report["required"]["credits_needed"] = required_credits_needed
    
    # 處理選修課程
    used_courses: Set[str] = set()
    
    # 處理各個選修群組
    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        courses = group.get("courses", [])
        
        # 標準化群組名稱
        if "核心" in group_name:
            group_key = "核心課程"
        elif "語言" in group_name:
            group_key = "語言課程"
        elif "社會文化" in group_name:
            group_key = "社會文化課程"
        else:
            continue
        
        group_report = detailed_report["group_electives"][group_key]
        group_report["min_credits"] = min_credits
        
        group_earned = 0.0
        
        for course in courses:
            course_name = course.get("course_name", "").strip()
            
            if course_name in passed_courses and course_name not in used_courses:
                student_credit = passed_courses[course_name]
                group_earned += student_credit
                passed_names.append(course_name)
                credits_earned += student_credit
                used_courses.add(course_name)
                
                group_report["passed_courses"].append({
                    "name": course_name,
                    "credits": student_credit
                })
            else:
                course_credits = course.get("credits", 0)
                group_report["missing_courses"].append({
                    "name": course_name,
                    "credits": course_credits
                })
        
        group_report["credits_earned"] = group_earned
        detailed_report["group_electives"]["credits_earned"] += group_earned
    
    # 計算總選修學分需求
    if year == "110":
        # 110年度：總選修30學分
        total_elective_needed = 30
    else:
        # 111-114年度：選修24學分
        total_elective_needed = 24
    
    detailed_report["group_electives"]["credits_needed"] = total_elective_needed
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 歷史系特殊處理 ──────────────────────────────────────────────────────────────

def _analyze_history_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int
) -> tuple[List[str], List[str], float, Dict]:
    """
    歷史系輔系專用分析
    
    特殊處理：
    1. 純選修制30學分
    2. 基礎課程（群修）：至少15學分，從6門指定課程選修
    3. 進階課程：至少9學分，從專史類和專題類課程選修
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
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "基礎課程": {
                "min_credits": 15,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "進階課程": {
                "min_credits": 9,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": [],
                "course_types": {
                    "專史類": {"credits": 0, "courses": []},
                    "專題類": {"credits": 0, "courses": []}
                }
            },
            "credits_needed": 30.0,
            "credits_earned": 0.0
        }
    }
    
    # 處理選修課程
    used_courses: Set[str] = set()
    
    # 處理各個選修群組
    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        courses = group.get("courses", [])
        
        # 標準化群組名稱
        if "基礎" in group_name:
            group_key = "基礎課程"
        elif "進階" in group_name:
            group_key = "進階課程"
        else:
            continue
        
        group_report = detailed_report["group_electives"][group_key]
        group_report["min_credits"] = min_credits
        
        group_earned = 0.0
        
        for course in courses:
            course_name = course.get("course_name", "").strip()
            
            if course_name in passed_courses and course_name not in used_courses:
                student_credit = passed_courses[course_name]
                group_earned += student_credit
                passed_names.append(course_name)
                credits_earned += student_credit
                used_courses.add(course_name)
                
                passed_course_info = {
                    "name": course_name,
                    "credits": student_credit
                }
                
                # 進階課程需要分類處理
                if group_key == "進階課程":
                    if "專史" in course_name:
                        group_report["course_types"]["專史類"]["credits"] += student_credit
                        group_report["course_types"]["專史類"]["courses"].append(passed_course_info)
                    elif "專題" in course_name:
                        group_report["course_types"]["專題類"]["credits"] += student_credit
                        group_report["course_types"]["專題類"]["courses"].append(passed_course_info)
                
                group_report["passed_courses"].append(passed_course_info)
            else:
                course_credits = course.get("credits", 0)
                missing_course_info = {
                    "name": course_name,
                    "credits": course_credits
                }
                group_report["missing_courses"].append(missing_course_info)
        
        group_report["credits_earned"] = group_earned
        detailed_report["group_electives"]["credits_earned"] += group_earned
    
    detailed_report["group_electives"]["credits_needed"] = credits_needed
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 會計系特殊處理 ──────────────────────────────────────────────────────────────

def _analyze_accounting_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int,
    year: str
) -> tuple[List[str], List[str], float, Dict]:
    """
    會計系輔系專用分析
    
    特殊處理：
    1. 110年度：必修15學分 + 群修9學分 + 選修12學分
    2. 111-112年度：必修15學分 + 群修9學分（無分開選修群組）
    3. 113-114年度：必修21學分 + 群修3學分
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
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "群修課程": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "選修課程": {
                "min_credits": 0,
                "credits_earned": 0.0,
                "passed_courses": [],
                "missing_courses": []
            },
            "credits_needed": 0.0,
            "credits_earned": 0.0
        }
    }
    
    # 必修課程比對
    required_credits_needed = 0.0
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        required_credits_needed += db_credits
        
        matched_name = _match_course(course, passed_courses)
        
        if matched_name:
            passed_names.append(course_name)
            credits_earned += db_credits
            detailed_report["required"]["passed"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": passed_courses[matched_name],
                "via_alternative": matched_name if matched_name != course_name else None
            })
            detailed_report["required"]["credits_earned"] += db_credits
        else:
            missing_names.append(course_name)
            detailed_report["required"]["missing"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": 0
            })
    
    detailed_report["required"]["credits_needed"] = required_credits_needed
    
    # 處理選修課程
    used_courses: Set[str] = set()
    
    # 處理各個選修群組
    for group in elective_groups:
        group_name = group.get("group_name", "")
        min_credits = group.get("min_credits", 0)
        courses = group.get("courses", [])
        
        # 標準化群組名稱
        if "群修" in group_name:
            group_key = "群修課程"
        elif "選修" in group_name:
            group_key = "選修課程"
        else:
            continue
        
        group_report = detailed_report["group_electives"][group_key]
        group_report["min_credits"] = min_credits
        
        group_earned = 0.0
        
        for course in courses:
            course_name = course.get("course_name", "").strip()
            
            if course_name in passed_courses and course_name not in used_courses:
                student_credit = passed_courses[course_name]
                group_earned += student_credit
                passed_names.append(course_name)
                credits_earned += student_credit
                used_courses.add(course_name)
                
                group_report["passed_courses"].append({
                    "name": course_name,
                    "credits": student_credit
                })
            else:
                course_credits = course.get("credits", 0)
                group_report["missing_courses"].append({
                    "name": course_name,
                    "credits": course_credits
                })
        
        group_report["credits_earned"] = group_earned
        detailed_report["group_electives"]["credits_earned"] += group_earned
    
    # 計算總選修學分需求
    if year == "110":
        # 110年度：群修9學分 + 選修12學分 = 21學分
        total_elective_needed = 21
    elif year in ["111", "112"]:
        # 111-112年度：只有群修課程9學分
        total_elective_needed = 9
    else:
        # 113-114年度：群修課程3學分
        total_elective_needed = 3
    
    detailed_report["group_electives"]["credits_needed"] = total_elective_needed
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 英文系特殊處理 ──────────────────────────────────────────────────────────────

def _check_english_linguistics_alternatives(course: dict, passed_courses: dict[str, float]) -> Dict:
    """
    檢查英語語言學概論的可替代課程
    
    資料庫中的替代課程：
    - 文學作品讀法
    - 西洋文學概論
    - 英國文學
    - 美國文學
    - 語言學習導論
    - 英語語言發展史
    - 語言與認知
    - 翻譯
    """
    required_course = "英語語言學概論"
    alternatives = [
        "文學作品讀法", 
        "西洋文學概論", 
        "英國文學", 
        "美國文學", 
        "語言學習導論", 
        "英語語言發展史", 
        "語言與認知", 
        "翻譯"
    ]
    
    # 檢查是否修了主課程
    if required_course in passed_courses:
        return {
            "completed": True,
            "course_name": required_course,
            "credits": passed_courses[required_course],
            "is_alternative": False,
            "alternative_used": None
        }
    
    # 檢查替代課程
    for alt in alternatives:
        if alt in passed_courses:
            return {
                "completed": True,
                "course_name": required_course,
                "credits": passed_courses[alt],
                "is_alternative": True,
                "alternative_used": alt
            }
    
    return {
        "completed": False,
        "course_name": required_course,
        "credits": 0,
        "is_alternative": False,
        "alternative_used": None
    }


def _analyze_english_minor(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    credits_needed: int
) -> tuple[List[str], List[str], float, Dict]:
    """
    英文系輔系專用分析
    
    特殊處理：
    1. 英語語言學概論有8門可替代課程
    2. 無選修課程要求（全部為必修）
    3. 總學分29學分
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
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "group_details": []
        }
    }
    
    # 必修課程比對
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        
        if course_name == "英語語言學概論":
            # 特殊處理英語語言學概論
            result = _check_english_linguistics_alternatives(course, passed_courses)
            
            if result["completed"]:
                passed_names.append(course_name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": result["credits"],
                    "via_alternative": result["alternative_used"]
                })
                detailed_report["required"]["credits_earned"] += db_credits
                
                if result["is_alternative"]:
                    detailed_report["required"]["alternatives_used"].append({
                        "required": course_name,
                        "completed": result["alternative_used"],
                        "credits": result["credits"]
                    })
            else:
                missing_names.append(course_name)
                detailed_report["required"]["missing"].append({
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": 0
                })
        else:
            # 一般必修課程處理
            matched_name = _match_course(course, passed_courses)
            
            if matched_name:
                passed_names.append(course_name)
                credits_earned += db_credits
                detailed_report["required"]["passed"].append({
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": passed_courses[matched_name],
                    "via_alternative": matched_name if matched_name != course_name else None
                })
                detailed_report["required"]["credits_earned"] += db_credits
            else:
                missing_names.append(course_name)
                detailed_report["required"]["missing"].append({
                    "name": course_name,
                    "credits": db_credits,
                    "earned_credits": 0
                })
    
    detailed_report["required"]["credits_needed"] = credits_needed
    
    # 英文系無選修課程要求
    detailed_report["group_electives"]["credits_needed"] = 0
    detailed_report["group_electives"]["credits_earned"] = 0
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── Group 2 通用分析邏輯 ───────────────────────────────────────────────────────────

def _match_minor_group2(
    required_courses: List[Dict],
    elective_groups: List[Dict], 
    passed_courses: Dict[str, float],
    dept_name: str,
    year: str,
    credits_needed: int,
    session_data: List = None
) -> tuple[List[str], List[str], float, Dict]:
    """
    Group 2 系所專用比對邏輯
    
    處理特殊需求：
    - 英文系：英語語言學概論可替代課程
    - 統計系：微積分甲可用全學年微積分替代
    - 社會系：113-114年度群修+選修特殊結構
    - 法文系：歐洲/歐盟相關選修課程特殊處理
    - 民族系：語言課程+社會文化課程分群處理
    - 歷史系：基礎課程+進階課程分群處理
    - 會計系：年度差異的群修+選修結構
    - 其他系所：一般輔系邏輯
    
    Returns:
        (passed_names, missing_names, credits_earned, detailed_report)
    """
    
    # 英文系使用特殊邏輯
    if "英文" in dept_name:
        return _analyze_english_minor(required_courses, elective_groups, passed_courses, credits_needed)
    
    # 統計系使用特殊邏輯
    if "統計" in dept_name:
        return _analyze_statistics_minor(required_courses, elective_groups, passed_courses, credits_needed)
    
    # 社會系使用特殊邏輯
    if "社會" in dept_name:
        return _analyze_sociology_minor(required_courses, elective_groups, passed_courses, credits_needed, year)
    
    # 法文系使用特殊邏輯
    if "法文" in dept_name:
        return _analyze_french_minor(required_courses, elective_groups, passed_courses, credits_needed)
    
    # 民族系使用特殊邏輯
    if "民族" in dept_name:
        return _analyze_ethnic_studies_minor(required_courses, elective_groups, passed_courses, credits_needed, year)
    
    # 歷史系使用特殊邏輯
    if "歷史" in dept_name:
        return _analyze_history_minor(required_courses, elective_groups, passed_courses, credits_needed)
    
    # 會計系使用特殊邏輯
    if "會計" in dept_name:
        return _analyze_accounting_minor(required_courses, elective_groups, passed_courses, credits_needed, year)
    
    # 其他系所使用一般邏輯
    passed_names: List[str] = []
    missing_names: List[str] = []
    credits_earned: float = 0.0
    
    # 詳細報告結構
    detailed_report = {
        "required": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "alternatives_used": []
        },
        "group_electives": {
            "passed": [],
            "missing": [],
            "credits_earned": 0.0,
            "credits_needed": 0.0,
            "group_details": []
        }
    }
    
    # 必修課程比對
    for course in required_courses:
        course_name = course["course_name"]
        db_credits = _course_credits(course)
        
        matched_name = _match_course(course, passed_courses)
        
        if matched_name:
            passed_names.append(course_name)
            credits_earned += db_credits
            detailed_report["required"]["passed"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": passed_courses[matched_name],
                "via_alternative": matched_name if matched_name != course_name else None
            })
            detailed_report["required"]["credits_earned"] += db_credits
            
            if matched_name != course_name:
                detailed_report["required"]["alternatives_used"].append({
                    "required": course_name,
                    "completed": matched_name,
                    "credits": passed_courses[matched_name]
                })
        else:
            missing_names.append(course_name)
            detailed_report["required"]["missing"].append({
                "name": course_name,
                "credits": db_credits,
                "earned_credits": 0
            })
    
    detailed_report["required"]["credits_needed"] = sum(_course_credits(c) for c in required_courses)
    
    # 選修群組處理
    group_credits_needed = 0.0
    used_courses: Set[str] = set()
    
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
        
        group_earned = 0.0
        
        for course in courses:
            course_name = course.get("course_name", "").strip()
            
            if course_name in passed_courses and course_name not in used_courses:
                student_credit = passed_courses[course_name]
                group_earned += student_credit
                passed_names.append(course_name)
                credits_earned += student_credit
                used_courses.add(course_name)
                
                group_detail["passed_courses"].append({
                    "name": course_name,
                    "credits": student_credit
                })
        
        group_detail["credits_earned"] = group_earned
        detailed_report["group_electives"]["group_details"].append(group_detail)
        detailed_report["group_electives"]["credits_earned"] += group_earned
    
    detailed_report["group_electives"]["credits_needed"] = group_credits_needed
    
    return passed_names, missing_names, credits_earned, detailed_report


# ── 公開介面 ──────────────────────────────────────────────────────────────────

def analyze_minor_group2(
    session_data: List,
    dept_name: str,
    year: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict:
    """
    Group 2 系所專用輔系分析函數
    
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
            "credits_needed": 應修學分數,
            "detailed_report": 詳細報告
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

        # 使用 Group 2 專用比對邏輯
        passed, missing, credits_earned, detailed_report = _match_minor_group2(
            required_courses,
            elective_groups,
            passed_courses,
            dept_name,
            year,
            credits_needed,
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

GROUP2_DEPT_MAPPING = {
    "英文系": "英文系",
    "經濟系": "經濟系",
    "統計系": "統計系",
    "社會系": "社會系",
    "泰文系": "泰文系",
    "法文系": "法文系",
    "法律系": "法律系",
    "民族系": "民族系",
    "歷史組": "歷史組",
    "會計系": "會計系",
    "日文系": "日文系",
    "電物學程": "電物學程"
}


def get_standard_dept_name(dept_name: str) -> str:
    """
    將常見簡稱轉換為資料庫中的標準名稱
    """
    return GROUP2_DEPT_MAPPING.get(dept_name, dept_name)


def check_english_minor_alternatives(session_data: List, dept_name: str = "英文系", year: str = "113") -> Dict:
    """
    專門檢查英文系輔系的可替代課程狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"英文系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 英語語言學概論替代檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        
        # 尋找英語語言學概論課程
        linguistics_course = None
        for course in required_courses:
            if course["course_name"] == "英語語言學概論":
                linguistics_course = course
                break
        
        if not linguistics_course:
            return {'error': '找不到英語語言學概論課程設定'}
        
        # 檢查替代情況
        result = _check_english_linguistics_alternatives(linguistics_course, passed_courses)
        
        return {
            'required_course': '英語語言學概論',
            'alternatives': _course_alternatives(linguistics_course),
            'student_completed': result["alternative_used"] if result["is_alternative"] else ("英語語言學概論" if result["completed"] else None),
            'is_alternative': result["is_alternative"],
            'requirement_met': result["completed"],
            'credits_earned': result["credits"]
        }

    finally:
        if should_close:
            conn.close()


def check_accounting_minor_alternatives(session_data: List, dept_name: str = "會計系", year: str = "113") -> Dict:
    """
    專門檢查會計系輔系的修課狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"會計系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 會計系輔系修課檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        elective_groups: List[Dict] = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        # 使用會計系專用分析邏輯
        passed, missing, credits_earned, detailed_report = _analyze_accounting_minor(
            required_courses, elective_groups, passed_courses, credits_needed, year
        )

        return {
            'dept_name': dept_name,
            'year': year,
            'total_credits_needed': credits_needed,
            'credits_earned': credits_earned,
            'passed_courses': passed,
            'missing_courses': missing,
            'requirement_met': len(missing) == 0 and credits_earned >= credits_needed,
            'detailed_report': detailed_report
        }

    finally:
        if should_close:
            conn.close()


def check_history_minor_alternatives(session_data: List, dept_name: str = "歷史系", year: str = "113") -> Dict:
    """
    專門檢查歷史系輔系的修課狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"歷史系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 歷史系輔系修課檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        elective_groups: List[Dict] = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        # 使用歷史系專用分析邏輯
        passed, missing, credits_earned, detailed_report = _analyze_history_minor(
            required_courses, elective_groups, passed_courses, credits_needed
        )

        return {
            'dept_name': dept_name,
            'year': year,
            'total_credits_needed': credits_needed,
            'credits_earned': credits_earned,
            'passed_courses': passed,
            'missing_courses': missing,
            'requirement_met': len(missing) == 0 and credits_earned >= credits_needed,
            'detailed_report': detailed_report
        }

    finally:
        if should_close:
            conn.close()


def check_ethnic_studies_minor_alternatives(session_data: List, dept_name: str = "民族系", year: str = "113") -> Dict:
    """
    專門檢查民族系輔系的修課狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"民族系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 民族系輔系修課檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        elective_groups: List[Dict] = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        # 使用民族系專用分析邏輯
        passed, missing, credits_earned, detailed_report = _analyze_ethnic_studies_minor(
            required_courses, elective_groups, passed_courses, credits_needed, year
        )

        return {
            'dept_name': dept_name,
            'year': year,
            'total_credits_needed': credits_needed,
            'credits_earned': credits_earned,
            'passed_courses': passed,
            'missing_courses': missing,
            'requirement_met': len(missing) == 0 and credits_earned >= credits_needed,
            'detailed_report': detailed_report
        }

    finally:
        if should_close:
            conn.close()


def check_french_minor_alternatives(session_data: List, dept_name: str = "法文系", year: str = "113") -> Dict:
    """
    專門檢查法文系輔系的修課狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"法文系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 法文系輔系修課檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        elective_groups: List[Dict] = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        # 使用法文系專用分析邏輯
        passed, missing, credits_earned, detailed_report = _analyze_french_minor(
            required_courses, elective_groups, passed_courses, credits_needed
        )

        return {
            'dept_name': dept_name,
            'year': year,
            'total_credits_needed': credits_needed,
            'credits_earned': credits_earned,
            'passed_courses': passed,
            'missing_courses': missing,
            'requirement_met': len(missing) == 0 and credits_earned >= credits_needed,
            'detailed_report': detailed_report
        }

    finally:
        if should_close:
            conn.close()


def check_sociology_minor_alternatives(session_data: List, dept_name: str = "社會系", year: str = "113") -> Dict:
    """
    專門檢查社會系輔系的修課狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"社會系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 社會系輔系修課檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        elective_groups: List[Dict] = json.loads(row["elective_groups"])
        credits_needed: int = row["total_credits_required"]

        # 使用社會系專用分析邏輯
        passed, missing, credits_earned, detailed_report = _analyze_sociology_minor(
            required_courses, elective_groups, passed_courses, credits_needed, year
        )

        return {
            'dept_name': dept_name,
            'year': year,
            'total_credits_needed': credits_needed,
            'credits_earned': credits_earned,
            'passed_courses': passed,
            'missing_courses': missing,
            'requirement_met': len(missing) == 0 and credits_earned >= credits_needed,
            'detailed_report': detailed_report
        }

    finally:
        if should_close:
            conn.close()


def check_statistics_minor_alternatives(session_data: List, dept_name: str = "統計系", year: str = "113") -> Dict:
    """
    專門檢查統計系輔系的可替代課程狀況
    
    Args:
        session_data: 全人 JSON 資料
        dept_name: 輔系名稱（預設"統計系"）
        year: 學年度（預設"113"）
    
    Returns:
        Dict: 微積分甲替代檢查結果
    """
    should_close = False
    conn = get_db()
    
    try:
        # 收集學生已通過的課程
        passed_courses = _collect_all_passed_courses(session_data)

        # 查詢輔系資料
        row = _get_minor_row(conn, dept_name, year)
        if row is None:
            return {'error': f'找不到輔系：{dept_name}（{year}）'}

        # 解析資料庫中的 JSON 資料
        required_courses: List[Dict] = json.loads(row["required_courses"])
        
        # 尋找微積分甲課程
        calculus_course = None
        for course in required_courses:
            if course["course_name"] == "微積分甲":
                calculus_course = course
                break
        
        if not calculus_course:
            return {'error': '找不到微積分甲課程設定'}
        
        # 檢查替代情況
        result = _check_statistics_calculus_alternatives(calculus_course, passed_courses)
        
        return {
            'required_course': '微積分甲',
            'alternatives': _course_alternatives(calculus_course),
            'student_completed': result["alternative_used"] if result["is_alternative"] else ("微積分甲" if result["completed"] else None),
            'is_alternative': result["is_alternative"],
            'requirement_met': result["completed"],
            'credits_earned': result["credits"]
        }

    finally:
        if should_close:
            conn.close()


if __name__ == "__main__":
    # 測試範例
    print("Group 2 輔系分析模組已載入")
    print(f"負責系所：{', '.join(GROUP2_DEPT_MAPPING.keys())}")
    
    # 測試英文系替代課程檢查
    test_english_courses = {
        "英美文學": 6,
        "文學作品讀法": 4,  # 這是英語語言學概論的可替代課程
        "英文作文(一)": 4,
        "英文作文(二)": 4,
        "閱讀指導": 4,
        "英語口語訓練": 4,
        "英語語音學": 3
    }
    
    print(f"\n測試英文系替代課程檢查:")
    print(f"模擬修課：{list(test_english_courses.keys())}")
    print(f"應包含'文學作品讀法'作為'英語語言學概論'的替代課程")
    
    # 測試統計系替代課程檢查
    test_statistics_courses = {
        "統計學(一)": 3,
        "統計學(二)": 3,
        "微積分": 3,        # 第一門微積分
        "微積分(二)": 3,    # 第二門微積分，共6學分替代微積分甲
        "線性代數": 3,
        "機率論": 3,
        "數理統計學(一)": 3,
        "數理統計學(二)": 3,
        "迴歸分析(一)": 3
    }
    
    print(f"\n測試統計系替代課程檢查:")
    print(f"模擬修課：{list(test_statistics_courses.keys())}")
    print(f"應包含'微積分 + 微積分(二)'作為'微積分甲'的替代課程（兩門3學分共6學分）")
    
    # 測試社會系群修選修
    test_sociology_courses_113 = {
        "社會學": 3,  # 必修
        "社會統計(一)": 4,  # 群修
        "社會學理論(上學期)": 4,  # 群修
        "大數據社會分析": 3,  # 選修
        "人口、家庭與空間研究": 3,  # 選修
        "社會組織": 3,  # 選修
        "新社會思想史": 3  # 選修
    }
    
    print(f"\n測試社會系113-114年度群修選修:")
    print(f"模擬修課：{list(test_sociology_courses_113.keys())}")
    print(f"必修3學分 + 群修8學分 + 選修12學分 = 23學分總要求")
    
    # 測試法文系歐洲相關選修
    test_french_courses = {
        "初級法文閱讀": 4,  # 必修
        "初級法文語法": 4,  # 必修
        "初級法文聽力會話": 4,  # 必修
        "初級法文應用": 4,  # 必修
        "歐洲聯盟概論": 3  # 歐洲相關選修
    }
    
    print(f"\n測試法文系歐洲相關選修:")
    print(f"模擬修課：{list(test_french_courses.keys())}")
    print(f"必修16學分 + 歐洲相關選修3學分 = 19學分總要求")
    
    # 測試民族系語言課程和社會文化課程
    test_ethnic_studies_courses = {
        "民族學": 6,  # 必修 (111-114年度)
        "民族政策": 3,  # 核心課程
        "滿語": 4,  # 語言課程
        "民族藝術": 3,  # 社會文化課程
        "民族宗教": 3,  # 社會文化課程
        "台灣民族史": 3  # 核心課程
    }
    
    print(f"\n測試民族系語言課程和社會文化課程:")
    print(f"模擬修課：{list(test_ethnic_studies_courses.keys())}")
    print(f"必修6學分 + 核心課程8學分 + 語言課程4學分 + 社會文化課程6學分 = 30學分總要求")
    
    # 測試歷史系基礎課程和進階課程
    test_history_courses = {
        "臺灣史": 3,  # 基礎課程
        "史學導論": 3,  # 基礎課程
        "中國通史(上)": 3,  # 基礎課程
        "中國通史(下)": 3,  # 基礎課程
        "世界通史(上)": 3,  # 基礎課程
        "世界通史(下)": 3,  # 基礎課程
        "專史類課程": 2,  # 進階課程
        "專題類課程": 2,  # 進階課程
        "專史類課程二": 2,  # 進階課程
        "專題類課程二": 2  # 進階課程
    }
    
    print(f"\n測試歷史系基礎課程和進階課程:")
    print(f"模擬修課：{list(test_history_courses.keys())}")
    print(f"基礎課程18學分 + 進階課程8學分 = 26學分（需30學分）")
    
    # 測試會計系群修和選修課程
    test_accounting_courses = {
        "中級會計學(一)": 3,  # 必修
        "中級會計學(二)": 3,  # 必修
        "成本管理會計(一)": 3,  # 必修
        "成本管理會計(二)": 3,  # 必修
        "稅務法規": 3,  # 必修
        "審計學(一)": 3,  # 必修 (113-114年度)
        "審計學(二)": 3,  # 必修 (113-114年度)
        "高級會計學(一)": 3,  # 群修課程
        "會計資訊系統(一)": 3  # 群修課程
    }
    
    print(f"\n測試會計系群修和選修課程:")
    print(f"模擬修課：{list(test_accounting_courses.keys())}")
    print(f"113-114年度：必修21學分 + 群修6學分 = 27學分（需36學分）")
    
    print(f"\n特殊處理功能:")
    print(f"- 英文系：英語語言學概論 → 8門可替代課程")
    print(f"- 統計系：微積分甲 → 兩門微積分課程（共6學分）")
    print(f"- 社會系：113-114年度群修+選修特殊結構")
    print(f"- 法文系：歐洲/歐盟相關選修課程特殊處理")
    print(f"- 民族系：語言課程+社會文化課程分群處理")
    print(f"- 歷史系：基礎課程+進階課程分群處理")
    print(f"- 會計系：年度差異的群修+選修結構")
    print(f"- 其他系所：一般輔系邏輯")
