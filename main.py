# ============================================
# 📁 FILE: main.py
# 📝 DESCRIPTION: BDG WinGo Scrape Bot (Polling Mode)
# 🔗 GAME: WinGo 1Min (Playwright)
# 🌐 URL: https://bdg4.cc/#/
# 🚀 RAILWAY: No Webhook Required
# ============================================

import os
import json
import logging
import asyncio
import random
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from playwright.async_api import async_playwright

# ============================================
# LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIG - BDG4.CC URLs
# ============================================

TOKEN = os.environ.get("BOT_TOKEN")
BDG_USERNAME = os.environ.get("BDG_USERNAME")
BDG_PASSWORD = os.environ.get("BDG_PASSWORD")
PORT = int(os.environ.get("PORT", 8080))

# ✅ BDG4.CC URLs
BDG_BASE_URL = "https://bdg4.cc/#/"
BDG_LOGIN_URL = "https://bdg4.cc/#/login"
BDG_WINGO_URL = "https://bdg4.cc/#/saasLottery/WinGo?gameCode=WinGo_1M&lottery=WinGo"
BDG_LOBBY_URL = "https://bdg4.cc/#/home"

if not TOKEN:
    logger.error("❌ BOT_TOKEN not set!")
    sys.exit(1)

if not BDG_USERNAME or not BDG_PASSWORD:
    logger.warning("⚠️ BDG_USERNAME or BDG_PASSWORD not set! Login will fail.")

# ============================================
# DATA STORE
# ============================================

DATA_FILE = "bdg_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ============================================
# COLOR CODES
# ============================================

COLORS = {"red": "🔴", "green": "🟢", "violet": "🟣", "big": "📈", "small": "📉"}

def get_color_emoji(color):
    return COLORS.get(color.lower(), "⚪")

# ============================================
# PERSISTENT BROWSER - BDG4.CC
# ============================================

