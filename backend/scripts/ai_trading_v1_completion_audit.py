"""Audit AI Trading V1 completion boundaries from local evidence.

This script does not call models, exchanges, GitHub, or order backends. It reads
the checked-in acceptance/status/memory documents and reports whether the local
V1 track is accepted, while keeping production/live-order work explicitly
pending until real external evidence exists.

Run from backend:

    uv run python scripts/ai_trading_v1_completion_audit.py --strict-local

Use --strict-production only for a production cutover audit. It intentionally
fails unless a complete sanitized production evidence file is supplied and the
caller also passes --allow-live-ready-from-evidence.

Use --explain-production-evidence to print an item-level, non-secret operations
checklist for filling or fixing the external production evidence file.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION = "hyperalpha.ai_trading.external_acceptance.v1"
EXPECTED_LOCAL_DEVELOPMENT_BRANCH = "codex/ai-agent-multitenant-foundation"
EXPECTED_GITHUB_UPLOAD_STATUS = "pushed_to_origin"
EXPECTED_REMOTE_TRACKING_BRANCH = f"origin/{EXPECTED_LOCAL_DEVELOPMENT_BRANCH}"
SAFE_ARTIFACT_REF_SCHEMES = {"https", "ops", "lark", "notion"}
ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS = {
    "version",
    "evidence_run_id",
    "generated_at",
    "expires_at",
    "cutover_window",
    "cutover_approval_ref",
    "secret_values_returned",
    "notes",
    "items",
}
ALLOWED_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_FIELDS = {"start_at", "end_at"}
ALLOWED_PRODUCTION_EVIDENCE_ITEM_FIELDS = {
    "status",
    "validated_at",
    "validated_by",
    "evidence_summary",
    "artifact_refs",
    "secret_values_returned",
}
MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS = 24
MAX_PRODUCTION_EVIDENCE_SUMMARY_CHARS = 600
MAX_PRODUCTION_EVIDENCE_VALIDATOR_CHARS = 120
MAX_PRODUCTION_EVIDENCE_NOTE_CHARS = 300
MAX_PRODUCTION_EVIDENCE_NOTES = 12
MAX_PRODUCTION_EVIDENCE_ARTIFACT_REF_CHARS = 300
MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS = 5
MAX_PRODUCTION_EVIDENCE_VALIDITY_DAYS = 7
MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS = 300
MAX_PRODUCTION_EVIDENCE_ITEM_VALIDATION_AGE_DAYS = 7
MAX_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_HOURS = 8
MIN_PRODUCTION_EVIDENCE_RUN_ID_CHARS = 12
MAX_PRODUCTION_EVIDENCE_RUN_ID_CHARS = 80
PRODUCTION_EVIDENCE_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
PRODUCTION_EVIDENCE_REQUIRED_ROOT_FIELDS = (
    f"version={EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION}",
    f"evidence_run_id=safe unique run id, {MIN_PRODUCTION_EVIDENCE_RUN_ID_CHARS}-{MAX_PRODUCTION_EVIDENCE_RUN_ID_CHARS} chars, letters/numbers/._:- only, referenced by cutover_approval_ref and item artifact_refs",
    f"generated_at=timezone-aware ISO-8601 timestamp not more than {MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS} seconds in the future",
    f"expires_at=timezone-aware ISO-8601 timestamp after generated_at, in the future, and within {MAX_PRODUCTION_EVIDENCE_VALIDITY_DAYS} days",
    f"cutover_window=start_at/end_at timezone-aware ISO-8601 window containing the production audit time and no longer than {MAX_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_HOURS} hours",
    "cutover_approval_ref=1 safe ops/lark/notion/https approval ref for the live-order cutover",
    "secret_values_returned=false",
    "items=documented external acceptance item ids only",
)
PLACEHOLDER_EVIDENCE_VALUES = {
    "-",
    "accepted",
    "change me",
    "change-me",
    "changeme",
    "done",
    "fill me",
    "fill-me",
    "n/a",
    "na",
    "none",
    "ok",
    "pending",
    "placeholder",
    "tbd",
    "test",
    "todo",
    "unknown",
}
PRODUCTION_EVIDENCE_TEMPLATE_NOTES = (
    "Copy this file outside the code repository or into a private ops evidence location before filling it; repo-local production evidence files cannot unlock live-order readiness.",
    "Do not include API keys, bearer tokens, database URLs, private keys, raw Authorization headers, or user secrets.",
    "Use only documented schema fields. Allowed root fields: version, evidence_run_id, generated_at, expires_at, cutover_window, cutover_approval_ref, secret_values_returned, notes, items. Allowed item fields: status, validated_at, validated_by, evidence_summary, artifact_refs, secret_values_returned.",
    "Root notes are optional and must be a bounded list of concise strings; do not use notes for raw logs, model output, traces, or pasted operational dumps.",
    "The items object must contain only the documented external acceptance item ids in this template; unknown item ids are rejected.",
    f"evidence_run_id must be a unique sanitized operations run id for this production acceptance attempt, {MIN_PRODUCTION_EVIDENCE_RUN_ID_CHARS}-{MAX_PRODUCTION_EVIDENCE_RUN_ID_CHARS} chars, letters/numbers/dot/underscore/colon/hyphen only; cutover_approval_ref must include it, and each item artifact_ref must include it plus the item id.",
    f"generated_at, expires_at, and item validated_at must be timezone-aware ISO-8601; generated_at/validated_at cannot be >{MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS}s in the future; item validation cannot be older than {MAX_PRODUCTION_EVIDENCE_ITEM_VALIDATION_AGE_DAYS} days at generated_at; expires_at must be after generated_at, future, and within {MAX_PRODUCTION_EVIDENCE_VALIDITY_DAYS} days.",
    f"cutover_window.start_at/end_at must be timezone-aware ISO-8601, contain the production audit time, and be no longer than {MAX_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_HOURS} hours.",
    "cutover_approval_ref must point to one sanitized ops://, lark://, notion://, or https:// approval record for the exact live-order cutover window and include evidence_run_id.",
    "artifact_refs must be non-empty item-specific sanitized refs using https://, ops://, lark://, or notion:// only; use no more than 5 per item, each <=300 chars, include evidence_run_id plus item id, never repeat or reuse refs, and avoid credentials/local/private URLs.",
    "Each item must become status=accepted with validated_at, a non-placeholder validated_by of 3-120 characters, a concrete evidence_summary of 24-600 characters, artifact_refs, and secret_values_returned=false before production cutover audit can pass.",
    "When an item is status=accepted, evidence_summary must mention that item's required non-secret proof terms from --explain-production-evidence; generic summaries are rejected.",
)
PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS = (
    "status=accepted",
    f"validated_at=timezone-aware ISO-8601 timestamp not more than {MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS} seconds in the future and not older than {MAX_PRODUCTION_EVIDENCE_ITEM_VALIDATION_AGE_DAYS} days at generated_at",
    "validated_by=non-placeholder reviewer/operator name, 3-120 chars",
    "evidence_summary=concrete sanitized acceptance summary, 24-600 chars",
    "artifact_refs=1-5 unique item-specific safe refs using https://, ops://, lark://, or notion:// and containing evidence_run_id plus the item id",
    "secret_values_returned=false",
)
PRODUCTION_EVIDENCE_COMMON_FORBIDDEN = (
    "API keys",
    "bearer tokens",
    "database URLs",
    "private keys",
    "raw Authorization headers",
    "raw model output",
    "raw operational dumps",
)
PRODUCTION_EVIDENCE_ROOT_GUIDANCE: tuple[dict[str, Any], ...] = (
    {
        "field": "version",
        "required_value": EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "related_blockers": ("external_evidence_version_mismatch",),
        "operator_guidance": (
            "Keep the evidence version equal to the generated template version.",
        ),
    },
    {
        "field": "evidence_run_id",
        "required_value": f"safe unique run id, {MIN_PRODUCTION_EVIDENCE_RUN_ID_CHARS}-{MAX_PRODUCTION_EVIDENCE_RUN_ID_CHARS} chars",
        "related_blockers": (
            "external_evidence_run_id_missing",
            "external_evidence_run_id_too_short",
            "external_evidence_run_id_too_long",
            "external_evidence_run_id_invalid_chars",
            "external_evidence_run_id_placeholder",
            "external_evidence_run_id_secret_pattern_detected",
        ),
        "operator_guidance": (
            "Use one sanitized production acceptance run id and repeat it in cutover_approval_ref plus every item artifact_ref.",
        ),
    },
    {
        "field": "generated_at",
        "required_value": "timezone-aware ISO-8601 timestamp",
        "related_blockers": (
            "external_evidence_generated_at_missing",
            "external_evidence_generated_at_timezone_missing",
            "external_evidence_generated_at_in_future",
            "external_evidence_generated_at_before_cutover_window",
            "external_evidence_generated_at_after_cutover_window",
        ),
        "operator_guidance": (
            "Set generated_at when compiling the evidence packet; keep it inside the approved cutover window.",
        ),
    },
    {
        "field": "expires_at",
        "required_value": f"future ISO-8601 timestamp within {MAX_PRODUCTION_EVIDENCE_VALIDITY_DAYS} days of generated_at",
        "related_blockers": (
            "external_evidence_expires_at_missing",
            "external_evidence_expires_at_timezone_missing",
            "external_evidence_expires_at_not_after_generated_at",
            "external_evidence_expires_at_too_far",
            "external_evidence_expired",
        ),
        "operator_guidance": (
            "Use a short-lived evidence expiry so stale production acceptance packets cannot unlock live orders later.",
        ),
    },
    {
        "field": "cutover_window",
        "required_value": f"start_at/end_at ISO-8601 window, max {MAX_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_HOURS} hours",
        "related_blockers": (
            "external_evidence_cutover_window_missing",
            "external_evidence_cutover_window_start_at_missing",
            "external_evidence_cutover_window_end_at_missing",
            "external_evidence_cutover_window_end_not_after_start",
            "external_evidence_cutover_window_too_long",
            "external_evidence_cutover_window_not_started",
            "external_evidence_cutover_window_ended",
        ),
        "operator_guidance": (
            "Use the exact approved live-order cutover window; the production audit time must fall inside it.",
        ),
    },
    {
        "field": "cutover_approval_ref",
        "required_value": "one safe ops/lark/notion/https approval ref containing evidence_run_id",
        "related_blockers": (
            "external_evidence_cutover_approval_ref_missing",
            "external_evidence_cutover_approval_ref_missing_run_id",
            "external_evidence_cutover_approval_ref_scheme_not_allowed",
            "external_evidence_cutover_approval_ref_secret_pattern_detected",
        ),
        "operator_guidance": (
            "Point to a sanitized approval record for the same cutover window; do not embed credentials or raw authorization headers.",
        ),
    },
    {
        "field": "secret_values_returned",
        "required_value": "false",
        "related_blockers": ("external_evidence_secret_values_returned_must_be_false",),
        "operator_guidance": (
            "Keep this false and store only metadata or sanitized artifact references in evidence.",
        ),
    },
    {
        "field": "notes",
        "required_value": "optional bounded concise strings",
        "related_blockers": (
            "external_evidence_notes_must_be_list",
            "external_evidence_notes_too_many",
            "external_evidence_note_too_long",
        ),
        "operator_guidance": (
            "Use notes only for short sanitized context; do not paste logs, traces, model output, or operation dumps.",
        ),
    },
)
PRODUCTION_EVIDENCE_ITEM_REQUIRED_SUMMARY_TERMS: dict[str, tuple[tuple[str, ...], ...]] = {
    "macos_reboot_recovery": (
        ("macOS reboot", "reboot"),
        ("LaunchAgent",),
        ("runtime mirror current", "runtime_mirror.current=true", "runtime mirror"),
        ("ready=true", "ready true"),
    ),
    "real_model_profile_live_acceptance": (
        ("DeepSeek", "Qwen"),
        ("live model-adjust", "model-adjust"),
        ("no signal event", "no signal events", "no signals"),
        ("no handoff", "no orders"),
    ),
    "real_order_backend_handoff": (
        ("HTTPS",),
        ("mode=http", "gateway mode=http", "gateway_mode=http"),
        ("token-present", "token present", "token_present"),
        ("production_handoff_approved=true", "production approval", "approved production handoff"),
    ),
    "production_auth_hard_risk_readiness": (
        ("JWKS",),
        ("hard risk", "hard-risk"),
        ("stop loss", "stop-loss"),
        ("take profit", "take-profit"),
        ("secret_values_returned=false", "no secrets"),
    ),
    "admin_readiness_real_auth_visual": (
        ("admin",),
        ("real auth", "logged-in", "login"),
        ("production readiness panel", "readiness panel"),
        ("no secrets", "no token"),
    ),
    "production_agent_session_visual": (
        ("agent-session", "agent session"),
        ("current user", "user-scoped"),
        ("context budget", "summary chars"),
        ("no context_summary", "no raw context", "no secrets"),
    ),
    "real_exchange_execution": (
        ("order backend", "backend"),
        ("exchange execution", "Hyperliquid"),
        ("not AI agent", "order backend only"),
        ("sanitized execution evidence", "sanitized"),
    ),
}
PRODUCTION_EVIDENCE_ITEM_GUIDANCE: dict[str, tuple[str, ...]] = {
    "macos_reboot_recovery": (
        "After a real macOS reboot, prove LaunchAgent restored frontend, backend, mock gateway, and Postgres readiness.",
        "Use ai_trading_v1_env_check.py --strict --require-runtime-mirror-current as the sanitized readiness artifact.",
    ),
    "real_model_profile_live_acceptance": (
        "Configure a user's Hyper AI profile with DeepSeek or Qwen credentials outside the evidence file.",
        "Run ai_trading_model_adjust_live_acceptance.py with explicit live-model confirmation and record only sanitized outcome metadata.",
    ),
    "real_order_backend_handoff": (
        "Configure the real HTTPS order-backend signal gateway and token outside the evidence file.",
        "Run the production handoff checker and capture sanitized proof that the gateway is external, token-present, and explicitly approved.",
    ),
    "production_auth_hard_risk_readiness": (
        "Validate production Auth/JWKS, issuer, audience, algorithms, hard TP/SL/notional/leverage caps, and production handoff approval.",
        "Use production readiness output that confirms no token, API key, DB URL, or raw authorization value is returned.",
    ),
    "admin_readiness_real_auth_visual": (
        "Under real auth, verify an admin/operator can see the Settings AI Trading production readiness panel.",
        "Record a sanitized visual artifact reference without cookies, tokens, or raw API responses.",
    ),
    "production_agent_session_visual": (
        "Under real production login, verify the agent-session detail page renders only the current user's session audit/context budget.",
        "Record a sanitized visual artifact reference proving no raw context_summary secrets are rendered.",
    ),
    "real_exchange_execution": (
        "Run this as a separate production live-trading acceptance outside local V1.",
        "Record only bounded sanitized execution evidence after the order backend, not the AI agent, performs the exchange action.",
    ),
}
SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\b(api[_-]?key|password|private[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*['\"]?[^'\"\s,}]{4,}", re.IGNORECASE),
    re.compile(r"\bsecret\s*[:=]\s*['\"]?[^'\"\s,}]{4,}", re.IGNORECASE),
    re.compile(r"\bpostgres(?:ql)?://[^\s'\"]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


@dataclass(frozen=True)
class EvidenceRequirement:
    id: str
    track: str
    description: str
    path: str
    required_phrases: tuple[str, ...] = ()
    required_patterns: tuple[str, ...] = ()
    status_if_present: str = "accepted"
    metadata: dict[str, Any] = field(default_factory=dict)


LOCAL_REQUIREMENTS: tuple[EvidenceRequirement, ...] = (
    EvidenceRequirement(
        id="aggregate_local_acceptance_runner",
        track="local_v1",
        description="One-key local acceptance runner covers tests, frontend build, runtime readiness, mock handoff, and DB-audit readiness blocker.",
        path="scripts/local-dev/run_ai_trading_v1_local_acceptance.sh",
        required_phrases=(
            "--confirm-local-mock-handoff",
            "Local dev shell syntax",
            "Default production readiness DB-audit gate remains blocked",
            "--include-db-audits",
            "Frontend build",
            "tests/test_ai_stream_routes.py",
            "tests/test_ai_trading_frontend_readiness_source.py",
            "tests/test_kline_routes.py",
            "tests/test_kline_collectors.py",
            "local completion summary gate",
            "git_governance.status",
            "ready_for_live_orders_false",
            EXPECTED_GITHUB_UPLOAD_STATUS,
            "codex/ai-agent-multitenant-foundation",
            "ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff",
            "Production evidence template remains blocked",
            "Production evidence explain mode gate",
            "--explain-production-evidence",
            "production_evidence_explain_gate",
            "Production evidence initializer gate",
            "--init-production-evidence-file",
            "production_evidence_initializer_gate",
            "real_order_backend_blocked",
            "Local LaunchAgent runtime sync",
            "scripts/local-dev/install_launch_agent.sh",
            "--require-runtime-mirror-current",
            "AI_TRADING_TRANSIENT_RETRY_ATTEMPTS",
            "AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS",
            "Transient local resource failure",
            "run_command_with_transient_retry",
            "make_temp_file_with_retry",
            "Resource temporarily unavailable",
            "Failed to spawn",
            "fork failed",
            "AI_TRADING_RUNTIME_READINESS_ATTEMPTS",
            "AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS",
            "Runtime readiness attempt",
            "Runtime readiness still blocked",
            "run_runtime_readiness_with_retry",
            "Production operator preflight remains blocked",
            "ai_trading_v1_production_operator_preflight.py --skip-local-runtime --strict",
            "production_operator_preflight_gate",
            "completion:live_orders_not_ready",
            "REDACTED_SENSITIVE_PREFLIGHT_VALUE",
            "--production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production",
        ),
    ),
    EvidenceRequirement(
        id="acceptance_checklist_latest_local_proof",
        track="local_v1",
        description="V1 checklist records the latest local acceptance proof and separates unfinished real-environment work.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=(
            "一键本地 V1 验收通过",
            "默认生产 DB-audit readiness gate 阻断",
            "当前未验收",
            "真实 DeepSeek/Qwen API key live model-adjust 未验收",
            "真实 HyperAlpha 订单后端 URL/token live handoff 未验收",
            "真实交易所执行不属于 V1 本地验收完成条件",
        ),
        required_patterns=(
            r"spec `#\d+`",
            r"signal event `#\d+`",
            r"agent_sessions\.total=\d+",
            r"handoff_attempts\.total=\d+",
        ),
    ),
    EvidenceRequirement(
        id="status_progress_marker",
        track="local_v1",
        description="Feature status marks the production operator preflight flow as accepted and the remote branch as synced.",
        path="docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md",
        required_phrases=(
            "Local V1 Production Operator Preflight Accepted / Remote Push Synced",
            "| AI Trading aggregate acceptance DB-audit gate | Done |",
            "| AI Trading V1 completion boundary audit | Done |",
            "| AI Trading production evidence gate | Done |",
            "| AI Trading production evidence text quality | Done |",
            "| AI Trading production evidence text bounds | Done |",
            "| AI Trading production evidence artifact-ref bounds | Done |",
            "| AI Trading production evidence item IDs | Done |",
            "| AI Trading production evidence path safety | Done |",
            "| AI Trading production evidence note safety | Done |",
            "| AI Trading production evidence summary terms | Done |",
            "| AI Trading production evidence expiry gate | Done |",
            "| AI Trading production evidence expiry window | Done |",
            "| AI Trading production evidence cutover approval ref | Done |",
            "| AI Trading production evidence future timestamp guard | Done |",
            "| AI Trading production evidence validation age guard | Done |",
            "| AI Trading production evidence cutover window guard | Done |",
            "| AI Trading production evidence run id guard | Done |",
            "| AI Trading production evidence run id traceability | Done |",
            "| AI Trading production evidence item artifact traceability | Done |",
            "| AI Trading production evidence artifact ref uniqueness | Done |",
            "| AI Trading production evidence artifact ref item uniqueness | Done |",
            "| AI Trading production evidence blocker labels | Done |",
            "| AI Trading production evidence template blocker labels | Done |",
            "| AI Trading production evidence explain root blocker labels | Done |",
            "| AI Trading production evidence progress summary | Done |",
            "| AI Trading production evidence progress actions | Done |",
            "| AI Trading production evidence progress root actions | Done |",
            "| AI Trading production evidence dry-run safety metadata | Done |",
            "| AI Trading production evidence non-object dry-run safety | Done |",
            "| AI Trading production evidence frontend error safety | Done |",
            "| AI Trading admin AI runtime last-error redaction | Done |",
            "| AI Trading AI stream polling error redaction | Done |",
            "| AI Trading frontend AI stream polling error safety | Done |",
            "| AI Trading frontend AI runtime error safety | Done |",
            "| AI Trading frontend production-readiness error safety | Done |",
            "| AI Trading frontend strategy-action error safety | Done |",
            "| AI Trading frontend backtest metrics JSON error safety | Done |",
            "| AI Trading frontend backtest summary inline no-prompt | Done |",
            "| AI Trading frontend program backtest inline no-prompt | Done |",
            "| AI Trading frontend program backtest run inline confirm | Done |",
            "| AI Trading frontend signal handoff inline confirm | Done |",
            "| AI Trading frontend agent-session archive inline confirm | Done |",
            "| AI Trading Hyperliquid wallet delete inline confirm | Done |",
            "| AI Trading Binance wallet delete inline confirm | Done |",
            "| AI Trading frontend prompt-packet sanitizer | Done |",
            "| AI Trading frontend handoff error safety | Done |",
            "| AI Trading frontend agent-session error safety | Done |",
            "| AI Trading local supervisor fork-pressure resilience | Done |",
            "| AI Trading env-check Docker probe fallback | Done |",
            "| AI Trading local acceptance transient retry | Done |",
            "| AI Trading production evidence initializer | Done |",
            "| AI Trading aggregate production evidence initializer gate | Done |",
            "| AI Trading production evidence explain mode | Done |",
            "| AI Trading aggregate production evidence explain gate | Done |",
            "| AI Trading admin production evidence explain API | Done |",
            "| AI Trading admin production evidence UI | Done |",
            "| AI Trading admin production evidence validation API | Done |",
            "| AI Trading admin production evidence validation UI | Done |",
            "| AI Trading admin production evidence template API | Done |",
            "| AI Trading admin production evidence template UI | Done |",
            "| AI Trading production evidence template guidance | Done |",
            "| AI Trading production evidence validation guidance | Done |",
            "| AI Trading production evidence root guidance | Done |",
            "| AI Trading production evidence root actions | Done |",
            "| AI Trading admin production evidence payload bounds | Done |",
            "| AI Trading agent-session response context redaction | Done |",
            "| AI Trading frontend session context prompt sanitizer | Done |",
            "| AI Trading model-adjust untrusted context boundary | Done |",
            "| AI Trading model-adjust output sanitizer | Done |",
            "| AI Trading frontend model-adjust output safety | Done |",
            "| AI Trading frontend validation warning labels | Done |",
            "| AI Trading model readiness UI source guard | Done |",
            "| AI Trading model readiness next actions | Done |",
            "| AI Trading model setup shortcut | Done |",
            "| AI Trading model setup runtime refresh | Done |",
            "| AI Trading frontend model-config error safety | Done |",
            "| AI Trading frontend onboarding error safety | Done |",
            "| AI Trading frontend onboarding blank-page guard | Done |",
            "| AI Trading frontend model-config nonblocking entry | Done |",
            "| AI Trading frontend onboarding API-key deferral | Done |",
            "| AI Trading frontend public asset path guard | Done |",
            "| AI Trading frontend bot/tool config error safety | Done |",
            "| AI Trading frontend market-universe error safety | Done |",
            "| AI Trading frontend market symbol sanitizer | Done |",
            "| AI Trading K-line local DB API | Done |",
            "| AI Trading K-line collector/backfill safety | Done |",
            "| AI Trading K-line maintenance endpoint safety | Done |",
            "| AI Trading private factor per-user result schema | Done |",
            "| AI Trading private factor precompute writer-reader | Done |",
            "| AI Trading private factor precompute DB smoke | Done |",
            "| AI Trading agent-session id safety | Done |",
            "| AI Trading agent-session id validation error safety | Done |",
            "| AI Trading agent-session name safety | Done |",
            "| AI Trading strategy-spec name safety | Done |",
            "| AI Trading handoff error-message safety | Done |",
            "| AI Trading handoff confirmation-source safety | Done |",
            "| AI Trading signal rejection reason safety | Done |",
            "| AI Trading backtest evidence safety | Done |",
            "| AI Trading market context safety | Done |",
            "| AI Trading strategy text source safety | Done |",
            "| AI Trading gateway mode guard | Done |",
            "| AI Trading runtime mirror freshness gate | Done |",
            "| AI Trading runtime readiness cold-start retry | Done |",
            "| AI Trading runtime readiness retry grace | Done |",
            "| AI Trading agent-session manual context secret rejection | Done |",
            "| AI Trading env-check runtime context budget gate | Done |",
            "| AI Trading runtime budget UI source guard | Done |",
            "| AI Trading completion audit git governance gate | Done |",
            "| AI Trading local completion summary gate | Done |",
            "| AI Trading production operator preflight | Done |",
            "| AI Trading production operator preflight dirty-tree blocker | Done |",
            "| AI Trading production operator preflight output redaction | Done |",
            "| AI Trading production URL host secret redaction | Done |",
            "| AI Trading production URL port safety | Done |",
            "| AI Trading production URL parse-error safety | Done |",
            "| Remote push | Done | Branch pushed to origin/codex/ai-agent-multitenant-foundation; no merge performed |",
        ),
    ),
    EvidenceRequirement(
        id="signal_only_gateway_contract",
        track="safety",
        description="Gateway contract keeps AI Trading signal-only and requires the order backend to be the only real order authority.",
        path="docs/hyperalpha/ai-trading-signal-gateway-contract.md",
        required_phrases=(
            "AI Trading emits reviewed trade signals only",
            "AI agent and AI Trading API must not place exchange orders directly",
            "order_backend_only",
            "not_an_order=true",
            "ai_may_place_orders=false",
            "requires_user_confirmation=true",
            "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
        ),
    ),
    EvidenceRequirement(
        id="development_governance",
        track="governance",
        description="Development governance requires memory compression, testing before acceptance, and branch separation.",
        path="docs/hyperalpha/development-governance.zh-CN.md",
        required_phrases=(
            "先做上下文记忆压缩，再开发",
            "测试未通过不能验收",
            "未验收不能标记完成",
            "GitHub 上传必须走分支管理，不直接合并",
            "implemented != done",
            "accepted 才能进入完成清单",
        ),
    ),
)


EXTERNAL_REQUIREMENTS: tuple[EvidenceRequirement, ...] = (
    EvidenceRequirement(
        id="macos_reboot_recovery",
        track="external_acceptance",
        description="Physical macOS reboot recovery must be proven outside the current local session.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("实际 macOS 整机重启后的自动恢复还未物理验收",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="real_model_profile_live_acceptance",
        track="external_acceptance",
        description="Real DeepSeek/Qwen model-adjust must be accepted with a user Hyper AI profile/API key.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实 DeepSeek/Qwen API key live model-adjust 未验收",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="real_order_backend_handoff",
        track="external_acceptance",
        description="Real HyperAlpha order-backend URL/token handoff must be accepted before production live orders.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实 HyperAlpha 订单后端 URL/token live handoff 未验收",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="production_auth_hard_risk_readiness",
        track="external_acceptance",
        description="Production Auth/JWKS, hard-risk values, and handoff approval must be validated with real deployment config.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实 HTTPS 订单后端 URL/token、真实 Auth/JWKS、硬风控生产值",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="admin_readiness_real_auth_visual",
        track="external_acceptance",
        description="Settings Admin readiness panel must be visually accepted under real auth/admin login.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实登录态/真实 Auth 配置下的可视化验收未做",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="production_agent_session_visual",
        track="external_acceptance",
        description="Agent-session detail page must be accepted under real production login state.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实生产登录态下的 session 详情页验收另行处理",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="real_exchange_execution",
        track="external_acceptance",
        description="Real exchange execution is outside local V1 and must use a separate production live-trading acceptance.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实交易所执行不属于 V1 本地验收完成条件",),
        status_if_present="out_of_local_v1_scope",
    ),
)


def _read_text(repo_root: Path, relative_path: str) -> str | None:
    path = repo_root / relative_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _evaluate_requirement(repo_root: Path, requirement: EvidenceRequirement) -> dict[str, Any]:
    text = _read_text(repo_root, requirement.path)
    missing_phrases: list[str] = []
    missing_patterns: list[str] = []
    if text is None:
        missing_phrases = list(requirement.required_phrases)
        missing_patterns = list(requirement.required_patterns)
        status = "missing_evidence_file"
    else:
        missing_phrases = [phrase for phrase in requirement.required_phrases if phrase not in text]
        missing_patterns = [pattern for pattern in requirement.required_patterns if re.search(pattern, text) is None]
        status = requirement.status_if_present if not missing_phrases and not missing_patterns else "incomplete_evidence"

    return {
        "id": requirement.id,
        "track": requirement.track,
        "description": requirement.description,
        "status": status,
        "path": requirement.path,
        "missing_phrases": missing_phrases,
        "missing_patterns": missing_patterns,
        **requirement.metadata,
    }


def _latest_memory_report(repo_root: Path) -> dict[str, Any]:
    latest_path = "docs/hyperalpha/memory/latest.md"
    latest_text = _read_text(repo_root, latest_path)
    if latest_text is None:
        return {
            "id": "latest_memory_pointer",
            "track": "governance",
            "status": "missing_evidence_file",
            "path": latest_path,
            "description": "latest.md must point to the latest compressed development memory.",
            "missing_phrases": ["Current:"],
            "missing_patterns": [],
        }

    match = re.search(r"Current:\s*`?([^`\n]+)`?", latest_text)
    memory_file = match.group(1).strip() if match else ""
    memory_path = f"docs/hyperalpha/memory/{memory_file}" if memory_file else ""
    memory_text = _read_text(repo_root, memory_path) if memory_path else None
    required_memory_phrases = (
        "GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation",
        EXPECTED_LOCAL_DEVELOPMENT_BRANCH,
        "已 push，不 merge",
        "default production readiness DB-audit blocker",
        "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
        "真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key",
    )
    missing_phrases = ["Current:"] if not match else []
    if memory_text is None:
        status = "missing_evidence_file"
        missing_phrases.extend(required_memory_phrases)
    else:
        missing_phrases.extend([phrase for phrase in required_memory_phrases if phrase not in memory_text])
        status = "accepted" if not missing_phrases else "incomplete_evidence"

    return {
        "id": "latest_memory_pointer",
        "track": "governance",
        "description": "latest.md points to compressed memory that records the latest local acceptance and external blockers.",
        "status": status,
        "path": latest_path,
        "memory_path": memory_path or None,
        "missing_phrases": missing_phrases,
        "missing_patterns": [],
    }


def _read_git_branch(repo_root: Path) -> dict[str, Any]:
    git_metadata_path = repo_root / ".git"
    if not git_metadata_path.exists():
        return {"branch": None, "detached": False, "metadata_available": False}

    git_dir = git_metadata_path
    if git_metadata_path.is_file():
        gitdir_text = git_metadata_path.read_text(encoding="utf-8", errors="replace").strip()
        if not gitdir_text.startswith("gitdir:"):
            return {"branch": None, "detached": False, "metadata_available": False}
        git_dir = (repo_root / gitdir_text.removeprefix("gitdir:").strip()).resolve()

    head_path = git_dir / "HEAD"
    try:
        head_text = head_path.read_text(encoding="utf-8", errors="replace").strip()
    except FileNotFoundError:
        return {"branch": None, "detached": False, "metadata_available": False}

    if head_text.startswith("ref: refs/heads/"):
        return {
            "branch": head_text.removeprefix("ref: refs/heads/"),
            "detached": False,
            "metadata_available": True,
        }
    return {"branch": None, "detached": bool(head_text), "metadata_available": True}


def _git_governance_report(repo_root: Path) -> dict[str, Any]:
    branch_report = _read_git_branch(repo_root)
    acceptance_text = _read_text(repo_root, "docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md") or ""
    status_text = _read_text(repo_root, "docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md") or ""
    latest_memory = _latest_memory_report(repo_root)
    memory_path = latest_memory.get("memory_path")
    memory_text = _read_text(repo_root, str(memory_path)) if memory_path else ""
    memory_text = memory_text or ""
    blockers: list[str] = []

    if not branch_report["metadata_available"]:
        blockers.append("git_metadata_unavailable")
    elif branch_report["detached"]:
        blockers.append("detached_head")
    elif branch_report["branch"] != EXPECTED_LOCAL_DEVELOPMENT_BRANCH:
        blockers.append("unexpected_branch")

    if f"`{EXPECTED_LOCAL_DEVELOPMENT_BRANCH}` 分支开发" not in acceptance_text:
        blockers.append("acceptance_checklist_missing_local_branch_boundary")
    if "GitHub 上传已同步到 origin/codex/ai-agent-multitenant-foundation" not in acceptance_text:
        blockers.append("acceptance_checklist_missing_github_upload_synced_boundary")
    if f"Branch: `{EXPECTED_LOCAL_DEVELOPMENT_BRANCH}`" not in status_text:
        blockers.append("status_missing_expected_branch")
    if "| Remote push | Done | Branch pushed to origin/codex/ai-agent-multitenant-foundation; no merge performed |" not in status_text:
        blockers.append("status_missing_remote_push_synced")
    if EXPECTED_LOCAL_DEVELOPMENT_BRANCH not in memory_text or "已 push，不 merge" not in memory_text:
        blockers.append("latest_memory_missing_branch_or_no_merge_boundary")

    return {
        "id": "git_governance",
        "track": "governance",
        "description": "Local V1 must stay on the approved codex branch, with GitHub upload synced to the remote feature branch and no merge boundary recorded.",
        "status": "accepted" if not blockers else "incomplete_evidence",
        "path": ".git/HEAD",
        "expected_branch": EXPECTED_LOCAL_DEVELOPMENT_BRANCH,
        "expected_remote_tracking_branch": EXPECTED_REMOTE_TRACKING_BRANCH,
        "current_branch": branch_report["branch"],
        "detached": branch_report["detached"],
        "github_upload": EXPECTED_GITHUB_UPLOAD_STATUS,
        "blockers": blockers,
        "missing_phrases": [],
        "missing_patterns": [],
    }


def _secret_pattern_hits(value: Any) -> list[str]:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    hits: list[str] = []
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(serialized):
            hits.append(pattern.pattern)
    return hits


def _artifact_ref_blockers(
    ref: Any,
    *,
    evidence_run_id: str | None = None,
    item_id: str | None = None,
) -> list[str]:
    if not isinstance(ref, str) or not ref.strip():
        return ["external_evidence_artifact_ref_must_be_non_empty_string"]
    ref_text = ref.strip()
    if len(ref_text) > MAX_PRODUCTION_EVIDENCE_ARTIFACT_REF_CHARS:
        return ["external_evidence_artifact_ref_too_long"]
    if _secret_pattern_hits(ref_text):
        return ["external_evidence_artifact_ref_secret_pattern_detected"]

    parsed = urlparse(ref_text)
    blockers: list[str] = []
    if evidence_run_id and evidence_run_id not in ref_text:
        blockers.append("external_evidence_artifact_ref_missing_run_id")
    if item_id and item_id not in ref_text:
        blockers.append("external_evidence_artifact_ref_missing_item_id")
    if parsed.scheme not in SAFE_ARTIFACT_REF_SCHEMES:
        blockers.append("external_evidence_artifact_ref_scheme_not_allowed")
    if parsed.username or parsed.password:
        blockers.append("external_evidence_artifact_ref_credentials_embedded")
    if parsed.scheme in {"http", "https"}:
        host = parsed.hostname or ""
        if not host:
            blockers.append("external_evidence_artifact_ref_host_missing")
        else:
            host_lower = host.lower()
            if host_lower in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host_lower.endswith(".local"):
                blockers.append("external_evidence_artifact_ref_local_host")
            try:
                ip = ipaddress.ip_address(host_lower)
            except ValueError:
                ip = None
            if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
                blockers.append("external_evidence_artifact_ref_private_or_reserved_ip")
    return blockers


def _cutover_approval_ref_blockers(ref: Any, *, evidence_run_id: str | None = None) -> list[str]:
    if not isinstance(ref, str) or not ref.strip():
        return ["external_evidence_cutover_approval_ref_missing"]
    return [
        blocker.replace("external_evidence_artifact_ref_", "external_evidence_cutover_approval_ref_", 1)
        for blocker in _artifact_ref_blockers(ref, evidence_run_id=evidence_run_id)
    ]


def _evidence_run_id_blockers(value: Any) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return ["external_evidence_run_id_missing"]

    run_id = value.strip()
    blockers: list[str] = []
    normalized = re.sub(r"\s+", " ", run_id).casefold()
    if normalized in PLACEHOLDER_EVIDENCE_VALUES:
        blockers.append("external_evidence_run_id_placeholder")
    if len(run_id) < MIN_PRODUCTION_EVIDENCE_RUN_ID_CHARS:
        blockers.append("external_evidence_run_id_too_short")
    if len(run_id) > MAX_PRODUCTION_EVIDENCE_RUN_ID_CHARS:
        blockers.append("external_evidence_run_id_too_long")
    if PRODUCTION_EVIDENCE_RUN_ID_PATTERN.fullmatch(run_id) is None:
        blockers.append("external_evidence_run_id_invalid_chars")
    if _secret_pattern_hits(run_id):
        blockers.append("external_evidence_run_id_secret_pattern_detected")
    return blockers


def _valid_evidence_run_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    run_id = value.strip()
    return run_id if run_id and not _evidence_run_id_blockers(run_id) else None


def _cutover_window_report(
    window: Any,
    *,
    generated_at_utc: datetime | None,
    now_utc: datetime,
) -> dict[str, Any]:
    report = {
        "present": False,
        "start_at": None,
        "end_at": None,
        "blockers": [],
        "unexpected_fields": [],
    }
    blockers: list[str] = report["blockers"]

    if not isinstance(window, dict):
        blockers.append("external_evidence_cutover_window_missing")
        return report

    report["present"] = True
    unexpected_fields = _unexpected_fields(window, ALLOWED_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_FIELDS)
    report["unexpected_fields"] = unexpected_fields
    if unexpected_fields:
        blockers.append("external_evidence_cutover_window_unexpected_fields")

    start_at_utc, start_blockers = _parse_iso_timestamp(
        window.get("start_at"),
        "cutover_window_start_at",
    )
    end_at_utc, end_blockers = _parse_iso_timestamp(
        window.get("end_at"),
        "cutover_window_end_at",
    )
    blockers.extend(start_blockers)
    blockers.extend(end_blockers)
    report["start_at"] = window.get("start_at") if isinstance(window.get("start_at"), str) else None
    report["end_at"] = window.get("end_at") if isinstance(window.get("end_at"), str) else None

    if start_at_utc is None or end_at_utc is None:
        return report
    if end_at_utc <= start_at_utc:
        blockers.append("external_evidence_cutover_window_end_not_after_start")
    if end_at_utc - start_at_utc > timedelta(hours=MAX_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_HOURS):
        blockers.append("external_evidence_cutover_window_too_long")
    if now_utc < start_at_utc - timedelta(seconds=MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS):
        blockers.append("external_evidence_cutover_window_not_started")
    if now_utc > end_at_utc:
        blockers.append("external_evidence_cutover_window_ended")
    if generated_at_utc is not None:
        if generated_at_utc < start_at_utc - timedelta(seconds=MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS):
            blockers.append("external_evidence_generated_at_before_cutover_window")
        if generated_at_utc > end_at_utc + timedelta(seconds=MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS):
            blockers.append("external_evidence_generated_at_after_cutover_window")

    return report


def _parse_iso_timestamp(value: Any, field_name: str) -> tuple[datetime | None, list[str]]:
    if not isinstance(value, str) or not value.strip():
        return None, [f"external_evidence_{field_name}_missing"]
    timestamp = value.strip()
    if "T" not in timestamp:
        return None, [f"external_evidence_{field_name}_invalid"]
    normalized = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, [f"external_evidence_{field_name}_invalid"]
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, [f"external_evidence_{field_name}_timezone_missing"]
    return parsed.astimezone(timezone.utc), []


def _unexpected_fields(payload: dict[str, Any], allowed_fields: set[str]) -> list[str]:
    return sorted(str(field) for field in payload if field not in allowed_fields)


def _evidence_notes_blockers(notes: Any) -> list[str]:
    if notes is None:
        return []
    if not isinstance(notes, list):
        return ["external_evidence_notes_must_be_list"]

    blockers: list[str] = []
    if len(notes) > MAX_PRODUCTION_EVIDENCE_NOTES:
        blockers.append("external_evidence_notes_too_many")
    for note in notes:
        if not isinstance(note, str) or not note.strip():
            blockers.append("external_evidence_note_must_be_non_empty_string")
            continue
        if len(note.strip()) > MAX_PRODUCTION_EVIDENCE_NOTE_CHARS:
            blockers.append("external_evidence_note_too_long")
    return blockers


def _evidence_text_quality_blockers(
    value: Any,
    field_name: str,
    *,
    min_chars: int = 3,
    max_chars: int | None = None,
) -> list[str]:
    if not isinstance(value, str):
        return [f"external_evidence_{field_name}_missing"]
    text = value.strip()
    if not text:
        return [f"external_evidence_{field_name}_missing"]

    blockers: list[str] = []
    normalized = re.sub(r"\s+", " ", text).casefold()
    if normalized in PLACEHOLDER_EVIDENCE_VALUES:
        blockers.append(f"external_evidence_{field_name}_placeholder")
    if len(text) < min_chars:
        blockers.append(f"external_evidence_{field_name}_too_short")
    if max_chars is not None and len(text) > max_chars:
        blockers.append(f"external_evidence_{field_name}_too_long")
    return blockers


def _summary_term_label(term_group: tuple[str, ...]) -> str:
    return " / ".join(term_group)


def _summary_term_blocker_label(term_group: tuple[str, ...]) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", term_group[0].casefold()).strip("_")
    return normalized or "required_term"


def _missing_required_summary_terms(item_id: str, evidence_summary: Any) -> list[str]:
    if not isinstance(evidence_summary, str) or not evidence_summary.strip():
        return []

    normalized_summary = re.sub(r"\s+", " ", evidence_summary).casefold()
    missing_terms: list[str] = []
    for term_group in PRODUCTION_EVIDENCE_ITEM_REQUIRED_SUMMARY_TERMS.get(item_id, ()):
        if any(term.casefold() in normalized_summary for term in term_group):
            continue
        missing_terms.append(_summary_term_label(term_group))
    return missing_terms


def _validate_external_evidence_item(
    item_id: str,
    item: Any,
    *,
    generated_at_utc: datetime | None = None,
    now_utc: datetime | None = None,
    evidence_run_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "id": item_id,
            "ready": False,
            "status": "missing",
            "blockers": ["external_evidence_item_missing"],
            "warnings": [],
        }

    blockers: list[str] = []
    warnings: list[str] = []
    unexpected_item_fields = _unexpected_fields(item, ALLOWED_PRODUCTION_EVIDENCE_ITEM_FIELDS)
    if unexpected_item_fields:
        blockers.append("external_evidence_unexpected_item_fields")
    status = str(item.get("status") or "")
    if status != "accepted":
        blockers.append("external_evidence_item_not_accepted")
    validated_at_utc, timestamp_blockers = _parse_iso_timestamp(item.get("validated_at"), "validated_at")
    blockers.extend(timestamp_blockers)
    if generated_at_utc is not None and validated_at_utc is not None and validated_at_utc > generated_at_utc:
        blockers.append("external_evidence_validated_at_after_generated_at")
    if (
        generated_at_utc is not None
        and validated_at_utc is not None
        and generated_at_utc - validated_at_utc > timedelta(days=MAX_PRODUCTION_EVIDENCE_ITEM_VALIDATION_AGE_DAYS)
    ):
        blockers.append("external_evidence_validated_at_too_old")
    if (
        now_utc is not None
        and validated_at_utc is not None
        and validated_at_utc > now_utc + timedelta(seconds=MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS)
    ):
        blockers.append("external_evidence_validated_at_in_future")
    blockers.extend(
        _evidence_text_quality_blockers(
            item.get("validated_by"),
            "validated_by",
            max_chars=MAX_PRODUCTION_EVIDENCE_VALIDATOR_CHARS,
        )
    )
    blockers.extend(
        _evidence_text_quality_blockers(
            item.get("evidence_summary"),
            "summary",
            min_chars=MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
            max_chars=MAX_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
        )
    )
    missing_summary_terms: list[str] = []
    if status == "accepted":
        missing_summary_terms = _missing_required_summary_terms(item_id, item.get("evidence_summary"))
        blockers.extend(
            "external_evidence_summary_missing_required_term:"
            + _summary_term_blocker_label((term.split(" / ", 1)[0],))
            for term in missing_summary_terms
        )
    artifact_refs = item.get("artifact_refs")
    if artifact_refs is None:
        blockers.append("external_evidence_artifact_refs_missing")
    elif not isinstance(artifact_refs, list):
        blockers.append("external_evidence_artifact_refs_must_be_list")
    elif not artifact_refs:
        blockers.append("external_evidence_artifact_refs_empty")
    else:
        if len(artifact_refs) > MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS:
            blockers.append("external_evidence_artifact_refs_too_many")
        ref_texts = _non_empty_artifact_ref_texts(item)
        if len(set(ref_texts)) < len(ref_texts):
            blockers.append("external_evidence_artifact_ref_duplicate_in_item")
        for ref in artifact_refs:
            blockers.extend(_artifact_ref_blockers(ref, evidence_run_id=evidence_run_id, item_id=item_id))
    if item.get("secret_values_returned") is not False:
        blockers.append("external_evidence_secret_values_returned_must_be_false")

    secret_hits = _secret_pattern_hits(item)
    if secret_hits:
        blockers.append("external_evidence_secret_pattern_detected")

    return {
        "id": item_id,
        "ready": not blockers,
        "status": status or "missing",
        "blockers": blockers,
        "warnings": warnings,
        "artifact_ref_count": len(artifact_refs) if isinstance(artifact_refs, list) else 0,
        "secret_pattern_count": len(secret_hits),
        "unexpected_fields": unexpected_item_fields,
        "missing_summary_terms": missing_summary_terms,
    }


def _non_empty_artifact_ref_texts(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return []
    artifact_refs = item.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        return []
    return [ref.strip() for ref in artifact_refs if isinstance(ref, str) and ref.strip()]


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _empty_external_evidence_report(
    *,
    provided: bool,
    path: str | None,
    blockers: list[str] | None = None,
    secret_pattern_count: int = 0,
) -> dict[str, Any]:
    return {
        "provided": provided,
        "path": path,
        "ready": False,
        "version": None,
        "evidence_run_id_present": False,
        "expires_at": None,
        "cutover_window_present": False,
        "cutover_window_start_at": None,
        "cutover_window_end_at": None,
        "cutover_approval_ref_present": False,
        "accepted_count": 0,
        "required_count": len(EXTERNAL_REQUIREMENTS),
        "blockers": blockers or [],
        "warnings": [],
        "items": [],
        "secret_pattern_count": secret_pattern_count,
    }


def _validate_external_evidence_payload(
    payload: Any,
    *,
    path: str | None = None,
    file_inside_repo: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    now_utc = datetime.now(timezone.utc)

    if not isinstance(payload, dict):
        secret_hits = _secret_pattern_hits(payload)
        non_object_blockers = ["external_evidence_root_must_be_object"]
        if secret_hits:
            non_object_blockers.append("external_evidence_secret_pattern_detected")
        return _empty_external_evidence_report(
            provided=True,
            path=path,
            blockers=non_object_blockers,
            secret_pattern_count=len(secret_hits),
        )

    version = payload.get("version")
    if file_inside_repo:
        blockers.append("external_evidence_file_must_be_outside_repo")
    unexpected_root_fields = _unexpected_fields(payload, ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS)
    if unexpected_root_fields:
        blockers.append("external_evidence_unexpected_root_fields")
    if version != EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION:
        blockers.append("external_evidence_version_mismatch")
    evidence_run_id = payload.get("evidence_run_id")
    evidence_run_id_blockers = _evidence_run_id_blockers(evidence_run_id)
    blockers.extend(evidence_run_id_blockers)
    valid_evidence_run_id = _valid_evidence_run_id(evidence_run_id) if not evidence_run_id_blockers else None
    generated_at_utc, timestamp_blockers = _parse_iso_timestamp(payload.get("generated_at"), "generated_at")
    blockers.extend(timestamp_blockers)
    expires_at_utc, expires_at_blockers = _parse_iso_timestamp(payload.get("expires_at"), "expires_at")
    blockers.extend(expires_at_blockers)
    if (
        generated_at_utc is not None
        and generated_at_utc > now_utc + timedelta(seconds=MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS)
    ):
        blockers.append("external_evidence_generated_at_in_future")
    if generated_at_utc is not None and expires_at_utc is not None and expires_at_utc <= generated_at_utc:
        blockers.append("external_evidence_expires_at_not_after_generated_at")
    if (
        generated_at_utc is not None
        and expires_at_utc is not None
        and expires_at_utc > generated_at_utc + timedelta(days=MAX_PRODUCTION_EVIDENCE_VALIDITY_DAYS)
    ):
        blockers.append("external_evidence_expires_at_too_far")
    if expires_at_utc is not None and expires_at_utc <= now_utc:
        blockers.append("external_evidence_expired")
    cutover_window = _cutover_window_report(
        payload.get("cutover_window"),
        generated_at_utc=generated_at_utc,
        now_utc=now_utc,
    )
    blockers.extend(cutover_window["blockers"])
    if payload.get("secret_values_returned") is not False:
        blockers.append("external_evidence_secret_values_returned_must_be_false")
    cutover_approval_ref = payload.get("cutover_approval_ref")
    blockers.extend(_cutover_approval_ref_blockers(cutover_approval_ref, evidence_run_id=valid_evidence_run_id))
    blockers.extend(_evidence_notes_blockers(payload.get("notes")))

    secret_hits = _secret_pattern_hits(payload)
    if secret_hits:
        blockers.append("external_evidence_secret_pattern_detected")

    required_ids = [requirement.id for requirement in EXTERNAL_REQUIREMENTS]
    items_payload = payload.get("items")
    unexpected_item_ids: list[str] = []
    if not isinstance(items_payload, dict):
        blockers.append("external_evidence_items_must_be_object")
        items_payload = {}
    else:
        unexpected_item_ids = sorted(str(item_id) for item_id in items_payload if item_id not in required_ids)
        if unexpected_item_ids:
            blockers.append("external_evidence_unexpected_item_ids")

    item_reports = [
        _validate_external_evidence_item(
            item_id,
            items_payload.get(item_id),
            generated_at_utc=generated_at_utc,
            now_utc=now_utc,
            evidence_run_id=valid_evidence_run_id,
        )
        for item_id in required_ids
    ]
    item_reports_by_id = {item["id"]: item for item in item_reports}
    artifact_ref_item_ids: dict[str, set[str]] = {}
    for item_id in required_ids:
        for ref_text in _non_empty_artifact_ref_texts(items_payload.get(item_id)):
            artifact_ref_item_ids.setdefault(ref_text, set()).add(item_id)
    duplicate_artifact_ref_item_ids = [
        sorted(item_ids)
        for item_ids in artifact_ref_item_ids.values()
        if len(item_ids) > 1
    ]
    for item_ids in duplicate_artifact_ref_item_ids:
        for item_id in item_ids:
            item_report = item_reports_by_id.get(item_id)
            if not item_report:
                continue
            if "external_evidence_artifact_ref_reused_across_items" not in item_report["blockers"]:
                item_report["blockers"].append("external_evidence_artifact_ref_reused_across_items")
            item_report["ready"] = False
    accepted_count = sum(1 for item in item_reports if item["ready"])
    item_blockers = [item["id"] for item in item_reports if not item["ready"]]
    if item_blockers:
        blockers.extend([f"external_evidence_item_blocked:{item_id}" for item_id in item_blockers])
    for item in item_reports:
        warnings.extend([f"{item['id']}:{warning}" for warning in item["warnings"]])

    return {
        "provided": True,
        "path": path,
        "ready": not blockers,
        "version": version,
        "evidence_run_id_present": isinstance(evidence_run_id, str) and bool(evidence_run_id.strip()),
        "accepted_count": accepted_count,
        "required_count": len(required_ids),
        "blockers": blockers,
        "warnings": warnings,
        "items": item_reports,
        "secret_pattern_count": len(secret_hits),
        "unexpected_fields": unexpected_root_fields,
        "unexpected_item_ids": unexpected_item_ids,
        "file_inside_repo": file_inside_repo,
        "notes_count": len(payload.get("notes")) if isinstance(payload.get("notes"), list) else 0,
        "expires_at": payload.get("expires_at") if isinstance(payload.get("expires_at"), str) else None,
        "cutover_window_present": cutover_window["present"],
        "cutover_window_start_at": cutover_window["start_at"],
        "cutover_window_end_at": cutover_window["end_at"],
        "cutover_window_unexpected_fields": cutover_window["unexpected_fields"],
        "cutover_approval_ref_present": isinstance(cutover_approval_ref, str) and bool(cutover_approval_ref.strip()),
    }


def _validate_external_evidence_file(
    production_evidence_file: Path | str | None,
    *,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    if production_evidence_file is None:
        return _empty_external_evidence_report(provided=False, path=None)

    evidence_path = Path(production_evidence_file).resolve()
    repo_root_resolved = Path(repo_root).resolve() if repo_root is not None else None
    evidence_file_inside_repo = (
        repo_root_resolved is not None and _path_is_relative_to(evidence_path, repo_root_resolved)
    )
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _empty_external_evidence_report(
            provided=True,
            path=str(evidence_path),
            blockers=["external_evidence_file_missing"],
        )
    except json.JSONDecodeError:
        return _empty_external_evidence_report(
            provided=True,
            path=str(evidence_path),
            blockers=["external_evidence_json_invalid"],
        )

    return _validate_external_evidence_payload(
        payload,
        path=str(evidence_path),
        file_inside_repo=evidence_file_inside_repo,
    )


def validate_external_acceptance_evidence_payload(payload: Any) -> dict[str, Any]:
    """Validate a submitted evidence JSON object without accepting file paths or enabling live orders."""
    return _validate_external_evidence_payload(payload, path=None, file_inside_repo=False)


def build_external_acceptance_evidence_template() -> dict[str, Any]:
    """Build a pending, secret-free external production evidence skeleton."""
    return {
        "version": EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "evidence_run_id": None,
        "generated_at": None,
        "expires_at": None,
        "cutover_window": {
            "start_at": None,
            "end_at": None,
        },
        "cutover_approval_ref": None,
        "secret_values_returned": False,
        "notes": list(PRODUCTION_EVIDENCE_TEMPLATE_NOTES),
        "items": {
            requirement.id: {
                "status": "pending_external_acceptance",
                "validated_at": None,
                "validated_by": None,
                "evidence_summary": "",
                "artifact_refs": [],
                "secret_values_returned": False,
            }
            for requirement in EXTERNAL_REQUIREMENTS
        },
    }


def build_external_acceptance_evidence_template_guidance() -> dict[str, Any]:
    """Build non-secret operator guidance for filling the pending evidence template."""
    root_fields = [
        {
            "field": item["field"],
            "required_value": item["required_value"],
            "related_blockers": list(item["related_blockers"]),
            "operator_guidance": list(item["operator_guidance"]),
            "forbidden_values": list(PRODUCTION_EVIDENCE_COMMON_FORBIDDEN),
        }
        for item in PRODUCTION_EVIDENCE_ROOT_GUIDANCE
    ]
    items: list[dict[str, Any]] = []
    for requirement in EXTERNAL_REQUIREMENTS:
        guidance = list(PRODUCTION_EVIDENCE_ITEM_GUIDANCE.get(requirement.id, ()))
        items.append(
            {
                "id": requirement.id,
                "description": requirement.description,
                "required_fields": list(PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS),
                "required_summary_terms": [
                    _summary_term_label(term_group)
                    for term_group in PRODUCTION_EVIDENCE_ITEM_REQUIRED_SUMMARY_TERMS.get(requirement.id, ())
                ],
                "operator_guidance": guidance,
                "safe_artifact_ref_schemes": sorted(SAFE_ARTIFACT_REF_SCHEMES),
                "forbidden_values": list(PRODUCTION_EVIDENCE_COMMON_FORBIDDEN),
            }
        )

    return {
        "secret_policy": "metadata_only_no_env_or_credentials",
        "root_fields": root_fields,
        "root_next_required_actions": [
            f"root.{item['field']}: {item['operator_guidance'][0]}"
            for item in root_fields
            if item.get("operator_guidance")
        ],
        "items": items,
        "next_required_actions": [
            f"{item['id']}: {item['operator_guidance'][0]}"
            for item in items
            if item.get("operator_guidance")
        ],
    }


def build_production_evidence_explain(
    repo_root: Path | str,
    *,
    production_evidence_file: Path | str | None = None,
    allow_live_ready_from_evidence: bool = False,
) -> dict[str, Any]:
    """Explain what sanitized external evidence is still needed for live-order readiness."""
    report = build_completion_report(
        repo_root,
        production_evidence_file=production_evidence_file,
        allow_live_ready_from_evidence=allow_live_ready_from_evidence,
    )
    return _build_production_evidence_explain_from_report(report, mode="production_evidence_explain")


def build_production_evidence_payload_validation(repo_root: Path | str, payload: Any) -> dict[str, Any]:
    """Validate a submitted evidence JSON object for admins without unlocking live-order readiness."""
    report = build_completion_report(repo_root)
    production_evidence = validate_external_acceptance_evidence_payload(payload)
    report["production_evidence"] = production_evidence
    report["ready_for_live_orders"] = False
    report["summary"]["production_track"] = (
        "external_evidence_accepted_pending_explicit_confirmation"
        if production_evidence["ready"]
        else "pending_external_acceptance"
    )
    report["summary"]["external_pending_count"] = (
        0 if production_evidence["ready"] else report["summary"]["documented_external_pending_count"]
    )
    report["summary"]["production_evidence_blockers"] = list(production_evidence["blockers"])
    validation = _build_production_evidence_explain_from_report(
        report,
        mode="production_evidence_payload_validation",
    )
    validation["next_actions"] = [
        "Store accepted evidence only in a private ops evidence location outside the code repository.",
        "Re-run validation after each real external acceptance item changes.",
        "Use strict production cutover only during an explicitly approved live-order window.",
    ]
    return validation


def _build_production_evidence_progress(
    report: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    production_evidence = report["production_evidence"]
    accepted_item_ids = [item["id"] for item in items if item["ready"]]
    pending_item_ids = [item["id"] for item in items if not item["ready"]]
    blocked_item_ids = [item["id"] for item in items if item["blockers"]]
    next_required_actions = [
        f"{item['id']}: {item['operator_guidance'][0]}"
        for item in items
        if not item["ready"] and item.get("operator_guidance")
    ]
    root_next_required_actions = _build_production_evidence_progress_root_actions(production_evidence)
    live_order_gate_blockers: list[str] = []

    if not report["local_v1_accepted"]:
        live_order_gate_blockers.append("local_v1_not_accepted")
    if not production_evidence["ready"]:
        live_order_gate_blockers.append("production_evidence_not_ready")
    elif not report["ready_for_live_orders"]:
        live_order_gate_blockers.append("explicit_live_ready_confirmation_required")

    if report["ready_for_live_orders"]:
        status = "live_ready"
    elif production_evidence["ready"]:
        status = "external_evidence_accepted_pending_explicit_confirmation"
    else:
        status = "pending_external_acceptance"

    return {
        "status": status,
        "accepted_item_ids": accepted_item_ids,
        "pending_item_ids": pending_item_ids,
        "blocked_item_ids": blocked_item_ids,
        "next_required_item_ids": pending_item_ids,
        "next_required_actions": next_required_actions,
        "root_next_required_actions": root_next_required_actions,
        "accepted_count": len(accepted_item_ids),
        "pending_count": len(pending_item_ids),
        "blocked_count": len(blocked_item_ids),
        "required_count": len(items),
        "live_order_gate_blockers": live_order_gate_blockers,
    }


def _build_production_evidence_progress_root_actions(production_evidence: dict[str, Any]) -> list[str]:
    """Return safe root-level actions for missing or blocked production evidence fields."""
    blockers = {str(blocker) for blocker in production_evidence.get("blockers") or []}
    include_all_root_fields = production_evidence.get("provided") is not True
    actions: list[str] = []

    if "external_evidence_root_must_be_object" in blockers:
        actions.append("root.schema: Provide evidence as one JSON object using the generated production evidence template.")
    if "external_evidence_unexpected_root_fields" in blockers:
        actions.append("root.schema: Remove unexpected root fields and keep only the generated template root fields.")
    if "external_evidence_file_must_be_outside_repo" in blockers:
        actions.append("evidence_file: Move sanitized production evidence outside the code repository or into a private ops evidence store.")

    for item in PRODUCTION_EVIDENCE_ROOT_GUIDANCE:
        related_blockers = {str(blocker) for blocker in item["related_blockers"]}
        if include_all_root_fields or blockers.intersection(related_blockers):
            actions.append(f"root.{item['field']}: {item['operator_guidance'][0]}")

    return actions


def _build_production_evidence_explain_from_report(
    report: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    production_evidence = report["production_evidence"]
    external_status_by_id = {
        item["id"]: item
        for item in report["external_acceptance"]
    }
    evidence_item_by_id = {
        item["id"]: item
        for item in production_evidence.get("items", [])
        if isinstance(item, dict) and item.get("id")
    }

    items: list[dict[str, Any]] = []
    for requirement in EXTERNAL_REQUIREMENTS:
        evidence_item = evidence_item_by_id.get(requirement.id)
        if evidence_item is None:
            evidence_blockers = [
                "external_evidence_item_not_provided"
                if not production_evidence.get("provided")
                else "external_evidence_item_not_reported"
            ]
            evidence_ready = False
            evidence_status = "not_provided"
            artifact_ref_count = 0
            secret_pattern_count = 0
            unexpected_fields: list[str] = []
        else:
            evidence_blockers = list(evidence_item.get("blockers") or [])
            evidence_ready = bool(evidence_item.get("ready"))
            evidence_status = str(evidence_item.get("status") or "missing")
            artifact_ref_count = int(evidence_item.get("artifact_ref_count") or 0)
            secret_pattern_count = int(evidence_item.get("secret_pattern_count") or 0)
            unexpected_fields = list(evidence_item.get("unexpected_fields") or [])

        documentation_status = external_status_by_id.get(requirement.id, {}).get("status")
        items.append(
            {
                "id": requirement.id,
                "description": requirement.description,
                "documentation_status": documentation_status,
                "evidence_status": evidence_status,
                "ready": evidence_ready,
                "blockers": evidence_blockers,
                "artifact_ref_count": artifact_ref_count,
                "secret_pattern_count": secret_pattern_count,
                "unexpected_fields": unexpected_fields,
                "required_fields": list(PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS),
                "required_summary_terms": [
                    _summary_term_label(term_group)
                    for term_group in PRODUCTION_EVIDENCE_ITEM_REQUIRED_SUMMARY_TERMS.get(requirement.id, ())
                ],
                "missing_summary_terms": list(evidence_item.get("missing_summary_terms") or [])
                if evidence_item is not None
                else [],
                "safe_artifact_ref_schemes": sorted(SAFE_ARTIFACT_REF_SCHEMES),
                "forbidden_values": list(PRODUCTION_EVIDENCE_COMMON_FORBIDDEN),
                "operator_guidance": list(PRODUCTION_EVIDENCE_ITEM_GUIDANCE.get(requirement.id, ())),
            }
        )

    return {
        "mode": mode,
        "version": EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "repo_root": report["repo_root"],
        "github_upload": report["github_upload"],
        "local_v1_accepted": report["local_v1_accepted"],
        "ready_for_live_orders": report["ready_for_live_orders"],
        "production_track": report["summary"]["production_track"],
        "production_evidence": {
            "provided": production_evidence["provided"],
            "path": production_evidence["path"],
            "ready": production_evidence["ready"],
            "evidence_run_id_present": production_evidence.get("evidence_run_id_present", False),
            "accepted_count": production_evidence["accepted_count"],
            "required_count": production_evidence["required_count"],
            "blockers": list(production_evidence["blockers"]),
            "warnings": list(production_evidence["warnings"]),
            "secret_pattern_count": production_evidence.get("secret_pattern_count", 0),
            "file_inside_repo": production_evidence.get("file_inside_repo", False),
            "expires_at": production_evidence.get("expires_at"),
            "cutover_window_present": production_evidence.get("cutover_window_present", False),
            "cutover_window_start_at": production_evidence.get("cutover_window_start_at"),
            "cutover_window_end_at": production_evidence.get("cutover_window_end_at"),
            "cutover_approval_ref_present": production_evidence.get("cutover_approval_ref_present", False),
        },
        "progress": _build_production_evidence_progress(report, items),
        "schema": {
            "allowed_root_fields": sorted(ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS),
            "allowed_item_fields": sorted(ALLOWED_PRODUCTION_EVIDENCE_ITEM_FIELDS),
            "required_root_fields": list(PRODUCTION_EVIDENCE_REQUIRED_ROOT_FIELDS),
            "required_item_ids": [requirement.id for requirement in EXTERNAL_REQUIREMENTS],
            "required_item_fields": list(PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS),
            "safe_artifact_ref_schemes": sorted(SAFE_ARTIFACT_REF_SCHEMES),
            "max_notes": MAX_PRODUCTION_EVIDENCE_NOTES,
            "max_note_chars": MAX_PRODUCTION_EVIDENCE_NOTE_CHARS,
            "max_artifact_refs_per_item": MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS,
            "max_artifact_ref_chars": MAX_PRODUCTION_EVIDENCE_ARTIFACT_REF_CHARS,
            "max_evidence_validity_days": MAX_PRODUCTION_EVIDENCE_VALIDITY_DAYS,
            "max_clock_skew_seconds": MAX_PRODUCTION_EVIDENCE_CLOCK_SKEW_SECONDS,
            "max_item_validation_age_days": MAX_PRODUCTION_EVIDENCE_ITEM_VALIDATION_AGE_DAYS,
            "max_cutover_window_hours": MAX_PRODUCTION_EVIDENCE_CUTOVER_WINDOW_HOURS,
            "min_evidence_run_id_chars": MIN_PRODUCTION_EVIDENCE_RUN_ID_CHARS,
            "max_evidence_run_id_chars": MAX_PRODUCTION_EVIDENCE_RUN_ID_CHARS,
            "summary_chars": {
                "min": MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
                "max": MAX_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
            },
        },
        "items": items,
        "next_actions": [
            "Generate a repo-external skeleton with --init-production-evidence-file if no evidence file exists yet.",
            "Fill only the required schema fields after each real external acceptance is completed.",
            "Keep the filled evidence outside the code repository or in a private ops evidence location.",
            "Run --explain-production-evidence with --production-evidence-file to see item-level blockers before strict production cutover.",
            "Run --strict-production with --allow-live-ready-from-evidence only during an explicitly approved live-order cutover window.",
        ],
    }


def write_external_acceptance_evidence_template(
    output_path: Path | str,
    *,
    repo_root: Path | str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a repo-external evidence skeleton and immediately validate it."""
    root = Path(repo_root).resolve()
    destination = Path(output_path).expanduser().resolve()
    blockers: list[str] = []
    warnings: list[str] = []

    if _path_is_relative_to(destination, root):
        blockers.append("external_evidence_output_must_be_outside_repo")
    if destination.exists() and not overwrite:
        blockers.append("external_evidence_output_exists")
    if destination.suffix.lower() != ".json":
        warnings.append("external_evidence_output_should_use_json_suffix")

    if blockers:
        return {
            "created": False,
            "path": str(destination),
            "repo_root": str(root),
            "blockers": blockers,
            "warnings": warnings,
            "ready_for_live_orders": False,
        }

    payload = build_external_acceptance_evidence_template()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = _validate_external_evidence_file(destination, repo_root=root)
    return {
        "created": True,
        "path": str(destination),
        "repo_root": str(root),
        "blockers": [],
        "warnings": warnings,
        "item_ids": [requirement.id for requirement in EXTERNAL_REQUIREMENTS],
        "production_evidence_ready": validation["ready"],
        "production_evidence_blockers": validation["blockers"],
        "ready_for_live_orders": False,
        "next_actions": [
            "Fill this file only after real external acceptance is completed, then update generated_at and each accepted item.",
            "Keep the filled file outside the code repository or in a private ops evidence location.",
            "Run ai_trading_v1_completion_audit.py with --production-evidence-file against the filled file before any production cutover.",
        ],
    }


