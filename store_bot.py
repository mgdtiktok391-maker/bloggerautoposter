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
    # تصميم المتجر النظيف بدون تداخل الإعلانات
    html_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        
        .store-body { 
            font-family: 'Cairo', sans-serif; 
            direction: rtl; 
            background: #f8f9fa; 
            padding: 10px; 
        }
        
        .products-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .product-card {
            background: #fff;
            border-radius: 12px;
            padding: 15px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid #eee;
            height: 100%;
            box-sizing: border-box;
        }

        .product-img {
            width: 100%;
            height: 200px;
            object-fit: contain;
            border-radius: 8px;
            margin-bottom: 15px;
            background: #fcfcfc;
        }

        .product-title {
            font-size: 16px;
            font-weight: 700;
            color: #2c3e50;
            margin: 0 0 10px 0;
            line-height: 1.5;
            min-height: 48px; /* مساحة كافية للعنوان الطويل */
        }

        .product-desc {
            font-size: 13px;
            color: #636e72;
            line-height: 1.6;
            margin-bottom: 20px;
            flex-grow: 1;
        }

        .actions-section {
            margin-top: auto;
        }

        .buy-now-btn {
            display: block;
            background: #ff4757;
            color: #fff !important;
            text-decoration: none;
            padding: 12px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 15px;
            text-align: center;
            margin-bottom: 10px;
            transition: 0.2s;
        }

        .small-ads-row {
            display: flex;
            gap: 5px;
        }

        .mini-ad-btn {
            flex: 1;
            font-size: 11px;
            padding: 8px;
            border-radius: 5px;
            color: #fff !important;
            text-decoration: none;
            text-align: center;
            font-weight: 600;
        }
        .bg-green { background: #27ae60; }
        .bg-blue { background: #2980b9; }

        .footer-banner {
            max-width: 1100px;
            margin: 40px auto;
            text-align: center;
            border-top: 2px dashed #ddd;
            padding-top: 30px;
        }

        @media (max-width: 992px) {
            .products-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 600px) {
            .products-grid { grid-template-columns: 1fr; }
            .product-img { height: 260px; }
        }
    </style>
    
    <div class="store-body">
        <div style="text-align:center; padding: 30px 0;">
            <h1 style="color:#2d3436; font-size:26px; font-weight:900;">🛒 Loading Store</h1>
            <p style="color:#95a5a6; font-size:14px;">عالم من المنتجات المبتكرة بضغطة زر</p>
        </div>
        
        <div class="products-grid">
    """
    
    for p in products:
        card = f"""
        <div class="product-card">
            <img src="{p['image']}" class="product-img" alt="{p['name']}">
            <h3 class="product-title">{p['name']}</h3>
            <p class="product-desc">{p['description']}</p>
            
            <div class="actions-section">
                <a href="{p['link']}" target="_blank" class="buy-now-btn">🛒 اشتر الآن</a>
                
                <div class="small-ads-row">
                    <a href="{AD_LINK_GENERAL}" target="_blank" class="mini-ad-btn bg-green">🎁 هدية المتجر</a>
                    <a href="{AD_LINK_GENERAL}" target="_blank" class="mini-ad-btn bg-blue">💎 عروض اليوم</a>
                </div>
            </div>
        </div>
        """
        html_content += card

    html_content += f"""
        </div> <div class="footer-banner">
            <p style="color:#7f8c8d; margin-bottom:15px; font-size:13px;">إعلان مميز</p>
            <a href="{AD_LINK_GENERAL}" target="_blank">
                <img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiqU8B8..." style="max-width:100%; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            </a>
            <p style="margin-top:20px; font-size:11px; color:#bdc3c7;">Loading Store © 2026</p>
        </div>
    </div>
    """
    return html_content

def update_store_page():
    print("🛒 Final Layout Polish Starting...")
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
            print("🚀 Fixed! The store is now clean and professional.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_store_page()
