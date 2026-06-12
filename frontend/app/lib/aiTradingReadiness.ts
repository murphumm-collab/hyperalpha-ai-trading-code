export interface AiTradingProductionComponent {
  ready: boolean
  blockers?: string[]
  warnings?: string[]
  checks?: Record<string, unknown>
}

export interface AiTradingProductionReadiness {
  production_ready: boolean
  blockers: string[]
  warnings: string[]
  checks: Record<string, AiTradingProductionComponent>
  next_actions: string[]
}

export interface AiTradingProductionEvidenceSummary {
  provided: boolean
  ready: boolean
  acceptedCount: number
  requiredCount: number
  evidenceRunIdPresent: boolean
  expiresAt: string | null
  cutoverWindowPresent: boolean
  cutoverWindowStartAt: string | null
  cutoverWindowEndAt: string | null
  cutoverApprovalRefPresent: boolean
  secretPatternCount: number
  blockers: string[]
  warnings: string[]
}

export interface AiTradingProductionEvidenceItemView {
  id: string
  description: string
  documentationStatus: string | null
  evidenceStatus: string
  ready: boolean
  blockers: string[]
  artifactRefCount: number
  requiredFields: string[]
  requiredSummaryTerms: string[]
  missingSummaryTerms: string[]
  safeArtifactRefSchemes: string[]
  forbiddenValues: string[]
  operatorGuidance: string[]
}

export interface AiTradingProductionEvidenceProgressView {
  status: string
  acceptedItemIds: string[]
  pendingItemIds: string[]
  blockedItemIds: string[]
  nextRequiredItemIds: string[]
  nextRequiredActions: string[]
  rootNextRequiredActions: string[]
  acceptedCount: number
  pendingCount: number
  blockedCount: number
  requiredCount: number
  liveOrderGateBlockers: string[]
}

export interface AiTradingProductionEvidenceExplainView {
  mode: string
  githubUpload: string | null
  localV1Accepted: boolean
  readyForLiveOrders: boolean
  productionTrack: string | null
  productionEvidence: AiTradingProductionEvidenceSummary
  progress: AiTradingProductionEvidenceProgressView
  requiredItemIds: string[]
  safeArtifactRefSchemes: string[]
  maxEvidenceValidityDays: number
  maxClockSkewSeconds: number
  maxItemValidationAgeDays: number
  maxCutoverWindowHours: number
  minEvidenceRunIdChars: number
  maxEvidenceRunIdChars: number
  items: AiTradingProductionEvidenceItemView[]
  nextActions: string[]
}

export interface AiTradingProductionEvidenceTemplateGuidanceItemView {
  id: string
  description: string
  requiredFields: string[]
  requiredSummaryTerms: string[]
  operatorGuidance: string[]
  safeArtifactRefSchemes: string[]
  forbiddenValues: string[]
}

export interface AiTradingProductionEvidenceRootGuidanceView {
  field: string
  requiredValue: string
  relatedBlockers: string[]
  operatorGuidance: string[]
  forbiddenValues: string[]
}

export interface AiTradingProductionEvidenceTemplateGuidanceView {
  secretPolicy: string
  rootFields: AiTradingProductionEvidenceRootGuidanceView[]
  rootNextRequiredActions: string[]
  items: AiTradingProductionEvidenceTemplateGuidanceItemView[]
  nextRequiredActions: string[]
}

export interface AiTradingProductionEvidenceDryRunView {
  mode: string
  acceptedInput: string
  expectedInput: string
  rootIsObject: boolean
  persistence: string
  payloadBytes: number
  maxPayloadBytes: number
  itemKeyCount: number
  maxItemKeys: number
  networkCalls: boolean
  modelCalls: boolean
  orderBackendCalls: boolean
  exchangeCalls: boolean
  githubCalls: boolean
  readyForLiveOrders: boolean
  liveOrdersUnlocked: boolean
  secretPolicy: string
}

export interface AiTradingAgentContextLocatorMeta {
  key: string
  label: string
  tone: string
}

