import os
import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable is not set.")
    print("💡 Go to Railway → Settings → Variables → Add BOT_TOKEN")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== FLASK WEB SERVER ==========
# Railway requires a web server for health checks
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 Serie AI Bot is running!"

@web_app.route('/health')
def health():
    return "✅ OK", 200

def run_flask():
    """Run Flask in a separate thread for Railway"""
    port = int(os.getenv("PORT", "8080"))
    web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ========== TELEGRAM BOT ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ *Bot Connected!* \n\n"
        "Try these commands:\n"
        "• `/predict Inter Milan` - Get match prediction\n"
        "• `/help` - Show help message",
        parse_mode='Markdown'
    )

async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Please provide two team names.\n"
            "*Example:* `/predict Inter Milan`",
            parse_mode='Markdown'
        )
        return
    
    home_team, away_team = context.args[0], context.args[1]
    
    # Simple prediction logic
    response = f"""
⚽ *Prediction: {home_team} vs {away_team}*

📊 Our Analysis:
• Home Win Probability: 62%
• Draw Probability: 24%
• Away Win Probability: 14%

🎯 Recommendation: **{home_team} to Win**
💰 Confidence: High

_Simulated data for demonstration_"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *Available Commands*

*/start* - Welcome message
*/predict [Team A] [Team B]* - Get match prediction
    Example: `/predict Barcelona RealMadrid`
*/help* - Show this message

Bot is running on Railway 🚀"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors but don't crash"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function - This is the corrected structure"""
    print("=" * 50)
    print("🚀 SERIE AI BOT - CORRECTED VERSION")
    print("=" * 50)
    
    # 1. Start Flask web server in background thread (for Railway)
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask web server started (for Railway health checks)")
    
    # 2. Build the Telegram bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 3. Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("predict", predict_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_error_handler(error_handler)
    
    logger.info("Bot initialized. Starting polling...")
    print("✅ Bot is ready! Testing commands:")
    print("   1. /start")
    print("   2. /predict Inter Milan")
    print("   3. /help")
    print("=" * 50)
    
    # 4. Start the bot (this runs forever)
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()