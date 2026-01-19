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
AD_LINK_GENERAL = "https://otieu.com/4/10485502"

# =================== الدوال ===================

def get_service():
    creds = Credentials(None, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    return build("blogger", "v3", credentials=creds)

def load_products():
    if not os.path.exists(PRODUCTS_FILE): return []
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_full_catalog_html(products):
    # التصميم الجديد لعرض 3 منتجات في السطر
    html_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        .store-body { font-family: 'Cairo', sans-serif; direction: rtl; background: #f4f7f6; padding: 10px; }
        
        .products-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr); /* 3 أعمدة متساوية */
            gap: 15px;
            max-width: 1100px;
            margin: 0 auto;
        }

        .product-card {
            background: #fff;
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: 0.3s;
            border: 1px solid #eee;
        }
        .product-card:hover { transform: translateY(-5px); }

        .product-img {
            width: 100%;
            height: 160px;
            object-fit: contain;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .product-title {
            font-size: 14px;
            font-weight: 700;
            color: #2c3e50;
            margin: 5px 0;
            height: 40px;
            overflow: hidden;
            line-height: 1.4;
        }

        .product-desc {
            font-size: 11px;
            color: #7f8c8d;
            height: 50px;
            overflow: hidden;
            margin-bottom: 10px;
        }

        .buy-btn {
            background: linear-gradient(45deg, #ff4757, #ff6b81);
            color: #fff !important;
            text-decoration: none;
            padding: 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 13px;
            text-align: center;
            margin-bottom: 8px;
        }

        .ads-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px;
        }

        .ad-btn {
            font-size: 10px;
            padding: 6px;
            border-radius: 4px;
            color: #fff !important;
            text-decoration: none;
            text-align: center;
            font-weight: bold;
        }
        .ad-r { background: #27ae60; }
        .ad-l { background: #2980b9; }

        /* التوافق مع الجوال */
        @media (max-width: 850px) {
            .products-container { grid-template-columns: repeat(2, 1fr); } /* منتجين في الجوال الكبير */
        }
        @media (max-width: 500px) {
            .products-container { grid-template-columns: 1fr; } /* منتج واحد في الجوال الصغير */
        }
    </style>
    
    <div class="store-body">
        <div style="text-align:center; padding: 20px 0;">
            <h1 style="color:#2c3e50; font-size:24px;">💎 متجر العروض الحصرية 💎</h1>
            <p style="color:#7f8c8d; font-size:14px;">أحدث الاختيارات الذكية من AliExpress</p>
        </div>
        
        <div class="products-container">
    """
    
    for p in products:
        card = f"""
        <div class="product-card">
            <img src="{p['image']}" class="product-img" alt="{p['name']}">
            <h3 class="product-title">{p['name']}</h3>
            <p class="product-desc">{p['description']}</p>
            
            <a href="{p['link']}" target="_blank" class="buy-btn">🛒 اشترِ الآن</a>
            
            <div class="ads-grid">
                <a href="{AD_LINK_GENERAL}" target="_blank" class="ad-btn ad-r">🎁 هدية</a>
                <a href="{AD_LINK_GENERAL}" target="_blank" class="ad-btn ad-l">💎 عرض</a>
            </div>
        </div>
        """
        html_content += card

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html_content += f"""
        </div>
        <div style="text-align:center; margin-top:40px; padding:20px; color:#bdc3c7; font-size:11px;">
            Updated: {timestamp} | Loading Store © 2026
        </div>
    </div>
    """
    return html_content

def update_store_page():
    print("🛒 Starting Store Grid Update...")
    service = get_service()
    products = load_products()
    
    try:
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        blog_id = blog["id"]
        pages = service.pages().list(blogId=blog_id).execute()
        
        target_page = next((p for p in pages['items'] if "store" in p['url'].lower() or "متجر" in p['title']), None)
        
        if target_page:
            body = {"title": target_page['title'], "content": generate_full_catalog_html(products)}
            service.pages().update(blogId=blog_id, pageId=target_page['id'], body=body).execute()
            print("🚀 Store Grid Updated Successfully (3 Items per row)!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_store_page()
