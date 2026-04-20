import json
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()

    try:
        raw_data = json.loads(content)
        return True

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")