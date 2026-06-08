#!/usr/bin/env python3
"""
Add per-user sampling preferences while keeping an effective global row.

Rows with user_id IS NOT NULL store each user's preference. The legacy NULL
user_id row remains the effective aggregate used by existing global collectors:
minimum sampling interval and maximum sampling depth across user preferences.
"""

import os
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


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        if not _column_exists(conn, "global_sampling_configs", "user_id"):
            conn.execute(text("""
                ALTER TABLE global_sampling_configs
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_global_sampling_configs_user_id
            ON global_sampling_configs(user_id)
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_global_sampling_configs_user_id
            ON global_sampling_configs(user_id)
            WHERE user_id IS NOT NULL
        """))

        existing_global = conn.execute(text("""
            SELECT id FROM global_sampling_configs
            WHERE user_id IS NULL
            ORDER BY id
            LIMIT 1
        """)).fetchone()
        if not existing_global:
            conn.execute(text("""
                INSERT INTO global_sampling_configs (user_id, sampling_interval, sampling_depth)
                VALUES (NULL, 18, 10)
            """))

        conn.commit()
        print("[Migration] Global sampling configs scoped by user")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
