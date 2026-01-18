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
LABELS = ["Gaming", "Games_2026", "Android_Games", "شروحات_ألعاب", "Game_Booster"]

PROBLEMS = [
    "حل مشكلة اللاغ والتقطيع (Fix Lag)",
    "تفعيل أعلى فريمات (Unlock 90/120 FPS)",
    "أفضل كود حساسية (Best Sensitivity)",
    "حل مشكلة الخروج المفاجئ (Crash Fix)",
    "تسريع اللعبة للأجهزة الضعيفة (Game Booster)",
    "تقليل البينغ والدمج الوهمي (Fix Ping)"
]

# =================== 1. المستشعر: جلب الألعاب ===================
def get_real_trending_games():
    print("📡 Contacting Google Play Store...")
    try:
        queries = ["New Action Games", "Trending Games", "Racing Games", "Battle Royale", "Shooting Games"]
        chosen_query = random.choice(queries)
        results = search(chosen_query, lang='ar', country='sa', n_hits=30)
        games_list = [game['title'] for game in results]
        if games_list:
            print(f"✅ Found {len(games_list)} games.")
            return games_list
        raise Exception("Zero results found")
    except Exception as e:
        print(f"⚠️ Scraper Warning: {e}")
        return ["PUBG Mobile", "Free Fire", "Call of Duty Mobile", "Roblox", "Minecraft"]

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
        # تصميم الصندوق: أبيض مع حدود ناعمة
        return f"""
        <div style="background:#f8f9fa; border:1px solid #ddd; padding:20px; margin:30px 0; text-align:center; border-radius:12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h3 style="margin:0 0 10px 0; color:#e67e22;">🛠️ عتاد المحترفين:</h3>
            <p style="color:#555;">لأفضل أداء في اللعب، ننصحك باستخدام: <strong>{p['name_ar']}</strong>.</p>
            <div style="margin:10px 0;"><img src="{p['image_url']}" style="width:100px;height:100px;object-fit:contain;background:#fff;border-radius:8px;border:1px solid #eee;"></div>
            <a href="{p['affiliate_link']}" target="_blank" style="display:inline-block; background:#e67e22; color:white; padding:8px 25px; text-decoration:none; border-radius:50px; font-weight:bold;">شاهد السعر 🛒</a>
        </div>
        """
    return ""

# =================== الذكاء الاصطناعي: الاكتشاف التلقائي للموديل ===================
def get_dynamic_model():
    print("🔍 Auto-detecting available Gemini models...")
    url = f"{GEMINI_API_ROOT}/v1beta/models?key={GEMINI_API_KEY}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            available_models = []
            for m in data.get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    clean_name = m['name'].replace('models/', '')
                    available_models.append(clean_name)
            
            preferred_order = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
            for pref in preferred_order:
                if pref in available_models:
                    print(f"✅ Selected Model: {pref}")
                    return pref
            if available_models: return available_models[0]
    except Exception as e:
        print(f"⚠️ Model Discovery Failed: {e}")
    return "gemini-1.5-flash"

def generate_content(prompt):
    model_name = get_dynamic_model()
    url = f"{GEMINI_API_ROOT}/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    print(f"🤖 Generating with {model_name}...")
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# =================== المنطق الرئيسي ===================
def discover_game_trend():
    real_games = get_real_trending_games()
    selected_game = random.choice(real_games)
    selected_problem = random.choice(PROBLEMS)
    print(f"🎯 Target: {selected_game} + {selected_problem}")
    
    prompt = f"اكتب عنوان مقال عربي جذاب (Clickbait) يجمع بين لعبة '{selected_game}' وحل مشكلة '{selected_problem}'. الرد بالعنوان فقط."
    title = generate_content(prompt)
    if title: return title.strip().replace('"', '').replace('*', ''), selected_game
    return None, None

def write_gaming_guide(title, game_name):
    if not title: return None
    product_box = get_product_recommendation()
    print(f"✍️ Writing Article: {title}")
    
    prompt = f"""
    اكتب مقالاً تقنياً طويلاً واحترافياً للجيمرز بعنوان: "{title}"
    استخدم تنسيق Markdown.
    الهيكل:
    1. مقدمة عن {game_name}.
    2. تحليل المشكلة.
    3. [AD_BUTTON_1]
    4. الخطوات العملية للحل.
    5. [PRODUCT_BOX]
    6. الخاتمة.
    7. [AD_BUTTON_2]
    استخدم الايموجي 🎮🔥.
    """
    content = generate_content(prompt)
    if content:
        content = content.replace("[PRODUCT_BOX]", product_box)
        return content
    return None

