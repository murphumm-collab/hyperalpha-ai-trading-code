"""
AI Stream Routes - Common polling API for all AI assistants

This module provides the shared polling endpoint for frontend to retrieve
AI streaming task results. All AI assistants use this common infrastructure.

Endpoints:
- GET /api/ai-stream/{task_id} - Poll for task chunks with offset support
- GET /api/ai-stream/{task_id}/status - Get task status only
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from services.ai_stream_service import get_ai_runtime_stats, get_buffer_manager
from api.auth_utils import get_admin_user_dependency, get_current_user_dependency
from database.connection import get_db
from database.models import User

router = APIRouter(prefix="/api/ai-stream", tags=["AI Stream"])

PUBLIC_AI_STREAM_ERROR_CODE = "ai_stream_task_failed"
PUBLIC_AI_STREAM_ERROR_MESSAGE = "AI stream task failed"
AI_STREAM_ERROR_CHUNK_TYPES = {"error", "interrupted"}


def _sanitize_runtime_last_error(
    component: object,
    *,
    code: str,
) -> object:
    """Return admin runtime component metadata without raw exception text."""
    if not isinstance(component, dict):
        return component

    sanitized = dict(component)
    has_error = bool(sanitized.get("last_error") or sanitized.get("last_error_code"))
    sanitized["last_error_present"] = has_error
    sanitized["last_error_code"] = code if has_error else None
    sanitized["last_error"] = code if has_error else None
    return sanitized


def sanitize_admin_ai_runtime_stats(stats: dict) -> dict:
    """Remove raw runtime exception strings before returning admin AI stats."""
    sanitized = dict(stats)
    sanitized["distributed_admission"] = _sanitize_runtime_last_error(
        sanitized.get("distributed_admission"),
        code="distributed_admission_unavailable",
    )
    sanitized["dispatch_queue"] = _sanitize_runtime_last_error(
        sanitized.get("dispatch_queue"),
        code="dispatch_queue_stats_unavailable",
    )
    return sanitized


def _safe_ai_stream_error_payload() -> dict:
    """Return a stable public error payload without provider/internal text."""
    return {
        "message": PUBLIC_AI_STREAM_ERROR_MESSAGE,
        "error_code": PUBLIC_AI_STREAM_ERROR_CODE,
        "error_present": True,
    }


def _sanitize_ai_stream_chunk(event_type: object, data: object) -> object:
    """Hide raw error chunk data before returning poll responses."""
    if str(event_type or "").lower() not in AI_STREAM_ERROR_CHUNK_TYPES:
        return data
    return _safe_ai_stream_error_payload()


@router.get("/admin/runtime")
def get_admin_ai_runtime(
    current_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db),
):
    """Return admin-only AI stream runtime capacity and per-user occupancy."""
    stats = sanitize_admin_ai_runtime_stats(get_ai_runtime_stats())
    user_entries = stats.get("users", [])
    user_ids = [
        entry.get("user_id")
        for entry in user_entries
        if entry.get("user_id") is not None
    ]
    users_by_id = {}
    if user_ids:
        rows = db.query(User).filter(User.id.in_(user_ids)).all()
        users_by_id = {user.id: user for user in rows}

    stats["users"] = [
        {
            **entry,
            "username": users_by_id[entry["user_id"]].username
            if entry.get("user_id") in users_by_id
            else None,
            "email": users_by_id[entry["user_id"]].email
            if entry.get("user_id") in users_by_id
            else None,
        }
        for entry in user_entries
    ]
    return stats


@router.get("/{task_id}")
def poll_task_chunks(
    task_id: str,
    offset: int = Query(0, ge=0, description="Offset to start reading chunks from"),
    current_user: User = Depends(get_current_user_dependency),
):
    """
    Poll for task chunks starting from offset.

    Returns:
    - chunks: List of {event_type, data, timestamp} objects
    - status: "running", "completed", "error", or "not_found"
    - next_offset: The offset to use for the next poll
    - result: Final result data if status is "completed"
    - error: Error message if status is "error"
    """
    manager = get_buffer_manager()
    chunks, status = manager.get_chunks(task_id, offset, user_id=current_user.id)

    if status == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")

    response = {
        "task_id": task_id,
        "status": status,
        "chunks": [
            {
                "event_type": c.event_type,
                "data": _sanitize_ai_stream_chunk(c.event_type, c.data),
                "timestamp": c.timestamp
            }
            for c in chunks
        ],
        "next_offset": offset + len(chunks)
    }

    # Include result/error for completed/failed tasks
    task = manager.get_task(task_id, user_id=current_user.id)
    if task:
        if status == "completed" and task.result:
            response["result"] = task.result
        elif status == "error":
            response["error"] = PUBLIC_AI_STREAM_ERROR_MESSAGE
            response["error_code"] = PUBLIC_AI_STREAM_ERROR_CODE
            response["error_present"] = True

    return response


@router.get("/{task_id}/status")
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user_dependency),
):
    """
    Get task status without chunks (lightweight check).

    Returns:
    - status: "running", "completed", "error", or "not_found"
    - conversation_id: Associated conversation ID if available
    - result: Final result if completed
    - error: Error message if failed
    """
    manager = get_buffer_manager()
    task = manager.get_task(task_id, user_id=current_user.id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    response = {
        "task_id": task_id,
        "status": task.status,
        "conversation_id": task.conversation_id,
        "created_at": task.created_at,
    }

    if task.status == "completed":
        response["completed_at"] = task.completed_at
        if task.result:
            response["result"] = task.result
    elif task.status == "error":
        response["completed_at"] = task.completed_at
        response["error"] = PUBLIC_AI_STREAM_ERROR_MESSAGE
        response["error_code"] = PUBLIC_AI_STREAM_ERROR_CODE
        response["error_present"] = True

    return response
