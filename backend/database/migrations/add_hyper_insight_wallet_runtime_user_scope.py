#!/usr/bin/env python3
"""
Create per-user Hyper Insight wallet runtime configuration.

The previous local runtime stored one global token and enabled flag in
system_configs. This migration preserves that local single-user setup by
copying it to the default user, while new To C users get isolated runtime
state and websocket connections.
"""

import os
import sys
from datetime import datetime

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


def _system_config_value(conn, key: str) -> str:
    row = conn.execute(text("""
        SELECT value FROM system_configs
        WHERE key = :key
        LIMIT 1
    """), {"key": key}).fetchone()
    return str(row[0] or "") if row else ""


def _parse_timestamp(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        default_user_id = _ensure_default_user(conn)

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hyper_insight_wallet_runtime_configs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                access_token TEXT,
                token_synced_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_hyper_insight_wallet_runtime_user_id
            ON hyper_insight_wallet_runtime_configs(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hyper_insight_wallet_runtime_enabled
            ON hyper_insight_wallet_runtime_configs(enabled)
        """))

        existing = conn.execute(text("""
            SELECT id FROM hyper_insight_wallet_runtime_configs
            WHERE user_id = :user_id
            LIMIT 1
        """), {"user_id": default_user_id}).fetchone()
        if not existing:
            enabled = _system_config_value(conn, "hyper_insight_wallet_enabled") == "true"
            access_token = _system_config_value(conn, "hyper_insight_wallet_access_token")
            token_synced_at = _parse_timestamp(_system_config_value(conn, "hyper_insight_wallet_token_synced_at"))
            if enabled or access_token or token_synced_at:
                conn.execute(text("""
                    INSERT INTO hyper_insight_wallet_runtime_configs
                        (user_id, enabled, access_token, token_synced_at)
                    VALUES
                        (:user_id, :enabled, :access_token, :token_synced_at)
                """), {
                    "user_id": default_user_id,
                    "enabled": enabled,
                    "access_token": access_token or None,
                    "token_synced_at": token_synced_at,
                })

        conn.commit()
        print("[Migration] Hyper Insight wallet runtime user scope ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
