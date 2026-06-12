"""
Create user-scoped factor result tables for private custom factors.

Shared factor_values/factor_effectiveness stay global and must not store
user-owned private custom factor rows by name.
"""

from sqlalchemy import text
from database.connection import SessionLocal


def _table_exists(db, table_name: str) -> bool:
    return bool(db.execute(text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
        )
    """), {"table_name": table_name}).scalar())


def upgrade():
    db = SessionLocal()
    try:
        if not _table_exists(db, "user_factor_values"):
            db.execute(text("""
                CREATE TABLE user_factor_values (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    custom_factor_id INTEGER NOT NULL REFERENCES custom_factors(id) ON DELETE CASCADE,
                    exchange VARCHAR(20) NOT NULL DEFAULT 'hyperliquid',
                    symbol VARCHAR(20) NOT NULL,
                    period VARCHAR(10) NOT NULL,
                    factor_name VARCHAR(100) NOT NULL,
                    factor_category VARCHAR(30) NOT NULL DEFAULT 'custom',
                    timestamp INTEGER NOT NULL,
                    value FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT user_factor_values_unique_key
                        UNIQUE (user_id, custom_factor_id, exchange, symbol, period, timestamp)
                )
            """))
            db.execute(text("""
                CREATE INDEX idx_user_factor_values_user_factor
                ON user_factor_values(user_id, custom_factor_id)
            """))
            db.execute(text("""
                CREATE INDEX idx_user_factor_values_symbol_period
                ON user_factor_values(user_id, exchange, symbol, period)
            """))
            db.execute(text("""
                CREATE INDEX idx_user_factor_values_timestamp
                ON user_factor_values(timestamp)
            """))

        if not _table_exists(db, "user_factor_effectiveness"):
            db.execute(text("""
                CREATE TABLE user_factor_effectiveness (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    custom_factor_id INTEGER NOT NULL REFERENCES custom_factors(id) ON DELETE CASCADE,
                    exchange VARCHAR(20) NOT NULL DEFAULT 'hyperliquid',
                    factor_name VARCHAR(100) NOT NULL,
                    factor_category VARCHAR(30) NOT NULL DEFAULT 'custom',
                    symbol VARCHAR(20) NOT NULL,
                    period VARCHAR(10) NOT NULL,
                    forward_period VARCHAR(10) NOT NULL,
                    calc_date DATE NOT NULL,
                    lookback_days INTEGER NOT NULL DEFAULT 30,
                    ic_mean FLOAT,
                    ic_std FLOAT,
                    icir FLOAT,
                    win_rate FLOAT,
                    decay_half_life INTEGER,
                    sample_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT user_factor_effectiveness_unique_key
                        UNIQUE (
                            user_id, custom_factor_id, exchange, symbol,
                            period, forward_period, calc_date
                        )
                )
            """))
            db.execute(text("""
                CREATE INDEX idx_user_factor_effectiveness_user_factor
                ON user_factor_effectiveness(user_id, custom_factor_id)
            """))
            db.execute(text("""
                CREATE INDEX idx_user_factor_effectiveness_symbol_period
                ON user_factor_effectiveness(user_id, exchange, symbol, period, forward_period)
            """))
            db.execute(text("""
                CREATE INDEX idx_user_factor_effectiveness_calc_date
                ON user_factor_effectiveness(calc_date)
            """))

        db.commit()
        print("[Migration] User-scoped factor result tables ready", flush=True)
    finally:
        db.close()
