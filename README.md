# 畢業審判官 — 畢業學分檢核系統

本專案原託管於 GitLab，後遷移至 GitHub。

針對政大學生設計，解析全人系統成績單 JSON，自動比對必修、通識、選修、體育學分規則，回報是否符合畢業資格。支援一般生與雙主修／輔系生兩種身分。

---

## 目錄結構

```
credit-check-system/
├── backend/
│   ├── main.py           ← FastAPI 主程式（API 路由與回應整合）
│   ├── database.py       ← SQLite 連線設定
│   ├── required.py       ← 必修學分分析
│   ├── general.py        ← 通識學分分析
│   ├── pe_elective.py    ← 體育／選修學分分析
│   ├── waiver.py         ← 抵免課程分析
│   └── minor.py          ← 輔系學分分析（所有系所）
├── db/
│   ├── data/
│   │   ├── 通識/         ← 各學期通識課程 xlsx 原始資料
│   │   └── 輔系/         ← 各輔系必修 PDF／JSON
│   └── database/
│       ├── schema.sql        ← 資料表定義
│       ├── init_db.py        ← 建立資料庫
│       ├── seed_db.py        ← 匯入必修課程資料
│       ├── seed_general.py   ← 匯入通識門檻資料
│       ├── seed_general_course.py ← 匯入通識課程清單
│       └── curriculum.db     ← SQLite 資料庫（不 commit）
├── frontend/
│   ├── app/
│   │   ├── page.tsx          ← 上傳主頁面（Next.js）
│   │   └── api/v1/analyze/   ← Mock API（開發測試用）
│   ├── hooks/useErrorHandler.ts  ← API 呼叫 + 錯誤處理
│   └── components/
│       ├── GraduationResult.tsx  ← 審查結果顯示元件
│       └── ErrorMessage.tsx      ← 錯誤訊息元件
├── tests/
│   ├── test_api.py           ← GET 端點測試
│   ├── test_upload.py        ← POST /api/v1/analyze 測試
│   ├── test_database.py      ← 資料庫函數測試
│   ├── required_double_test.py ← 雙主修必修測試
│   ├── conftest.py           ← temp_db fixture
│   └── test_data/            ← 測試用假資料
├── pyproject.toml        ← Python 套件設定（uv 管理）
├── .env                  ← 本地環境變數（不 commit，請複製 .env.example）
└── .env.example          ← 環境變數範本（commit 追蹤）
```

---

## 快速啟動

