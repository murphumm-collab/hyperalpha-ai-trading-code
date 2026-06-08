#!/usr/bin/env python3
"""
Persist AI stream polling tasks and chunks.

The old stream buffer lived only in process memory, which meant page refreshes
were resumable but service restarts lost task status and buffered chunks. These
tables let polling recover completed/error tasks and mark stale running tasks as
interrupted after a restart.
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
            CREATE TABLE IF NOT EXISTS ai_stream_tasks (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(120) NOT NULL UNIQUE,
                user_id INTEGER REFERENCES users(id),
                conversation_id INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                result TEXT,
                error_message TEXT,
                created_at_epoch DOUBLE PRECISION NOT NULL,
                completed_at_epoch DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_tasks_task_id
            ON ai_stream_tasks(task_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_tasks_user_id
            ON ai_stream_tasks(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_tasks_conversation_id
            ON ai_stream_tasks(conversation_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_tasks_status
            ON ai_stream_tasks(status)
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_stream_chunks (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(120) NOT NULL,
                chunk_index INTEGER NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                data TEXT NOT NULL,
                timestamp_epoch DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_ai_stream_chunks_task_index
                    UNIQUE (task_id, chunk_index)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ai_stream_chunks_task_id
            ON ai_stream_chunks(task_id)
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_stream_chunks_task_index
            ON ai_stream_chunks(task_id, chunk_index)
        """))

        conn.commit()
        print("[Migration] AI stream persistence ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
