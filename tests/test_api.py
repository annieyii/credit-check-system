import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check():
    """GET / 應回傳系統運作中訊息"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_departments_returns_list():
    """GET /departments 應回傳非空清單"""
    response = client.get("/departments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_departments_fields():
    """每筆系所資料應包含必要欄位"""
    response = client.get("/departments")
    dept = response.json()[0]
    assert "dept_name" in dept
    assert "applicable_year" in dept
    assert "min_graduation_credits" in dept
    assert "compulsory_credits_required" in dept


def test_get_courses_valid_department():
    """GET /departments/{dept_name}/courses 找得到的系所應回傳 200"""
    response = client.get("/departments/資訊科學系/courses?year=114")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_courses_invalid_department():
    """GET /departments/{dept_name}/courses 找不到的系所應回傳 404"""
    response = client.get("/departments/不存在的系所XYZXYZ/courses?year=114")
    assert response.status_code == 404


def test_get_courses_fields():
    """每筆課程資料應包含必要欄位"""
    response = client.get("/departments/資訊科學系/courses?year=114")
    course = response.json()[0]
    assert "name" in course
    assert "credits" in course
    assert "type" in course
