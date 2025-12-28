#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - COMPLETE VERSION
"""

import os
import sys
import logging
import random
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ===== CONFIGURATION =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "").split(",")
INVITE_ONLY = os.environ.get("INVITE_ONLY", "false").lower() == "true"

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== DATABASE =====
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect('serie_ai.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Predictions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            home_team TEXT,
            away_team TEXT,
            league TEXT,
            prediction TEXT,
            confidence REAL,
            home_goals INTEGER,
            away_goals INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Value bets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS value_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            match TEXT,
            selection TEXT,
            odds REAL,
            edge REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn, cursor

db_conn, db_cursor = init_database()

# ===== USER MANAGEMENT =====
class UserManager:
    def __init__(self):
        self.allowed_users = set()
        for admin_id in ADMIN_USER_ID:
            if admin_id.strip().isdigit():
                self.allowed_users.add(int(admin_id.strip()))
        logger.info(f"✅ Loaded {len(self.allowed_users)} admin users")
    
    def is_allowed(self, user_id):
        """Check if user is allowed"""
        if not INVITE_ONLY:
            return True
        return user_id in self.allowed_users
    
    def add_user(self, user_id):
        """Add user to allowed list"""
        if user_id not in self.allowed_users:
            self.allowed_users.add(user_id)
            return True
        return False
    
    def save_user_to_db(self, user_id, username, first_name, last_name):
        """Save user to database"""
        try:
            db_cursor.execute('''
                INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            db_conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error saving user: {e}")
            return False

user_manager = UserManager()

# ===== DATA MANAGER =====
class DataManager:
    def __init__(self):
        self.leagues = {
            'SA': '🇮🇹 Serie A',
            'PL': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League',
            'PD': '🇪🇸 La Liga',
            'BL1': '🇩🇪 Bundesliga',
            'CL': '🏆 Champions League'
        }
    
    def get_todays_matches(self):
        """Get today's matches"""
        return [
            {'home': 'Inter', 'away': 'Milan', 'league': 'SA', 'time': '20:45'},
            {'home': 'Man City', 'away': 'Liverpool', 'league': 'PL', 'time': '12:30'},
            {'home': 'Barcelona', 'away': 'Real Madrid', 'league': 'PD', 'time': '21:00'},
            {'home': 'Bayern', 'away': 'Dortmund', 'league': 'BL1', 'time': '17:30'},
            {'home': 'Juventus', 'away': 'Napoli', 'league': 'SA', 'time': '18:00'}
        ]
    
    def analyze_match(self, home, away, league="Unknown"):
        """Analyze a match and generate predictions"""
        # Simulate analysis
        home_prob = random.randint(40, 80)
        draw_prob = random.randint(15, 35)
        away_prob = 100 - home_prob - draw_prob
        
        home_goals = random.randint(0, 4)
        away_goals = random.randint(0, 3)
        
        # Determine prediction
        if home_prob > away_prob and home_prob > draw_prob:
            prediction = f"1 - {home} Win"
            confidence = home_prob
        elif draw_prob > home_prob and draw_prob > away_prob:
            prediction = "X - Draw"
            confidence = draw_prob
        else:
            prediction = f"2 - {away} Win"
            confidence = away_prob
        
        # Calculate value bet
        fair_odds = round(100 / confidence, 2)
        market_odds = round(fair_odds * random.uniform(0.92, 0.97), 2)
        edge = round((market_odds - fair_odds) * 100 / market_odds, 1)
        
        return {
            'probabilities': {
                'home': home_prob,
                'draw': draw_prob,
                'away': away_prob
            },
            'prediction': prediction,
            'confidence': confidence,
            'goals': {
                'home': home_goals,
                'away': away_goals,
                'total': home_goals + away_goals
            },
            'value_bet': {
                'selection': prediction.split(' - ')[1],
                'odds': market_odds,
                'fair_odds': fair_odds,
                'edge': edge,
                'stake': '⭐⭐' if edge > 5 else '⭐' if edge > 3 else '⏸️'
            },
            'league': self.leagues.get(league, league)
        }

data_manager = DataManager()

# ===== ACCESS CONTROL =====
def require_access(func):
    """Decorator to check user access"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not user_manager.is_allowed(user_id):
            await update.message.reply_text(
                "🔒 *Access Restricted*\n\n"
                "This bot is currently invite-only.\n"
                "Contact administrator for access.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

# ===== COMMAND HANDLERS =====
@require_access
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Save user to database
    user_manager.save_user_to_db(
        user.id,
        user.username,
        user.first_name,
        user.last_name
    )
    
    text = f"""