export interface AiTradingAgentContextLocatorView extends AiTradingAgentContextLocatorMeta {
  id: number | null
  agentSessionId: string | null
  status: string | null
  contextSummaryChars: number | null
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

const stringList = (value: unknown): string[] => {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

const numberValue = (value: unknown): number => {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

const readableEvidenceSuffix = (value: string): string => {
  return value
    .replace(/^external_evidence_/, '')
    .replace(/[:_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const PRODUCTION_EVIDENCE_BLOCKER_LABELS: Record<string, string> = {
  explicit_live_ready_confirmation_required: 'Explicit live-order confirmation required',
  external_evidence_accepted_pending_explicit_confirmation: 'Explicit production confirmation still required',
  external_evidence_artifact_ref_credentials_embedded: 'Artifact ref embeds credentials',
  external_evidence_artifact_ref_duplicate_in_item: 'Duplicate artifact ref in item',
  external_evidence_artifact_ref_host_missing: 'Artifact ref host missing',
  external_evidence_artifact_ref_local_host: 'Artifact ref points to localhost',
  external_evidence_artifact_ref_missing_item_id: 'Artifact ref missing item id',
  external_evidence_artifact_ref_missing_run_id: 'Artifact ref missing run id',
  external_evidence_artifact_ref_must_be_non_empty_string: 'Artifact ref must be a non-empty string',
  external_evidence_artifact_ref_private_or_reserved_ip: 'Artifact ref points to private or reserved IP',
  external_evidence_artifact_ref_reused_across_items: 'Artifact ref reused across items',
  external_evidence_artifact_ref_scheme_not_allowed: 'Artifact ref scheme is not allowed',
  external_evidence_artifact_ref_secret_pattern_detected: 'Artifact ref contains secret-like text',
  external_evidence_artifact_ref_too_long: 'Artifact ref is too long',
  external_evidence_artifact_refs_empty: 'Artifact refs are empty',
  external_evidence_artifact_refs_missing: 'Artifact refs missing',
  external_evidence_artifact_refs_must_be_list: 'Artifact refs must be a list',
  external_evidence_artifact_refs_too_many: 'Too many artifact refs',
  external_evidence_cutover_approval_ref_credentials_embedded: 'Cutover approval ref embeds credentials',
  external_evidence_cutover_approval_ref_host_missing: 'Cutover approval ref host missing',
  external_evidence_cutover_approval_ref_local_host: 'Cutover approval ref points to localhost',
  external_evidence_cutover_approval_ref_missing: 'Cutover approval ref missing',
  external_evidence_cutover_approval_ref_missing_run_id: 'Cutover approval ref missing run id',
  external_evidence_cutover_approval_ref_private_or_reserved_ip: 'Cutover approval ref points to private or reserved IP',
  external_evidence_cutover_approval_ref_scheme_not_allowed: 'Cutover approval ref scheme is not allowed',
  external_evidence_cutover_approval_ref_secret_pattern_detected: 'Cutover approval ref contains secret-like text',
  external_evidence_cutover_approval_ref_too_long: 'Cutover approval ref is too long',
  external_evidence_cutover_window_end_not_after_start: 'Cutover window end must be after start',
  external_evidence_cutover_window_end_at_missing: 'Cutover window end time missing',
  external_evidence_cutover_window_ended: 'Cutover window has ended',
  external_evidence_cutover_window_missing: 'Cutover window missing',
  external_evidence_cutover_window_not_started: 'Cutover window has not started',
  external_evidence_cutover_window_start_at_missing: 'Cutover window start time missing',
  external_evidence_cutover_window_too_long: 'Cutover window is too long',
  external_evidence_cutover_window_unexpected_fields: 'Cutover window has unexpected fields',
  external_evidence_expired: 'Evidence has expired',
  external_evidence_expires_at_missing: 'Evidence expiry missing',
  external_evidence_expires_at_not_after_generated_at: 'Evidence expiry must be after generation time',
  external_evidence_expires_at_timezone_missing: 'Evidence expiry timezone missing',
  external_evidence_expires_at_too_far: 'Evidence expiry is too far out',
  external_evidence_file_missing: 'Evidence file missing',
  external_evidence_file_must_be_outside_repo: 'Evidence file must be outside the code repo',
  external_evidence_generated_at_after_cutover_window: 'Evidence generated after cutover window',
  external_evidence_generated_at_before_cutover_window: 'Evidence generated before cutover window',
  external_evidence_generated_at_in_future: 'Evidence generation time is in the future',
  external_evidence_generated_at_missing: 'Evidence generation time missing',
  external_evidence_generated_at_timezone_missing: 'Evidence generation timezone missing',
  external_evidence_item_missing: 'Evidence item missing',
  external_evidence_item_not_accepted: 'Evidence item is not accepted',
  external_evidence_item_not_provided: 'Evidence item not provided',
  external_evidence_item_not_reported: 'Evidence item not reported',
  external_evidence_items_must_be_object: 'Evidence items must be an object',
  external_evidence_json_invalid: 'Evidence JSON is invalid',
  external_evidence_note_must_be_non_empty_string: 'Evidence note must be a non-empty string',
  external_evidence_note_too_long: 'Evidence note is too long',
  external_evidence_notes_must_be_list: 'Evidence notes must be a list',
  external_evidence_notes_too_many: 'Too many evidence notes',
  external_evidence_output_exists: 'Evidence output already exists',
  external_evidence_output_must_be_outside_repo: 'Evidence output must be outside the code repo',
  external_evidence_output_should_use_json_suffix: 'Evidence output should use a JSON suffix',
  external_evidence_root_must_be_object: 'Evidence root must be an object',
  external_evidence_run_id_invalid_chars: 'Evidence run id has invalid characters',
  external_evidence_run_id_missing: 'Evidence run id missing',
  external_evidence_run_id_placeholder: 'Evidence run id is a placeholder',
  external_evidence_run_id_secret_pattern_detected: 'Evidence run id contains secret-like text',
  external_evidence_run_id_too_long: 'Evidence run id is too long',
  external_evidence_run_id_too_short: 'Evidence run id is too short',
  external_evidence_secret_pattern_detected: 'Evidence contains secret-like text',
  external_evidence_secret_values_returned_must_be_false: 'Secret values returned must be false',
  external_evidence_summary_missing: 'Evidence summary missing',
  external_evidence_summary_placeholder: 'Evidence summary is a placeholder',
  external_evidence_summary_too_long: 'Evidence summary is too long',
  external_evidence_summary_too_short: 'Evidence summary is too short',
  external_evidence_unexpected_item_fields: 'Evidence item has unexpected fields',
  external_evidence_unexpected_item_ids: 'Evidence includes unexpected item ids',
  external_evidence_unexpected_root_fields: 'Evidence root has unexpected fields',
  external_evidence_validated_at_after_generated_at: 'Validation time is after generation time',
  external_evidence_validated_at_in_future: 'Validation time is in the future',
  external_evidence_validated_at_invalid: 'Validation time is invalid',
  external_evidence_validated_at_missing: 'Validation time missing',
  external_evidence_validated_at_timezone_missing: 'Validation timezone missing',
  external_evidence_validated_at_too_old: 'Validation time is too old',
  external_evidence_validated_by_placeholder: 'Validator name is a placeholder',
  external_evidence_validated_by_missing: 'Validator name missing',
  external_evidence_validated_by_too_long: 'Validator name is too long',
  external_evidence_validated_by_too_short: 'Validator name is too short',
  external_evidence_version_mismatch: 'Evidence version mismatch',
  local_v1_not_accepted: 'Local V1 acceptance is not complete',
  production_evidence_not_ready: 'Production evidence is not ready',
}

export const formatAiTradingProductionEvidenceBlocker = (code: string): string => {
  if (!code) return ''
  const directLabel = PRODUCTION_EVIDENCE_BLOCKER_LABELS[code]
  if (directLabel) return directLabel
  if (code.startsWith('external_evidence_item_blocked:')) {
    return `Evidence item blocked: ${readableEvidenceSuffix(code.split(':').slice(1).join(':'))}`
  }
  if (code.startsWith('external_evidence_summary_missing_required_term:')) {
    return `Missing required summary term: ${readableEvidenceSuffix(code.split(':').slice(1).join(':'))}`
  }
  return readableEvidenceSuffix(code) || code
}

const PRODUCTION_EVIDENCE_API_ERROR_LABELS: Record<string, string> = {
  production_evidence_items_too_many: 'Evidence has too many item keys',
  production_evidence_payload_too_large: 'Evidence JSON is too large for dry-run validation',
}

const PRODUCTION_EVIDENCE_API_STATUS_LABELS: Record<number, string> = {
  401: 'Admin authentication required',
  403: 'Admin role required',
  413: 'Evidence JSON is too large for dry-run validation',
  422: 'Evidence request was rejected by the safe validator',
}

const PRODUCTION_READINESS_API_DETAIL_LABELS: Record<string, string> = {
  'Admin privileges required': 'Admin role required',
  'Authentication required': 'Admin authentication required',
  'Bearer token expired': 'Admin authentication required',
  'Invalid authentication credentials': 'Admin authentication required',
  'Invalid bearer token': 'Admin authentication required',
  'Invalid or expired session': 'Admin authentication required',
  'Not authenticated': 'Admin authentication required',
  'Session user not found': 'Admin authentication required',
}

const PRODUCTION_READINESS_API_STATUS_LABELS: Record<number, string> = {
  400: 'AI Trading production readiness request is invalid',
  401: 'Admin authentication required',
  403: 'Admin role required',
  404: 'AI Trading production readiness endpoint was not found',
  422: 'AI Trading production readiness request is invalid',
  429: 'Too many AI Trading production readiness requests',
  500: 'AI Trading production readiness service failed',
  503: 'AI Trading production readiness service is unavailable',
}

const MODEL_CONFIG_API_DETAIL_LABELS: Record<string, string> = {
  'Base URL is required for custom provider': 'Base URL is required for custom provider',
  'Connection test failed': 'Model connection test failed',
  'Connection timeout': 'Model provider connection timed out',
  'Invalid Base URL': 'Base URL is invalid',
  'Invalid provider': 'Model provider is not supported',
  'base_url is required for custom provider': 'Base URL is required for custom provider',
}

const MODEL_CONFIG_API_STATUS_LABELS: Record<number, string> = {
  400: 'Model connection test failed',
  401: 'Authentication required',
  403: 'Model configuration is not allowed',
  422: 'Model configuration request is invalid',
  429: 'Too many model configuration requests',
  500: 'Model configuration service failed',
  503: 'Model provider service is unavailable',
}

const MARKET_UNIVERSE_API_DETAIL_LABELS: Record<string, string> = {
  'Could not validate credentials': 'Authentication required',
  'Invalid authentication credentials': 'Authentication required',
  'Not authenticated': 'Authentication required',
  'Unauthorized': 'Authentication required',
  market_universe_unavailable: 'Trading market universe is unavailable',
  symbols_unavailable: 'Trading symbols are unavailable',
}

const MARKET_UNIVERSE_API_STATUS_LABELS: Record<number, string> = {
  400: 'Trading-symbol request is invalid',
  401: 'Authentication required',
  403: 'Trading-symbol access is not allowed',
  404: 'Trading-symbol source was not found',
  422: 'Trading-symbol request is invalid',
  429: 'Too many trading-symbol requests',
  500: 'Trading-symbol service failed',
  502: 'Trading-symbol upstream is unavailable',
  503: 'Trading-symbol service is unavailable',
}

const safeProductionEvidenceApiDetailCode = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    const knownLabel = PRODUCTION_EVIDENCE_API_ERROR_LABELS[detail] || PRODUCTION_EVIDENCE_BLOCKER_LABELS[detail]
    return knownLabel ? detail : null
  }
  if (isRecord(detail) && typeof detail.code === 'string') {
    const knownLabel = PRODUCTION_EVIDENCE_API_ERROR_LABELS[detail.code] || PRODUCTION_EVIDENCE_BLOCKER_LABELS[detail.code]
    return knownLabel ? detail.code : null
  }
  return null
}

export const formatAiTradingProductionEvidenceApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeCode = safeProductionEvidenceApiDetailCode(detail)
  const safeDetail = safeCode
    ? PRODUCTION_EVIDENCE_API_ERROR_LABELS[safeCode] || PRODUCTION_EVIDENCE_BLOCKER_LABELS[safeCode]
    : PRODUCTION_EVIDENCE_API_STATUS_LABELS[status] || fallback
  return `${statusLabel}: ${safeDetail}`
}

const safeProductionReadinessApiDetailLabel = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    return PRODUCTION_READINESS_API_DETAIL_LABELS[detail] || null
  }
  if (isRecord(detail) && typeof detail.code === 'string') {
    return PRODUCTION_READINESS_API_DETAIL_LABELS[detail.code] || null
  }
  return null
}

export const formatAiTradingProductionReadinessApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeDetail = safeProductionReadinessApiDetailLabel(detail)
    || PRODUCTION_READINESS_API_STATUS_LABELS[status]
    || fallback
  return `${statusLabel}: ${safeDetail || readableEvidenceSuffix(fallback)}`
}

