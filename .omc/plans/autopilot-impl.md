# HyperAlpha AI Agent Multi-Tenant Foundation Plan

## Phase 1: Development Governance

- Create a dedicated development branch.
- Store this spec and implementation plan under `.omc`.
- Track progress under `docs/hyperalpha/status`.

## Phase 2: User Identity Foundation

- Add a backend helper that resolves the current user from:
  - existing `session_token`;
  - `Authorization: Bearer <arena_token>`;
  - local default user fallback.
- For bearer JWTs, decode payload and expiry for local user mapping.
- Mark signature verification as pending for production.

## Phase 3: Hyper AI User Scoping

- Add `user_id` to:
  - `hyper_ai_profile`;
  - `hyper_ai_memory`;
  - `hyper_ai_conversations`.
- Backfill existing local data to the default user.
- Filter profile, memory, conversations, skills, and tool config by `user_id`.

## Phase 4: Signal AI User Scoping

- Resolve the current user for Signal AI chat/history endpoints.
- Validate that the requested `accountId` belongs to the current user before AI signal generation.

## Phase 5: Frontend Token Propagation

- Add a small auth-aware fetch helper.
- Use it in Hyper AI, Hyper AI onboarding, Tool Config, Signal AI chat, startup profile checks, and AI stream polling.
- Keep unauthenticated local mode working.

## Phase 6: Verification

- Run Python compile checks for changed backend files.
- Run frontend build after dependency install.
- Record acceptance status and not-accepted items.

## Phase 7: Commit And Handoff

- Commit to the development branch.
- Do not merge.
- Push only if GitHub auth is available.
