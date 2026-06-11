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
  items: AiTradingProductionEvidenceTemplateGuidanceItemView[]
  nextRequiredActions: string[]
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
