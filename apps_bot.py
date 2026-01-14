# -*- coding: utf-8 -*-
import os, random, markdown as md
from datetime import datetime
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

# قائمة بحث شاملة
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
    random.shuffle(queries)
    print(f"🔍 Scanning for apps...")
    
    for query in queries:
        try:
            results = play_search(query, lang="en", country="us", n_hits=50)
            for app_summary in results:
                pkg = app_summary['appId']
                if pkg in used_apps: continue
                
                score = app_summary.get('score', 0)
                if score and score < 4.0: continue 

                try: details = play_app(pkg, lang='en', country='us')
                except: continue
                
                if not details.get('icon'): continue
                
                print(f"✅ Found App: {details['title']}")
                return details
        except: continue  
    return None

# =================== اكتشاف الموديل ===================
def get_working_model():
    url = f"{GEMINI_API_ROOT}/v1beta/models?key={GEMINI_API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200: return "gemini-pro"
        data = r.json()
        for model in data.get('models', []):
            name = model['name'].replace('models/', '')
            if 'generateContent' in model.get('supportedGenerationMethods', []):
                return name
        return "gemini-1.5-flash"
    except: return "gemini-pro"

def _rest_generate(prompt):
    model_name = get_working_model()
    url = f"{GEMINI_API_ROOT}/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety_settings}, timeout=60)
        if r.status_code == 200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except: return None

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def ask_gemini_app_review(app_details):
    title = app_details['title']
    desc = app_details.get('description', '')[:2500]
    prompt = f"""
    تصرف كخبير تقني. اكتب مراجعة لتطبيق: {title}
    الوصف: {desc}
    المطلوب (Markdown):
    1. **عنوان المقال**: (H1) جذاب.
    2. **مقدمة**: بسيطة.
    3. **المميزات**: 5 نقاط.
    4. **شرح الاستخدام**.
    5. **معلومات تقنية**: جدول.
    6. **الخاتمة**: نصيحة.
    لا تضع روابط.
    """
    return _rest_generate(prompt)

# =================== تعديل الزر الذكي ===================
def build_app_post_html(app_details, article_html):
    image_url = app_details.get('headerImage') or app_details.get('icon')
    title = app_details['title']
    pkg_id = app_details['appId']
    
    # رابط المتجر الحقيقي
    real_play_store_url = f"https://play.google.com/store/apps/details?id={pkg_id}"
    
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1);"></div>'
    
    # الزر الذكي:
    # href: يوجه للرابط الحقيقي (المتجر)
    # onclick: يفتح الإعلان في نافذة جديدة فور الضغط
    button = f"""
    <div style="text-align:center; margin-top:40px; margin-bottom:40px; padding: 20px; background: #f0fdf4; border: 2px solid #2ecc71; border-radius: 15px;">
        <h3 style="margin:0 0 15px 0; color:#145a32;">🚀 تحميل التطبيق</h3>
        
        <a href="{real_play_store_url}" 
           onclick="window.open('{MONETAG_DIRECT_LINK}', '_blank');" 
           class="app-download-btn" 
           target="_self" 
           rel="nofollow noopener" 
           style="display:inline-block; padding:15px 40px; background:#27ae60; color:white; text-decoration:none; border-radius:50px; font-weight:bold; font-size:20px; box-shadow: 0 5px 15px rgba(39, 174, 96, 0.4); cursor:pointer;">
            اضغط هنا للتحميل (APK) 📥
        </a>
        
        <p style="margin-top:10px; font-size:13px; color:#555;">سيتم توجيهك للمتجر الرسمي فوراً</p>
    </div>
    """
    return header + md.markdown(article_html, extensions=['extra']) + button

def post_to_blogger(title, content):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    body = {"kind": "blogger#post", "title": title, "content": content, "labels": APP_LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

if __name__ == "__main__":
    print("🚀 Starting App Bot v7 (Smart Button)...")
    app_data = get_fresh_app()
    if app_data:
        print(f"📝 Generating content for: {app_data['title']}...")
        article = ask_gemini_app_review(app_data)
        if article:
            lines = article.strip().split('\n')
            title = lines[0].replace('#', '').replace('*', '').strip()
            if len(title) < 5: title = f"تحميل تطبيق {app_data['title']}"
            final_html = build_app_post_html(app_data, article)
            try:
                res = post_to_blogger(title, final_html)
                save_used_app(app_data['appId'])
                print(f"🎉 PUBLISHED! URL: {res.get('url')}")
            except Exception as e: print(f"❌ Publish Error: {e}")
        else: print("❌ Content generation failed.")
    else: print("❌ No app found.")
