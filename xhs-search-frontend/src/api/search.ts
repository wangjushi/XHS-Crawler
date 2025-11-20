import axios from 'axios';
import type { SearchResult, SearchRequest, VideoInfo } from '../types';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const searchComments = async (query: string, top_k: number = 10): Promise<SearchResult[]> => {
  try {
    const response = await api.get('/search', {
      params: {
        q: query,
        top_k: top_k,
      },
    });
    return response.data.results;
  } catch (error) {
    console.error('搜索失败:', error);
    throw error;
  }
};

export const checkHealth = async (): Promise<boolean> => {
  try {
    const response = await api.get('/health');
    return response.data.status === 'ok';
  } catch (error) {
    console.error('健康检查失败:', error);
    return false;
  }
};

export const getVideoInfo = async (videoId: string): Promise<VideoInfo> => {
  try {
    const response = await api.get(`/video/${videoId}`);
    return response.data;
  } catch (error) {
    console.error('获取视频信息失败:', error);
    throw error;
  }
};