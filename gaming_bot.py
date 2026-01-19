# -*- coding: utf-8 -*-
import os, random, markdown as md
import requests
import backoff
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_play_scraper import search as play_search, app as play_app

# =================== إعدادات المستخدم ===================
MONETAG_DIRECT_LINK = "https://otieu.com/4/10485502"
GAME_LABELS = ["Games", "Solutions", "Android", "Fix", "شروحات"]

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
HISTORY_GAMES_FILE = "history_gaming.txt"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

# قائمة المشاكل التقنية التي يعاني منها اللاعبون
GAMING_PROBLEMS = [
    "حل مشكلة اللاغ والتقطيع (Fix Lag)",
    "تفعيل 90 فريم (Unlock 90 FPS)",
    "حل مشكلة ارتفاع حرارة الهاتف (Fix Overheating)",
    "تسريع اللعبة للأجهزة الضعيفة (Boost Performance)",
    "حل مشكلة البينغ العالي (Fix High Ping)",
    "حل مشكلة الخروج المفاجئ (Fix Crash)",
    "تقليل استهلاك البطارية أثناء اللعب"
]

SEARCH_QUERIES = [
    "PUBG Mobile", "Free Fire", "Call of Duty Mobile", "Roblox", "Minecraft",
    "Genshin Impact", "Mobile Legends", "Brawl Stars", "CarX Street", "FIFA Mobile",
    "Asphalt 9", "Subway Surfers", "Clash of Clans", "Efootball", "Warzone Mobile"
]

# =================== 1. دوال التاريخ والجلب ===================
def load_used_games():
    if not os.path.exists(HISTORY_GAMES_FILE): return set()
    with open(HISTORY_GAMES_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_used_game(package_name):
    with open(HISTORY_GAMES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{package_name}\n")

def get_fresh_game_problem():
    used_games = load_used_games()
    queries = SEARCH_QUERIES[:]
    random.shuffle(queries)
    print(f"🎮 Scanning Google Play for targets...")
    
    for query in queries:
        try:
            results = play_search(query, lang="ar", country="sa", n_hits=15)
            for game in results:
                pkg = game['appId']
                
                # نسمح بتكرار اللعبة إذا كانت المشكلة مختلفة، لكن حالياً سنمنع التكرار لضمان التنوع
                if pkg in used_games: continue
                if game.get('score', 0) < 3.5: continue 

                try: details = play_app(pkg, lang='ar', country='sa')
                except: continue
                
                if not details.get('icon'): continue
                
                # اختيار مشكلة عشوائية لهذه اللعبة
                problem = random.choice(GAMING_PROBLEMS)
                
                print(f"✅ Target Acquired: {details['title']} -> Problem: {problem}")
                return details, problem
        except: continue
    return None, None

# =================== 2. المحرك الذكي (Auto-Detect Model) ===================
def get_working_model():
    url = f"{GEMINI_API_ROOT}/v1beta/models?key={GEMINI_API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200: 
            return "gemini-1.5-flash"
        data = r.json()
        for model in data.get('models', []):
            name = model['name'].replace('models/', '')
            if 'generateContent' in model.get('supportedGenerationMethods', []):
                return name
        return "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def ask_gemini_solution(game_details, problem):
    model_name = get_working_model()
    title = game_details['title']
    
    prompt = f"""
    تصرف كمهندس برمجيات وخبير ألعاب أندرويد.
    المهمة: اكتب مقالاً تقنياً لحل مشكلة "{problem}" في لعبة "{title}".
    
    الهيكل المطلوب (Markdown):
    1. **عنوان المقال (H1)**: يجب أن يكون عن حل المشكلة (مثلاً: أخيراً.. تفعيل 90 فريم في {title}).
    2. **تشخيص المشكلة**: لماذا تحدث هذه المشكلة في {title}؟ (فقرة قصيرة).
    3. **الحلول المقترحة**: خطوات عملية (إعدادات الجرافيك، تنظيف الذاكرة، استخدام مسرع الألعاب).
    4. **جدول أفضل الإعدادات**: جدول يوضح الإعدادات المناسبة للأجهزة الضعيفة والمتوسطة.
    5. **أسئلة شائعة (FAQ)**: سؤالين وجوابين عن المشكلة.
    6. **الخاتمة**: نصيحة بتحميل النسخة الرسمية.

    استخدم الايموجي 🛠️🎮⚡. لا تذكر أسماء تطبيقات خارجية محددة، قل "استخدم أدوات التسريع" فقط.
    """
    
    url = f"{GEMINI_API_ROOT}/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    safety = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
    
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety}, timeout=60)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

