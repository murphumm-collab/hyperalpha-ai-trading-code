#!/usr/bin/env python3
"""
Add per-config webhook secrets for bot integrations.

Telegram webhooks are public HTTP entry points. In a To C deployment each user's
bot must route through a user-owned secret so one inbound message cannot fall
back to the first configured bot/session on the server.
"""

import os
import secrets
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


def _column_exists(conn, table: str, column: str) -> bool:
    return bool(conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = :table
              AND column_name = :column
        )
    """), {"table": table, "column": column}).scalar())


def _generate_secret(conn) -> str:
    while True:
        secret = secrets.token_urlsafe(32)
        exists = conn.execute(text("""
            SELECT 1 FROM bot_configs
            WHERE webhook_secret = :secret
            LIMIT 1
        """), {"secret": secret}).fetchone()
        if not exists:
            return secret


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        if not _column_exists(conn, "bot_configs", "webhook_secret"):
            conn.execute(text("""
                ALTER TABLE bot_configs
                ADD COLUMN webhook_secret VARCHAR(96)
            """))

        rows = conn.execute(text("""
            SELECT id
            FROM bot_configs
            WHERE webhook_secret IS NULL OR webhook_secret = ''
        """)).fetchall()

        for row in rows:
            conn.execute(text("""
                UPDATE bot_configs
                SET webhook_secret = :secret
                WHERE id = :id
            """), {"id": row[0], "secret": _generate_secret(conn)})

        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_bot_configs_webhook_secret
            ON bot_configs(webhook_secret)
            WHERE webhook_secret IS NOT NULL
        """))

        conn.commit()
        print("[Migration] Bot webhook secrets ensured")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
