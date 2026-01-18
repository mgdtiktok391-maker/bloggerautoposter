# -*- coding: utf-8 -*-
import os
import random
import json
import requests
import markdown as md
import backoff
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

# 🔗 رابط الإعلان (الكنز)
DIRECT_LINK = "https://otieu.com/4/10481709"

HISTORY_FILE = "history_tech_solutions.json"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"
LABELS = ["شروحات_تقنية", "صيانة", "Technology", "دليل_شامل"]

# =================== مجالات التفكير (NICHES) ===================
NICHES = [
    "صيانة الهواتف الذكية (Android & iOS)",
    "أدوات ومواقع الذكاء الاصطناعي (AI Tools)",
    "حماية المعلومات والأمن السيبراني (Cybersecurity)",
    "خبايا وأسرار الويندوز والكمبيوتر (Windows Tips)",
    "تطبيقات الإنتاجية والتعديل (Best Apps)",
    "الربح من الإنترنت والعمل الحر (Freelancing)",
    "حلول مشاكل الألعاب والإنترنت (Gaming & Network)",
    "أسرار التطبيقات الشهيرة (WhatsApp, Instagram, etc)"
]

# =================== إدارة الذاكرة ===================
def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def save_history(topic):
    history = load_history()
    history.append(topic)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# =================== المحرك الذهبي ===================
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
        if r.status_code == 200: 
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"❌ API Error: {r.text}")
            return None
    except Exception as e:
        print(f"❌ Request Failed: {e}")
        return None

# =================== العقل المدبر (الابتكار) ===================
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def invent_topic():
    history = load_history()
    recent = history[-15:] if len(history) > 15 else history
    niche = random.choice(NICHES)
    
    prompt = f"""
    تصرف كمدير تحرير لموقع تقني عالمي.
    أحتاج منك ابتكار "عنوان مقال تقني" واحد فقط في مجال: "{niche}".
    
    الشروط الصارمة:
    1. العنوان يجب أن يكون عن **مشكلة محددة جداً** أو **أداة معينة** أو **حيلة ذكية**.
    2. تجنب العناوين العامة. كن محدداً وجذاباً (Clicky).
    3. اللغة العربية.
    4. ممنوع تكرار هذه المواضيع: {recent}
    5. الرد يكون العنوان فقط.
    """
    return _rest_generate(prompt)

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def write_tech_article(topic):
    prompt = f"""
    اكتب مقالاً تقنياً احترافياً (دليل شامل) بعنوان: "{topic}"
    
    تعليمات التنسيق (Markdown):
    1. استخدم العناوين (#, ##) لتقسيم المقال.
    2. استخدم الايموجي 📱💻🔧 لتزيين الفقرات.
    3. الأسلوب يجب أن يكون سهلاً ومباشراً.
    
    الهيكل المطلوب:
    # {topic}
    (مقدمة تشرح المشكلة أو الأهمية في 3 أسطر)

    ## 🛠️ الأدوات أو المتطلبات
    (نقاط)

    ## 🚀 الشرح والخطوات العملية
    (اشرح الحل أو الطريقة بخطوات مرقمة 1. 2. 3. بشكل دقيق جداً)

    ## 💡 نصائح إضافية (Pro Tips)
    (نصائح لتجنب المشاكل مستقبلاً)

    ## ❓ الأسئلة الشائعة (FAQ)
    (3 أسئلة وإجاباتها)

    ## الخاتمة
    (خاتمة قصيرة)
    """
    return _rest_generate(prompt)