const safeModelConfigApiDetailLabel = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    const exactLabel = MODEL_CONFIG_API_DETAIL_LABELS[detail]
    if (exactLabel) return exactLabel

    if (detail.startsWith('Unknown provider:')) {
      return 'Model provider is not supported'
    }
    if (detail.startsWith('Connection failed:')) {
      return 'Model provider connection failed'
    }
    if (detail.startsWith('HTTP ')) {
      return 'Model provider rejected the connection test'
    }

    return null
  }
  if (isRecord(detail) && typeof detail.code === 'string') {
    return MODEL_CONFIG_API_DETAIL_LABELS[detail.code] || null
  }
  return null
}

export const formatAiTradingModelConfigApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeDetail = safeModelConfigApiDetailLabel(detail)
    || MODEL_CONFIG_API_STATUS_LABELS[status]
    || fallback
  return `${statusLabel}: ${safeDetail || readableEvidenceSuffix(fallback)}`
}

const safeMarketUniverseApiDetailLabel = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    return MARKET_UNIVERSE_API_DETAIL_LABELS[detail] || null
  }
  if (isRecord(detail) && typeof detail.code === 'string') {
    return MARKET_UNIVERSE_API_DETAIL_LABELS[detail.code] || null
  }
  return null
}

export const formatAiTradingMarketUniverseApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeDetail = safeMarketUniverseApiDetailLabel(detail)
    || MARKET_UNIVERSE_API_STATUS_LABELS[status]
    || fallback
  return `${statusLabel}: ${safeDetail || readableEvidenceSuffix(fallback)}`
}

