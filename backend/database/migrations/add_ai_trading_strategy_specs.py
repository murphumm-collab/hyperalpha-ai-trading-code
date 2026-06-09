#!/usr/bin/env python3
"""
Persist per-user AI Trading strategy specs.

These records track draft/review/approved strategy JSON contracts. Approval is
only a product workflow state; it never triggers live order placement.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_trading_strategy_specs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name VARCHAR(120) NOT NULL,
                symbol VARCHAR(64) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                source VARCHAR(50) NOT NULL DEFAULT 'manual',
                spec_json TEXT NOT NULL,
                validation_json TEXT NOT NULL DEFAULT '{}',
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_strategy_specs_user_id
            ON ai_trading_strategy_specs(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_strategy_specs_symbol
            ON ai_trading_strategy_specs(symbol)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_strategy_specs_status
            ON ai_trading_strategy_specs(status)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_strategy_specs_user_status
            ON ai_trading_strategy_specs(user_id, status)
        """))

        conn.commit()
        print("[Migration] AI Trading strategy specs ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
