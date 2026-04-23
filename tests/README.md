# 測試說明

## 環境設置

測試使用 [uv](https://docs.astral.sh/uv/) 管理 Python 環境與依賴。

**1. 安裝 uv**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. 安裝依賴（含 dev 套件）**

```bash
uv sync --all-groups
```

這會自動建立 `.venv` 虛擬環境並安裝所有套件，包含 `pytest`、`httpx`、`fastapi`、`python-multipart` 等。

**3. 設定 `.env`**

確認根目錄的 `.env` 有以下設定：

```
DB_PATH=db/database/curriculum.db
```

## 執行測試

```bash
uv run pytest tests/ -v
```

---

## 測試檔案

### `test_upload.py` — 上傳 API 測試

對應後端：`backend/upload_file.py`，路由 `POST /upload_file`

| 測試名稱 | 情境 | 預期結果 |
|---------|------|---------|
| `test_upload_valid_json` | 上傳合法全人 JSON | 200，回傳 `true` |
| `test_upload_fake_data_with_failing_grades` | 上傳含不及格科目的假資料 | 200，回傳 `true`（格式合法） |
| `test_upload_invalid_json` | 上傳格式錯誤的 JSON | 422 |
| `test_upload_empty_file` | 上傳空檔案 | 422 |
| `test_upload_non_json_content` | 上傳純文字 | 422 |

---

### `test_api.py` — 後端 API 端點測試

對應後端：`backend/main.py`

| 測試名稱 | 情境 | 預期結果 |
|---------|------|---------|
| `test_health_check` | GET `/` | 200，`status == "ok"` |
| `test_get_departments_returns_list` | GET `/departments` | 200，非空清單 |
| `test_get_departments_fields` | GET `/departments` 欄位檢查 | 包含必要欄位 |
| `test_get_courses_valid_department` | GET `/departments/資訊科學系/courses?year=114` | 200，非空清單 |
| `test_get_courses_invalid_department` | GET 不存在的系所 | 404 |
| `test_get_courses_fields` | 課程資料欄位檢查 | 包含必要欄位 |

---

### `test_database.py` — 資料庫函數測試

對應：`backend/database.py`、`db/database/seed_db.py`

| 測試名稱 | 情境 | 預期結果 |
|---------|------|---------|
| `test_get_db_returns_connection` | `get_db()` 基本連線 | 回傳非空連線 |
| `test_get_db_row_factory` | 連線支援欄位名稱存取 | `row["name"]` 可用 |
| `test_all_tables_exist` | Schema 完整性 | 五張資料表皆存在 |
| `test_load_records_with_dict` | JSON 為單一 dict | 包裝成 list 回傳 |
| `test_load_records_with_list` | JSON 為 list | 回傳所有 dict 項目 |
| `test_load_records_filters_non_dict` | list 含非 dict 項目 | 非 dict 被過濾掉 |
| `test_reset_department_data_clears_courses` | 清除必修課與開課學期 | 該系資料歸零 |
| `test_reset_department_data_clears_special_rules` | 清除特殊規則 | 該系規則歸零 |

---

## 測試資料

| 檔案 | 說明 |
|------|------|
| `tests/test_data/exportStudentData_fake.json` | 假資料，含 10 門不及格科目，用於測試邊界情境 |

詳細假資料內容見 [tests/test_data/exportStudentData_fake.md](test_data/exportStudentData_fake.md)。

---

## Fixtures（conftest.py）

| Fixture | 說明 |
|---------|------|
| `temp_db` | 每個測試獨立的記憶體 SQLite DB，載入 `db/database/schema.sql`，測完自動清除 |

---

## CI 觸發條件

有任何 commit push 到 `backend/sprint1-test` branch 時自動執行，分兩個 stage：

1. **lint** — 檢查所有後端與測試 Python 檔案的語法
2. **test** — 執行全部 19 個測試
