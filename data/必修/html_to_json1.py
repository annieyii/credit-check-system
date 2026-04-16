import os
import json
import re
from bs4 import BeautifulSoup

# --- 路徑設定 ---
input_folder = './114/html' 
output_folder = './114/result' 
output_filename = "114_requirements.json"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

all_departments_data = []

print(f"--- 開始批次解析並合併完整資料 ---")

for filename in os.listdir(input_folder):
    if filename.endswith(".html"):
        file_path = os.path.join(input_folder, filename)
        
        # 定義更詳盡的結構
        dept_info = {
            "metadata": {
                "dept_name": "",
                "source_file": filename,
                "min_graduation_credits": 0,    # 畢業總學分
                "major_required_credits": 0      # 專業必修學分
            },
            "special_rules": [],                 # 包含軍訓、體育限制
            "required_courses": []
        }

        try:
            with open(file_path, 'r', encoding='big5', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
                # 1. 抓取系所名稱
                title_tag = soup.find('font', {'face': '標楷體'})
                dept_info["metadata"]["dept_name"] = title_tag.get_text(strip=True) if title_tag else filename.replace(".html", "")

                # 2. 抓取畢業學分門檻與規則 (利用 Regex)
                page_text = soup.get_text()
                grad_min = re.search(r'最低畢業總學分數：(\d+)', page_text)
                if grad_min:
                    dept_info["metadata"]["min_graduation_credits"] = int(grad_min.group(1))
                
                comp_min = re.search(r'規定必修：\s*(\d+)', page_text)
                if comp_min:
                    dept_info["metadata"]["major_required_credits"] = int(comp_min.group(1))

                # 抓取「修課特殊規定」表格內容
                rules_td = soup.find(string=re.compile("修課特殊規定"))
                if rules_td:
                    target_td = rules_td.find_parent('td')
                    if target_td:
                        # 將特殊規定按行切分並清理
                        rules_list = [r.strip() for r in target_td.get_text(strip=True).split('\n') if r.strip()]
                        dept_info["special_rules"] = rules_list

                # 3. 解析課程表格
                # 排除標頭，針對內容列進行解析
                table = soup.find('table', border="1")
                if table:
                    rows = table.find_all('tr')[2:]  # 跳過前兩行標頭
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 11:
                            course_name = cols[0].get_text(strip=True)
                            
                            if course_name and course_name != "無":
                                # 判斷建議修課學年：檢查 v 出現在哪一格 (4-11格對應一到四年級上下)
                                suggested_year = 0
                                for i in range(4, 12):
                                    if 'ｖ' in cols[i].get_text():
                                        suggested_year = (i - 4) // 2 + 1
                                        break
                                
                                dept_info["required_courses"].append({
                                    "name": course_name,
                                    "type": cols[1].get_text(strip=True),
                                    "credit": int(cols[2].get_text(strip=True)) if cols[2].get_text(strip=True).isdigit() else 0,
                                    "semesters": int(cols[3].get_text(strip=True)) if cols[3].get_text(strip=True).isdigit() else 1,
                                    "suggested_year": suggested_year,
                                    "recognition": cols[12].get_text(strip=True), # 系所認定方式
                                    "note": cols[16].get_text(strip=True)        # 備註
                                })
            
            all_departments_data.append(dept_info)
            print(f"解析成功: {dept_info['metadata']['dept_name']}")

        except Exception as e:
            print(f"錯誤檔案 {filename}: {e}")

# 4. 存成大檔案
output_file_path = os.path.join(output_folder, output_filename)
with open(output_file_path, 'w', encoding='utf-8') as f:
    json.dump(all_departments_data, f, ensure_ascii=False, indent=4)

print(f"\n--- 合併完成！共處理 {len(all_departments_data)} 個系所 ---")