import json
import pytest
from backend.pe_elective import analyze_elective
from backend.required import analyze_required
from backend.general import analyze_general
from backend.waiver import analyze_waiver


def _load(filename):
    with open(f"tests/test_data/{filename}", encoding="utf-8") as f:
        return json.load(f)


def _session(grade_records=None, waived=None):
    return [{
        "課業學習": {
            "coursePlan": {},
            "aboutMe": {
                "registerMajor": "資訊科學系",
                "doubleMajor": "",
                "registerDoubleMajor": "",
            },
            "waivedCourseList": waived or [],
            "gradeRecordList": grade_records or [],
        }
    }]


def _waived_course(name, code, credit, category, remark=""):
    return {
        "courseCode": code,
        "courseName": name,
        "credit": str(credit),
        "requiredOrElectiveCourse": category,
        "remark": remark,
        "semester": "1",
        "academicYear": "113",
    }


# ── Harry (112cs_Harry.json) ─────────────────────────────────────────────────

class TestHarryWaiverElective:
    """曾祈綸，轉學生，112 資訊科學系，有多筆抵免"""

    @pytest.fixture(scope="class")
    def result(self):
        return analyze_elective(_load("112cs_Harry.json"), "資訊科學系", "112")

    def test_waived_other_dept_required_counted_as_elective(self, result):
        """非本系必修抵免（商業資料分析基礎：Python（一））應計入選修"""
        course_names = [c["courseName"] for c in result["out_dept_courses"]]
        assert "商業資料分析基礎：Python （一）" in course_names

    def test_waived_own_dept_required_not_double_counted(self, result):
        """本系必修抵免（計算機程式設計（一））不應出現在選修"""
        all_names = [c["courseName"] for c in result["in_dept_courses"] + result["out_dept_courses"]]
        assert "計算機程式設計（一）" not in all_names

    def test_waived_pe_not_counted_as_elective(self, result):
        """體育抵免不應出現在選修"""
        all_names = [c["courseName"] for c in result["in_dept_courses"] + result["out_dept_courses"]]
        assert "體育" not in all_names

    def test_waived_group_course_not_double_counted(self, result):
        """群修抵免（計算機網路）不應出現在選修"""
        all_names = [c["courseName"] for c in result["in_dept_courses"] + result["out_dept_courses"]]
        assert "計算機網路" not in all_names


# ── 抵免邏輯單元測試（合成 session）──────────────────────────────────────────

def test_waived_elective_counted():
    """抵免選修課應計入 out_dept 選修學分"""
    waived = [_waived_course("某選修課", "999999001", 3.0, "選")]
    result = analyze_elective(_session(waived=waived), "資訊科學系", "112")
    course_names = [c["courseName"] for c in result["out_dept_courses"]]
    assert "某選修課" in course_names
    assert result["out_dept_credits"] >= 3


def test_waived_zero_credit_not_counted():
    """0 學分抵免課不應計入"""
    waived = [_waived_course("零學分課", "999999002", 0.0, "必")]
    result = analyze_elective(_session(waived=waived), "資訊科學系", "112")
    all_names = [c["courseName"] for c in result["in_dept_courses"] + result["out_dept_courses"]]
    assert "零學分課" not in all_names


def test_waived_pe_excluded():
    """體育抵免（課號 002 開頭）不應計入選修"""
    waived = [_waived_course("體育（網球）", "002000001", 1.0, "必")]
    result = analyze_elective(_session(waived=waived), "資訊科學系", "112")
    all_names = [c["courseName"] for c in result["in_dept_courses"] + result["out_dept_courses"]]
    assert "體育（網球）" not in all_names


def test_waived_group_course_excluded():
    """群修類別抵免不應計入選修（由 required 模組處理）"""
    waived = [_waived_course("計算機網路", "703027001", 3.0, "群")]
    result = analyze_elective(_session(waived=waived), "資訊科學系", "112")
    all_names = [c["courseName"] for c in result["in_dept_courses"] + result["out_dept_courses"]]
    assert "計算機網路" not in all_names


# ── analyze_required 抵免測試 ────────────────────────────────────────────────

class TestHarryWaiverRequired:
    """Harry 的 waivedCourseList 中有三門本系必修，應全數計為通過"""

    @pytest.fixture(scope="class")
    def result(self):
        return analyze_required(
            _load("112cs_Harry.json"), dept_name="資訊科學系", year="112"
        )

    def test_waived_required_in_passed(self, result):
        """抵免的本系必修（計算機程式設計（一）、線性代數）應出現在 passed"""
        passed = result["passed"]
        assert "計算機程式設計（一）" in passed
        assert "線性代數" in passed

    def test_waived_required_not_in_missing(self, result):
        """抵免的本系必修不應出現在 missing"""
        missing = result["missing"]
        assert "計算機程式設計（一）" not in missing
        assert "線性代數" not in missing


