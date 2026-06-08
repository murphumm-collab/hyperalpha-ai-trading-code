# HyperAlpha AI Agent Multi-Tenant Foundation Spec

Date: 2026-06-08
Branch: codex/ai-agent-multitenant-foundation

## Objective

Turn the current Vibe-Trading/Hyper AI demo-style AI session model into a To C-ready foundation where AI conversations, memory, and strategy work are scoped to the logged-in user.

## First Development Slice

This slice does not change live order execution. It focuses on the safety foundation:

- Persist the development plan and status markers.
- Add user resolution for Hyper AI and Signal AI requests.
- Scope Hyper AI profile, memory, conversations, skill settings, and tool settings by user.
- Keep local development compatible by falling back to the default user when no login token exists.
- Send the logged-in `arena_token` from Hyper AI and Signal AI frontend requests.
- Mark production JWT signature verification as not accepted until JWKS verification is implemented.

## Non-Goals For This Slice

- No direct AI order execution changes.
- No Hyperliquid order gateway changes.
- No full Redis queue replacement yet.
- No production-grade Casdoor JWKS verification yet.
- No complete Prompt AI / Program AI / sub-agent user isolation yet.

## Acceptance Rules

- Tests/checks must pass before a status is marked accepted.
- Incomplete or untested items must remain marked as pending or blocked.
- All work must stay on a `codex/` branch until reviewed.
- AI must not receive or handle exchange API keys directly.
