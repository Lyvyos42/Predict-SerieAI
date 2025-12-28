#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - WITH AUTO MESSAGES & INVITE-ONLY
Advanced features for professional deployment
"""

import os
import sys
import logging
import random
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask
from threading import Thread
import schedule
import time

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "").split(",")  # Comma-separated admin IDs
INVITE_ONLY = os.environ.get("INVITE_ONLY", "true").lower() == "true"  # Default: true

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATA STORAGE ==========
class UserStorage:
    """Manages user data and permissions"""
    
    def __init__(self):
        self.allowed_users = set()  # Users who can access the bot
        self.subscribers = set()    # Users who want auto messages
        self.user_preferences = {}  # User preferences
        self.load_data()
        
        # Add admin users automatically
        for admin_id in ADMIN_USER_ID:
            if admin_id.strip().isdigit():
                self.allowed_users.add(int(admin_id.strip()))
    
    def load_data(self):
        """Load user data from file (simple JSON)"""
        try:
            with open('user_data.json', 'r') as f:
                data = json.load(f)
                self.allowed_users = set(data.get('allowed_users', []))
                self.subscribers = set(data.get('subscribers', []))
                self.user_preferences = data.get('preferences', {})
        except FileNotFoundError:
            self.save_data()
    
    def save_data(self):
        """Save user data to file"""
        data = {
            'allowed_users': list(self.allowed_users),
            'subscribers': list(self.subscribers),
            'preferences': self.user_preferences,
            'last_updated': datetime.now().isoformat()
        }
        with open('user_data.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        if not INVITE_ONLY:
            return True  # Open to everyone if INVITE_ONLY is false
        return user_id in self.allowed_users
    
    def add_user(self, user_id: int, invited_by: int = None) -> bool:
        """Add a new user to allowed list"""
        if user_id not in self.allowed_users:
            self.allowed_users.add(user_id)
            self.save_data()
            logger.info(f"✅ User {user_id} added to allowed list")
            return True
        return False
    
    def remove_user(self, user_id: int) -> bool:
        """Remove user from allowed list"""
        if user_id in self.allowed_users:
            self.allowed_users.remove(user_id)
            self.subscribers.discard(user_id)
            self.save_data()
            logger.info(f"❌ User {user_id} removed from allowed list")
            return True
        return False
    
    def subscribe_user(self, user_id: int) -> bool:
        """Subscribe user to auto messages"""
        if user_id in self.allowed_users:
            self.subscribers.add(user_id)
            self.save_data()
            logger.info(f"🔔 User {user_id} subscribed to auto messages")
            return True
        return False
    
    def unsubscribe_user(self, user_id: int) -> bool:
        """Unsubscribe user from auto messages"""
        if user_id in self.subscribers:
            self.subscribers.remove(user_id)
            self.save_data()
            logger.info(f"🔕 User {user_id} unsubscribed from auto messages")
            return True
        return False
    
    def get_subscribers(self) -> List[int]:
        """Get all subscribers"""
        return list(self.subscribers)
    
    def get_allowed_users(self) -> List[int]:
        """Get all allowed users"""
        return list(self.allowed_users)
    
    def get_user_count(self) -> Dict:
        """Get user statistics"""
        return {
            'total_allowed': len(self.allowed_users),
            'total_subscribers': len(self.subscribers),
            'invite_only': INVITE_ONLY
        }

# ========== AUTO MESSAGE SCHEDULER ==========
class AutoMessenger:
    """Handles automatic messages to users"""
    
    def __init__(self, bot, user_storage: UserStorage):
        self.bot = bot
        self.user_storage = user_storage
        self.running = False
        
        # Message templates
        self.templates = {
            'morning_update': """
🌅 *GOOD MORNING FOOTBALL FANS!*

⚽ *Today's Top Matches:*
• Inter vs Milan (Serie A) - 20:45
• Barcelona vs Real Madrid (La Liga) - 21:00
• Bayern vs Dortmund (Bundesliga) - 17:30

💎 *Value Bet Alert:*
Inter vs Milan - Over 2.5 Goals @ 2.10
Edge: +7.3% | Confidence: High

_Use /predict for detailed analysis_
            """,
            
            'value_bet_alert': """
🔔 *VALUE BET ALERT!*

Match: {match}
Bet: {bet}
Odds: {odds}
Edge: {edge}
Confidence: {confidence}

_This bet has >5% expected value_
            """,
            
            'match_reminder': """
