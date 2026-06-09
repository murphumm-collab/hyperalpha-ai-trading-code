#!/usr/bin/env python3
"""
Persist AI stream high-risk tool confirmations.

The first AI stream persistence migration stores tasks and chunks. This table
stores runtime checkpoint responses so a confirmation submitted to one backend
instance can be observed by the instance currently running the AI task.
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
            CREATE TABLE IF NOT EXISTS ai_stream_confirmations (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(120) NOT NULL,
                user_id INTEGER REFERENCES users(id),
                confirmation_id VARCHAR(120) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                confirmed BOOLEAN,
                response TEXT,
                created_at_epoch DOUBLE PRECISION NOT NULL,
                submitted_at_epoch DOUBLE PRECISION,
                cleared_at_epoch DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_ai_stream_confirmations_task_confirmation
                    UNIQUE (task_id, confirmation_id)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_confirmations_task_id
            ON ai_stream_confirmations(task_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_confirmations_user_id
            ON ai_stream_confirmations(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_confirmations_confirmation_id
            ON ai_stream_confirmations(confirmation_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_confirmations_status
            ON ai_stream_confirmations(status)
        """))

        conn.commit()
        print("[Migration] AI stream confirmations ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