const SIGNAL_ACTION_API_DETAIL_LABELS: Record<string, string> = {
  'AI Trading signal gateway is disabled': 'Signal gateway is disabled',
  'Only review_candidate signal events can be rejected': 'Only review-candidate signals can be rejected',
  'Signal event not found': 'Signal event was not found',
  'Signal handoff requires explicit user confirmation': 'Explicit user confirmation is required',
  agent_session_archived: 'Agent session is archived',
  event_status_not_review_candidate: 'Signal is not a review candidate',
  execution_boundary_missing: 'Signal execution boundary is missing',
  gateway_disabled: 'Signal gateway is disabled',
  gateway_url_not_configured: 'Signal gateway is not configured',
  handoff_already_submitted: 'Signal handoff was already submitted',
  production_gateway_mode_must_be_http_json: 'Gateway mode must be HTTP JSON',
  production_gateway_timeout_invalid: 'Gateway timeout is invalid',
  production_gateway_timeout_too_high: 'Gateway timeout is too high',
  production_gateway_token_required: 'Production gateway token is required',
  production_gateway_url_must_be_https: 'Production gateway URL must use HTTPS',
  production_gateway_url_must_not_be_local_or_private: 'Production gateway URL cannot be local or private',
  production_gateway_url_must_not_be_placeholder: 'Production gateway URL cannot be a placeholder',
  production_gateway_url_must_not_embed_credentials_or_query: 'Production gateway URL cannot embed credentials or query text',
  production_handoff_approval_required: 'Production handoff approval is required',
  production_signal_max_handoff_age_required: 'Signal max-age gate is required',
  production_signal_max_handoff_age_too_high: 'Signal max-age gate is too high',
  signal_action_not_tradeable: 'Signal action is not tradeable',
  signal_allows_direct_ai_order_placement: 'Signal allows direct AI order placement',
  signal_candidate_type_invalid: 'Signal candidate type is invalid',
  signal_event_action_mismatch: 'Signal action does not match the audit event',
  signal_event_created_at_missing: 'Signal creation time is missing',
  signal_event_stale_for_handoff: 'Signal is stale for handoff',
  signal_event_symbol_mismatch: 'Signal symbol does not match the audit event',
  signal_missing_not_an_order_boundary: 'Signal is missing the not-an-order boundary',
  signal_missing_order_backend_only_boundary: 'Signal is missing the order-backend-only boundary',
  signal_missing_signal_only_boundary: 'Signal is missing the signal-only boundary',
  signal_missing_user_confirmation_boundary: 'Signal is missing the user-confirmation boundary',
  signal_not_eligible_for_backend_handoff: 'Signal is not eligible for backend handoff',
  signal_payload_missing: 'Signal payload is missing',
  signal_symbol_missing: 'Signal symbol is missing',
  signal_venue_must_be_hyperliquid: 'Signal venue must be Hyperliquid',
  signal_version_mismatch: 'Signal version does not match',
  strategy_backtest_required_before_handoff: 'Handoff-ready backtest evidence is required',
}

