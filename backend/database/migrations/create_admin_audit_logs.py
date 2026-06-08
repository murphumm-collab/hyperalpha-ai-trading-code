#!/usr/bin/env python3
"""
Create persistent admin audit logs.

Role changes and future security-sensitive admin operations should be written
here so operator actions survive process restarts.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        table_exists = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'admin_audit_logs'
            )
        """)).scalar()

        if not table_exists:
            conn.execute(text("""
                CREATE TABLE admin_audit_logs (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(50) NOT NULL,
                    actor_user_id INTEGER REFERENCES users(id),
                    actor_username VARCHAR(50),
                    target_user_id INTEGER REFERENCES users(id),
                    target_username VARCHAR(50),
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_actor
            ON admin_audit_logs(actor_user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_target
            ON admin_audit_logs(target_user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_created
            ON admin_audit_logs(created_at)
        """))
        conn.commit()
        print("[Migration] Admin audit logs ensured")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
