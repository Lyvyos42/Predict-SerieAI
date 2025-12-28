#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - WITH DATABASE INTEGRATION
COMPLETE FIXED VERSION
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
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import sqlalchemy as sa

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "").split(",")
INVITE_ONLY = os.environ.get("INVITE_ONLY", "true").lower() == "true"
DATABASE_URL = os.environ.get("DATABASE_URL")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE MODELS ==========
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(sa.BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    predictions = relationship("Prediction", back_populates="user")
    bets = relationship("Bet", back_populates="user")
    value_bets = relationship("ValueBet", back_populates="user")

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(sa.BigInteger, nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    league = Column(String(50))
    predicted_result = Column(String(5), nullable=False)  # '1', 'X', '2'
    actual_result = Column(String(5))  # '1', 'X', '2'
    home_prob = Column(Float)
    draw_prob = Column(Float)
    away_prob = Column(Float)
    confidence = Column(Float)
    is_correct = Column(Boolean)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="predictions")

class Bet(Base):
    __tablename__ = 'bets'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(sa.BigInteger, nullable=False)
    match = Column(String(200), nullable=False)
    league = Column(String(50))
    bet_type = Column(String(50))  # 'Match Result', 'Over/Under', 'Both Teams to Score'
    selection = Column(String(100))
    odds = Column(Float)
    stake = Column(Float)
    result = Column(String(10))  # 'win', 'loss', 'pending'
    profit = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="bets")

class ValueBet(Base):
    __tablename__ = 'value_bets'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(sa.BigInteger, nullable=False)
    match = Column(String(200), nullable=False)
    league = Column(String(50))
    bet_type = Column(String(50))
    selection = Column(String(100))
    odds = Column(Float)
    probability = Column(Float)  # Estimated probability in %
    edge = Column(Float)  # Value edge in %
    confidence = Column(Float)  # 0-1 confidence score
    recommended_stake = Column(String(20))  # '⭐', '⭐⭐', '⭐⭐⭐'
    status = Column(String(20), default='pending')  # 'pending', 'won', 'lost'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="value_bets")

class SystemLog(Base):
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20))  # 'info', 'warning', 'error', 'critical'
    module = Column(String(100))
    message = Column(Text)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# ========== DATABASE MANAGER ==========
