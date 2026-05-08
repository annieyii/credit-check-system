# 輔系 JSON 架構說明與正規化計畫

## 一、原始 JSON 頂層結構

所有 210 個檔案（42 系 × 5 學年）共有以下頂層欄位：

```
metadata
credit_summary
prerequisites_external      ← 201/210 有（9 個舊年度沒有）
course_structure
special_regulations
```

---

## 二、各欄位詳細說明

### `metadata`
```json
{
  "department": "日本語文學系",
  "applicable_year": "110",
  "last_updated": null,
  "contact_extension": null
}
```
- `department`：系所名稱（注意：部分與資料夾/檔名不同，例如檔名「資訊系」、欄位「資訊科學學系」）
- `applicable_year`：學年度字串

---

### `credit_summary`
```json
{
  "total_credits_required": 32,
  "breakdown": {
    "required": 28,
    "group_elective": 4,
    "general_elective": 0
  },
  "foundation_credits_not_counted": 0,
  "note": "合計學分：32學分"
}
```
- `total_credits_required`：輔系應修總學分
- `breakdown.required`：必選修科目學分
- `breakdown.group_elective`：選修群組學分（**99% 的情況**）
- `breakdown.group_elective_a` / `breakdown.group_elective_b`：僅創國（113、114）兩筆，分成 A/B 群
- `breakdown.general_elective`：通識（幾乎都是 0）
- `breakdown.elective`：9 個東南亞語系檔案用的欄位名稱（同 group_elective 意義）
- `foundation_credits_not_counted`：基礎科目學分（**不計入**輔系畢業學分）

---

### `prerequisites_external`
9 個舊年度檔案沒有此欄，其餘多為空陣列。少數系（23 筆）有預修要求，格式：
```json
[
  {
    "subject": "微積分",
    "credits": { "min": 3, "max": 3, "display": "3" },
    "is_mandatory": true,
    "can_be_taken_concurrently": false
  }
]
```
→ **不影響學分計算，analyze_minor 不需要比對，忽略。**

---

### `course_structure`

這是最複雜的欄位，包含以下子欄位（並非每個檔案都有）：

#### `required_courses`（全部 210 個都有此 key，但 19 個是空陣列）

19 個空的系：教育系（110–114）、歷史系（110–114）、法律系（110–114）、社會系（110–111）  
→ 這些系「全部學分都來自 group_electives」，無必選修。

有資料的格式：
```json
{
  "course_name": "詩選",
  "credits": { "min": 3, "max": 3, "display": "3" },
  "offering_type": "隨系附修",
  "prerequisites_internal": [],
  "alternative_courses": [...],
  "recommended_year": "第一年",
  "note": null
}
```

**`alternative_courses` 有三種格式：**

| 格式 | 範例 | 出現情況 |
|------|------|---------|
| `[]` | `[]` | 大多數課程 |
| `[{course_name, credits}]` | `[{"course_name": "詩選及習作", "credits": 3}]` | 182/210 個檔案（主流格式） |
| `["字串"]` | `["000219032", "個體經濟學"]` | 少數，字串可能是課號（9 位數字）或課名 |

#### `group_electives`（201/210 有，無 group_electives 的 9 個也沒有選修課程）
```json
{
  "selection_rule": "任選 4 門專業選修課程（共計 12 學分）。",
  "groups": [
    {
      "group_name": "選修課程",
      "min_credits_required": 12,
      "courses": [
        {
          "course_name": "物件導向程式設計",
          "credits": { "min": 3, "max": 3, "display": "3" },
          "offering_type": "隨系附修",
          "note": null
        }
      ]
    }
  ]
}
```
- 絕大多數系只有 1 個 group
- 創國（113、114）有 2 個 group（群A、群B），各自有 min_credits_required

#### `foundation_courses`（6/210，僅會計系 110–114 及部分年度）
```json
[
  {
    "course_name": "經濟學",
    "credits": { "min": 3, "max": 3, "display": "3" },
    "offering_type": "隨系附修",
    "alternative_courses": ["個體經濟學"],
    "note": "基礎科目"
  }
]
```
- 修課門檻，但**不計入輔系應修學分**（`foundation_credits_not_counted` 欄位說明）
- → **analyze_minor 不需要計分，忽略。**

#### `elective_courses`（9/210，東南亞語系）
```json
[
  {
    "course_name": "本學程開設之必、群、選修科目",
    "credits_to_complete": 6,
    "note": "原則上不予採計第二東南亞語言類及大學外文科目"
  }
]
```
- 這是「任選 X 學分」的文字說明，**不是實際課名**，無法用來比對課程。
- → **忽略，分析結果顯示「請參閱特殊規定」。**

#### `general_electives`（9/210，會計系部分年度）
```json
{ "note": "學生應自本系學士班及碩士班開設課程中，任選 4 門以上，至少 12 學分。" }
```
- 只有 note 字串，沒有實際課程清單。
- → **忽略，分析結果顯示「請參閱特殊規定」。**

---

### `special_regulations`
```json
["限修習本校資科系 (科目代號前三碼 703) 所開課程。", "修讀標準：..."]
```
純文字，全部存下來顯示給學生看。

---

## 三、正規化計畫

### 目標格式（存入 DB 的 JSON 欄位）

```json
{
  "required_courses": [
    {
      "course_name": "計算機程式設計(一)",
      "credits": 3,
      "alternatives": ["計算機程式設計", "計算機概論"]
    }
  ],
  "elective_groups": [
    {
      "group_name": "選修課程",
      "min_credits": 12,
      "courses": [
        { "course_name": "物件導向程式設計", "credits": 3 }
      ]
    }
  ]
}
```

### 正規化規則

| 原始欄位 | 處理方式 |
|---------|---------|
| `course_structure.required_courses` | 逐筆取 `course_name` 和 `credits.min`（或 `credits` 若已是整數） |
| `required_courses[].alternative_courses` | dict 格式：取 `course_name`；字串格式：過濾掉純數字課號（9位），保留課名 |
| `course_structure.group_electives.groups` | 展開每個 group，取 `group_name`、`min_credits_required`、courses 清單 |
| `group_electives.groups[].courses` | 取 `course_name` 和 `credits.min` |
| `course_structure.foundation_courses` | **忽略**（不計入學分） |
| `course_structure.elective_courses` | **忽略**（無法用課名比對） |
| `course_structure.general_electives` | **忽略**（無課名清單） |
| `prerequisites_external` | **忽略**（不影響學分計算） |
| `special_regulations` | 原樣存入 `special_regulations` 欄位 |

### `analyze_minor` 比對邏輯（預覽）

```
必選修通過條件：學生修課清單中有課名符合 course_name 或任一 alternatives，且成績及格
選修群組通過條件：學生在該群組內通過的課程學分加總 >= min_credits
```

### DB Schema（一張表）

```sql
CREATE TABLE IF NOT EXISTS minor_departments (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name              TEXT NOT NULL,
    applicable_year        TEXT NOT NULL,
    total_credits_required INTEGER DEFAULT 0,
    required_credits       INTEGER DEFAULT 0,
    group_elective_credits INTEGER DEFAULT 0,
    required_courses       TEXT,   -- JSON: 正規化後的必選修課程
    elective_groups        TEXT,   -- JSON: 正規化後的選修群組
    special_regulations    TEXT,   -- JSON: 特殊規定字串陣列
    UNIQUE(dept_name, applicable_year)
);
```
