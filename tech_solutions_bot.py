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

# 🔗 رابط الإعلان
DIRECT_LINK = "https://otieu.com/4/10481709"

HISTORY_FILE = "history_tech_solutions.json"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"
LABELS = ["شروحات_تقنية", "صيانة", "Technology", "دليل_شامل"]

# =================== مجالات التفكير ===================
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

# =================== العقل المدبر ===================
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

# =================== التصميم البسيط (Simple Layout) ===================
def build_styled_html(title, markdown_content):
    rand_id = random.randint(1, 1000)
    image_url = f"https://picsum.photos/seed/{rand_id}/800/400" 
    
    content_html = md.markdown(markdown_content, extensions=['extra'])
    
    # ستايل الأزرار (متجاوب مع الموبايل)
    btn_style = """
    display: block; margin: 30px auto; padding: 12px 20px; 
    text-align: center; font-weight: bold; color: #fff; border-radius: 50px; 
    text-decoration: none; font-size: 16px; width: fit-content; max-width: 90%;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2); transition: transform 0.2s;
    animation: glow 2s infinite;
    """
    
    btn1_html = f"""
    <div style="text-align:center; margin: 25px 0;">
        <a href="{DIRECT_LINK}" target="_blank" style="{btn_style} background: linear-gradient(45deg, #ff416c, #ff4b2b);">
            👀 شاهد من هنا
        </a>
    </div>
    """
    
    btn2_html = f"""
    <div style="text-align:center; margin: 40px 0;">
        <a href="{DIRECT_LINK}" target="_blank" style="{btn_style} background: linear-gradient(45deg, #2193b0, #6dd5ed);">
            🎓 كورسات تقنية
        </a>
    </div>
    """
    
    # حقن الأزرار
    if "<h2>" in content_html:
        parts = content_html.split("<h2>", 1)
        content_html = parts[0] + btn1_html + "<h2>" + parts[1]
    else:
        content_html = btn1_html + content_html

    content_html += btn2_html

    # القالب البسيط (بدون صناديق معقدة)
    styled_template = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;800&display=swap');
        
        /* ضبط شامل لكل العناصر لتبقى داخل الحدود */
        * {{
            box-sizing: border-box !important;
            max-width: 100% !important;
        }}

        @keyframes glow {{
            0% {{ box-shadow: 0 0 5px rgba(0,0,0,0.2); transform: scale(1); }}
            50% {{ box-shadow: 0 0 15px rgba(255, 75, 43, 0.5); transform: scale(1.02); }}
            100% {{ box-shadow: 0 0 5px rgba(0,0,0,0.2); transform: scale(1); }}
        }}

        .tech-article {{
            font-family: 'Tajawal', sans-serif;
            line-height: 1.8;
            color: #222;
            background: #fff;
            text-align: right;
            direction: rtl;
            width: 100%;
            overflow-wrap: break-word; /* كسر الكلمات الطويلة */
            word-wrap: break-word;
        }}
        
        .tech-header-img {{
            width: 100%;
            height: auto;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .tech-article h1 {{
            color: #2c3e50;
            font-size: 24px;
            font-weight: 800;
            margin-bottom: 15px;
            line-height: 1.4;
        }}
        
        .tech-article h2 {{
            color: #0d47a1; /* لون أزرق غامق بسيط */
            margin-top: 25px;
            margin-bottom: 10px;
            font-size: 20px;
            font-weight: 700;
            border-bottom: 1px solid #ddd; /* خط بسيط أسفل العنوان */
            padding-bottom: 5px;
        }}
        
        .tech-article ul, .tech-article ol {{
            padding-right: 20px; /* مسافة بسيطة للقوائم */
        }}

        .tech-article li {{
            margin-bottom: 8px;
        }}
        
        /* إزالة الصناديق تماماً - تحويل الاقتباسات لنص عادي مائل */
        blockquote {{
            background: none !important;
            border: none !important;
            padding: 10px 0 !important;
            margin: 15px 0 !important;
            color: #555;
            font-style: italic;
            border-right: 3px solid #ccc !important; /* خط رمادي بسيط جداً على اليمين */
            padding-right: 15px !important;
        }}
        
        .tech-footer {{
            margin-top: 40px;
            padding: 15px;
            background: #f1f1f1;
            color: #333;
            text-align: center;
            border-radius: 8px;
            font-size: 13px;
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
    print("🚀 Starting Tech Solutions Bot (Clean Layout)...")
    
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
            print("📝 Content Generated. Styling...")
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
