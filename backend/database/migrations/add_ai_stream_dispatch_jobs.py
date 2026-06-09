#!/usr/bin/env python3
"""
Create persistent AI stream dispatch queue.

Jobs in this table are serializable task requests that can be claimed by a
backend worker instance. This avoids relying on an in-process Python closure
when multi-instance worker routing is enabled.
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
            CREATE TABLE IF NOT EXISTS ai_stream_dispatch_jobs (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(120) NOT NULL UNIQUE,
                task_type VARCHAR(80) NOT NULL,
                user_id INTEGER REFERENCES users(id),
                conversation_id INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                payload TEXT NOT NULL,
                runner_id VARCHAR(120),
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                created_at_epoch DOUBLE PRECISION NOT NULL,
                claimed_at_epoch DOUBLE PRECISION,
                completed_at_epoch DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_dispatch_jobs_task_type
            ON ai_stream_dispatch_jobs(task_type)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_dispatch_jobs_user_id
            ON ai_stream_dispatch_jobs(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_dispatch_jobs_conversation_id
            ON ai_stream_dispatch_jobs(conversation_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_dispatch_jobs_status
            ON ai_stream_dispatch_jobs(status)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_dispatch_jobs_runner_id
            ON ai_stream_dispatch_jobs(runner_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_dispatch_jobs_created_at_epoch
            ON ai_stream_dispatch_jobs(created_at_epoch)
        """))

        conn.commit()
        print("[Migration] AI stream dispatch jobs ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
