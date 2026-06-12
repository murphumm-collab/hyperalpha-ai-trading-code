"""
Hyper AI Memory Service - User insights and memory management

This module provides:
1. Memory storage and retrieval with automatic system prompt injection
2. Batch LLM-based deduplication (single call for all memories)
3. Memory categories for organized storage
4. Importance scoring and automatic limit enforcement (max 50)

Memory Categories:
- preference: User trading preferences and style
- decision: Important trading decisions made
- lesson: Lessons learned from trades
- insight: Market insights and observations
- context: General context about user's situation
- strategy_memory: Durable strategy logic, thesis, and approved spec details
- risk_memory: User-specific risk constraints, max loss, leverage, TP/SL rules
- performance_memory: Backtest/live performance conclusions and attribution lessons
- execution_memory: Order backend, handoff, fill/reject, and operational learnings

Architecture:
- Memory is extracted during context compression (async, non-blocking)
- Batch deduplication: 1 LLM call handles all new memories vs all existing
- Memories auto-injected into system prompt alongside user profile
- user_info category (from onboarding) is excluded from dedup/eviction
"""
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from database.models import HyperAiMemory

logger = logging.getLogger(__name__)

# Memory capacity limit
MAX_MEMORIES = 50

# Memory categories
MEMORY_CATEGORIES = [
    "preference",          # Trading preferences
    "decision",            # Important decisions
    "lesson",              # Lessons learned
    "insight",             # Market insights
    "context",             # General context
    "strategy_memory",     # Strategy logic and approved specs
    "risk_memory",         # Risk constraints and guardrails
    "performance_memory",  # Backtest/live performance conclusions
    "execution_memory",    # Order backend and execution operations
]

_MEMORY_SENSITIVE_PATTERN = re.compile(
    r"api[_-]?key|authorization|bearer|private[_-]?key|password|"
    r"secret\s*[:=]|token\s*[:=]|postgres://|redis://",
    re.IGNORECASE,
)

_REDACTED_MEMORY_PROMPT_TEXT = "[redacted_sensitive_memory_text]"
REDACTED_SENSITIVE_MEMORY_CONTENT = "[redacted_sensitive_memory_content]"
SENSITIVE_MEMORY_CONTENT_ERROR = "memory_content_rejected_sensitive"


def _memory_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _redact_sensitive_text_for_memory_prompt(value: Any) -> str:
    text = _memory_text(value)
    if _MEMORY_SENSITIVE_PATTERN.search(text):
        return _REDACTED_MEMORY_PROMPT_TEXT
    return text


def is_memory_content_sensitive(value: Any) -> bool:
    return bool(_MEMORY_SENSITIVE_PATTERN.search(_memory_text(value)))


def validate_memory_content_for_storage(value: Any) -> str:
    text = _memory_text(value).strip()
    if not text:
        raise ValueError("memory_content_empty")
    if is_memory_content_sensitive(text):
        raise ValueError(SENSITIVE_MEMORY_CONTENT_ERROR)
    return text


def _sanitize_memory_content_for_storage(value: Any) -> Optional[str]:
    try:
        return validate_memory_content_for_storage(value)
    except ValueError:
        return None


def _redact_memory_content_for_response(value: Any) -> str:
    text = _memory_text(value).strip()
    if not text:
        return ""
    if is_memory_content_sensitive(text):
        return REDACTED_SENSITIVE_MEMORY_CONTENT
    return text


