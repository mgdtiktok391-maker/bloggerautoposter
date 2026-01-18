import google.generativeai as genai
import requests
import json
import random
import os
import time

# =========================================================
# 🔐 الإعدادات
# =========================================================
BLOG_ID = os.environ["BLOG_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

HISTORY_FILE = 'history_tech_solutions.json'

# إعداد مكتبة جوجل الرسمية
genai.configure(api_key=GEMINI_API_KEY)

# =========================================================
# 🔄 دالة تجديد التوكن (Blogger)
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
# 🧠 الاتصال بـ Gemini (بالمكتبة الرسمية - الحل المضمون)
# =========================================================
def call_gemini(prompt):
    # قائمة الموديلات التي سنجربها بالترتيب
    models_to_try = ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro']
    
    for model_name in models_to_try:
        try:
            # إعداد الموديل
            model = genai.GenerativeModel(model_name)
            
            # إرسال الطلب
            response = model.generate_content(prompt)
            
            # استخراج النص
            if response.text:
                return response.text
                
        except Exception as e:
            # إذا فشل موديل، نجرب التالي بصمت
            continue
            
    print("❌ Failed to generate content with all models.")
    return None

# =========================================================
# 💡 ابتكار العنوان
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

try:
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        published_history = json.load(f)
except:
    published_history = []

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
    
    return call_gemini(prompt)

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
    
    # استخدام صور Picsum لأنها مستقرة
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
    print("🤖 Tech Solutions Bot Started (Official SDK Mode)...")
    
    token = get_access_token()
    
    if token:
        new_topic = ""
        # محاولات الابتكار
        for i in range(3):
            print(f"🔄 Attempt {i+1} to invent topic...")
            # تنظيف العنوان من أي علامات
            raw_topic = invent_new_topic()
            if raw_topic:
                clean_topic = raw_topic.strip().replace('"', '').replace('*', '')
                if clean_topic not in published_history:
                    new_topic = clean_topic
                    break
            else:
                print("⚠️ Empty response from AI, retrying...")
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
                    print("❌ Failed to Publish.")
            else:
                print("❌ Failed to generate body.")
        else:
            print("❌ No Unique Topic Found (Check Quota or Region).")
    else:
        print("❌ Critical: Token Failed.")
