"""
AI Stream Service - Shared Infrastructure for AI Assistants

This module provides the common streaming infrastructure for all AI assistants:
- StreamBuffer: In-memory queue management with 15-minute expiration
- Background task management for decoupled frontend/backend communication
- Common message field handling (role, content, reasoning_snapshot, tool_calls_log, is_complete)

For new AI assistants, use this module as the foundation and only implement:
- Domain-specific tools
- Domain-specific result fields (e.g., prompt_result, signal_configs, code_suggestion)

Architecture (IMPORTANT - read before modifying any AI streaming code):

    The frontend and backend are FULLY DECOUPLED via an in-memory buffer.
    This is NOT a direct SSE long-connection. The flow is:

    1. Frontend POST /api/hyper-ai/chat -> Backend returns task_id immediately
    2. Backend spawns a background thread running the AI generator (e.g. stream_chat_response)
    3. Generator yields SSE-formatted strings -> run_ai_task_in_background() parses them
       and writes each event into StreamBufferManager (in-memory, keyed by task_id)
    4. Frontend polls GET /api/ai-stream/{task_id}?offset=N every 300ms to pull new events
    5. If frontend disconnects (page close/refresh), the background thread keeps running
       and events keep accumulating in the buffer (15-min expiry)
    6. Frontend reconnects -> resumes polling from last offset -> gets all missed events

    Key implication: ANY event yielded by the generator automatically becomes available
    to the frontend via polling. To add new event types (e.g. subagent progress), just
    yield them from the generator - no changes needed in this module.
"""
import asyncio
import json
import logging
import os
import socket
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional
from datetime import datetime, timedelta

from sqlalchemy import func

from database.connection import SessionLocal
from database.models import (
    AiStreamChunkRecord,
    AiStreamConfirmationRecord,
    AiStreamDispatchJobRecord,
    AiStreamTaskRecord,
)

logger = logging.getLogger(__name__)

# Buffer expiration time (15 minutes)
BUFFER_EXPIRATION_SECONDS = 15 * 60
AI_TASK_MAX_WORKERS = int(os.getenv("AI_TASK_MAX_WORKERS", "12"))
AI_BACKGROUND_MAX_WORKERS = int(os.getenv("AI_BACKGROUND_MAX_WORKERS", "4"))
AI_STREAM_MAX_RUNNING_GLOBAL = int(os.getenv("AI_STREAM_MAX_RUNNING_GLOBAL", str(AI_TASK_MAX_WORKERS)))
AI_STREAM_MAX_RUNNING_PER_USER = int(os.getenv("AI_STREAM_MAX_RUNNING_PER_USER", "2"))
AI_STREAM_PERSISTENCE_ENABLED = os.getenv("AI_STREAM_PERSISTENCE_ENABLED", "true").lower() == "true"
AI_STREAM_DB_RETENTION_SECONDS = int(os.getenv("AI_STREAM_DB_RETENTION_SECONDS", str(24 * 60 * 60)))
AI_STREAM_REDIS_URL = os.getenv("AI_STREAM_REDIS_URL", "").strip()
AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED = (
    os.getenv(
        "AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED",
        "true" if AI_STREAM_REDIS_URL else "false",
    ).lower() == "true"
)
AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN = (
    os.getenv("AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN", "false").lower() == "true"
)
AI_STREAM_DISTRIBUTED_ADMISSION_PREFIX = os.getenv(
    "AI_STREAM_DISTRIBUTED_ADMISSION_PREFIX",
    "hyperalpha:ai-stream",
).strip() or "hyperalpha:ai-stream"
AI_STREAM_DISTRIBUTED_LEASE_TTL_SECONDS = int(
    os.getenv("AI_STREAM_DISTRIBUTED_LEASE_TTL_SECONDS", str(BUFFER_EXPIRATION_SECONDS * 2))
)
AI_STREAM_RUNNER_ID = (
    os.getenv("AI_STREAM_RUNNER_ID", "").strip()
    or f"{socket.gethostname()}:{os.getpid()}"
)[:120]
AI_STREAM_DISTRIBUTED_WORKER_ENABLED = (
    os.getenv("AI_STREAM_DISTRIBUTED_WORKER_ENABLED", "false").lower() == "true"
)
AI_STREAM_DISPATCH_MAX_ATTEMPTS = int(os.getenv("AI_STREAM_DISPATCH_MAX_ATTEMPTS", "1"))
AI_STREAM_DISPATCH_POLL_INTERVAL_SECONDS = float(
    os.getenv("AI_STREAM_DISPATCH_POLL_INTERVAL_SECONDS", "1.0")
)

_ai_task_executor = ThreadPoolExecutor(
    max_workers=AI_TASK_MAX_WORKERS,
    thread_name_prefix="ai-task",
)
_ai_background_executor = ThreadPoolExecutor(
    max_workers=AI_BACKGROUND_MAX_WORKERS,
    thread_name_prefix="ai-bg",
)


@dataclass
class StreamChunk:
    """A single chunk in the stream buffer."""
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class StreamTask:
    """Represents a streaming task with its buffer and metadata."""
    task_id: str
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None
    status: str = "running"  # running, completed, error
    chunks: List[StreamChunk] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    # Accumulated data for database persistence
    reasoning_parts: List[str] = field(default_factory=list)
    tool_calls_log: List[Dict[str, Any]] = field(default_factory=list)
    final_content: str = ""

    # Runtime checkpoint state for Hyper AI high-risk tool confirmations
    confirmation_event: threading.Event = field(default_factory=threading.Event)
    confirmation_response: Optional[Dict[str, Any]] = field(default=None)
    pending_confirmation_id: Optional[str] = field(default=None)
    distributed_admission_acquired: bool = False
    remote_hydrated: bool = False


class TaskAdmissionError(RuntimeError):
    """Raised when the AI stream runtime refuses a new task for capacity reasons."""

    def __init__(self, message: str, scope: str, limit: int, running: int):
        super().__init__(message)
        self.scope = scope
        self.limit = limit
        self.running = running

    def to_response(self) -> Dict[str, Any]:
        return {
            "message": str(self),
            "scope": self.scope,
            "limit": self.limit,
            "running": self.running,
        }