👋 *Welcome {user.first_name}!*

⚽ *SERIE AI PREDICTION BOT*

🎯 *Complete Features:*
• 📅 Today's Matches
• 🏆 League Standings  
• 🎯 Smart Predictions
• 💎 Value Bets
• 📊 Match Analysis
• 📈 Prediction History
• 👤 User Statistics

📋 *Available Commands:*
• /predict [Home] [Away] - Analyze any match
• /matches - Today's football matches
• /standings - League tables
• /value - Today's best value bets
• /mystats - Your personal statistics
• /admin - Check admin status
• /help - Complete guide

_Ready to analyze football matches with AI!_
"""
    
    keyboard = [
        [InlineKeyboardButton("📅 Today's Matches", callback_data="show_matches")],
        [InlineKeyboardButton("🎯 Make Prediction", callback_data="show_predict")],
        [InlineKeyboardButton("📊 My Statistics", callback_data="show_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

@require_access
async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /predict command"""
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "📝 *Usage:* `/predict [Home Team] [Away Team]`\n"
            "📝 *Example:* `/predict Inter Milan`\n"
            "📝 *Advanced:* `/predict \"Real Madrid\" \"Barcelona\" \"La Liga\"`",
            parse_mode='Markdown'
        )
        return
    
    home, away = args[0], args[1]
    league = args[2] if len(args) > 2 else "Unknown"
    
    # Analyze match
    analysis = data_manager.analyze_match(home, away, league)
    
    # Save prediction to database
    try:
        db_cursor.execute('''
            INSERT INTO predictions 
            (telegram_id, home_team, away_team, league, prediction, confidence, home_goals, away_goals)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            update.effective_user.id,
            home,
            away,
            league,
            analysis['prediction'],
            analysis['confidence'],
            analysis['goals']['home'],
            analysis['goals']['away']
        ))
        
        # Save value bet if edge is significant
        if analysis['value_bet']['edge'] > 3:
            db_cursor.execute('''
                INSERT INTO value_bets (telegram_id, match, selection, odds, edge)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                update.effective_user.id,
                f"{home} vs {away}",
                analysis['value_bet']['selection'],
                analysis['value_bet']['odds'],
                analysis['value_bet']['edge']
            ))
        
        db_conn.commit()
        save_note = "✅ *Saved to your history*"
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        save_note = "⚠️ *Not saved to history*"
    
    # Build response
    probs = analysis['probabilities']
    goals = analysis['goals']
    value = analysis['value_bet']
    
    response = f"""
⚡ *QUICK PREDICTION: {home} vs {away}*

🏆 *League:* {analysis['league']}

📊 *PROBABILITIES:*
• 🏠 {home} Win: `{probs['home']}%`
• ⚖️ Draw: `{probs['draw']}%`
• 🚌 {away} Win: `{probs['away']}%`

🎯 *PREDICTION:*
• Result: *{analysis['prediction']}*
• Confidence: `{analysis['confidence']}%`

🥅 *EXPECTED SCORE:*
• `{goals['home']}-{goals['away']}` (Total: {goals['total']} goals)

💎 *VALUE BET DETECTED:*
• Selection: `{value['selection']}`
• Market Odds: `{value['odds']}` (Fair: {value['fair_odds']})
• Edge: `+{value['edge']}%`
• Recommended Stake: {value['stake']}

{save_note}

_AI Analysis • {datetime.now().strftime('%Y-%m-%d %H:%M')}_
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@require_access
async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /matches command"""
    matches = data_manager.get_todays_matches()
    
    response = "📅 *TODAY'S FOOTBALL MATCHES*\n\n"
    
    # Group by league
    leagues = {}
    for match in matches:
        league_name = data_manager.leagues.get(match['league'], match['league'])
        if league_name not in leagues:
            leagues[league_name] = []
        leagues[league_name].append(match)
    
    for league_name, league_matches in leagues.items():
        response += f"*{league_name}*\n"
        for match in league_matches:
            response += f"• ⏰ {match['home']} vs {match['away']} ({match['time']})\n"
        response += "\n"
    
    response += f"📊 _Total: {len(matches)} matches_\n"
    response += "💡 _Use `/predict [Home] [Away]` for analysis_"
    
    await update.message.reply_text(response, parse_mode='Markdown')