# =================== التصميم والحقن (Design & Injection) ===================
def build_styled_html(title, markdown_content):
    rand_id = random.randint(1, 1000)
    image_url = f"https://picsum.photos/seed/{rand_id}/800/400" 
    
    # 1. تحويل المحتوى الأساسي
    content_html = md.markdown(markdown_content, extensions=['extra'])
    
    # 2. تصميم الأزرار المتوهجة
    btn_style = """
    display: block; margin: 30px auto; padding: 15px 30px; 
    text-align: center; font-weight: bold; color: #fff; border-radius: 50px; 
    text-decoration: none; font-size: 18px; width: fit-content;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: transform 0.2s;
    animation: glow 2s infinite;
    """
    
    # زر 1: شاهد من هنا (أحمر)
    btn1_html = f"""
    <div style="text-align:center; margin: 20px 0;">
        <a href="{DIRECT_LINK}" target="_blank" style="{btn_style} background: linear-gradient(45deg, #ff416c, #ff4b2b);">
            👀 شاهد من هنا
        </a>
    </div>
    """
    
    # زر 2: كورسات تقنية (أزرق/بنفسجي)
    btn2_html = f"""
    <div style="text-align:center; margin: 40px 0;">
        <a href="{DIRECT_LINK}" target="_blank" style="{btn_style} background: linear-gradient(45deg, #2193b0, #6dd5ed);">
            🎓 كورسات تقنية
        </a>
    </div>
    """
    
    # 3. حقن الأزرار في الأماكن الصحيحة
    # الحقن الأول: بعد المقدمة (نبحث عن أول عنوان فرعي H2 ونضع الزر قبله)
    if "<h2>" in content_html:
        # نقسم النص عند أول H2
        parts = content_html.split("<h2>", 1)
        # نضع الزر الأول بين المقدمة والعنوان الأول
        content_html = parts[0] + btn1_html + "<h2>" + parts[1]
    else:
        # إذا لم نجد عنواناً، نضعه في البداية
        content_html = btn1_html + content_html

    # الحقن الثاني: في النهاية (نضيف الزر الثاني قبل الخاتمة)
    content_html += btn2_html

    # 4. القالب والتصميم النهائي (مع إصلاح الموبايل)
    styled_template = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;800&display=swap');
        
        /* أنيميشن التوهج */
        @keyframes glow {{
            0% {{ box-shadow: 0 0 5px rgba(0,0,0,0.2); transform: scale(1); }}
            50% {{ box-shadow: 0 0 20px rgba(255, 75, 43, 0.6); transform: scale(1.05); }}
            100% {{ box-shadow: 0 0 5px rgba(0,0,0,0.2); transform: scale(1); }}
        }}

        .tech-article {{
            font-family: 'Tajawal', sans-serif;
            line-height: 1.8;
            color: #333;
            background: #fff;
            text-align: right;
            direction: rtl;
            overflow-x: hidden; /* لمنع التمرير الأفقي في الموبايل */
        }}
        
        .tech-header-img {{
            width: 100%;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            margin-bottom: 30px;
        }}
        
        .tech-article h1 {{
            color: #2c3e50;
            font-size: 26px;
            font-weight: 800;
            margin-bottom: 20px;
            border-bottom: 3px solid #3498db;
            display: inline-block;
            padding-bottom: 10px;
        }}
        
        .tech-article h2 {{
            background: #f0f8ff;
            color: #2980b9;
            padding: 12px 15px;
            border-radius: 10px;
            border-right: 5px solid #2980b9;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 20px;
            font-weight: 700;
        }}
        
        .tech-article ul, .tech-article ol {{
            background: #fdfdfd;
            padding: 20px 40px 20px 20px;
            border: 1px solid #eee;
            border-radius: 10px;
        }}
        
        blockquote {{
            background-color: #fff8e1;
            border-right: 5px solid #ffc107;
            margin: 20px 0;
            padding: 15px;
            border-radius: 8px;
            color: #856404;
            font-weight: bold;
        }}
        
        .tech-footer {{
            margin-top: 50px;
            padding: 20px;
            background: #222;
            color: #fff;
            text-align: center;
            border-radius: 12px;
            font-size: 14px;
        }}

        /* 📱 إصلاح الموبايل (Mobile Responsive) */
        @media only screen and (max-width: 600px) {{
            .tech-article {{
                padding: 10px !important;
                font-size: 16px;
            }}
            .tech-article h1 {{ font-size: 22px; }}
            .tech-article h2 {{ font-size: 18px; padding: 10px; }}
            .tech-article ul, .tech-article ol {{ padding: 15px 30px 15px 15px; }}
        }}
    </style>

    <div class="tech-article">
        <img src="{image_url}" alt="{title}" class="tech-header-img">
        {content_html}
        <div class="tech-footer">
            <p>🛡️ تم إعداد هذا الشرح بواسطة فريق التحرير التقني في منصة لودينغ</p>
        </div>
    </div>
    """
    return styled_template

def post_to_blogger(title, content):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    try:
        blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    except:
        blog_id = BLOG_ID 

    body = {"kind": "blogger#post", "title": title, "content": content, "labels": LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

# =================== التشغيل ===================
if __name__ == "__main__":
    print("🚀 Starting Tech Solutions Bot (Ads & Responsive Mode)...")
    
    raw_topic = None
    for i in range(3):
        print(f"🧠 Brainstorming attempt {i+1}...")
        temp_topic = invent_topic()
        if temp_topic:
            clean_topic = temp_topic.strip().replace('"', '').replace('*', '')
            if len(clean_topic) > 10 and len(clean_topic) < 100: 
                raw_topic = clean_topic
                break
    
    if raw_topic:
        print(f"💡 Topic Selected: {raw_topic}")
        article_md = write_tech_article(raw_topic)
        
        if article_md:
            print("📝 Content Generated. Injecting Ads & Styling...")
            final_html = build_styled_html(raw_topic, article_md)
            
            try:
                res = post_to_blogger(raw_topic, final_html)
                print(f"🎉 PUBLISHED! URL: {res.get('url')}")
                save_history(raw_topic)
            except Exception as e:
                print(f"❌ Publish Error: {e}")
        else:
            print("❌ Content generation failed.")
    else:
        print("❌ Failed to invent a valid topic.")
