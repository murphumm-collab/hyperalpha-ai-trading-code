#!/usr/bin/env python3
"""
Add user roles for admin-only system management endpoints.

Existing local/demo installs keep the `default` user as admin so development
workflows remain usable. New To C users default to the ordinary `user` role
unless promoted by DB state or auth environment configuration.
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
        if not _column_exists(conn, "users", "role"):
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'
            """))

        conn.execute(text("""
            UPDATE users
            SET role = 'user'
            WHERE role IS NULL OR role = ''
        """))

        conn.execute(text("""
            UPDATE users
            SET role = 'admin'
            WHERE username = 'default'
              AND role = 'user'
        """))

        conn.commit()
        print("[Migration] User roles ensured")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
