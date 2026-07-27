import os
import time
import json
import logging
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# ============== LOGGING SETUP ==============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============== ENVIRONMENT VARIABLES ==============
USER_ID = os.environ.get("BDG_ID", "")
PASSWORD = os.environ.get("BDJ_PASSWORD", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
LOGIN_URL = "https://bdg2027.com/#/login"
DASHBOARD_URL = "https://bdg2027.com/#/dashboard"

# ============== FILE PATHS ==============
SESSION_FILE = "session.json"
DATA_FILE = "data.json"
COOKIES_FILE = "cookies.json"

# ============== COOKIES MANAGEMENT ==============
def save_cookies(cookies):
    """Save cookies to file"""
    try:
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info("💾 Cookies saved!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save cookies: {e}")
        return False

def load_cookies():
    """Load cookies from file"""
    try:
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
                logger.info("🔄 Cookies loaded!")
                return cookies
    except Exception as e:
        logger.error(f"❌ Failed to load cookies: {e}")
    return None

# ============== SESSION MANAGEMENT ==============
def save_session(cookies, storage):
    """Save full session"""
    try:
        session_data = {
            "cookies": cookies,
            "local_storage": storage,
            "timestamp": datetime.now().isoformat()
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=2)
        logger.info("💾 Session saved!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save session: {e}")
        return False

def load_session():
    """Load full session"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                logger.info("🔄 Session loaded!")
                return data
    except Exception as e:
        logger.error(f"❌ Failed to load session: {e}")
    return None

# ============== TELEGRAM NOTIFICATION ==============
def send_telegram(message):
    """Send message to Telegram"""
    if BOT_TOKEN and CHAT_ID:
        try:
            import requests
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("📨 Telegram message sent")
                return True
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    return False

# ============== CLOUDFLARE HANDLING ==============
def handle_cloudflare(page):
    """Handle Cloudflare challenge"""
    try:
        page_title = page.title().lower()
        if "cloudflare" in page_title or "attention required" in page_title:
            logger.warning("⚠️ Cloudflare detected!")
            
            # Wait and reload
            for attempt in range(5):
                logger.info(f"🔄 Cloudflare attempt {attempt + 1}/5")
                time.sleep(10)
                
                # Scroll like human
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(2)
                
                # Reload
                page.reload(wait_until="domcontentloaded")
                time.sleep(5)
                
                # Check if gone
                new_title = page.title().lower()
                if "cloudflare" not in new_title and "attention required" not in new_title:
                    logger.info("✅ Cloudflare bypassed!")
                    return True
            
            logger.error("❌ Cloudflare still blocking after 5 attempts")
            return False
        return True
    except Exception as e:
        logger.error(f"❌ Cloudflare handling error: {e}")
        return False

# ============== LOGIN WITH COOKIES ==============
def login_with_cookies(page):
    """Try to login using saved cookies"""
    cookies = load_cookies()
    if not cookies:
        return False
    
    try:
        page.context.add_cookies(cookies)
        page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        
        if "login" not in page.url.lower():
            logger.info("✅ Login successful using cookies!")
            return True
        else:
            logger.warning("⚠️ Cookies expired, need fresh login")
            return False
    except Exception as e:
        logger.error(f"❌ Cookie login failed: {e}")
        return False

# ============== MANUAL LOGIN ==============
def manual_login(page):
    """Perform manual login with credentials"""
    if not USER_ID or not PASSWORD:
        logger.error("❌ No credentials found!")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Login attempt {attempt + 1}/{max_retries}")
            
            # Navigate with random delay
            random_delay = random.randint(3000, 7000)
            logger.info(f"⏳ Waiting {random_delay/1000} seconds...")
            time.sleep(random_delay / 1000)
            
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            # Handle Cloudflare
            if not handle_cloudflare(page):
                continue
            
            # Wait for page to load
            time.sleep(3)
            logger.info(f"📄 Page title: {page.title()}")
            logger.info(f"📄 Current URL: {page.url}")
            
            # ===== FIND ID FIELD =====
            id_filled = False
            id_selectors = [
                'input[type="text"]',
                'input[type="tel"]',
                'input[name="username"]',
                'input[name="user"]',
                'input[name="id"]',
                'input[name="phone"]',
                'input[id="username"]',
                'input[id="user"]',
                'input[id="id"]',
                'input[placeholder*="ID"]',
                'input[placeholder*="User"]',
                'input[placeholder*="Phone"]',
                'input[placeholder*="Email"]'
            ]
            
            for selector in id_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).click()
                        page.locator(selector).fill(USER_ID)
                        logger.info(f"✅ ID filled using: {selector}")
                        id_filled = True
                        break
                except:
                    continue
            
            # Try to find any visible input
            if not id_filled:
                try:
                    inputs = page.locator('input:visible').all()
                    for inp in inputs:
                        try:
                            inp_type = inp.get_attribute('type')
                            if inp_type and inp_type != 'password':
                                inp.click()
                                inp.fill(USER_ID)
                                logger.info(f"✅ ID filled using visible input")
                                id_filled = True
                                break
                        except:
                            continue
                except:
                    pass
            
            if not id_filled:
                logger.error("❌ Could not find ID field")
                page.screenshot(path="login_error_id.png")
                continue
            
            # ===== FIND PASSWORD FIELD =====
            pass_filled = False
            pass_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[name="pass"]',
                'input[id="password"]',
                'input[id="pass"]',
                'input[placeholder*="Password"]'
            ]
            
            for selector in pass_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).click()
                        page.locator(selector).fill(PASSWORD)
                        logger.info(f"✅ Password filled using: {selector}")
                        pass_filled = True
                        break
                except:
                    continue
            
            if not pass_filled:
                logger.error("❌ Could not find Password field")
                page.screenshot(path="login_error_pass.png")
                continue
            
            # ===== SUBMIT =====
            submitted = False
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign In")',
                'button:has-text("Submit")',
                'button:has-text("log in")',
                'button:has-text("Signin")'
            ]
            
            for selector in submit_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).click()
                        logger.info(f"✅ Submitted using: {selector}")
                        submitted = True
                        break
                except:
                    continue
            
            if not submitted:
                try:
                    page.keyboard.press("Enter")
                    logger.info("✅ Submitted using Enter key")
                    submitted = True
                except:
                    logger.error("❌ Could not submit form")
                    continue
            
            # ===== WAIT FOR LOGIN =====
            time.sleep(10)
            
            # Check if login successful
            if "login" not in page.url.lower():
                logger.info("✅ Login successful!")
                
                # Save cookies
                cookies = page.context.cookies()
                save_cookies(cookies)
                
                # Save session
                try:
                    storage = page.evaluate("() => JSON.stringify(localStorage)")
                    save_session(cookies, storage)
                except:
                    pass
                
                send_telegram("✅ <b>Galaxy Brother Bot</b>\nLogin successful! 🚀")
                return True
            else:
                logger.warning(f"⚠️ Login failed, URL: {page.url}")
                page.screenshot(path=f"login_failed_attempt_{attempt}.png")
                continue
                
        except Exception as e:
            logger.error(f"❌ Login attempt {attempt + 1} error: {e}")
            try:
                page.screenshot(path=f"login_error_{attempt}.png")
            except:
                pass
            time.sleep(5)
            continue
    
    logger.error("❌ All login attempts failed")
    send_telegram("❌ <b>Galaxy Brother Bot</b>\nLogin failed! Please check credentials.")
    return False

# ============== CHECK LOGIN STATUS ==============
def is_logged_in(page):
    """Check if user is logged in"""
    try:
        url = page.url.lower()
        title = page.title().lower()
        return "login" not in url and "cloudflare" not in title
    except:
        return False

# ============== SCRAPE DATA ==============
def scrape_data(page):
    """Scrape data from website"""
    logger.info("📊 Scraping data...")
    
    try:
        time.sleep(3)
        
        # Find table
        table_selectors = ['table', '.table', '#data-table', 'div[class*="table"]']
        table_found = False
        
        for selector in table_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.wait_for_selector(selector, timeout=5000)
                    table_found = True
                    logger.info(f"✅ Table found using: {selector}")
                    break
            except:
                continue
        
        if not table_found:
            logger.warning("⚠️ No table found")
            return []
        
        # Extract data
        rows = page.locator('table tbody tr').all()
        data = []
        
        for row in rows:
            try:
                cols = row.locator('td').all_text_contents()
                if cols and len(cols) >= 2:
                    data.append({
                        "period": cols[0].strip() if len(cols) > 0 else "",
                        "number": cols[1].strip() if len(cols) > 1 else "",
                        "big_small": cols[2].strip() if len(cols) > 2 else "",
                        "color": cols[3].strip() if len(cols) > 3 else "",
                        "timestamp": datetime.now().isoformat()
                    })
            except:
                continue
        
        # Save data
        if data:
            existing = []
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, "r") as f:
                        existing = json.load(f)
                except:
                    existing = []
            
            existing_periods = {d.get("period") for d in existing}
            new_data = [d for d in data if d.get("period") not in existing_periods]
            
            if new_data:
                existing.extend(new_data)
                with open(DATA_FILE, "w") as f:
                    json.dump(existing, f, indent=2)
                logger.info(f"✅ {len(new_data)} new records saved!")
                return new_data
            else:
                logger.info("ℹ️ No new data")
                return []
        else:
            logger.warning("⚠️ No data extracted")
            return []
            
    except Exception as e:
        logger.error(f"❌ Scraping error: {e}")
        return []

# ============== MAIN FUNCTION ==============
def main():
    """Main bot function"""
    logger.info("🚀 Galaxy Brother Bot Starting...")
    
    # Check credentials
    if not USER_ID or not PASSWORD:
        logger.warning("⚠️ No credentials found. Using cookies only...")
    
    with sync_playwright() as p:
        # Browser launch with anti-detection
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Chromium";v="120", "Not_A_Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        page = context.new_page()
        
        # Apply stealth
        try:
            stealth_sync(page)
            logger.info("✅ Stealth mode enabled")
        except Exception as e:
            logger.warning(f"⚠️ Stealth mode failed: {e}")
        
        # Try login with cookies first
        if not login_with_cookies(page):
            logger.info("🆕 No valid cookies, performing manual login...")
            if not manual_login(page):
                logger.error("❌ Login failed, exiting...")
                browser.close()
                return
        
        logger.info("✅ Bot ready, starting main loop...")
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                logger.info(f"🔄 Loop {loop_count} starting...")
                
                # Navigate to dashboard
                page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                
                # Check if still logged in
                if not is_logged_in(page):
                    logger.warning("⚠️ Session expired, re-logging...")
                    if not manual_login(page):
                        logger.error("❌ Re-login failed, waiting 10 minutes...")
                        time.sleep(600)
                        continue
                
                # Scrape data
                new_data = scrape_data(page)
                
                # Send notification
                if new_data:
                    msg = f"📊 <b>New Data</b>\n📈 {len(new_data)} records\n🕐 {datetime.now().strftime('%H:%M:%S')}"
                    send_telegram(msg)
                
                # Wait
                wait_time = 300
                logger.info(f"⏳ Waiting {wait_time // 60} minutes...")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"⚠️ Loop error: {e}")
                time.sleep(600)

if __name__ == "__main__":
    main()
