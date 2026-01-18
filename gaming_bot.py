# -*- coding: utf-8 -*-
import os
import random
import json
import time
import requests
import markdown as md
import backoff
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_play_scraper import search

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

# الروابط
AD_LINK = "https://otieu.com/4/10483041"
STORE_PAGE = "https://www.loadingapk.online/p/loading-store.html"
PRODUCTS_FILE = "products.json"
HISTORY_FILE = "history_gaming.json"

GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

# ⚠️ التعديل الجذري: استخدام الموديلات المستقرة على القناة v1
# هذا الترتيب يضمن المحاولة بالأذكى ثم الأسرع ثم الأقدم والأكثر استقراراً
MODELS_TO_TRY = [
    "gemini-1.5-flash",  # سريع وجديد
    "gemini-1.5-pro",    # ذكي جداً
    "gemini-pro"         # (Legacy) الموديل القديم الذي يعمل دائماً ولا يتعطل
]

LABELS = ["Gaming", "Games_2026", "Android_Games", "شروحات_ألعاب", "Game_Booster"]

PROBLEMS = [
    "حل مشكلة اللاغ والتقطيع (Fix Lag)",
    "تفعيل أعلى فريمات (Unlock 90/120 FPS)",
    "أفضل كود حساسية (Best Sensitivity)",
    "حل مشكلة الخروج المفاجئ (Crash Fix)",
    "تسريع اللعبة للأجهزة الضعيفة (Game Booster)",
    "تقليل البينغ والدمج الوهمي (Fix Ping)"
]

# =================== 1. المستشعر: جلب الألعاب (Google Play) ===================
def get_real_trending_games():
    print("📡 Contacting Google Play Store...")
    try:
        queries = ["New Action Games", "Trending Games", "Racing Games", "Battle Royale", "Shooting Games"]
        chosen_query = random.choice(queries)
        
        # استخدام دالة search المضمونة
        results = search(chosen_query, lang='ar', country='sa', n_hits=30)
        games_list = [game['title'] for game in results]
        
        if games_list:
            print(f"✅ Found {len(games_list)} games.")
            return games_list
        raise Exception("Zero results found")
    except Exception as e:
        print(f"⚠️ Scraper Warning: {e}")
        return ["PUBG Mobile", "Free Fire", "Call of Duty Mobile", "Roblox", "Minecraft", "Subway Surfers", "Ludo King"]

# =================== دوال المساعدة ===================
def load_json(filename):
    if not os.path.exists(filename): return []
    with open(filename, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return []

def save_history(topic):
    history = load_json(HISTORY_FILE)
    history.append(topic)
    if len(history) > 100: history = history[-100:] 
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_product_recommendation():
    products = load_json(PRODUCTS_FILE)
    if products:
        p = random.choice(products)
        return f"""
        <div style="background:#1e272e; border:2px dashed #ff9f43; padding:20px; margin:30px 0; text-align:center; border-radius:15px;">
            <h3 style="margin:0 0 10px 0; color:#ff9f43;">🛠️ عتاد المحترفين:</h3>
            <p style="color:#d2dae2;">لأفضل أداء في اللعب، ننصحك باستخدام: <strong>{p['name_ar']}</strong>.</p>
            <div style="margin:10px 0;"><img src="{p['image_url']}" style="width:80px;height:80px;object-fit:contain;background:#fff;border-radius:8px;"></div>
            <a href="{p['affiliate_link']}" target="_blank" style="display:inline-block; background:#ff9f43; color:white; padding:8px 20px; text-decoration:none; border-radius:50px;">شاهد السعر 🛒</a>
        </div>
        """
    return ""

# =================== الاتصال الذكي بـ Gemini (v1 Stable) ===================
def generate_with_retry(prompt):
    """يحاول الاتصال بعدة موديلات باستخدام الإصدار المستقر v1"""
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    for model in MODELS_TO_TRY:
        print(f"🤖 Trying model: {model} (on v1)...")
        
        # ⚠️ التغيير هنا: استخدام v1 بدلاً من v1beta
        url = f"{GEMINI_API_ROOT}/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": safety_settings
        }
        
        try:
            r = requests.post(url, json=payload, timeout=50)
            if r.status_code == 200:
                print("✅ Success!")
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                # طباعة تفاصيل الخطأ للمساعدة في التشخيص
                print(f"⚠️ Failed ({model}): Code {r.status_code}")
                # print(f"Error Details: {r.text}") # قم بإلغاء التعليق إذا احتجت تفاصيل أكثر
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error ({model}): {e}")
            time.sleep(1)
            
    print("❌ All models failed to generate content.")
    return None

# =================== المنطق الرئيسي ===================
def discover_game_trend():
    real_games = get_real_trending_games()
    selected_game = random.choice(real_games)
    selected_problem = random.choice(PROBLEMS)
    
    print(f"🎯 Target: {selected_game} + {selected_problem}")
    
    prompt = f"اكتب عنوان مقال عربي جذاب (Clickbait) يجمع بين لعبة '{selected_game}' وحل مشكلة '{selected_problem}'. الرد بالعنوان فقط بدون علامات تنصيص."
    
    title = generate_with_retry(prompt)
    
    if title: 
        return title.strip().replace('"', '').replace('*', ''), selected_game
    return None, None

