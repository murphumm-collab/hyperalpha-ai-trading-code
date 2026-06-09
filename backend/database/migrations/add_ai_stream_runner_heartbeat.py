#!/usr/bin/env python3
"""
Add AI stream runner heartbeat metadata.

This records which backend instance owns a running AI stream task and when it
last persisted activity. It is a foundation for later distributed worker
routing or takeover without changing current execution behavior.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import DATABASE_URL


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE ai_stream_tasks
            ADD COLUMN IF NOT EXISTS runner_id VARCHAR(120)
        """))
        conn.execute(text("""
            ALTER TABLE ai_stream_tasks
            ADD COLUMN IF NOT EXISTS last_heartbeat_epoch DOUBLE PRECISION
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_tasks_runner_id
            ON ai_stream_tasks(runner_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_tasks_last_heartbeat
            ON ai_stream_tasks(last_heartbeat_epoch)
        """))

        conn.commit()
        print("[Migration] AI stream runner heartbeat ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
