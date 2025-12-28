from models import SessionLocal, User, Prediction, Bet, ValueBet, SystemLog
from datetime import datetime, timedelta
from sqlalchemy import desc, func

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def get_or_create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Get user or create if doesn't exist"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                last_seen=datetime.utcnow()
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            print(f"✅ Created new user: {telegram_id}")
        else:
            user.last_seen = datetime.utcnow()
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            self.db.commit()
        
        return user
    
    def save_prediction(self, telegram_id: int, home_team: str, away_team: str, league: str,
                       predicted_result: str, home_prob: float, draw_prob: float, 
                       away_prob: float, confidence: float):
        """Save user prediction"""
        user = self.get_or_create_user(telegram_id)
        
        prediction = Prediction(
            user_id=user.id,
            home_team=home_team,
            away_team=away_team,
            league=league,
            predicted_result=predicted_result,
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            confidence=confidence
        )
        
        self.db.add(prediction)
        self.db.commit()
        return prediction
    
    def update_prediction_result(self, prediction_id: int, actual_result: str):
        """Update prediction with actual result"""
        prediction = self.db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if prediction:
            prediction.actual_result = actual_result
            prediction.is_correct = (prediction.predicted_result == actual_result)
            self.db.commit()
    
    def get_user_stats(self, telegram_id: int):
        """Get user prediction statistics"""
        user = self.get_or_create_user(telegram_id)
        
        # Total predictions
        total = self.db.query(Prediction).filter(Prediction.user_id == user.id).count()
        
        # Correct predictions
        correct = self.db.query(Prediction).filter(
            Prediction.user_id == user.id,
            Prediction.is_correct == True
        ).count()
        
        # Recent predictions
        recent = self.db.query(Prediction).filter(
            Prediction.user_id == user.id
        ).order_by(desc(Prediction.created_at)).limit(5).all()
        
        # Calculate accuracy
        accuracy = (correct / total * 100) if total > 0 else 0
        
        return {
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy': round(accuracy, 1),
            'recent_predictions': recent,
            'user': user
        }
    
    def get_todays_value_bets(self):
        """Get today's value bets"""
        today = datetime.utcnow()
        tomorrow = today + timedelta(days=1)
        
        bets = self.db.query(ValueBet).filter(
            ValueBet.is_active == True,
            ValueBet.expires_at > today,
            ValueBet.expires_at < tomorrow
        ).order_by(desc(ValueBet.edge)).limit(10).all()
        
        return bets
    
    def add_value_bet(self, match: str, league: str, bet_type: str, selection: str,
                     odds: float, probability: float, edge: float, confidence: float,
                     recommended_stake: str):
        """Add new value bet"""
        expires_at = datetime.utcnow() + timedelta(days=1)
        
        bet = ValueBet(
            match=match,
            league=league,
            bet_type=bet_type,
            selection=selection,
            odds=odds,
            probability=probability,
            edge=edge,
            confidence=confidence,
            recommended_stake=recommended_stake,
            expires_at=expires_at
        )
        
        self.db.add(bet)
        self.db.commit()
        return bet
    
    def log_system_event(self, level: str, message: str, user_id: int = None):
        """Log system event"""
        log = SystemLog(
            level=level,
            message=message,
            user_id=user_id
        )
        self.db.add(log)
        self.db.commit()
    
    def close(self):
        """Close database connection"""
        self.db.close()