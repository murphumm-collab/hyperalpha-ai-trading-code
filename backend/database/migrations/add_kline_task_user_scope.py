#!/usr/bin/env python3
"""
Scope K-line backfill tasks to the user who created them.

The collected candle data remains shared market data, but task visibility and
deletion need user ownership so To C users cannot inspect or delete each
other's operational jobs.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


def _ensure_default_user(conn) -> int:
    row = conn.execute(text("SELECT id FROM users WHERE username = 'default' LIMIT 1")).fetchone()
    if row:
        return int(row[0])

    row = conn.execute(text("""
        INSERT INTO users (username, is_active)
        VALUES ('default', 'true')
        RETURNING id
    """)).fetchone()
    return int(row[0])


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        default_user_id = _ensure_default_user(conn)

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kline_collection_tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                exchange VARCHAR(20) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                period VARCHAR(10) NOT NULL DEFAULT '1m',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                progress INTEGER NOT NULL DEFAULT 0,
                total_records INTEGER DEFAULT 0,
                collected_records INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            ALTER TABLE kline_collection_tasks
            ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_kline_tasks_user_id
            ON kline_collection_tasks(user_id)
        """))
        conn.execute(text("""
            UPDATE kline_collection_tasks
            SET user_id = :default_user_id
            WHERE user_id IS NULL
        """), {"default_user_id": default_user_id})
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_kline_tasks_status
            ON kline_collection_tasks(status, created_at DESC)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_kline_tasks_exchange_symbol
            ON kline_collection_tasks(exchange, symbol)
        """))

        conn.commit()
        print("[Migration] K-line task user scope ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
