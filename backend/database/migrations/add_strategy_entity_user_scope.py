#!/usr/bin/env python3
"""
Add user ownership to strategy-facing prompt and signal entities.

System prompt templates remain global (`user_id` NULL). Existing non-system
prompt templates, signal definitions, and signal pools are assigned to the
default user so current local installs keep their data.
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


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    row = conn.execute(text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
    """), {"table_name": table_name, "column_name": column_name}).fetchone()
    return row is not None


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

        for table_name in ("prompt_templates", "signal_definitions", "signal_pools"):
            _add_user_id_column(conn, table_name)

        conn.execute(text("""
            UPDATE prompt_templates
            SET user_id = :default_user_id
            WHERE user_id IS NULL
              AND COALESCE(is_system, 'false') != 'true'
        """), {"default_user_id": default_user_id})

        for table_name in ("signal_definitions", "signal_pools"):
            conn.execute(text(f"""
                UPDATE {table_name}
                SET user_id = :default_user_id
                WHERE user_id IS NULL
            """), {"default_user_id": default_user_id})

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prompt_templates_user_id
            ON prompt_templates(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_signal_definitions_user_id
            ON signal_definitions(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_signal_pools_user_id
            ON signal_pools(user_id)
        """))

        conn.commit()
        print("[Migration] Strategy entity user scope ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
