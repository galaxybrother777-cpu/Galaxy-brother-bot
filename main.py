import os
import time
import json
import logging
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
USER_ID = os.environ.get("BDG_ID", "your_id")
PASSWORD = os.environ.get("BDJ_PASSWORD", "your_password")
LOGIN_URL = "https://bdg2027.com/#/login"  # Fixed URL

# ============== FILE PATHS ==============
SESSION_FILE = "session.json"
DATA_FILE = "data.json"
COOKIES_FILE = "cookies.json"

# ============== SESSION MANAGEMENT ==============
def save_session(cookies, storage, local_storage):
    """Save session data"""
    try:
        session_data = {
            "cookies": cookies,
            "local_storage": local_storage,
            "timestamp": datetime.now().isoformat()
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=2)
        logger.info("💾 Session saved successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save session: {e}")
        return False

def load_session():
    """Load saved session"""
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                logger.info("🔄 Session loaded successfully!")
                return data
    except Exception as e:
        logger.error(f"❌ Failed to load session: {e}")
    return None

def save_cookies(cookies):
    """Save cookies separately"""
    try:
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, indent=2)
        return True
    except:
        return False

def load_cookies():
    """Load saved cookies"""
    try:
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, "r") as f:
                return json.load(f)
    except:
        return None
    return None

# ============== LOGIN FUNCTION ==============
def login(page):
    """Login to BDG website with retry logic"""
    
    logger.info(f"🔑 Logging in to {LOGIN_URL}...")
    
    # Try saved cookies first
    saved_cookies = load_cookies()
    if saved_cookies:
        try:
            page.context.add_cookies(saved_cookies)
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Check if logged in
            if "login" not in page.url.lower() and "cloudflare" not in page.title().lower():
                logger.info("✅ Login successful using saved cookies!")
                return True
        except Exception as e:
            logger.warning(f"⚠️ Cookie login failed: {e}")
    
    # If cookies don't work, try fresh login
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Login attempt {attempt + 1}/{max_retries}")
            
            # Step 1: Navigate with proper wait
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
            
            # Step 2: Wait for page to stabilize
            page.wait_for_timeout(5000)
            
            # Step 3: Handle Cloudflare
            if "cloudflare" in page.title().lower():
                logger.warning("⚠️ Cloudflare detected, waiting...")
                page.wait_for_timeout(15000)
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(10000)
            
            # Step 4: Click login button if needed (SPA navigation)
            try:
                login_btn = page.locator('a:has-text("Login"), button:has-text("Login")')
                if login_btn.count() > 0:
                    login_btn.click()
                    page.wait_for_timeout(3000)
            except:
                pass
            
            # Step 5: Fill credentials with multiple selector attempts
            id_filled = False
            id_selectors = [
                'input[type="text"]',
                'input[name="username"]',
                'input[name="user"]',
                'input[id="username"]',
                'input[id="user"]',
                'input[placeholder*="ID"]',
                'input[placeholder*="User"]',
                'input[placeholder*="Phone"]',
                'input[placeholder*="Email"]'
            ]
            
            for selector in id_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.fill(selector, USER_ID)
                        logger.info(f"✅ ID filled using: {selector}")
                        id_filled = True
                        break
                except:
                    continue
            
            if not id_filled:
                logger.error("❌ Could not find ID field")
                page.screenshot(path="login_error_id.png")
                continue
            
            # Password fill
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
                        page.fill(selector, PASSWORD)
                        logger.info(f"✅ Password filled using: {selector}")
                        pass_filled = True
                        break
                except:
                    continue
            
            if not pass_filled:
                logger.error("❌ Could not find Password field")
                page.screenshot(path="login_error_pass.png")
                continue
            
            # Submit
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
                        page.click(selector)
                        logger.info(f"✅ Submitted using: {selector}")
                        submitted = True
                        break
                except:
                    continue
            
            if not submitted:
                # Try pressing Enter
                try:
                    page.keyboard.press("Enter")
                    logger.info("✅ Submitted using Enter key")
                    submitted = True
                except:
                    logger.error("❌ Could not submit form")
                    continue
            
            # Step 6: Wait for login to complete
            page.wait_for_timeout(8000)
            
            # Step 7: Check if login successful
            if "login" not in page.url.lower() and "cloudflare" not in page.title().lower():
                logger.info("✅ Login successful!")
                
                # Save session
                try:
                    cookies = page.context.cookies()
                    storage = page.evaluate("() => JSON.stringify(localStorage)")
                    save_session(cookies, storage, {})
                    save_cookies(cookies)
                except:
                    pass
                
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
    return False

