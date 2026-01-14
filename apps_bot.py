# -*- coding: utf-8 -*-
import os, random, markdown as md
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import backoff
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_play_scraper import search as play_search, app as play_app

# =================== إعدادات المستخدم ===================
MONETAG_DIRECT_LINK = "https://otieu.com/4/10464710" # رابطك الربحي
APP_LABELS = ["apps", "أدوات", "تطبيقات_اندرويد"] # التسميات الجديدة

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
HISTORY_APPS_FILE = "history_apps.txt"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

SEARCH_QUERIES = [
    "AI Tools", "Productivity", "Photo Editor", "Video Editor", 
    "VPN", "Security", "Scanner", "PDF Tools", "Health", 
    "Education", "Learn Languages", "Finance Manager", 
    "File Manager", "Battery Saver", "Launcher", "Wallpaper",
    "Screen Recorder", "Music Player", "Fitness", "Backup"
]

def load_used_apps():
    if not os.path.exists(HISTORY_APPS_FILE): return set()
    with open(HISTORY_APPS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_used_app(package_name):
    with open(HISTORY_APPS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{package_name}\n")

def get_fresh_app():
    used_apps = load_used_apps()
    queries = SEARCH_QUERIES[:]
    random.shuffle(queries)
    for query in queries:
        try:
            results = play_search(query, lang="en", country="us", n=20)
            for app_summary in results:
                pkg = app_summary['appId']
                if pkg in used_apps: continue
                try: details = play_app(pkg, lang='ar', country='us')
                except: details = play_app(pkg, lang='en', country='us')
                if details.get('score', 0) < 3.8: continue
                if not details.get('icon') and not details.get('headerImage'): continue
                return details
        except: continue
    return None

def _rest_generate(prompt):
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for model in models:
        url = f"{GEMINI_API_ROOT}/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
            if r.ok: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return None

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def ask_gemini_app_review(app_details):
    title = app_details['title']
    desc = app_details.get('description', '')[:1500]
    prompt = f"""
    اكتب مقالاً مفصلاً وجذاباً باللغة العربية حول تطبيق: "{title}".
    معلومات التطبيق: {desc}
    المطلوب (Markdown):
    1. **عنوان جذاب**: (H1) يبدأ بـ #.
    2. **مقدمة**: تشويقية.
    3. **المميزات**: 5 نقاط رئيسية.
    4. **شرح الاستخدام**.
    5. **معلومات تقنية**: جدول (الإصدار، الحجم، التقييم).
    6. **الخاتمة**: توصية.
    لا تضع روابط تحميل.
    """
    return _rest_generate(prompt)

def build_app_post_html(app_details, article_html):
    image_url = app_details.get('headerImage') or app_details.get('icon')
    title = app_details['title']
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:10px;box-shadow:0 4px 8px rgba(0,0,0,0.2);"></div>'
    button = f'<div style="text-align:center;margin-top:40px;margin-bottom:50px;"><p style="font-weight:bold;margin-bottom:15px;">حمله الآن 👇</p><a href="{MONETAG_DIRECT_LINK}" class="app-download-btn" target="_blank" rel="nofollow noopener">📥 تحميل التطبيق (رابط مباشر)</a></div>'
    return header + md.markdown(article_html, extensions=['extra']) + button

def post_to_blogger(title, content):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    body = {"kind": "blogger#post", "title": title, "content": content, "labels": APP_LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

if __name__ == "__main__":
    print("Starting App Bot...")
    app_data = get_fresh_app()
    if app_data:
        print(f"Found: {app_data['title']}")
        article = ask_gemini_app_review(app_data)
        if article:
            title = article.split('\n')[0].replace('#', '').strip()
            if len(title) < 5: title = f"تحميل تطبيق {app_data['title']} للاندرويد"
            final_html = build_app_post_html(app_data, article)
            try:
                post_to_blogger(title, final_html)
                save_used_app(app_data['appId'])
                print("App Published Successfully ✅")
            except Exception as e: print(f"Publish Error: {e}")
    else: print("No app found.")
