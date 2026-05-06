-- =============================================
-- 1. 系所基本資訊表（對應 metadata）
-- =============================================
CREATE TABLE IF NOT EXISTS departments (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file                 TEXT,               -- 原始 HTML 檔名，e.g. "CS.html"
    dept_name                   TEXT NOT NULL,       -- 系所名稱
    applicable_year             TEXT NOT NULL,       -- 適用學年度 e.g. "114"
    min_graduation_credits      INTEGER DEFAULT 0,   -- 最低畢業總學分
    compulsory_credits_required INTEGER DEFAULT 0,   -- 規定必修學分數

    UNIQUE(dept_name, applicable_year)               -- 同系同年度不重複
);

-- =============================================
-- 2. 必修課程表（對應 required_courses[]）
-- =============================================
CREATE TABLE IF NOT EXISTS required_courses (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id           INTEGER NOT NULL,
    name                    TEXT NOT NULL,       -- 科目名稱
    type                    TEXT,               -- 修別：必修/選修/通識...
    credits                 INTEGER DEFAULT 0,  -- 規定學分
    semesters               INTEGER DEFAULT 1,  -- 學期數
    suggested_year          INTEGER,            -- 建議修課年級 1~4
    recognition             TEXT,               -- 本系認定方式
    course_code             TEXT,               -- 本系科目代碼
    dual_major_recognition  TEXT,               -- 雙主修認定方式
    dual_major_course_code  TEXT,               -- 雙主修科目代碼
    remarks                 TEXT,               -- 備註

    FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- =============================================
-- 3. 開課學期表（對應 schedule{}）
-- 把 Y1S1~Y4S2 八個布林值拆成獨立欄位
-- =============================================
CREATE TABLE IF NOT EXISTS course_schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL UNIQUE,    -- 對應 required_courses.id
    Y1S1            INTEGER DEFAULT 0,          -- 一上（0=否, 1=是）
    Y1S2            INTEGER DEFAULT 0,          -- 一下
    Y2S1            INTEGER DEFAULT 0,          -- 二上
    Y2S2            INTEGER DEFAULT 0,          -- 二下
    Y3S1            INTEGER DEFAULT 0,          -- 三上
    Y3S2            INTEGER DEFAULT 0,          -- 三下
    Y4S1            INTEGER DEFAULT 0,          -- 四上
    Y4S2            INTEGER DEFAULT 0,          -- 四下

    FOREIGN KEY (course_id) REFERENCES required_courses(id)
);

-- =============================================
-- 4. 修課特殊規定表（對應 special_rules[]）
-- =============================================
CREATE TABLE IF NOT EXISTS special_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id   INTEGER NOT NULL,
    rule_order      INTEGER NOT NULL,   -- 第幾條規則（保留順序）
    rule_text       TEXT NOT NULL,      -- 規則內容

    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS general_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,            -- 課程代碼
    credit INTEGER,       -- 學分數
    course_name TEXT,     -- 課程名稱
    semester TEXT,        -- 學期
    type TEXT,            -- 領域（人文/社會/自然...）
    is_core TEXT          -- 是否為核通
);