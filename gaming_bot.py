# -*- coding: utf-8 -*-
import os, random, markdown as md
import requests
import backoff
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_play_scraper import search as play_search, app as play_app

# =================== إعدادات المستخدم ===================
MONETAG_DIRECT_LINK = "https://otieu.com/4/10485502"
GAME_LABELS = ["Games", "العاب", "Android", "Gaming", "Review"]

# =================== إعدادات النظام ===================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
HISTORY_GAMES_FILE = "history_gaming.txt"
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"

# قائمة الموديلات بالترتيب (إذا فشل الأول يجرب الثاني)
MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-pro"]

SEARCH_QUERIES = [
    "Battle Royale", "FPS Shooting", "Action RPG", "Open World", "Survival", 
    "Racing Car", "Zombie", "Strategy", "Fighting Game", "Adventure", 
    "Simulation", "Sports Football", "Sniper 3D", "Multiplayer", "Among Us", "Minecraft"
]

def load_used_games():
    if not os.path.exists(HISTORY_GAMES_FILE): return set()
    with open(HISTORY_GAMES_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_used_game(package_name):
    with open(HISTORY_GAMES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{package_name}\n")

def get_fresh_game():
    used_games = load_used_games()
    queries = SEARCH_QUERIES[:]
    random.shuffle(queries)
    print(f"🎮 Scanning Google Play for Games...")
    
    for query in queries:
        try:
            results = play_search(query, lang="ar", country="sa", n_hits=30)
            for game_summary in results:
                pkg = game_summary['appId']
                if pkg in used_games: continue
                
                score = game_summary.get('score', 0)
                if score and score < 3.5: continue 

                try: details = play_app(pkg, lang='ar', country='sa')
                except: continue
                
                if not details.get('icon'): continue
                
                print(f"✅ Found Game: {details['title']}")
                return details
        except Exception as e:
            print(f"⚠️ Search Error: {e}")
            continue
    return None

# =================== محرك Gemini المصفح ===================
def _generate_with_retry(prompt):
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]
    
    for model in MODELS_TO_TRY:
        url = f"{GEMINI_API_ROOT}/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            # print(f"⏳ Trying model: {model}...") 
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety_settings}, timeout=30)
            
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"⚠️ Model {model} Failed: {r.status_code} - {r.text[:100]}") # طباعة الخطأ لمعرفته
        except Exception as e:
            print(f"⚠️ Connection Error with {model}: {e}")
            continue
            
    print("❌ All models failed to generate content.")
    return None

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def ask_gemini_game_review(game_details):
    title = game_details['title']
    desc = game_details.get('description', '')[:2000]
    
    prompt = f"""
    تصرف كخبير ألعاب (Gamer) محترف ومرح. اكتب مراجعة للعبة: {title}
    الوصف: {desc}
    
    المطلوب (Markdown):
    1. **عنوان جذاب**: (H1) يجذب اللاعبين.
    2. **لماذا هي ترند؟**: فقرة حماسية.
    3. **الجرافيك والتحكم**: رأيك بصراحة.
    4. **نصائح للفوز**: (H2) حركات سرية أو نصائح للمحترفين.
    5. **المواصفات**: جدول بسيط لمتطلبات التشغيل.
    6. **الخاتمة**: هل تستحق التحميل؟
    
    استخدم الايموجي 🎮🔥🚀. ممنوع الروابط.
    """
    return _generate_with_retry(prompt)

# =================== الأزرار الإعلانية الذكية ===================
def build_game_post_html(game_details, article_html):
    image_url = game_details.get('headerImage') or game_details.get('icon')
    title = game_details['title']
    pkg_id = game_details['appId']
    real_play_store_url = f"https://play.google.com/store/apps/details?id={pkg_id}"
    
    header = f'<div style="text-align:center;margin-bottom:20px;"><img src="{image_url}" alt="{title}" style="max-width:100%;border-radius:15px;box-shadow:0 8px 20px rgba(0,0,0,0.2);"></div>'
    
    buttons_html = f"""
    <style>
        .gaming-btns {{ display: flex; flex-direction: column; gap: 15px; margin: 30px 0; }}
        .g-btn {{
            display: block; padding: 15px; text-align: center; color: white !important;
            text-decoration: none; font-weight: bold; border-radius: 50px;
            font-size: 18px; transition: transform 0.2s; position: relative; overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        .g-btn:hover {{ transform: scale(1.02); }}
        .btn-gold {{ background: linear-gradient(45deg, #f1c40f, #f39c12); }}
        .btn-blue {{ background: linear-gradient(45deg, #3498db, #2980b9); }}
        .btn-green {{ background: linear-gradient(45deg, #2ecc71, #27ae60); }}
    </style>

    <div class="gaming-btns">
        <a href="{MONETAG_DIRECT_LINK}" target="_blank" class="g-btn btn-gold">
            💎 شحن جواهر/شدات (مجاناً)
        </a>
        <a href="{MONETAG_DIRECT_LINK}" target="_blank" class="g-btn btn-blue">
            🚀 تفعيل 90 فريم وإزالة اللاغ
        </a>
        <a href="{real_play_store_url}" 
           onclick="window.open('{MONETAG_DIRECT_LINK}', '_blank');" 
           target="_blank" class="g-btn btn-green">
            📥 تحميل اللعبة (Google Play)
        </a>
        <p style="text-align:center; font-size:12px; color:#777; margin-top:5px;">رابط مباشر وآمن 100% ✅</p>
    </div>
    """
    
    return header + md.markdown(article_html, extensions=['extra']) + buttons_html

def post_to_blogger(title, content):
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    service = build("blogger", "v3", credentials=creds)
    blog_id = service.blogs().getByUrl(url=BLOG_URL).execute()["id"]
    body = {"kind": "blogger#post", "title": title, "content": content, "labels": GAME_LABELS}
    return service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

if __name__ == "__main__":
    print("🎮 Starting Gaming Bot (Robust Version)...")
    game_data = get_fresh_game()
    if game_data:
        print(f"📝 Generating review for: {game_data['title']}...")
        article = ask_gemini_game_review(game_data)
        if article:
            lines = article.strip().split('\n')
            title = lines[0].replace('#', '').replace('*', '').strip()
            if len(title) < 5: title = f"تحميل لعبة {game_data['title']} مهكرة (شرح كامل)"
            
            final_html = build_game_post_html(game_data, article)
            try:
                res = post_to_blogger(title, final_html)
                save_used_game(game_data['appId'])
                print(f"🎉 PUBLISHED! URL: {res.get('url')}")
            except Exception as e: print(f"❌ Publish Error: {e}")
        else: print("❌ Content generation failed (Check logs above for API error).")
    else: print("❌ No game found.")
