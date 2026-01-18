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

# =================== إعدادات النظام ===================
# يتم جلب المفاتيح من إعدادات المستودع (Secrets)
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

# 🔗 الروابط الخاصة بك (تم تحديثها)
AD_LINK = "https://otieu.com/4/10483041"  # رابط مونيتاغ المباشر
STORE_PAGE = "https://www.loadingapk.online/p/loading-store.html" # رابط صفحة المتجر

# ملفات البيانات
PRODUCTS_FILE = "products.json"
HISTORY_FILE = "history_gaming.json"

# إعدادات Gemini API (نستخدم requests مباشرة لضمان التوافق مع مكتباتك)
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

# تصنيفات بلوجر للمقال
LABELS = ["Gaming", "Games_2026", "شروحات_ألعاب", "Game_Booster", "حلول_تقنية", "PUBG_Mobile", "Free_Fire"]

# قائمة المشاكل التقنية (سيطبقها البوت على أحدث الألعاب)
PROBLEMS = [
    "حل مشكلة اللاغ وهبوط الفريمات (Fix Lag & Drop FPS)",
    "تفعيل 90 و 120 فريم حقيقي (Unlock Max FPS)",
    "أفضل كود حساسية لتثبيت الإيم (No Recoil Config)",
    "حل مشكلة ارتفاع حرارة الهاتف واستنزاف البطارية",
    "أسرع DNS للألعاب في الشرق الأوسط (Ping Reducer)",
    "ضبط إعدادات الجرافيك للحصول على دقة HDR",
    "تحميل ملف ماجيك بوليت وتثبيت السلاح (Magic Bullet)",
    "إزالة العشب والضباب (No Grass Config)"
]