# =================== 3. بناء المقال وزر التحميل المصلح ===================
def build_game_post_html(game_details, article_html, problem):
    image_url = game_details.get('headerImage') or game_details.get('icon')
    title = game_details['title']
    pkg_id = game_details['appId']
    
    # بناء رابط المتجر يدوياً لضمان صحته 100%
    real_play_store_url = f"https://play.google.com/store/apps/details?id={pkg_id}"
    
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:15px;box-shadow:0 8px 20px rgba(0,0,0,0.2);"></div>'
    
    # الأزرار: تم إصلاح زر التحميل ليعمل بشكل أكيد
    buttons_html = f"""
    <style>
        .gaming-btns {{ display: flex; flex-direction: column; gap: 15px; margin: 30px 0; }}
        .g-btn {{
            display: block; padding: 15px; text-align: center; color: white !important;
            text-decoration: none; font-weight: bold; border-radius: 50px;
            font-size: 18px; transition: transform 0.2s; position: relative; overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        .g-btn:hover {{ transform: scale(1.02); }}
        .btn-gold {{ background: linear-gradient(45deg, #f1c40f, #f39c12); }}
        .btn-blue {{ background: linear-gradient(45deg, #3498db, #2980b9); }}
        .btn-green {{ background: linear-gradient(45deg, #2ecc71, #27ae60); }}
    </style>

    <div class="gaming-btns">
        <a href="{MONETAG_DIRECT_LINK}" target="_blank" class="g-btn btn-gold">
            🛠️ اضغط هنا لإصلاح المشكلة فوراً
        </a>
        
        <a href="{MONETAG_DIRECT_LINK}" target="_blank" class="g-btn btn-blue">
            🚀 تفعيل أقصى أداء (Performance Mode)
        </a>
        
        <a href="{real_play_store_url}" 
           target="_blank" 
           onclick="window.open('{MONETAG_DIRECT_LINK}', '_blank');"
           class="g-btn btn-green">
            📥 تحميل التحديث الرسمي من Google Play
        </a>
        
        <p style="text-align:center; font-size:12px; color:#777; margin-top:5px;">
            ✅ تم التحقق من الرابط: آمن ورسمي
        </p>
    </div>
    """
    
    return header + md.markdown(article_html, extensions=['extra']) + buttons_html

def post_to_blogger(title, content):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    body = {"kind": "blogger#post", "title": title, "content": content, "labels": GAME_LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

if __name__ == "__main__":
    print("🛠️ Starting Gaming Bot (Tech Support Mode)...")
    game_data, problem = get_fresh_game_problem()
    
    if game_data and problem:
        print(f"📝 Writing solution for: {game_data['title']} ({problem})...")
        article = ask_gemini_solution(game_data, problem)
        
        if article:
            lines = article.strip().split('\n')
            title = lines[0].replace('#', '').replace('*', '').strip()
            # ضمان أن العنوان جذاب
            if len(title) < 5 or "عنوان" in title: 
                title = f"حل مشكلة {problem} في لعبة {game_data['title']} (طريقة مضمونة)"
            
            final_html = build_game_post_html(game_data, article, problem)
            
            try:
                res = post_to_blogger(title, final_html)
                save_used_game(game_data['appId'])
                print(f"🎉 PUBLISHED! URL: {res.get('url')}")
            except Exception as e: print(f"❌ Publish Error: {e}")
        else: print("❌ Content generation failed.")
    else: print("❌ No game target found.")