@require_access
async def standings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /standings command"""
    keyboard = [
        [InlineKeyboardButton("🇮🇹 Serie A", callback_data="standings_SA")],
        [InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", callback_data="standings_PL")],
        [InlineKeyboardButton("🇪🇸 La Liga", callback_data="standings_PD")],
        [InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="standings_BL1")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏆 *Select League Standings:*", reply_markup=reply_markup, parse_mode='Markdown')

@require_access
async def value_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /value command"""
    # Get today's value bets from database
    try:
        db_cursor.execute('''
            SELECT match, selection, odds, edge 
            FROM value_bets 
            WHERE DATE(created_at) = DATE('now')
            ORDER BY edge DESC
            LIMIT 5
        ''')
        value_bets = db_cursor.fetchall()
    except:
        value_bets = []
    
    if not value_bets:
        response = "💎 *NO VALUE BETS TODAY*\n\nNo strong value bets identified for today's matches."
    else:
        response = "💎 *TODAY'S TOP VALUE BETS*\n\n"
        for i, bet in enumerate(value_bets, 1):
            response += f"`{i}.` *{bet[0]}*\n"
            response += f"   • Bet: `{bet[1]}`\n"
            response += f"   • Odds: `{bet[2]}` | Edge: `+{bet[3]}%`\n\n"
    
    response += """
📈 *Value Betting Strategy:*
• Only bet when edge > 3%
• Use 1/4 Kelly stake (conservative)
• Track all bets for analysis

_Generated by Serie AI • Database Edition_
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@require_access
async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mystats command"""
    user_id = update.effective_user.id
    
    # Get user statistics
    try:
        # Count predictions
        db_cursor.execute("SELECT COUNT(*) FROM predictions WHERE telegram_id = ?", (user_id,))
        total_predictions = db_cursor.fetchone()[0]
        
        # Count value bets
        db_cursor.execute("SELECT COUNT(*) FROM value_bets WHERE telegram_id = ?", (user_id,))
        total_value_bets = db_cursor.fetchone()[0]
        
        # Get average confidence
        db_cursor.execute("SELECT AVG(confidence) FROM predictions WHERE telegram_id = ?", (user_id,))
        avg_confidence = db_cursor.fetchone()[0] or 0
        
        # Get recent predictions
        db_cursor.execute('''
            SELECT home_team, away_team, prediction, created_at
            FROM predictions 
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            LIMIT 3
        ''', (user_id,))
        recent_predictions = db_cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        total_predictions = 0
        total_value_bets = 0
        avg_confidence = 0
        recent_predictions = []
    
    # Calculate user level
    if total_predictions > 100:
        user_level = "🟡 Master"
        level_emoji = "👑"
    elif total_predictions > 50:
        user_level = "🟣 Expert"
        level_emoji = "💎"
    elif total_predictions > 20:
        user_level = "🔵 Pro"
        level_emoji = "⚡"
    elif total_predictions > 5:
        user_level = "🟢 Intermediate"
        level_emoji = "🚀"
    else:
        user_level = "⚪ Beginner"
        level_emoji = "🌱"
    
    # Build response
    response = f"""
{level_emoji} *YOUR STATISTICS*

👤 *Profile:*
• Name: {update.effective_user.first_name}
• ID: `{user_id}`
• Level: {user_level}

📊 *Database Records:*
• Total Predictions: `{total_predictions}`
• Value Bets Found: `{total_value_bets}`
• Average Confidence: `{round(avg_confidence, 1) if avg_confidence else 0}%`

🏆 *Recent Activity:*
"""
    
    if recent_predictions:
        for pred in recent_predictions:
            home, away, result, created = pred
            date_str = created[:10] if isinstance(created, str) else created.strftime('%Y-%m-%d') if hasattr(created, 'strftime') else "Recent"
            response += f"• {home} vs {away} ({date_str})\n"
    else:
        response += "• No predictions yet\n"
    
    response += f"""
📈 *Tips for Improvement:*
1. Focus on matches with >65% confidence
2. Track value bets with edge > 3%
3. Review your predictions weekly

_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@require_access
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user_id = update.effective_user.id
    is_admin = user_id in user_manager.allowed_users
    
    # Database stats
    try:
        db_cursor.execute("SELECT COUNT(*) FROM users")
        total_users = db_cursor.fetchone()[0]
        
        db_cursor.execute("SELECT COUNT(*) FROM predictions")
        total_predictions = db_cursor.fetchone()[0]
    except:
        total_users = 0
        total_predictions = 0
    
    response = f"""
