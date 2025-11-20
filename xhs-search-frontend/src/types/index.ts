export interface SearchResult {
  note_id: string;
  note_title: string;
  note_content: string;
  publish_time: string; // 或可转为 Date，但原始数据通常是字符串如 "2025-03-10"
  commenter_name: string;
  commenter_red_id: string;
  commenter_location: string;
  author_name: string;
  author_red_id: string;
  author_location: string;
  comment_content: string;
  comment_time: string; // 同上，通常为格式化后的时间字符串
  similarity: number;
  comment_id: string;
}

export interface SearchRequest {
  query: string;
  top_k: number;
}

export interface VideoInfo {
  sec_uid: string;
  nickname: string;
  title: string;
  desc: string;
  create_time: number;
  video_download_url: string | undefined;
  source_keyword: string;
}