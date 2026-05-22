import pytest
from backend.pe_elective import analyze_pe


def _session(physical_count, grade_records=None, waived=None):
    return [{
        "課業學習": {
            "coursePlan": {"commonPhysicalCount": physical_count},
            "waivedCourseList": waived or [],
            "gradeRecordList": grade_records or [],
        }
    }]


def _pe_course(name, score, code="00200001"):
    return {
        "courseCode": code,
        "courseName": name,
        "score": score,
        "credit": "1.0",
        "requiredOrElectiveCourse": "必",
    }


def _semester(courses):
    return {"GradeRecords": courses}


def test_result_keys():
    """回傳應包含必要欄位"""
    result = analyze_pe(_session("4"), "資訊科學系", "112")
    assert "credits_earned" in result
    assert "credits_needed" in result
    assert "passed" in result
    assert "courses" in result


def test_empty_physical_count_defaults_to_4():
    """commonPhysicalCount 為空字串時，credits_needed 應 fallback 為 4 不崩潰"""
    result = analyze_pe(_session(""), "資訊科學系", "112")
    assert result["credits_needed"] == 4


def test_four_pe_passed():
    """修完 4 門體育應 passed=True"""
    courses = [_pe_course(f"體育（{i}）", "80") for i in range(1, 5)]
    result = analyze_pe(_session("4", [_semester(courses)]), "資訊科學系", "112")
    assert result["credits_earned"] == 4
    assert result["passed"] is True


def test_two_pe_passed():
    """只修完 2 門體育應 passed=False"""
    courses = [_pe_course(f"體育（{i}）", "80") for i in range(1, 3)]
    result = analyze_pe(_session("4", [_semester(courses)]), "資訊科學系", "112")
    assert result["credits_earned"] == 2
    assert result["passed"] is False


def test_failed_course_not_counted():
    """不及格的體育課不應計入 credits_earned"""
    courses = [_pe_course("體育（一）", "50")]
    result = analyze_pe(_session("4", [_semester(courses)]), "資訊科學系", "112")
    assert result["credits_earned"] == 0


def test_waived_pe_counted():
    """抵免的體育課應計入"""
    waived = [{"courseCode": "00200001", "courseName": "體育（一）", "credit": "1.0",
               "requiredOrElectiveCourse": "必"}]
    result = analyze_pe(_session("4", waived=waived), "資訊科學系", "112")
    assert result["credits_earned"] == 1