# ============== CHECK LOGIN STATUS ==============
def is_logged_in(page):
    """Check if user is logged in"""
    try:
        url = page.url.lower()
        title = page.title().lower()
        return "login" not in url and "signin" not in url and "cloudflare" not in title
    except:
        return False

# ============== SCRAPE DATA ==============
def scrape_data(page):
    """Scrape data from the website"""
    logger.info("📊 Starting data scraping...")
    
    try:
        # Wait for data to load
        page.wait_for_timeout(3000)
        
        # Try to find data table
        table_selectors = [
            'table',
            '.table',
            '#data-table',
            'div[class*="table"]',
            'div[class*="data"]',
            '.MuiTable-root'
        ]
        
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
            logger.warning("⚠️ No table found on page")
            page.screenshot(path="no_table.png")
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
            
            # Avoid duplicates
            existing_periods = {d.get("period") for d in existing}
            new_data = [d for d in data if d.get("period") not in existing_periods]
            
            if new_data:
                existing.extend(new_data)
                with open(DATA_FILE, "w") as f:
                    json.dump(existing, f, indent=2)
                logger.info(f"✅ {len(new_data)} new records saved!")
                return new_data
            else:
                logger.info("ℹ️ No new data to save")
                return []
        else:
            logger.warning("⚠️ No data extracted")
            return []
            
    except Exception as e:
        logger.error(f"❌ Scraping error: {e}")
        try:
            page.screenshot(path="scrape_error.png")
        except:
            pass
        return []

# ============== SEND TELEGRAM MESSAGE (Optional) ==============
def send_telegram_message(message):
    """Send message to Telegram (if configured)"""
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    
    if bot_token and chat_id:
        try:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("📨 Telegram message sent")
            else:
                logger.warning(f"⚠️ Telegram send failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")

# ============== MAIN FUNCTION ==============
def main():
    """Main bot function"""
    logger.info("🚀 Galaxy Brother Bot Starting...")
    
    # Check credentials
    if USER_ID == "your_id" or PASSWORD == "your_password":
        logger.error("❌ Please set BDG_ID and BDJ_PASSWORD environment variables!")
        return
    
    with sync_playwright() as p:
        # Launch browser with anti-detection args
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
                "--disable-features=BlockInsecurePrivateNetworkRequests",
                "--disable-features=OutOfBlinkCors",
                "--window-size=1920,1080"
            ]
        )
        
        # Create context with realistic settings
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata",
            geolocation={"latitude": 22.5726, "longitude": 88.3639},
            permissions=["geolocation"],
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Chromium";v="120", "Not_A_Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        page = context.new_page()
        
        # Apply stealth
        try:
            stealth_sync(page)
            logger.info("✅ Stealth mode enabled")
        except Exception as e:
            logger.warning(f"⚠️ Stealth mode not available: {e}")
        
        # Initial navigation
        logger.info("🌐 Navigating to website...")
        
        # Try login
        if not login(page):
            logger.error("❌ Login failed, exiting...")
            send_telegram_message("❌ <b>Galaxy Brother Bot</b>\nLogin failed! Please check credentials.")
            browser.close()
            return
        
        # Main loop
        logger.info("✅ Bot ready, starting main loop...")
        send_telegram_message("✅ <b>Galaxy Brother Bot</b>\nBot started successfully! 🚀")
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                logger.info(f"🔄 Loop {loop_count} starting...")
                
                # Navigate to dashboard
                page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)
                
                # Check if still logged in
                if not is_logged_in(page):
                    logger.warning("⚠️ Session expired, re-logging...")
                    if not login(page):
                        logger.error("❌ Re-login failed, waiting 10 minutes...")
                        time.sleep(600)
                        continue
                
                # Scrape data
                new_data = scrape_data(page)
                
                # If new data found, send notification
                if new_data:
                    msg = f"📊 <b>New Data Received</b>\n"
                    msg += f"📈 {len(new_data)} new records\n"
                    msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    send_telegram_message(msg)
                
                # Wait before next loop
                wait_time = 300  # 5 minutes
                logger.info(f"⏳ Waiting {wait_time // 60} minutes...")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"⚠️ Loop error: {e}")
                time.sleep(600)  # Wait 10 minutes on error

if __name__ == "__main__":
    main()
