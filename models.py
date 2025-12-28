from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set in Railway Variables!")
    exit(1)

# Fix Railway PostgreSQL URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """User table"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_subscribed = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    subscription_ends = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="user")
    bets = relationship("Bet", back_populates="user")

class Prediction(Base):
    """Prediction history"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    home_team = Column(String(100))
    away_team = Column(String(100))
    league = Column(String(50))
    predicted_result = Column(String(1))  # 1, X, 2
    actual_result = Column(String(1), nullable=True)
    home_prob = Column(Float)
    draw_prob = Column(Float)
    away_prob = Column(Float)
    confidence = Column(Float)
    is_correct = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="predictions")

class Bet(Base):
    """Bet tracking"""
    __tablename__ = "bets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    match = Column(String(200))
    bet_type = Column(String(50))  # "1X2", "Over/Under", "BTTS"
    selection = Column(String(50))
    odds = Column(Float)
    stake = Column(Float)
    result = Column(String(10), nullable=True)  # "win", "loss", "void"
    profit_loss = Column(Float, nullable=True)
    placed_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="bets")

class ValueBet(Base):
    """Value bet recommendations"""
    __tablename__ = "value_bets"
    
    id = Column(Integer, primary_key=True, index=True)
    match = Column(String(200))
    league = Column(String(50))
    bet_type = Column(String(50))
    selection = Column(String(50))
    odds = Column(Float)
    probability = Column(Float)
    edge = Column(Float)  # Expected value %
    confidence = Column(Float)
    recommended_stake = Column(String(20))  # "⭐", "⭐⭐", "⭐⭐⭐"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

class SystemLog(Base):
    """System logs"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20))  # "INFO", "WARNING", "ERROR"
    message = Column(Text)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Database error: {e}")

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()