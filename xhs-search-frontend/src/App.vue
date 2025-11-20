<template>
  <div class="app">
    <div class="container">
      <!-- 搜索框 -->
      <SearchBox
        @search="handleSearch"
        @results="handleResults"
        @error="handleError"
      />
      
      <!-- 主要内容区域 -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>搜索中...</p>
      </div>
      
      <div v-else-if="error" class="error">
        <div class="error-icon">⚠️</div>
        <h3>搜索失败</h3>
        <p>{{ error }}</p>
        <button @click="clearError" class="retry-button">重试</button>
      </div>
      
      <div v-else-if="searchResults.length > 0" class="main-content">
        <div class="layout">
          <!-- 左侧：评论列表 -->
          <div class="left-panel">
            <CommentList
              :results="searchResults"
              :selected-comment-id="selectedComment?.comment_id"
              @select="handleCommentSelect"
            />
          </div>
          
          <!-- 右侧：视频信息 -->
          <div class="right-panel">
            <VideoPanel
              :selected-comment="selectedComment"
            />
          </div>
        </div>
      </div>
      
      <!-- 初始状态 -->
      <div v-else class="welcome">
        <div class="welcome-content">
          <h2>小红书评论语义搜索</h2>
          <p>输入关键词搜索相关评论，点击评论查看对应视频信息</p>
          <div class="features">
            <div class="feature">
              <span class="feature-icon">🔍</span>
              <h4>语义搜索</h4>
              <p>基于AI理解搜索意图，而非简单关键词匹配</p>
            </div>
            <div class="feature">
              <span class="feature-icon">💬</span>
              <h4>评论分析</h4>
              <p>查看评论内容、用户信息和互动数据</p>
            </div>
            <div class="feature">
              <span class="feature-icon">🎬</span>
              <h4>笔记关联</h4>
              <p>快速定位评论所属的笔记内容</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import SearchBox from './components/SearchBox.vue';
import CommentList from './components/CommentList.vue';
import VideoPanel from './components/VideoPanel.vue';
import { searchComments,getVideoInfo } from './api/search';
import type { SearchResult, VideoInfo } from './types';

const loading = ref(false);
const error = ref('');
const searchResults = ref<SearchResult[]>([]);
const selectedComment = ref<SearchResult | null>(null);
const selectedVideo = ref<VideoInfo | null>(null);

// 处理搜索
const handleSearch = async (query: string, top_k: number) => {
  loading.value = true;
  error.value = '';
  selectedComment.value = null;
  
  try {
    const results = await searchComments(query, top_k);
    searchResults.value = results;
  } catch (err) {
    error.value = '搜索失败，请检查网络连接或稍后重试';
    searchResults.value = [];
  } finally {
    loading.value = false;
  }
};
//获取视频
const handleVideoInfo = async (videoId: string) => {
  loading.value = true;
  error.value = '';
  selectedVideo.value = null;
  try {
    const videoInfo = await getVideoInfo(videoId);
    selectedVideo.value = videoInfo;
  } catch (err) {
    error.value = '获取视频信息失败，请检查网络连接或稍后重试';
    selectedVideo.value = null;
  } finally {
    loading.value = false;
  }
}

// 处理结果
const handleResults = (results: SearchResult[]) => {
  searchResults.value = results;
};

// 处理错误
const handleError = (err: string) => {
  error.value = err;
};

// 清除错误
const clearError = () => {
  error.value = '';
};

// 处理评论选择
const handleCommentSelect = (comment: SearchResult) => {
  selectedComment.value = comment;
  //handleVideoInfo(comment.aweme_id);
};


// 相关评论（同一视频的评论）
// const relatedComments = computed(() => {
//   if (!selectedComment.value) return [];
  
//   const currentAwemeId = selectedComment.value.aweme_id;
//   return searchResults.value.filter(
//     comment => comment.aweme_id === currentAwemeId
//   );
// });
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f8f9fa;
  color: #333;
  line-height: 1.6;
}

.app {
  min-height: 100vh;
  padding: 20px;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
}

.loading {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  text-align: center;
  padding: 60px 20px;
  color: #dc3545;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.retry-button {
  margin-top: 20px;
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-button:hover {
  background: #0056b3;
}

.main-content {
  margin-top: 20px;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
  height: calc(100vh - 200px);
}

.left-panel {
  min-height: 600px;
}

.right-panel {
  min-height: 600px;
}

.welcome {
  text-align: center;
  padding: 60px 20px;
}

.welcome-content h2 {
  margin-bottom: 15px;
  color: #333;
}

.welcome-content p {
  color: #666;
  margin-bottom: 40px;
  font-size: 16px;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  max-width: 800px;
  margin: 0 auto;
}

.feature {
  padding: 30px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  font-size: 36px;
  margin-bottom: 15px;
  display: block;
}

.feature h4 {
  margin-bottom: 10px;
  color: #333;
}

.feature p {
  color: #666;
  font-size: 14px;
}

@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .right-panel {
    height: 500px;
  }
  
  .features {
    grid-template-columns: 1fr;
  }
}
</style>