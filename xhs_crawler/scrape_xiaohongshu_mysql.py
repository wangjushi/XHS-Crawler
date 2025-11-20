# -*- coding: utf-8 -*-
import os
import time
import re
import yaml
from datetime import datetime, timedelta
import urllib.parse
import pymysql
from playwright.sync_api import sync_playwright, TimeoutError
import requests
import random
import uuid

# ===========================
# 🧩 读取配置文件
# ===========================
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

MYSQL_DB_HOST = config["mysql"]["host"]
MYSQL_DB_PORT = int(config["mysql"]["port"])
MYSQL_DB_USER = config["mysql"]["user"]
MYSQL_DB_PWD = config["mysql"]["password"]
MYSQL_DB_NAME = config["mysql"]["database"]

KEYWORDS = [kw.strip() for kw in config["crawler"]["keywords"].split(",")]
MAX_NOTES_PER_KEYWORD = int(config["crawler"].get("max_notes_per_keyword", 30))
MAX_COMMENTS_PER_NOTE = int(config["crawler"].get("max_comments_per_note", -1))
SCROLL_PAUSE = float(config["crawler"].get("scroll_pause", 2.0))
SCROLL_RETRY = int(config["crawler"].get("scroll_retry", 3))
RANDOM_DELAY_MIN = float(config["crawler"].get("random_delay_min", 1.5))
RANDOM_DELAY_MAX = float(config["crawler"].get("random_delay_max", 4.0))
MAX_RETRIES = int(config["crawler"].get("max_retries", 3))
BATCH_SLEEP_AFTER = int(config["crawler"].get("batch_sleep_after", 10))
BATCH_SLEEP_SEC = int(config["crawler"].get("batch_sleep_sec", 300))
USER_AGENT_ROTATE = bool(config["crawler"].get("user_agent_rotate", True))
PROXY = config["crawler"].get("proxy", "")

