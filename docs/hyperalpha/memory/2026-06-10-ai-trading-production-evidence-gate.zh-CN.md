# 2026-06-10 AI Trading Production Evidence Gate Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading V1 completion audit 现在支持生产外部验收 evidence 文件校验，用来把真实 Auth/JWKS、真实订单后端、真实模型 profile、管理员可视化、生产 session detail、实际 reboot、真实交易所执行等七项外部验收记录成脱敏 JSON。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- `backend/scripts/ai_trading_v1_completion_audit.py`：
  - 继续支持 `--strict-local`，要求本地 V1 证据完整，包括 aggregate local acceptance runner、default production readiness DB-audit blocker、signal-only gateway contract、development governance 和 latest compressed memory。
  - `--strict-local` 现在还要求一键本地验收 runner 包含 production evidence template expected-failure gate。
  - 新增 `--production-evidence-file`，读取 `hyperalpha.ai_trading.external_acceptance.v1` evidence JSON。
  - Evidence 必须覆盖七个外部验收项，且每项都为 `status=accepted`、有 `validated_at`、`validated_by`、`evidence_summary`、`artifact_refs`、`secret_values_returned=false`。
  - Evidence 根级 `generated_at` 和每项 `validated_at` 必须是可解析、带时区的 ISO-8601 timestamp，例如 `2026-06-10T12:00:00Z`，且 `generated_at` 不能早于任何 item `validated_at`。
  - Evidence 会扫描 Authorization/Bearer、API key/password/private key/access token、DB URL、OpenAI-style `sk-...`、AWS-style key 等常见密钥模式。
  - Evidence `artifact_refs` 现在必须是非空安全引用，scheme 仅允许 `https` / `ops` / `lark` / `notion`，并拒绝 embedded credentials、localhost、私网/保留 IP、secret-looking value。
  - Evidence root/item 字段现在是严格白名单；root 只允许 `version`、`generated_at`、`secret_values_returned`、`notes`、`items`，item 只允许 `status`、`validated_at`、`validated_by`、`evidence_summary`、`artifact_refs`、`secret_values_returned`，任何未知字段都会阻断 live ready。
  - Evidence `items` 下的验收项 ID 现在也严格白名单，只允许七个外部验收项；额外旧字段名、假验收项或未知 ID 会阻断 live ready。
  - Evidence `validated_by` 和 `evidence_summary` 现在会做文本质量检查，拒绝 `TBD`、`placeholder`、`OK`、`accepted` 等占位/过短内容，防止形式化生产验收材料解锁 live ready。
  - Evidence `validated_by` 现在限制为最多 120 字符，`evidence_summary` 限制为 24-600 字符，防止把大段原始日志或模型输出塞进生产证据。
  - 即使 evidence 完整，默认仍保持 `ready_for_live_orders=false`；必须显式追加 `--allow-live-ready-from-evidence` 才允许 live-ready 变 true。
  - 报告区分 effective `external_pending_count` 和 `documented_external_pending_count`：默认/模板为 `7/7`；完整脱敏 evidence 可把 effective pending 降到 `0`，但保留文档里的 local-V1 pending marker 数。
  - 继承最新一键本地验收证据：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。

- `docs/hyperalpha/ai-trading-v1-production-evidence.template.json`：
  - 提供七项外部验收的脱敏 evidence 模板。
  - 模板 notes 明确 `generated_at` 和每项 `validated_at` 必须使用带时区的 ISO-8601 timestamp，且 `generated_at` 不能早于任何 item `validated_at`。
  - 模板 notes 明确 `artifact_refs` 必须非空，只能使用 `https://`、`ops://`、`lark://`、`notion://`，不能嵌入 credentials 或指向 localhost/private-network URL。
  - 模板 notes 明确 production evidence 只能使用 documented schema fields；未知 root/item 字段会被拒绝。
  - 模板 notes 明确 `items` 只能包含模板列出的外部验收项 ID；未知 item ID 会被拒绝。
  - 模板 notes 明确每项必须有非 placeholder 的 `validated_by` 和具体 `evidence_summary`，并记录 3-120 / 24-600 字符长度边界。
  - 模板自身全是 pending，不能通过 `--strict-production`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：
  - 新增 `Production evidence template remains blocked` expected-failure 步骤，显式运行 completion audit 的 `--production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production`。

