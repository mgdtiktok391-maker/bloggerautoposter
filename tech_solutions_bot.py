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

HISTORY_FILE = 'history_tech_solutions.json'

# =========================================================
# 🔄 دالة تجديد التوكن
# =========================================================
def get_access_token():
    url = "https://oauth2.googleapis.com/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            print(f"❌ Token Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error (Token): {e}")
        return None

# =========================================================
# 🎯 مجالات التفكير
# =========================================================
NICHES = [
    "شرح مواقع الذكاء الاصطناعي (أدوات التصميم، الكتابة)",
    "حلول مشاكل الهواتف (أندرويد وآيفون)",
    "شرح تطبيقات الهاتف الاحترافية والمفيدة",
    "أسرار وحيل تقنية في الويندوز",
    "طرق الربح من الإنترنت للمبتدئين",
    "أمن المعلومات وحماية الحسابات",
    "مراجعة إضافات ومواقع خدمية نادرة"
]

# تحميل الذاكرة
try:
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        published_history = json.load(f)
except:
    published_history = []

# =========================================================
# 🧠 الاتصال بـ Gemini (تم التبديل إلى gemini-pro المستقر)
# =========================================================
def call_gemini(prompt):
    # التغيير هنا: استخدام gemini-pro لأنه الأكثر استقراراً
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
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
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # طباعة الخطأ بوضوح للمساعدة في الحل
            print(f"⚠️ Gemini API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Connection Error (Gemini): {e}")
        return None

# =========================================================
# 💡 ابتكار العنوان
# =========================================================
def invent_new_topic():
    niche = random.choice(NICHES)
    recent = published_history[-10:] if len(published_history) > 10 else published_history
    
    prompt = f"""
    بصفتك خبير تقني، اقترح عنوان مقال واحد فقط في مجال: {niche}.
    الشروط:
    1. عنوان جذاب وحصري باللغة العربية.
    2. لا يشبه هذه العناوين: {recent}
    3. اكتب العنوان فقط بدون مقدمات.
    """
    
    topic = call_gemini(prompt)
    if topic:
        return topic.strip().replace('"', '').replace('*', '')
    return None

# =========================================================
# ✍️ كتابة المحتوى
# =========================================================
def write_article(title):
    prompt = f"""
    اكتب مقالاً تقنياً احترافياً بعنوان: "{title}".
    التنسيق HTML:
    - <h2>مقدمة</h2>
    - <h2>الشرح التفصيلي</h2>
    - <ul>المميزات/الخطوات</ul>
    - <h2>طريقة الاستخدام</h2> (<ol>)
    - <div style="background:#f1f1f1; padding:15px;">نصيحة إضافية</div>
    - <h2>الخاتمة</h2>
    الشروط: طويل (600 كلمة)، عربي فصحى، منسق HTML.
    """
    return call_gemini(prompt)

# =========================================================
# 🚀 النشر
# =========================================================
def post_to_blogger(title, content, access_token):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts"
    
    # استخدام صور Picsum لأنها أكثر استقراراً من Unsplash Source حالياً
    random_id = random.randint(1, 1000)
    img_url = f"https://picsum.photos/seed/{random_id}/800/400"
    
    final_html = f"""
    <div style="text-align:center; margin-bottom:20px;">
        <img src="{img_url}" alt="{title}" style="width:100%; max-width:700px; border-radius:10px;">
    </div>
    {content}
    <br><hr>
    <p style="text-align:center; color:#888;">تم التحرير بواسطة بوت الشروحات الذكي.</p>
    """
    
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {
        "kind": "blogger#post", 
        "blog": {"id": BLOG_ID}, 
        "title": title, 
        "content": final_html, 
        "labels": ["شروحات تقنية", "Technology"]
    }
    
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        return True
    else:
        print(f"❌ Blogger Post Error: {res.text}")
        return False

# =========================================================
# 🏁 التشغيل
# =========================================================
if __name__ == "__main__":
    print("🤖 Tech Solutions Bot Started...")
    
    # 1. جلب التوكن
    token = get_access_token()
    
    if token:
        new_topic = ""
        # نحاول 3 مرات لضمان الحصول على عنوان
        for i in range(3):
            print(f"🔄 Attempt {i+1} to invent topic...")
            suggested = invent_new_topic()
            if suggested and suggested not in published_history:
                new_topic = suggested
                break
            else:
                print("⚠️ Duplicate or empty, retrying...")
                time.sleep(2) 
        
        if new_topic:
            print(f"💡 Topic Found: {new_topic}")
            content = write_article(new_topic)
            
            if content:
                print("📝 Content Generated. Publishing...")
                if post_to_blogger(new_topic, content, token):
                    print("✅ PUBLISHED SUCCESSFULLY!")
                    
                    published_history.append(new_topic)
                    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                        json.dump(published_history, f, ensure_ascii=False, indent=2)
                else:
                    print("❌ Failed to Publish (Blogger Error).")
            else:
                print("❌ Failed to generate article body.")
        else:
            print("❌ No Unique Topic Found (Gemini Error).")
    else:
        print("❌ Critical: Token Failed.")