def build_completion_report(
    repo_root: Path | str,
    *,
    production_evidence_file: Path | str | None = None,
    allow_live_ready_from_evidence: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    local_items = [_evaluate_requirement(root, requirement) for requirement in LOCAL_REQUIREMENTS]
    governance_items = [_latest_memory_report(root), _git_governance_report(root)]
    external_items = [_evaluate_requirement(root, requirement) for requirement in EXTERNAL_REQUIREMENTS]
    production_evidence = _validate_external_evidence_file(production_evidence_file, repo_root=root)

    local_evidence_items = local_items + governance_items
    local_blockers = [
        item["id"]
        for item in local_evidence_items
        if item["status"] not in {"accepted"}
    ]
    missing_external_markers = [
        item["id"]
        for item in external_items
        if item["status"] in {"missing_evidence_file", "incomplete_evidence"}
    ]
    pending_external_items = [
        item["id"]
        for item in external_items
        if item["status"] in {"pending_external_acceptance", "out_of_local_v1_scope"}
    ]
    local_v1_accepted = not local_blockers and not missing_external_markers
    ready_for_live_orders = (
        local_v1_accepted
        and production_evidence["ready"]
        and allow_live_ready_from_evidence
    )
    if ready_for_live_orders:
        production_track = "accepted"
    elif production_evidence["ready"]:
        production_track = "external_evidence_accepted_pending_explicit_confirmation"
    else:
        production_track = "pending_external_acceptance"
    effective_external_pending_count = 0 if production_evidence["ready"] else len(pending_external_items)

    return {
        "local_v1_accepted": local_v1_accepted,
        "ready_for_live_orders": ready_for_live_orders,
        "github_upload": EXPECTED_GITHUB_UPLOAD_STATUS,
        "git_governance": next(item for item in governance_items if item["id"] == "git_governance"),
        "repo_root": str(root),
        "summary": {
            "local_track": "accepted" if not local_blockers and not missing_external_markers else "incomplete",
            "production_track": production_track,
            "external_pending_count": effective_external_pending_count,
            "documented_external_pending_count": len(pending_external_items),
            "local_blockers": local_blockers,
            "missing_external_markers": missing_external_markers,
            "production_evidence_blockers": list(production_evidence["blockers"]),
        },
        "local_evidence": local_evidence_items,
        "external_acceptance": external_items,
        "production_evidence": production_evidence,
        "next_actions": [
            "Continue local development only on codex/ai-agent-multitenant-foundation; push updates only to the remote feature branch and do not merge without explicit acceptance.",
            "For production live-order acceptance, provide real Auth/JWKS, real order-backend URL/token, hard-risk values, and explicit production handoff approval.",
            "For real model-adjust acceptance, configure a user's Hyper AI DeepSeek/Qwen profile and run the live model-adjust runner with explicit confirmation.",
            "Record external acceptance in a sanitized production evidence JSON file outside the code repository with documented schema fields/item IDs, bounded notes, bounded non-placeholder validated_by and evidence_summary, generated_at/validated_at/expires_at ISO timestamps, and unique item-specific safe artifact refs; do not include API keys, bearer tokens, DB URLs, private keys, or raw authorization headers.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root to audit. Defaults to this script's repository.",
    )
    parser.add_argument("--strict-local", action="store_true", help="Exit 1 unless local V1 evidence is accepted.")
    parser.add_argument(
        "--strict-production",
        action="store_true",
        help="Exit 1 unless production/live-order acceptance has no pending external items.",
    )
    parser.add_argument(
        "--production-evidence-file",
        help="Optional sanitized JSON file with real external production acceptance evidence.",
    )
    parser.add_argument(
        "--allow-live-ready-from-evidence",
        action="store_true",
        help=(
            "Allow ready_for_live_orders=true when local V1 and the production evidence file are both accepted. "
            "Without this explicit flag, accepted evidence is reported but live-order readiness remains false."
        ),
    )
    parser.add_argument(
        "--init-production-evidence-file",
        help=(
            "Create a pending external production evidence skeleton at this path and exit. "
            "The output path must be outside the code repository unless you are editing the checked-in template manually."
        ),
    )
    parser.add_argument(
        "--overwrite-production-evidence-file",
        action="store_true",
        help="Allow --init-production-evidence-file to replace an existing output file.",
    )
    parser.add_argument(
        "--explain-production-evidence",
        action="store_true",
        help="Print a non-secret item-level checklist for the external production evidence file.",
    )
    args = parser.parse_args()

    if args.init_production_evidence_file:
        init_report = write_external_acceptance_evidence_template(
            args.init_production_evidence_file,
            repo_root=args.repo_root,
            overwrite=args.overwrite_production_evidence_file,
        )
        print(json.dumps(init_report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if init_report["created"] else 1

    if args.explain_production_evidence:
        explain_report = build_production_evidence_explain(
            args.repo_root,
            production_evidence_file=args.production_evidence_file,
            allow_live_ready_from_evidence=args.allow_live_ready_from_evidence,
        )
        print(json.dumps(explain_report, ensure_ascii=False, indent=2, sort_keys=True))
        if args.strict_local and not explain_report["local_v1_accepted"]:
            return 1
        if args.strict_production and not explain_report["ready_for_live_orders"]:
            return 1
        return 0

    report = build_completion_report(
        args.repo_root,
        production_evidence_file=args.production_evidence_file,
        allow_live_ready_from_evidence=args.allow_live_ready_from_evidence,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.strict_local and not report["local_v1_accepted"]:
        return 1
    if args.strict_production and not report["ready_for_live_orders"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