def write_gaming_guide(title, game_name):
    if not title: return None
    
    product_box = get_product_recommendation()
    print(f"✍️ Writing Article: {title}")
    
    prompt = f"""
    اكتب مقالاً تقنياً طويلاً واحترافياً للجيمرز بعنوان: "{title}"
    استخدم تنسيق Markdown. اجعل المقال مفصلاً (أكثر من 500 كلمة).
    
    الهيكل المطلوب:
    1. مقدمة حماسية جداً عن شهرة لعبة {game_name}.
    2. تحليل سبب المشكلة (لماذا يحدث اللاغ أو التقطيع؟).
    3. [AD_BUTTON_1]
    4. الخطوات العملية للحل (إعدادات الجرافيك، خيارات المطور).
    5. شرح طريقة استخدام الملفات أو الـ DNS.
    6. [PRODUCT_BOX]
    7. نصائح إضافية للاحتراف.
    8. الخاتمة.
    9. [AD_BUTTON_2]
    
    استخدم الايموجي 🎮🔥⚡ وتحدث بلغة تشجع اللاعبين.
    """
    
    content = generate_with_retry(prompt)
    if content:
        content = content.replace("[PRODUCT_BOX]", product_box)
        return content
    return None

# =================== التصميم والنشر ===================
def build_html(title, markdown_content):
    rand_id = random.randint(1, 1000)
    image_url = f"https://picsum.photos/seed/{rand_id}/800/450?grayscale"
    
    btn1 = f"""<div style="text-align:center; margin:35px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn download-btn"><span class="btn-icon">📥</span> اضغط هنا للتحميل وتفعيل الإعدادات</a><p style="color:#7f8fa6; font-size:12px; margin-top:8px;">(تم الفحص: آمن 100% ✅)</p></div>"""
    btn2 = f"""<div style="text-align:center; margin:40px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn gift-btn">💎 احصل على شدات/جواهر مجاناً</a></div>"""
    
    content = md.markdown(markdown_content, extensions=['extra'])
    content = content.replace("[AD_BUTTON_1]", btn1).replace("[AD_BUTTON_2]", btn2)
    if "[AD_BUTTON_1]" not in markdown_content: content += btn1 + btn2

    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        .game-article {{ font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; line-height: 1.8; color: #dcdde1; background: #191919; padding: 15px; border-radius: 12px; }}
        .game-header-img {{ width: 100%; border-radius: 12px; margin-bottom: 25px; border: 2px solid #e1b12c; }}
        h1 {{ color: #e1b12c; font-weight: 900; font-size: 24px; border-bottom: 1px solid #353b48; padding-bottom: 15px; }}
        h2 {{ color: #00a8ff; margin-top: 35px; background: #2f3640; padding: 10px; border-right: 5px solid #00a8ff; border-radius: 8px; }}
        strong {{ color: #4cd137; }}
        .gaming-btn {{ display: inline-block; padding: 15px 20px; font-weight: 900; font-size: 18px; border-radius: 50px; text-decoration: none; width: 90%; max-width: 400px; transition: 0.3s; }}
        .download-btn {{ background: linear-gradient(45deg, #44bd32, #009432); color: #fff !important; border: 2px solid #b8e994; animation: pulse-g 2s infinite; }}
        .gift-btn {{ background: linear-gradient(45deg, #8c7ae6, #9c88ff); color: #fff !important; border: 2px solid #dcd6f7; }}
        @keyframes pulse-g {{ 0% {{ box-shadow: 0 0 0 0 rgba(68,189,50,0.7); }} 70% {{ box-shadow: 0 0 0 15px rgba(68,189,50,0); }} 100% {{ box-shadow: 0 0 0 0 rgba(68,189,50,0); }} }}
        @media (max-width:600px) {{ .gaming-btn {{ font-size:16px; padding:12px; }} }}
    </style>
    <div class="game-article">
        <img src="{image_url}" alt="{title}" class="game-header-img">
        {content}
        <div style="text-align:center; margin-top:30px; border-top:1px solid #333; padding-top:15px; font-size:12px; color:#777;">🎮 Loading Gaming Zone © 2026 | <a href="{STORE_PAGE}" style="color:#e1b12c;">المتجر</a></div>
    </div>
    """

def post_to_blogger(title, content):
    print("🚀 Publishing to Blogger...")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    try: 
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        blog_id = blog["id"]
        body = {"kind": "blogger#post", "title": f"🔥 {title}", "content": content, "labels": LABELS}
        return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
    except Exception as e:
        print(f"❌ Blog Error: {e}")
        return None

# =================== التشغيل ===================
if __name__ == "__main__":
    print("🎮 Gaming Bot (v1 Stable Channel) Starting...")
    
    topic, game_name = discover_game_trend()
    
    if topic and game_name:
        article_md = write_gaming_guide(topic, game_name)
        
        if article_md:
            article_html = build_html(topic, article_md)
            res = post_to_blogger(topic, article_html)
            if res:
                print(f"✅ DONE! Article published: {res.get('url')}")
                save_history(topic)
            else:
                print("❌ Failed to post to Blogger.")
        else:
            print("❌ Failed to write content (Check API Key or Quota).")
    else:
        print("❌ Failed to find a topic/game.")
