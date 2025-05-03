#!/usr/bin/env python3
"""
Initialize database with basic data.
"""

from app.database.connection import SessionLocal
from app.database.models import Currency, ImpactLevel
from app.config import config

def init_currencies():
    """Initialize currencies table."""
    db = SessionLocal()
    try:
        existing_currencies = {c.code for c in db.query(Currency).all()}
        
        for currency_code in config.AVAILABLE_CURRENCIES:
            if currency_code not in existing_currencies:
                currency = Currency(
                    code=currency_code,
                    name=currency_code
                )
                db.add(currency)
                print(f"Added currency: {currency_code}")
        
        db.commit()
        print("Currencies initialized successfully")
    finally:
        db.close()

def init_impact_levels():
    """Initialize impact levels table."""
    db = SessionLocal()
    try:
        existing_levels = {il.code for il in db.query(ImpactLevel).all()}
        
        impact_levels = [
            ("NON_ECONOMIC", "Non-Economic", 0),
            ("LOW", "Low Impact", 1),
            ("MEDIUM", "Medium Impact", 2),
            ("HIGH", "High Impact", 3)
        ]
        
        for code, name, priority in impact_levels:
            if code not in existing_levels:
                impact_level = ImpactLevel(
                    code=code,
                    name=name,
                    priority=priority
                )
                db.add(impact_level)
                print(f"Added impact level: {code} - {name}")
        
        db.commit()
        print("Impact levels initialized successfully")
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database with basic data...")
    init_currencies()
    init_impact_levels()
    print("Database initialization completed!")
