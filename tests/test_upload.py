import json
from fastapi.testclient import TestClient
from backend.main import app

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
