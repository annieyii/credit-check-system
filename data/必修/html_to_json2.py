import os
import json
import re
from bs4 import BeautifulSoup
from pathlib import Path

input_folder = './114/html' 
output_folder = './114/result' 

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

for filename in os.listdir(input_folder):
    if filename.endswith(".html"):
        file_path = os.path.join(input_folder, filename)
        
        # 初始化更完整的結構
        dept_info = {
            "metadata": {
                "source_file": filename,
                "dept_name": "",
                "applicable_year": "114", # 預設年度
                "min_graduation_credits": 0,
                "compulsory_credits_required": 0
            },
            "required_courses": [],
            "special_rules": []
        }

        try:
            with open(file_path, 'r', encoding='big5', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
                # --- 1. 解析標題與系名 ---
                title_tag = soup.find('font', {'face': '標楷體'})
                if title_tag:
                    dept_info["metadata"]["dept_name"] = title_tag.get_text(strip=True)
                
                # --- 2. 解析畢業學分與備註 ---
                page_text = soup.get_text()
                # 抓取「最低畢業總學分數：128學分」
                grad_min = re.search(r'最低畢業總學分數：(\d+)', page_text)
                if grad_min:
                    dept_info["metadata"]["min_graduation_credits"] = int(grad_min.group(1))
                
                # 抓取「規定必修：51學分」
                comp_min = re.search(r'規定必修：\s*(\d+)', page_text)
                if comp_min:
                    dept_info["metadata"]["compulsory_credits_required"] = int(comp_min.group(1))

                # 抓取「修課特殊規定」
                rules_section = soup.find(string=re.compile("修課特殊規定"))
                if rules_section:
                    rules_text = rules_section.find_parent('td').get_text(strip=True)
                    # 簡單切分規則
                    dept_info["special_rules"] = [r.strip() for r in rules_text.split('\n') if r.strip()]

                # --- 3. 精確解析課程表格 ---
                # 尋找包含課程的表格
                table = soup.find('table', border="1")
                if table:
                    rows = table.find_all('tr')[2:]  # 跳過前兩列標頭
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 11:
                            # 判定建議修課學年
                            suggested_year = 0
                            for i in range(4, 12): # 對應第一到第四學年的上下學期
                                if 'ｖ' in cols[i].get_text():
                                    suggested_year = (i - 4) // 2 + 1
                                    break
                            
                            course_name = cols[0].get_text(strip=True)
                            if course_name and course_name != "無":
                                course_data = {
                                    "name": course_name,
                                    "type": cols[1].get_text(strip=True),
                                    "credits": int(cols[2].get_text(strip=True)) if cols[2].get_text(strip=True).isdigit() else 0,
                                    "semesters": int(cols[3].get_text(strip=True)) if cols[3].get_text(strip=True).isdigit() else 1,
                                    "suggested_year": suggested_year,
                                    "recognition": cols[12].get_text(strip=True), # 本系認定方式
                                    "remarks": cols[16].get_text(strip=True)      # 備註
                                }
                                dept_info["required_courses"].append(course_data)
                
                # --- 4. 儲存 ---
                clean_name = Path(filename).stem
                save_path = os.path.join(output_folder, f"{clean_name}.json")
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(dept_info, f, ensure_ascii=False, indent=4)
                
                print(f"成功解析: {filename}")

        except Exception as e:
            print(f"處理 {filename} 時發生錯誤: {e}")