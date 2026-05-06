import sqlite3

def sync_cs_requirements():
    conn = sqlite3.connect('curriculum.db')
    cursor = conn.cursor()
    
    # 找出所有年度的資訊科學系 ID
    cursor.execute("SELECT id, applicable_year FROM departments WHERE dept_name LIKE '資訊科學系%'")
    depts = cursor.fetchall()
    
    for dept_id, year in depts:
        # 插入資科系通識規則：28學分、國英12、三向度各3
        cursor.execute("""
            INSERT INTO general_education_requirements 
            (department_id, total_required, compulsory_lang, min_humanities, min_social, min_natural)
            VALUES (?, 28, 12, 3, 3, 3)
        """, (dept_id,))
        print(f"已同步：資訊科學系 {year} 年度門檻")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    sync_cs_requirements()