import os
import json
import re
from bs4 import BeautifulSoup
from pathlib import Path

input_folder = './114/html'
output_folder = './114/result'

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 學年上下學期對應的欄位 index（cols[4]~cols[11]）
SCHEDULE_KEYS = ["Y1S1", "Y1S2", "Y2S1", "Y2S2", "Y3S1", "Y3S2", "Y4S1", "Y4S2"]

for filename in os.listdir(input_folder):
    if not filename.endswith(".html"):
        continue

    file_path = os.path.join(input_folder, filename)

    dept_info = {
        "metadata": {
            "source_file": filename,
            "dept_name": "",
            "applicable_year": "114",
            "min_graduation_credits": 0,
            "compulsory_credits_required": 0
        },
        "required_courses": [],
        "special_rules": []
    }

    try:
        with open(file_path, 'r', encoding='big5', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # --- 1. 系名 ---
        title_tag = soup.find('font', {'face': '標楷體'})
        if title_tag:
            # 取得原始文字： "土耳其語文學系\n 【學士班】\n 專業必修科目表一覽表"
            raw_title = title_tag.get_text(strip=True)
            # 修正後： "土耳其語文學系"
            dept_info["metadata"]["dept_name"] = re.sub(r'【學士班】.*|專業必修科目表一覽表.*', '', raw_title).strip()
        
        # --- 2. 畢業學分與必修學分 ---
        page_text = soup.get_text()
        grad_min = re.search(r'最低畢業總學分數：(\d+)', page_text)
        if grad_min:
            dept_info["metadata"]["min_graduation_credits"] = int(grad_min.group(1))

        comp_min = re.search(r'規定必修：\s*(\d+)', page_text)
        if comp_min:
            dept_info["metadata"]["compulsory_credits_required"] = int(comp_min.group(1))

        # --- 3. 修課特殊規定 ---
        rules_section = soup.find(string=re.compile("修課特殊規定"))
        if rules_section:
            rules_text = rules_section.find_parent('td').get_text(strip=True)
            dept_info["special_rules"] = [r.strip() for r in rules_text.split('\n') if r.strip()]

        # --- 4. 課程表格 ---
        # 欄位順序（共17欄，index 0-based）：
        # 0  科目名稱
        # 1  修別
        # 2  規定學分
        # 3  學期數
        # 4  一上  5  一下
        # 6  二上  7  二下
        # 8  三上  9  三下
        # 10 四上  11 四下
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

                # 逐學期建立 schedule，True 表示該學期開課
                schedule = {}
                for i, key in enumerate(SCHEDULE_KEYS):
                    schedule[key] = 'ｖ' in cols[4 + i].get_text()

                # suggested_year：取第一個 True 的學年
                suggested_year = 0
                for i, active in enumerate(schedule.values()):
                    if active:
                        suggested_year = i // 2 + 1
                        break

                def clean(val):
                    v = val.get_text(strip=True)
                    return None if v in ('無', '') else v

                course_data = {
                    "name": course_name,
                    "type": cols[1].get_text(strip=True),
                    "credits": int(cols[2].get_text(strip=True)) if cols[2].get_text(strip=True).isdigit() else 0,
                    "semesters": int(cols[3].get_text(strip=True)) if cols[3].get_text(strip=True).isdigit() else 1,
                    "suggested_year": suggested_year,
                    "schedule": schedule,                        # ★ 新增：完整上下學期
                    "recognition": cols[12].get_text(strip=True),
                    "course_code": clean(cols[13]),              # ★ 新增：本系科目代碼
                    "dual_major_recognition": cols[14].get_text(strip=True),  # ★ 新增
                    "dual_major_course_code": clean(cols[15]),   # ★ 新增：雙主修科目代碼
                    "remarks": cols[16].get_text(strip=True) or None
                }
                dept_info["required_courses"].append(course_data)

        # --- 5. 儲存 ---
        clean_name = Path(filename).stem
        save_path = os.path.join(output_folder, f"{clean_name}.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(dept_info, f, ensure_ascii=False, indent=4)

        print(f"✓ 成功解析: {filename}")

    except Exception as e:
        print(f"✗ 處理 {filename} 時發生錯誤: {e}")