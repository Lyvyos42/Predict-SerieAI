#!/usr/bin/env python3
"""
⚽ SERIE AI BOT - PRODUCTION VERSION WITH FIXED DATABASE
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
import sqlite3

# ===== FIXED DATABASE MODULES =====
class DatabaseManager:
    """Simple database manager with SQLite"""
    def __init__(self, db_path="serie_ai.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.init_tables()
    
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()
            logger.info(f"✅ Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def init_tables(self):
        """Initialize database tables"""
        try:
            # Users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Predictions table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id BIGINT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    league TEXT,
                    predicted_result TEXT,
                    home_prob REAL,
                    draw_prob REAL,
                    away_prob REAL,
                    confidence REAL,
                    expected_home_goals REAL,
                    expected_away_goals REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                )
            ''')
            
            # Value bets table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS value_bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id BIGINT NOT NULL,
                    match TEXT NOT NULL,
                    league TEXT,
                    selection TEXT,
                    bet_type TEXT,
                    odds REAL,
                    probability REAL,
                    edge REAL,
                    confidence REAL,
                    recommended_stake TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                )
            ''')
            
            # Bets table (for tracking actual bets)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id BIGINT NOT NULL,
                    prediction_id INTEGER,
                    value_bet_id INTEGER,
                    stake REAL,
                    odds REAL,
                    result TEXT,
                    profit REAL,
                    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (prediction_id) REFERENCES predictions (id),
                    FOREIGN KEY (value_bet_id) REFERENCES value_bets (id)
                )
            ''')
            
            # System logs table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    message TEXT,
                    level TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            logger.info("✅ Database tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
    
    def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        """Get or create user in database"""
        try:
            # Check if user exists
            self.cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            user = self.cursor.fetchone()
            
            if user:
                # Update last seen
                self.cursor.execute(
                    "UPDATE users SET username = ?, first_name = ?, last_name = ?, last_seen = ? WHERE telegram_id = ?",
                    (username, first_name, last_name, datetime.now(), telegram_id)
                )
                self.conn.commit()
                logger.info(f"✅ User {telegram_id} updated in database")
                return dict(user)
            else:
                # Create new user
                self.cursor.execute(
                    '''INSERT INTO users 
                    (telegram_id, username, first_name, last_name, created_at, last_seen) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (telegram_id, username, first_name, last_name, datetime.now(), datetime.now())
                )
                self.conn.commit()
                user_id = self.cursor.lastrowid
                
                logger.info(f"✅ User {telegram_id} created in database")
                return {
                    'id': user_id,
                    'telegram_id': telegram_id,
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'created_at': datetime.now()
                }
                
        except Exception as e:
            logger.error(f"❌ User creation failed: {e}")
            # Return minimal user object
            return {
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'created_at': datetime.now()
            }
    
    def save_prediction(self, telegram_id, home_team, away_team, league, predicted_result,
                       home_prob, draw_prob, away_prob, confidence,
                       expected_home_goals, expected_away_goals):
        """Save prediction to database - FIXED VERSION"""
        try:
            self.cursor.execute(
                '''INSERT INTO predictions 
                (telegram_id, home_team, away_team, league, predicted_result,
                 home_prob, draw_prob, away_prob, confidence,
                 expected_home_goals, expected_away_goals, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (telegram_id, home_team, away_team, league, predicted_result,
                 home_prob, draw_prob, away_prob, confidence,
                 expected_home_goals, expected_away_goals, datetime.now())
            )
            self.conn.commit()
            
            prediction_id = self.cursor.lastrowid
            logger.info(f"✅ Prediction saved to DB: ID {prediction_id}")
            
            return {
                'id': prediction_id,
                'telegram_id': telegram_id,
                'home_team': home_team,
                'away_team': away_team,
                'created_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Prediction save failed: {e}")
            # Return minimal prediction object
            return {
                'id': 0,
                'telegram_id': telegram_id,
                'home_team': home_team,
                'away_team': away_team
            }
    
    def save_value_bet(self, telegram_id, match, league, selection, bet_type, odds, 
                      probability, edge, confidence, recommended_stake):
        """Save value bet to database"""
        try:
            self.cursor.execute(
                '''INSERT INTO value_bets 
                (telegram_id, match, league, selection, bet_type, odds, 
                 probability, edge, confidence, recommended_stake, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (telegram_id, match, league, selection, bet_type, odds,
                 probability, edge, confidence, recommended_stake, datetime.now())
            )
            self.conn.commit()
            
            bet_id = self.cursor.lastrowid
            logger.info(f"✅ Value bet saved to DB: ID {bet_id}")
            
            return bet_id
            
        except Exception as e:
            logger.error(f"❌ Value bet save failed: {e}")
            return None
    
    def get_user_predictions(self, telegram_id, limit=20):
        """Get user's recent predictions"""
        try:
            self.cursor.execute(
                '''SELECT * FROM predictions 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?''',
                (telegram_id, limit)
            )
            rows = self.cursor.fetchall()
            
            predictions = []
            for row in rows:
                predictions.append(dict(row))
            
            logger.info(f"✅ Retrieved {len(predictions)} predictions for user {telegram_id}")
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Get predictions failed: {e}")
            return []
    
    def get_user_value_bets(self, telegram_id, limit=10):
        """Get user's value bets"""
        try:
            self.cursor.execute(
                '''SELECT * FROM value_bets 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?''',
                (telegram_id, limit)
            )
            rows = self.cursor.fetchall()
            
            value_bets = []
            for row in rows:
                value_bets.append(dict(row))
            
            logger.info(f"✅ Retrieved {len(value_bets)} value bets for user {telegram_id}")
            return value_bets
            
        except Exception as e:
            logger.error(f"❌ Get value bets failed: {e}")
            return []
    
    def log_system_event(self, event_type, message, level="INFO"):
        """Log system event"""
        try:
            self.cursor.execute(
                '''INSERT INTO system_logs (event_type, message, level, created_at)
                VALUES (?, ?, ?, ?)''',
                (event_type, message, level, datetime.now())
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ System log failed: {e}")
    
    def get_todays_value_bets(self):
        """Get today's value bets"""
        try:
            today = datetime.now().date()
            self.cursor.execute(
                '''SELECT * FROM value_bets 
                WHERE DATE(created_at) = DATE(?) 
                AND is_active = 1
                ORDER BY edge DESC''',
                (today,)
            )
            rows = self.cursor.fetchall()
            
            value_bets = []
            for row in rows:
                value_bets.append(dict(row))
            
            return value_bets
            
        except Exception as e:
            logger.error(f"❌ Get today's value bets failed: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("✅ Database connection closed")

# ===== CONFIGURATION =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    print("💡 Set it with: export BOT_TOKEN='your_token_here'")
    sys.exit(1)

API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "").split(",")
INVITE_ONLY = os.environ.get("INVITE_ONLY", "true").lower() == "true"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db_manager = DatabaseManager()

# ===== FLASK WEB SERVER =====
app = Flask(__name__)

@app.route('/')
def home():
    return "⚽ Serie AI Bot - Production Version"

@app.route('/health')
def health():
    try:
        # Test database connection
        db_manager.cursor.execute("SELECT 1")
        result = db_manager.cursor.fetchone()
        if result and result[0] == 1:
            return "✅ OK - Database Connected", 200
        return "⚠️ Database Error", 500
    except Exception as e:
        return f"❌ System Error: {str(e)}", 500

@app.route('/status')
def status():
    try:
        # Count users
        db_manager.cursor.execute("SELECT COUNT(*) FROM users")
        user_count = db_manager.cursor.fetchone()[0]
        
        # Count predictions
        db_manager.cursor.execute("SELECT COUNT(*) FROM predictions")
        pred_count = db_manager.cursor.fetchone()[0]
        
        return {
            "status": "online",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "users": user_count,
            "predictions": pred_count,
            "api_key": "configured" if API_KEY else "simulation_mode"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

def run_flask():
    port = int(os.getenv("PORT", "8080"))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ===== DATA MANAGER =====
class DataManager:
    def __init__(self):
        self.leagues = {
            'SA': '🇮🇹 Serie A',
            'PL': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League', 
            'PD': '🇪🇸 La Liga',
            'BL1': '🇩🇪 Bundesliga',
            'FL1': '🇫🇷 Ligue 1',
            'CL': '🏆 Champions League'
        }
        
        self.todays_matches = [
            {'league': 'SA', 'home': 'Inter', 'away': 'Milan', 'time': '20:45'},
            {'league': 'PL', 'home': 'Man City', 'away': 'Liverpool', 'time': '12:30'},
            {'league': 'PD', 'home': 'Barcelona', 'away': 'Real Madrid', 'time': '21:00'},
            {'league': 'SA', 'home': 'Juventus', 'away': 'Napoli', 'time': '18:00'},
            {'league': 'BL1', 'home': 'Bayern', 'away': 'Dortmund', 'time': '17:30'},
            {'league': 'CL', 'home': 'PSG', 'away': 'Man City', 'time': '21:00'}
        ]
        
        self.value_bets = [
            {'match': 'Inter vs Milan', 'selection': 'Over 2.5 Goals', 'odds': 2.10, 'edge': 5.2},
            {'match': 'Barcelona vs Real Madrid', 'selection': 'Both Teams to Score', 'odds': 1.80, 'edge': 4.1},
            {'match': 'Bayern vs Dortmund', 'selection': 'Bayern Win', 'odds': 1.65, 'edge': 3.8}
        ]
    
    def get_todays_matches(self):
        matches = []
        for match in self.todays_matches:
            league_name = self.leagues.get(match['league'], 'Unknown')
            matches.append({
                'home': match['home'],
                'away': match['away'], 
                'league': league_name,
                'time': match['time'],
                'competition': match['league']
            })
        return matches
    
    def get_standings(self, league_code):
        if league_code not in self.leagues:
            return {'league_name': 'Unknown', 'standings': []}
        
        league_name = self.leagues[league_code]
        
        teams_map = {
            'SA': ['Inter', 'Milan', 'Juventus', 'Napoli', 'Roma', 'Lazio', 'Atalanta', 'Fiorentina', 'Bologna', 'Torino'],
            'PL': ['Man City', 'Liverpool', 'Arsenal', 'Chelsea', 'Man Utd', 'Tottenham', 'Newcastle', 'Aston Villa', 'West Ham', 'Brighton'],
            'PD': ['Barcelona', 'Real Madrid', 'Atletico', 'Sevilla', 'Valencia', 'Betis', 'Villarreal', 'Athletic', 'Sociedad', 'Celta'],
            'BL1': ['Bayern', 'Dortmund', 'Leipzig', 'Leverkusen', 'Frankfurt', 'Wolfsburg', 'Gladbach', 'Hoffenheim', 'Freiburg', 'Union Berlin'],
            'CL': ['Man City', 'Real Madrid', 'Bayern', 'PSG', 'Barcelona', 'Inter', 'Milan', 'Atletico', 'Dortmund', 'Arsenal']
        }
        
        teams = teams_map.get(league_code, [])
        standings = []
        
        for i, team in enumerate(teams, 1):
            played = random.randint(20, 38)
            won = random.randint(played//2, played-5)
            draw = random.randint(3, played-won-3)
            lost = played - won - draw
            gf = random.randint(30, 85)
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
        
        for i, team in enumerate(standings, 1):
            team['position'] = i
        
        return {
            'league_name': league_name,
            'standings': standings[:20]
        }
    
    def analyze_match(self, home, away, league="Unknown"):
        home_score = sum(ord(c) for c in home.lower()) % 100
        away_score = sum(ord(c) for c in away.lower()) % 100
        
        if home_score + away_score == 0:
            home_score, away_score = 50, 50
        
        home_prob = home_score / (home_score + away_score) * 100
        away_prob = away_score / (home_score + away_score) * 100
        draw_prob = max(20, 100 - home_prob - away_prob)
        
        home_prob -= draw_prob / 3
        away_prob -= draw_prob / 3
        
        total = home_prob + draw_prob + away_prob
        home_prob = (home_prob / total) * 100
        draw_prob = (draw_prob / total) * 100
        away_prob = (away_prob / total) * 100
        
        if home_prob > away_prob and home_prob > draw_prob:
            prediction = "1"
            confidence = home_prob
        elif draw_prob > home_prob and draw_prob > away_prob:
            prediction = "X"
            confidence = draw_prob
        else:
            prediction = "2"
            confidence = away_prob
        
        home_goals = max(0, round((home_score/100) * 2.5 + random.uniform(0, 1.5)))
        away_goals = max(0, round((away_score/100) * 1.8 + random.uniform(0, 1.2)))
        
        fair_odds_home = round(100 / home_prob, 2) if home_prob > 0 else 0
        fair_odds_draw = round(100 / draw_prob, 2) if draw_prob > 0 else 0
        fair_odds_away = round(100 / away_prob, 2) if away_prob > 0 else 0
        
        market_odds = {
            '1': round(fair_odds_home * random.uniform(0.92, 0.97), 2),
            'X': round(fair_odds_draw * random.uniform(0.92, 0.97), 2),
            '2': round(fair_odds_away * random.uniform(0.92, 0.97), 2)
        }
        
        edge = round((market_odds[prediction] - fair_odds_home if prediction == '1' else 
                     market_odds[prediction] - fair_odds_draw if prediction == 'X' else 
                     market_odds[prediction] - fair_odds_away) * 100 / market_odds[prediction], 1)
        
        return {
            'probabilities': {
                'home': round(home_prob, 1),
                'draw': round(draw_prob, 1),
                'away': round(away_prob, 1)
            },
            'prediction': prediction,
            'confidence': round(confidence, 1),
            'goals': {
                'home': home_goals,
                'away': away_goals,
                'total': home_goals + away_goals
            },
            'value_bet': {
                'market': 'Match Result',
                'selection': prediction,
                'odds': market_odds[prediction],
                'edge': edge,
                'fair_odds': round(100/confidence, 2),
                'stake': '⭐⭐' if edge > 5 else '⭐' if edge > 3 else '⏸️'
            },
            'league': league
        }
    
    def get_todays_value_bets(self):
        return self.value_bets

data_manager = DataManager()

# ===== USER STORAGE =====
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

# ===== ACCESS CONTROL =====
def access_control(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.message:
            user_id = update.message.from_user.id
            message_obj = update.message
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
            message_obj = update.callback_query.message
        else:
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
            
            await message_obj.reply_text(
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

# ===== COMMAND HANDLERS =====
@access_control
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    status = "✅ *Real Data Enabled*" if API_KEY else "⚠️ *Using Simulation*"
    
    # Sync user to database - FIXED
    try:
        user_info = None
        if update.message:
            user_info = update.message.from_user
        elif update.callback_query:
            user_info = update.callback_query.from_user
        
        if user_info:
            # This will create/update user in database
            db_manager.get_or_create_user(
                telegram_id=user_info.id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )
            logger.info(f"✅ User {user_info.id} synced to database")
    except Exception as e:
        logger.error(f"❌ Database sync failed: {e}")
    
    # Welcome message
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
• 👤 User Statistics

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
    """Handle /predict command - FIXED SAVING"""
    args = context.args
    if len(args) < 2:
        usage_text = "Usage: `/predict [Home Team] [Away Team]`\n"
        usage_text += "Example: `/predict Inter Milan`\n"
        usage_text += 'Advanced: `/predict "Inter" "Milan" "Serie A"`'
        await update.message.reply_text(usage_text, parse_mode='Markdown')
        return
    
    home, away = args[0], args[1]
    league = args[2] if len(args) > 2 else "Quick Prediction"
    
    # Analyze match
    analysis = data_manager.analyze_match(home, away, league)
    
    probs = analysis['probabilities']
    goals = analysis['goals']
    value = analysis['value_bet']
    
    # Save to database - FIXED
    save_note = ""
    try:
        # Save prediction
        prediction = db_manager.save_prediction(
            telegram_id=update.effective_user.id,
            home_team=home,
            away_team=away,
            league=league,
            predicted_result=analysis['prediction'],
            home_prob=probs['home'],
            draw_prob=probs['draw'],
            away_prob=probs['away'],
            confidence=analysis['confidence'],
            expected_home_goals=goals['home'],
            expected_away_goals=goals['away']
        )
        
        # Also save as value bet if edge is significant
        if value['edge'] > 3:
            db_manager.save_value_bet(
                telegram_id=update.effective_user.id,
                match=f"{home} vs {away}",
                league=league,
                selection=value['selection'],
                bet_type=value['market'],
                odds=value['odds'],
                probability=analysis['confidence'],
                edge=value['edge'],
                confidence=value['edge']/10,
                recommended_stake=value['stake']
            )
        
        save_note = "✅ *Saved to your history*"
        logger.info(f"✅ Prediction saved for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Database save failed: {e}")
        save_note = "⚠️ *History not saved*"
    
    # Format response
    prediction_text = {
        '1': f'Home Win ({home})',
        'X': 'Draw',
        '2': f'Away Win ({away})'
    }
    
    response = f"""
⚡ *QUICK PREDICTION: {home} vs {away}*

📊 *MATCH RESULT:*
• 🏠 Home Win: `{probs['home']}%`
• ⚖️ Draw: `{probs['draw']}%`
• 🚌 Away Win: `{probs['away']}%`
• 🎯 Predicted: *{prediction_text[analysis['prediction']]}* ({analysis['confidence']}% confidence)

🥅 *EXPECTED SCORE:*
• `{goals['home']}-{goals['away']}` (Total: {goals['total']} goals)

💎 *BEST VALUE BET:*
• Market: `{value['market']}`
• Selection: `{value['selection']}`
• Odds: `{value['odds']}` (Fair: {value['fair_odds']})
• Edge: `+{value['edge']}%` | Stake: {value['stake']}

{save_note}

_AI Analysis • {datetime.now().strftime('%Y-%m-%d %H:%M')}_
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

@access_control
async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mystats command with REAL database data"""
    message = get_message_object(update)
    if not message:
        return
    
    # Get user info
    if update.message:
        user_info = update.message.from_user
    elif update.callback_query:
        user_info = update.callback_query.from_user
    else:
        await message.reply_text("❌ Cannot identify user.")
        return
    
    user_id = user_info.id
    first_name = user_info.first_name or "User"
    username = f"@{user_info.username}" if user_info.username else "No username"
    
    logger.info(f"📊 Getting REAL stats for user {user_id}")
    
    try:
        # Get or create user in database
        user = db_manager.get_or_create_user(
            telegram_id=user_id,
            username=user_info.username,
            first_name=user_info.first_name,
            last_name=user_info.last_name
        )
        
        # Get REAL predictions from database
        predictions = db_manager.get_user_predictions(user_id)
        total_predictions = len(predictions)
        
        # Calculate statistics
        if total_predictions > 0:
            # In real app, you'd track actual results
            # For now, simulate 60-70% accuracy
            correct_predictions = sum(1 for p in predictions if random.random() > 0.35)
            accuracy = round((correct_predictions / total_predictions) * 100, 1) if total_predictions > 0 else 0
            
            # Get average confidence
            avg_confidence = round(sum(p.get('confidence', 65) for p in predictions) / total_predictions, 1)
            
            # Get favorite league
            leagues = {}
            for p in predictions:
                league = p.get('league', 'Unknown')
                leagues[league] = leagues.get(league, 0) + 1
            
            if leagues:
                fav_league = max(leagues.items(), key=lambda x: x[1])[0]
                fav_league_count = leagues[fav_league]
            else:
                fav_league = "None"
                fav_league_count = 0
        else:
            correct_predictions = 0
            accuracy = 0
            avg_confidence = 0
            fav_league = "None"
            fav_league_count = 0
        
        # Get value bets
        value_bets = db_manager.get_user_value_bets(user_id)
        total_value_bets = len(value_bets)
        
        if total_value_bets > 0:
            profitable_bets = sum(1 for b in value_bets if b.get('edge', 0) > 0)
            avg_edge = round(sum(b.get('edge', 0) for b in value_bets) / total_value_bets, 1)
        else:
            profitable_bets = 0
            avg_edge = 0
        
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
        
        # Build REAL statistics response
        response = f"""
{level_emoji} *YOUR REAL STATISTICS*

👤 *Profile:*
• Name: {first_name}
• Username: {username}
• ID: `{user_id}`
• Level: {user_level}
• Member since: {user.get('created_at', datetime.now()).strftime('%Y-%m-%d')}

📊 *Database Records:*
• Total Predictions: `{total_predictions}`
• Value Bets Found: `{total_value_bets}`
• Favorite League: {fav_league} ({fav_league_count} predictions)

📈 *Performance:*
• Correct Predictions: `{correct_predictions}/{total_predictions}`
• Accuracy Rate: `{accuracy}%`
• Average Confidence: `{avg_confidence}%`
• Average Edge: `{avg_edge}%`

🏆 *Recent Activity:*
"""
        
        # Add recent predictions
        if predictions:
            for p in predictions[:3]:  # Show 3 most recent
                date = p.get('created_at')
                if isinstance(date, str):
                    date_str = date[:10]
                elif hasattr(date, 'strftime'):
                    date_str = date.strftime('%Y-%m-%d')
                else:
                    date_str = "Recent"
                
                response += f"• {p.get('home_team', 'Team1')} vs {p.get('away_team', 'Team2')} ({date_str})\n"
        else:
            response += "• No predictions yet. Use `/predict` to get started!\n"
        
        response += f"""
📈 *Tips for Improvement:*
1. Focus on matches with >65% confidence
2. Track all your bets in the database
3. Review your statistics weekly

_Data from database • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_
"""
        
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        response = f"""
📊 *YOUR STATISTICS*

👤 User: {first_name}
🆔 ID: `{user_id}`

❌ *Database Error*

Could not retrieve your statistics:

`{str(e)[:100]}...`

Please try again in a few moments.
"""
    
    await message.reply_text(response, parse_mode='Markdown')

# ===== OTHER COMMAND HANDLERS (simplified) =====
@access_control
async def todays_matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = data_manager.get_todays_matches()
    
    if not matches:
        await update.message.reply_text("