def test_waived_required_counted_synthetic():
    """合成資料：只有 waivedCourseList，抵免一門必修，應出現在 passed 不在 missing"""
    session = [{
        "課業學習": {
            "coursePlan": {},
            "aboutMe": {
                "registerMajor": "資訊科學系",
                "doubleMajor": "",
                "registerDoubleMajor": "",
            },
            "waivedCourseList": [
                _waived_course("資料結構", "703008001", 3.0, "必"),
            ],
            "gradeRecordList": [],
        }
    }]
    result = analyze_required(session, dept_name="資訊科學系", year="112")
    assert "資料結構" in result["passed"]
    assert "資料結構" not in result["missing"]


def test_non_waived_required_still_missing():
    """沒有抵免也沒有修課，必修應出現在 missing"""
    session = [{
        "課業學習": {
            "coursePlan": {},
            "aboutMe": {
                "registerMajor": "資訊科學系",
                "doubleMajor": "",
                "registerDoubleMajor": "",
            },
            "waivedCourseList": [],
            "gradeRecordList": [],
        }
    }]
    result = analyze_required(session, dept_name="資訊科學系", year="112")
    assert "資料結構" in result["missing"]


# ── analyze_general 通識抵免測試 ─────────────────────────────────────────────
# 測試資料：111cs輔日抵免資料.json
# waivedCourseList 含：國文（一）、大學英文（一）、大學英文（二）、人文學通識、體育×2

class TestGeneralWaiver:
    @pytest.fixture(scope="class")
    def result(self):
        return analyze_general(_load("111cs輔日抵免資料.json"), "資訊科學系", "111")

    def test_waived_chinese_counted(self, result):
        """抵免國文（一）應計入中文通識學分"""
        assert result["by_category"]["中文"] >= 3.0

    def test_waived_english_counted(self, result):
        """抵免大學英文（一）+（二）應計入英文通識學分共 6 學分"""
        assert result["by_category"]["英文"] == 6.0

    def test_waived_pe_not_counted_as_general(self, result):
        """體育抵免不應計入任何通識類別"""
        cats = result["by_category"]
        # 體育不屬於任何通識領域，總計 = 各類加總不含體育
        total_from_cats = sum(cats.values())
        assert total_from_cats == result["credits_earned"]

    def test_waived_courses_appear_in_taken_courses(self, result):
        """抵免課應出現在 taken_courses，source 標記為 waived"""
        waived = [c for c in result["taken_courses"] if c.get("source") == "waived"]
        waived_names = {c["courseName"] for c in waived}
        assert "國文（一）" in waived_names
        assert "大學英文（一）" in waived_names
        assert "大學英文（二）" in waived_names

    def test_credits_earned(self, result):
        """含抵免的總通識學分應為 26"""
        assert result["credits_earned"] == 26.0


# ── analyze_waiver 彙整模組測試 ──────────────────────────────────────────────

class TestAnalyzeWaiver:
    @pytest.fixture(scope="class")
    def result(self):
        return analyze_waiver(_load("111cs輔日抵免資料.json"))

    def test_result_keys(self, result):
        for key in ("total_credits", "course_count", "by_category", "courses"):
            assert key in result, f"缺少欄位：{key}"

    def test_course_count(self, result):
        """應有 6 筆抵免課"""
        assert result["course_count"] == 6

    def test_total_credits(self, result):
        """總抵免學分應為 13"""
        assert result["total_credits"] == 13.0

    def test_chinese_classified(self, result):
        """國文（一）應分類為語言通識（中文）"""
        cats = result["by_category"]
        assert "語言通識（中文）" in cats
        assert cats["語言通識（中文）"] == 3.0

    def test_english_classified(self, result):
        """大學英文應分類為語言通識（英文），共 6 學分"""
        cats = result["by_category"]
        assert "語言通識（英文）" in cats
        assert cats["語言通識（英文）"] == 6.0

    def test_pe_classified(self, result):
        """體育抵免應分類為體育，共 2 學分"""
        cats = result["by_category"]
        assert "體育" in cats
        assert cats["體育"] == 2.0

    def test_by_category_sums_to_total(self, result):
        """by_category 加總應等於 total_credits"""
        total = sum(result["by_category"].values())
        assert total == result["total_credits"]