⏰ *MATCH STARTING SOON!*

{match} starts in 30 minutes!

Use /predict for last-minute analysis
            """,
            
            'weekly_stats': """
📊 *WEEKLY PERFORMANCE REPORT*

📈 Your Stats (This Week):
• Predictions made: {predictions}
• Accuracy: {accuracy}%
• ROI: {roi}%
• Best Bet: {best_bet}

💡 Tip: {tip}

_Keep up the good work!_
            """
        }
    
    async def send_to_subscribers(self, message: str, parse_mode: str = 'Markdown'):
        """Send message to all subscribers"""
        subscribers = self.user_storage.get_subscribers()
        if not subscribers:
            return 0
        
        sent_count = 0
        for user_id in subscribers:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode
                )
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
        
        logger.info(f"📢 Sent message to {sent_count}/{len(subscribers)} subscribers")
        return sent_count
    
    async def send_daily_update(self):
        """Send daily morning update"""
        message = self.templates['morning_update']
        return await self.send_to_subscribers(message)
    
    async def send_value_bet_alert(self, match: str, bet: str, odds: float, edge: str):
        """Send value bet alert"""
        message = self.templates['value_bet_alert'].format(
            match=match, bet=bet, odds=odds, edge=edge, confidence="High"
        )
        return await self.send_to_subscribers(message)
    
    async def send_match_reminder(self, match: str):
        """Send match reminder"""
        message = self.templates['match_reminder'].format(match=match)
        return await self.send_to_subscribers(message)
    
    async def send_personal_message(self, user_id: int, message: str):
        """Send personal message to specific user"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send personal message to {user_id}: {e}")
            return False

# ========== FLASK FOR RAILWAY ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "⚽ Serie AI Bot - Auto Messages & Invite-Only"

@app.route('/health')
def health():
    return "✅ OK", 200

@app.route('/stats')
def stats():
    """API endpoint for statistics"""
    stats_data = {
        'status': 'online',
        'users': user_storage.get_user_count(),
        'features': ['auto_messages', 'invite_only', 'value_bets', 'predictions'],
        'timestamp': datetime.now().isoformat()
    }
    return json.dumps(stats_data, indent=2)

def run_flask():
    port = int(os.getenv("PORT", "8080"))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== GLOBAL INSTANCES ==========
user_storage = UserStorage()
data_manager = None  # Your existing DataManager class
auto_messenger = None

# ========== ACCESS CONTROL MIDDLEWARE ==========
def access_control(func):
    """Decorator to check if user is allowed"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not user_storage.is_user_allowed(user_id):
            # Check if this is an invitation attempt
            if update.message and update.message.text:
                if update.message.text.startswith('/start'):
                    # First contact - check for invite code
                    parts = update.message.text.split()
                    if len(parts) > 1 and parts[1] == "invite123":  # Simple invite code
                        user_storage.add_user(user_id)
                        await update.message.reply_text(
                            "✅ *Invitation accepted!* Welcome to Serie AI Bot.\n\n"
                            "Use /start to access all features.",
                            parse_mode='Markdown'
                        )
                        return
            
            # User not allowed and no valid invite code
            await update.message.reply_text(
                "🔒 *Access Restricted*\n\n"
                "This bot is invitation-only.\n"
                "Please contact the administrator for access.\n\n"
                "If you have an invite code, use:\n"
                "`/start invite123`",
                parse_mode='Markdown'
            )
            return
        
        # User is allowed, proceed with command
        return await func(update, context, *args, **kwargs)
    
    return wrapper

# ========== ADMIN COMMANDS ==========
@access_control
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if str(user_id) not in ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    stats = user_storage.get_user_count()
    
    response = f"""
🔐 *ADMIN PANEL*

📊 *Statistics:*
• Total Allowed Users: {stats['total_allowed']}
• Active Subscribers: {stats['total_subscribers']}
• Invite-Only Mode: {'✅ Enabled' if stats['invite_only'] else '❌ Disabled'}

⚙️ *Admin Commands:*
/adduser [user_id] - Add user to allowed list
/removeuser [user_id] - Remove user from allowed list
/listusers - List all allowed users
/broadcast [message] - Send message to all subscribers
/toggleinvite - Toggle invite-only mode
/substats - Subscription statistics