const SIGNAL_ACTION_API_STATUS_LABELS: Record<number, string> = {
  400: 'Signal action was rejected by safety checks',
  401: 'Authentication required',
  403: 'Permission denied',
  404: 'Signal event was not found',
  409: 'Signal gateway is disabled',
  422: 'Signal action request is invalid',
}

const STRATEGY_ACTION_API_DETAIL_LABELS: Record<string, string> = {
  'Adjustment instruction is required': 'Adjustment instruction is required',
  'AI Trading agent session is archived': 'Agent session is archived',
  'AI Trading agent session not found': 'Agent session not found',
  'Backtest result not found': 'Backtest result not found',
  'LLM model or base URL is missing': 'Model endpoint is not configured',
  'LLM not configured for AI Trading model adjustment': 'DeepSeek/Qwen profile is not configured',
  'No handoff-ready Program BacktestResult found for strategy symbol': 'No handoff-ready matching Program Backtest result was found',
  'No Program Backtest evidence attached': 'No Program Backtest evidence is attached',
  'No valid LLM endpoint for AI Trading model adjustment': 'Model endpoint is not valid',
  'Strategy spec is not valid for approval': 'Strategy spec failed approval safety checks',
  'Strategy spec is not valid for signal preview': 'Strategy spec failed signal-preview safety checks',
  'Strategy spec must be an object': 'Strategy spec payload is invalid',
  'Strategy spec must be approved before signal preview': 'Strategy spec must be approved before signal preview',
  'Strategy spec not found': 'Strategy spec was not found',
  'Strategy spec symbol is required before attaching backtest evidence': 'Strategy symbol is required before attaching backtest evidence',
  'Strategy spec symbol is required before backtest preflight': 'Strategy symbol is required before backtest preflight',
  'AI Trading model adjustment requires a DeepSeek or Qwen profile': 'DeepSeek or Qwen profile is required',
  agent_session_archived: 'Agent session is archived',
  binding_symbol_mismatch: 'Program binding symbol does not match the strategy',
  missing_default_request: 'Backtest preflight did not return a runnable request',
  no_eligible_symbol_matching_program_binding: 'No eligible symbol-matching Program binding was found',
  no_program_bindings: 'No Program bindings are available for backtest preflight',
  strategy_backtest_max_drawdown_required: 'Backtest max drawdown metric is required',
  strategy_backtest_performance_metric_required: 'Backtest performance metric is required',
  strategy_backtest_required_before_handoff: 'Handoff-ready backtest evidence is required',
  strategy_backtest_trade_count_required: 'Backtest trade count is required',
}

const STRATEGY_ACTION_API_STATUS_LABELS: Record<number, string> = {
  400: 'Strategy action was rejected by safety checks',
  401: 'Authentication required',
  403: 'Strategy action is not allowed',
  404: 'Strategy record was not found',
  409: 'Strategy action conflicts with current state',
  422: 'Strategy action request is invalid',
  429: 'Too many strategy action requests',
  500: 'Strategy service failed',
  503: 'Strategy service is unavailable',
}

