#!/usr/bin/env python3
"""
Create per-user symbol watchlists for To C account isolation.

Existing single-user installs keep their current global Hyperliquid/Binance
watchlists by copying system_configs values to the default user. New users get
their own watchlist rows and do not overwrite each other through SystemConfig.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


WATCHLIST_CONFIG_KEYS = {
    "hyperliquid": "hyperliquid_selected_symbols",
    "binance": "binance_selected_symbols",
}


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


def _system_config_value(conn, key: str) -> str:
    row = conn.execute(text("""
        SELECT value FROM system_configs
        WHERE key = :key
        LIMIT 1
    """), {"key": key}).fetchone()
    return str(row[0] or "") if row else ""


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        default_user_id = _ensure_default_user(conn)

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_symbol_watchlists (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                exchange VARCHAR(32) NOT NULL,
                symbols TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_symbol_watchlists_user_exchange
                    UNIQUE (user_id, exchange)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_symbol_watchlists_user_id
            ON user_symbol_watchlists(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_symbol_watchlists_exchange
            ON user_symbol_watchlists(exchange)
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_user_symbol_watchlists_user_exchange
            ON user_symbol_watchlists(user_id, exchange)
        """))

        for exchange, config_key in WATCHLIST_CONFIG_KEYS.items():
            existing = conn.execute(text("""
                SELECT id FROM user_symbol_watchlists
                WHERE user_id = :user_id
                  AND exchange = :exchange
                LIMIT 1
            """), {
                "user_id": default_user_id,
                "exchange": exchange,
            }).fetchone()
            if existing:
                continue

            symbols = _system_config_value(conn, config_key) or "[]"
            conn.execute(text("""
                INSERT INTO user_symbol_watchlists (user_id, exchange, symbols)
                VALUES (:user_id, :exchange, :symbols)
            """), {
                "user_id": default_user_id,
                "exchange": exchange,
                "symbols": symbols,
            })

        conn.commit()
        print("[Migration] User symbol watchlists ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
