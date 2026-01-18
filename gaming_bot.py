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
# ⚠️ عدنا للموديل المستقر الذي نجح معك سابقاً
MODEL_NAME = "gemini-1.5-flash"

LABELS = ["Gaming", "Games_2026", "Android_Games", "شروحات_ألعاب", "Game_Booster"]

PROBLEMS = [
    "حل مشكلة اللاغ والتقطيع (Fix Lag)",
    "تفعيل أعلى فريمات (Unlock 90/120 FPS)",
    "أفضل كود حساسية (Best Sensitivity)",
    "حل مشكلة الخروج المفاجئ (Crash Fix)",
    "تسريع اللعبة للأجهزة الضعيفة (Game Booster)",
    "تقليل البينغ والدمج الوهمي (Fix Ping)"
]

# =================== 1. المستشعر: جلب الألعاب وصورها ===================
def get_real_trending_games():
    print("📡 Contacting Google Play Store...")
    try:
        # نبحث عن كلمات تضمن وجود نتائج
        queries = ["Action Games", "Racing Games", "Shooting Games", "Zombie Games"]
        chosen_query = random.choice(queries)
        
        results = search(chosen_query, lang='ar', country='sa', n_hits=30)
        
        games_data = []
        for game in results:
            games_data.append({
                "title": game['title'],
                "image": game['icon'] # رابط الصورة الحقيقي
            })
            
        if games_data:
            print(f"✅ Found {len(games_data)} games.")
            return games_data
        raise Exception("Zero results found")
    except Exception as e:
        print(f"⚠️ Scraper Warning: {e}")
        # بيانات احتياطية
        return [
            {"title": "PUBG Mobile", "image": "https://play-lh.googleusercontent.com/JRd05pyBH41qjgsJuWduRJpDeZG0Hnb0yjf2nWqO7VaGKL10-G5UIygxED-WNOc3pg"},
            {"title": "Free Fire", "image": "https://play-lh.googleusercontent.com/l4Zdf0hNq2123233e7eH_7nL1e15g2_6w2332"}
        ]

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
        # تصميم نظيف جداً للمنتج (بدون ألوان فاقعة)
        return f"""
        <div style="border: 1px solid #eee; padding: 20px; margin: 30px 0; text-align: center; border-radius: 10px; background-color: #f9f9f9;">
            <h3 style="margin:0 0 10px 0; color:#e67e22;">🛠️ عتاد المحترفين:</h3>
            <p style="color:#666;">لأفضل أداء، جرب: <strong>{p['name_ar']}</strong>.</p>
            <div style="margin:15px 0;"><img src="{p['image_url']}" style="width:100px;height:100px;object-fit:contain;border-radius:8px;background:#fff;"></div>
            <a href="{p['affiliate_link']}" target="_blank" style="display:inline-block; background:#e67e22; color:white; padding:10px 25px; text-decoration:none; border-radius:50px; font-weight:bold;">شاهد السعر 🛒</a>
        </div>
        """
    return ""

# =================== الاتصال بـ Gemini (الطريقة القديمة المضمونة) ===================
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def generate_content(prompt):
    # نستخدم v1beta مع الموديل الثابت 1.5-flash
    url = f"{GEMINI_API_ROOT}/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    print(f"🤖 Generating with {MODEL_NAME}...")
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"❌ API Error: {r.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# =================== المنطق الرئيسي ===================
def discover_game_trend():
    games_data = get_real_trending_games()
    selected = random.choice(games_data)
    
    game_name = selected['title']
    game_image = selected['image']
    problem = random.choice(PROBLEMS)
    
    print(f"🎯 Target: {game_name} + {problem}")
    
    prompt = f"اكتب عنوان مقال عربي جذاب (Clickbait) يجمع بين لعبة '{game_name}' وحل مشكلة '{problem}'. الرد بالعنوان فقط."
    title = generate_content(prompt)
    
    if title: 
        return title.strip().replace('"', '').replace('*', ''), game_name, game_image
    return None, None, None

