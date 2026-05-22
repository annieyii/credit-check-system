"""
對 tests/test_data/ 下所有 JSON 檔跑整合測試。
新增檔案到該資料夾後不需修改此檔，pytest 自動收入。
缺少 registerMajor 或 studentNumber 的檔案會被 skip。
"""
import glob
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def _all_json_files():
    return sorted(glob.glob("tests/test_data/*.json"))


def _load_session(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [data] if isinstance(data, dict) else data


def _is_analyzable(session):
    about = session[0].get("課業學習", {}).get("aboutMe", {})
    return bool(about.get("registerMajor")) and bool(about.get("studentNumber"))


@pytest.mark.parametrize("filepath", _all_json_files())
def test_analyze_all_data_files(filepath):
    """每個測試 JSON 都應能正常呼叫 /api/v1/analyze 並回傳完整結構"""
    session = _load_session(filepath)
    if not _is_analyzable(session):
        pytest.skip(f"缺少 registerMajor 或 studentNumber，略過：{filepath}")

    response = client.post("/api/v1/analyze", json={
        "role": "dual",
        "data": session,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert "required_courses" in body
    assert "general_education" in body
    assert "physical_education" in body
    assert "elective" in body
    assert "minor" in body
    assert "is_eligible_to_graduate" in body
    assert isinstance(body["is_eligible_to_graduate"], bool)