class PersistentBrowser:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.is_logged_in = False
        self.playwright = None

    async def init(self):
        if self.browser is not None:
            logger.info("✅ Browser already initialized")
            return
        
        logger.info("🌐 Starting browser...")
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process'
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()
        
        await self._login()
        self.is_logged_in = True
        logger.info("✅ Browser initialized and logged in")

    async def _login(self):
        if not BDG_USERNAME or not BDG_PASSWORD:
            logger.error("❌ Login credentials missing!")
            return
        
        logger.info(f"🌐 Going to login page: {BDG_LOGIN_URL}")
        await self.page.goto(BDG_LOGIN_URL, timeout=60000)
        await self.page.wait_for_timeout(5000)

        try:
            # Take screenshot for debugging
            await self.page.screenshot(path="debug_login.png")
            logger.info("📸 Login page screenshot saved")
            
            # Try different selectors for username
            username_selectors = ["#username", "input[type='text']", "input[name='username']", "input[placeholder*='username' i]"]
            username_input = None
            for sel in username_selectors:
                try:
                    username_input = await self.page.query_selector(sel)
                    if username_input:
                        logger.info(f"✅ Username field found with selector: {sel}")
                        break
                except:
                    continue
            
            if username_input:
                await username_input.fill(BDG_USERNAME)
                logger.info("✅ Username filled")
            else:
                logger.warning("⚠️ Username field not found!")
            
            # Try different selectors for password
            password_selectors = ["#password", "input[type='password']", "input[name='password']"]
            password_input = None
            for sel in password_selectors:
                try:
                    password_input = await self.page.query_selector(sel)
                    if password_input:
                        logger.info(f"✅ Password field found with selector: {sel}")
                        break
                except:
                    continue
            
            if password_input:
                await password_input.fill(BDG_PASSWORD)
                logger.info("✅ Password filled")
            else:
                logger.warning("⚠️ Password field not found!")
            
            # Try different selectors for login button
            login_selectors = ["#login-button", "button[type='submit']", "button:has-text('Login')", "button:has-text('Sign In')"]
            login_button = None
            for sel in login_selectors:
                try:
                    login_button = await self.page.query_selector(sel)
                    if login_button:
                        logger.info(f"✅ Login button found with selector: {sel}")
                        break
                except:
                    continue
            
            if login_button:
                await login_button.click()
                logger.info("✅ Login button clicked")
            else:
                logger.warning("⚠️ Login button not found!")
            
            await self.page.wait_for_timeout(5000)
            
            # Check if login was successful
            current_url = self.page.url
            logger.info(f"📍 Current URL after login: {current_url}")
            
            if "login" not in current_url.lower():
                logger.info("✅ Login successful!")
            else:
                logger.warning("⚠️ Login might have failed, still on login page")
                await self.page.screenshot(path="debug_login_failed.png")
            
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            await self.page.screenshot(path="debug_login_error.png")
            raise

    async def navigate_to_wingo(self):
        """Navigate to WinGo 1Min and extract data"""
        if not self.is_logged_in:
            await self.init()
        
        logger.info(f"🎯 Navigating to WinGo: {BDG_WINGO_URL}")
        
        try:
            await self.page.goto(BDG_WINGO_URL, timeout=60000)
            await self.page.wait_for_timeout(5000)
            
            # Scroll down
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(3000)
            
            # Take screenshot for debugging
            await self.page.screenshot(path="debug_wingo.png")
            logger.info("📸 WinGo page screenshot saved")
            
            # Try to find data using different methods
            data = await self._extract_data_from_page()
            
            if data:
                logger.info(f"✅ Extracted {len(data)} records")
                return data
            else:
                logger.warning("⚠️ No data extracted, trying alternative method...")
                # Try alternative extraction
                data = await self._extract_data_alternative()
                return data
            
        except Exception as e:
            logger.error(f"❌ Navigation error: {e}")
            await self.page.screenshot(path="debug_error.png")
            return None

    async def _extract_data_from_page(self):
        """Extract data using JavaScript evaluation"""
        try:
            data = await self.page.evaluate('''
                () => {
                    const result = [];
                    
                    // Find all rows in the table
                    const rows = document.querySelectorAll('tr, div[class*="row"], div[class*="history-item"]');
                    
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td, div[class*="col"], span');
                        if (cells.length >= 4) {
                            const period = cells[0]?.textContent?.trim() || '';
                            const number = parseInt(cells[1]?.textContent?.trim()) || 0;
                            const colorText = cells[2]?.textContent?.trim()?.toLowerCase() || '';
                            const sizeText = cells[3]?.textContent?.trim()?.toLowerCase() || '';
                            
                            let color = 'unknown';
                            if (colorText.includes('green')) color = 'green';
                            else if (colorText.includes('red')) color = 'red';
                            else if (colorText.includes('violet')) color = 'violet';
                            
                            let size = 'unknown';
                            if (sizeText.includes('big')) size = 'big';
                            else if (sizeText.includes('small')) size = 'small';
                            
                            if (period && number > 0) {
                                result.push({
                                    period: period,
                                    number: number,
                                    color: color,
                                    size: size,
                                    timestamp: new Date().toISOString()
                                });
                            }
                        }
                    }
                    
                    return result;
                }
            ''')
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Extract error: {e}")
            return None

    async def _extract_data_alternative(self):
        """Alternative data extraction method"""
        try:
            # Get all text content from the page
            text_content = await self.page.evaluate('''
                () => {
                    return document.body.innerText;
                }
            ''')
            
            logger.info(f"📄 Page text length: {len(text_content)}")
            
            # Parse text for numbers and periods
            import re
            lines = text_content.split('\n')
            data = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for period (long number) and single digit
                period_match = re.search(r'\b\d{14,}\b', line)
                number_match = re.search(r'\b[0-9]\b', line)
                
                if period_match and number_match:
                    period = period_match.group()
                    number = int(number_match.group())
                    
                    # Check for color indicators
                    color = 'unknown'
                    if 'green' in line.lower():
                        color = 'green'
                    elif 'red' in line.lower():
                        color = 'red'
                    elif 'violet' in line.lower():
                        color = 'violet'
                    
                    # Check for size indicators
                    size = 'unknown'
                    if 'big' in line.lower():
                        size = 'big'
                    elif 'small' in line.lower():
                        size = 'small'
                    
                    data.append({
                        'period': period,
                        'number': number,
                        'color': color,
                        'size': size,
                        'timestamp': str(datetime.now())
                    })
            
            return data[:10]  # Limit to 10 records
            
        except Exception as e:
            logger.error(f"❌ Alternative extract error: {e}")
            return None

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            self.is_logged_in = False
            logger.info("🔒 Browser closed")

