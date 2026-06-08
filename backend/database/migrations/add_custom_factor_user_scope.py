#!/usr/bin/env python3
"""
Scope user-created custom factors by user.

Built-in expression factors remain global (user_id IS NULL). Existing manual/AI
custom factors are assigned to the default user for backwards compatibility.
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


def _drop_name_only_unique_constraints(conn) -> None:
    rows = conn.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'custom_factors'::regclass
          AND contype = 'u'
          AND pg_get_constraintdef(oid) = 'UNIQUE (name)'
    """)).fetchall()
    for row in rows:
        conn.execute(text(f'ALTER TABLE custom_factors DROP CONSTRAINT IF EXISTS "{row[0]}"'))


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        default_user_id = _ensure_default_user(conn)

        if not _column_exists(conn, "custom_factors", "user_id"):
            conn.execute(text("""
                ALTER TABLE custom_factors
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """))

        conn.execute(text("""
            UPDATE custom_factors
            SET user_id = :default_user_id
            WHERE user_id IS NULL
              AND COALESCE(source, '') != 'builtin_expression'
        """), {"default_user_id": default_user_id})

        _drop_name_only_unique_constraints(conn)

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_custom_factors_user_id
            ON custom_factors(user_id)
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_custom_factors_user_name
            ON custom_factors(user_id, name)
            WHERE user_id IS NOT NULL
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_custom_factors_builtin_name
            ON custom_factors(name)
            WHERE user_id IS NULL
        """))

        conn.commit()
        print("[Migration] Custom factors scoped by user")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