# ===========================
# 🧩 数据库操作
# ===========================
def get_conn():
    return pymysql.connect(
        host=MYSQL_DB_HOST,
        port=MYSQL_DB_PORT,
        user=MYSQL_DB_USER,
        password=MYSQL_DB_PWD,
        database=MYSQL_DB_NAME,
        charset="utf8mb4"
    )

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # 笔记表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS xhs_notes (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            note_id VARCHAR(64) NOT NULL,
            title VARCHAR(255),
            node_text TEXT,
            author VARCHAR(255),
            user_id VARCHAR(64),
            publish_time VARCHAR(100),
            url TEXT,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- ✅ 唯一约束：note_id 唯一
            UNIQUE KEY uk_note_id (note_id),
            INDEX idx_author (author),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 评论表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS xhs_comments (
            id VARCHAR(255) PRIMARY KEY,
            note_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(64),
            user_name VARCHAR(255),
            user_url TEXT,
            location VARCHAR(255),
            content TEXT,
            comment_time VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_note_id (note_id),
            INDEX idx_user_id (user_id),
            -- ✅ 联合唯一约束：同一 note_id + content(255) + user_id 不重复
            UNIQUE KEY uk_note_comment_user (note_id, content(255), user_id),
            FOREIGN KEY (note_id) REFERENCES xhs_notes(note_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 用户表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS xhs_users (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(64) UNIQUE,
            user_url TEXT,
            user_name VARCHAR(255),
            user_red_id VARCHAR(255),
            location VARCHAR(255),
            gender VARCHAR(10),
            avatar_url TEXT,
            followers VARCHAR(50),
            following VARCHAR(50),
            likes VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ 数据库结构已初始化（xhs_notes + xhs_comments + xhs_users）")

# ===========================
# 🧩 工具函数（时间、ID解析）
# ===========================
def extract_id_from_url(url: str) -> str | None:
    if url is None or url == "":
        return None
    match = re.search(r'/([^/?]+)(?:\?|$)', url)
    return match.group(1) if match else None
def parse_xiaohongshu_time(time_str: str, now: datetime = None) -> str | None:
    """
    解析小红书各种时间显示格式，统一转为 'YYYY-MM-DD'（或更精确到秒，按需扩展）。
    
    支持格式：
      - "刚刚"
      - "3分钟前"
      - "2小时前"
      - "今天 14:30"
      - "昨天 09:15"
      - "4天前"
      - "10-12"
      - "2024-03-15"
      - "2025-02-14 13:45:22" （兼容）
    
    Args:
        time_str: 原始时间字符串
        now: 参考时间（默认为当前系统时间）
    
    Returns:
        标准 ISO 日期字符串（如 "2025-11-07"），或 None
    """
    if now is None:
        now = datetime.now()
    
    time_str = time_str.strip()
    if not time_str or time_str in ("N/A", "无", "未知"):
        return None

    # 1. 刚刚
    if "刚刚" in time_str:
        return now.strftime("%Y-%m-%d")

    # 2. X分钟前
    min_match = re.match(r'^(\d+)分钟前$', time_str)
    if min_match:
        minutes = int(min_match.group(1))
        dt = now - timedelta(minutes=minutes)
        return dt.strftime("%Y-%m-%d")

    # 3. X小时前
    hour_match = re.match(r'^(\d+)小时前$', time_str)
    if hour_match:
        hours = int(hour_match.group(1))
        dt = now - timedelta(hours=hours)
        return dt.strftime("%Y-%m-%d")

    # 4. 今天 HH:mm[:ss]
    today_match = re.match(r'^今天\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$', time_str)
    if today_match:
        h, m, s = int(today_match.group(1)), int(today_match.group(2)), today_match.group(3)
        s = int(s) if s else 0
        dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
        return dt.strftime("%Y-%m-%d")

    # 5. 昨天 HH:mm[:ss]
    yesterday_match = re.match(r'^昨天\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$', time_str)
    if yesterday_match:
        h, m, s = int(yesterday_match.group(1)), int(yesterday_match.group(2)), yesterday_match.group(3)
        s = int(s) if s else 0
        dt = (now - timedelta(days=1)).replace(hour=h, minute=m, second=s, microsecond=0)
        return dt.strftime("%Y-%m-%d")

    # 6. X天前
    day_match = re.match(r'^(\d+)天前$', time_str)
    if day_match:
        days = int(day_match.group(1))
        dt = now - timedelta(days=days)
        return dt.strftime("%Y-%m-%d")

    # 7. YYYY-MM-DD HH:mm:ss （完整时间）
    full_match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$', time_str)
    if full_match:
        y, mo, d, h, m, s = map(int, full_match.groups()[:5]) + (int(full_match.group(6)) if full_match.group(6) else 0,)
        try:
            dt = datetime(y, mo, d, h, m, s)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 8. YYYY-MM-DD
    ymd_match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', time_str)
    if ymd_match:
        y, mo, d = map(int, ymd_match.groups())
        try:
            dt = datetime(y, mo, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 9. MM-DD （最常见于搜索页）
    md_match = re.match(r'^(\d{1,2})-(\d{1,2})$', time_str)
    if md_match:
        mo, d = map(int, md_match.groups())
        try:
            # 先试今年
            candidate = datetime(now.year, mo, d)
            if candidate > now:
                candidate = datetime(now.year - 1, mo, d)
            return candidate.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 无法识别
    return time_str

def random_wait(base=RANDOM_DELAY_MIN, var=RANDOM_DELAY_MAX):
    delay = base + random.random() * (var - base)
    print(f"⏳ 随机等待 {delay:.2f} 秒...")
    time.sleep(delay)

def with_retry(max_retries=MAX_RETRIES):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"⚠️ {func.__name__} 第 {i+1} 次失败：{e}")
                    time.sleep(3 + i * 2)
            print(f"❌ {func.__name__} 多次失败，跳过。")
            return None
        return wrapper
    return decorator

# ===========================
# 🧩 数据保存函数
# ===========================
def save_note_to_db(note):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT IGNORE INTO xhs_notes (note_id, title, node_text, author, user_id, publish_time, url, keywords)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (note["note_id"], note["title"], note["node_text"], note["author"], note.get("user_id"), note["time"], note["url"], note["keyword"]))
        conn.commit()
    except Exception as e:
        print("❌ 保存笔记失败:", e)
    finally:
        cur.close()
        conn.close()

def save_comments_to_db(note_url, comments):
    conn = get_conn()
    cur = conn.cursor()
    note_id = extract_id_from_url(note_url)
    if not note_id:
        print("⚠️ 无法提取笔记ID，跳过评论保存")
        return
    try:
        ids = []
        for cmt in comments:
            id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO xhs_comments (id, note_id, user_name, content, comment_time, user_id, user_url, location)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (id, note_id, cmt["user"], cmt["content"], cmt["time"], cmt.get("user_id"), cmt.get("user_url"), cmt.get("location")))
            ids.append(id)
        conn.commit()
        for id in ids:
            requests.post("http://127.0.0.1:5000/api/embeddings", json={
                "comment_id": id
            })
        print(f"💾 已新增 {len(comments)} 条评论")
    except Exception as e:
        print("❌ 保存评论失败:", e)
    finally:
        cur.close()
        conn.close()

# ===========================
# 🧩 用户检查与保存
# ===========================
def user_exists(user_id, user_url):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM xhs_users WHERE user_id=%s OR user_url=%s", (user_id, user_url))
    exists = cur.fetchone()[0] > 0
    cur.close()
    conn.close()
    return exists

def save_user_to_db(user):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT IGNORE INTO xhs_users (user_id, user_url, user_name, user_red_id, location, gender, avatar_url, followers, following, likes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            user.get("user_id"), user.get("user_url"), user.get("user_name"), user.get("user_red_id"),
            user.get("location"), user.get("gender"), user.get("avatar_url"),
            user.get("followers"), user.get("following"), user.get("likes")
        ))
        conn.commit()
        print(f"✅ 用户 {user.get('user_name')} 信息已保存")
    except Exception as e:
        print("❌ 保存用户失败:", e)
    finally:
        cur.close()
        conn.close()

