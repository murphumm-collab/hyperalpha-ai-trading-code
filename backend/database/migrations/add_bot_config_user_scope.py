#!/usr/bin/env python3
"""
Scope bot integration configuration by user.

The legacy table stored one Telegram/Discord configuration per platform for the
whole server. To C deployments need each signed-in user to manage their own bot
credentials and notification toggles without overwriting another user's setup.
Existing global rows are assigned to the default user for backwards
compatibility.
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


def _column_exists(conn, table: str, column: str) -> bool:
    return bool(conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = :table
              AND column_name = :column
        )
    """), {"table": table, "column": column}).scalar())


def _drop_platform_only_unique_constraints(conn) -> None:
    rows = conn.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'bot_configs'::regclass
          AND contype = 'u'
          AND pg_get_constraintdef(oid) = 'UNIQUE (platform)'
    """)).fetchall()

    for row in rows:
        conn.execute(text(f'ALTER TABLE bot_configs DROP CONSTRAINT IF EXISTS "{row[0]}"'))


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        default_user_id = _ensure_default_user(conn)

        if not _column_exists(conn, "bot_configs", "user_id"):
            conn.execute(text("""
                ALTER TABLE bot_configs
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """))

        if not _column_exists(conn, "bot_chat_bindings", "user_id"):
            conn.execute(text("""
                ALTER TABLE bot_chat_bindings
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """))

        conn.execute(text("""
            UPDATE bot_configs
            SET user_id = :default_user_id
            WHERE user_id IS NULL
        """), {"default_user_id": default_user_id})

        _drop_platform_only_unique_constraints(conn)

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bot_configs_user_id
            ON bot_configs(user_id)
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_bot_configs_user_platform
            ON bot_configs(user_id, platform)
            WHERE user_id IS NOT NULL
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bot_chat_bindings_user_id
            ON bot_chat_bindings(user_id)
        """))

        conn.commit()
        print("[Migration] Bot configs scoped by user")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
