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

export interface AiTradingProductionEvidenceExplainView {
  mode: string
  githubUpload: string | null
  localV1Accepted: boolean
  readyForLiveOrders: boolean
  productionTrack: string | null
  productionEvidence: AiTradingProductionEvidenceSummary
  requiredItemIds: string[]
  safeArtifactRefSchemes: string[]
  items: AiTradingProductionEvidenceItemView[]
  nextActions: string[]
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
      blockers: stringList(productionEvidenceSource.blockers),
      warnings: stringList(productionEvidenceSource.warnings),
    },
    requiredItemIds: stringList(schemaSource.required_item_ids),
    safeArtifactRefSchemes: stringList(schemaSource.safe_artifact_ref_schemes),
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