# ===========================
# 🧩 爬取用户详情
# ===========================
        
@with_retry()
def scrape_user_detail(context, user_url):
    if not user_url:
        return None

    user_id = extract_id_from_url(user_url)
    if user_exists(user_id, user_url):
        print(f"⏭️ 用户 {user_id} 已存在，跳过")
        return None

    print(f"🧭 正在爬取用户详情: {user_url}")
    page = context.new_page()
    try:
        page.goto(f"https://www.xiaohongshu.com{user_url}", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector(".info", timeout=15000)

        user_name = page.locator(".user-name").inner_text(timeout=5000)
        red_id = page.locator(".user-redId").inner_text(timeout=5000).replace("小红书号：", "").strip() if page.locator(".user-redId").count() else ""
        location = page.locator(".user-IP").inner_text(timeout=5000).replace("IP属地：", "").strip() if page.locator(".user-IP").count() else ""
        #avatar_url = page.locator(".avatar img").get_attribute("src") if page.locator(".avatar img").count() else ""
        gender = "女" if page.locator(".gender use[xlink\\:href='#female']").count() else ("男" if page.locator(".gender use[xlink\\:href='#male']").count() else "")
        counts = page.locator(".user-interactions div span.count").all_inner_texts()
        following, followers, likes = (counts + ["", "", ""])[:3]

        user_data = {
            "user_id": user_id,
            "user_url": user_url,
            "user_name": user_name,
            "user_red_id": red_id,
            "location": location,
            "gender": gender,
            #"avatar_url": avatar_url,
            "followers": followers,
            "following": following,
            "likes": likes,
        }

        save_user_to_db(user_data)
        print(f"✅ 用户详情抓取完成: {user_name} ({user_id})")
        return user_data
    except Exception as e:
        print("❌ 用户详情抓取失败:", e)
        return None
    finally:
        page.close()

# ===========================
# 🧩 爬取笔记与评论
# ===========================
def scrape_keyword(context,page, keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    target_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}"
    print(f"\n🔍 正在搜索: {keyword}")

    try:
        page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector("section.note-item", timeout=20000)
    except Exception as e:
        print("⚠️ 搜索异常:", e)
        input("请手动处理验证码后回车继续 >>> ")

    results = []
    note_items = page.query_selector_all("section.note-item")[:MAX_NOTES_PER_KEYWORD]
    for item in note_items:
        try:
            if item.query_selector("a.cover") is None:
                continue
            title_elem = item.query_selector("a.title span")
            title = title_elem.inner_text().strip() if title_elem else "N/A"
            author_elem = item.query_selector("a.author .name")
            user_url = item.query_selector("a.author").get_attribute("href")
            user_id = extract_id_from_url(user_url)
            author = author_elem.inner_text().strip() if author_elem else "N/A"
            time_elem = item.query_selector("a.author .time")
            post_time = parse_xiaohongshu_time(time_elem.inner_text().strip()) if time_elem else "N/A"
            href = item.query_selector("a.cover").get_attribute("href")
            detail_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
            note_id = extract_id_from_url(href)
            results.append({
                "title": title, "author": author, "time": post_time,
                "url": detail_url, "note_id": note_id, "user_id": user_id, "user_url": user_url, 
                "keyword": keyword
            })
            if user_id and not user_exists(user_id, user_url):
                scrape_user_detail(context, user_url)
        except Exception as e:
            print("❌ 笔记解析失败",e)
            continue
    return results
@with_retry()
def scrape_comments_by_url(context, url):
    print(f"🧭 打开笔记: {url}")
    page = context.new_page()
    comments = []
    node_text = ""
    try:
        page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_selector(".note-scroller", timeout=15000)
        node_text = page.query_selector(".note-text").inner_html()
        attempt = 0
        while True:
            try:
                page.evaluate("document.querySelector('.note-scroller').scrollTo(0, document.querySelector('.note-scroller').scrollHeight)")
                time.sleep(SCROLL_PAUSE + random.random() * 1.5)
            except Exception as e:
                print(f"⚠️ 滚动第 {attempt+1} 次失败: {e}")
                time.sleep(2)
            if page.locator('.end-container').count() or page.locator(".no-comments").count():
                break
        if page.locator(".no-comments").count():
            return node_text,[]
        elems = page.query_selector_all(".comment-item")
        for el in elems:
            user_elem = el.query_selector("a.name")
            href = user_elem.get_attribute("href") if user_elem else None
            user_url = f"https://www.xiaohongshu.com{href}" if href and href.startswith("/") else None
            user_id = extract_id_from_url(href)
            content_elem = el.query_selector(".content ")
            time_elem = el.query_selector(".date span:not(.location)")
            location_elem = el.query_selector(".date .location")
            time_str = parse_xiaohongshu_time(time_elem.inner_text().strip()) if time_elem else ""
            comments.append({
                "user": user_elem.inner_text().strip() if user_elem else "匿名",
                "content": content_elem.inner_text().strip() if content_elem else "",
                "location": location_elem.inner_text().strip() if location_elem else "",
                "time": time_str,
                "user_id": user_id,
                "user_url": user_url
            })
            if user_id and not user_exists(user_id, user_url):
                scrape_user_detail(context, href)
    except Exception as e:
        print("❌ 评论抓取失败:", e)
    finally:
        page.close()
    return node_text,comments

# ---------- 辅助：安全的查询器 ----------
def safe_query_selector(page, selector: str, wait_timeout: int = 2500, retries: int = 2):
    """
    尝试等待并查询元素，自动捕获因导航导致的执行上下文销毁错误。
    返回 page.query_selector(...) 或 None（失败时）。
    wait_timeout: 等待选择器的超时(ms)
    retries: 出错后的重试次数
    """
    for attempt in range(retries + 1):
        try:
            # 先尝试等待元素出现（短超时），有时 wait_for_selector 会在导航中失败 -> 捕获
            page.wait_for_selector(selector, timeout=wait_timeout)
            return page.query_selector(selector)
        except Exception:
            # 可能因为导航、重渲染或执行上下文被替换导致失败，短暂 sleep 后重试
            time.sleep(0.3)
            try:
                # 最后再尝试直接 query（若上下文稳定则可能成功）
                return page.query_selector(selector)
            except Exception:
                time.sleep(0.2)
                continue
    return None

def safe_query_selector_text(page, selector: str, wait_timeout: int = 2500, default: str = "") -> str:
    el = safe_query_selector(page, selector, wait_timeout=wait_timeout)
    try:
        return el.inner_text().strip() if el else default
    except Exception:
        return default

# ---------- 在 main() 中使用更稳健的登录检测 ----------
def main():
    init_db()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="./xhs_profile",
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",  # 去除自动化特征
                "--disable-infobars",
                "--start-maximized",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-position=0,0",
            ],
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        )


        # 获取或创建第一页
        page = context.pages[0] if context.pages else context.new_page()

        # 更稳健地打开首页并等待基本载入（等待 load 状态）
        try:
            page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """)

            page.goto("https://www.xiaohongshu.com", timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as e:
            print("⚠️ 访问小红书首页时发生异常（但程序继续）：", e)

        # 使用 safe_query_selector 检查登录状态（避免 Execution context 错误）
        try:
            avatar_el = safe_query_selector(page, "div.user-avatar", wait_timeout=2000)
            name_el = safe_query_selector(page, "span.name", wait_timeout=2000)
            if not avatar_el and not name_el:
                print("⚠️ 请手动扫码登录小红书...")
                # 等待用户手动登录：这里也用 loop 检测登录成功，避免 query_selector 导致 error
                while True:
                    input("扫码登录完成后按回车继续 >>> ")
                    # 重新加载当前页面的 DOM 并检测
                    try:
                        page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        window.navigator.chrome = { runtime: {} };
                        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        """)
                        page.goto("https://www.xiaohongshu.com", timeout=20000)
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    avatar_el = safe_query_selector(page, "div.user-avatar", wait_timeout=2000)
                    name_el = safe_query_selector(page, "span.name", wait_timeout=2000)
                    if avatar_el or name_el:
                        print("✅ 已检测到登录状态，继续爬取")
                        break
                    else:
                        print("仍未检测到登录，请确认已完成扫码并刷新页面后重试。")
            else:
                print("✅ 已检测到登录状态")
        except Exception as e:
            # 兜底：如果检测过程仍然抛出了异常，打印并继续，让后续逻辑更安全
            print("⚠️ 登录检测过程中捕获异常（继续执行）:", e)

        # 主循环：爬关键词
        for keyword in KEYWORDS:
            try:
                notes = scrape_keyword(context,page, keyword)
            except Exception as e:
                print(f"⚠️ scrape_keyword 出错（跳过该关键词）：{keyword} -> {e}")
                continue

            for i, note in enumerate(notes, 1):
                if i % BATCH_SLEEP_AFTER == 0:
                    print(f"😴 达到 {BATCH_SLEEP_AFTER} 篇，休息 {BATCH_SLEEP_SEC} 秒以防风控...")
                    time.sleep(BATCH_SLEEP_SEC)
                try:
                    node_text,comments = scrape_comments_by_url(context, note["url"])
                    note["node_text"] = node_text
                    save_note_to_db(note)
                    if comments:
                        save_comments_to_db(note["url"], comments)
                except Exception as e:
                    print(f"⚠️ 处理笔记 {note.get('url')} 时出错：", e)

        context.close()

if __name__ == "__main__":
    main()
