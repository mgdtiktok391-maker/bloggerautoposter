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
# ⚠️ استدعاء المكتبة الموجودة في ملفك لجلب الألعاب الحقيقية
from google_play_scraper import Sort, collection

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
MODEL_NAME = "gemini-1.5-flash" 

LABELS = ["Gaming", "Games_2026", "Android_Games", "شروحات_ألعاب", "Game_Booster"]

# المشاكل التقنية التي سنطبقها على الألعاب التي نكتشفها
PROBLEMS = [
    "حل مشكلة اللاغ والتقطيع (Fix Lag)",
    "تفعيل أعلى فريمات (Unlock 90/120 FPS)",
    "أفضل كود حساسية (Best Sensitivity)",
    "حل مشكلة الخروج المفاجئ (Crash Fix)",
    "تسريع اللعبة للأجهزة الضعيفة (Game Booster)",
    "تقليل البينغ والدمج الوهمي (Fix Ping)"
]

# =================== 1. المستشعر: جلب الألعاب من جوجل بلاي ===================
def get_real_trending_games():
    """يجلب قائمة حقيقية بالألعاب الترند حالياً من متجر جوجل"""
    print("📡 Contacting Google Play Store...")
    try:
        # نجلب قائمة "أفضل الألعاب المجانية" في السعودية (كمقياس للشرق الأوسط)
        result = collection(
            collection=collection.TOP_FREE,
            category='GAME',
            lang='ar',      # اللغة العربية
            country='sa',   # المنطقة (السعودية تعطي نتائج دقيقة للترند العربي)
            sort=Sort.NEWEST, # نجلب الألعاب الجديدة والساخنة
            count=40        # نفحص أول 40 لعبة
        )
        # استخراج أسماء الألعاب فقط
        games_list = [game['title'] for game in result]
        print(f"✅ Found {len(games_list)} trending games.")
        return games_list
    except Exception as e:
        print(f"⚠️ Scraper Error: {e}")
        # قائمة طوارئ في حال فشل الاتصال بالمتجر
        return ["PUBG Mobile", "Free Fire", "Call of Duty: Warzone Mobile", "Roblox", "EA SPORTS FC Mobile", "Subway Surfers"]