# =================== دوال المساعدة ===================
def load_json(filename):
    if not os.path.exists(filename): return []
    with open(filename, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_history(topic):
    history = load_json(HISTORY_FILE)
    history.append(topic)
    if len(history) > 60: history = history[-60:] # نحفظ آخر 60 عنوان لعدم التكرار
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_product_recommendation():
    """يختار منتجاً من ملف المنتجات ويحوله لإعلان داخل المقال"""
    products = load_json(PRODUCTS_FILE)
    if products:
        p = random.choice(products)
        # تصميم صندوق المنتج بشكل جذاب
        return f"""
        <div style="background:#1e272e; border:2px dashed #ff9f43; padding:20px; margin:30px 0; text-align:center; border-radius:15px; box-shadow: 0 0 15px rgba(255, 159, 67, 0.1);">
            <h3 style="margin:0 0 10px 0; color:#ff9f43;">🛠️ نصيحة للمحترفين:</h3>
            <p style="color:#d2dae2; font-size:16px;">لتحصل على تجربة لعب مريحة وتبريد مثالي، ننصحك باستخدام <strong>{p['name_ar']}</strong>.</p>
            <div style="margin: 15px 0;">
                <img src="{p['image_url']}" style="width:120px; height:120px; object-fit:contain; border-radius:10px; background:#fff; padding:5px;">
            </div>
            <a href="{p['affiliate_link']}" target="_blank" style="display:inline-block; background:linear-gradient(45deg, #ff9f43, #ee5253); color:white; padding:10px 25px; text-decoration:none; border-radius:50px; font-weight:bold;">شاهد السعر والتفاصيل 🛒</a>
            <br>
            <a href="{STORE_PAGE}" style="color:#7f8fa6; font-size:14px; text-decoration:none; margin-top:15px; display:inline-block; border-bottom:1px solid #7f8fa6;">تصفح باقي المتجر 👈</a>
        </div>
        """
    return ""

# =================== محرك Gemini الذكي (باستخدام requests) ===================
def get_working_model():
    """يحاول العثور على موديل متاح للعمل"""
    url = f"{GEMINI_API_ROOT}/v1beta/models?key={GEMINI_API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200: return "gemini-1.5-flash"
        data = r.json()
        # نفضل الموديلات السريعة والذكية
        preferred_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        for pref in preferred_models:
            for model in data.get('models', []):
                if pref in model['name']:
                    return model['name'].replace('models/', '')
        return "gemini-1.5-flash"
    except: return "gemini-1.5-flash"

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def _rest_generate(prompt):
    """دالة الاتصال بـ Gemini API مباشرة"""
    model_name = get_working_model()
    url = f"{GEMINI_API_ROOT}/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    # إعدادات الأمان (مفتوحة لضمان عدم حظر محتوى الألعاب)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": safety_settings,
        "generationConfig": {
            "temperature": 0.9, # إبداع عالي
            "topK": 40,
            "topP": 0.95,
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200: 
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"API Error: {r.text}")
        return None
    except Exception as e: 
        print(f"Connection Error: {e}")
        return None

# =================== 1. صائد الترندات (Trend Hunter) ===================
def discover_game_trend():
    problem = random.choice(PROBLEMS)
    history = load_json(HISTORY_FILE)
    
    print("🔍 Searching for trends...")
    
    prompt = f"""
    أنت خبير ألعاب (Gamer) ومطلع على أحدث الألعاب الشائعة (Trending Games) في العالم العربي لعام 2025 و 2026.
    
    المهمة: اقترح عنوان مقال "فيروسي" (Clickbait) يجمع بين:
    1. اسم لعبة موبايل مشهورة جداً وشعبية (مثل: PUBG Mobile, Free Fire, COD Warzone, Genshin Impact, أو أي لعبة صاعدة جديدة).
    2. المشكلة التقنية التالية: "{problem}".
    
    الشروط:
    - العنوان يجب أن يكون باللغة العربية ومثير جداً للاهتمام.
    - يجب أن يوحي العنوان بوجود "حل سحري" أو "ملف جديد".
    - ممنوع تكرار أي عنوان من هذه القائمة السابقة: {history}
    
    مثال للرد المقبول: "أخيراً! ملف تفعيل 120 فريم للعبة ببجي موبايل التحديث الجديد - بدون باند 😱🔥"
    
    الرد: (أعطني العنوان فقط بدون أي مقدمات)
    """
    
    title = _rest_generate(prompt)
    if title:
        return title.strip().replace('"', '').replace('*', '')
    return None

# =================== 2. كاتب الدليل ===================
def write_gaming_guide(title):
    product_box = get_product_recommendation()
    
    print(f"✍️ Writing content for: {title}")
    
    prompt = f"""
    أنت كاتب محتوى ألعاب (Gaming Tech Writer) محترف. اكتب مقالاً تفصيلياً وحماسياً جداً بعنوان:
    "{title}"
    
    استخدم تنسيق Markdown وركز على تقديم خطوات عملية.
    
    الهيكل المطلوب للمقال:
    
    # {title}
    (اكتب مقدمة نارية تشرح حجم المشكلة وكيف أن هذا الحل سيجعل اللاعب محترفاً ويهزم الجميع)

    ## ⚙️ أولاً: إعدادات الجرافيك السرية (Graphics Settings)
    (اشرح بالتفصيل أفضل الأرقام والإعدادات من داخل اللعبة للحصول على أعلى أداء)

    ## 🚀 ثانياً: خطوات تسريع النظام (System Booster)
    (اشرح كيفية استخدام خيارات المطور Developer Options في الأندرويد لتقليل اللاغ)

    [AD_BUTTON_1]

    ## 🔧 ثالثاً: الحل التقني والملفات المطلوبة
    (تحدث تقنياً عن طريقة تفعيل الملفات أو ضبط الـ DNS أو كود الحساسية، واجعل القارئ يشعر أنه يحصل على سر كبير)

    ## 💎 نصيحة ذهبية: استخدم هذه الأداة للفوز
    (تحدث عن أن المحترفين يستخدمون أدوات مساعدة خارجية)
    [PRODUCT_BOX]

    ## الخاتمة
    (خاتمة قصيرة ومشجعة)
    [AD_BUTTON_2]
    
    ملاحظة هامة:
    - استخدم لغة الشباب والجيمرز (مثل: "جلد السيرفر"، "ايم مسطرة"، "فريمات طيارة").
    - استخدم الايموجي بكثرة: 🎮 🔥 ⚡ 😱 💣.
    """
    
    content = _rest_generate(prompt)
    if content:
        # حقن صندوق المنتج
        content = content.replace("[PRODUCT_BOX]", product_box)
    return content

# =================== التصميم والحقن (Injection) ===================
def build_html(title, markdown_content):
    # صور عشوائية للألعاب (تكنولوجيا غامضة)
    rand_id = random.randint(1, 1000)
    image_url = f"https://picsum.photos/seed/{rand_id}/800/450?grayscale&blur=2" # صورة غامضة قليلاً
    
    # 1. زر التحميل (إعلان مونيتاغ) - الأكثر جاذبية
    btn1_html = f"""
    <div style="text-align:center; margin: 35px 0;">
        <a href="{AD_LINK}" target="_blank" class="gaming-btn download-btn">
            <span class="btn-icon">📥</span> اضغط هنا لتحميل الملف وتفعيل الإعدادات
        </a>
        <p style="color:#7f8fa6; font-size:12px; margin-top:8px;">(تم الفحص: الملف آمن 100% ✅)</p>
    </div>
    """

    # 2. زر الهدايا (إعلان مونيتاغ) - تكميلي
    btn2_html = f"""
    <div style="text-align:center; margin: 40px 0; padding:20px; background:#2f3640; border-radius:15px; border: 1px dashed #8c7ae6;">
        <h4 style="color:#fbc531; margin-bottom:15px; margin-top:0;">🎁 هدية حصرية للزوار اليوم:</h4>
        <a href="{AD_LINK}" target="_blank" class="gaming-btn gift-btn">
            💎 اضغط هنا للحصول على شدات/جواهر مجاناً
        </a>
    </div>
    """
    
    # تحويل الماركداون إلى HTML
    content_html = md.markdown(markdown_content, extensions=['extra'])
    
    # استبدال العلامات بالأزرار
    if "[AD_BUTTON_1]" in content_html:
        content_html = content_html.replace("[AD_BUTTON_1]", btn1_html)
    else:
        content_html += btn1_html # وضع افتراضي
        
    if "[AD_BUTTON_2]" in content_html:
        content_html = content_html.replace("[AD_BUTTON_2]", btn2_html)
    else:
        content_html += btn2_html # وضع افتراضي

    # قالب HTML النهائي (Dark Gaming Mode)
    html = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        
        .game-article {{
            font-family: 'Cairo', sans-serif;
            direction: rtl;
            text-align: right;
            line-height: 1.8;
            color: #dcdde1;
            background: #191919;
            padding: 15px;
            border-radius: 12px;
            overflow: hidden;
        }}
        
        .game-header-img {{
            width: 100%;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 2px solid #e1b12c;
            box-shadow: 0 0 20px rgba(225, 177, 44, 0.15);
        }}
        
        .game-article h1 {{ color: #e1b12c; font-weight: 900; font-size: 24px; margin-bottom: 20px; border-bottom: 1px solid #353b48; padding-bottom: 15px; }}
        .game-article h2 {{ color: #00a8ff; margin-top: 35px; background: #2f3640; padding: 10px 15px; border-right: 5px solid #00a8ff; border-radius: 8px; font-size: 20px; }}
        .game-article strong {{ color: #4cd137; }}
        .game-article ul, .game-article ol {{ background: #2f3640; padding: 20px 40px 20px 20px; border-radius: 10px; margin-bottom: 20px; }}
        .game-article li {{ margin-bottom: 10px; }}
        
        /* أزرار الجيمينج */
        .gaming-btn {{
            display: inline-block;
            padding: 15px 20px;
            text-decoration: none;
            font-weight: 900;
            font-size: 18px;
            border-radius: 50px;
            transition: all 0.3s ease;
            width: 90%;
            max-width: 400px;
            position: relative;
        }}
        
        .download-btn {{
            background: linear-gradient(45deg, #44bd32, #009432);
            color: #fff !important;
            box-shadow: 0 5px 15px rgba(68, 189, 50, 0.3);
            border: 2px solid #b8e994;
            animation: pulse-green 2s infinite;
        }}
        
        .gift-btn {{
            background: linear-gradient(45deg, #8c7ae6, #9c88ff);
            color: #fff !important;
            box-shadow: 0 5px 15px rgba(140, 122, 230, 0.3);
            border: 2px solid #dcd6f7;
            animation: pulse-purple 2s infinite;
        }}
        
        .gaming-btn:hover {{ transform: scale(1.03); filter: brightness(1.1); }}
        
        @keyframes pulse-green {{
            0% {{ box-shadow: 0 0 0 0 rgba(68, 189, 50, 0.7); }}
            70% {{ box-shadow: 0 0 0 15px rgba(68, 189, 50, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(68, 189, 50, 0); }}
        }}
        
        @keyframes pulse-purple {{
            0% {{ box-shadow: 0 0 0 0 rgba(140, 122, 230, 0.7); }}
            70% {{ box-shadow: 0 0 0 15px rgba(140, 122, 230, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(140, 122, 230, 0); }}
        }}

        @media (max-width: 600px) {{
            .game-article {{ padding: 10px; }}
            .gaming-btn {{ font-size: 16px; padding: 12px; }}
            .game-article h1 {{ font-size: 20px; }}
        }}
    </style>

    <div class="game-article">
        <img src="{image_url}" alt="{title}" class="game-header-img">
        {content_html}
        <div style="text-align:center; margin-top:30px; border-top:1px solid #333; padding-top:15px; color:#718093; font-size:12px;">
            🎮 Loading Gaming Zone © 2026 | <a href="{STORE_PAGE}" style="color:#e1b12c; text-decoration:none;">منتجات الجيمرز</a>
        </div>
    </div>
    """
    return html

def post_to_blogger(title, content):
    print("🚀 Publishing to Blogger...")
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    
    try:
        # محاولة جلب آيدي المدونة تلقائياً
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        blog_id = blog["id"]
    except Exception as e:
        print(f"⚠️ Could not fetch blog ID automatically: {e}")
        # يمكنك وضع الآيدي يدوياً هنا إذا فشل الجلب
        # blog_id = "YOUR_BLOG_ID" 
        return None

    body = {
        "kind": "blogger#post",
        "title": f"🔥 {title}",
        "content": content,
        "labels": LABELS
    }
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

# =================== التشغيل ===================
if __name__ == "__main__":
    print("🎮 Gaming Bot (Requests Version) Starting...")
    
    topic = discover_game_trend()
    
    if topic:
        print(f"🎯 New Trend Found: {topic}")
        article_md = write_gaming_guide(topic)
        
        if article_md:
            print("📝 Content Generated. Building HTML...")
            final_html = build_html(topic, article_md)
            
            try:
                res = post_to_blogger(topic, final_html)
                if res:
                    print(f"✅ Published! URL: {res.get('url')}")
                    save_history(topic)
                else:
                    print("❌ Published failed (No Blog ID).")
            except Exception as e:
                print(f"❌ Publish Error: {e}")
        else:
            print("❌ Content generation failed.")
    else:
        print("❌ No new trend found today.")
