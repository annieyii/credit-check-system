<template>
  <div id="app" style="padding: 20px;">
    <h1>畢業審判官 - 檔案上傳系統</h1>
    
    <div style="margin-bottom: 20px;">
      <label>請選擇身分：</label>
      <select v-model="role">
        <option value="general">一般大四學生</option>
        <option value="dual">雙主修/輔系學生</option>
      </select>
    </div>

    <div 
      @dragover.prevent 
      @drop.prevent="handleFileDrop"
      style="border: 2px dashed #ccc; padding: 40px; text-align: center; cursor: pointer;"
      @click="$refs.fileInput.click()"
    >
      <p>拖放 JSON 檔案至此，或點擊上傳</p>
      <input type="file" ref="fileInput" hidden accept=".json" @change="handleFileChange">
    </div>

    <div v-if="previewData" style="margin-top: 20px;">
      <h3>資料預覽：</h3>
      <pre style="background: #f4f4f4; padding: 10px; max-height: 200px; overflow: auto;">{{ previewData }}</pre>
      <button @click="uploadToServer" :disabled="loading">確認並送出分析</button>
    </div>

    <p v-if="loading">分析中，請稍候...</p>
    <p v-if="message" :style="{ color: isError ? 'red' : 'green' }">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const role = ref('general');
const previewData = ref(null);
const loading = ref(false);
const message = ref('');
const isError = ref(false);

// 處理檔案讀取
const processFile = (file) => {
  if (file.type !== "application/json") {
    alert("請上傳 JSON 格式檔案！");
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      previewData.value = JSON.parse(e.target.result);
      message.value = "檔案讀取成功，請確認預覽資料。";
      isError.value = false;
    } catch (err) {
      alert("JSON 格式毀損，請檢查檔案。");
    }
  };
  reader.readAsText(file);
};

const handleFileChange = (e) => processFile(e.target.files[0]);
const handleFileDrop = (e) => processFile(e.dataTransfer.files[0]);

// 前端邏輯與 API 對接
const uploadToServer = async () => {
  loading.value = true;
  message.value = "";
  try {
    const response = await axios.post('http://127.0.0.1:8000/api/v1/analyze', {
      role: role.value,
      data: previewData.value
    });
    message.value = "分析完成：" + response.data.message;
    isError.value = false;
  } catch (error) {
    isError.value = true;
    // 錯誤處理：後端斷線或 400 報錯
    message.value = error.response ? `錯誤：${error.response.data.detail}` : "無法連接到後端伺服器";
  } finally {
    loading.value = false;
  }
};
</script>
