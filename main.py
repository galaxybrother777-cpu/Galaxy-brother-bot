import os
import time
import json
from playwright.sync_api import sync_playwright
from camoufox.sync_api import Camoufox

# 🔑 Environment Variables से ID और Password लें
YOUR_ID = os.environ.get("BDG_ID", "your_username")
YOUR_PASSWORD = os.environ.get("BDG_PASSWORD", "your_password")

def login_and_scrape():
    with Camoufox(
        headless=False,          # पहले False रखें (देखने के लिए), बाद में True करें
        humanize=True,           # इंसानों जैसा व्यवहार
        geoip=False              # अगर VPN/प्रॉक्सी नहीं तो False रखें
    ) as browser:
        
        page = browser.new_page()
        
        print("🌐 वेबसाइट खुल रही है...")
        
        # 1️⃣ लॉगिन पेज पर जाएं
        page.goto("https://bdg1.cc/#/")
        page.wait_for_timeout(3000)  # पेज लोड होने का इंतज़ार
        
        print("🔑 ID और Password डाल रहा हूँ...")
        
        # 2️⃣ ID डालें (सही सेलेक्टर खुद ढूंढें)
        try:
            # Inspect करके सही selector डालें
            page.fill('input[type="text"]', YOUR_ID)
            # अगर ना चले तो नीचे वाला uncomment करें:
            # page.fill('#username', YOUR_ID)
            # page.fill('[name="username"]', YOUR_ID)
            # page.fill('[placeholder*="ID"]', YOUR_ID)
            print("✅ ID डाल दिया")
        except Exception as e:
            print(f"❌ ID वाला इनपुट नहीं मिला: {e}")
            return
        
        # 3️⃣ Password डालें
        try:
            page.fill('input[type="password"]', YOUR_PASSWORD)
            # अगर ना चले तो नीचे वाला uncomment करें:
            # page.fill('#password', YOUR_PASSWORD)
            # page.fill('[name="password"]', YOUR_PASSWORD)
            # page.fill('[placeholder*="Password"]', YOUR_PASSWORD)
            print("✅ Password डाल दिया")
        except Exception as e:
            print(f"❌ Password वाला इनपुट नहीं मिला: {e}")
            return
        
        # 4️⃣ लॉगिन बटन क्लिक करें
        try:
            page.click('button[type="submit"]')
            # अगर ना चले तो नीचे वाला uncomment करें:
            # page.click('#loginBtn')
            # page.click('button:has-text("Login")')
            # page.click('button:has-text("Sign In")')
            print("✅ Login बटन क्लिक किया")
        except Exception as e:
            print(f"❌ Login बटन नहीं मिला: {e}")
            return
        
        # 5️⃣ लॉगिन सफल हुआ या नहीं चेक करें
        page.wait_for_timeout(5000)  # 5 सेकंड इंतज़ार
        
        # अगर URL में dashboard या home आ गया तो समझें लॉगिन हो गया
        current_url = page.url.lower()
        if "dashboard" in current_url or "home" in current_url:
            print("✅ लॉगिन सफल! 🎉")
            
            # 📸 स्क्रीनशॉट लें (जांच के लिए)
            page.screenshot(path="login_success.png")
            print("📸 login_success.png सेव किया")
            
            # 6️⃣ अब डेटा निकालें
            print("📊 डेटा निकाल रहा हूँ...")
            
            # 🔍 यहाँ आपको खुद सेलेक्टर डालने होंगे (Inspect करके देखें)
            # Example:
            try:
                # मान लें कि डेटा एक टेबल में है
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
                
                # 7️⃣ डेटा सेव करें
                with open("data.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"✅ {len(data)} रिकॉर्ड data.json में सेव हो गए!")
                
            except Exception as e:
                print(f"❌ डेटा निकालते समय समस्या: {e}")
                # कम से कम पेज का HTML सेव कर लें
                with open("page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("📄 page.html सेव किया (बाद में Inspect करें)")
            
        else:
            print(f"❌ लॉगिन फेल! Current URL: {page.url}")
            # स्क्रीनशॉट लें
            page.screenshot(path="login_failed.png")
            print("📸 login_failed.png में स्क्रीनशॉट सेव किया")
            
            # पेज का HTML भी सेव करें
            with open("login_failed.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("📄 login_failed.html सेव किया")

if __name__ == "__main__":
    login_and_scrape()
