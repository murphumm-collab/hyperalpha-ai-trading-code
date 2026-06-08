#!/usr/bin/env python3
"""
Add user scoping to Hyper AI tables.

This migration is intentionally idempotent. Existing single-user local data is
assigned to the default user so old installs keep working while new To C users
get isolated profiles, memories, and conversations.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


def _ensure_default_user(conn) -> int:
    result = conn.execute(text("SELECT id FROM users WHERE username = 'default' LIMIT 1"))
    row = result.fetchone()
    if row:
        return int(row[0])

    result = conn.execute(text("""
        INSERT INTO users (username, is_active)
        VALUES ('default', 'true')
        RETURNING id
    """))
    return int(result.fetchone()[0])


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
    """), {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None


def _add_user_id_column(conn, table_name: str) -> None:
    if _column_exists(conn, table_name, "user_id"):
        return

    conn.execute(text(f"""
        ALTER TABLE {table_name}
        ADD COLUMN user_id INTEGER REFERENCES users(id)
    """))


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        default_user_id = _ensure_default_user(conn)

        for table_name in ("hyper_ai_profile", "hyper_ai_memory", "hyper_ai_conversations"):
            _add_user_id_column(conn, table_name)

        existing_default_profile = conn.execute(text("""
            SELECT id FROM hyper_ai_profile
            WHERE user_id = :default_user_id
            LIMIT 1
        """), {"default_user_id": default_user_id}).fetchone()
        if not existing_default_profile:
            conn.execute(text(f"""
                UPDATE hyper_ai_profile
                SET user_id = :default_user_id
                WHERE id = (
                    SELECT id FROM hyper_ai_profile
                    WHERE user_id IS NULL
                    ORDER BY id ASC
                    LIMIT 1
                )
            """), {"default_user_id": default_user_id})

        for table_name in ("hyper_ai_memory", "hyper_ai_conversations"):
            conn.execute(text(f"""
                UPDATE {table_name}
                SET user_id = :default_user_id
                WHERE user_id IS NULL
            """), {"default_user_id": default_user_id})

        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_hyper_ai_profile_user_id
            ON hyper_ai_profile(user_id)
            WHERE user_id IS NOT NULL
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hyper_ai_memory_user_id
            ON hyper_ai_memory(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_hyper_ai_conversations_user_id
            ON hyper_ai_conversations(user_id)
        """))

        conn.commit()
        print("[Migration] Hyper AI user scope ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
