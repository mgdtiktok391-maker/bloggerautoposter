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
    # التصميم المطور لمنع تداخل الإعلانات وظهور الأسماء كاملة
    html_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
        
        .store-body { 
            font-family: 'Cairo', sans-serif; 
            direction: rtl; 
            background: #ffffff; 
            padding: 5px; 
        }
        
        .products-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            max-width: 1200px;
            margin: 0 auto;
            padding: 10px;
        }

        .product-card {
            background: #fff;
            border: 1px solid #f0f0f0;
            border-radius: 12px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            height: 100%; /* لتوحيد ارتفاع البطاقات في السطر */
            box-sizing: border-box;
        }

        .product-img {
            width: 100%;
            height: 180px;
            object-fit: contain;
            border-radius: 8px;
            margin-bottom: 12px;
            background: #fdfdfd;
        }

        .product-title {
            font-size: 15px;
            font-weight: 700;
            color: #2c3e50;
            margin: 0 0 10px 0;
            line-height: 1.4;
            min-height: 42px; /* ضمان مساحة لسطرين على الأقل */
        }

        .product-desc {
            font-size: 12px;
            color: #636e72;
            line-height: 1.5;
            margin-bottom: 15px;
            flex-grow: 1; /* يدفع ما تحته للأسفل */
        }

        .actions-wrapper {
            margin-top: auto; /* يجبر الأزرار على البقاء في القاع */
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .buy-btn {
            background: #ff4757;
            color: #ffffff !important;
            text-decoration: none;
            padding: 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 14px;
            text-align: center;
            transition: 0.2s;
        }

        .ads-row {
            display: flex;
            gap: 5px;
        }

        .ad-link {
            flex: 1;
            font-size: 11px;
            padding: 7px;
            border-radius: 4px;
            color: #fff !important;
            text-decoration: none;
            text-align: center;
            font-weight: 600;
        }
        .ad-green { background: #27ae60; }
        .ad-blue { background: #2980b9; }

        /* تعديلات الموبايل لضمان الوضوح */
        @media (max-width: 900px) {
            .products-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 550px) {
            .products-grid { grid-template-columns: 1fr; }
            .product-img { height: 250px; } /* تكبير الصورة في الموبايل */
        }
    </style>
    
    <div class="store-body">
        <div style="text-align:center; padding: 25px 10px;">
            <h1 style="color:#2d3436; font-size:22px; font-weight:900;">🛒 متجر التحميل الذكي</h1>
            <p style="color:#b2bec3; font-size:13px;">منتجات مبتكرة مختارة لكم بعناية</p>
        </div>
        
        <div class="products-grid">
    """
    
    for p in products:
        card = f"""
        <div class="product-card">
            <img src="{p['image']}" class="product-img" alt="{p['name']}">
            <h3 class="product-title">{p['name']}</h3>
            <p class="product-desc">{p['description']}</p>
            
            <div class="actions-wrapper">
                <a href="{p['link']}" target="_blank" class="buy-btn">🛒 اشترِ الآن</a>
                
                <div class="ads-row">
                    <a href="{AD_LINK_GENERAL}" target="_blank" class="ad-link ad-green">🎁 هدية المتجر</a>
                    <a href="{AD_LINK_GENERAL}" target="_blank" class="ad-link ad-blue">💎 عروض اليوم</a>
                </div>
            </div>
        </div>
        """
        html_content += card

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    html_content += f"""
        </div>
        <div style="text-align:center; margin-top:50px; padding:20px; color:#dfe6e9; font-size:10px; border-top: 1px solid #f1f2f6;">
            Loading Store © 2026 | تحديث يومي: {timestamp}
        </div>
    </div>
    """
    return html_content

def update_store_page():
    print("🛒 Updating Store Page (Layout Fix)...")
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
            print("🚀 Layout Fixed! Check your store page.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_store_page()
