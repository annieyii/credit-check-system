# 畢業學分檢核系統 - 畢業審判官

這是一個針對大學生（特別是雙主修與輔系生）設計的畢業學分自動檢核系統。透過解析成績單數據，提供精確的畢業資格分析與修課建議。

## 📂 目錄結構說明

本專案採用前後端分離架構：

- **/backend**: 使用 Python FastAPI 實作的核心邏輯層。
  - `main.py`: API 入口與路由設定。
  - `requirements.txt`: Python 套件依賴清單。
- **/frontend**: 使用 Vue.js (Vite) 實作的使用者介面。
  - `src/App.vue`: 主要檢核頁面邏輯。
  - `package.json`: 前端套件依賴清單。
- **.gitignore**: 排除 node_modules 與 Python 快取等不必要檔案。

## 快速啟動

### 後端 (Backend)
1. 進入目錄：`cd backend`
2. 安裝套件：`pip install -r requirements.txt`
3. 啟動伺服器：`uvicorn main:app --reload` (預設啟動於 http://127.0.0.1:8000)

### 前端 (Frontend)
1. 進入目錄：`cd frontend`
2. 安裝套件：`npm install`
3. 啟動開發伺服器：`npm run dev`

## Sprint 1 開發重點
- [ ] 實作 JSON 檔案拖放與上傳介面。
- [ ] 建立前後端 API 串接 (Axios to FastAPI)。
- [ ] 實作基礎 JSON 預覽與資料預檢邏輯。
- [ ] 處理異常狀態提醒（格式錯誤、連線失敗）。

## 開發規範
1. **禁止直接推送到 `main` 分支**。
2. 開發新功能請建立新分支：`git checkout -b feat/功能名稱`。
3. 完成後提交 **Merge Request (MR)** 並指派給 PM 進行 Code Review。
