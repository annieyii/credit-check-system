import pytest
from fastapi.testclient import TestClient
from backend.upload_file import app

client = TestClient(app)

FAKE_DATA = "tests/test_data/exportStudentData_fake.json"


def test_upload_valid_json():
    """合法的全人 JSON 應回傳 200 且結果為 true"""
    with open(FAKE_DATA, "rb") as f:
        response = client.post("/upload_file", files={"file": ("data.json", f, "application/json")})
    assert response.status_code == 200
    assert response.json() is True


def test_upload_fake_data_with_failing_grades():
    """含不及格科目的假資料應仍能正常上傳（格式合法）"""
    with open(FAKE_DATA, "rb") as f:
        response = client.post("/upload_file", files={"file": ("fake.json", f, "application/json")})
    assert response.status_code == 200
    assert response.json() is True


def test_upload_invalid_json():
    """格式錯誤的 JSON 應回傳 422"""
    bad_content = b"{ this is not valid json"
    response = client.post("/upload_file", files={"file": ("bad.json", bad_content, "application/json")})
    assert response.status_code == 422


def test_upload_empty_file():
    """空檔案應回傳 422"""
    response = client.post("/upload_file", files={"file": ("empty.json", b"", "application/json")})
    assert response.status_code == 422


def test_upload_non_json_content():
    """純文字檔案應回傳 422"""
    response = client.post("/upload_file", files={"file": ("text.json", b"hello world", "application/json")})
    assert response.status_code == 422