🔐 *ADMIN STATUS CHECK*

👤 *Your Info:*
• ID: `{user_id}`
• Name: {update.effective_user.first_name}
• Admin Status: {'✅ YES' if is_admin else '❌ NO'}

📋 *System Status:*
• Invite Only: `{INVITE_ONLY}`
• Total Users in DB: `{total_users}`
• Total Predictions: `{total_predictions}`
• Loaded Admins: `{len(user_manager.allowed_users)}`

👥 *Admin Users:*
"""
    
    if user_manager.allowed_users:
        for admin_id in user_manager.allowed_users:
            response += f"• `{admin_id}`\n"
    else:
        response += "• No admin users configured\n"
    
    response += f"""
💡 *To add yourself as admin:*
1. Stop the bot
2. Set environment variable:
   ```bash
   export ADMIN_USER_ID="{user_id}"
 await update.message.reply_text(response, parse_mode='Markdown')
@require_access
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
"""Handle /help command"""
help_text = """

await update.message.reply_text(help_text, parse_mode='Markdown')
===== CALLBACK HANDLER =====
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
"""Handle callback queries"""
query = update.callback_query
await query.answer()

data = query.data

if data == "show_matches":
    await matches_command(update, context)
elif data == "show_predict":
    await query.edit_message_text("Type: `/predict [Home Team] [Away Team]`\nExample: `/predict Inter Milan`", parse_mode='Markdown')
elif data == "show_stats":
    await mystats_command(update, context)
elif data == "back_to_start":
    await start_command(update, context)
elif data.startswith("standings_"):
    league_code = data.replace("standings_", "")
    league_name = data_manager.leagues.get(league_code, league_code)
    
    # Generate sample standings
    teams = [
        ("Team A", 45, 14, 3, 2, 38, 15, 23),
        ("Team B", 42, 13, 3, 3, 35, 18, 17),
        ("Team C", 40, 12, 4, 3, 32, 20, 12),
        ("Team D", 38, 11, 5, 3, 30, 22, 8),
        ("Team E", 35, 10, 5, 4, 28, 25, 3)
    ]
    
    response = f"🏆 *{league_name} STANDINGS*\n\n"
    response += "```\n"
    response += "Pos | Team     | Pts | Pld | W  | D  | L  | GF | GA | GD\n"
    response += "----|----------|-----|-----|----|----|----|----|----|----\n"
    
    for i, (team, pts, pld, w, d, l, gf, ga, gd) in enumerate(teams, 1):
        response += f"{i:3} | {team:8} | {pts:3} | {pld:3} | {w:2} | {d:2} | {l:2} | {gf:2} | {ga:2} | {gd:3}\n"
    
    response += "```\n"
    response += f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
    
    await query.edit_message_text(response, parse_mode='Markdown')
else:
    await query.edit_message_text("❌ Unknown action. Use /start", parse_mode='Markdown')
===== MAIN FUNCTION =====
def main():
"""Main function to run the bot"""
logger.info("🚀 Starting Serie AI Bot...")
logger.info(f"📊 Loaded {len(user_manager.allowed_users)} admin users")

# Create application
application = Application.builder().token(BOT_TOKEN).build()

# Add command handlers
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("predict", predict_command))
application.add_handler(CommandHandler("matches", matches_command))
application.add_handler(CommandHandler("standings", standings_command))
application.add_handler(CommandHandler("value", value_command))
application.add_handler(CommandHandler("mystats", mystats_command))
application.add_handler(CommandHandler("admin", admin_command))
application.add_handler(CommandHandler("help", help_command))

# Add callback handler
application.add_handler(CallbackQueryHandler(callback_handler))

# Run bot
logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
logger.info("✅ All features: Database, Predictions, Value Bets, Statistics")

application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
===== CLEANUP =====
def cleanup():
"""Cleanup on exit"""
logger.info("👋 Cleaning up...")
db_conn.close()

===== ENTRY POINT =====
if name == "main":
try:
main()
except KeyboardInterrupt:
logger.info("👋 Bot stopped by user")
cleanup()
except Exception as e:
logger.error(f"💥 Fatal error: {e}")
cleanup()
sys.exit(1)  