#!/usr/bin/env python3
"""
Add AI Trading agent-session metadata to strategy, signal, and handoff audit rows.

The fields are product-level context partitions for multi-session To C usage.
They are not authentication sessions and never carry trading credentials.
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from database.connection import DATABASE_URL


TABLE_COLUMNS = {
    "ai_trading_strategy_specs": (
        ("agent_session_id", "VARCHAR(80)"),
        ("agent_session_name", "VARCHAR(120)"),
        ("agent_context_summary", "TEXT"),
    ),
    "ai_trading_signal_events": (
        ("agent_session_id", "VARCHAR(80)"),
        ("agent_session_name", "VARCHAR(120)"),
    ),
    "ai_trading_signal_handoff_attempts": (
        ("agent_session_id", "VARCHAR(80)"),
        ("agent_session_name", "VARCHAR(120)"),
    ),
}


def _has_table(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def _has_column(conn, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspect(conn).get_columns(table_name)}


def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        for table_name, columns in TABLE_COLUMNS.items():
            if not _has_table(conn, table_name):
                continue
            for column_name, column_type in columns:
                if not _has_column(conn, table_name, column_name):
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                    ))

        for table_name in TABLE_COLUMNS:
            if _has_table(conn, table_name):
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_agent_session_id
                    ON {table_name}(agent_session_id)
                """))

        conn.commit()
        print("[Migration] AI Trading agent-session fields ready")


def upgrade():
    migrate()


if __name__ == "__main__":
    migrate()