# =================== التصميم الجديد (فاتح واحترافي) ===================
def build_html(title, markdown_content):
    rand_id = random.randint(1, 1000)
    # صورة ملونة عادية بدلاً من الأبيض والأسود لتكون أجمل
    image_url = f"https://picsum.photos/seed/{rand_id}/800/450"
    
    # أزرار بتصميم مسطح (Flat Design)
    btn1 = f"""<div style="text-align:center; margin:35px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn download-btn"><span class="btn-icon">📥</span> اضغط هنا للتحميل وتفعيل الإعدادات</a><p style="color:#7f8fa6; font-size:12px; margin-top:8px;">(تم الفحص: آمن 100% ✅)</p></div>"""
    btn2 = f"""<div style="text-align:center; margin:40px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn gift-btn">💎 احصل على شدات/جواهر مجاناً</a></div>"""
    
    content = md.markdown(markdown_content, extensions=['extra'])
    content = content.replace("[AD_BUTTON_1]", btn1).replace("[AD_BUTTON_2]", btn2)
    if "[AD_BUTTON_1]" not in markdown_content: content += btn1 + btn2

    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        
        /* الحاوية الرئيسية */
        .game-article {{
            font-family: 'Cairo', sans-serif;
            direction: rtl;
            text-align: right;
            line-height: 1.8;
            color: #333333;           /* نص داكن للقراءة المريحة */
            background: #ffffff;      /* خلفية بيضاء */
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05); /* ظل خفيف جداً */
            width: 100%;
            max-width: 100%;          /* منع تجاوز العرض */
            box-sizing: border-box;   /* حساب الحواف بشكل صحيح */
            overflow-wrap: break-word; /* منع قص النص */
            word-wrap: break-word;
        }}
        
        /* الصور */
        .game-header-img {{
            width: 100%;
            height: auto;
            border-radius: 12px;
            margin-bottom: 25px;
        }}
        
        /* العناوين */
        h1 {{
            color: #2c3e50;
            font-weight: 900;
            font-size: 24px;
            border-bottom: 2px solid #3498db; /* خط أزرق تحت العنوان */
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        h2 {{
            color: #2980b9;
            margin-top: 35px;
            background: #f0f8ff; /* خلفية سماوية فاتحة جداً للعناوين الفرعية */
            padding: 10px 15px;
            border-right: 5px solid #2980b9;
            border-radius: 4px;
        }}
        
        strong {{ color: #e67e22; }}
        
        /* القوائم */
        ul, ol {{
            padding-right: 20px;
            background: #fafafa;
            padding: 15px 30px 15px 15px;
            border-radius: 8px;
        }}
        
        /* الأزرار */
        .gaming-btn {{
            display: inline-block;
            padding: 12px 25px;
            font-weight: 700;
            font-size: 16px;
            border-radius: 50px;
            text-decoration: none;
            width: 90%;
            max-width: 350px;
            transition: 0.3s;
            box-sizing: border-box;
        }}
        
        .download-btn {{
            background: #27ae60;
            color: #fff !important;
            box-shadow: 0 4px 10px rgba(39, 174, 96, 0.3);
        }}
        
        .gift-btn {{
            background: #8e44ad;
            color: #fff !important;
            box-shadow: 0 4px 10px rgba(142, 68, 173, 0.3);
        }}

        .gaming-btn:hover {{ transform: translateY(-2px); }}

        @media (max-width:600px) {{
            .game-article {{ padding: 15px; }}
            h1 {{ font-size: 20px; }}
            .gaming-btn {{ width: 100%; }}
        }}
    </style>

    <div class="game-article">
        <img src="{image_url}" alt="{title}" class="game-header-img">
        {content}
        <div style="text-align:center; margin-top:30px; border-top:1px solid #eee; padding-top:15px; font-size:12px; color:#888;">
            🎮 Loading Gaming Zone © 2026 | <a href="{STORE_PAGE}" style="color:#e67e22; text-decoration:none;">زيارة المتجر</a>
        </div>
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
    print("🎮 Gaming Bot (Light Theme + Auto Fix) Starting...")
    
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
            print("❌ Failed to write content.")
    else:
        print("❌ Failed to find a topic/game.")