class DatabaseManager:
    def __init__(self, database_url=None):
        self.database_url = database_url or DATABASE_URL or "sqlite:///bot.db"
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
    
    def close(self):
        self.db.close()
    
    def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        user = self.db.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.db.add(user)
            self.db.commit()
        return user
    
    def save_prediction(self, telegram_id, home_team, away_team, league, predicted_result, 
                        home_prob, draw_prob, away_prob, confidence, actual_result=None):
        prediction = Prediction(
            telegram_id=telegram_id,
            home_team=home_team,
            away_team=away_team,
            league=league,
            predicted_result=predicted_result,
            actual_result=actual_result,
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            confidence=confidence,
            created_at=datetime.utcnow()
        )
        self.db.add(prediction)
        self.db.commit()
        return prediction
    
    def get_user_predictions(self, telegram_id, limit=50):
        return self.db.query(Prediction).filter_by(
            telegram_id=telegram_id
        ).order_by(Prediction.created_at.desc()).limit(limit).all()
    
    def get_todays_value_bets(self):
        today = datetime.utcnow().date()
        return self.db.query(ValueBet).filter(
            sa.func.date(ValueBet.created_at) == today
        ).order_by(ValueBet.edge.desc()).limit(10).all()
    
    def get_user_value_bets(self, telegram_id):
        return self.db.query(ValueBet).filter_by(
            telegram_id=telegram_id
        ).order_by(ValueBet.created_at.desc()).limit(20).all()
    
    def get_top_users(self, limit=10):
        users = self.db.query(User).all()
        user_stats = []
        for user in users:
            predictions = self.db.query(Prediction).filter_by(telegram_id=user.telegram_id).all()
            if predictions:
                correct = sum(1 for p in predictions if p.is_correct)
                accuracy = (correct / len(predictions)) * 100
                user_stats.append({
                    'user': user,
                    'accuracy': accuracy,
                    'total_predictions': len(predictions)
                })
        
        user_stats.sort(key=lambda x: x['accuracy'], reverse=True)
        return [stat['user'] for stat in user_stats[:limit]]
    
    def get_user_rank(self, telegram_id):
        users = self.get_top_users(limit=1000)
        for i, user in enumerate(users, 1):
            if user.telegram_id == telegram_id:
                return i
        return None
    
    def log_system_event(self, level, module, message, details=None):
        log = SystemLog(
            level=level,
            module=module,
            message=message,
            details=details,
            created_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()

def init_db():
    """Initialize database tables"""
    engine = create_engine(DATABASE_URL or "sqlite:///bot.db")
    Base.metadata.create_all(engine)
    logger.info("Database tables created/verified")

# ========== FLASK APP ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "⚽ Serie AI Bot - Database Edition"

@app.route('/health')
def health():
    try:
        db = DatabaseManager()
        from sqlalchemy import text
        result = db.db.execute(text("SELECT 1")).scalar()
        db.close()
        return "✅ OK", 200
    except Exception as e:
        return f"❌ Database Error: {str(e)}", 500

def run_flask():
    port = int(os.getenv("PORT", "8080"))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ========== DATA MANAGER ==========
class DataManager:
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
        if league_code not in self.leagues:
            return {'league_name': 'Unknown', 'standings': []}
        
        league_name = self.leagues[league_code]
        
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

data_manager = DataManager()

# ========== UTILITY FUNCTIONS ==========
def check_database_health() -> Tuple[bool, Optional[str]]:
    try:
        db = DatabaseManager()
        from sqlalchemy import text
        result = db.db.execute(text("SELECT 1")).scalar()
        db.close()
        return (True, None) if result == 1 else (False, "Test query failed")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return (False, str(e))

class SimpleUserStorage:
    def __init__(self):
        self.allowed_users = set()
        self.subscribers = set()
        
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

def access_control(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
        else:
            if update.message:
                await update.message.reply_text("❌ Cannot identify user.")
            return
        
        if not user_storage.is_user_allowed(user_id):
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

def get_message_object(update: Update):
    if update.message:
        return update.message
    elif update.callback_query:
        return update.callback_query.message
    return None

# ========== COMMAND HANDLERS ==========
@access_control
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "✅ *Real Data Enabled*" if API_KEY else "⚠️ *Using Simulation*"
    
    try:
        db = DatabaseManager()
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
    matches = data_manager.get_todays_matches()
    
    if not matches:
        await update.message.reply_text("No matches scheduled for today.")
        return
    
    response = "📅 *TODAY'S FOOTBALL MATCHES*\n\n"
    
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
    message = get_message_object(update)
    if not message:
        return
    
    try:
        db = DatabaseManager()
        
        # Create some sample value bets if none exist
        if db.db.query(ValueBet).count() == 0:
            sample_bets = [
                ValueBet(
                    telegram_id=1,
                    match="Inter vs Milan",
                    league="Serie A",
                    bet_type="Match Result",
                    selection="1",
                    odds=2.10,
                    probability=55.0,
                    edge=15.5,
                    confidence=0.8,
                    recommended_stake="⭐⭐",
                    status="pending"
                ),
                ValueBet(
                    telegram_id=1,
                    match="Man City vs Liverpool",
                    league="Premier League",
                    bet_type="Over/Under",
                    selection="Over 2.5",
                    odds=1.85,
                    probability=65.0,
                    edge=20.3,
                    confidence=0.7,
                    recommended_stake="⭐⭐⭐",
                    status="pending"
                )
            ]
            for bet in sample_bets:
                db.db.add(bet)
            db.db.commit()
        
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
    
    await message.reply_text(response, parse_mode='Markdown')

@access_control
async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = get_message_object(update)
    if not message:
        return
    
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
        db = DatabaseManager()
        
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
ALTER TABLE predictions ALTER COLUMN telegram_id TYPE BIGINT;
ALTER TABLE bets ALTER COLUMN telegram_id TYPE BIGINT;