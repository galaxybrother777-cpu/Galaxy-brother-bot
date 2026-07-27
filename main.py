 import os
import time
import json
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# 🔑 Environment Variables से ID और Password लें
YOUR_ID = os.environ.get("BDG_ID", "your_username")
YOUR_PASSWORD = os.environ.get("BDG_PASSWORD", "your_password")

# 📁 Session और Data Store करने के लिए Files
SESSION_FILE = "session.json"
DATA_FILE = "data.json"

def save_session(cookies, storage):
    """Session (Cookies + LocalStorage) को सेव करें"""
    session_data = {
        "cookies": cookies,
        "storage": storage
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f, indent=2)
    print("💾 Session सेव हो गया!")

def load_session():
    """पुराना Session लोड करें (अगर मौजूद है)"""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return None

def login(page):
    """Login करने का Function"""
    print("🔑 Login कर रहा हूँ...")
    
    # पेज पर जाएं
    page.goto("https://bdg1.cc/#/")
    page.wait_for_timeout(3000)
    
    # ID डालें
    try:
        page.fill('input[type="text"]', YOUR_ID)
        print("✅ ID डाल दिया")
    except Exception as e:
        print(f"❌ ID नहीं डाल पाया: {e}")
        return False
    
    # Password डालें
    try:
        page.fill('input[type="password"]', YOUR_PASSWORD)
        print("✅ Password डाल दिया")
    except Exception as e:
        print(f"❌ Password नहीं डाल पाया: {e}")
        return False
    
    # Login बटन क्लिक करें
    try:
        page.click('button[type="submit"]')
        print("✅ Login बटन क्लिक किया")
    except Exception as e:
        print(f"❌ Login बटन नहीं मिला: {e}")
        return False
    
    # Login सफल हुआ या नहीं
    page.wait_for_timeout(5000)
    
    if "dashboard" in page.url.lower() or "home" in page.url.lower():
        print("✅ Login सफल! 🎉")
        # Session सेव करें
        cookies = page.context.cookies()
        storage = page.evaluate("() => JSON.stringify(localStorage)")
        save_session(cookies, storage)
        return True
    else:
        print(f"❌ Login फेल! URL: {page.url}")
        return False

def is_logged_in(page):
    """Check करें कि Login है या नहीं"""
    try:
        if "login" in page.url.lower() or "signin" in page.url.lower():
            return False
        return True
    except:
        return False

def load_previous_session(page):
    """पुराना Session Load करें (Cookies + Storage)"""
    session = load_session()
    if session:
        try:
            page.context.add_cookies(session["cookies"])
            # LocalStorage Load करें
            page.evaluate(f"() => {{ {session['storage']} }}")
            print("🔄 पुराना Session लोड हो गया!")
            return True
        except Exception as e:
            print(f"⚠️ Session Load करने में समस्या: {e}")
            return False
    return False

def scrape_data(page):
    """Data निकालें और Store करें"""
    print("📊 डेटा निकाल रहा हूँ...")
    
    try:
        rows = page.locator('table tbody tr').all()
        data = []
        for row in rows:
            cols = row.locator('td').all_text_contents()
            if cols:
                data.append({
                    "period": cols[0] if len(cols) > 0 else "",
                    "number": cols[1] if len(cols) > 1 else "",
                    "big_small": cols[2] if len(cols) > 2 else "",
                    "color": cols[3] if len(cols) > 3 else "",
                })
        
        # पुराना Data Load करें और नया Add करें
        existing_data = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                existing_data = json.load(f)
        
        existing_periods = {d.get("period") for d in existing_data}
        new_data = [d for d in data if d.get("period") not in existing_periods]
        
        if new_data:
            existing_data.extend(new_data)
            with open(DATA_FILE, "w") as f:
                json.dump(existing_data, f, indent=2)
            print(f"✅ {len(new_data)} नए रिकॉर्ड सेव हो गए!")
        else:
            print("ℹ️ कोई नया डेटा नहीं मिला")
        
        return data
        
    except Exception as e:
        print(f"❌ डेटा निकालते समय समस्या: {e}")
        return []

def main():
    """Main Function - 24/7 चलेगा"""
    with sync_playwright() as p:
        # 🚀 Browser Launch (Railway के लिए headless=True)
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 🛡️ Stealth Mode Enable करें
        stealth_sync(page)
        
        # 🎯 Step 1: पुराना Session Load करने की कोशिश करें
        session_loaded = load_previous_session(page)
        
        if session_loaded:
            page.goto("https://bdg1.cc/#/")
            page.wait_for_timeout(3000)
            
            if not is_logged_in(page):
                print("⚠️ Session Expired हो गया है, फिर से Login कर रहा हूँ...")
                if login(page):
                    print("✅ Auto-Relogin सफल!")
                else:
                    print("❌ Auto-Relogin फेल!")
                    return
            else:
                print("✅ पुराना Session Valid है!")
        else:
            print("🆕 पहली बार Login कर रहा हूँ...")
            if not login(page):
                print("❌ Login फेल!")
                return
        
        # 🎯 Step 2: पहली बार Data Scrape करें
        scrape_data(page)
        
        # 🎯 Step 3: 24/7 Loop - हर 5 मिनट में Data Scrape करें
        while True:
            try:
                print("\n⏳ 5 मिनट बाद फिर से Data Scrape होगा...")
                time.sleep(300)  # 5 मिनट
                
                page.reload()
                page.wait_for_timeout(3000)
                
                if not is_logged_in(page):
                    print("⚠️ Logout हो गया है, Auto-Relogin कर रहा हूँ...")
                    if login(page):
                        print("✅ Auto-Relogin सफल!")
                    else:
                        print("❌ Auto-Relogin फेल! Loop में वापस जा रहा हूँ...")
                        continue
                
                scrape_data(page)
                
            except Exception as e:
                print(f"⚠️ Loop में समस्या: {e}")
                time.sleep(600)

if __name__ == "__main__":
    main()
