"""Verify private custom factor precompute storage against local Postgres.

This smoke inserts synthetic 1h klines under an isolated exchange, creates two
users with the same private factor name, computes both factors, and proves that
results are stored and queried through user_factor_* tables rather than shared
factor_values/factor_effectiveness rows.

Run from backend:

    DATABASE_URL=postgresql://alpha_user:alpha_pass@127.0.0.1:5432/alpha_arena \
      uv run python scripts/ai_trading_private_factor_precompute_smoke.py
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from database.connection import SessionLocal
from database.models import CustomFactor, User
from database.migrations.create_user_factor_result_tables import upgrade as ensure_user_factor_tables
from services.factor_effectiveness_service import FactorEffectivenessService
from services.hyper_ai_tools import execute_query_factors


EXCHANGE = "codex_smoke"
SYMBOL = "CXSFACTOR"
PERIOD = "1h"
BAR_COUNT = 2000


def _cleanup(db, run_id: str) -> None:
    usernames = [f"{run_id}-alice", f"{run_id}-bob"]
    factor_names = [f"{run_id}_same_private_factor"]

    factor_rows = db.query(CustomFactor).filter(CustomFactor.name.in_(factor_names)).all()
    factor_ids = [int(row.id) for row in factor_rows]
    user_rows = db.query(User).filter(User.username.in_(usernames)).all()
    user_ids = [int(row.id) for row in user_rows]

    if factor_ids:
        db.execute(
            text("DELETE FROM user_factor_effectiveness WHERE custom_factor_id = ANY(:factor_ids)"),
            {"factor_ids": factor_ids},
        )
        db.execute(
            text("DELETE FROM user_factor_values WHERE custom_factor_id = ANY(:factor_ids)"),
            {"factor_ids": factor_ids},
        )
        db.execute(
            text("DELETE FROM factor_effectiveness WHERE exchange = :ex AND factor_name = ANY(:factor_names)"),
            {"ex": EXCHANGE, "factor_names": factor_names},
        )
        db.execute(
            text("DELETE FROM factor_values WHERE exchange = :ex AND factor_name = ANY(:factor_names)"),
            {"ex": EXCHANGE, "factor_names": factor_names},
        )
        db.query(CustomFactor).filter(CustomFactor.id.in_(factor_ids)).delete(synchronize_session=False)

    db.execute(
        text("DELETE FROM crypto_klines WHERE exchange = :ex AND symbol = :sym AND period = :period"),
        {"ex": EXCHANGE, "sym": SYMBOL, "period": PERIOD},
    )

    if user_ids:
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    db.commit()


def _insert_users_and_factors(db, run_id: str) -> dict[str, Any]:
    alice = User(username=f"{run_id}-alice", is_active="true")
    bob = User(username=f"{run_id}-bob", is_active="true")
    db.add_all([alice, bob])
    db.flush()

    factor_name = f"{run_id}_same_private_factor"
    alice_factor = CustomFactor(
        user_id=alice.id,
        name=factor_name,
        expression="ROC(close, 1)",
        description="Smoke-only private factor for Alice.",
        category="custom",
        source="ai",
        is_active=True,
    )
    bob_factor = CustomFactor(
        user_id=bob.id,
        name=factor_name,
        expression="ROC(close, 2)",
        description="Smoke-only private factor for Bob.",
        category="custom",
        source="ai",
        is_active=True,
    )
    db.add_all([alice_factor, bob_factor])
    db.flush()
    db.commit()

    return {
        "factor_name": factor_name,
        "alice_user_id": int(alice.id),
        "bob_user_id": int(bob.id),
        "alice_factor_id": int(alice_factor.id),
        "bob_factor_id": int(bob_factor.id),
    }


def _insert_klines(db) -> None:
    start_ts = int(time.time()) - (BAR_COUNT + 24) * 3600
    rows = []
    for i in range(BAR_COUNT):
        ts = start_ts + i * 3600
        wave = (i % 17) * 0.03
        close = 100.0 + i * 0.08 + wave
        open_price = close - 0.05
        high = close + 0.4
        low = close - 0.4
        volume = 1000.0 + (i % 31) * 7.0
        rows.append({
            "exchange": EXCHANGE,
            "symbol": SYMBOL,
            "market": "CRYPTO",
            "timestamp": ts,
            "period": PERIOD,
            "datetime_str": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "open_price": open_price,
            "high_price": high,
            "low_price": low,
            "close_price": close,
            "volume": volume,
            "environment": "mainnet",
        })

    db.execute(text("""
        INSERT INTO crypto_klines (
            exchange, symbol, market, timestamp, period, datetime_str,
            open_price, high_price, low_price, close_price, volume, environment
        )
        VALUES (
            :exchange, :symbol, :market, :timestamp, :period, :datetime_str,
            :open_price, :high_price, :low_price, :close_price, :volume, :environment
        )
        ON CONFLICT (exchange, symbol, market, period, timestamp, environment)
        DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume
    """), rows)
    db.commit()


def _json_tool_result(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if "error" in payload:
        raise AssertionError(payload["error"])
    return payload


def _scalar(db, sql: str, params: dict[str, Any]) -> int:
    return int(db.execute(text(sql), params).scalar() or 0)


def run_smoke() -> dict[str, Any]:
    ensure_user_factor_tables()
    db = SessionLocal()
    run_id = f"pfsmoke_{int(time.time())}"
    try:
        _cleanup(db, run_id)
        ids = _insert_users_and_factors(db, run_id)
        _insert_klines(db)

        service = FactorEffectivenessService()
        service._get_symbols = lambda db, exchange: [SYMBOL]
        alice_compute = service.compute_single_factor(
            db, EXCHANGE, ids["factor_name"], user_id=ids["alice_user_id"]
        )
        bob_compute = service.compute_single_factor(
            db, EXCHANGE, ids["factor_name"], user_id=ids["bob_user_id"]
        )
        if alice_compute.get("storage_scope") != "user_private":
            raise AssertionError(f"alice storage_scope mismatch: {alice_compute}")
        if bob_compute.get("storage_scope") != "user_private":
            raise AssertionError(f"bob storage_scope mismatch: {bob_compute}")

        alice_query = _json_tool_result(execute_query_factors(
            db,
            EXCHANGE,
            symbol=SYMBOL,
            factor_name=ids["factor_name"],
            days=3650,
            user_id=ids["alice_user_id"],
        ))
        bob_query = _json_tool_result(execute_query_factors(
            db,
            EXCHANGE,
            symbol=SYMBOL,
            factor_name=ids["factor_name"],
            days=3650,
            user_id=ids["bob_user_id"],
        ))
        ranking = _json_tool_result(execute_query_factors(
            db,
            EXCHANGE,
            symbol=SYMBOL,
            user_id=ids["alice_user_id"],
        ))

        if alice_query.get("storage_scope") != "user_private":
            raise AssertionError(f"alice query did not use private storage: {alice_query}")
        if bob_query.get("storage_scope") != "user_private":
            raise AssertionError(f"bob query did not use private storage: {bob_query}")
        if alice_query.get("custom_factor_id") != ids["alice_factor_id"]:
            raise AssertionError("alice query returned the wrong custom_factor_id")
        if bob_query.get("custom_factor_id") != ids["bob_factor_id"]:
            raise AssertionError("bob query returned the wrong custom_factor_id")
        if alice_query.get("latest_value") == bob_query.get("latest_value"):
            raise AssertionError("same-name private factors returned the same latest value unexpectedly")
        if not alice_query.get("effectiveness") or not bob_query.get("effectiveness"):
            raise AssertionError("private factor effectiveness was not returned")
        if not alice_query.get("history") or not bob_query.get("history"):
            raise AssertionError("private factor history was not returned")

        top_private = [
            item for item in ranking.get("top_factors", [])
            if item.get("custom_factor_id") == ids["alice_factor_id"]
            and item.get("source") == "user_private"
        ]
        if not top_private:
            raise AssertionError("private factor ranking did not include Alice's scoped factor")

        alice_value_rows = _scalar(db, """
            SELECT COUNT(*) FROM user_factor_values
            WHERE user_id = :uid AND custom_factor_id = :cfid
        """, {"uid": ids["alice_user_id"], "cfid": ids["alice_factor_id"]})
        bob_value_rows = _scalar(db, """
            SELECT COUNT(*) FROM user_factor_values
            WHERE user_id = :uid AND custom_factor_id = :cfid
        """, {"uid": ids["bob_user_id"], "cfid": ids["bob_factor_id"]})
        alice_effect_rows = _scalar(db, """
            SELECT COUNT(*) FROM user_factor_effectiveness
            WHERE user_id = :uid AND custom_factor_id = :cfid
        """, {"uid": ids["alice_user_id"], "cfid": ids["alice_factor_id"]})
        bob_effect_rows = _scalar(db, """
            SELECT COUNT(*) FROM user_factor_effectiveness
            WHERE user_id = :uid AND custom_factor_id = :cfid
        """, {"uid": ids["bob_user_id"], "cfid": ids["bob_factor_id"]})
        global_effect_rows = _scalar(db, """
            SELECT COUNT(*) FROM factor_effectiveness
            WHERE exchange = :ex AND factor_name = :factor_name
        """, {"ex": EXCHANGE, "factor_name": ids["factor_name"]})
        global_value_rows = _scalar(db, """
            SELECT COUNT(*) FROM factor_values
            WHERE exchange = :ex AND factor_name = :factor_name
        """, {"ex": EXCHANGE, "factor_name": ids["factor_name"]})

        if min(alice_value_rows, bob_value_rows, alice_effect_rows, bob_effect_rows) <= 0:
            raise AssertionError("missing user-scoped value/effectiveness rows")
        if global_effect_rows or global_value_rows:
            raise AssertionError(
                "private factor precompute polluted shared factor tables: "
                f"effectiveness={global_effect_rows}, values={global_value_rows}"
            )

        return {
            "success": True,
            "exchange": EXCHANGE,
            "symbol": SYMBOL,
            "factor_name": ids["factor_name"],
            "alice": {
                "user_id": ids["alice_user_id"],
                "custom_factor_id": ids["alice_factor_id"],
                "value_rows": alice_value_rows,
                "effectiveness_rows": alice_effect_rows,
                "latest_value": alice_query["latest_value"],
            },
            "bob": {
                "user_id": ids["bob_user_id"],
                "custom_factor_id": ids["bob_factor_id"],
                "value_rows": bob_value_rows,
                "effectiveness_rows": bob_effect_rows,
                "latest_value": bob_query["latest_value"],
            },
            "shared_table_rows": {
                "factor_values": global_value_rows,
                "factor_effectiveness": global_effect_rows,
            },
            "ranking_private_items": len(top_private),
        }
    finally:
        try:
            _cleanup(db, run_id)
        finally:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    report = run_smoke()
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