def write_gaming_guide(title, game_name):
    if not title: return None
    product_box = get_product_recommendation()
    print(f"✍️ Writing Article: {title}")
    
    prompt = f"""
    اكتب مقالاً تقنياً طويلاً واحترافياً للجيمرز بعنوان: "{title}"
    استخدم تنسيق Markdown.
    
    الهيكل:
    1. مقدمة عن {game_name}.
    2. لماذا تحدث المشكلة؟
    3. [AD_BUTTON_1]
    4. خطوات الحل (إعدادات الجرافيك + خيارات المطور).
    5. [PRODUCT_BOX]
    6. الخاتمة.
    7. [AD_BUTTON_2]
    
    استخدم الايموجي 🎮🔥. لا تستخدم العناوين الملونة أو الصناديق.
    """
    
    content = generate_content(prompt)
    if content:
        content = content.replace("[PRODUCT_BOX]", product_box)
        return content
    return None

# =================== التصميم النظيف (Clean Design) ===================
def build_html(title, markdown_content, game_image_url):
    
    # 1. صورة اللعبة الحقيقية في الأعلى
    header_html = f"""
    <div style="text-align:center; margin-bottom: 25px;">
        <img src="{game_image_url}" alt="{title}" style="width: 110px; height: 110px; border-radius: 22px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
        <h1 style="color: #333; font-size: 22px; margin-top: 15px; line-height: 1.4;">{title}</h1>
    </div>
    """
    
    # أزرار مسطحة (Flat)
    btn1 = f"""<div style="text-align:center; margin:30px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn download-btn"><span class="btn-icon">📥</span> اضغط هنا للتحميل وتفعيل الإعدادات</a><p style="color:#999; font-size:12px; margin-top:5px;">(تم الفحص: آمن 100% ✅)</p></div>"""
    btn2 = f"""<div style="text-align:center; margin:40px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn gift-btn">💎 احصل على شدات/جواهر مجاناً</a></div>"""
    
    content = md.markdown(markdown_content, extensions=['extra'])
    content = content.replace("[AD_BUTTON_1]", btn1).replace("[AD_BUTTON_2]", btn2)
    # تنظيف العنوان المكرر
    content = content.replace(f"<h1>{title}</h1>", "")

    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        
        .game-article {{
            font-family: 'Cairo', sans-serif;
            direction: rtl;
            text-align: right;
            line-height: 1.8;
            color: #222;
            background: #fff; /* خلفية بيضاء */
            padding: 15px;
            width: 100%;
            box-sizing: border-box; /* يمنع الخروج عن الحواف */
            overflow-wrap: break-word; /* يكسر الكلمات الطويلة */
        }}
        
        /* تنسيق العناوين - بسيط جداً لمنع القص */
        h1, h2, h3 {{
            color: #2c3e50;
            margin-top: 25px;
            margin-bottom: 10px;
        }}
        
        h2 {{
            font-size: 20px;
            border-bottom: 2px solid #3498db;
            display: inline-block;
            padding-bottom: 5px;
        }}
        
        strong {{ color: #e67e22; }}
        
        /* القوائم */
        ul, ol {{ margin-right: 20px; }}
        li {{ margin-bottom: 8px; }}
        
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
        .download-btn {{ background: #27ae60; color: #fff !important; }}
        .gift-btn {{ background: #8e44ad; color: #fff !important; }}

        @media (max-width:600px) {{
            .game-article {{ padding: 10px; }}
            h1 {{ font-size: 18px; }}
            .gaming-btn {{ width: 100%; }}
        }}
    </style>

    <div class="game-article">
        {header_html}
        {content}
        <div style="text-align:center; margin-top:40px; border-top:1px solid #eee; padding-top:20px; font-size:12px; color:#aaa;">
            🎮 Loading Gaming Zone © 2026
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
    print("🎮 Gaming Bot (Restored Stability + Clean Design) Starting...")
    
    topic, game_name, game_image = discover_game_trend()
    
    if topic and game_name:
        article_md = write_gaming_guide(topic, game_name)
        if article_md:
            article_html = build_html(topic, article_md, game_image)
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
