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
    
    print(f"Scanning categories...")
    
    for query in queries:
        try:
            # استخدام n_hits الصحيح
            results = play_search(query, lang="en", country="us", n_hits=50)
            
            for app_summary in results:
                pkg = app_summary['appId']
                
                if pkg in used_apps: continue
                
                score = app_summary.get('score', 0)
                if score and score < 3.8: continue # رفعنا الجودة قليلاً لضمان تطبيقات جيدة

                try: 
                    details = play_app(pkg, lang='en', country='us')
                except: continue
                
                if not details.get('icon'): continue
                
                print(f"✅ Found suitable app: {details['title']}")
                return details
                
        except Exception as e: 
            print(f"⚠️ Search error in '{query}': {e}")
            continue
            
    return None

def _rest_generate(prompt):
    # استخدام الموديل المستقر والسريع فقط
    model = "gemini-1.5-flash"
    url = f"{GEMINI_API_ROOT}/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    
    # إعدادات لتعطيل فلاتر الأمان لضمان عدم رفض المقال
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": safety_settings,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2000
        }
    }

    try:
        r = requests.post(url, json=body, timeout=60)
        
        # إذا حدث خطأ، نطبع تفاصيل الخطأ لنعرف السبب
        if not r.ok:
            print(f"❌ Gemini API Error: {r.status_code} - {r.text}")
            return None
            
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def ask_gemini_app_review(app_details):
    title = app_details['title']
    desc = app_details.get('description', '')[:2500] # زيادة حجم النص المرسل
    
    prompt = f"""
    تصرف كخبير تقني. اكتب مراجعة شاملة لتطبيق الأندرويد التالي باللغة العربية.
    
    اسم التطبيق: {title}
    وصف التطبيق: {desc}
    
    المطلوب (بتنسيق Markdown):
    1. **عنوان المقال**: (H1) جذاب ويحتوي اسم التطبيق.
    2. **مقدمة**: تشرح فكرة التطبيق ببساطة.
    3. **المميزات الرئيسية**: 5 نقاط تشرح لماذا هذا التطبيق مميز.
    4. **شرح الاستخدام**: كيف يستفيد منه المستخدم العادي.
    5. **معلومات تقنية**: جدول يحتوي على (الإصدار، الحجم، التقييم، عدد التحميلات).
    6. **الخاتمة**: نصيحة أخيرة.
    
    هام: لا تضع أي روابط خارجية.
    """
    return _rest_generate(prompt)

def build_app_post_html(app_details, article_html):
    image_url = app_details.get('headerImage') or app_details.get('icon')
    title = app_details['title']
    
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1);"></div>'
    
    button = f"""
    <div style="text-align:center; margin-top:40px; margin-bottom:40px; padding: 20px; background: #f0fdf4; border: 2px solid #2ecc71; border-radius: 15px;">
        <h3 style="margin:0 0 15px 0; color:#145a32;">🚀 جاهز للتجربة؟</h3>
        <a href="{MONETAG_DIRECT_LINK}" class="app-download-btn" target="_blank" rel="nofollow noopener" style="display:inline-block; padding:15px 40px; background:#27ae60; color:white; text-decoration:none; border-radius:50px; font-weight:bold; font-size:20px; box-shadow: 0 5px 15px rgba(39, 174, 96, 0.4);">
            تحميل التطبيق (APK) 📥
        </a>
        <p style="margin-top:10px; font-size:13px; color:#555;">رابط مباشر آمن 100%</p>
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
    print("🚀 Starting App Bot v4 (Stability Fixes)...")
    app_data = get_fresh_app()
    
    if app_data:
        print(f"📝 Generating article for: {app_data['title']}...")
        article = ask_gemini_app_review(app_data)
        
        if article:
            lines = article.strip().split('\n')
            title = lines[0].replace('#', '').replace('*', '').strip()
            if len(title) < 5: title = f"تحميل تطبيق {app_data['title']} للاندرويد"
            
            final_html = build_app_post_html(app_data, article)
            try:
                res = post_to_blogger(title, final_html)
                save_used_app(app_data['appId'])
                print(f"🎉 PUBLISHED SUCCESSFULLY! Check URL: {res.get('url')}")
            except Exception as e: print(f"❌ Publish Error: {e}")
        else:
            print("❌ Failed to generate article content. Check API logs above.")
    else: 
        print("❌ No suitable app found despite extensive search.")
