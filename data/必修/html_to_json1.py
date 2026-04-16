import os
import json
import re
from bs4 import BeautifulSoup
from pathlib import Path

# --- 路徑設定 ---
input_folder = './110/html'
output_folder = './110/result'
output_filename = "110_requirements.json"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 學年上下學期對應欄位 index（cols[4]~cols[11]）
SCHEDULE_KEYS = ["Y1S1", "Y1S2", "Y2S1", "Y2S2", "Y3S1", "Y3S2", "Y4S1", "Y4S2"]

all_departments_data = []

print("--- 開始批次解析並合併完整資料 ---")

for filename in sorted(os.listdir(input_folder)):
    if not filename.endswith(".html"):
        continue

    file_path = os.path.join(input_folder, filename)

    dept_info = {
        "metadata": {
            "source_file": filename,
            "dept_name": "",
            "applicable_year": "114",
            "min_graduation_credits": 0,
            "major_required_credits": 0
        },
        "group_requirements": {},
        "required_courses": [],
        "special_rules": []
    }

    try:
        with open(file_path, 'r', encoding='big5', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # --- 1. 系名 ---
        title_tag = soup.find('font', {'face': '標楷體'})
        dept_info["metadata"]["dept_name"] = (
            title_tag.get_text(strip=True) if title_tag
            else Path(filename).stem
        )

        # --- 2. 畢業學分 & 必修學分 ---
        page_text = soup.get_text()
        grad_min = re.search(r'最低畢業總學分數：(\d+)', page_text)
        if grad_min:
            dept_info["metadata"]["min_graduation_credits"] = int(grad_min.group(1))

        comp_min = re.search(r'規定必修：\s*(\d+)', page_text)
        if comp_min:
            dept_info["metadata"]["major_required_credits"] = int(comp_min.group(1))

        # --- 3. 修課特殊規定 ---
        rules_td = soup.find(string=re.compile("修課特殊規定"))
        if rules_td:
            target_td = rules_td.find_parent('td')
            if target_td:
                dept_info["special_rules"] = [
                    r.strip() for r in target_td.get_text(strip=True).split('\n') if r.strip()
                ]

        # --- 4. 課程表格 ---
        # 欄位對照（共 17 欄，index 0-based）：
        # 0  科目名稱
        # 1  修別
        # 2  規定學分
        # 3  學期數
        # 4~11  一上/一下/二上/二下/三上/三下/四上/四下
        # 12 本系認定方式
        # 13 須修本門課之科目代碼（本系）
        # 14 雙主修認定方式
        # 15 雙主修須修本門課之科目代碼
        # 16 備註

        table = soup.find('table', border="1")
        if table:
            rows = table.find_all('tr')[2:]  # 跳過兩列標頭
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 17:
                    continue

                course_name = cols[0].get_text(strip=True)
                if not course_name or course_name == "無":
                    continue

                def col(i):
                    v = cols[i].get_text(strip=True)
                    return None if v in ('無', '') else v

                note_text = cols[16].get_text(strip=True) or None
                course_type = cols[1].get_text(strip=True)

                # 完整上下學期 schedule
                schedule = {
                    key: 'ｖ' in cols[4 + i].get_text() or 'v' in cols[4 + i].get_text().lower()
                    for i, key in enumerate(SCHEDULE_KEYS)
                }

                # suggested_year：取 schedule 第一個 True 的學年
                suggested_year = next(
                    (i // 2 + 1 for i, active in enumerate(schedule.values()) if active),
                    0
                )

                # 群修規則（首次遇到該群時建立）
                if "群" in course_type and course_type not in dept_info["group_requirements"]:
                    min_courses = re.search(r'至少選(\d+)門', note_text or '')
                    min_credits = re.search(r'至少(\d+)學分', note_text or '')
                    dept_info["group_requirements"][course_type] = {
                        "min_courses": int(min_courses.group(1)) if min_courses else None,
                        "min_credits": int(min_credits.group(1)) if min_credits else None,
                        "note": note_text
                    }

                course_obj = {
                    "name": course_name,
                    "type": course_type,
                    "credits": int(cols[2].get_text(strip=True)) if cols[2].get_text(strip=True).isdigit() else 0,
                    "semesters": int(cols[3].get_text(strip=True)) if cols[3].get_text(strip=True).isdigit() else 1,
                    "suggested_year": suggested_year,
                    "schedule": schedule,                              # ★ 完整上下學期
                    "recognition": cols[12].get_text(strip=True),
                    "course_code": col(13),                            # ★ 本系科目代碼
                    "dual_major_recognition": cols[14].get_text(strip=True),  # ★ 雙主修認定
                    "dual_major_course_code": col(15),                 # ★ 雙主修科目代碼
                    "has_lab": "實習" in (note_text or ""),
                    "remarks": note_text
                }
                dept_info["required_courses"].append(course_obj)

        all_departments_data.append(dept_info)
        print(f"✓ {dept_info['metadata']['dept_name']} ({filename})")

    except Exception as e:
        print(f"✗ 錯誤檔案 {filename}: {e}")

# --- 5. 儲存 ---
output_path = os.path.join(output_folder, output_filename)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_departments_data, f, ensure_ascii=False, indent=4)

print(f"\n--- 完成！共解析 {len(all_departments_data)} 個系所 → {output_path} ---")