const AGENT_SESSION_API_DETAIL_LABELS: Record<string, string> = {
  'agent_session_id is required': 'Agent session id is required',
  'AI Trading agent session not found': 'Agent session not found',
  'AI Trading agent session is archived': 'Agent session is archived',
  'AI Trading agent session already exists': 'Agent session already exists',
  'AI Trading agent session name is required': 'Agent session name is required',
}

const AGENT_SESSION_API_STATUS_LABELS: Record<number, string> = {
  400: 'Invalid agent session request',
  401: 'Authentication required',
  403: 'Agent session action is not allowed',
  404: 'Agent session not found',
  409: 'Agent session conflict',
  422: 'Agent session input failed validation',
  429: 'Too many agent session requests',
  500: 'Agent session service failed',
  503: 'Agent session service is unavailable',
}

const readableSignalActionSuffix = (value: string): string => {
  return value
    .replace(/^signal_/, '')
    .replace(/^production_/, '')
    .replace(/[:_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const formatSignalActionCodes = (codes: string[]): string | null => {
  const labels = codes
    .map(code => SIGNAL_ACTION_API_DETAIL_LABELS[code.trim()])
    .filter((label): label is string => Boolean(label))
  if (!labels.length) {
    return null
  }
  return labels.slice(0, 3).join(', ')
}

const formatStrategyActionCodes = (codes: string[]): string | null => {
  const labels = codes
    .map(code => STRATEGY_ACTION_API_DETAIL_LABELS[code.trim()])
    .filter((label): label is string => Boolean(label))
  if (!labels.length) {
    return null
  }
  return labels.slice(0, 3).join(', ')
}

const safeSignalActionApiDetailLabel = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    const exactLabel = SIGNAL_ACTION_API_DETAIL_LABELS[detail]
    if (exactLabel) return exactLabel

    if (detail.startsWith('Signal event is not eligible for handoff:')) {
      const codes = detail.split(':').slice(1).join(':').split(',')
      return formatSignalActionCodes(codes) || 'Signal is not eligible for handoff'
    }

    if (detail.startsWith('Signal gateway handoff failed:')) {
      const statusMatch = detail.match(/\(status\s+(\d{3})\)/)
      return statusMatch ? `Order-backend handoff failed with HTTP ${statusMatch[1]}` : 'Order-backend handoff failed'
    }

    return null
  }

  if (isRecord(detail) && typeof detail.code === 'string') {
    return SIGNAL_ACTION_API_DETAIL_LABELS[detail.code] || null
  }

  return null
}

const safeStrategyActionApiDetailLabel = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    const exactLabel = STRATEGY_ACTION_API_DETAIL_LABELS[detail]
      || SIGNAL_ACTION_API_DETAIL_LABELS[detail]
      || AGENT_SESSION_API_DETAIL_LABELS[detail]
    if (exactLabel) return exactLabel

    if (detail.startsWith('agent_session_id must be')) {
      return 'Agent session id format is invalid'
    }

    if (detail.startsWith('Backtest preflight blocked:')) {
      const codes = detail.split(':').slice(1).join(':').split(',')
      return formatStrategyActionCodes(codes) || 'Backtest preflight is blocked'
    }

    if (detail.startsWith('LLM request failed')) {
      return 'Model adjustment request failed'
    }

    if (detail.startsWith('Program Backtest failed')) {
      return 'Program Backtest failed'
    }

    return null
  }

  if (isRecord(detail) && typeof detail.code === 'string') {
    return STRATEGY_ACTION_API_DETAIL_LABELS[detail.code]
      || SIGNAL_ACTION_API_DETAIL_LABELS[detail.code]
      || AGENT_SESSION_API_DETAIL_LABELS[detail.code]
      || null
  }

  return null
}

const safeAgentSessionApiDetailLabel = (detail: unknown): string | null => {
  if (typeof detail === 'string') {
    const exactLabel = AGENT_SESSION_API_DETAIL_LABELS[detail]
    if (exactLabel) return exactLabel

    if (detail.startsWith('agent_session_id must be')) {
      return 'Agent session id format is invalid'
    }

    if (detail.startsWith('AI Trading agent session ' + 'context_' + 'summary must not contain')) {
      return 'Context summary contains sensitive text'
    }

    return null
  }

  if (isRecord(detail) && typeof detail.code === 'string') {
    return AGENT_SESSION_API_DETAIL_LABELS[detail.code] || null
  }

  return null
}

export const formatAiTradingSignalActionApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeDetail = safeSignalActionApiDetailLabel(detail)
    || SIGNAL_ACTION_API_STATUS_LABELS[status]
    || fallback
  return `${statusLabel}: ${safeDetail || readableSignalActionSuffix(fallback)}`
}

export const formatAiTradingStrategyActionApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeDetail = safeStrategyActionApiDetailLabel(detail)
    || STRATEGY_ACTION_API_STATUS_LABELS[status]
    || fallback
  return `${statusLabel}: ${safeDetail || readableSignalActionSuffix(fallback)}`
}

export const formatAiTradingAgentSessionApiError = (
  status: number,
  detail: unknown,
  fallback: string
): string => {
  const statusLabel = status > 0 ? `HTTP ${status}` : 'Request failed'
  const safeDetail = safeAgentSessionApiDetailLabel(detail)
    || AGENT_SESSION_API_STATUS_LABELS[status]
    || fallback
  return `${statusLabel}: ${safeDetail || readableSignalActionSuffix(fallback)}`
}

export const extractAiTradingAgentContextLocators = (
  report: AiTradingProductionComponent,
  locatorMeta: AiTradingAgentContextLocatorMeta[]
): AiTradingAgentContextLocatorView[] => {
  const checks = report.checks || {}

  return locatorMeta.reduce<AiTradingAgentContextLocatorView[]>((acc, meta) => {
    const rawLocator = checks[meta.key]
    if (!rawLocator || typeof rawLocator !== 'object' || Array.isArray(rawLocator)) {
      return acc
    }
    const locator = rawLocator as Record<string, unknown>
    const id = typeof locator.id === 'number' ? locator.id : null
    const agentSessionId = typeof locator.agent_session_id === 'string' ? locator.agent_session_id : null
    if (id === null && !agentSessionId) {
      return acc
    }
    acc.push({
      ...meta,
      id,
      agentSessionId,
      status: typeof locator.status === 'string' ? locator.status : null,
      contextSummaryChars:
        typeof locator.context_summary_chars === 'number' ? locator.context_summary_chars : null,
    })
    return acc
  }, [])
}

export const extractAiTradingProductionEvidenceExplain = (
  source: unknown
): AiTradingProductionEvidenceExplainView | null => {
  if (!isRecord(source)) return null

  const productionEvidenceSource = isRecord(source.production_evidence) ? source.production_evidence : {}
  const progressSource = isRecord(source.progress) ? source.progress : {}
  const schemaSource = isRecord(source.schema) ? source.schema : {}
  const rawItems = Array.isArray(source.items) ? source.items : []

  return {
    mode: typeof source.mode === 'string' ? source.mode : '',
    githubUpload: typeof source.github_upload === 'string' ? source.github_upload : null,
    localV1Accepted: source.local_v1_accepted === true,
    readyForLiveOrders: source.ready_for_live_orders === true,
    productionTrack: typeof source.production_track === 'string' ? source.production_track : null,
    productionEvidence: {
      provided: productionEvidenceSource.provided === true,
      ready: productionEvidenceSource.ready === true,
      acceptedCount: numberValue(productionEvidenceSource.accepted_count),
      requiredCount: numberValue(productionEvidenceSource.required_count),
      evidenceRunIdPresent: productionEvidenceSource.evidence_run_id_present === true,
      expiresAt: typeof productionEvidenceSource.expires_at === 'string' ? productionEvidenceSource.expires_at : null,
      cutoverWindowPresent: productionEvidenceSource.cutover_window_present === true,
      cutoverWindowStartAt: typeof productionEvidenceSource.cutover_window_start_at === 'string' ? productionEvidenceSource.cutover_window_start_at : null,
      cutoverWindowEndAt: typeof productionEvidenceSource.cutover_window_end_at === 'string' ? productionEvidenceSource.cutover_window_end_at : null,
      cutoverApprovalRefPresent: productionEvidenceSource.cutover_approval_ref_present === true,
      secretPatternCount: numberValue(productionEvidenceSource.secret_pattern_count),
      blockers: stringList(productionEvidenceSource.blockers),
      warnings: stringList(productionEvidenceSource.warnings),
    },
    progress: {
      status: typeof progressSource.status === 'string' ? progressSource.status : '',
      acceptedItemIds: stringList(progressSource.accepted_item_ids),
      pendingItemIds: stringList(progressSource.pending_item_ids),
      blockedItemIds: stringList(progressSource.blocked_item_ids),
      nextRequiredItemIds: stringList(progressSource.next_required_item_ids),
      nextRequiredActions: stringList(progressSource.next_required_actions),
      rootNextRequiredActions: stringList(progressSource.root_next_required_actions),
      acceptedCount: numberValue(progressSource.accepted_count),
      pendingCount: numberValue(progressSource.pending_count),
      blockedCount: numberValue(progressSource.blocked_count),
      requiredCount: numberValue(progressSource.required_count),
      liveOrderGateBlockers: stringList(progressSource.live_order_gate_blockers),
    },
    requiredItemIds: stringList(schemaSource.required_item_ids),
    safeArtifactRefSchemes: stringList(schemaSource.safe_artifact_ref_schemes),
    maxEvidenceValidityDays: numberValue(schemaSource.max_evidence_validity_days),
    maxClockSkewSeconds: numberValue(schemaSource.max_clock_skew_seconds),
    maxItemValidationAgeDays: numberValue(schemaSource.max_item_validation_age_days),
    maxCutoverWindowHours: numberValue(schemaSource.max_cutover_window_hours),
    minEvidenceRunIdChars: numberValue(schemaSource.min_evidence_run_id_chars),
    maxEvidenceRunIdChars: numberValue(schemaSource.max_evidence_run_id_chars),
    items: rawItems.reduce<AiTradingProductionEvidenceItemView[]>((acc, rawItem) => {
      if (!isRecord(rawItem)) return acc
      const id = typeof rawItem.id === 'string' ? rawItem.id : ''
      if (!id) return acc
      acc.push({
        id,
        description: typeof rawItem.description === 'string' ? rawItem.description : id,
        documentationStatus:
          typeof rawItem.documentation_status === 'string' ? rawItem.documentation_status : null,
        evidenceStatus: typeof rawItem.evidence_status === 'string' ? rawItem.evidence_status : 'unknown',
        ready: rawItem.ready === true,
        blockers: stringList(rawItem.blockers),
        artifactRefCount: numberValue(rawItem.artifact_ref_count),
        requiredFields: stringList(rawItem.required_fields),
        requiredSummaryTerms: stringList(rawItem.required_summary_terms),
        missingSummaryTerms: stringList(rawItem.missing_summary_terms),
        safeArtifactRefSchemes: stringList(rawItem.safe_artifact_ref_schemes),
        forbiddenValues: stringList(rawItem.forbidden_values),
        operatorGuidance: stringList(rawItem.operator_guidance),
      })
      return acc
    }, []),
    nextActions: stringList(source.next_actions),
  }
}

