#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - SIMPLE WORKING VERSION
"""

import os
import sys
from telegram.ext import Application, CommandHandler

# Check token
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

# Simple command handlers
async def start(update, context):
    await update.message.reply_text("✅ Bot is working! Use /help for commands.")

async def help_cmd(update, context):
    text = """
🎯 *SERIE AI BOT*

📋 *Commands:*
• /start - Start bot
• /help - Show help
• /test - Test command
• /id - Show your ID
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def test(update, context):
    await update.message.reply_text("🧪 Test successful! Bot is responding.")

async def id_cmd(update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Your ID: `{user_id}`", parse_mode='Markdown')

async def admin_cmd(update, context):
    user_id = update.effective_user.id
    text = f"""
🔐 *ADMIN STATUS*

👤 Your ID: `{user_id}`
👤 Name: {update.effective_user.first_name}

💡 *To add yourself as admin:*
Set environment variable:
ADMIN_USER_ID="{user_id}"
"""
    await update.message.reply_text(text, parse_mode='Markdown')

# Main function
def main():
    print("🚀 Starting bot...")
    
    # Create bot
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    
    # Run
    print("🤖 Bot running. Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

# Start
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("👋 Bot stopped")
    except Exception as e:
        print(f"💥 Error: {e}")