# ============================================
# GLOBAL BROWSER INSTANCE
# ============================================

browser_session = PersistentBrowser()

# ============================================
# TELEGRAM COMMANDS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    keyboard = [
        [InlineKeyboardButton("📥 Scrape & Fetch", callback_data="fetch")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🔮 Prediction", callback_data="predict")],
        [InlineKeyboardButton("📋 View History", callback_data="view")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    data = load_data()
    await update.message.reply_text(
        f"🤖 **BDG WinGo Scrape Bot**\n\n"
        f"🌐 URL: bdg4.cc\n"
        f"📦 Total Records: {len(data)}\n"
        f"🔄 Auto-Scrape: Every 30 seconds\n\n"
        f"**Commands:**\n"
        f"/fetch - Manual scrape\n"
        f"/view - Last 10 records\n"
        f"/pattern - Pattern analysis\n"
        f"/predict - Prediction\n"
        f"/stats - Statistics\n"
        f"/reset - Delete all data\n"
        f"/bdg - Open BDG Game",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def fetch_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual fetch command"""
    msg = await update.message.reply_text("📡 Scraping BDG Game data from bdg4.cc...")
    
    try:
        global browser_session
        if not browser_session.is_logged_in:
            await browser_session.init()
        
        data = await browser_session.navigate_to_wingo()
        
        if not data:
            await msg.edit_text("❌ Failed to scrape data! Check logs.")
            return
        
        existing = load_data()
        existing_periods = {item.get('period') for item in existing}
        new_count = 0
        
        for item in data:
            if item['period'] not in existing_periods:
                existing.append(item)
                new_count += 1
        
        save_data(existing)
        
        await msg.edit_text(
            f"✅ **Scraped Successfully!**\n"
            f"🌐 Source: bdg4.cc\n"
            f"📊 New Records: {new_count}\n"
            f"📦 Total Records: {len(existing)}"
        )
        
    except Exception as e:
        logger.error(f"❌ Fetch error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")

async def view_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View last 10 records"""
    data = load_data()
    if not data:
        await update.message.reply_text("📭 No data.")
        return
    
    last_10 = data[-10:] if len(data) >= 10 else data
    msg = "📊 **Last 10 Records:**\n\n"
    
    for idx, item in enumerate(last_10, 1):
        emoji = get_color_emoji(item.get('color', 'unknown'))
        size_emoji = "📈" if item.get('size') == 'big' else "📉" if item.get('size') == 'small' else ""
        msg += f"{idx}. {emoji} {item.get('color', 'N/A').upper()} {item.get('number', 'N/A')} {size_emoji} ({item.get('size', 'N/A')})\n"
    
    msg += f"\n📦 **Total:** {len(data)} records"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistics"""
    data = load_data()
    if not data:
        await update.message.reply_text("📭 No data.")
        return
    
    total = len(data)
    red = sum(1 for i in data if i.get('color') == 'red')
    green = sum(1 for i in data if i.get('color') == 'green')
    violet = sum(1 for i in data if i.get('color') == 'violet')
    
    await update.message.reply_text(
        f"📊 **Full Statistics**\n\n"
        f"📦 Total: {total}\n"
        f"{get_color_emoji('red')} Red: {red} ({red/total*100:.1f}%)\n"
        f"{get_color_emoji('green')} Green: {green} ({green/total*100:.1f}%)\n"
        f"{get_color_emoji('violet')} Violet: {violet} ({violet/total*100:.1f}%)",
        parse_mode='Markdown'
    )

async def pattern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pattern analysis"""
    data = load_data()
    if len(data) < 5:
        await update.message.reply_text("⚠️ Need 5+ records.")
        return
    
    last_50 = data[-50:] if len(data) >= 50 else data
    color_count = {}
    number_count = {}
    
    for item in last_50:
        color = item.get('color', 'unknown')
        num = item.get('number', 0)
        color_count[color] = color_count.get(color, 0) + 1
        number_count[num] = number_count.get(num, 0) + 1
    
    if last_50:
        streak_color = last_50[-1].get('color', 'unknown')
        streak_count = 1
        for i in range(len(last_50)-2, -1, -1):
            if last_50[i].get('color') == streak_color:
                streak_count += 1
            else:
                break
    else:
        streak_color = 'N/A'
        streak_count = 0
    
    hot_color = max(color_count, key=color_count.get) if color_count else 'N/A'
    hot_number = max(number_count, key=number_count.get) if number_count else 0
    
    await update.message.reply_text(
        f"🎯 **Pattern Analysis**\n\n"
        f"📊 Last 50 Distribution:\n"
        f"{get_color_emoji('red')} Red: {color_count.get('red', 0)}\n"
        f"{get_color_emoji('green')} Green: {color_count.get('green', 0)}\n"
        f"{get_color_emoji('violet')} Violet: {color_count.get('violet', 0)}\n\n"
        f"📈 Streak: {streak_count}x {streak_color.upper()}\n"
        f"🔥 Hot Color: {hot_color.upper()} ({color_count.get(hot_color, 0)}x)\n"
        f"🎯 Hot Number: {hot_number} ({number_count.get(hot_number, 0)}x)",
        parse_mode='Markdown'
    )

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prediction based on history"""
    data = load_data()
    if len(data) < 5:
        await update.message.reply_text("⚠️ Need 5+ records.")
        return
    
    last_100 = data[-100:] if len(data) >= 100 else data
    total = len(last_100)
    
    red = sum(1 for i in last_100 if i.get('color') == 'red')
    green = sum(1 for i in last_100 if i.get('color') == 'green')
    violet = sum(1 for i in last_100 if i.get('color') == 'violet')
    
    probs = {
        'RED': (red/total)*100 if total > 0 else 0,
        'GREEN': (green/total)*100 if total > 0 else 0,
        'VIOLET': (violet/total)*100 if total > 0 else 0
    }
    
    best = max(probs, key=probs.get)
    
    await update.message.reply_text(
        f"🔮 **Prediction**\n\n"
        f"{get_color_emoji(best.lower())} **Best Bet:** {best} ({probs[best]:.1f}%)\n\n"
        f"📊 Probability:\n"
        f"{get_color_emoji('red')} Red: {probs['RED']:.1f}%\n"
        f"{get_color_emoji('green')} Green: {probs['GREEN']:.1f}%\n"
        f"{get_color_emoji('violet')} Violet: {probs['VIOLET']:.1f}%\n\n"
        f"📦 Based on {total} rounds\n"
        f"⚠️ Not financial advice.",
        parse_mode='Markdown'
    )

async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all data"""
    data = load_data()
    if not data:
        await update.message.reply_text("📭 No data to delete.")
        return
    
    save_data([])
    await update.message.reply_text(f"🗑️ {len(data)} records deleted!")

async def bdg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open BDG Game"""
    keyboard = [[InlineKeyboardButton("🎯 Open BDG Game", web_app={"url": BDG_WINGO_URL})]]
    await update.message.reply_text("🎯 **BDG Game (bdg4.cc)**\n\nClick below:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "fetch":
        await query.edit_message_text("📡 Scraping BDG data from bdg4.cc...")
        global browser_session
        
        try:
            if not browser_session.is_logged_in:
                await browser_session.init()
            
            data = await browser_session.navigate_to_wingo()
            
            if data:
                existing = load_data()
                existing_periods = {item.get('period') for item in existing}
                count = 0
                for item in data:
                    if item['period'] not in existing_periods:
                        existing.append(item)
                        count += 1
                save_data(existing)
                await query.edit_message_text(f"✅ {count} new records saved!\n📦 Total: {len(existing)}")
            else:
                await query.edit_message_text("❌ No data scraped.")
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    elif query.data == "stats":
        data = load_data()
        if not data:
            await query.edit_message_text("📭 No data.")
            return
        total = len(data)
        red = sum(1 for i in data if i.get('color') == 'red')
        green = sum(1 for i in data if i.get('color') == 'green')
        violet = sum(1 for i in data if i.get('color') == 'violet')
        await query.edit_message_text(
            f"📊 **Stats**\n📦 Total: {total}\n"
            f"🔴 Red: {red} ({red/total*100:.1f}%)\n"
            f"🟢 Green: {green} ({green/total*100:.1f}%)\n"
            f"🟣 Violet: {violet} ({violet/total*100:.1f}%)"
        )
    
    elif query.data == "predict":
        data = load_data()
        if len(data) < 5:
            await query.edit_message_text("⚠️ Need 5+ records.")
            return
        last_100 = data[-100:] if len(data) >= 100 else data
        total = len(last_100)
        red = sum(1 for i in last_100 if i.get('color') == 'red')
        green = sum(1 for i in last_100 if i.get('color') == 'green')
        violet = sum(1 for i in last_100 if i.get('color') == 'violet')
        probs = {'RED': (red/total)*100, 'GREEN': (green/total)*100, 'VIOLET': (violet/total)*100}
        best = max(probs, key=probs.get)
        await query.edit_message_text(
            f"🔮 **Prediction**\n🎯 Best: {best} ({probs[best]:.1f}%)\n"
            f"🔴 Red: {probs['RED']:.1f}%\n"
            f"🟢 Green: {probs['GREEN']:.1f}%\n"
            f"🟣 Violet: {probs['VIOLET']:.1f}%"
        )
    
    elif query.data == "view":
        data = load_data()
        if not data:
            await query.edit_message_text("📭 No data.")
            return
        last_10 = data[-10:] if len(data) >= 10 else data
        msg = "📊 **Last 10 Records:**\n\n"
        for idx, item in enumerate(last_10, 1):
            emoji = get_color_emoji(item.get('color', 'unknown'))
            msg += f"{idx}. {emoji} {item.get('color', 'N/A').upper()} {item.get('number', 'N/A')}\n"
        msg += f"\n📦 Total: {len(data)} records"
        await query.edit_message_text(msg)

# ============================================
# AUTO FETCH (Background - Every 30 seconds)
# ============================================

async def auto_fetch():
    """Auto fetch data every 30 seconds"""
    global browser_session
    
    while True:
        try:
            if not browser_session.is_logged_in:
                await browser_session.init()
            
            data = await browser_session.navigate_to_wingo()
            
            if data:
                existing = load_data()
                existing_periods = {item.get('period') for item in existing}
                count = 0
                
                for item in data:
                    if item['period'] not in existing_periods:
                        existing.append(item)
                        count += 1
                
                if count > 0:
                    save_data(existing)
                    logger.info(f"✅ Auto-scraped {count} new records | Total: {len(existing)}")
            
        except Exception as e:
            logger.error(f"❌ Auto-fetch error: {e}")
            await browser_session.close()
            browser_session.is_logged_in = False
        
        await asyncio.sleep(30)

# ============================================
# MAIN - No Webhook, Only Polling
# ============================================

async def main():
    """Main function - Polling mode (no webhook)"""
    logger.info("🚀 Starting BDG WinGo Scrape Bot...")
    logger.info("📡 Mode: Polling (No Webhook)")
    logger.info(f"🌐 Using URL: {BDG_BASE_URL}")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("fetch", fetch_data))
    application.add_handler(CommandHandler("view", view_data))
    application.add_handler(CommandHandler("pattern", pattern))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("reset", reset_data))
    application.add_handler(CommandHandler("bdg", bdg_cmd))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    await application.initialize()
    
    asyncio.create_task(auto_fetch())
    
    try:
        logger.info("✅ Bot started in polling mode!")
        await application.start()
        await application.updater.start_polling()
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("✅ Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
