import json
import pytest
from backend.minor import analyze_minor

CS_MINOR_PATH = "tests/test_data/cs_minor.json"


@pytest.fixture
def finance_minor_session():
    with open(CS_MINOR_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [data] if isinstance(data, dict) else data


def test_result_keys(finance_minor_session):
    """analyze_minor 回傳應包含必要欄位"""
    result = analyze_minor(finance_minor_session, "財管系", "112")
    assert "credits_earned" in result
    assert "credits_needed" in result
    assert "passed" in result
    assert "missing" in result


def test_passed_and_missing_are_lists(finance_minor_session):
    """passed / missing 應為 list"""
    result = analyze_minor(finance_minor_session, "財管系", "112")
    assert isinstance(result["passed"], list)
    assert isinstance(result["missing"], list)


def test_credits_valid(finance_minor_session):
    """credits_earned >= 0，credits_needed > 0"""
    result = analyze_minor(finance_minor_session, "財管系", "112")
    assert result["credits_earned"] >= 0
    assert result["credits_needed"] > 0


def test_passed_is_list(finance_minor_session):
    """passed 應為課程名稱列表"""
    result = analyze_minor(finance_minor_session, "財管系", "112")
    assert isinstance(result["passed"], list)


def test_unknown_dept_raises_value_error(finance_minor_session):
    """找不到的輔系應 raise ValueError"""
    with pytest.raises(ValueError):
        analyze_minor(finance_minor_session, "不存在的系所XYZXYZ", "112")


def test_passed_and_missing_no_overlap(finance_minor_session):
    """同一門課不應同時出現在 passed 和 missing 中"""
    result = analyze_minor(finance_minor_session, "財管系", "112")
    overlap = set(result["passed"]) & set(result["missing"])
    assert len(overlap) == 0