# =================== دوال المساعدة ===================
def load_json(filename):
    if not os.path.exists(filename): return []
    with open(filename, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return []

def save_history(topic):
    history = load_json(HISTORY_FILE)
    history.append(topic)
    if len(history) > 100: history = history[-100:] # نحفظ آخر 100 لمنع التكرار
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_product_recommendation():
    products = load_json(PRODUCTS_FILE)
    if products:
        p = random.choice(products)
        return f"""
        <div style="background:#1e272e; border:2px dashed #ff9f43; padding:20px; margin:30px 0; text-align:center; border-radius:15px; box-shadow: 0 0 15px rgba(255, 159, 67, 0.1);">
            <h3 style="margin:0 0 10px 0; color:#ff9f43;">🛠️ سلاح المحترفين:</h3>
            <p style="color:#d2dae2; font-size:16px;">لتحصل على أفضل أداء في هذه اللعبة، ننصحك باستخدام <strong>{p['name_ar']}</strong>.</p>
            <div style="margin: 15px 0;">
                <img src="{p['image_url']}" style="width:100px; height:100px; object-fit:contain; border-radius:10px; background:#fff; padding:5px;">
            </div>
            <a href="{p['affiliate_link']}" target="_blank" style="display:inline-block; background:linear-gradient(45deg, #ff9f43, #ee5253); color:white; padding:10px 25px; text-decoration:none; border-radius:50px; font-weight:bold;">شاهد السعر 🛒</a>
        </div>
        """
    return ""

# =================== الاتصال بـ Gemini ===================
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def _rest_generate(prompt):
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
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200: 
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except Exception as e: 
        print(f"⚠️ API Error: {e}")
        return None

# =================== المنطق الذكي ===================
def discover_game_trend():
    # 1. جلب الألعاب الحقيقية من المتجر
    real_games = get_real_trending_games()
    history = load_json(HISTORY_FILE)
    
    # 2. تنظيف القائمة (حذف ما تم نشره سابقاً)
    # ملاحظة: التحقق هنا بسيط، سنعتمد على العنوان الكامل لاحقاً
    
    # 3. اختيار عشوائي للعبة + مشكلة
    selected_game = random.choice(real_games)
    selected_problem = random.choice(PROBLEMS)
    
    print(f"🎯 Selected Target: {selected_game} + {selected_problem}")
    
    # 4. الطلب من Gemini صياغة العنوان
    prompt = f"""
    لدينا لعبة موبايل حقيقية اسمها: "{selected_game}"
    ولدينا مشكلة تقنية: "{selected_problem}"
    
    المهمة: اكتب عنوان مقال عربي "جذاب جداً" (Clickbait) يجمع بين اسم اللعبة وحل هذه المشكلة.
    مثال: "وأخيراً! حل مشكلة اللاغ في لعبة {selected_game} للأجهزة الضعيفة 2026"
    
    الشروط:
    - العنوان بالعربية فقط.
    - لا تضع علامات تنصيص "".
    - تأكد أن العنوان غير موجود في هذه القائمة: {history}
    """
    
    title = _rest_generate(prompt)
    if title: return title.strip().replace('"', '').replace('*', '')
    
    # fallback بسيط جداً
    return f"شرح لعبة {selected_game} : {selected_problem} - حل نهائي 2026"

def write_gaming_guide(title):
    product_box = get_product_recommendation()
    print(f"✍️ Writing Content: {title}")
    
    prompt = f"""
    اكتب مقالاً تقنياً احترافياً ومفصلاً للجيمرز بعنوان: "{title}"
    استخدم تنسيق Markdown.
    
    يجب أن يتضمن المقال:
    1. مقدمة قوية عن اللعبة المذكورة في العنوان.
    2. شرح دقيق للإعدادات (Graphics/Audio) المناسبة لهذه اللعبة تحديداً.
    3. خطوات تقنية لتسريع الهاتف (Developer Options).
    4. [AD_BUTTON_1] (مكان زر التحميل).
    5. حلول تقنية (DNS/Clearing Cache) خاصة بالأندرويد.
    6. نصيحة باستخدام أداة خارجية (Product Recommendation).
    7. [PRODUCT_BOX]
    8. الخاتمة.
    9. [AD_BUTTON_2]
    
    استخدم ايموجي 🎮🔥 وتحدث بلغة الشباب.
    """
    
    content = _rest_generate(prompt)
    if content:
        content = content.replace("[PRODUCT_BOX]", product_box)
    return content

# =================== التصميم والنشر ===================
def build_html(title, markdown_content):
    rand_id = random.randint(1, 1000)
    image_url = f"https://picsum.photos/seed/{rand_id}/800/450?grayscale"
    
    btn1 = f"""<div style="text-align:center; margin:35px 0;"><a href="{AD_LINK}" target="_blank" class="gaming-btn download-btn"><span class="btn-icon">📥</span> اضغط هنا للتحميل وتفعيل الإعدادات</a><p style="color:#7f8fa6; font-size:12px; margin-top:8px;">(آمن 100% ✅)</p></div>"""
    btn2 = f"""<div style="text-align:center; margin:40px 0; padding:20px; background:#2f3640; border-radius:15px; border:1px dashed #8c7ae6;"><h4 style="color:#fbc531; margin:0 0 15px 0;">🎁 هدية حصرية:</h4><a href="{AD_LINK}" target="_blank" class="gaming-btn gift-btn">💎 احصل على شدات/جواهر مجاناً</a></div>"""
    
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
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    try: blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    except: return None
    body = {"kind": "blogger#post", "title": f"🔥 {title}", "content": content, "labels": LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

# =================== التشغيل ===================
if __name__ == "__main__":
    print("🎮 Gaming Bot (Real-Time Scraper) Starting...")
    
    topic = discover_game_trend()
    
    if topic:
        article_md = write_gaming_guide(topic)
        if article_md:
            article_html = build_html(topic, article_md)
            try:
                res = post_to_blogger(topic, article_html)
                if res:
                    print(f"✅ Published: {topic}")
                    save_history(topic)
                else: print("❌ Blog ID Error")
            except Exception as e: print(f"❌ Error: {e}")
    else:
        print("❌ Failed to generate topic.")