export const extractAiTradingProductionEvidenceTemplateGuidance = (
  source: unknown
): AiTradingProductionEvidenceTemplateGuidanceView | null => {
  if (!isRecord(source)) return null
  const rawItems = Array.isArray(source.items) ? source.items : []
  const rawRootFields = Array.isArray(source.root_fields) ? source.root_fields : []

  return {
    secretPolicy: typeof source.secret_policy === 'string' ? source.secret_policy : '',
    nextRequiredActions: stringList(source.next_required_actions),
    rootNextRequiredActions: stringList(source.root_next_required_actions),
    rootFields: rawRootFields.reduce<AiTradingProductionEvidenceRootGuidanceView[]>((acc, rawItem) => {
      if (!isRecord(rawItem)) return acc
      const field = typeof rawItem.field === 'string' ? rawItem.field : ''
      if (!field) return acc
      acc.push({
        field,
        requiredValue: typeof rawItem.required_value === 'string' ? rawItem.required_value : '',
        relatedBlockers: stringList(rawItem.related_blockers),
        operatorGuidance: stringList(rawItem.operator_guidance),
        forbiddenValues: stringList(rawItem.forbidden_values),
      })
      return acc
    }, []),
    items: rawItems.reduce<AiTradingProductionEvidenceTemplateGuidanceItemView[]>((acc, rawItem) => {
      if (!isRecord(rawItem)) return acc
      const id = typeof rawItem.id === 'string' ? rawItem.id : ''
      if (!id) return acc
      acc.push({
        id,
        description: typeof rawItem.description === 'string' ? rawItem.description : id,
        requiredFields: stringList(rawItem.required_fields),
        requiredSummaryTerms: stringList(rawItem.required_summary_terms),
        operatorGuidance: stringList(rawItem.operator_guidance),
        safeArtifactRefSchemes: stringList(rawItem.safe_artifact_ref_schemes),
        forbiddenValues: stringList(rawItem.forbidden_values),
      })
      return acc
    }, []),
  }
}

export const extractAiTradingProductionEvidenceDryRun = (
  source: unknown
): AiTradingProductionEvidenceDryRunView | null => {
  if (!isRecord(source)) return null

  return {
    mode: typeof source.mode === 'string' ? source.mode : '',
    acceptedInput: typeof source.accepted_input === 'string' ? source.accepted_input : '',
    expectedInput: typeof source.expected_input === 'string' ? source.expected_input : '',
    rootIsObject: source.root_is_object === true,
    persistence: typeof source.persistence === 'string' ? source.persistence : '',
    payloadBytes: numberValue(source.payload_bytes),
    maxPayloadBytes: numberValue(source.max_payload_bytes),
    itemKeyCount: numberValue(source.item_key_count),
    maxItemKeys: numberValue(source.max_item_keys),
    networkCalls: source.network_calls === true,
    modelCalls: source.model_calls === true,
    orderBackendCalls: source.order_backend_calls === true,
    exchangeCalls: source.exchange_calls === true,
    githubCalls: source.github_calls === true,
    readyForLiveOrders: source.ready_for_live_orders === true,
    liveOrdersUnlocked: source.live_orders_unlocked === true,
    secretPolicy: typeof source.secret_policy === 'string' ? source.secret_policy : '',
  }
}
