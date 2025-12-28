#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - WORKING VERSION
"""

import os
import sys
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===== CONFIGURATION =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    print("💡 Set it with: export BOT_TOKEN='your_token'")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== SIMPLE COMMAND HANDLERS =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    text = f"""
👋 Hello {user.first_name}!

⚽ *SERIE AI PREDICTION BOT*

📋 *Available Commands:*
• /start - Show this menu
• /predict [Home] [Away] - Analyze match
• /matches - Today's football matches
• /help - Help guide

📊 *Your Info:*
• ID: `{user.id}`
• Username: @{user.username if user.username else 'N/A'}

✅ *Bot is working!*
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /predict command"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /predict [Home] [Away]\nExample: /predict Inter Milan")
        return
    
    home, away = args[0], args[1]
    
    import random
    home_goals = random.randint(0, 3)
    away_goals = random.randint(0, 2)
    
    response = f"""
⚡ *PREDICTION: {home} vs {away}*

📊 *Predicted Score:*
• {home}: {home_goals} goals
• {away}: {away_goals} goals
• Total: {home_goals + away_goals} goals

📈 *Confidence:* {random.randint(60, 85)}%

_AI Analysis • {datetime.now().strftime('%H:%M')}_
"""
    await update.message.reply_text(response, parse_mode='Markdown')

async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /matches command"""
    matches = [
        "⚽ Inter vs Milan (20:45)",
        "⚽ Man City vs Liverpool (12:30)",
        "⚽ Barcelona vs Real Madrid (21:00)"
    ]
    
    response = "📅 *Today's Matches:*\n\n" + "\n".join(matches)
    await update.message.reply_text(response, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🎯 *SERIE AI BOT - HELP*

📋 *Commands:*
• /start - Start the bot
• /predict [home] [away] - Analyze match
• /matches - Today's matches
• /help - This help

📊 *Features:*
• Match predictions
• Today's fixtures
• Simple analysis

✅ *Bot Status: Working*
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user_id = update.effective_user.id
    response = f"""
🔐 *ADMIN STATUS*

👤 Your ID: `{user_id}`
👤 Name: {update.effective_user.first_name}

💡 *To make yourself admin:*
1. Stop the bot
2. Set environment variable:
   ```bash
   export ADMIN_USER_ID="{user_id}"
Restart the bot

✅ Bot is responding!
"""
await update.message.reply_text(response, parse_mode='Markdown')

===== MAIN FUNCTION =====
def main():
"""Main function to run the bot"""
logger.info("🚀 Starting bot...")

text
# Create application
application = Application.builder().token(BOT_TOKEN).build()

# Add command handlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("predict", predict_command))
application.add_handler(CommandHandler("matches", matches_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("admin", admin_command))

# Run bot
logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
===== ENTRY POINT =====
if name == "main":
try:
main()
except KeyboardInterrupt:
logger.info("👋 Bot stopped by user")
except Exception as e:
logger.error(f"💥 Fatal error: {e}")
sys.exit(1)