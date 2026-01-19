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
    # تصميم المتجر "النظيف جداً" لمنع تداخل الإعلانات
    html_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        
        .store-bg { 
            font-family: 'Cairo', sans-serif; 
            direction: rtl; 
            background: #ffffff; 
            padding: 5px; 
        }
        
        .grid-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .item-card {
            background: #ffffff;
            border: 1px solid #f1f1f1;
            border-radius: 10px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
            height: 100%;
            box-sizing: border-box;
            position: relative;
        }

        .item-img {
            width: 100%;
            height: 160px;
            object-fit: contain;
            margin-bottom: 10px;
        }

        .item-name {
            font-size: 14px;
            font-weight: 700;
            color: #333;
            margin: 5px 0;
            line-height: 1.4;
            min-height: 40px;
        }

        .item-desc {
            font-size: 11px;
            color: #666;
            line-height: 1.5;
            margin-bottom: 15px;
            flex-grow: 1;
        }

        /* منع التداخل عبر عزل منطقة الأزرار */
        .btn-section {
            margin-top: auto;
            border-top: 1px solid #f9f9f9;
            padding-top: 10px;
        }

        .main-buy-btn {
            display: block;
            background: #ff4757;
            color: #ffffff !important;
            text-decoration: none;
            padding: 10px;
            border-radius: 5px;
            font-weight: 700;
            font-size: 13px;
            text-align: center;
            margin-bottom: 8px;
        }

        .secondary-btns {
            display: flex;
            gap: 4px;
        }

        .mini-btn {
            flex: 1;
            font-size: 10px;
            padding: 6px 2px;
            border-radius: 4px;
            color: #fff !important;
            text-decoration: none;
            text-align: center;
            font-weight: 600;
        }
        .green { background: #27ae60; }
        .blue { background: #2980b9; }

        @media (max-width: 900px) {
            .grid-container { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 500px) {
            .grid-container { grid-template-columns: 1fr; }
        }
    </style>
    
    <div class="store-bg">
        <div style="text-align:center; padding-bottom: 20px;">
            <h2 style="color:#333;">🛒 قائمة المنتجات المختارة</h2>
        </div>
        
        <div class="grid-container">
    """
    
    for p in products:
        card = f"""
        <div class="item-card">
            <img src="{p['image']}" class="item-img" alt="{p['name']}">
            <div class="item-name">{p['name']}</div>
            <div class="item-desc">{p['description']}</div>
            
            <div class="btn-section">
                <a href="{p['link']}" target="_blank" class="main-buy-btn">🛒 اشتر الآن</a>
                <div class="secondary-btns">
                    <a href="{AD_LINK_GENERAL}" target="_blank" class="mini-btn green">🎁 هدية المتجر</a>
                    <a href="{AD_LINK_GENERAL}" target="_blank" class="mini-btn blue">💎 عروض اليوم</a>
                </div>
            </div>
        </div>
        """
        html_content += card

    html_content += """
        </div>
        <div style="text-align:center; margin-top:40px; color:#ccc; font-size:10px;">
            Loading Store © 2026
        </div>
    </div>
    """
    return html_content

def update_store_page():
    print("🛒 Fixing Store Overlap...")
    service = get_service()
    products = load_products()
    
    try:
        blog = service.blogs().getByUrl(url=BLOG_URL).execute()
        blog_id = blog["id"]
        pages = service.pages().list(blogId=blog_id).execute()
        
        target = next((p for p in pages['items'] if "store" in p['url'].lower() or "متجر" in p['title']), None)
        
        if target:
            body = {"title": target['title'], "content": generate_full_catalog_html(products)}
            service.pages().update(blogId=blog_id, pageId=target['id'], body=body).execute()
            print("🚀 Fixed! The products are now isolated from ads.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_store_page()