class DistributedAdmissionController:
    """
    Optional Redis-backed task admission controller.

    It stores running task leases in Redis sorted sets so multiple backend
    instances share the same global/per-user capacity counters. The in-memory
    StreamBufferManager remains the source of buffered chunks for this process.
    """

    _ACQUIRE_SCRIPT = """
local global_key = KEYS[1]
local user_key = KEYS[2]
local task_id = ARGV[1]
local now = tonumber(ARGV[2])
local expires_at = tonumber(ARGV[3])
local global_limit = tonumber(ARGV[4])
local user_limit = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', global_key, '-inf', now)
local has_user = user_key ~= nil and user_key ~= '' and user_limit > 0
if has_user then
  redis.call('ZREMRANGEBYSCORE', user_key, '-inf', now)
end

local global_running = redis.call('ZCARD', global_key)
if global_limit > 0 and global_running >= global_limit then
  return {0, 'global', global_limit, global_running}
end

local user_running = 0
if has_user then
  user_running = redis.call('ZCARD', user_key)
  if user_running >= user_limit then
    return {0, 'user', user_limit, user_running}
  end
end

redis.call('ZADD', global_key, expires_at, task_id)
if has_user then
  redis.call('ZADD', user_key, expires_at, task_id)
end

return {1, 'accepted', global_limit, global_running + 1, user_limit, user_running + 1}
"""

    def __init__(
        self,
        redis_url: str,
        prefix: str,
        lease_ttl_seconds: int,
        fail_open: bool = False,
    ):
        self.redis_url = redis_url
        self.prefix = prefix.rstrip(":")
        self.lease_ttl_seconds = lease_ttl_seconds
        self.fail_open = fail_open
        self._client = None
        self._client_lock = threading.Lock()
        self._available = False
        self._last_error: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return bool(self.redis_url)

    def _global_key(self) -> str:
        return f"{self.prefix}:running:global"

    def _user_key(self, user_id: Optional[int]) -> str:
        return f"{self.prefix}:running:user:{user_id}"

    def _get_client(self):
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is not None:
                return self._client
            try:
                import redis  # type: ignore
                self._client = redis.Redis.from_url(
                    self.redis_url,
                    socket_timeout=2,
                    socket_connect_timeout=2,
                    decode_responses=True,
                )
                self._client.ping()
                self._available = True
                self._last_error = None
                return self._client
            except Exception as exc:
                self._available = False
                self._last_error = str(exc)
                if self.fail_open:
                    logger.warning(
                        "[StreamBuffer] Redis admission unavailable; falling back to local admission: %s",
                        exc,
                    )
                    return None
                raise TaskAdmissionError(
                    "Distributed AI task admission is unavailable. Please retry later.",
                    scope="distributed",
                    limit=0,
                    running=0,
                ) from exc

    def acquire(self, task_id: str, user_id: Optional[int]) -> bool:
        client = self._get_client()
        if client is None:
            return False

        now = time.time()
        expires_at = now + max(1, self.lease_ttl_seconds)
        user_key = self._user_key(user_id) if user_id is not None else f"{self.prefix}:running:user:none"
        try:
            result = client.eval(
                self._ACQUIRE_SCRIPT,
                2,
                self._global_key(),
                user_key,
                task_id,
                now,
                expires_at,
                AI_STREAM_MAX_RUNNING_GLOBAL,
                AI_STREAM_MAX_RUNNING_PER_USER if user_id is not None else 0,
            )
            accepted = int(result[0]) == 1
            if accepted:
                self._available = True
                self._last_error = None
                return True
            scope = str(result[1])
            limit = int(result[2])
            running = int(result[3])
            message = (
                "AI task capacity is full. Please retry after an existing task finishes."
                if scope == "global"
                else "You already have too many AI tasks running. Please wait for one to finish."
            )
            raise TaskAdmissionError(message, scope=scope, limit=limit, running=running)
        except TaskAdmissionError:
            raise
        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            if self.fail_open:
                logger.warning(
                    "[StreamBuffer] Redis admission acquire failed; falling back to local admission: %s",
                    exc,
                )
                return False
            raise TaskAdmissionError(
                "Distributed AI task admission is unavailable. Please retry later.",
                scope="distributed",
                limit=0,
                running=0,
            ) from exc

    def refresh(self, task_id: str, user_id: Optional[int]) -> None:
        try:
            client = self._get_client()
        except Exception as exc:
            logger.warning("[StreamBuffer] Redis admission refresh unavailable for %s: %s", task_id, exc)
            return
        if client is None:
            return
        expires_at = time.time() + max(1, self.lease_ttl_seconds)
        try:
            client.zadd(self._global_key(), {task_id: expires_at}, xx=True)
            if user_id is not None:
                client.zadd(self._user_key(user_id), {task_id: expires_at}, xx=True)
        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            logger.warning("[StreamBuffer] Failed to refresh Redis admission lease %s: %s", task_id, exc)

    def release(self, task_id: str, user_id: Optional[int]) -> None:
        try:
            client = self._get_client()
        except Exception as exc:
            logger.warning("[StreamBuffer] Redis admission release unavailable for %s: %s", task_id, exc)
            return
        if client is None:
            return
        try:
            keys = [self._global_key()]
            if user_id is not None:
                keys.append(self._user_key(user_id))
            for key in keys:
                client.zrem(key, task_id)
        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            logger.warning("[StreamBuffer] Failed to release Redis admission lease %s: %s", task_id, exc)

    def cleanup_expired(self) -> None:
        try:
            client = self._get_client()
        except Exception as exc:
            logger.warning("[StreamBuffer] Redis admission cleanup unavailable: %s", exc)
            return
        if client is None:
            return
        now = time.time()
        try:
            client.zremrangebyscore(self._global_key(), "-inf", now)
        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            logger.warning("[StreamBuffer] Failed to cleanup Redis admission leases: %s", exc)

    def has_active_lease(self, task_id: str, user_id: Optional[int]) -> bool:
        try:
            client = self._get_client()
        except Exception as exc:
            logger.warning("[StreamBuffer] Redis admission lease check unavailable for %s: %s", task_id, exc)
            return False
        if client is None:
            return False
        now = time.time()
        try:
            client.zremrangebyscore(self._global_key(), "-inf", now)
            score = client.zscore(self._global_key(), task_id)
            if score is None or float(score) <= now:
                return False
            if user_id is not None:
                client.zremrangebyscore(self._user_key(user_id), "-inf", now)
                user_score = client.zscore(self._user_key(user_id), task_id)
                return user_score is not None and float(user_score) > now
            return True
        except Exception as exc:
            self._available = False
            self._last_error = str(exc)
            logger.warning("[StreamBuffer] Failed to check Redis admission lease %s: %s", task_id, exc)
            return False

    def stats(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "enabled": self.enabled,
            "available": self._available,
            "prefix": self.prefix,
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "fail_open": self.fail_open,
            "last_error": self._last_error,
        }
        if not self.enabled:
            return data
        try:
            client = self._get_client()
            if client is not None:
                self.cleanup_expired()
                data["running_tasks"] = int(client.zcard(self._global_key()) or 0)
                data["available"] = True
                data["last_error"] = None
        except Exception:
            data["available"] = self._available
            data["last_error"] = self._last_error
        return data


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _json_loads_dict(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


@dataclass
class AiStreamDispatchJob:
    """Serializable AI stream worker job claimed from the persistent queue."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    attempts: int = 0


_ai_stream_task_handlers: Dict[
    str,
    Callable[[AiStreamDispatchJob], Generator[str, None, None]],
] = {}


def register_ai_stream_task_handler(
    task_type: str,
    handler: Callable[[AiStreamDispatchJob], Generator[str, None, None]],
) -> None:
    """Register a serializable AI stream task handler for distributed workers."""
    if not task_type:
        raise ValueError("task_type is required")
    _ai_stream_task_handlers[task_type] = handler


def is_ai_stream_dispatch_enabled() -> bool:
    """Return whether serialized AI stream dispatch is enabled."""
    return AI_STREAM_DISTRIBUTED_WORKER_ENABLED and AI_STREAM_PERSISTENCE_ENABLED


class StreamBufferManager:
    """
    Manages stream buffers for all active AI tasks.

    Thread-safe singleton that handles:
    - Creating and tracking stream tasks
    - Adding chunks to task buffers
    - Retrieving chunks with offset support
    - Automatic cleanup of expired tasks
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._tasks: Dict[str, StreamTask] = {}
        self._tasks_lock = threading.Lock()
        self._cleanup_thread = None
        self._dispatch_thread = None
        self._running = True
        self._admission_controller = self._build_distributed_admission_controller()
        self._start_cleanup_thread()
        self._start_dispatch_worker()
        self._initialized = True

    def _build_distributed_admission_controller(self) -> Optional[DistributedAdmissionController]:
        if not AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED or not AI_STREAM_REDIS_URL:
            return None
        return DistributedAdmissionController(
            redis_url=AI_STREAM_REDIS_URL,
            prefix=AI_STREAM_DISTRIBUTED_ADMISSION_PREFIX,
            lease_ttl_seconds=AI_STREAM_DISTRIBUTED_LEASE_TTL_SECONDS,
            fail_open=AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN,
        )

    def _has_active_distributed_lease(self, task_id: str, user_id: Optional[int]) -> bool:
        if not self._admission_controller:
            return False
        return self._admission_controller.has_active_lease(task_id, user_id)

    def _persist_task(self, task: StreamTask) -> None:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return

        db = SessionLocal()
        try:
            record = db.query(AiStreamTaskRecord).filter(
                AiStreamTaskRecord.task_id == task.task_id
            ).first()
            if not record:
                record = AiStreamTaskRecord(
                    task_id=task.task_id,
                    user_id=task.user_id,
                    conversation_id=task.conversation_id,
                    created_at_epoch=task.created_at,
                )
                db.add(record)

            record.user_id = task.user_id
            record.conversation_id = task.conversation_id
            record.status = task.status
            record.runner_id = AI_STREAM_RUNNER_ID
            record.last_heartbeat_epoch = time.time()
            record.result = _json_dumps(task.result) if task.result is not None else None
            record.error_message = task.error_message
            record.created_at_epoch = task.created_at
            record.completed_at_epoch = task.completed_at
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("[StreamBuffer] Failed to persist task %s: %s", task.task_id, exc)
        finally:
            db.close()

    def _persist_chunk(self, task_id: str, chunk_index: int, chunk: StreamChunk) -> None:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return

        db = SessionLocal()
        try:
            task_record = db.query(AiStreamTaskRecord).filter(
                AiStreamTaskRecord.task_id == task_id
            ).first()
            if task_record and task_record.status == "running":
                task_record.runner_id = AI_STREAM_RUNNER_ID
                task_record.last_heartbeat_epoch = chunk.timestamp

            existing = db.query(AiStreamChunkRecord.id).filter(
                AiStreamChunkRecord.task_id == task_id,
                AiStreamChunkRecord.chunk_index == chunk_index,
            ).first()
            if not existing:
                db.add(AiStreamChunkRecord(
                    task_id=task_id,
                    chunk_index=chunk_index,
                    event_type=chunk.event_type,
                    data=_json_dumps(chunk.data),
                    timestamp_epoch=chunk.timestamp,
                ))
                db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("[StreamBuffer] Failed to persist chunk %s/%s: %s", task_id, chunk_index, exc)
        finally:
            db.close()

    def _begin_persisted_confirmation(self, task: StreamTask, confirmation_id: str) -> bool:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return True

        db = SessionLocal()
        try:
            pending = db.query(AiStreamConfirmationRecord).filter(
                AiStreamConfirmationRecord.task_id == task.task_id,
                AiStreamConfirmationRecord.status == "pending",
            ).first()
            if pending and pending.confirmation_id != confirmation_id:
                return False

            record = pending or db.query(AiStreamConfirmationRecord).filter(
                AiStreamConfirmationRecord.task_id == task.task_id,
                AiStreamConfirmationRecord.confirmation_id == confirmation_id,
            ).first()
            if not record:
                record = AiStreamConfirmationRecord(
                    task_id=task.task_id,
                    user_id=task.user_id,
                    confirmation_id=confirmation_id,
                    created_at_epoch=time.time(),
                )
                db.add(record)

            record.user_id = task.user_id
            record.status = "pending"
            record.confirmed = None
            record.response = None
            record.submitted_at_epoch = None
            record.cleared_at_epoch = None
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.warning(
                "[StreamBuffer] Failed to persist confirmation begin %s/%s: %s",
                task.task_id,
                confirmation_id,
                exc,
            )
            return False
        finally:
            db.close()

    def _submit_persisted_confirmation(
        self,
        task_id: str,
        confirmation_id: str,
        confirmed: bool,
        user_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return None

        db = SessionLocal()
        try:
            task_record = db.query(AiStreamTaskRecord).filter(
                AiStreamTaskRecord.task_id == task_id,
            ).first()
            if not task_record or task_record.status != "running":
                return None
            if user_id is not None and task_record.user_id != user_id:
                return None

            record = db.query(AiStreamConfirmationRecord).filter(
                AiStreamConfirmationRecord.task_id == task_id,
                AiStreamConfirmationRecord.confirmation_id == confirmation_id,
            ).first()
            if not record or record.status != "pending":
                return None
            if user_id is not None and record.user_id != user_id:
                return None

            submitted_at = time.time()
            response = {
                "confirmation_id": confirmation_id,
                "confirmed": bool(confirmed),
                "submitted_at": submitted_at,
            }
            record.status = "confirmed" if confirmed else "cancelled"
            record.confirmed = bool(confirmed)
            record.submitted_at_epoch = submitted_at
            record.response = _json_dumps(response)
            db.commit()
            return response
        except Exception as exc:
            db.rollback()
            logger.warning(
                "[StreamBuffer] Failed to persist confirmation submit %s/%s: %s",
                task_id,
                confirmation_id,
                exc,
            )
            return None
        finally:
            db.close()

    def _get_persisted_confirmation_response(
        self,
        task_id: str,
        confirmation_id: str,
    ) -> Optional[Dict[str, Any]]:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return None

        db = SessionLocal()
        try:
            record = db.query(AiStreamConfirmationRecord).filter(
                AiStreamConfirmationRecord.task_id == task_id,
                AiStreamConfirmationRecord.confirmation_id == confirmation_id,
            ).first()
            if not record or record.status not in {"confirmed", "cancelled"}:
                return None

            response = _json_loads_dict(record.response)
            if not response:
                response = {
                    "confirmation_id": confirmation_id,
                    "confirmed": record.status == "confirmed",
                    "submitted_at": record.submitted_at_epoch or time.time(),
                }
            response["confirmation_id"] = confirmation_id
            response["confirmed"] = record.status == "confirmed" and bool(record.confirmed)
            if record.submitted_at_epoch is not None:
                response["submitted_at"] = record.submitted_at_epoch
            return response
        except Exception as exc:
            logger.warning(
                "[StreamBuffer] Failed to read confirmation response %s/%s: %s",
                task_id,
                confirmation_id,
                exc,
            )
            return None
        finally:
            db.close()

    def _clear_persisted_confirmation(self, task_id: str, confirmation_id: str) -> None:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return

        db = SessionLocal()
        try:
            record = db.query(AiStreamConfirmationRecord).filter(
                AiStreamConfirmationRecord.task_id == task_id,
                AiStreamConfirmationRecord.confirmation_id == confirmation_id,
            ).first()
            if record and record.status == "pending":
                record.status = "cleared"
                record.confirmed = False
                record.cleared_at_epoch = time.time()
                db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning(
                "[StreamBuffer] Failed to clear persisted confirmation %s/%s: %s",
                task_id,
                confirmation_id,
                exc,
            )
        finally:
            db.close()

    def _hydrate_task_from_db(self, task_id: str, user_id: Optional[int] = None) -> Optional[StreamTask]:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return None

        db = SessionLocal()
        try:
            record = db.query(AiStreamTaskRecord).filter(
                AiStreamTaskRecord.task_id == task_id
            ).first()
            if not record:
                return None
            if user_id is not None and record.user_id != user_id:
                return None

            remote_running = False
            if record.status == "running":
                remote_running = self._has_active_distributed_lease(record.task_id, record.user_id)
            if record.status == "running" and not remote_running:
                record.status = "error"
                record.error_message = "Task interrupted by service restart"
                record.completed_at_epoch = time.time()
                db.commit()

            rows = db.query(AiStreamChunkRecord).filter(
                AiStreamChunkRecord.task_id == task_id
            ).order_by(AiStreamChunkRecord.chunk_index.asc()).all()
            task = StreamTask(
                task_id=record.task_id,
                conversation_id=record.conversation_id,
                user_id=record.user_id,
                status=record.status,
                created_at=record.created_at_epoch,
                completed_at=record.completed_at_epoch,
                error_message=record.error_message,
                result=_json_loads_dict(record.result),
                chunks=[
                    StreamChunk(
                        event_type=row.event_type,
                        data=_json_loads_dict(row.data),
                        timestamp=row.timestamp_epoch,
                    )
                    for row in rows
                ],
            )
            task.remote_hydrated = remote_running
            self._tasks[task_id] = task
            return task
        except Exception as exc:
            logger.warning("[StreamBuffer] Failed to hydrate task %s: %s", task_id, exc)
            return None
        finally:
            db.close()

    def _hydrate_pending_task_for_conversation(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[StreamTask]:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return None

        db = SessionLocal()
        try:
            query = db.query(AiStreamTaskRecord.task_id).filter(
                AiStreamTaskRecord.conversation_id == conversation_id,
                AiStreamTaskRecord.status == "running",
            )
            if user_id is not None:
                query = query.filter(AiStreamTaskRecord.user_id == user_id)

            rows = query.order_by(AiStreamTaskRecord.created_at_epoch.desc()).all()
        except Exception as exc:
            logger.warning(
                "[StreamBuffer] Failed to find pending task for conversation %s: %s",
                conversation_id,
                exc,
            )
            return None
        finally:
            db.close()

        for row in rows:
            task = self._hydrate_task_from_db(row[0], user_id=user_id)
            if task and task.status == "running":
                return task
        return None

    def _cleanup_persistent_tasks(self, now: float) -> None:
        if not AI_STREAM_PERSISTENCE_ENABLED or AI_STREAM_DB_RETENTION_SECONDS <= 0:
            return

        cutoff = now - AI_STREAM_DB_RETENTION_SECONDS
        db = SessionLocal()
        try:
            old_task_ids = [
                row[0]
                for row in db.query(AiStreamTaskRecord.task_id).filter(
                    AiStreamTaskRecord.completed_at_epoch.isnot(None),
                    AiStreamTaskRecord.completed_at_epoch < cutoff,
                ).all()
            ]
            if not old_task_ids:
                return

            db.query(AiStreamChunkRecord).filter(
                AiStreamChunkRecord.task_id.in_(old_task_ids)
            ).delete(synchronize_session=False)
            db.query(AiStreamTaskRecord).filter(
                AiStreamTaskRecord.task_id.in_(old_task_ids)
            ).delete(synchronize_session=False)
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("[StreamBuffer] Failed to cleanup persistent tasks: %s", exc)
        finally:
            db.close()

    def _start_cleanup_thread(self):
        """Start background thread for cleaning up expired tasks."""
        def cleanup_loop():
            while self._running:
                try:
                    self._cleanup_expired_tasks()
                except Exception as e:
                    logger.error(f"[StreamBuffer] Cleanup error: {e}")
                time.sleep(60)  # Check every minute

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _start_dispatch_worker(self):
        """Start a lightweight polling worker for serialized AI stream jobs."""
        if not is_ai_stream_dispatch_enabled():
            return
        if self._dispatch_thread and self._dispatch_thread.is_alive():
            return

        self._dispatch_thread = threading.Thread(
            target=self._dispatch_worker_loop,
            daemon=True,
            name=f"ai-dispatch-{AI_STREAM_RUNNER_ID}",
        )
        self._dispatch_thread.start()

    def _dispatch_worker_loop(self):
        while self._running:
            try:
                task_types = set(_ai_stream_task_handlers.keys())
                if not task_types:
                    time.sleep(AI_STREAM_DISPATCH_POLL_INTERVAL_SECONDS)
                    continue

                job = self.claim_dispatch_job(task_types)
                if job:
                    _ai_task_executor.submit(run_ai_stream_dispatch_job, job)
                else:
                    time.sleep(AI_STREAM_DISPATCH_POLL_INTERVAL_SECONDS)
            except Exception as exc:
                logger.warning("[StreamBuffer] Dispatch worker loop error: %s", exc)
                time.sleep(AI_STREAM_DISPATCH_POLL_INTERVAL_SECONDS)

    def _cleanup_expired_tasks(self):
        """Remove tasks that have been completed for more than 15 minutes."""
        now = time.time()
        expired_ids = []

        with self._tasks_lock:
            for task_id, task in self._tasks.items():
                # Only clean up completed/error tasks after expiration
                if task.status in ("completed", "error"):
                    if task.completed_at and (now - task.completed_at) > BUFFER_EXPIRATION_SECONDS:
                        expired_ids.append(task_id)
                # Also clean up very old running tasks (stuck tasks, > 30 minutes)
                elif (now - task.created_at) > BUFFER_EXPIRATION_SECONDS * 2:
                    expired_ids.append(task_id)

            for task_id in expired_ids:
                del self._tasks[task_id]
                logger.debug(f"[StreamBuffer] Cleaned up expired task: {task_id}")

        self._cleanup_persistent_tasks(now)
        if self._admission_controller:
            self._admission_controller.cleanup_expired()

    def create_task(
        self,
        task_id: str,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None,
        enforce_limits: bool = True,
    ) -> StreamTask:
        """Create a new stream task."""
        with self._tasks_lock:
            if task_id in self._tasks:
                logger.warning(f"[StreamBuffer] Task {task_id} already exists, overwriting")
            distributed_admission_acquired = False
            try:
                if enforce_limits:
                    if self._admission_controller:
                        distributed_admission_acquired = self._admission_controller.acquire(task_id, user_id)
                    self._assert_task_capacity(user_id)
                task = StreamTask(task_id=task_id, conversation_id=conversation_id, user_id=user_id)
                task.distributed_admission_acquired = distributed_admission_acquired
                self._tasks[task_id] = task
                self._persist_task(task)
                return task
            except Exception:
                if self._admission_controller and distributed_admission_acquired:
                    self._admission_controller.release(task_id, user_id)
                raise

    def _release_task_admission(self, task: StreamTask) -> None:
        if self._admission_controller and task.distributed_admission_acquired:
            self._admission_controller.release(task.task_id, task.user_id)
            task.distributed_admission_acquired = False

    def _running_task_counts(self, user_id: Optional[int] = None) -> tuple[int, int]:
        global_running = 0
        user_running = 0
        for task in self._tasks.values():
            if task.status != "running":
                continue
            global_running += 1
            if user_id is not None and task.user_id == user_id:
                user_running += 1
        return global_running, user_running

    def _assert_task_capacity(self, user_id: Optional[int]) -> None:
        global_running, user_running = self._running_task_counts(user_id)
        if AI_STREAM_MAX_RUNNING_GLOBAL > 0 and global_running >= AI_STREAM_MAX_RUNNING_GLOBAL:
            raise TaskAdmissionError(
                "AI task capacity is full. Please retry after an existing task finishes.",
                scope="global",
                limit=AI_STREAM_MAX_RUNNING_GLOBAL,
                running=global_running,
            )
        if (
            user_id is not None
            and AI_STREAM_MAX_RUNNING_PER_USER > 0
            and user_running >= AI_STREAM_MAX_RUNNING_PER_USER
        ):
            raise TaskAdmissionError(
                "You already have too many AI tasks running. Please wait for one to finish.",
                scope="user",
                limit=AI_STREAM_MAX_RUNNING_PER_USER,
                running=user_running,
            )

    def get_task(self, task_id: str, user_id: Optional[int] = None) -> Optional[StreamTask]:
        """Get a task by ID."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task and task.remote_hydrated and task.status == "running":
                task = self._hydrate_task_from_db(task_id, user_id=user_id)
            if not task:
                task = self._hydrate_task_from_db(task_id, user_id=user_id)
            if not task:
                return None
            if user_id is not None and task.user_id != user_id:
                return None
            return task

    def adopt_task_for_dispatch(
        self,
        task_id: str,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> StreamTask:
        """Attach this runner to a persisted dispatch task without re-admitting capacity."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                return task

            task = self._hydrate_task_from_db(task_id, user_id=user_id)
            if task and task.status == "running":
                task.remote_hydrated = False
                task.distributed_admission_acquired = self._has_active_distributed_lease(task_id, task.user_id)
                self._tasks[task_id] = task
                self._persist_task(task)
                return task

            task = StreamTask(
                task_id=task_id,
                conversation_id=conversation_id,
                user_id=user_id,
            )
            task.distributed_admission_acquired = self._has_active_distributed_lease(task_id, user_id)
            self._tasks[task_id] = task
            self._persist_task(task)
            return task

    def add_chunk(self, task_id: str, event_type: str, data: Dict[str, Any]):
        """Add a chunk to a task's buffer."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                chunk_index = len(task.chunks)
                chunk = StreamChunk(event_type=event_type, data=data)
                task.chunks.append(chunk)
                if self._admission_controller and task.distributed_admission_acquired:
                    self._admission_controller.refresh(task_id, task.user_id)
                self._persist_chunk(task_id, chunk_index, chunk)

    def get_chunks(
        self,
        task_id: str,
        offset: int = 0,
        user_id: Optional[int] = None,
    ) -> tuple[List[StreamChunk], str]:
        """
        Get chunks from a task starting at offset.
        Returns (chunks, status).
        """
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task and task.remote_hydrated and task.status == "running":
                task = self._hydrate_task_from_db(task_id, user_id=user_id)
            if not task:
                task = self._hydrate_task_from_db(task_id, user_id=user_id)
            if not task:
                return [], "not_found"
            if user_id is not None and task.user_id != user_id:
                return [], "not_found"
            return task.chunks[offset:], task.status

    def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None):
        """Mark a task as completed."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "completed"
                task.completed_at = time.time()
                task.result = result
                self._release_task_admission(task)
                self._persist_task(task)

    def fail_task(self, task_id: str, error_message: str):
        """Mark a task as failed."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "error"
                task.completed_at = time.time()
                task.error_message = error_message
                self._release_task_admission(task)
                self._persist_task(task)

    def update_task_data(self, task_id: str, **kwargs):
        """Update task accumulated data (reasoning_parts, tool_calls_log, etc.)."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

    def submit_confirmation(
        self,
        task_id: str,
        confirmation_id: str,
        confirmed: bool,
        user_id: Optional[int] = None,
    ) -> bool:
        """Submit a user response for a pending runtime checkpoint."""
        persisted_response = self._submit_persisted_confirmation(
            task_id,
            confirmation_id,
            confirmed,
            user_id=user_id,
        )
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "running":
                return persisted_response is not None
            if user_id is not None and task.user_id != user_id:
                return persisted_response is not None
            if not task.pending_confirmation_id:
                return persisted_response is not None
            if task.pending_confirmation_id != confirmation_id:
                return persisted_response is not None
            task.confirmation_response = persisted_response or {
                "confirmation_id": confirmation_id,
                "confirmed": bool(confirmed),
                "submitted_at": time.time(),
            }
            task.confirmation_event.set()
            return True

    def begin_confirmation(self, task_id: str, confirmation_id: str) -> bool:
        """Start a pending runtime checkpoint for a task."""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "running":
                return False
            if task.pending_confirmation_id:
                return False
            if not self._begin_persisted_confirmation(task, confirmation_id):
                return False
            task.confirmation_response = None
            task.pending_confirmation_id = confirmation_id
            task.confirmation_event.clear()
            return True

    def wait_for_confirmation(
        self,
        task_id: str,
        confirmation_id: str,
        timeout_seconds: float = 300,
        poll_interval: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """Wait for a confirmation response from local memory or the DB mailbox."""
        deadline = time.time() + max(0, timeout_seconds)
        poll_interval = max(0.05, poll_interval)

        while True:
            with self._tasks_lock:
                task = self._tasks.get(task_id)
                if (
                    not task
                    or task.status != "running"
                    or task.pending_confirmation_id != confirmation_id
                ):
                    return None
                if task.confirmation_response:
                    return task.confirmation_response
                confirmation_event = task.confirmation_event

            remaining = deadline - time.time()
            if remaining <= 0:
                return None

            if confirmation_event.wait(timeout=min(poll_interval, remaining)):
                with self._tasks_lock:
                    task = self._tasks.get(task_id)
                    if task and task.confirmation_response:
                        return task.confirmation_response

            response = self._get_persisted_confirmation_response(task_id, confirmation_id)
            if response:
                with self._tasks_lock:
                    task = self._tasks.get(task_id)
                    if task and task.pending_confirmation_id == confirmation_id:
                        task.confirmation_response = response
                        task.confirmation_event.set()
                return response

    def clear_confirmation(self, task_id: str, confirmation_id: Optional[str] = None):
        """Clear pending runtime checkpoint state."""
        should_clear_persisted = False
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task:
                should_clear_persisted = bool(confirmation_id)
            elif confirmation_id and task.pending_confirmation_id != confirmation_id:
                return
            else:
                should_clear_persisted = bool(task.pending_confirmation_id)
                task.confirmation_response = None
                task.pending_confirmation_id = None
                task.confirmation_event.clear()

        if should_clear_persisted and confirmation_id:
            self._clear_persisted_confirmation(task_id, confirmation_id)

    def get_pending_task_for_conversation(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[StreamTask]:
        """Check if there's a running task for a conversation."""
        with self._tasks_lock:
            for task in self._tasks.values():
                if (
                    task.conversation_id == conversation_id
                    and task.status == "running"
                    and (user_id is None or task.user_id == user_id)
                ):
                    return task
            return self._hydrate_pending_task_for_conversation(conversation_id, user_id=user_id)

    def get_persistent_running_snapshot(self, local_running_task_ids: set[str]) -> Dict[str, Any]:
        """Summarize DB/Redis running task state for admin runtime visibility."""
        snapshot: Dict[str, Any] = {
            "persisted_running_tasks": 0,
            "remote_running_tasks": 0,
            "stale_running_tasks": 0,
            "users": {},
        }
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return snapshot

        db = SessionLocal()
        try:
            rows = db.query(
                AiStreamTaskRecord.task_id,
                AiStreamTaskRecord.user_id,
                AiStreamTaskRecord.created_at_epoch,
            ).filter(
                AiStreamTaskRecord.status == "running",
            ).all()
        except Exception as exc:
            logger.warning("[StreamBuffer] Failed to collect persistent running snapshot: %s", exc)
            return snapshot
        finally:
            db.close()

        now = time.time()
        for task_id, user_id, created_at_epoch in rows:
            is_local = task_id in local_running_task_ids
            has_active_lease = self._has_active_distributed_lease(task_id, user_id)
            is_remote = bool(has_active_lease and not is_local)
            is_stale = bool(self._admission_controller and not has_active_lease and not is_local)
            age_seconds = max(0, int(now - (created_at_epoch or now)))

            snapshot["persisted_running_tasks"] += 1
            if is_remote:
                snapshot["remote_running_tasks"] += 1
            if is_stale:
                snapshot["stale_running_tasks"] += 1

            entry = snapshot["users"].setdefault(user_id, {
                "user_id": user_id,
                "persisted_running_tasks": 0,
                "remote_running_tasks": 0,
                "stale_running_tasks": 0,
                "oldest_persisted_running_age_seconds": None,
            })
            entry["persisted_running_tasks"] += 1
            if is_remote:
                entry["remote_running_tasks"] += 1
            if is_stale:
                entry["stale_running_tasks"] += 1
            current_oldest = entry["oldest_persisted_running_age_seconds"]
            if current_oldest is None or age_seconds > current_oldest:
                entry["oldest_persisted_running_age_seconds"] = age_seconds
        return snapshot

    def enqueue_dispatch_job(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        max_attempts: Optional[int] = None,
    ) -> bool:
        """Persist a serializable AI stream job for a distributed worker."""
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return False

        db = SessionLocal()
        try:
            existing = db.query(AiStreamDispatchJobRecord).filter(
                AiStreamDispatchJobRecord.task_id == task_id
            ).first()
            if existing:
                return existing.status in {"pending", "claimed", "running"}

            db.add(AiStreamDispatchJobRecord(
                task_id=task_id,
                task_type=task_type,
                user_id=user_id,
                conversation_id=conversation_id,
                status="pending",
                payload=_json_dumps(payload or {}),
                attempts=0,
                max_attempts=max_attempts or AI_STREAM_DISPATCH_MAX_ATTEMPTS,
                created_at_epoch=time.time(),
            ))
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.warning("[StreamBuffer] Failed to enqueue dispatch job %s: %s", task_id, exc)
            return False
        finally:
            db.close()

    def claim_dispatch_job(
        self,
        supported_task_types: Optional[set[str]] = None,
    ) -> Optional[AiStreamDispatchJob]:
        """Claim one pending serializable AI stream job for this runner."""
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return None

        db = SessionLocal()
        try:
            query = db.query(AiStreamDispatchJobRecord).filter(
                AiStreamDispatchJobRecord.status == "pending",
                AiStreamDispatchJobRecord.attempts < AiStreamDispatchJobRecord.max_attempts,
            )
            if supported_task_types:
                query = query.filter(AiStreamDispatchJobRecord.task_type.in_(supported_task_types))

            record = query.order_by(
                AiStreamDispatchJobRecord.created_at_epoch.asc()
            ).with_for_update(skip_locked=True).first()
            if not record:
                return None

            record.status = "claimed"
            record.runner_id = AI_STREAM_RUNNER_ID
            record.attempts = int(record.attempts or 0) + 1
            record.claimed_at_epoch = time.time()
            db.commit()
            return AiStreamDispatchJob(
                task_id=record.task_id,
                task_type=record.task_type,
                payload=_json_loads_dict(record.payload),
                user_id=record.user_id,
                conversation_id=record.conversation_id,
                attempts=record.attempts,
            )
        except Exception as exc:
            db.rollback()
            logger.warning("[StreamBuffer] Failed to claim dispatch job: %s", exc)
            return None
        finally:
            db.close()

    def mark_dispatch_job_running(self, task_id: str) -> None:
        self._update_dispatch_job_status(task_id, "running")

    def complete_dispatch_job(self, task_id: str) -> None:
        self._update_dispatch_job_status(task_id, "completed", completed=True)

    def fail_dispatch_job(self, task_id: str, error_message: str) -> None:
        self._update_dispatch_job_status(task_id, "failed", error_message=error_message, completed=True)

    def _update_dispatch_job_status(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
        completed: bool = False,
    ) -> None:
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return

        db = SessionLocal()
        try:
            record = db.query(AiStreamDispatchJobRecord).filter(
                AiStreamDispatchJobRecord.task_id == task_id
            ).first()
            if not record:
                return
            record.status = status
            record.runner_id = AI_STREAM_RUNNER_ID
            record.error_message = error_message
            if completed:
                record.completed_at_epoch = time.time()
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("[StreamBuffer] Failed to update dispatch job %s: %s", task_id, exc)
        finally:
            db.close()

    def get_dispatch_queue_stats(self) -> Dict[str, Any]:
        """Return dispatch queue counts for admin runtime visibility."""
        stats: Dict[str, Any] = {
            "enabled": AI_STREAM_DISTRIBUTED_WORKER_ENABLED,
            "pending": 0,
            "claimed": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "total": 0,
        }
        if not AI_STREAM_PERSISTENCE_ENABLED:
            return stats

        db = SessionLocal()
        try:
            rows = db.query(
                AiStreamDispatchJobRecord.status,
                func.count(AiStreamDispatchJobRecord.id),
            ).group_by(AiStreamDispatchJobRecord.status).all()
            for status, count in rows:
                key = status if status in stats else "total"
                if key != "total":
                    stats[key] = int(count or 0)
                stats["total"] += int(count or 0)
        except Exception as exc:
            stats["last_error"] = str(exc)
            logger.warning("[StreamBuffer] Failed to collect dispatch queue stats: %s", exc)
        finally:
            db.close()
        return stats


# Global singleton instance
_buffer_manager: Optional[StreamBufferManager] = None


def get_buffer_manager() -> StreamBufferManager:
    """Get the global StreamBufferManager instance."""
    global _buffer_manager
    if _buffer_manager is None:
        _buffer_manager = StreamBufferManager()
    return _buffer_manager


def format_sse_event(event_type: str, data: Any) -> str:
    """Format data as an SSE event string."""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def generate_task_id(prefix: str = "ai") -> str:
    """Generate a unique task ID."""
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}"


def _extract_stream_error_message(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("message", "content", "error", "text", "raw"):
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                text = str(value).strip()
                if text:
                    return text
                continue
            try:
                text = _json_dumps(value).strip()
            except Exception:
                text = str(value).strip()
            if text:
                return text[:500]
        return "Unknown error"
    if data is not None:
        text = str(data).strip()
        if text:
            return text[:500]
    return "Unknown error"


def _consume_ai_stream_generator(
    task_id: str,
    generator: Generator[str, None, None],
    on_complete: Optional[Callable[[StreamTask], None]] = None,
    on_error: Optional[Callable[[StreamTask, Exception], None]] = None,
) -> None:
    """Parse yielded SSE events into the shared polling buffer."""
    manager = get_buffer_manager()
    task = manager.get_task(task_id)

    try:
        for sse_event in generator:
            # Parse SSE event: "event: type\ndata: {...}\n\n"
            if not sse_event or not sse_event.strip():
                continue

            lines = sse_event.strip().split('\n')
            event_type = "message"
            data: Any = {}

            for line in lines:
                if line.startswith('event: '):
                    event_type = line[7:]
                elif line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        data = {"raw": line[6:]}

            if not isinstance(data, dict):
                data = {"raw": data}
            manager.add_chunk(task_id, event_type, data)

            if event_type == "done":
                manager.complete_task(task_id, data)
                if on_complete and task:
                    on_complete(task)
                return
            if event_type == "error":
                manager.fail_task(task_id, _extract_stream_error_message(data))
                return
            if event_type == "interrupted":
                manager.fail_task(task_id, f"Interrupted: {_extract_stream_error_message(data)}")
                return

        manager.complete_task(task_id, {"status": "completed"})
        if on_complete and task:
            on_complete(task)
    except Exception as e:
        logger.error(f"[AITask {task_id}] Background task error: {e}", exc_info=True)
        manager.fail_task(task_id, str(e))
        if on_error and task:
            on_error(task, e)


def run_ai_task_in_background(
    task_id: str,
    generator_func: Callable[[], Generator[str, None, None]],
    on_complete: Optional[Callable[[StreamTask], None]] = None,
    on_error: Optional[Callable[[StreamTask, Exception], None]] = None
) -> Future:
    """
    Run an AI streaming task in a background thread.

    The generator_func yields SSE-formatted strings. Each event is parsed and stored
    in StreamBufferManager, where the frontend retrieves it via polling. The generator
    runs independently of the frontend connection - if the frontend disconnects, this
    thread keeps running and events accumulate in the buffer (15-min expiry).

    Any new SSE event type yielded by the generator will automatically be available
    to the frontend without changes here.
    """
    def run():
        _consume_ai_stream_generator(
            task_id,
            generator_func(),
            on_complete=on_complete,
            on_error=on_error,
        )

    return _ai_task_executor.submit(run)


def run_ai_stream_dispatch_job(job: AiStreamDispatchJob) -> None:
    """Run one claimed serializable AI stream job using the registered handler."""
    manager = get_buffer_manager()
    handler = _ai_stream_task_handlers.get(job.task_type)
    if not handler:
        manager.fail_dispatch_job(job.task_id, f"No handler registered for {job.task_type}")
        manager.fail_task(job.task_id, f"No handler registered for {job.task_type}")
        return

    manager.adopt_task_for_dispatch(
        job.task_id,
        conversation_id=job.conversation_id,
        user_id=job.user_id,
    )
    manager.mark_dispatch_job_running(job.task_id)
    try:
        _consume_ai_stream_generator(job.task_id, handler(job))
        task = manager.get_task(job.task_id, user_id=job.user_id)
        if task and task.status == "error":
            manager.fail_dispatch_job(job.task_id, task.error_message or "AI stream task failed")
        else:
            manager.complete_dispatch_job(job.task_id)
    except Exception as exc:
        manager.fail_dispatch_job(job.task_id, str(exc))


def submit_ai_background_task(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Future:
    """Run non-stream AI background work with a bounded executor."""
    return _ai_background_executor.submit(func, *args, **kwargs)


def get_ai_runtime_stats() -> Dict[str, Any]:
    """Return bounded AI executor stats for low-frequency health monitoring."""
    manager = get_buffer_manager()

    with manager._tasks_lock:
        now = time.time()
        running_tasks = 0
        completed_tasks = 0
        error_tasks = 0
        local_running_task_ids: set[str] = set()
        user_stats: Dict[Optional[int], Dict[str, Any]] = {}

        for task in manager._tasks.values():
            entry = user_stats.setdefault(task.user_id, {
                "user_id": task.user_id,
                "total_tasks": 0,
                "running_tasks": 0,
                "remote_running_tasks": 0,
                "persisted_running_tasks": 0,
                "stale_running_tasks": 0,
                "completed_tasks": 0,
                "error_tasks": 0,
                "oldest_running_age_seconds": None,
                "oldest_persisted_running_age_seconds": None,
            })
            entry["total_tasks"] += 1

            if task.status == "running":
                running_tasks += 1
                local_running_task_ids.add(task.task_id)
                entry["running_tasks"] += 1
                age_seconds = max(0, int(now - task.created_at))
                current_oldest = entry["oldest_running_age_seconds"]
                if current_oldest is None or age_seconds > current_oldest:
                    entry["oldest_running_age_seconds"] = age_seconds
            elif task.status == "completed":
                completed_tasks += 1
                entry["completed_tasks"] += 1
            elif task.status == "error":
                error_tasks += 1
                entry["error_tasks"] += 1

    persistent_snapshot = manager.get_persistent_running_snapshot(local_running_task_ids)
    for user_id, persistent_entry in persistent_snapshot.get("users", {}).items():
        entry = user_stats.setdefault(user_id, {
            "user_id": user_id,
            "total_tasks": 0,
            "running_tasks": 0,
            "remote_running_tasks": 0,
            "persisted_running_tasks": 0,
            "stale_running_tasks": 0,
            "completed_tasks": 0,
            "error_tasks": 0,
            "oldest_running_age_seconds": None,
            "oldest_persisted_running_age_seconds": None,
        })
        entry["remote_running_tasks"] = persistent_entry["remote_running_tasks"]
        entry["persisted_running_tasks"] = persistent_entry["persisted_running_tasks"]
        entry["stale_running_tasks"] = persistent_entry["stale_running_tasks"]
        entry["oldest_persisted_running_age_seconds"] = persistent_entry[
            "oldest_persisted_running_age_seconds"
        ]

    users = sorted(
        user_stats.values(),
        key=lambda item: (
            -int(item["running_tasks"] + item.get("remote_running_tasks", 0)),
            -int(item["total_tasks"]),
            item["user_id"] if item["user_id"] is not None else -1,
        ),
    )

    task_threads = len(getattr(_ai_task_executor, "_threads", ()))
    background_threads = len(getattr(_ai_background_executor, "_threads", ()))
    task_queue = getattr(getattr(_ai_task_executor, "_work_queue", None), "qsize", lambda: 0)()
    background_queue = getattr(getattr(_ai_background_executor, "_work_queue", None), "qsize", lambda: 0)()

    return {
        "runner_id": AI_STREAM_RUNNER_ID,
        "running_tasks": running_tasks,
        "remote_running_tasks": persistent_snapshot["remote_running_tasks"],
        "effective_running_tasks": running_tasks + persistent_snapshot["remote_running_tasks"],
        "persisted_running_tasks": persistent_snapshot["persisted_running_tasks"],
        "stale_running_tasks": persistent_snapshot["stale_running_tasks"],
        "completed_buffered_tasks": completed_tasks,
        "error_buffered_tasks": error_tasks,
        "total_buffered_tasks": running_tasks + completed_tasks + error_tasks,
        "task_max_workers": AI_TASK_MAX_WORKERS,
        "task_max_running_global": AI_STREAM_MAX_RUNNING_GLOBAL,
        "task_max_running_per_user": AI_STREAM_MAX_RUNNING_PER_USER,
        "task_threads": task_threads,
        "task_queue": task_queue,
        "background_max_workers": AI_BACKGROUND_MAX_WORKERS,
        "background_threads": background_threads,
        "background_queue": background_queue,
        "dispatch_queue": manager.get_dispatch_queue_stats(),
        "distributed_admission": (
            manager._admission_controller.stats()
            if manager._admission_controller
            else {
                "enabled": False,
                "available": False,
                "prefix": AI_STREAM_DISTRIBUTED_ADMISSION_PREFIX,
                "lease_ttl_seconds": AI_STREAM_DISTRIBUTED_LEASE_TTL_SECONDS,
                "fail_open": AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN,
                "last_error": None,
            }
        ),
        "users": users,
    }
