# -*- coding: utf-8 -*-
import os
import json
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# =================== إعدادات النظام ===================
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

PRODUCTS_FILE = "products.json"
AD_LINK_RIGHT = "https://otieu.com/4/10485502"
AD_LINK_LEFT = "https://otieu.com/4/10485502"

# =================== الدوال ===================

def get_service():
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    return build("blogger", "v3", credentials=creds)

def load_products():
    if not os.path.exists(PRODUCTS_FILE): return []
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_full_catalog_html(products):
    # CSS وتصميم الصفحة
    html_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        .store-container { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; color: #333; }
        .product-card { background: #fff; border: 1px solid #eee; border-radius: 15px; padding: 20px; margin-bottom: 40px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); text-align: center; }
        .product-title { color: #2d3436; margin-bottom: 15px; font-size: 22px; font-weight: 900; }
        .product-img { width: 100%; max-width: 300px; height: auto; border-radius: 12px; margin: 10px 0; object-fit: contain; }
        .product-desc { color: #636e72; font-size: 16px; line-height: 1.7; margin: 15px 0; }
        .buy-btn { display: block; width: 100%; background: linear-gradient(45deg, #ff9f43, #ee5253); color: white !important; padding: 15px 0; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 18px; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(238, 82, 83, 0.3); transition: 0.3s; }
        .buy-btn:hover { transform: translateY(-3px); }
        .ads-container { display: flex; gap: 10px; justify-content: center; margin-top: 10px; }
        .ad-btn { flex: 1; padding: 10px; border-radius: 10px; text-decoration: none; font-size: 14px; font-weight: bold; color: white !important; text-align: center; }
        .ad-right { background: #00b894; }
        .ad-left { background: #0984e3; }
    </style>
    
    <div class="store-container">
        <div style="text-align:center; margin-bottom: 40px; padding: 20px; background: #f9f9f9; border-radius: 15px;">
            <h1 style="color:#e17055; margin:0;">🔥 Loading Store 🔥</h1>
            <p style="color:#777;">أفضل المنتجات التقنية والغريبة المختارة بعناية</p>
        </div>
    """
    
    for product in products:
        # هنا التعديل الذكي: يحاول قراءة الاسم الجديد، فإذا لم يجده يجرب القديم
        name = product.get('name', product.get('name_ar', 'منتج مميز'))
        desc = product.get('description', 'وصف المنتج...')
        image = product.get('image', product.get('image_url', ''))
        link = product.get('link', product.get('affiliate_link', '#'))
        
        # إذا لم يكن هناك صورة، تجاوز هذا المنتج
        if not image: continue

        card = f"""
        <div class="product-card">
            <h3 class="product-title">{name}</h3>
            <img src="{image}" class="product-img" alt="{name}">
            <p class="product-desc">{desc}</p>
            <a href="{link}" target="_blank" class="buy-btn">🛒 اضغط للشراء (خصم خاص)</a>
            <div class="ads-container">
                <a href="{AD_LINK_RIGHT}" target="_blank" class="ad-btn ad-right">🎁 هدية المتجر</a>
                <a href="{AD_LINK_LEFT}" target="_blank" class="ad-btn ad-left">💎 عروض اليوم</a>
            </div>
        </div>
        """
        html_content += card

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html_content += f"""
        <div style="text-align:center; margin-top:50px; color:#aaa; font-size:12px;">
            Last Updated: {timestamp}
        </div>
    </div>
    """
    return html_content

def update_store_page():
    print("🛒 Store Bot (Safe Mode) Starting...")
    service = get_service()
    
    products = load_products()
    if not products:
        print("❌ No products found in JSON file!")
        return
    print(f"📦 Loaded {len(products)} products.")

    print("🔍 Finding Store Page...")
    try:
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        blog_id = blog["id"]
        pages = service.pages().list(blogId=blog_id, fetchBodies=False).execute()
        
        store_page_id = None
        store_page_title = None
        
        if "items" in pages:
            for page in pages['items']:
                if "store" in page['url'].lower() or "متجر" in page['title']:
                    store_page_id = page['id']
                    store_page_title = page['title']
                    break
        
        if not store_page_id:
            print("❌ Store page not found!")
            return

        print(f"✅ Found Page: {store_page_title} ({store_page_id})")

        full_html = generate_full_catalog_html(products)
        
        body = {
            "title": store_page_title,
            "content": full_html
        }
        
        service.pages().update(blogId=blog_id, pageId=store_page_id, body=body).execute()
        print("🚀 Store Page Updated Successfully!")
        
    except Exception as e:
        print(f"❌ Error details: {e}")

if __name__ == "__main__":
    update_store_page()
