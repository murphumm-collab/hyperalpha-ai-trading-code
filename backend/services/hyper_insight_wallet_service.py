"""Runtime client for Hyper Insight wallet tracking integration.

The To C version needs more than one user to keep a live Hyper Insight
connection. This service stores a per-user runtime token/enabled flag and keeps
one websocket loop per active user, while matching wallet events only against
that user's wallet-tracking signal pools.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from database.connection import SessionLocal
from database.models import (
    HyperInsightWalletRuntimeConfig,
    SignalPool,
    SignalTriggerLog,
)

logger = logging.getLogger(__name__)

HYPER_INSIGHT_WS_URL = "wss://hyper.akooi.com/ws/events"

MARKET_SIGNAL_SOURCE = "market_signals"
WALLET_TRACKING_SOURCE = "wallet_tracking"
WALLET_TRIGGER_SYMBOL = "WALLET"
MAX_RECENT_EVENT_KEYS = 4096


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_json_text(value: Any, fallback: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    if value is None:
        return fallback
    return value


def _serialize_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _default_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "disabled",
        "tier": None,
        "synced_addresses": [],
        "last_connected_at": None,
        "last_message_at": None,
        "last_event_at": None,
        "last_error": None,
        "active_wallet_pool_count": 0,
        "token_synced_at": None,
    }


class HyperInsightWalletService:
    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._runner_tasks: dict[int, asyncio.Task] = {}
        self._callback_worker_task: Optional[asyncio.Task] = None
        self._callback_queue: Optional[asyncio.Queue[tuple[int, str, dict[str, Any], dict[str, Any]]]] = None
        self._refresh_events: dict[int, asyncio.Event] = {}
        self._shutdown = False
        self._ws_by_user: dict[int, WebSocketClientProtocol] = {}
        self._state_lock = asyncio.Lock()
        self._states: dict[int, dict[str, Any]] = {}
        self._recent_event_keys: dict[int, deque[str]] = {}
        self._recent_event_key_sets: dict[int, set[str]] = {}

    async def startup(self) -> None:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        if self._callback_queue is None:
            self._callback_queue = asyncio.Queue(maxsize=1000)
        if self._callback_worker_task is None or self._callback_worker_task.done():
            self._callback_worker_task = asyncio.create_task(
                self._callback_worker_loop(),
                name="hyper-insight-wallet-callback-worker",
            )
        self._shutdown = False
        await self.refresh_runtime()

    async def shutdown(self) -> None:
        self._shutdown = True
        for event in self._refresh_events.values():
            event.set()
        await self._close_ws()

        for task in list(self._runner_tasks.values()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._runner_tasks.clear()
        self._refresh_events.clear()

        if self._callback_worker_task and not self._callback_worker_task.done():
            self._callback_worker_task.cancel()
            try:
                await self._callback_worker_task
            except asyncio.CancelledError:
                pass
        self._callback_worker_task = None

    def request_refresh(self, user_id: Optional[int] = None) -> None:
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(self._request_refresh_in_loop, user_id)

    def _request_refresh_in_loop(self, user_id: Optional[int] = None) -> None:
        if user_id is None:
            asyncio.create_task(self.refresh_runtime())
            return
        self._ensure_user_runner(user_id)
        self._refresh_events[user_id].set()

    async def refresh_runtime(self, user_id: Optional[int] = None) -> None:
        user_ids = [user_id] if user_id is not None else self._load_runtime_user_ids()
        for runtime_user_id in user_ids:
            self._ensure_user_runner(runtime_user_id)
            self._refresh_events[runtime_user_id].set()

    async def sync_access_token(self, user_id: int, access_token: str) -> None:
        previous_token = self._load_runtime_config(user_id).get("access_token") or ""
        timestamp = _utcnow_naive()
        with SessionLocal() as db:
            row = self._get_or_create_runtime_config(db, user_id)
            row.access_token = access_token
            row.token_synced_at = timestamp
            db.commit()

        await self._update_state(user_id, token_synced_at=timestamp.isoformat(), last_error=None)
        if previous_token and previous_token != access_token:
            await self._close_ws(user_id)
        await self.refresh_runtime(user_id)

    async def clear_access_token(self, user_id: int) -> None:
        with SessionLocal() as db:
            row = self._get_or_create_runtime_config(db, user_id)
            row.access_token = ""
            db.commit()

        await self._close_ws(user_id)
        await self._update_state(
            user_id,
            tier=None,
            synced_addresses=[],
            last_message_at=None,
            last_event_at=None,
            last_error=None,
        )
        await self.refresh_runtime(user_id)

    async def set_enabled(self, user_id: int, enabled: bool) -> None:
        with SessionLocal() as db:
            row = self._get_or_create_runtime_config(db, user_id)
            row.enabled = enabled
            db.commit()

        if not enabled:
            await self._close_ws(user_id)
        await self._update_state(user_id, enabled=enabled)
        await self.refresh_runtime(user_id)

    def get_status_snapshot(self, user_id: int) -> dict[str, Any]:
        runtime = self._load_runtime_config(user_id)
        snapshot = _default_state()
        snapshot.update(dict(self._states.get(user_id) or {}))
        snapshot["user_id"] = user_id
        snapshot["enabled"] = runtime["enabled"]
        snapshot["token_synced_at"] = runtime["token_synced_at"]
        snapshot["active_wallet_pool_count"] = runtime["active_wallet_pool_count"]
        snapshot["synced_addresses"] = list(snapshot.get("synced_addresses") or [])

        if not runtime["enabled"]:
            snapshot["status"] = "disabled"
        elif not runtime["access_token"]:
            snapshot["status"] = "waiting_for_token"
        elif snapshot.get("status") in {None, "disabled", "waiting_for_token"}:
            snapshot["status"] = "connecting"

        if runtime["enabled"] and runtime["access_token"]:
            self.request_refresh(user_id)

        return snapshot

    def get_access_token(self, user_id: int) -> str:
        return (self._load_runtime_config(user_id).get("access_token") or "").strip()

    def _get_or_create_runtime_config(self, db, user_id: int) -> HyperInsightWalletRuntimeConfig:
        row = (
            db.query(HyperInsightWalletRuntimeConfig)
            .filter(HyperInsightWalletRuntimeConfig.user_id == user_id)
            .first()
        )
        if row:
            return row

        row = HyperInsightWalletRuntimeConfig(user_id=user_id, enabled=False, access_token="")
        db.add(row)
        db.flush()
        return row

    def _load_runtime_user_ids(self) -> list[int]:
        with SessionLocal() as db:
            rows = db.query(HyperInsightWalletRuntimeConfig.user_id).all()
            return [int(row[0]) for row in rows if row[0] is not None]

    def _load_runtime_config(self, user_id: int) -> dict[str, Any]:
        with SessionLocal() as db:
            row = (
                db.query(HyperInsightWalletRuntimeConfig)
                .filter(HyperInsightWalletRuntimeConfig.user_id == user_id)
                .first()
            )
            active_wallet_pool_count = self._count_enabled_wallet_pools(db, user_id)
            if not row:
                return {
                    "enabled": False,
                    "access_token": "",
                    "token_synced_at": None,
                    "active_wallet_pool_count": active_wallet_pool_count,
                }
            return {
                "enabled": bool(row.enabled),
                "access_token": (row.access_token or "").strip(),
                "token_synced_at": _serialize_timestamp(row.token_synced_at),
                "active_wallet_pool_count": active_wallet_pool_count,
            }

    def _count_enabled_wallet_pools(self, db, user_id: int) -> int:
        return (
            db.query(SignalPool)
            .filter(
                SignalPool.user_id == user_id,
                SignalPool.enabled == True,  # noqa: E712
                SignalPool.is_deleted != True,  # noqa: E712
                SignalPool.source_type == WALLET_TRACKING_SOURCE,
            )
            .count()
        )

    def _ensure_user_runner(self, user_id: int) -> None:
        if user_id not in self._refresh_events:
            self._refresh_events[user_id] = asyncio.Event()
        task = self._runner_tasks.get(user_id)
        if task is None or task.done():
            self._runner_tasks[user_id] = asyncio.create_task(
                self._runner_loop(user_id),
                name=f"hyper-insight-wallet-service-user-{user_id}",
            )

    async def _runner_loop(self, user_id: int) -> None:
        backoff_seconds = 1
        while not self._shutdown:
            runtime = self._load_runtime_config(user_id)
            await self._apply_idle_state(user_id, runtime)

            should_connect = runtime["enabled"] and runtime["access_token"]
            if not should_connect:
                await self._close_ws(user_id)
                event = self._refresh_events[user_id]
                event.clear()
                await event.wait()
                backoff_seconds = 1
                continue

            try:
                await self._connect_once(user_id, runtime["access_token"])
                backoff_seconds = 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self._update_state(user_id, status="error", last_error=str(exc))
                logger.warning("[HyperInsight] user=%s wallet runtime connection error: %s", user_id, exc)
                event = self._refresh_events[user_id]
                event.clear()
                try:
                    await asyncio.wait_for(event.wait(), timeout=backoff_seconds)
                except asyncio.TimeoutError:
                    pass
                backoff_seconds = min(backoff_seconds * 2, 30)

    async def _apply_idle_state(self, user_id: int, runtime: dict[str, Any]) -> None:
        updates = {
            "enabled": runtime["enabled"],
            "token_synced_at": runtime["token_synced_at"],
            "active_wallet_pool_count": runtime["active_wallet_pool_count"],
        }
        current_status = (self._states.get(user_id) or {}).get("status")
        if not runtime["enabled"]:
            updates["status"] = "disabled"
        elif not runtime["access_token"]:
            updates["status"] = "waiting_for_token"
        elif current_status not in {"connected", "connecting"}:
            updates["status"] = "connecting"
        await self._update_state(user_id, **updates)

    async def _connect_once(self, user_id: int, access_token: str) -> None:
        url = f"{HYPER_INSIGHT_WS_URL}?token={access_token}"
        await self._update_state(user_id, status="connecting", last_error=None)
        async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
            async with self._state_lock:
                self._ws_by_user[user_id] = ws
            await self._update_state(
                user_id,
                status="connected",
                last_connected_at=_utcnow_naive().isoformat(),
            )
            try:
                while not self._shutdown:
                    try:
                        raw_message = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        continue
                    await self._touch_last_message(user_id)
                    message = json.loads(raw_message)
                    await self._handle_message(user_id, ws, message)
            finally:
                async with self._state_lock:
                    if self._ws_by_user.get(user_id) is ws:
                        self._ws_by_user.pop(user_id, None)

    async def _touch_last_message(self, user_id: int) -> None:
        await self._update_state(user_id, last_message_at=_utcnow_naive().isoformat())

    async def _handle_message(self, user_id: int, ws: WebSocketClientProtocol, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        if message_type == "connected":
            await self._update_state(
                user_id,
                tier=message.get("tier"),
                synced_addresses=list(message.get("addresses") or []),
            )
            return
        if message_type == "subscription_update":
            address = message.get("address")
            action = message.get("action")
            async with self._state_lock:
                state = self._state_for_user_unlocked(user_id)
                addresses = set(state.get("synced_addresses") or [])
                if address:
                    if action == "added":
                        addresses.add(address)
                    elif action == "removed":
                        addresses.discard(address)
                state["synced_addresses"] = sorted(addresses)
            return
        if message_type == "ping":
            await ws.send(json.dumps({"type": "pong"}))
            return
        if message_type == "error":
            detail = message.get("detail") or "Unknown upstream error"
            await self._update_state(
                user_id,
                status="auth_error" if "unauthor" in detail.lower() else "error",
                last_error=detail,
            )
            raise RuntimeError(detail)

        if message.get("version") == 1 and message.get("address") and message.get("event_type"):
            await self._process_wallet_event(user_id, message)

    async def _process_wallet_event(self, user_id: int, event: dict[str, Any]) -> None:
        if self._is_duplicate_event(user_id, event):
            return

        triggered_at = self._event_timestamp_to_naive_datetime(event.get("timestamp"))
        event_address = str(event.get("address") or "").strip().lower()
        event_type = str(event.get("event_type") or "").strip()
        callback_payloads: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []
        with SessionLocal() as db:
            pools = (
                db.query(SignalPool)
                .filter(
                    SignalPool.user_id == user_id,
                    SignalPool.enabled == True,  # noqa: E712
                    SignalPool.is_deleted != True,  # noqa: E712
                    SignalPool.source_type == WALLET_TRACKING_SOURCE,
                )
                .all()
            )

            for pool in pools:
                source_config = _parse_json_text(pool.source_config, {})
                if not isinstance(source_config, dict):
                    continue
                addresses = source_config.get("addresses") or []
                event_types = source_config.get("event_types") or []
                normalized_addresses = {
                    str(address).strip().lower()
                    for address in addresses
                    if isinstance(address, str) and address.strip()
                }
                if event_address not in normalized_addresses:
                    continue
                normalized_event_types = {
                    str(item).strip()
                    for item in event_types
                    if isinstance(item, str) and item.strip()
                }
                # Early test pools may still store "fill" from the raw realtime phase.
                # Treat aggregated position_change as a compatible successor so existing
                # wallet pools do not silently stop matching after the upstream cleanup.
                if event_type == "position_change" and "fill" in normalized_event_types:
                    normalized_event_types.add("position_change")
                if normalized_event_types and event_type not in normalized_event_types:
                    continue

                trigger_value = {
                    "source": "hyper_insight",
                    "source_type": WALLET_TRACKING_SOURCE,
                    "user_id": user_id,
                    "address": event_address,
                    "event_type": event_type,
                    "event_level": event.get("event_level"),
                    "tier": event.get("tier"),
                    "summary": event.get("summary"),
                    "detail": event.get("detail"),
                    "event_timestamp": event.get("timestamp"),
                }
                trigger_log = SignalTriggerLog(
                    signal_id=None,
                    pool_id=pool.id,
                    symbol=(event.get("symbol") or WALLET_TRIGGER_SYMBOL)[:20],
                    trigger_value=json.dumps(trigger_value),
                    triggered_at=triggered_at,
                    market_regime=None,
                )
                db.add(trigger_log)
                db.flush()
                callback_payloads.append(
                    (
                        user_id,
                        (event.get("symbol") or WALLET_TRIGGER_SYMBOL)[:20],
                        {
                            "pool_id": pool.id,
                            "pool_name": pool.pool_name,
                            "user_id": user_id,
                            "logic": pool.logic or "OR",
                            "trigger_log_id": trigger_log.id,
                            # Downstream consumers first identify this as a wallet-origin event,
                            # then normalize it back into the existing signal family where needed.
                            "trigger_type": "wallet_signal",
                            "wallet_event": trigger_value,
                            "signals_triggered": [],
                        },
                        {},
                    )
                )

            db.commit()

        await self._update_state(user_id, last_event_at=triggered_at.isoformat())

        if callback_payloads and self._callback_queue is not None:
            for payload in callback_payloads:
                try:
                    self._callback_queue.put_nowait(payload)
                except asyncio.QueueFull:
                    logger.warning(
                        "[HyperInsightWallet] Callback queue full; dropping wallet callback for user=%s pool=%s symbol=%s",
                        payload[0],
                        payload[2].get("pool_id"),
                        payload[1],
                    )

    def _event_timestamp_to_naive_datetime(self, timestamp_ms: Any) -> datetime:
        if isinstance(timestamp_ms, (int, float)) and timestamp_ms > 0:
            return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
        return _utcnow_naive()

    def _build_event_key(self, event: dict[str, Any]) -> str:
        detail = event.get("detail") or {}
        detail_hash = detail.get("hash") if isinstance(detail, dict) else None
        return "|".join(
            [
                str(event.get("address") or ""),
                str(event.get("event_type") or ""),
                str(event.get("timestamp") or ""),
                str(detail_hash or ""),
            ]
        )

    def _is_duplicate_event(self, user_id: int, event: dict[str, Any]) -> bool:
        key = self._build_event_key(event)
        keys = self._recent_event_keys.setdefault(user_id, deque(maxlen=MAX_RECENT_EVENT_KEYS))
        key_set = self._recent_event_key_sets.setdefault(user_id, set())
        if key in key_set:
            return True
        if len(keys) == keys.maxlen:
            oldest = keys.popleft()
            key_set.discard(oldest)
        keys.append(key)
        key_set.add(key)
        return False

    async def _close_ws(self, user_id: Optional[int] = None) -> None:
        user_ids = list(self._ws_by_user.keys()) if user_id is None else [user_id]
        for runtime_user_id in user_ids:
            ws = self._ws_by_user.pop(runtime_user_id, None)
            if ws is not None:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def _callback_worker_loop(self) -> None:
        from services.signal_detection_service import signal_detection_service

        while not self._shutdown:
            try:
                if self._callback_queue is None:
                    await asyncio.sleep(0.1)
                    continue
                user_id, symbol, pool_trigger, market_data = await self._callback_queue.get()
                try:
                    pool_trigger.setdefault("user_id", user_id)
                    await asyncio.to_thread(
                        signal_detection_service._notify_callbacks,
                        symbol,
                        pool_trigger,
                        market_data,
                    )
                finally:
                    self._callback_queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("[HyperInsightWallet] Callback worker error: %s", exc)

    def _state_for_user_unlocked(self, user_id: int) -> dict[str, Any]:
        if user_id not in self._states:
            self._states[user_id] = _default_state()
        return self._states[user_id]

    async def _update_state(self, user_id: int, **updates: Any) -> None:
        async with self._state_lock:
            self._state_for_user_unlocked(user_id).update(updates)


hyper_insight_wallet_service = HyperInsightWalletService()
