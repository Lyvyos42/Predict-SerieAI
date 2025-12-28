#!/usr/bin/env python3
"""Initialize the database with sample data"""
from models import init_db, SessionLocal, ValueBet
from datetime import datetime, timedelta

def create_sample_data():
    """Create sample value bets"""
    db = SessionLocal()
    
    # Sample value bets
    sample_bets = [
        {
            'match': 'Inter vs Milan',
            'league': 'Serie A',
            'bet_type': 'Over/Under',
            'selection': 'Over 2.5 Goals',
            'odds': 2.10,
            'probability': 52.4,
            'edge': 7.3,
            'confidence': 0.85,
            'recommended_stake': '⭐⭐⭐'
        },
        {
            'match': 'Barcelona vs Real Madrid',
            'league': 'La Liga',
            'bet_type': 'BTTS',
            'selection': 'Yes',
            'odds': 1.75,
            'probability': 68.2,
            'edge': 5.8,
            'confidence': 0.78,
            'recommended_stake': '⭐⭐'
        }
    ]
    
    for bet_data in sample_bets:
        expires_at = datetime.utcnow() + timedelta(days=1)
        bet = ValueBet(
            **bet_data,
            is_active=True,
            expires_at=expires_at
        )
        db.add(bet)
    
    db.commit()
    db.close()
    print("✅ Sample data created")

if __name__ == "__main__":
    init_db()
    create_sample_data()