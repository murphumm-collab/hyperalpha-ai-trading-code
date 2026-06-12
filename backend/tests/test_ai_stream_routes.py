import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import ai_stream_routes


class _FakeStreamManager:
    def __init__(self):
        self.requested_user_ids = []
        self.raw_error = (
            "Provider 502 https://model.internal/v1/chat Authorization: Bearer leaked-token "
            "redis://:secret-redis-password@redis.internal:6379/0"
        )
        self.task = SimpleNamespace(
            task_id="task-secret",
            status="error",
            conversation_id=88,
            created_at=1000.0,
            completed_at=1002.0,
            error_message=self.raw_error,
            result=None,
        )
        self.chunks = [
            SimpleNamespace(
                event_type="message",
                data={"content": "safe partial answer"},
                timestamp=1001.0,
            ),
            SimpleNamespace(
                event_type="error",
                data={"raw": self.raw_error, "message": "token=chunk-secret"},
                timestamp=1002.0,
            ),
        ]

    def get_chunks(self, task_id, offset=0, user_id=None):
        self.requested_user_ids.append(("chunks", user_id))
        if task_id != self.task.task_id:
            return [], "not_found"
        return self.chunks[offset:], self.task.status

    def get_task(self, task_id, user_id=None):
        self.requested_user_ids.append(("task", user_id))
        if task_id != self.task.task_id:
            return None
        return self.task


def _build_client():
    app = FastAPI()
    app.include_router(ai_stream_routes.router)
    app.dependency_overrides[ai_stream_routes.get_current_user_dependency] = (
        lambda: SimpleNamespace(id=42)
    )
    return TestClient(app)


def test_ai_stream_polling_redacts_task_error_and_error_chunks(monkeypatch):
    fake_manager = _FakeStreamManager()
    monkeypatch.setattr(ai_stream_routes, "get_buffer_manager", lambda: fake_manager)
    client = _build_client()

    response = client.get("/api/ai-stream/task-secret?offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"] == "AI stream task failed"
    assert payload["error_code"] == "ai_stream_task_failed"
    assert payload["error_present"] is True
    assert payload["chunks"][0]["data"] == {"content": "safe partial answer"}
    assert payload["chunks"][1]["event_type"] == "error"
    assert payload["chunks"][1]["data"] == {
        "message": "AI stream task failed",
        "error_code": "ai_stream_task_failed",
        "error_present": True,
    }
    assert ("chunks", 42) in fake_manager.requested_user_ids
    assert ("task", 42) in fake_manager.requested_user_ids

    serialized = json.dumps(payload, ensure_ascii=False)
    assert fake_manager.raw_error not in serialized
    assert "leaked-token" not in serialized
    assert "secret-redis-password" not in serialized
    assert "chunk-secret" not in serialized
    assert "model.internal" not in serialized


def test_ai_stream_status_redacts_task_error(monkeypatch):
    fake_manager = _FakeStreamManager()
    monkeypatch.setattr(ai_stream_routes, "get_buffer_manager", lambda: fake_manager)
    client = _build_client()

    response = client.get("/api/ai-stream/task-secret/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"] == "AI stream task failed"
    assert payload["error_code"] == "ai_stream_task_failed"
    assert payload["error_present"] is True
    assert ("task", 42) in fake_manager.requested_user_ids

    serialized = json.dumps(payload, ensure_ascii=False)
    assert fake_manager.raw_error not in serialized
    assert "Bearer leaked-token" not in serialized
    assert "secret-redis-password" not in serialized
    assert "model.internal" not in serialized