- `backend/tests/test_ai_trading_v1_completion_audit.py`：
  - 从 3 条扩展到 11 条。
  - 覆盖 accepted sanitized production evidence 仍需显式 live-ready confirmation。
  - 覆盖 missing evidence item 不能 live ready。
  - 覆盖 Authorization/Bearer secret-pattern 不能 live ready。
  - 覆盖缺失/缺时区 `generated_at`、malformed `validated_at`、以及 `generated_at` 早于 `validated_at` 不能 live ready。
  - 覆盖空 artifact_refs、localhost/private IP、disallowed scheme、embedded credentials 不能 live ready。
  - 覆盖未知 root/item evidence 字段不能 live ready，避免把任意原始输出塞进生产证据。
  - 覆盖未知 `items` 验收项 ID 不能 live ready，避免夹带旧验收项或假验收项。
  - 覆盖 placeholder/过短 `validated_by` 和 `evidence_summary` 不能 live ready。
  - 覆盖过长 `validated_by` 和 `evidence_summary` 不能 live ready，避免夹带原始日志/模型输出。

## 已验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：11 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed，返回 `local_v1_accepted=true`、`ready_for_live_orders=false`、`production_evidence.provided=false`、`production_track=pending_external_acceptance`。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production`：按预期 exit 1，返回 `production_evidence.provided=true`、`production_evidence.ready=false`、`accepted_count=0`、`required_count=7`、`ready_for_live_orders=false`。
- 临时完整脱敏 accepted evidence CLI 检查：未加 `--allow-live-ready-from-evidence` 时返回 `ready_for_live_orders=false`、`production_track=external_evidence_accepted_pending_explicit_confirmation`、effective/documented pending `0/7`；加 `--allow-live-ready-from-evidence --strict-production` 后返回 `ready_for_live_orders=true`、`production_track=accepted`、effective/documented pending `0/7`。
- 临时 artifact-ref CLI 检查：完整 evidence 使用安全 `https://ops.hyperalpha.org/...` artifact refs 且带 `--allow-live-ready-from-evidence --strict-production` 时通过；空 artifact refs 或使用 `http://127.0.0.1:8802/internal-proof` 时按预期阻断，后者报告 disallowed scheme、local host、private/reserved IP blockers。
- 临时 timestamp CLI 检查：完整 evidence 使用带时区 ISO `generated_at` / `validated_at` 且带 `--allow-live-ready-from-evidence --strict-production` 时通过；缺失/缺时区 `generated_at`、malformed `validated_at`、或 `generated_at` 早于 `validated_at` 时按预期阻断。
- 临时 schema-field CLI 检查：完整 evidence 只使用白名单字段时通过；root extra 字段和 item extra 字段分别按预期 exit 1，并报告 unexpected root/item fields。
- 临时 item-id CLI 检查：额外 `legacy_manual_acceptance` item ID 会按预期阻断，不允许 live ready。
- 临时 text-quality CLI 检查：`TBD` / `OK` / `accepted` / 过短验收人会按预期阻断，不允许 live ready。
- 临时 text-bounds CLI 检查：过长 `validated_by` / `evidence_summary` 会按预期阻断，不允许 live ready。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：74 passed，5 个既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；一键本地验收覆盖 backend compile、74 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blockers、local V1 completion boundary audit、production completion boundary expected blocker、production evidence template expected blocker、frontend build、runtime readiness 和 live local mock handoff。最新证据为 strategy spec `#52`、signal event `#50`、agent sessions `37`、handoff attempts `48`、gateway response `mock_accepted`、model-adjust blocker `model_profile_not_configured`。

## 下一步注意

- 本切片只增加生产验收 evidence 校验，不改变交易 API、模型调用、handoff 或订单执行。
- 本地 V1 accepted 不等于 production ready；真实 evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- Evidence 文件不能包含 API keys、bearer tokens、DB URLs、private keys、raw Authorization headers、用户 secret；timestamp 必须带时区且顺序一致；artifact refs 也不能指向本地/私网 URL 或嵌入 credentials；root/item 不能带模板外的任意字段；`items` 不能包含未知验收项 ID；`validated_by` 和 `evidence_summary` 不能是 placeholder、过短形式化文本或过长原始输出。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。
- AI Trading 仍保持 signal-only；真实订单执行仍必须由 HyperAlpha 订单后端处理。
