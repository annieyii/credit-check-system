import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "curriculum.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 讀取 schema.sql 並執行
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    
    cursor.executescript(schema)
    conn.commit()
    conn.close()
    print("✅ 資料庫建立完成！路徑：", DB_PATH)

if __name__ == "__main__":
    init_db()