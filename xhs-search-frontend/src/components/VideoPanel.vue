<template>
  <div class="video-panel">
    <div v-if="selectedComment?.note_content" class="video-detail">
      <div class="video-header">
        <h3>内容</h3>
        <span class="video-id">视频来源关键词: 暂无</span>
      </div>
      <div class="video-content">
        <!-- 视频封面/播放器 -->
        <div class="video-player">
          <!-- <div
            v-if="!selectedVideo.video_download_url"
            class="video-placeholder"
          >
            <span class="video-icon">🎬</span>
            <p>视频预览</p>
            <small>暂无视频</small>
          </div> -->
          <!--嵌入一个视频播放器-->
          <!-- <div v-else class="video-player">
            <video
              controls
              :src="videoUrl"
              style="max-width: 100%; height: auto"
              @loadeddata="onVideoLoaded"
              @error="onVideoError"
            >
              您的浏览器不支持视频播放
            </video>
          </div> -->
          <div v-html="selectedComment.note_content"></div>
        </div>

        <!-- 视频信息 -->
        <div class="video-info">
          <div class="info-item">
            <strong>作者:</strong>
            <!-- <span
              style="color: blue; cursor: pointer"
              @click="openUser(selectedVideo.sec_uid)"
              >{{ selectedVideo.nickname || "未知用户" }}</span
            > -->
            <span style="color: blue; cursor: pointer">{{
              selectedComment.author_name
            }}</span>
          </div>
          <div class="info-item">
            <strong>小红书ID:</strong>
            <span>{{ selectedComment.author_red_id }}</span>
          </div>
          <div class="info-item">
            <strong>标题:</strong>
            <span>{{ selectedComment.note_title || "无标题" }}</span>
          </div>
          <div class="info-item">
            <strong>位置:</strong>
            <span>{{ selectedComment.author_location || "无位置" }}</span>
          </div>
          <div class="info-item">
            <strong>发布时间:</strong>
            <span>{{ selectedComment.publish_time }}</span>
          </div>
        </div>
      </div>

      <div class="comments-user" v-if="selectedComment">
        <h4>评论用户</h4>
        <div class="info-item">
          <strong>用户:</strong>
          <!-- <span
              style="color: blue; cursor: pointer"
              @click="openUser(selectedComment.sec_uid)"
              >{{ selectedComment.nickname || "未知用户" }}</span
            > -->
          <span style="color: blue; cursor: pointer">{{
            selectedComment.commenter_name
          }}</span>
        </div>
        <div class="info-item">
          <strong>小红书ID:</strong>
          <span>{{ selectedComment.commenter_red_id }}</span>
        </div>
        <div class="info-item">
          <strong>评论内容:</strong>
          <span>{{ selectedComment.comment_content }}</span>
        </div>
        <div class="info-item">
          <strong>位置:</strong>
          <span>{{ selectedComment.commenter_location || "无位置" }}</span>
        </div>
      </div>
    </div>

    <div v-else class="video-placeholder">
      <div class="placeholder-content">
        <span class="placeholder-icon">📺</span>
        <p>选择一条评论查看相关内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { VideoInfo, SearchResult } from "../types";
import { ref, watch } from "vue";

interface Props {
  //selectedVideo?: VideoInfo;
  //relatedComments: SearchResult[];
  selectedComment: SearchResult | null;
}

const props = defineProps<Props>();
const videoUrl = ref("");

// 监听 selectedComment 的变化，根据 aweme_id 构建视频URL
// watch(
//   () => props.selectedComment,
//   (newComment) => {
//     if (newComment?.aweme_id) {
//       // 使用 aweme_id 构建视频代理URL
//       videoUrl.value = `http://192.168.0.200:8000/proxy/video/${newComment.aweme_id}`;
//       console.log('视频URL更新:', videoUrl.value);
//     } else {
//       videoUrl.value = "";
//     }
//   },
//   { immediate: true }
// );

const openUser = (uid: string) => {
  window.open(`https://www.douyin.com/user/${uid}`, "_blank");
};

const onVideoLoaded = () => {
  console.log("视频加载成功");
};

const onVideoError = (e: Event) => {
  console.error("视频加载失败:", e);
  // 可以在这里添加错误处理，比如显示错误信息或备用方案
};
</script>

<style scoped>
/* 您的样式保持不变 */
.video-panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 100%;
  overflow-y: auto;
}

.video-detail {
  padding: 20px;
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.video-header h3 {
  margin: 0;
  color: #333;
}

.video-id {
  color: #666;
  font-size: 12px;
  background: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
}

.video-content {
  margin-bottom: 20px;
}

.video-player {
  margin-bottom: 15px;
}

.video-placeholder {
  background: #f8f9fa;
  border: 2px dashed #dee2e6;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  color: #6c757d;
}

.video-placeholder .video-icon {
  font-size: 48px;
  margin-bottom: 10px;
  display: block;
}

.video-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
}

.info-item strong {
  min-width: 80px;
  color: #495057;
}

.info-item span {
  color: #212529;
}

.comments-user h4 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
}

.placeholder-content {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
}

.placeholder-icon {
  font-size: 48px;
  margin-bottom: 15px;
  display: block;
}
</style>
