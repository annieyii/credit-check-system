import sqlite3
import pytest

SCHEMA_PATH = "db/database/schema.sql"


@pytest.fixture
def temp_db():
    """每個測試用獨立的記憶體 DB，測完自動丟棄"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()
