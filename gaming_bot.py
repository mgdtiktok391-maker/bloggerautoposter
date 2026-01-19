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
from google_play_scraper import search # المكتبة المطلوبة

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

HISTORY_FILE = "history_gaming.json"
PRODUCTS_FILE = "products.json"

# رابط الموديل الصحيح (v1beta) لتجنب خطأ 404
MODEL_NAME = "gemini-1.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

# قائمة المشاكل لدمجها مع الألعاب
PROBLEMS = [
    "حل مشكلة اللاغ والتقطيع (Fix Lag)",
    "تفعيل 90/120 فريم (Unlock FPS)",
    "حل مشكلة سخونة الهاتف (Overheating)",
    "تسريع اللعبة للأجهزة الضعيفة (Game Booster)",
    "حل مشكلة الخروج المفاجئ (Crash Fix)",
    "تقليل البينغ (Fix High Ping)"
]

# رابط الإعلان للأزرار الجانبية
AD_LINK = "https://otieu.com/4/10485502"

# =================== 1. الدوال المساعدة ===================
def load_products():
    """تحميل المنتجات لاختيار واحد منها كحل"""
    if not os.path.exists(PRODUCTS_FILE): return []
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_product_card(product):
    """تصميم بطاقة المنتج لإدراجها وسط المقال"""
    if not product: return ""
    
    html = f"""
    <div style="background: #fff; border: 2px dashed #ff4757; border-radius: 12px; padding: 20px; margin: 30px 0; text-align: center;">
        <h3 style="color: #2f3542; margin-bottom: 10px;">🔥 الحل الأقوى: {product['name']}</h3>
        <p style="color: #57606f; font-size: 14px; margin-bottom: 15px;">{product['description']}</p>
        <img src="{product['image']}" style="width: 150px; height: 150px; object-fit: contain; margin-bottom: 15px;">
        <br>
        <a href="{product['link']}" target="_blank" style="display: inline-block; background: #ff4757; color: white; padding: 10px 25px; text-decoration: none; border-radius: 50px; font-weight: bold;">
            🛒 احصل عليه الآن (خصم خاص)
        </a>
    </div>
    """
    return html

# =================== 2. مستشعر غوغل بلاي ===================
def get_game_from_google_play():
    print("📡 Contacting Google Play Store...")
    try:
        # كلمات بحث تجلب ألعاباً قوية
        queries = ["Action Games", "Battle Royale", "Racing", "FPS Shooting", "RPG"]
        chosen_query = random.choice(queries)
        
        # البحث عن ألعاب في السعودية (للمحتوى العربي)
        results = search(chosen_query, lang='ar', country='sa', n_hits=30)
        
        if results:
            return results # إرجاع قائمة الألعاب
        return []
    except Exception as e:
        print(f"⚠️ Google Play Error: {e}")
        return []

# =================== 3. الذكاء الاصطناعي (Gemini) ===================
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def generate_content(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# =================== 4. المحرك الرئيسي ===================
def run_gaming_bot():
    print("🎮 Gaming Bot (Play + Product Logic) Starting...")
    
    # 1. جلب لعبة جديدة
    games_list = get_game_from_google_play()
    if not games_list:
        print("❌ No games found.")
        return

    # تحميل السجل لمنع التكرار
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    # اختيار لعبة لم تنشر من قبل
    selected_game = None
    for game in games_list:
        if game['title'] not in history:
            selected_game = game
            break
    
    if not selected_game:
        print("⚠️ All games in this batch are duplicates. Picking random...")
        selected_game = random.choice(games_list)

    # 2. تجهيز البيانات
    game_title = selected_game['title']
    game_icon = selected_game['icon']
    problem = random.choice(PROBLEMS)
    
    # 3. اختيار منتج من المتجر
    products = load_products()
    selected_product = random.choice(products) if products else None
    product_html = get_product_card(selected_product)

    print(f"📝 Writing about: {game_title} + {problem}")

    # 4. كتابة المقال
    prompt = f"""
    اكتب مقالاً تقنياً احترافياً (SEO) بعنوان جذاب يجمع بين لعبة "{game_title}" ومشكلة "{problem}".
    استخدم تنسيق HTML (عناوين h2, h3 وفقرات).
    
    الهيكل المطلوب:
    1. مقدمة قوية عن شهرة اللعبة ولماذا يواجه اللاعبون مشكلة {problem}.
    2. فقرة تشويقية تذكر أن الحل يكمن في الأدوات المناسبة (تمهيد للمنتج).
    3. [PRODUCT_PLACEHOLDER] (اترك هذا النص كما هو سأستبدله لاحقاً).
    4. خطوات تقنية (إعدادات، نصائح) لتحسين اللعبة وحل المشكلة.
    5. خاتمة تشجع على زيارة المتجر.
    
    استخدم الايموجي 🎮🔥. لا تضع مقدمات مثل "إليك المقال".
    """
    
    content = generate_content(prompt)
    if not content: return

    # 5. تجميع المقال (استبدال الرمز ببطاقة المنتج)
    content = content.replace("[PRODUCT_PLACEHOLDER]", product_html)
    content = content.replace("```html", "").replace("```", "") # تنظيف

    # إضافة صورة اللعبة والأزرار السفلية
    final_html = f"""
    <div style="text-align:center; margin-bottom: 20px;">
        <img src="{game_icon}" alt="{game_title}" style="width: 100px; border-radius: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
        <h2 style="color:#e17055; margin-top:10px;">{game_title}</h2>
    </div>
    
    {content}
    
    <div style="display: flex; gap: 10px; margin-top: 30px;">
        <a href="{AD_LINK}" target="_blank" style="flex:1; background:#27ae60; color:white; padding:12px; text-align:center; border-radius:50px; text-decoration:none; font-weight:bold;">🎁 هدية اللاعبين</a>
        <a href="{AD_LINK}" target="_blank" style="flex:1; background:#2980b9; color:white; padding:12px; text-align:center; border-radius:50px; text-decoration:none; font-weight:bold;">💎 شحن جواهر</a>
    </div>
    """

    # 6. النشر
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    
    try:
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        title = f"حل مشكلة {problem} في لعبة {game_title} 🔥"
        body = {
            "kind": "blogger#post",
            "title": title,
            "content": final_html,
            "labels": ["Games", "Solutions", "Android"]
        }
        service.posts().insert(blogId=blog["id"], body=body).execute()
        print(f"🚀 Published: {title}")
        
        # حفظ في السجل
        history.append(game_title)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-100:], f, ensure_ascii=False)
            
    except Exception as e:
        print(f"❌ Blogger Error: {e}")

if __name__ == "__main__":
    run_gaming_bot()
