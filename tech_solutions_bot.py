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

HISTORY_FILE = "history_tech_solutions.json"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"
LABELS = ["شروحات_تقنية", "صيانة", "Technology", "HowTo"]

# =================== مجالات التفكير (NICHES) ===================
NICHES = [
    "حلول مشاكل ارتفاع حرارة الهاتف واستنزاف البطارية",
    "طرق استرجاع الصور والملفات المحذوفة (للاندرويد والايفون)",
    "شرح مواقع الذكاء الاصطناعي المجانية للتصميم والكتابة",
    "أسرار وحيل مخفية في الواتساب والماسنجر",
    "طريقة تسريع الويندوز والكمبيوتر بدون فورمات",
    "كيفية حماية حسابات السوشيال ميديا من الاختراق",
    "حل مشكلة الذاكرة ممتلئة رغم عدم وجود ملفات",
    "طرق الربح من الانترنت للمبتدئين (شروحات صادقة)"
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

# =================== المحرك (نفس كود بوت التطبيقات) ===================
def get_working_model():
    """هذه الدالة هي السر الذي يجعل بوت التطبيقات يعمل"""
    url = f"{GEMINI_API_ROOT}/v1beta/models?key={GEMINI_API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200: return "gemini-pro" # Fallback
        data = r.json()
        for model in data.get('models', []):
            name = model['name'].replace('models/', '')
            if 'generateContent' in model.get('supportedGenerationMethods', []):
                return name
        return "gemini-1.5-flash"
    except: return "gemini-pro"

def _rest_generate(prompt):
    """دالة الاتصال المباشر المأخوذة من البوت الناجح"""
    model_name = get_working_model()
    # print(f"DEBUG: Using Model: {model_name}") 
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

# =================== العقل المدبر (ابتكار وكتابة) ===================
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def invent_topic():
    history = load_history()
    recent = history[-10:] if len(history) > 10 else history
    niche = random.choice(NICHES)
    
    prompt = f"""
    تصرف كمدير محتوى تقني. اقترح عنواناً واحداً فقط لمقال حصري في مجال: "{niche}".
    الشروط:
    1. العنوان يجب أن يحل مشكلة أو يشرح طريقة.
    2. ممنوع تكرار هذه المواضيع: {recent}
    3. الرد يكون العنوان فقط (بدون علامات تنصيص).
    """
    return _rest_generate(prompt)

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def write_tech_article(topic):
    prompt = f"""
    اكتب مقالاً تقنياً احترافياً وشاملاً بعنوان: "{topic}"
    
    تنسيق Markdown المطلوب بدقة:
    # {topic}
    (اكتب هنا مقدمة جذابة تشرح المشكلة أو الأهمية)

    ## 🛠️ الأدوات المطلوبة / المتطلبات
    (قائمة نقطية بالأشياء التي نحتاجها)

    ## 🚀 الشرح التفصيلي (خطوة بخطوة)
    (استخدم أرقاماً 1. 2. 3. للشرح بدقة)

    ## 💡 مميزات وعيوب
    (اشرح الإيجابيات والسلبيات إن وجدت)

    ## ❓ الأسئلة الشائعة (FAQ)
    (سؤال وجواب)

    ## الخاتمة
    (نصيحة أخيرة)

    الشروط:
    - المقال طويل (أكثر من 500 كلمة).
    - اللغة عربية فصحى سهلة وممتعة.
    - استخدم الايموجي وعلامات التنسيق (Bold).
    """
    return _rest_generate(prompt)

# =================== النشر ===================
def build_html(title, markdown_content):
    # صورة عشوائية تقنية لضمان شكل جميل
    rand_id = random.randint(1, 1000)
    image_url = f"https://picsum.photos/seed/{rand_id}/800/400" 
    
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1);"></div>'
    
    # تحويل المارك داون إلى HTML
    content_html = md.markdown(markdown_content, extensions=['extra'])
    
    footer = """
    <hr>
    <div style="text-align:center; background:#f9f9f9; padding:15px; border-radius:10px; margin-top:20px;">
        <p>تم إعداد هذا الشرح بواسطة فريق التحرير التقني في لودينغ تي في 🛡️</p>
    </div>
    """
    
    return header + content_html + footer

def post_to_blogger(title, content):
    # استخدام مكتبة جوجل الرسمية للنشر (كما في البوت الناجح)
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    
    # جلب ID المدونة
    try:
        blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    except:
        # حل احتياطي إذا فشل جلب الـ ID بالرابط، نستخدم المتغير البيئي إذا كنت تعرفه، أو دعها كما هي
        blog_id = BLOG_ID 

    body = {"kind": "blogger#post", "title": title, "content": content, "labels": LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

# =================== التشغيل الرئيسي ===================
if __name__ == "__main__":
    print("🚀 Starting Tech Solutions Bot (Golden Engine)...")
    
    # 1. ابتكار العنوان
    raw_topic = invent_topic()
    if raw_topic:
        topic = raw_topic.strip().replace('"', '').replace('*', '')
        print(f"💡 Topic Idea: {topic}")
        
        # 2. كتابة المقال
        article_md = write_tech_article(topic)
        
        if article_md:
            print("📝 Content Generated. Processing...")
            
            # 3. تحويل وتجهيز HTML
            final_html = build_html(topic, article_md)
            
            # 4. النشر
            try:
                res = post_to_blogger(topic, final_html)
                print(f"🎉 PUBLISHED! URL: {res.get('url')}")
                
                # 5. حفظ الذاكرة
                save_history(topic)
                
            except Exception as e:
                print(f"❌ Publish Error: {e}")
        else:
            print("❌ Content generation failed (Empty response).")
    else:
        print("❌ Topic generation failed.")
