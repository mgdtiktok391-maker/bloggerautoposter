import requests
import json
import random
import os
import time

# =========================================================
# 🔐 الإعدادات والأسرار
# =========================================================
BLOG_ID = os.environ["BLOG_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

# اسم ملف الذاكرة الجديد الخاص بهذا البوت فقط
HISTORY_FILE = 'history_tech_solutions.json'

# =========================================================
# 🔄 دالة تجديد التوكن (لضمان الاستمرارية)
# =========================================================
def get_access_token():
    url = "https://oauth2.googleapis.com/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print("❌ Error refreshing token:", response.text)
        return None

# =========================================================
# 🎯 مجالات التفكير (Niches)
# =========================================================
NICHES = [
    "شرح مواقع الذكاء الاصطناعي الجديدة والمجانية (تصميم، كتابة، فيديو)",
    "حلول مشاكل الهواتف (أندرويد وآيفون) وصيانتها برمجياً",
    "شرح تطبيقات الهاتف الاحترافية (مونتاج، صور، إنتاجية)",
    "أسرار وحيل تقنية في الويندوز ومتصفح كروم",
    "طرق الربح من الإنترنت والعمل الحر للمبتدئين",
    "أمن المعلومات وحماية الحسابات من الاختراق",
    "شروحات تقنية حصرية ومفيدة جداً"
]

# تحميل الذاكرة الخاصة بهذا البوت
try:
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        published_history = json.load(f)
except:
    published_history = []

# دالة الاتصال بـ Gemini
def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        try:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            return None
    return None

# =========================================================
# 🧠 المرحلة 1: ابتكار العنوان
# =========================================================
def invent_new_topic():
    niche = random.choice(NICHES)
    # نرسل له آخر 20 عنوان لعدم التكرار
    recent_topics = published_history[-20:] if len(published_history) > 20 else published_history
    
    prompt = f"""
    بصفتك مدير محتوى تقني، اقترح عنوان مقال واحد فقط في مجال: {niche}.
    
    الشروط:
    1. العنوان يجب أن يكون جذاباً، حصرياً، وعملياً (يحل مشكلة أو يشرح أداة).
    2. ممنوع اقتراح أي عنوان يشبه هذه العناوين: {recent_topics}
    3. اكتب العنوان فقط باللغة العربية.
    """
    
    topic = call_gemini(prompt)
    if topic:
        return topic.strip().replace('"', '').replace('*', '')
    return None

# =========================================================
# ✍️ المرحلة 2: كتابة المحتوى
# =========================================================
def write_article(title):
    prompt = f"""
    اكتب مقالاً تقنياً احترافياً بعنوان: "{title}".
    
    التنسيق المطلوب (HTML):
    1. <h2>مقدمة</h2> جذابة.
    2. <h2>الشرح التفصيلي</h2> (شرح المشكلة أو الأداة).
    3. <ul>المميزات أو الخطوات</ul>.
    4. <h2>طريقة التنفيذ/الاستخدام</h2> (خطوة بخطوة).
    5. <div style="background:#f1f1f1; padding:15px; border-radius:10px;">نصيحة ذهبية</div>.
    6. <h2>الخاتمة</h2>.
    
    الشروط: مقال طويل (600+ كلمة)، لغة عربية فصحى وسلسة، منسق HTML جاهز للنشر.
    """
    return call_gemini(prompt)

# =========================================================
# 🚀 المرحلة 3: النشر
# =========================================================
def post_to_blogger(title, content, access_token):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts"
    
    # صورة عشوائية تقنية
    keywords = ["technology", "coding", "phone", "ai", "laptop"]
    img_url = f"https://source.unsplash.com/800x400/?{random.choice(keywords)}"
    
    final_html = f"""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="{img_url}" alt="{title}" style="width:100%; max-width:700px; border-radius:10px;">
    </div>
    {content}
    <br><hr>
    <p style="text-align:center; color:#888;">تم التحرير بواسطة بوت الشروحات الذكي - لودينغ تي في.</p>
    """
    
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {
        "kind": "blogger#post", 
        "blog": {"id": BLOG_ID}, 
        "title": title, 
        "content": final_html, 
        "labels": ["شروحات تقنية", "تكنولوجيا", "AI"]
    }
    
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        return True
    return False

# =========================================================
# 🏁 التشغيل
# =========================================================
if __name__ == "__main__":
    print("🤖 Tech Solutions Bot Started...")
    token = get_access_token()
    
    if token:
        new_topic = ""
        # محاولتان للابتكار
        for _ in range(2):
            suggested = invent_new_topic()
            if suggested and suggested not in published_history:
                new_topic = suggested
                break
        
        if new_topic:
            print(f"💡 Topic: {new_topic}")
            content = write_article(new_topic)
            if content:
                if post_to_blogger(new_topic, content, token):
                    print("✅ Published Successfully.")
                    # تحديث الذاكرة الخاصة
                    published_history.append(new_topic)
                    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                        json.dump(published_history, f, ensure_ascii=False, indent=2)
                else:
                    print("❌ Failed to Publish.")
            else:
                print("❌ Content Generation Failed.")
        else:
            print("❌ No Unique Topic Found.")
    else:
        print("❌ Token Error.")
