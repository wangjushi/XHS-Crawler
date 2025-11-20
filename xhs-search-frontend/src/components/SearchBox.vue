<template>
  <div class="search-box">
    <div class="search-header">
      <h1>小红书评论语义搜索</h1>
      <div class="search-controls">
        <div class="search-input-group">
          <input
            v-model="query"
            type="text"
            placeholder="输入关键词搜索评论..."
            @keyup.enter="handleSearch"
            class="search-input"
          />
          <button @click="handleSearch" :disabled="loading" class="search-button">
            {{ loading ? '搜索中...' : '搜索' }}
          </button>
        </div>
        <div class="search-options">
          <label>
            结果数量:
            <select v-model="top_k" class="select-input">
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="500">500</option>
            </select>
          </label>
        </div>
      </div>
    </div>
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { SearchResult } from '../types';

interface Emits {
  (e: 'search', query: string, top_k: number): void;
  (e: 'results', results: SearchResult[]): void;
  (e: 'error', error: string): void;
}

const emit = defineEmits<Emits>();

const query = ref('');
const top_k = ref(50);
const loading = ref(false);
const error = ref('');

const handleSearch = async () => {
  if (!query.value.trim()) {
    error.value = '请输入搜索关键词';
    return;
  }

  loading.value = true;
  error.value = '';
  
  try {
    emit('search', query.value, top_k.value);
  } catch (err) {
    error.value = '搜索失败，请检查网络连接';
    emit('error', error.value);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.search-box {
  margin-bottom: 20px;
}

.search-header {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.search-header h1 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 24px;
}

.search-controls {
  display: flex;
  gap: 20px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.search-input-group {
  flex: 1;
  min-width: 300px;
  display: flex;
  gap: 10px;
}

.search-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #007bff;
}

.search-button {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.search-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.search-button:hover:not(:disabled) {
  background: #0056b3;
}

.search-options {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.error-message {
  color: #dc3545;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
}
</style>