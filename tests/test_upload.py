import json
from fastapi.testclient import TestClient
from backend.main import app, _extract_minor_targets

client = TestClient(app)

FAKE_DATA_PATH = "tests/test_data/112cs_fake.json"


def _load_fake_data() -> list:
    with open(FAKE_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_upload_valid_json():
    """合法的全人 JSON 應回傳 200 且包含各分析結果"""
    response = client.post("/api/v1/analyze", json={
        "role": "general",
        "data": _load_fake_data()
    })
    assert response.status_code == 200
    body = response.json()
    assert "required_courses" in body
    assert "general_education" in body
    assert "physical_education" in body
    assert "elective" in body


def test_upload_fake_data_with_failing_grades():
    """含不及格科目的假資料應仍能正常分析（格式合法）"""
    response = client.post("/api/v1/analyze", json={
        "role": "dual",
        "data": _load_fake_data()
    })
    assert response.status_code == 200
    assert "required_courses" in response.json()


def test_upload_empty_data():
    """data 欄位為空應回傳 422"""
    response = client.post("/api/v1/analyze", json={
        "role": "general",
        "data": {}
    })
    assert response.status_code == 422


def test_upload_missing_role():
    """缺少 role 欄位應回傳 422"""
    response = client.post("/api/v1/analyze", json={
        "data": _load_fake_data()
    })
    assert response.status_code == 422


def test_upload_missing_data():
    """缺少 data 欄位應回傳 422"""
    response = client.post("/api/v1/analyze", json={
        "role": "general"
    })
    assert response.status_code == 422


def test_upload_response_includes_minor_key():
    """有輔系的學生，response 應包含非 None 的 minor 欄位"""
    session_data = [{
        "課業學習": {
            "aboutMe": {
                "registerMajor": "資訊科學系",
                "registerMinor": "財管系",
                "studentNumber": "112703001",
                "chineseName": "測試學生",
            },
            "gradeRecordList": [],
            "waivedCourseList": [],
            "coursePlan": {"commonPhysicalCount": "4"},
        }
    }]
    response = client.post("/api/v1/analyze", json={
        "role": "dual",
        "data": session_data,
    })
    assert response.status_code == 200
    body = response.json()
    assert "minor" in body
    assert body["minor"] is not None


def test_upload_response_no_minor_key_is_none():
    """無輔系的學生，minor 欄位應為 None"""
    response = client.post("/api/v1/analyze", json={
        "role": "general",
        "data": _load_fake_data(),
    })
    assert response.status_code == 200
    body = response.json()
    assert "minor" in body
    assert body["minor"] is None


def test_extract_minor_targets_uses_minor1_minor2_years():
    """雙輔系時應分別使用 minor1 / minor2 的申請年度"""
    about = {
        "registerMinor": "統計學系、日本語文學系",
        "minor1": "統計系（113）",
        "minor2": "日文系（114）",
        "studentNumber": "111303007",
    }

    assert _extract_minor_targets(about) == [
        ("統計學系", "113"),
        ("日本語文學系", "114"),
    ]
