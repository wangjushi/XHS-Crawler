<template>
  <div class="comment-list">
    <div class="list-header">
      <h3>搜索结果 ({{ results.length }})</h3>
      <div class="sort-options">
        <label>
          排序:
          <select v-model="sortBy" class="select-input">
            <option value="similarity">相关性</option>
            <!-- <option value="like_count">点赞数</option> -->
            <option value="create_time">时间</option>
          </select>
        </label>
      </div>
    </div>
    
    <div v-if="results.length === 0" class="empty-state">
      <div class="empty-icon">🔍</div>
      <p>暂无搜索结果</p>
      <small>输入关键词搜索相关评论</small>
    </div>
    
    <div v-else class="comments-container">
      <div
        v-for="comment in sortedResults"
        :key="comment.comment_id"
        class="comment-item"
        :class="{ active: comment.comment_id === selectedCommentId }"
        @click="selectComment(comment)"
      >
        <div class="comment-header">
          <span class="nickname">{{ comment.commenter_name }}</span>
          <span class="similarity">匹配度: {{ (comment.similarity * 100 ).toFixed(1) }} %</span>
        </div>
        
        <div class="comment-content">
          {{ comment.comment_content }}
        </div>
        
        <div class="comment-footer">
          <!-- <span class="likes">❤️ {{ comment.like_count }}</span> -->
          <span class="time">{{ comment.comment_time }}</span>
          <!-- <span class="video-id">视频: {{ comment.aweme_id }}</span> -->
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SearchResult, VideoInfo } from '../types';
import { computed, ref } from 'vue';

interface Props {
  results: SearchResult[];
  selectedCommentId?: string;
}

interface Emits {
  (e: 'select', comment: SearchResult): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const sortBy = ref<'similarity' | 'like_count' | 'create_time'>('similarity');

const sortedResults = computed(() => {
  return [...props.results].sort((a, b) => {
    if (sortBy.value === 'similarity') {
      return b.similarity - a.similarity;
    } else if (sortBy.value === 'like_count') {
      //return b.like_count - a.like_count;
      return 0;
    } else {
      //return new Date(b.create_time).getTime() - new Date(a.create_time).getTime();
      return 0;
    }
  });
});

const selectComment = (comment: SearchResult) => {
  emit('select', comment);
};


/**
 * 将时间戳转换为可读的日期时间格式
 * @param {number} timestamp - 时间戳（秒级）
 * @param {string} format - 输出格式，可选值：'full', 'date', 'time', 'custom'
 * @param {string} timezone - 时区，默认使用本地时区
 * @returns {string} 格式化后的日期时间字符串
 */
 const formatTimestamp = (timestamp:number, format = 'full', timezone = 'local') => {
  // 将秒级时间戳转换为毫秒级
  const date = new Date(timestamp * 1000);
  
  // 检查时间戳是否有效
  if (isNaN(date.getTime())) {
    return '无效的时间戳';
  }
  
  // 根据时区处理
  let options = {};
  if (timezone !== 'local') {
    options.timeZone = timezone;
  }
  
  // 根据格式返回不同的字符串
  switch (format) {
    case 'full':
      options = {
        ...options,
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      };
      return date.toLocaleString('zh-CN', options);
      
    case 'date':
      options = {
        ...options,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      };
      return date.toLocaleDateString('zh-CN', options);
      
    case 'time':
      options = {
        ...options,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      };
      return date.toLocaleTimeString('zh-CN', options);
      
    case 'custom':
      // 自定义格式：YYYY-MM-DD HH:mm:ss
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
      
    default:
      return date.toLocaleString('zh-CN', options);
  }
}

/**
 * 获取时间戳的详细信息
 * @param {number} timestamp - 时间戳（秒级）
 * @returns {object} 包含详细时间信息的对象
 */
const getTimestampDetails = (timestamp:number) => {
  const date = new Date(timestamp * 1000);
  
  if (isNaN(date.getTime())) {
    return { error: '无效的时间戳' };
  }
  
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
  const months = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'];
  
  return {
    timestamp: timestamp,
    date: date,
    year: date.getFullYear(),
    month: date.getMonth() + 1,
    day: date.getDate(),
    weekday: weekdays[date.getDay()],
    hours: date.getHours(),
    minutes: date.getMinutes(),
    seconds: date.getSeconds(),
    isoString: date.toISOString(),
    localeString: date.toLocaleString('zh-CN'),
    chineseDate: `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`,
    chineseTime: `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`,
    monthName: months[date.getMonth()]
  };
}

</script>

<style scoped>
.comment-list {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.list-header h3 {
  margin: 0;
  color: #333;
}

.sort-options {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-input {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px 20px;
  color: #6c757d;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.comments-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.comment-item {
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.comment-item:hover {
  border-color: #007bff;
  box-shadow: 0 2px 4px rgba(0, 123, 255, 0.1);
}

.comment-item.active {
  border-color: #007bff;
  background: #f8f9fa;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.nickname {
  font-weight: bold;
  color: #495057;
}

.similarity {
  font-size: 12px;
  color: #28a745;
  background: #d4edda;
  padding: 2px 6px;
  border-radius: 10px;
}

.comment-content {
  line-height: 1.5;
  color: #212529;
  margin-bottom: 10px;
}

.comment-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6c757d;
}

.likes {
  color: #dc3545;
}
</style>