# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from text2vec import SentenceModel
import faiss
import numpy as np
import pymysql
import os

app = Flask(__name__)

# ===============================
# 🔹 使用更强的中文语义模型
# ===============================
# 可选："shibing624/text2vec-large-chinese" 或 "BAAI/bge-large-zh-v1.5"
model = SentenceModel("BAAI/bge-large-zh-v1.5")
VECTOR_DIM = 1024  # bge-large 输出 1024 维
INDEX_PATH = "vector_store.faiss"

# ===============================
# 🔹 MySQL 配置
# ===============================
MYSQL_CONFIG = {
    "host": "192.168.0.200",
    "port": 3306,
    "user": "root",
    "password": "pt9r2HKeo3QBvpMa",
    "database": "xiaohongshu",
    "charset": "utf8mb4"
}

# ===============================
# 🔹 初始化 FAISS 索引（改为内积）
# ===============================
if os.path.exists(INDEX_PATH):
    index = faiss.read_index(INDEX_PATH)
    print("✅ 已加载现有向量索引")
else:
    # 改为内积索引（cosine similarity）
    index = faiss.IndexFlatIP(VECTOR_DIM)
    print("🆕 创建新向量索引（余弦相似度）")

# comment_id 映射
ID_MAP_PATH = "id_map.npy"
if os.path.exists(ID_MAP_PATH):
    id_map = np.load(ID_MAP_PATH, allow_pickle=True).tolist()
else:
    id_map = []

# ===============================
# 📥 工具函数：向量归一化
# ===============================
def normalize(vecs):
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


# ===============================
# 📥 初始化向量
# ===============================
@app.route("/api/init", methods=["POST"])
def init_embeddings():
    global index, id_map

    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT id, content FROM xhs_comments WHERE content IS NOT NULL AND content != ''")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"msg": "数据库中没有可用评论"}), 400

    texts = [r[1] for r in rows]
    ids = [r[0] for r in rows]

    vectors = model.encode(texts, normalize_embeddings=True)  # ✅ 自动归一化
    vectors = np.array(vectors).astype("float32")

    index = faiss.IndexFlatIP(VECTOR_DIM)
    index.add(vectors)
    faiss.write_index(index, INDEX_PATH)

    id_map = ids
    np.save(ID_MAP_PATH, np.array(id_map, dtype=object))

    return jsonify({"msg": f"已初始化 {len(rows)} 条评论向量"})


# ===============================
# 📥 保存单条评论向量
# ===============================
@app.route("/api/embeddings", methods=["POST"])
def save_embedding():
    global id_map

    data = request.get_json()
    comment_id = data.get("comment_id")
    if not comment_id:
        return jsonify({"error": "缺少 comment_id"}), 400

    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM xhs_comments WHERE id = %s", (comment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"未找到ID为 {comment_id} 的评论"}), 404

    content = row[0]
    if not content.strip():
        return jsonify({"error": "评论内容为空"}), 400

    vector = model.encode([content], normalize_embeddings=True)
    vector_np = np.array(vector).astype("float32")
    index.add(vector_np)
    faiss.write_index(index, INDEX_PATH)

    id_map.append(comment_id)
    np.save(ID_MAP_PATH, np.array(id_map, dtype=object))

    return jsonify({"msg": "评论向量已保存", "comment_id": comment_id})


# ===============================
# 🔍 搜索接口（余弦相似度）
# ===============================
@app.route("/api/search", methods=["GET"])
def search():
    query = request.args.get("q", "")
    top_k = int(request.args.get("top_k", 10))
    if not query.strip():
        return jsonify({"error": "缺少参数 q"}), 400

    if index.ntotal == 0:
        return jsonify({"error": "没有向量索引，请先初始化或添加"}), 400

    q_vec = model.encode([query], normalize_embeddings=True)
    q_vec = np.array(q_vec).astype("float32")

    D, I = index.search(q_vec, top_k)

    results = []
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    for score, idx in zip(D[0], I[0]):
        if idx >= len(id_map):
            continue
        comment_id = id_map[idx]
        cursor.execute(
            """
            SELECT
                xn.note_id AS note_id,
                xn.title AS note_title,
                xn.node_text AS note_content,
                xn.publish_time AS note_publish_time,
                xcu.user_name   AS commenter_name,
                xcu.user_red_id AS commenter_red_id,
                xcu.location    AS commenter_location,
                xnu.user_name   AS author_name,
                xnu.user_red_id AS author_red_id,
                xnu.location    AS author_location,
                xc.content      AS comment_content,
                xc.comment_time AS comment_time,
                xc.id           AS comment_id
            FROM xhs_comments xc
            LEFT JOIN xhs_notes xn ON xc.note_id = xn.note_id 
            LEFT JOIN xhs_users xcu ON xc.user_id = xcu.user_id 
            LEFT JOIN xhs_users xnu ON xn.user_id = xnu.user_id 
            WHERE xc.id = %s
            """,
            (comment_id,)
        )
        row = cursor.fetchone()
        if row:
            results.append({
                "note_id": row[0],
                "note_title": row[1],
                "note_content": row[2],
                "publish_time": row[3],
                "commenter_name": row[4],
                "commenter_red_id": row[5],
                "commenter_location": row[6],
                "author_name": row[7],
                "author_red_id": row[8],
                "author_location": row[9],
                "comment_content": row[10],
                "comment_time": row[11],
                "comment_id": row[12],
                "similarity": float(score)
            })
    conn.close()

    results = sorted(results, key=lambda x: x["similarity"], reverse=True)
    return jsonify({"query": query, "results": results})


# ===============================
# 🧹 重置接口
# ===============================
@app.route("/api/reset", methods=["POST"])
def reset():
    global index, id_map
    index = faiss.IndexFlatIP(VECTOR_DIM)
    id_map = []
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)
    if os.path.exists(ID_MAP_PATH):
        os.remove(ID_MAP_PATH)
    return jsonify({"msg": "已清空向量索引"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
