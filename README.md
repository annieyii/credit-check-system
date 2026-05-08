# 畢業審判官 — 畢業學分檢核系統

針對政大雙主修／輔系生設計，解析全人系統成績單 JSON，自動比對各系必修規則，回報是否符合畢業資格。

---

## 目錄結構

```
credit-check-system/
├── backend/
│   ├── main.py          ← FastAPI 主程式（API 路由）
│   ├── database.py      ← SQLite 連線設定
│   └── upload_file.py   ← 曾祈綸的上傳草稿（保留備用）
├── db/
│   ├── data/            ← 各系所必修 HTML / JSON 原始資料
│   └── database/
│       ├── schema.sql        ← 資料表定義
│       ├── init_db.py        ← 建立資料庫
│       ├── seed_db.py        ← 匯入必修 JSON 資料
│       ├── seed_minor_db.py  ← 匯入輔系 JSON 資料
│       └── curriculum.db     ← SQLite 資料庫（不 commit）
├── frontend/
│   ├── app/page.tsx     ← 上傳主頁面（Next.js）
│   ├── hooks/useErrorHandler.ts ← API 呼叫 + 錯誤處理
│   └── components/ErrorMessage.tsx ← 錯誤訊息元件
├── tests/
│   ├── test_api.py      ← GET 端點測試
│   ├── test_upload.py   ← POST /api/v1/analyze 測試
│   ├── test_database.py ← 資料庫函數測試
│   ├── conftest.py      ← temp_db fixture
│   └── test_data/       ← 假資料
├── .gitlab-ci.yml       ← CI：push 到 backend/sprint1-test 自動跑
├── pyproject.toml       ← Python 套件設定（uv 管理，僅測試用）
└── .env                 ← 本地環境變數（不 commit）
```

---

## 快速啟動

### 後端

```bash
pip install fastapi uvicorn python-dotenv
uvicorn backend.main:app --reload
# → http://127.0.0.1:8000
```

`.env` 設定（放根目錄）：
```
DB_PATH=db/database/curriculum.db
```



### 前端

```bash
cd frontend
pnpm install
pnpm dev
# → http://localhost:3000
```

---

## API 端點

| 方法 | 路徑 | 功能 |
|------|------|------|
| GET | `/` | 健康檢查 |
| GET | `/departments` | 查所有系所清單 |
| GET | `/departments/{dept_name}/courses?year=114` | 查指定系所必修課程 |
| POST | `/api/v1/analyze` | 接收全人 JSON，回傳分析結果 |

**POST /api/v1/analyze 請求格式：**
```json
{
  "role": "general",
  "data": { ...全人 JSON 課業學習物件... }
}
```
`role` 可為 `"general"`（一般生）或 `"dual"`（雙輔生）。

---

## 資料庫說明

**資料表：**

| 資料表 | 說明 |
|--------|------|
| `departments` | 系所基本資訊（系名、學年、最低畢業學分） |
| `required_courses` | 各系各年度必修課程清單 |
| `course_schedules` | 每門課開課學期（Y1S1 ～ Y4S2，與 required_courses 1對1） |
| `special_rules` | 各系修課特殊規定 |
| `minor_departments` | 輔系資料（必選修課程、選修群組、特殊規定，以 JSON 欄位儲存） |

**初始化資料庫（首次或重建時）：**
```bash
# 1. 建立所有資料表
python -m db.database.init_db

# 2. 匯入必修資料（約 230 筆）
python -m db.database.seed_db

# 3. 匯入輔系資料（210 筆，42 系 × 5 學年）
python -m db.database.seed_minor_db | tee seed_minor.log
# ⚠️ 若有警告會印出，可用 grep ⚠️ seed_minor.log 查看
```


### 終端機查詢
```bash
sqlite3 db/database/curriculum.db
```
```bash
.tables   # 先看表
.schema departments      # 看欄位
.schema required_courses  
```
```bash
-- 先找有哪些系所/年度
SELECT id, dept_name, applicable_year
FROM departments
ORDER BY applicable_year DESC
LIMIT 20;

-- 查某系某年度的必修課（含建議年級）
SELECT rc.name, rc.credits, rc.type, rc.suggested_year
FROM required_courses rc
JOIN departments d ON rc.department_id = d.id
WHERE d.dept_name LIKE '資訊%' AND d.applicable_year = '114'
ORDER BY rc.suggested_year, rc.name;

-- 查特殊規定
SELECT sr.rule_order, sr.rule_text
FROM special_rules sr
JOIN departments d ON sr.department_id = d.id
WHERE d.dept_name LIKE '資訊%' AND d.applicable_year = '114'
ORDER BY sr.rule_order;
```


### 後端查詢範例（Python）
```python
import sqlite3
conn = sqlite3.connect("database/curriculum.db")
cursor = conn.cursor()

# 查某系某學年的必修課（含開課學期）
cursor.execute("""
    SELECT rc.name, rc.credits, rc.type, rc.suggested_year,
           cs.Y1S1, cs.Y1S2, cs.Y2S1, cs.Y2S2,
           cs.Y3S1, cs.Y3S2, cs.Y4S1, cs.Y4S2
    FROM required_courses rc
    JOIN departments d ON rc.department_id = d.id
    JOIN course_schedules cs ON cs.course_id = rc.id
    WHERE d.dept_name LIKE '資訊科學系%'
      AND d.applicable_year = '114'
      AND rc.type = '必修'
    ORDER BY rc.suggested_year
""")

# 查某系的特殊規定
# dept_name 可能包含「學士班/表名」等附加文字，建議使用 LIKE '系名%' 查詢。
cursor.execute("""
    SELECT rule_text FROM special_rules
    WHERE department_id = (
        SELECT id FROM departments
        WHERE dept_name LIKE '資訊科學系%' AND applicable_year = '114'
    )
    ORDER BY rule_order
""")
```
---

## 執行測試

需要先安裝 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync --all-groups
uv run pytest tests/ -v
```

目前共 19 個測試，涵蓋 API 端點、資料庫函數、上傳驗證。
