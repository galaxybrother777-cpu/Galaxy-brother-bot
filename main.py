import os
import time
import json
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# Environment Variables
USER_ID = os.environ.get("BDG_ID", "your_id")
PASSWORD = os.environ.get("BDG_PASSWORD", "your_password")

# New URL
LOGIN_URL = "https://bdg2027.com//#/login"

SESSION_FILE = "session.json"
DATA_FILE = "data.json"

def save_session(cookies, storage):
    with open(SESSION_FILE, "w") as f:
        json.dump({"cookies": cookies, "storage": storage}, f, indent=2)
    print("💾 Session saved!")

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return None

def login(page):
    print(f"🔑 Logging in to {LOGIN_URL}...")
    
    try:
        # Website pe jao
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        print("✅ Page loaded")
        
        # Thoda wait karo
        page.wait_for_timeout(5000)
        
        # Page ka title check karo
        print(f"📄 Page title: {page.title()}")
        print(f"📄 Current URL: {page.url}")
        
        # 🎯 Selectors try karo (multiple options)
        selectors_id = [
            'input[type="text"]',
            'input[name="username"]',
            'input[name="user"]',
            'input[id="username"]',
            'input[id="user"]',
            'input[placeholder*="ID"]',
            'input[placeholder*="User"]',
            'input[placeholder*="user"]'
        ]
        
        selectors_pass = [
            'input[type="password"]',
            'input[name="password"]',
            'input[name="pass"]',
            'input[id="password"]',
            'input[id="pass"]',
            'input[placeholder*="Password"]',
            'input[placeholder*="password"]'
        ]
        
        selectors_submit = [
            'button[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign In")',
            'button:has-text("Submit")',
            'button:has-text("log in")'
        ]
        
        # ID fill karo
        id_filled = False
        for selector in selectors_id:
            try:
                if page.locator(selector).count() > 0:
                    page.fill(selector, USER_ID)
                    print(f"✅ ID filled using: {selector}")
                    id_filled = True
                    break
            except:
                continue
        
        if not id_filled:
            print("❌ Could not find ID field")
            page.screenshot(path="login_error.png")
            print("📸 Screenshot saved as login_error.png")
            return False
        
        # Password fill karo
        pass_filled = False
        for selector in selectors_pass:
            try:
                if page.locator(selector).count() > 0:
                    page.fill(selector, PASSWORD)
                    print(f"✅ Password filled using: {selector}")
                    pass_filled = True
                    break
            except:
                continue
        
        if not pass_filled:
            print("❌ Could not find Password field")
            return False
        
        # Submit button click karo
        submitted = False
        for selector in selectors_submit:
            try:
                if page.locator(selector).count() > 0:
                    page.click(selector)
                    print(f"✅ Submitted using: {selector}")
                    submitted = True
                    break
            except:
                continue
        
        if not submitted:
            print("❌ Could not find Submit button")
            return False
        
        # Wait for navigation
        page.wait_for_timeout(5000)
        
        # Check karo login hua ya nahi
        if "dashboard" in page.url.lower() or "home" in page.url.lower():
            print("✅ Login successful!")
            cookies = page.context.cookies()
            storage = page.evaluate("() => JSON.stringify(localStorage)")
            save_session(cookies, storage)
            return True
        else:
            print(f"❌ Login failed! URL: {page.url}")
            page.screenshot(path="login_failed.png")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        try:
            page.screenshot(path="login_error.png")
            print("📸 Screenshot saved as login_error.png")
        except:
            pass
        return False

def is_logged_in(page):
    try:
        return "login" not in page.url.lower() and "signin" not in page.url.lower()
    except:
        return False

def load_previous_session(page):
    session = load_session()
    if session:
        try:
            page.context.add_cookies(session["cookies"])
            page.evaluate(f"() => {{ {session['storage']} }}")
            print("🔄 Previous session loaded!")
            return True
        except Exception as e:
            print(f"⚠️ Session load error: {e}")
    return False

def scrape_data(page):
    print("📊 Scraping data...")
    try:
        page.wait_for_selector('table', timeout=10000)
        
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

        existing = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                existing = json.load(f)

        existing_periods = {d.get("period") for d in existing}
        new_data = [d for d in data if d.get("period") not in existing_periods]

        if new_data:
            existing.extend(new_data)
            with open(DATA_FILE, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"✅ {len(new_data)} new records saved!")
        else:
            print("ℹ️ No new data")
    except Exception as e:
        print(f"❌ Scraping error: {e}")

def main():
    print("🚀 Bot starting...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            stealth_sync(page)
        except:
            print("⚠️ Stealth mode not available")

        if not load_previous_session(page):
            print("🆕 No session found, logging in...")
            if not login(page):
                print("❌ Login failed, exiting...")
                return

        page.goto(LOGIN_URL)
        page.wait_for_timeout(3000)

        if not is_logged_in(page):
            print("⚠️ Session expired, re-logging...")
            if not login(page):
                print("❌ Re-login failed, exiting...")
                return

        print("✅ Bot ready, starting main loop...")
        while True:
            try:
                scrape_data(page)
                print("⏳ Waiting 5 minutes...")
                time.sleep(300)
                page.reload()
                page.wait_for_timeout(3000)

                if not is_logged_in(page):
                    print("⚠️ Logged out, re-logging...")
                    if not login(page):
                        print("❌ Re-login failed, retrying in 10 minutes...")
                        time.sleep(600)
                        continue
            except Exception as e:
                print(f"⚠️ Loop error: {e}")
                time.sleep(600)

if __name__ == "__main__":
    main()