def _sanitize_memory_candidates(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for mem in memories:
        if not isinstance(mem, dict):
            continue
        category = mem.get("category", "context")
        if category not in MEMORY_CATEGORIES:
            continue
        content = _sanitize_memory_content_for_storage(mem.get("content", ""))
        if not content:
            continue
        sanitized_mem = dict(mem)
        sanitized_mem["category"] = category
        sanitized_mem["content"] = content
        sanitized.append(sanitized_mem)
    return sanitized


def _require_user_id(user_id: Optional[int], context: str) -> int:
    if user_id is None:
        raise ValueError(f"{context} requires authenticated user context")
    return user_id


def get_memories(
    db: Session,
    category: Optional[str] = None,
    limit: int = 20,
    active_only: bool = True,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve memories, optionally filtered by category.

    Args:
        db: Database session
        category: Filter by category (None for all)
        limit: Maximum number of memories to return
        active_only: Only return active memories

    Returns:
        List of memory dictionaries
    """
    resolved_user_id = _require_user_id(user_id, "Hyper AI memories")
    query = db.query(HyperAiMemory).filter(HyperAiMemory.user_id == resolved_user_id)

    if active_only:
        query = query.filter(HyperAiMemory.is_active == True)

    if category:
        query = query.filter(HyperAiMemory.category == category)

    # Order by importance and recency
    memories = query.order_by(
        HyperAiMemory.importance.desc(),
        HyperAiMemory.created_at.desc()
    ).limit(limit).all()

    safe_memories = []
    for m in memories:
        safe_content = _redact_memory_content_for_response(m.content)
        safe_memories.append({
            "id": m.id,
            "user_id": m.user_id,
            "category": m.category,
            "content": safe_content,
            "content_redacted": safe_content == REDACTED_SENSITIVE_MEMORY_CONTENT,
            "source": m.source,
            "importance": m.importance,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return safe_memories


def add_memory(
    db: Session,
    category: str,
    content: str,
    source: str = "conversation",
    importance: float = 0.5,
    user_id: Optional[int] = None,
) -> HyperAiMemory:
    """
    Add a new memory entry.

    Args:
        db: Database session
        category: Memory category
        content: Memory content
        source: Source of the memory (conversation, compression, manual)
        importance: Importance score (0.0 to 1.0)

    Returns:
        Created memory object
    """
    resolved_user_id = _require_user_id(user_id, "Hyper AI memory")
    safe_content = validate_memory_content_for_storage(content)
    memory = HyperAiMemory(
        user_id=resolved_user_id,
        category=category,
        content=safe_content,
        source=source,
        importance=importance,
        is_active=True
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def update_memory(
    db: Session,
    memory_id: int,
    content: Optional[str] = None,
    importance: Optional[float] = None,
    is_active: Optional[bool] = None,
    user_id: Optional[int] = None,
) -> Optional[HyperAiMemory]:
    """Update an existing memory."""
    resolved_user_id = _require_user_id(user_id, "Hyper AI memory update")
    memory = db.query(HyperAiMemory).filter(
        HyperAiMemory.id == memory_id,
        HyperAiMemory.user_id == resolved_user_id,
    ).first()
    if not memory:
        return None

    if content is not None:
        memory.content = validate_memory_content_for_storage(content)
    if importance is not None:
        memory.importance = importance
    if is_active is not None:
        memory.is_active = is_active

    memory.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(memory)
    return memory


def delete_memory(db: Session, memory_id: int, user_id: Optional[int] = None) -> bool:
    """Soft delete a memory by marking it inactive."""
    resolved_user_id = _require_user_id(user_id, "Hyper AI memory delete")
    memory = db.query(HyperAiMemory).filter(
        HyperAiMemory.id == memory_id,
        HyperAiMemory.user_id == resolved_user_id,
    ).first()
    if not memory:
        return False

    memory.is_active = False
    memory.updated_at = datetime.utcnow()
    db.commit()
    return True


# Batch deduplication prompt - handles all new memories in a single LLM call
BATCH_DEDUP_PROMPT = """You are a memory deduplication assistant for a crypto trading AI.

## Existing Memories (already stored):
{existing_memories}

## New Memories (candidates to add):
{new_memories}

For EACH new memory, decide ONE action by comparing against ALL existing memories:
- ADD: New memory is different and valuable, add it
- UPDATE: New memory refines/updates an existing one. Provide existing_id and merged content
- DELETE: New memory contradicts/replaces an existing one. Provide existing_id to delete, then add new
- NONE: New memory is redundant/duplicate of existing, discard it

Respond in JSON only:
{{"actions": [
  {{"new_index": 0, "action": "ADD"}},
  {{"new_index": 1, "action": "UPDATE", "existing_id": 4, "merged": "merged content here"}},
  {{"new_index": 2, "action": "NONE"}},
  {{"new_index": 3, "action": "DELETE", "existing_id": 8}}
]}}"""


def batch_dedup_memories(
    db: Session,
    new_memories: List[Dict[str, Any]],
    api_config: Dict[str, Any],
    source: str = "compression",
    user_id: Optional[int] = None,
) -> int:
    """
    Batch deduplication: compare all new memories against all existing in 1 LLM call.
    Replaces the old per-memory dedup loop.

    Args:
        new_memories: List of {"category", "content", "importance"} dicts
        api_config: LLM config
        source: Memory source tag

    Returns:
        Number of memories added/updated
    """
    if not new_memories:
        return 0
    resolved_user_id = _require_user_id(user_id, "Hyper AI memory dedup")
    new_memories = _sanitize_memory_candidates(new_memories)
    if not new_memories:
        return 0

    # Get all active memories (exclude user_info from onboarding)
    existing = get_memories(db, limit=MAX_MEMORIES, user_id=resolved_user_id)
    existing = [m for m in existing if m.get("category") != "user_info"]

    # If no existing memories, just add all
    if not existing:
        count = 0
        for mem in new_memories:
            cat = mem.get("category", "context")
            content = _sanitize_memory_content_for_storage(mem.get("content"))
            if cat not in MEMORY_CATEGORIES or not content:
                continue
            add_memory(db, cat, content, source, mem.get("importance", 0.5), user_id=resolved_user_id)
            count += 1
        enforce_memory_limit(db, user_id=resolved_user_id)
        return count

    # Build prompt with existing and new memories
    existing_text = "\n".join(
        f"[ID:{m['id']}] ({m['category']}) "
        f"{_redact_sensitive_text_for_memory_prompt(m.get('content', ''))}"
        for m in existing
    )
    new_text = "\n".join(
        f"[{i}] ({m.get('category','context')}) "
        f"{_redact_sensitive_text_for_memory_prompt(m.get('content', ''))}"
        for i, m in enumerate(new_memories)
    )

    prompt = BATCH_DEDUP_PROMPT.format(
        existing_memories=existing_text,
        new_memories=new_text
    )

    # Single LLM call for all dedup decisions
    actions = _call_llm_for_dedup(prompt, api_config)
    if actions is None:
        # LLM failed, fallback: add all as new
        logger.warning("[Memory] Batch dedup LLM failed, adding all as new")
        count = 0
        for mem in new_memories:
            cat = mem.get("category", "context")
            if cat not in MEMORY_CATEGORIES or not mem.get("content"):
                continue
            add_memory(db, cat, mem["content"], source, mem.get("importance", 0.5), user_id=resolved_user_id)
            count += 1
        enforce_memory_limit(db, user_id=resolved_user_id)
        return count

    # Execute actions
    count = 0
    for act in actions:
        idx = act.get("new_index")
        if idx is None or idx >= len(new_memories):
            continue
        mem = new_memories[idx]
        cat = mem.get("category", "context")
        content = _sanitize_memory_content_for_storage(mem.get("content", ""))
        importance = mem.get("importance", 0.5)
        if not content or cat not in MEMORY_CATEGORIES:
            continue

        action = act.get("action", "ADD").upper()

        if action == "ADD":
            add_memory(db, cat, content, source, importance, user_id=resolved_user_id)
            count += 1
        elif action == "UPDATE":
            eid = act.get("existing_id")
            merged = act.get("merged") or content
            if eid:
                old = next((m for m in existing if m["id"] == eid), None)
                old_imp = old.get("importance", 0.5) if old else 0.5
                safe_merged = _sanitize_memory_content_for_storage(merged) or content
                update_memory(db, eid, content=safe_merged, importance=max(importance, old_imp), user_id=resolved_user_id)
                count += 1
            else:
                add_memory(db, cat, content, source, importance, user_id=resolved_user_id)
                count += 1
        elif action == "DELETE":
            eid = act.get("existing_id")
            if eid:
                delete_memory(db, eid, user_id=resolved_user_id)
            add_memory(db, cat, content, source, importance, user_id=resolved_user_id)
            count += 1
        # NONE: discard, do nothing

    enforce_memory_limit(db, user_id=resolved_user_id)
    return count


def _call_llm_for_dedup(
    prompt: str,
    api_config: Dict[str, Any]
) -> Optional[List[Dict[str, Any]]]:
    """
    Single LLM call for batch deduplication. Returns list of action dicts or None on failure.
    """
    base_url = api_config.get("base_url", "")
    api_key = api_config.get("api_key", "")
    model = api_config.get("model", "")
    api_format = api_config.get("api_format", "openai")

    if not all([base_url, api_key, model]):
        logger.warning("[Memory] Incomplete API config for dedup")
        return None

    try:
        from services.ai_decision_service import (
            build_chat_completion_endpoints, build_llm_payload, build_llm_headers
        )
        endpoints = build_chat_completion_endpoints(base_url, model)
        if api_format == "anthropic":
            endpoint = endpoints[0] if endpoints else f"{base_url.rstrip('/')}/messages"
        else:
            endpoint = endpoints[0] if endpoints else f"{base_url}/chat/completions"

        headers = build_llm_headers(api_format, api_key, base_url)
        body = build_llm_payload(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_format=api_format,
            max_tokens=800,
            temperature=None,
        )

        response = requests.post(endpoint, headers=headers, json=body, timeout=60)

        if response.status_code != 200:
            logger.warning(
                "[Memory] Dedup API error: status=%s response_body_present=%s",
                response.status_code,
                bool(getattr(response, "content", b"")),
            )
            return None

        data = response.json()

        if api_format == "anthropic":
            content = data.get("content", [])
            text = content[0].get("text", "") if content else ""
        else:
            choices = data.get("choices", [])
            text = choices[0].get("message", {}).get("content", "") if choices else ""

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("actions", [])

        logger.warning("[Memory] Dedup response not valid JSON")
        return None

    except requests.exceptions.Timeout:
        logger.warning("[Memory] Dedup API timeout (60s)")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("[Memory] Dedup API connection error")
        return None
    except json.JSONDecodeError:
        logger.warning("[Memory] Dedup response JSON parse error")
        return None
    except Exception:
        logger.warning("[Memory] Dedup unexpected error")
        return None


def enforce_memory_limit(db: Session, user_id: Optional[int] = None) -> int:
    """
    Enforce MAX_MEMORIES limit by soft-deleting lowest importance memories.
    Excludes user_info category (managed by onboarding).
    Returns number of memories evicted.
    """
    resolved_user_id = _require_user_id(user_id, "Hyper AI memory limit")
    active_query = db.query(HyperAiMemory).filter(
        HyperAiMemory.is_active == True,
        HyperAiMemory.category != "user_info",
        HyperAiMemory.user_id == resolved_user_id,
    )
    active_count = active_query.count()

    if active_count <= MAX_MEMORIES:
        return 0

    excess = active_count - MAX_MEMORIES
    # Get lowest importance memories to evict
    evict_query = db.query(HyperAiMemory).filter(
        HyperAiMemory.is_active == True,
        HyperAiMemory.category != "user_info",
        HyperAiMemory.user_id == resolved_user_id,
    )
    to_evict = evict_query.order_by(
        HyperAiMemory.importance.asc(),
        HyperAiMemory.created_at.asc()
    ).limit(excess).all()

    for m in to_evict:
        m.is_active = False
        m.updated_at = datetime.utcnow()

    db.commit()
    logger.warning(f"[Memory] Evicted {len(to_evict)} memories (limit={MAX_MEMORIES})")
    return len(to_evict)


# Memory extraction prompt for compression
EXTRACT_MEMORIES_PROMPT = """You are a memory extraction assistant for a crypto trading AI platform.
Analyze this conversation and extract key user insights worth remembering long-term.

Conversation:
{conversation}

## Categories and what to extract:

**preference** (importance 0.7-0.9):
- Trading style (scalping, swing, intraday), risk tolerance, leverage preferences
- Preferred coins/pairs, timeframes, position sizing rules
- Daily routines (e.g. close all positions before UTC 23:30)

**decision** (importance 0.6-0.8):
- Strategy parameters chosen (e.g. EMA periods, RSI thresholds, TP/SL percentages)
- Specific trading rules or conditions the user confirmed
- Configuration changes (e.g. switched model, changed leverage from 5x to 3x)

**lesson** (importance 0.7-0.9):
- Losses or mistakes and what the user learned
- What worked well and why
- Market behavior patterns the user identified

**insight** (importance 0.5-0.7):
- Market observations (e.g. "BTC tends to dump after funding rate > 0.1%")
- Correlations or patterns discussed
- Backtesting results and conclusions

**strategy_memory** (importance 0.7-0.9):
- Durable strategy thesis, entry/exit logic, approved strategy-spec details
- Natural-language strategy changes the user confirmed for future reuse

**risk_memory** (importance 0.8-0.95):
- Max loss, leverage, position sizing, stop-loss/take-profit requirements
- User-specific constraints that should affect future AI Trading drafts/signals

**performance_memory** (importance 0.7-0.9):
- Backtest/live results, attribution findings, what improved or hurt returns
- Strategy-specific metrics or lessons that should guide future revisions

**execution_memory** (importance 0.7-0.9):
- Order backend handoff rules, fill/reject outcomes, operational issues
- Execution constraints such as slippage, retries, gateway availability, timing

## Rules:
- Each memory should be specific and self-contained (readable without context)
- Include concrete numbers/parameters when available
- Max 5 memories per extraction, only truly important ones
- If nothing significant, return empty list

Respond in JSON:
{{"memories": [{{"category": "...", "content": "...", "importance": 0.8}}]}}"""


def extract_memories_from_conversation(
    conversation_text: str,
    api_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Extract memories from conversation using LLM.

    Returns:
        List of {"category", "content", "importance"} dicts
    """
    safe_conversation_text = _redact_sensitive_text_for_memory_prompt(conversation_text)
    prompt = EXTRACT_MEMORIES_PROMPT.format(
        conversation=safe_conversation_text[:6000]
    )

    base_url = api_config.get("base_url", "")
    api_key = api_config.get("api_key", "")
    model = api_config.get("model", "")
    api_format = api_config.get("api_format", "openai")

    if not all([base_url, api_key, model]):
        return []

    try:
        from services.ai_decision_service import build_chat_completion_endpoints, build_llm_payload, build_llm_headers

        endpoints = build_chat_completion_endpoints(base_url, model)
        if api_format == "anthropic":
            endpoint = endpoints[0] if endpoints else f"{base_url.rstrip('/')}/messages"
        else:
            endpoint = endpoints[0] if endpoints else f"{base_url}/chat/completions"

        # Use unified headers/payload builders (see build_llm_payload in ai_decision_service)
        headers = build_llm_headers(api_format, api_key, base_url)
        body = build_llm_payload(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_format=api_format,
            max_tokens=500,
            temperature=None,
        )

        response = requests.post(endpoint, headers=headers, json=body, timeout=60)

        if response.status_code != 200:
            logger.warning(
                "[Memory] Extraction API error: status=%s response_body_present=%s",
                response.status_code,
                bool(getattr(response, "content", b"")),
            )
            return []

        data = response.json()

        # Extract response text
        if api_format == "anthropic":
            content = data.get("content", [])
            text = content[0].get("text", "") if content else ""
        else:
            choices = data.get("choices", [])
            text = choices[0].get("message", {}).get("content", "") if choices else ""

        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            memories = result.get("memories", [])
            if isinstance(memories, list):
                return _sanitize_memory_candidates(memories)

    except requests.exceptions.Timeout:
        logger.warning("[Memory] Extraction API timeout (60s)")
    except requests.exceptions.ConnectionError:
        logger.warning("[Memory] Extraction API connection error")
    except json.JSONDecodeError:
        logger.warning("[Memory] Extraction response JSON parse error")
    except Exception:
        logger.warning("[Memory] Extraction unexpected error")

    return []


def process_compression_memories(
    db: Session,
    conversation_text: str,
    api_config: Dict[str, Any],
    user_id: Optional[int] = None,
) -> int:
    """
    Extract and store memories during context compression.
    Uses batch dedup: 1 LLM call for extraction + 1 for dedup = 2 total.

    Returns:
        Number of memories added/updated
    """
    if user_id is None:
        logger.warning("[Memory] Skipping memory extraction because user context is missing")
        return 0

    memories = extract_memories_from_conversation(conversation_text, api_config)

    if not memories:
        return 0

    # Filter valid memories
    valid = _sanitize_memory_candidates(memories)

    if not valid:
        return 0

    count = batch_dedup_memories(db, valid, api_config, source="compression", user_id=user_id)
    logger.warning(f"[Memory] Processed {count} memories from compression (batch mode)")
    return count
