from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 這是為了讓你的 Vue 網頁能連上 API，非常重要！
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "畢業審判官 API 已啟動"}

@app.post("/api/v1/analyze")
async def analyze_json(data: dict):
    # 這裡之後會放解析邏輯
    return {"status": "received", "data_summary": "已收到 JSON 資料"}
