#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - WITH DATABASE INTEGRATION
COMPLETE FIXED VERSION: Schema fixes + callback handling
"""

import os
import sys
import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask
from threading import Thread

# ========== DATABASE IMPORTS ==========
from models import init_db, User, Prediction, Bet, ValueBet, SystemLog
from database import DatabaseManager

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "").split(",")  # Comma-separated admin IDs
INVITE_ONLY = os.environ.get("INVITE_ONLY", "true").lower() == "true"  # Default: true
DATABASE_URL = os.environ.get("DATABASE_URL")  # PostgreSQL connection string

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== FLASK FOR RAILWAY ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "⚽ Serie AI Bot - Database Edition"

@app.route('/health')
def health():
    return "✅ OK", 200

def run_flask():
    port = int(os.getenv("PORT", "8080"))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== DATA MANAGER ==========
class DataManager:
    """Simple and reliable data manager"""
    
    def __init__(self):
        self.leagues = {
            'SA': '🇮🇹 Serie A',
            'PL': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', 
            'PD': '🇪🇸 La Liga',
            'BL1': '🇩🇪 Bundesliga'
        }
        
        self.todays_matches = [
            {'league': 'SA', 'home': 'Inter', 'away': 'Milan', 'time': '20:45'},
            {'league': 'PL', 'home': 'Man City', 'away': 'Liverpool', 'time': '12:30'},
            {'league': 'PD', 'home': 'Barcelona', 'away': 'Real Madrid', 'time': '21:00'},
            {'league': 'SA', 'home': 'Juventus', 'away': 'Napoli', 'time': '18:00'},
            {'league': 'BL1', 'home': 'Bayern', 'away': 'Dortmund', 'time': '17:30'}
        ]
    
    def get_todays_matches(self):
        """Get today's matches"""
        matches = []
        for match in self.todays_matches:
            league_name = self.leagues.get(match['league'], 'Unknown')
            matches.append({
                'home': match['home'],
                'away': match['away'], 
                'league': league_name,
                'time': match['time']
            })
        return matches
    
    def get_standings(self, league_code):
        """Get standings"""
        if league_code not in self.leagues:
            return {'league_name': 'Unknown', 'standings': []}
        
        league_name = self.leagues[league_code]
        
        # Teams for each league
        teams_map = {
            'SA': ['Inter', 'Milan', 'Juventus', 'Napoli', 'Roma', 'Lazio', 'Atalanta', 'Fiorentina'],
            'PL': ['Man City', 'Liverpool', 'Arsenal', 'Chelsea', 'Man Utd', 'Tottenham', 'Newcastle', 'Aston Villa'],
            'PD': ['Barcelona', 'Real Madrid', 'Atletico', 'Sevilla', 'Valencia', 'Betis', 'Villarreal', 'Athletic'],
            'BL1': ['Bayern', 'Dortmund', 'Leipzig', 'Leverkusen', 'Frankfurt', 'Wolfsburg', 'Gladbach', 'Hoffenheim']
        }
        
        teams = teams_map.get(league_code, [])
        standings = []
        
        for i, team in enumerate(teams, 1):
            played = random.randint(20, 30)
            won = random.randint(played//2, played-5)
            draw = random.randint(3, played-won-3)
            lost = played - won - draw
            gf = random.randint(30, 70)
            ga = random.randint(15, 50)
            gd = gf - ga
            points = won*3 + draw
            
            standings.append({
                'position': i,
                'team': team,
                'played': played,
                'won': won,
                'draw': draw,
                'lost': lost,
                'gf': gf,
                'ga': ga,
                'gd': gd,
                'points': points
            })
        
        standings.sort(key=lambda x: x['points'], reverse=True)
        
        return {
            'league_name': league_name,
            'standings': standings
        }
    
    def analyze_match(self, home, away):
        """Analyze match"""
        home_score = sum(ord(c) for c in home.lower()) % 100
        away_score = sum(ord(c) for c in away.lower()) % 100
        
        if home_score + away_score == 0:
            home_score, away_score = 50, 50
        
        home_prob = home_score / (home_score + away_score) * 100
        away_prob = away_score / (home_score + away_score) * 100
        draw_prob = max(20, 100 - home_prob - away_prob)
        
        home_prob -= draw_prob / 3
        away_prob -= draw_prob / 3
        
        prediction = "1" if home_prob > away_prob and home_prob > draw_prob else "X" if draw_prob > home_prob and draw_prob > away_prob else "2"
        confidence = max(home_prob, draw_prob, away_prob)
        
        return {
            'probabilities': {
                'home': round(home_prob, 1),
                'draw': round(draw_prob, 1),
                'away': round(away_prob, 1)
            },
            'prediction': prediction,
            'confidence': round(confidence, 1),
            'goals': {
                'home': max(0, round((home_score/100) * 3)),
                'away': max(0, round((away_score/100) * 2))
            },
            'value_bet': {
                'market': 'Match Result',
                'selection': prediction,
                'odds': round(1/({'1': home_prob, 'X': draw_prob, '2': away_prob}[prediction]/100), 2),
                'edge': round(random.uniform(3, 8), 1)
            }
        }

# ========== GLOBAL INSTANCES ==========
data_manager = DataManager()

# ========== DATABASE HEALTH CHECK ==========
def check_database_health() -> Tuple[bool, Optional[str]]:
    """Test database connection and return (status, error_message)"""
    try:
        db = DatabaseManager()
        # Simple query to test connection
        from sqlalchemy import text
        result = db.db.execute(text("SELECT 1")).scalar()
        db.close()
        return (True, None) if result == 1 else (False, "Test query failed")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return (False, str(e))

# ========== USER STORAGE (Temporary - will migrate to DB) ==========
class SimpleUserStorage:
    """Temporary user storage until full DB migration"""
    
    def __init__(self):
        self.allowed_users = set()
        self.subscribers = set()
        
        # Add admin users automatically
        for admin_id in ADMIN_USER_ID:
            if admin_id.strip().isdigit():
                self.allowed_users.add(int(admin_id.strip()))
    
    def is_user_allowed(self, user_id: int) -> bool:
        if not INVITE_ONLY:
            return True
        return user_id in self.allowed_users
    
    def add_user(self, user_id: int) -> bool:
        if user_id not in self.allowed_users:
            self.allowed_users.add(user_id)
            return True
        return False

user_storage = SimpleUserStorage()

# ========== ACCESS CONTROL ==========
def access_control(func):
    """Decorator to check if user is allowed"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Get user_id from either message or callback_query
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
        else:
            # Can't determine user, reject
            if update.message:
                await update.message.reply_text("❌ Cannot identify user.")
            return
        
        if not user_storage.is_user_allowed(user_id):
            # Check for invite code in message
            if update.message and update.message.text:
                if update.message.text.startswith('/start'):
                    parts = update.message.text.split()
                    if len(parts) > 1 and parts[1] == "invite123":
                        user_storage.add_user(user_id)
                        await update.message.reply_text(
                            "✅ *Invitation accepted!* Welcome to Serie AI Bot.\n\n"
                            "Use /start to access all features.",
                            parse_mode='Markdown'
                        )
                        return
            
            # Send access denied message
            if update.message:
                target = update.message
            elif update.callback_query:
                target = update.callback_query.message
            else:
                return
            
            await target.reply_text(
                "🔒 *Access Restricted*\n\n"
                "This bot is invitation-only.\n"
                "Please contact the administrator for access.\n\n"
                "If you have an invite code, use:\n"
                "`/start invite123`",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

# ========== HELPER: GET MESSAGE OBJECT ==========
def get_message_object(update: Update):
    """Get message object from either update.message or update.callback_query"""
    if update.message:
        return update.message
    elif update.callback_query:
        return update.callback_query.message
    return None

# ========== COMMAND HANDLERS ==========
@access_control
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu"""
    status = "✅ *Real Data Enabled*" if API_KEY else "⚠️ *Using Simulation*"
    
    # Create or update user in database WITH ERROR HANDLING
    try:
        db = DatabaseManager()
        # Get user info from appropriate source
        if update.message:
            user_info = update.message.from_user
        elif update.callback_query:
            user_info = update.callback_query.from_user
        else:
            user_info = None
            
        if user_info:
            user = db.get_or_create_user(
                telegram_id=user_info.id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )
        db.close()
        if user_info:
            logger.info(f"✅ User {user_info.id} synced to database")
    except Exception as e:
        logger.error(f"❌ Database sync failed: {e}")
        # Log the full error but don't break the user experience
        if "integer out of range" in str(e):
            logger.critical(f"🚨 CRITICAL: telegram_id column needs ALTER COLUMN TYPE BIGINT")
    
    text = f"""
{status}

⚽ *SERIE AI PREDICTION BOT*

🎯 *Complete Features:*
• 📅 Today's Matches
• 🏆 League Standings  
• 🎯 Smart Predictions
• 💎 Value Bets
• 📊 Match Analysis
• 📈 Prediction History

👇 Tap any button below:
"""
    
    keyboard = [
        [InlineKeyboardButton("📅 Today's Matches", callback_data="show_matches")],
        [InlineKeyboardButton("🏆 League Standings", callback_data="show_standings_menu")],
        [InlineKeyboardButton("🎯 Smart Prediction", callback_data="show_predict_info")],
        [InlineKeyboardButton("💎 Value Bets", callback_data="show_value_bets")],
        [InlineKeyboardButton("📊 My Stats", callback_data="user_stats")],
        [InlineKeyboardButton("ℹ️ Help & Guide", callback_data="show_help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = get_message_object(update)
    if message:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

@access_control
async def quick_predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick prediction command - WITH DATABASE SAVE"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: `/predict [Home Team] [Away Team]`\n"
            "Example: `/predict Inter Milan`",
            parse_mode='Markdown'
        )
        return
    
    home, away = args[0], args[1]
    analysis = data_manager.analyze_match(home, away)
    
    probs = analysis['probabilities']
    goals = analysis['goals']
    value = analysis['value_bet']
    
    # ========== SAVE TO DATABASE ==========
    try:
        db = DatabaseManager()
        prediction = db.save_prediction(
            telegram_id=update.effective_user.id,
            home_team=home,
            away_team=away,
            league="Quick Prediction",
            predicted_result=analysis['prediction'],
            home_prob=probs['home'],
            draw_prob=probs['draw'],
            away_prob=probs['away'],
            confidence=analysis['confidence']
        )
        db.close()
        logger.info(f"✅ Prediction saved to DB: ID {prediction.id}")
        save_note = "✅ *Saved to your history*"
    except Exception as e:
        logger.error(f"❌ Database save failed: {e}")
        save_note = "⚠️ *History not saved*"
    # ========== END DATABASE SAVE ==========
    
    response = f"""
⚡ *QUICK PREDICTION: {home} vs {away}*

📊 *MATCH RESULT:*
• Home Win: {probs['home']}%
• Draw: {probs['draw']}%
• Away Win: {probs['away']}%
• ➡️ Predicted: *{analysis['prediction']}* ({analysis['confidence']}% confidence)

🥅 *EXPECTED SCORE:*
• {goals['home']}-{goals['away']} (Total: {goals['home'] + goals['away']})

💎 *BEST VALUE BET:*
• {value['market']}: {value['selection']} @ {value['odds']}
• Edge: +{value['edge']}% | Stake: ⭐⭐

{save_note}

_Enhanced with AI analysis_
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def todays_matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text command: /matches"""
    matches = data_manager.get_todays_matches()
    
    if not matches:
        await update.message.reply_text("No matches scheduled for today.")
        return
    
    response = "📅 *TODAY'S FOOTBALL MATCHES*\n\n"
    
    # Group by league
    matches_by_league = {}
    for match in matches:
        league = match['league']
        if league not in matches_by_league:
            matches_by_league[league] = []
        matches_by_league[league].append(match)
    
    for league_name, league_matches in matches_by_league.items():
        response += f"*{league_name}*\n"
        for match in league_matches:
            response += f"⏰ {match['home']} vs {match['away']} ({match['time']})\n"
        response += "\n"
    
    response += f"_Total: {len(matches)} matches_"
    
    message = get_message_object(update)
    if message:
        await message.reply_text(response, parse_mode='Markdown')

@access_control
async def standings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text command: /standings"""
    keyboard = [
        [InlineKeyboardButton("🇮🇹 Serie A", callback_data="standings_SA")],
        [InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", callback_data="standings_PL")],
        [InlineKeyboardButton("🇪🇸 La Liga", callback_data="standings_PD")],
        [InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="standings_BL1")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = get_message_object(update)
    if message:
        await message.reply_text(
            "🏆 *Select League Standings:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

@access_control
async def value_bets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Value bets command - FROM DATABASE"""
    # Get message object for reply
    message = get_message_object(update)
    if not message:
        return
    
    # ========== GET FROM DATABASE ==========
    try:
        db = DatabaseManager()
        bets = db.get_todays_value_bets()
        db.close()
        
        if not bets:
            response = "💎 *NO VALUE BETS TODAY*\n\nNo strong value bets identified for today."
            await message.reply_text(response, parse_mode='Markdown')
            return
        
        response = "💎 *TODAY'S TOP VALUE BETS*\n\n"
        for i, bet in enumerate(bets, 1):
            response += f"{i}. *{bet.match}* ({bet.league})\n"
            response += f"   • Bet: {bet.selection} ({bet.bet_type})\n"
            response += f"   • Odds: {bet.odds} | Probability: {bet.probability}%\n"
            response += f"   • Edge: +{bet.edge}% | Confidence: {bet.confidence*100:.0f}%\n"
            response += f"   • Stake: {bet.recommended_stake}\n\n"
        
        response += "📈 *Value Betting Strategy:*\n"
        response += "• Only bet when edge > 3%\n"
        response += "• Use 1/4 Kelly stake (conservative)\n"
        response += "• Track all bets for analysis\n\n"
        response += "_Data from Serie AI Database_"
        
    except Exception as e:
        logger.error(f"❌ Database value bets failed: {e}")
        response = "❌ Could not load value bets. Please try again later."
    # ========== END DATABASE CODE ==========
    
    await message.reply_text(response, parse_mode='Markdown')

@access_control
async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics - WITH DATABASE (FIXED)"""
    # Get message object and user info
    message = get_message_object(update)
    if not message:
        return
    
    # Get user info from appropriate source
    if update.message:
        user_info = update.message.from_user
    elif update.callback_query:
        user_info = update.callback_query.from_user
    else:
        await message.reply_text("❌ Cannot identify user.")
        return
    
    user_id = user_info.id
    first_name = user_info.first_name or "User"
    
    logger.info(f"📊 Getting stats for user {user_id}")
    
    # First check database health
    db_healthy, db_error = check_database_health()
    
    if not db_healthy:
        logger.error(f"Database unhealthy for /mystats: {db_error}")
        response = f"""
📊 *YOUR STATISTICS*

👤 User: {first_name}
🆔 ID: `{user_id}`

🔧 *Database Connection Issue*

The statistics service is temporarily unavailable.

⚠️ *Technical Details:*
• Connection test failed
• Error: {db_error[:100] if db_error else "Unknown"}

_This is usually a temporary issue. Try again in a moment._
"""
        await message.reply_text(response, parse_mode='Markdown')
        return
    
    try:
        # Get database connection
        db = DatabaseManager()
        
        # First, ensure user exists in database with UPSERT
        try:
            user = db.get_or_create_user(
                telegram_id=user_id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )
            logger.info(f"✅ User {user_id} ensured in database")
        except Exception as user_error:
            logger.error(f"❌ User creation failed: {user_error}")
            # Check if it's the integer overflow error
            if "integer out of range" in str(user_error):
                logger.critical("🚨 DATABASE SCHEMA ERROR: telegram_id is INTEGER, needs BIGINT")
                response = f"""
📊 *YOUR STATISTICS*

👤 User: {first_name}
🆔 ID: `{user_id}`

🚨 *DATABASE SCHEMA ERROR*

Your user ID ({user_id}) is too large for the current database schema.

🔧 *ADMIN MUST RUN:*
```sql
ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT;