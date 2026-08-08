# ============================================
# 📁 FILE: main.py
# 📝 DESCRIPTION: BDG WinGo Scrape Bot (Polling Mode)
# 🔗 GAME: WinGo 1Min (Playwright) — Period, Number, Big/Small, Color
# 🚀 RAILWAY: No Webhook Required
# ============================================

import os
import json
import logging
import asyncio
import random
import sys
import signal
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
# CONFIG - Environment Variables
# ============================================

TOKEN = os.environ.get("BOT_TOKEN")
BDG_USERNAME = os.environ.get("BDG_USERNAME")
BDG_PASSWORD = os.environ.get("BDG_PASSWORD")
PORT = int(os.environ.get("PORT", 8080))

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
# PERSISTENT BROWSER (No Webhook)
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
        
        logger.info("🌐 Going to login page...")
        await self.page.goto("https://7bdg.com/#/login", timeout=60000)
        await self.page.wait_for_timeout(3000)

        try:
            # Username
            username_input = await self.page.query_selector("#username") or await self.page.query_selector("input[type='text']")
            if username_input:
                await username_input.fill(BDG_USERNAME)
                logger.info("✅ Username filled")
            
            # Password
            password_input = await self.page.query_selector("#password") or await self.page.query_selector("input[type='password']")
            if password_input:
                await password_input.fill(BDG_PASSWORD)
                logger.info("✅ Password filled")
            
            # Login Button
            login_button = await self.page.query_selector("#login-button") or await self.page.query_selector("button[type='submit']")
            if login_button:
                await login_button.click()
                logger.info("✅ Login button clicked")
            
            await self.page.wait_for_timeout(5000)
            logger.info("✅ Login successful!")
            
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            raise

    async def navigate_to_wingo(self):
        """Navigate to WinGo 1Min and extract data"""
        if not self.is_logged_in:
            await self.init()
        
        logger.info("🎯 Navigating to WinGo 1Min...")
        
        try:
            # Go to WinGo page directly
            await self.page.goto("https://7bdg.com/#/saasLottery/WinGo?gameCode=WinGo_1M&lottery=WinGo", timeout=60000)
            await self.page.wait_for_timeout(5000)
            
            # Scroll down
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(2000)
            
            # Try to find table
            rows = await self.page.query_selector_all("div[class*='row'], tr, div[role='row']")
            
            if not rows:
                logger.warning("⚠️ No rows found!")
                return None
            
            data = []
            for row in rows[:10]:
                cells = await row.query_selector_all("div, span, td")
                if len(cells) >= 4:
                    try:
                        period = await cells[0].text_content()
                        number = await cells[1].text_content()
                        
                        # Color detection
                        color_value = "unknown"
                        color_elem = await cells[2].query_selector("span, i")
                        if color_elem:
                            class_name = await color_elem.get_attribute("class") or ""
                            style = await color_elem.get_attribute("style") or ""
                            combined = (class_name + style).lower()
                            if "green" in combined:
                                color_value = "green"
                            elif "red" in combined:
                                color_value = "red"
                            elif "violet" in combined or "purple" in combined:
                                color_value = "violet"
                        
                        # Big/Small
                        size_text = await cells[3].text_content()
                        size = size_text.strip().lower() if size_text else "unknown"
                        
                        if period and number:
                            data.append({
                                "period": period.strip(),
                                "number": int(number.strip()),
                                "color": color_value,
                                "size": size,
                                "timestamp": str(datetime.now())
                            })
                            logger.info(f"📥 {period.strip()} | {number.strip()} | {color_value} | {size}")
                    except Exception as e:
                        logger.error(f"Row error: {e}")
                        continue
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Navigation error: {e}")
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
    msg = await update.message.reply_text("📡 Scraping BDG Game data...")
    
    try:
        global browser_session
        if not browser_session.is_logged_in:
            await browser_session.init()
        
        data = await browser_session.navigate_to_wingo()
        
        if not data:
            await msg.edit_text("❌ Failed to scrape data!")
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
    
    # Streak
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
    keyboard = [[InlineKeyboardButton("🎯 Open BDG Game", web_app={"url": "https://7bdg.com/#/saasLottery/WinGo?gameCode=WinGo_1M&lottery=WinGo"})]]
    await update.message.reply_text("🎯 **BDG Game**\n\nClick below:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "fetch":
        await query.edit_message_text("📡 Scraping BDG data...")
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
            # Reconnect on error
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
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("fetch", fetch_data))
    application.add_handler(CommandHandler("view", view_data))
    application.add_handler(CommandHandler("pattern", pattern))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("reset", reset_data))
    application.add_handler(CommandHandler("bdg", bdg_cmd))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start auto-fetch in background
    asyncio.create_task(auto_fetch())
    
    # Start polling (no webhook!)
    logger.info("✅ Bot started in polling mode!")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
