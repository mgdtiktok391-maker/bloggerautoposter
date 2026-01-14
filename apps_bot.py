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
MONETAG_DIRECT_LINK = "https://otieu.com/4/10464710" 
APP_LABELS = ["apps", "أدوات", "تطبيقات_اندرويد"]

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
HISTORY_APPS_FILE = "history_apps.txt"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

# قائمة بحث موسعة جداً لضمان العثور على نتائج
SEARCH_QUERIES = [
    "Tool", "Utility", "AI", "Photo", "Video", "Maker", "Editor", 
    "Scanner", "PDF", "Cleaner", "Battery", "VPN", "Security", 
    "Health", "Fitness", "Learn", "Language", "Translate", "Keyboard", 
    "Launcher", "Wallpaper", "Icon Pack", "Music", "Audio", "Player",
    "Browser", "File Manager", "Backup", "Zip", "Calculator", "Notes"
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
    random.shuffle(queries) # خلط عشوائي للكلمات
    
    print(f"Checking {len(queries)} categories...")
    
    for query in queries:
        try:
            # زيادة عدد النتائج إلى 100 بدلاً من 20 لضمان العثور على تطبيق
            results = play_search(query, lang="en", country="us", n=100)
            
            for app_summary in results:
                pkg = app_summary['appId']
                
                # تخطي التطبيقات المستخدمة سابقاً
                if pkg in used_apps: continue
                
                # تخطي التطبيقات ذات التقييم المنخفض جداً (أقل من 3.0)
                score = app_summary.get('score', 0)
                if score and score < 3.0: continue 

                # جلب التفاصيل
                try: 
                    # نحاول جلب التفاصيل (لا يهم اللغة، البوت سيترجم)
                    details = play_app(pkg, lang='en', country='us')
                except: 
                    continue
                
                # إذا لم يكن هناك أيقونة، نتجاوزه (نادر جداً)
                if not details.get('icon'): continue
                
                print(f"Found suitable app: {details['title']}")
                return details
                
        except Exception as e: 
            print(f"Search error in '{query}': {e}")
            continue
            
    return None

def _rest_generate(prompt):
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
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
    desc = app_details.get('description', '')[:2000]
    
    prompt = f"""
    أنت محرر تقني. اكتب مقال مراجعة لتطبيق أندرويد باللغة العربية.
    اسم التطبيق: {title}
    معلومات عنه: {desc}
    
    الهيكل المطلوب (Markdown):
    1. **عنوان المقال**: (H1) جذاب وقصير.
    2. **مقدمة**: فقرة واحدة تشرح وظيفة التطبيق.
    3. **المميزات**: 5 نقاط واضحة.
    4. **شرح موجز**: كيف يعمل.
    5. **معلومات**: جدول (الإصدار، الحجم، التقييم).
    6. **الخاتمة**: نصيحة بالتحميل.
    
    تنبيه: لا تضع روابط خارجية.
    """
    return _rest_generate(prompt)

def build_app_post_html(app_details, article_html):
    # استخدام صورة الغلاف إذا وجدت، وإلا استخدام الأيقونة بحجم كبير
    image_url = app_details.get('headerImage') or app_details.get('icon')
    title = app_details['title']
    
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1);"></div>'
    
    # تحسين تصميم الزر وجعله أكثر وضوحاً
    button = f"""
    <div style="text-align:center; margin-top:50px; margin-bottom:50px; padding: 20px; background: #f9f9f9; border-radius: 10px;">
        <h3 style="margin-bottom:15px;">📥 روابط التحميل</h3>
        <a href="{MONETAG_DIRECT_LINK}" class="app-download-btn" target="_blank" rel="nofollow noopener" style="display:inline-block; padding:15px 30px; background:#27ae60; color:white; text-decoration:none; border-radius:50px; font-weight:bold; font-size:18px;">
            تحميل التطبيق الآن (APK)
        </a>
        <p style="margin-top:10px; font-size:14px; color:#666;">رابط مباشر وسريع</p>
    </div>
    """
    return header + md.markdown(article_html, extensions=['extra']) + button

def post_to_blogger(title, content):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    # نشر مباشر (isDraft=False)
    body = {"kind": "blogger#post", "title": title, "content": content, "labels": APP_LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

if __name__ == "__main__":
    print("Starting App Bot v2 (Relaxed Filters)...")
    app_data = get_fresh_app()
    if app_data:
        print(f"Selected App: {app_data['title']}")
        article = ask_gemini_app_review(app_data)
        if article:
            # تنظيف العنوان
            lines = article.strip().split('\n')
            title = lines[0].replace('#', '').replace('*', '').strip()
            if len(title) < 5: title = f"تحميل تطبيق {app_data['title']}"
            
            final_html = build_app_post_html(app_data, article)
            try:
                post_to_blogger(title, final_html)
                save_used_app(app_data['appId'])
                print("App Published Successfully ✅ Check your blog now.")
            except Exception as e: print(f"Publish Error: {e}")
        else:
            print("Error: Gemini returned empty article.")
    else: 
        print("STILL No app found! (Try checking internet or library)")
