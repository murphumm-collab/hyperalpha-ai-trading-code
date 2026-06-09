#!/usr/bin/env python3
"""
Persist AI Trading signal candidate audit events.

Events are generated from approved strategy specs and remain review candidates
until a separate backend handoff is explicitly implemented and enabled.
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
            CREATE TABLE IF NOT EXISTS ai_trading_signal_events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                strategy_spec_id INTEGER NOT NULL REFERENCES ai_trading_strategy_specs(id),
                symbol VARCHAR(64) NOT NULL,
                action VARCHAR(20) NOT NULL DEFAULT 'hold',
                status VARCHAR(30) NOT NULL DEFAULT 'review_candidate',
                handoff_status VARCHAR(30) NOT NULL DEFAULT 'not_submitted',
                signal_json TEXT NOT NULL,
                error_message TEXT,
                submitted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_events_user_id
            ON ai_trading_signal_events(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_events_strategy_spec_id
            ON ai_trading_signal_events(strategy_spec_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_events_symbol
            ON ai_trading_signal_events(symbol)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_events_status
            ON ai_trading_signal_events(status)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_events_user_status
            ON ai_trading_signal_events(user_id, status)
        """))

        conn.commit()
        print("[Migration] AI Trading signal events ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