> Python 套件使用 [uv](https://docs.astral.sh/uv/) 管理，前端使用 pnpm。

### 後端

```bash
# 安裝依賴（首次）
uv sync

# 啟動 FastAPI（含熱重載）
uv run uvicorn backend.main:app --reload
# → http://127.0.0.1:8000
```

`.env` 設定（放根目錄，不 commit）：
```bash
cp .env.example .env
# 依需要修改後使用
```

`.env.example`（預設值）：
```
DB_PATH=db/database/curriculum.db
```

### 前端

```bash
cd frontend
pnpm install   # 首次安裝
pnpm dev
# → http://localhost:3000
```

前端會直接呼叫 `http://127.0.0.1:8000/api/v1/analyze`，請確認後端已啟動。

---

## API 端點

| 方法 | 路徑 | 功能 |
|------|------|------|
| GET | `/` | 健康檢查 |
| GET | `/departments` | 查所有系所清單 |
| GET | `/departments/{dept_name}/courses?year=114` | 查指定系所必修課程 |
| POST | `/api/v1/analyze` | 接收全人 JSON，回傳完整畢業分析結果 |

### POST /api/v1/analyze

**請求格式：**
```json
{
  "role": "general",
  "data": [ ...全人系統匯出的 JSON 陣列... ]
}
```
`role` 可為 `"general"`（一般生）或 `"dual"`（雙主修／輔系生）。

**回應格式：**
```json
{
  "dept_name": "資訊科學系",
  "applicable_year": "112",
  "summary": {
    "total_credits_earned": 95,
    "required_credits_earned": 62,
    "required_credits_needed": 72,
    "pe_credits_earned": 4,
    "pe_credits_needed": 4,
    "general_credits_earned": 20,
    "general_credits_needed": 28,
    "elective_credits_earned": 9,
    "elective_credits_needed": 24
  },
  "required_courses": {
    "passed": ["計算機概論", "資料結構", "..."],
    "missing": ["作業系統", "..."]
  },
  "general_education": {
    "credits_earned": 20,
    "credits_needed": 28,
    "passed": false,
    "by_category": { "人文": 6, "社會": 6, "自然": 2, "書院": 0, "國+英": 6 }
  },
  "physical_education": {
    "credits_earned": 4,
    "credits_needed": 4,
    "passed": true,
    "courses": ["體育（一）", "體育（二）", "體育（三）", "體育（四）"]
  },
  "elective": {
    "credits_earned": 9,
    "credits_needed": 24,
    "passed": false,
    "in_dept_credits": 6,
    "out_dept_credits": 3
  },
  "waiver": {
    "total_credits": 10,
    "course_count": 4,
    "by_category": { "語言通識（英文）": 6, "體育": 2, "通識（人文）": 2 },
    "courses": [ ... ]
  },
  "is_eligible_to_graduate": false
}
```

---

## 資料庫說明

### 資料表

| 資料表 | 說明 |
|--------|------|
| `departments` | 系所基本資訊（系名、學年、最低畢業學分、必修學分要求） |
| `required_courses` | 各系各年度必修課程清單 |
| `course_schedules` | 每門課開課學期（Y1S1 ～ Y4S2，與 required_courses 1對1） |
| `special_rules` | 各系修課特殊規定 |
| `general_education_requirements` | 各系通識門檻（總學分、語言通識、人文／社會／自然最低要求） |
| `general_courses` | 通識課程清單（課號、課名、領域、是否核通） |
| `minor_departments` | 各輔系必修／選修課程結構（JSON 欄位，由 seed_minor_db.py 填入） |

### 初始化資料庫（首次或重建時）

```bash
python db/database/init_db.py              # 建立資料表
python db/database/seed_db.py              # 匯入必修課程
python db/database/seed_general.py         # 匯入通識門檻
python db/database/seed_general_course.py  # 匯入通識課程清單
python db/database/seed_minor_db.py        # 匯入輔系課程資料
```

### 終端機查詢

```bash
sqlite3 db/database/curriculum.db
```
```sql
.tables
.schema departments

-- 查有哪些系所與學年
SELECT id, dept_name, applicable_year FROM departments ORDER BY applicable_year DESC LIMIT 20;

-- 查某系某年度的必修課
SELECT rc.name, rc.credits, rc.suggested_year
FROM required_courses rc
JOIN departments d ON rc.department_id = d.id
WHERE d.dept_name LIKE '資訊%' AND d.applicable_year = '114'
ORDER BY rc.suggested_year, rc.name;
```

---

## 執行測試

```bash
uv sync --all-groups
uv run pytest tests/ -v
```

---

## CI/CD 本地 Runner 設定

GitLab 免費帳號的 shared runner 配額有限。**每位成員**需在自己的電腦設定本地 runner，各自產生獨立的 token（token 與機器綁定，不共用）。

### 安裝

**macOS**
```bash
brew install gitlab-runner
```

**Linux**
```bash
sudo curl -L --output /usr/local/bin/gitlab-runner \
  https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
sudo chmod +x /usr/local/bin/gitlab-runner
sudo gitlab-runner install
```

### 取得 Token（每人各自操作）

到 GitLab 專案 **Settings → CI/CD → Runners → New project runner**：
- 勾選 **Run untagged jobs**
- 按 **Create runner**，複製產生的 `glrt-` token

### 註冊

```bash
gitlab-runner register \
  --url https://gitlab.com \
  --token <你自己的 glrt- token>
# 詢問 name → 自訂（例如 local-mac）
# 詢問 executor → shell
```

### 啟動

**macOS**
```bash
brew services start gitlab-runner
```

**Linux**
```bash
sudo gitlab-runner start
```
