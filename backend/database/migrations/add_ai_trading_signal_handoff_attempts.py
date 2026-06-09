#!/usr/bin/env python3
"""
Persist AI Trading signal handoff attempt audit records.

Attempts record non-secret preflight and submission outcomes so blocked,
failed, and submitted handoffs are reviewable without exposing gateway URLs,
tokens, or user trading credentials.
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
            CREATE TABLE IF NOT EXISTS ai_trading_signal_handoff_attempts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                signal_event_id INTEGER NOT NULL REFERENCES ai_trading_signal_events(id),
                strategy_spec_id INTEGER NOT NULL REFERENCES ai_trading_strategy_specs(id),
                symbol VARCHAR(64) NOT NULL,
                action VARCHAR(20) NOT NULL DEFAULT 'hold',
                result VARCHAR(30) NOT NULL,
                gateway_ready BOOLEAN NOT NULL DEFAULT FALSE,
                blockers_json TEXT NOT NULL DEFAULT '[]',
                eligibility_json TEXT NOT NULL DEFAULT '{}',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_handoff_attempts_user_id
            ON ai_trading_signal_handoff_attempts(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_handoff_attempts_event_id
            ON ai_trading_signal_handoff_attempts(signal_event_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_handoff_attempts_strategy_spec_id
            ON ai_trading_signal_handoff_attempts(strategy_spec_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_handoff_attempts_user_event
            ON ai_trading_signal_handoff_attempts(user_id, signal_event_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_trading_signal_handoff_attempts_result
            ON ai_trading_signal_handoff_attempts(result)
        """))

        conn.commit()
        print("[Migration] AI Trading signal handoff attempts ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
