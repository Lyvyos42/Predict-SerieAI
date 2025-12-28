from models import SessionLocal, User, Prediction, Bet, ValueBet, SystemLog
from datetime import datetime, timedelta
from sqlalchemy import desc, func, text
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations with error handling"""
    
    def __init__(self):
        self.db = None
        try:
            self.db = SessionLocal()
            # Test connection
            self.db.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def get_or_create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Get user or create if doesn't exist"""
        try:
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
                logger.info(f"✅ Created new user: {telegram_id}")
            else:
                user.last_seen = datetime.utcnow()
                user.username = username or user.username
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                self.db.commit()
            
            return user
        except Exception as e:
            logger.error(f"❌ get_or_create_user failed: {e}")
            self.db.rollback()
            raise
    
    def save_prediction(self, telegram_id: int, home_team: str, away_team: str, league: str,
                       predicted_result: str, home_prob: float, draw_prob: float, 
                       away_prob: float, confidence: float):
        """Save user prediction"""
        try:
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
            logger.info(f"✅ Prediction saved for user {telegram_id}")
            return prediction
        except Exception as e:
            logger.error(f"❌ save_prediction failed: {e}")
            self.db.rollback()
            raise
    
    def get_user_stats(self, telegram_id: int):
        """Get user prediction statistics"""
        try:
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
            
            logger.info(f"✅ Stats retrieved for user {telegram_id}: {total} predictions")
            
            return {
                'total_predictions': total,
                'correct_predictions': correct,
                'accuracy': round(accuracy, 1),
                'recent_predictions': recent,
                'user': user
            }
        except Exception as e:
            logger.error(f"❌ get_user_stats failed: {e}")
            return {
                'total_predictions': 0,
                'correct_predictions': 0,
                'accuracy': 0,
                'recent_predictions': [],
                'user': None
            }
    
    def get_todays_value_bets(self):
        """Get today's value bets"""
        try:
            today = datetime.utcnow()
            tomorrow = today + timedelta(days=1)
            
            bets = self.db.query(ValueBet).filter(
                ValueBet.is_active == True,
                ValueBet.expires_at > today,
                ValueBet.expires_at < tomorrow
            ).order_by(desc(ValueBet.edge)).limit(10).all()
            
            logger.info(f"✅ Retrieved {len(bets)} value bets")
            return bets
        except Exception as e:
            logger.error(f"❌ get_todays_value_bets failed: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()