🔄 *Auto Messages:*
/sendupdate - Send daily update now
/sendalert - Send value bet alert
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add user to allowed list (admin only)"""
    user_id = update.effective_user.id
    if str(user_id) not in ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: `/adduser [user_id]`", parse_mode='Markdown')
        return
    
    try:
        new_user_id = int(args[0])
        if user_storage.add_user(new_user_id, invited_by=user_id):
            await update.message.reply_text(f"✅ User {new_user_id} added successfully.")
        else:
            await update.message.reply_text(f"⚠️ User {new_user_id} already exists.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

@access_control
async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all allowed users (admin only)"""
    user_id = update.effective_user.id
    if str(user_id) not in ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    users = user_storage.get_allowed_users()
    if not users:
        await update.message.reply_text("No users in the allowed list.")
        return
    
    response = "👥 *ALLOWED USERS*\n\n"
    for i, uid in enumerate(users[:20], 1):  # Show first 20
        response += f"{i}. `{uid}`\n"
    
    if len(users) > 20:
        response += f"\n_Showing 20 of {len(users)} users_"
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all subscribers (admin only)"""
    user_id = update.effective_user.id
    if str(user_id) not in ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Usage: `/broadcast [message]`")
        return
    
    subscribers = user_storage.get_subscribers()
    if not subscribers:
        await update.message.reply_text("❌ No subscribers to broadcast to.")
        return
    
    await update.message.reply_text(f"📢 Broadcasting to {len(subscribers)} users...")
    
    sent = 0
    for sub_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=sub_id,
                text=f"📢 *ADMIN BROADCAST*\n\n{message}",
                parse_mode='Markdown'
            )
            sent += 1
            await asyncio.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"✅ Broadcast sent to {sent}/{len(subscribers)} users.")

# ========== USER COMMANDS ==========
@access_control
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu with access control"""
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    # Welcome message based on user status
    if INVITE_ONLY:
        access_status = "🔒 *Invitation-Only Access*"
    else:
        access_status = "🔓 *Open Access*"
    
    # Check subscription status
    is_subscribed = user_id in user_storage.subscribers
    
    welcome_text = f"""
{access_status}

👋 Welcome *{first_name}* to SERIE AI BOT!

⚽ *Complete Prediction Platform*

🎯 *FEATURES:*
• 📅 Today's Matches
• 🏆 League Standings  
• 🎯 AI Predictions
• 💎 Value Bets
• 🔔 Auto Alerts ({'✅ Subscribed' if is_subscribed else '❌ Not subscribed'})

🔧 *USER COMMANDS:*
/subscribe - Enable auto messages
/unsubscribe - Disable auto messages
/mystats - Your usage statistics
/invite - Get invite info

👇 Tap a button below:
"""
    
    keyboard = [
        [InlineKeyboardButton("📅 Today's Matches", callback_data="show_matches")],
        [InlineKeyboardButton("🏆 League Standings", callback_data="show_standings_menu")],
        [InlineKeyboardButton("🎯 Smart Prediction", callback_data="show_predict_info")],
        [InlineKeyboardButton("💎 Value Bets", callback_data="show_value_bets")],
        [
            InlineKeyboardButton("🔔 Subscribe", callback_data="user_subscribe"),
            InlineKeyboardButton("📊 My Stats", callback_data="user_stats")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

@access_control
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to auto messages"""
    user_id = update.effective_user.id
    
    if user_storage.subscribe_user(user_id):
        response = """
✅ *SUBSCRIPTION ACTIVATED*

You will now receive:
• Morning match updates (9:00 AM)
• Value bet alerts
• Match reminders
• Weekly performance reports

Use /unsubscribe to stop messages.
"""
    else:
        response = "⚠️ You are already subscribed or not in the allowed list."
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from auto messages"""
    user_id = update.effective_user.id
    
    if user_storage.unsubscribe_user(user_id):
        response = "🔕 *Unsubscribed* - You will no longer receive auto messages."
    else:
        response = "⚠️ You were not subscribed."
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    is_allowed = user_storage.is_user_allowed(user_id)
    is_subscribed = user_id in user_storage.subscribers
    
    response = f"""
📊 *YOUR STATISTICS*

👤 User: {first_name}
🆔 ID: `{user_id}`

🔐 *Access Status:*
• Allowed: {'✅ Yes' if is_allowed else '❌ No'}
• Invite-Only Mode: {'✅ Enabled' if INVITE_ONLY else '❌ Disabled'}

🔔 *Subscriptions:*
• Auto Messages: {'✅ Subscribed' if is_subscribed else '❌ Not subscribed'}

⚽ *Usage:*
• Predictions made: 0 (coming soon)
• Accuracy: 0% (coming soon)
• Favorite league: Not set

⚙️ *Commands:*
/subscribe - Enable auto messages
/unsubscribe - Disable auto messages
/settings - Configure preferences (coming soon)
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show invite information"""
    if not INVITE_ONLY:
        response = "🔓 *Open Access* - Anyone can use this bot."
    else:
        response = """
🔒 *INVITATION-ONLY ACCESS*

This bot requires an invitation to use.

*How to get access:*
1. Contact the administrator
2. Receive your personal invite code
3. Use: `/start [your_invite_code]`

*Current Invite Code:* `invite123`

*Note:* This is a demo code. Real codes are personalized.
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ========== BUTTON HANDLERS ==========
@access_control
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "user_subscribe":
        if user_storage.subscribe_user(user_id):
            await query.edit_message_text(
                "✅ *Subscribed to Auto Messages!*\n\n"
                "You will now receive:\n"
                "• Daily match updates\n"
                "• Value bet alerts\n"
                "• Match reminders\n\n"
                "Use /unsubscribe to stop.",
                parse_mode='Markdown'
            )
        else:
            await query.answer("⚠️ Already subscribed or not allowed.")
    
    elif data == "user_stats":
        await mystats_command(update, context)
        await start_command(update, context)
    
    elif data == "show_matches":
        # Your existing matches callback
        pass
    
    elif data == "show_standings_menu":
        # Your existing standings callback
        pass
    
    elif data.startswith("standings_"):
        # Your existing specific standings callback
        pass
    
    elif data == "show_predict_info":
        # Your existing prediction info callback
        pass
    
    elif data == "show_value_bets":
        # Your existing value bets callback
        pass
    
    elif data == "show_help":
        # Your existing help callback
        pass
    
    elif data == "back_to_menu":
        await start_command(update, context)

# ========== AUTO MESSAGE SCHEDULER THREAD ==========
async def auto_message_scheduler(bot):
    """Background task for sending auto messages"""
    messenger = AutoMessenger(bot, user_storage)
    
    while True:
        try:
            now = datetime.now()
            
            # Send morning update at 9:00 AM
            if now.hour == 9 and now.minute == 0:
                logger.info("⏰ Sending morning update...")
                await messenger.send_daily_update()
            
            # Send value bet alert at 2:00 PM
            elif now.hour == 14 and now.minute == 0:
                logger.info("⏰ Sending value bet alert...")
                await messenger.send_value_bet_alert(
                    match="Inter vs Milan",
                    bet="Over 2.5 Goals",
                    odds=2.10,
                    edge="+7.3%"
                )
            
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Auto message scheduler error: {e}")
            await asyncio.sleep(60)

# ========== MAIN FUNCTION ==========
async def main_async():
    """Async main function"""
    global auto_messenger
    
    print("=" * 60)
    print("⚽ SERIE AI BOT - ADVANCED FEATURES")
    print("=" * 60)
    
    # Initialize user storage
    print(f"👥 User Storage: {user_storage.get_user_count()['total_allowed']} allowed users")
    print(f"🔒 Invite-Only Mode: {'✅ Enabled' if INVITE_ONLY else '❌ Disabled'}")
    
    if ADMIN_USER_ID:
        print(f"👑 Admin Users: {len(ADMIN_USER_ID)} configured")
    
    # Start Flask for Railway
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Build bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers with @access_control
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("invite", invite_command))
    
    # Admin commands
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("adduser", add_user_command))
    application.add_handler(CommandHandler("listusers", list_users_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Keep your existing command handlers (with @access_control decorator added)
    # application.add_handler(CommandHandler("predict", quick_predict_command))
    # application.add_handler(CommandHandler("matches", todays_matches_command))
    # application.add_handler(CommandHandler("standings", standings_command))
    # application.add_handler(CommandHandler("value", value_bets_command))
    # application.add_handler(CommandHandler("help", help_command))
    
    # Register button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Initialize auto messenger
    auto_messenger = AutoMessenger(application.bot, user_storage)
    
    print("✅ Bot initialized with advanced features")
    print("📢 Auto Messages: Enabled")
    print("🔒 Access Control: Enabled")
    print("=" * 60)
    
    # Start auto message scheduler in background
    asyncio.create_task(auto_message_scheduler(application.bot))
    
    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("🤖 Bot is running with auto messages & invite-only access!")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
        await application.stop()

def main():
    """Main entry point"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()