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
