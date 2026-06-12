/**
 * HyperAiPage - Independent page for Hyper AI (three-column layout)
 * Left: Conversation list
 * Center: Chat area
 * Right: Config panel
 */
import { useState, useEffect, useRef, useMemo, memo } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import PacmanLoader from '@/components/ui/pacman-loader'
import {
  Plus,
  Send,
  Settings,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
  PanelLeftClose,
  PanelLeftOpen,
  Loader2,
  Bot,
  Pencil,
  X,
  CheckCircle2,
  AlertCircle,
  User,
  Wrench,
  Play,
  Brain,
  MessageCircle,
  Blocks,
  FileJson,
  Save,
  ShieldCheck,
  History,
  BarChart3,
  Link2,
  ExternalLink,
  RefreshCw,
  Archive,
  Search as SearchIcon
} from 'lucide-react'
import { pollAiStream } from '@/lib/pollAiStream'
import { authFetch } from '@/lib/authFetch'
import {
  formatAiTradingAgentSessionApiError,
  formatAiTradingMarketUniverseApiError,
  formatAiTradingModelConfigApiError,
  formatAiTradingSignalActionApiError,
  formatAiTradingStrategyActionApiError,
} from '@/lib/aiTradingReadiness'
import BotIntegrationModal from './BotIntegrationModal'
import NotificationConfigModal from './NotificationConfigModal'
import ToolConfigModal, { type ToolInfo } from './ToolConfigModal'

interface Conversation {
  id: number
  title: string
  message_count: number
  is_bot_conversation?: boolean
  updated_at: string
}

interface ToolCallEntry {
  type: 'tool_call' | 'tool_result' | 'reasoning' | 'subagent_progress' | 'confirmation_required' | 'tool_error'
  name?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  content?: string
  subagent?: string
  step?: string
  round?: number
  max_rounds?: number
  taskId?: string
  confirmationId?: string
  description?: string
  status?: 'pending' | 'confirmed' | 'cancelled' | 'failed'
  message?: string
  severity?: string
}

// API format for tool_calls_log from database
interface ToolCallLogEntry {
  tool: string
  args: Record<string, unknown>
  result: string
}

/**
 * Represents a successfully created entity that should be displayed as a card.
 * Extracted from tool_calls_log when save_xxx tools return success: true.
 */
interface CreatedEntityCard {
  type: 'prompt' | 'program' | 'signal_pool' | 'ai_trader' | 'factor'
  id: number
  name: string
  content?: string  // template_text for prompt, code for program, JSON for signal_pool
  viewUrl: string
}

interface Message {
  id?: number
  role: 'user' | 'assistant'
  content: string
  reasoning_snapshot?: string
  tool_calls_log?: string
  is_complete?: boolean
  interrupt_reason?: string
  created_at?: string
  // Streaming state
  isStreaming?: boolean
  statusText?: string
  toolCalls?: ToolCallEntry[]
  isInterrupted?: boolean
  interruptedRound?: number
}

interface AiTradingStrategySpec {
  symbol?: string
  timeframe?: string
  metadata?: Record<string, unknown>
  backtest?: AiTradingBacktestSummary
  entry?: {
    bias?: string
  }
  exit?: {
    stop_loss?: {
      required?: boolean
      rule?: string | null
    }
    take_profit?: {
      required?: boolean
      rule?: string | null
    }
  }
  risk?: {
    profile?: string
    max_loss_pct?: number | null
    max_loss_usd?: number | null
    max_leverage?: number | null
    position_notional_usd?: number | null
  }
  execution?: {
    signal_only?: boolean
    auto_execution_enabled?: boolean
    requires_user_approval?: boolean
    ai_may_place_orders?: boolean
    order_backend_only?: boolean
  }
  validation?: {
    status?: string
    issues?: string[]
    warnings?: string[]
    safe_to_emit_signal?: boolean
  }
}

interface AiTradingBacktestSummary {
  required_before_handoff?: boolean
  status?: string
  accepted_for_handoff?: boolean
  backtest_id?: string | null
  source?: string | null
  metrics?: Record<string, unknown>
  period?: Record<string, unknown>
  updated_at?: string | null
}

interface AiTradingStrategySpecRecord {
  id: number
  name: string
  symbol: string
  status: string
  approved_at?: string | null
  agent_session?: {
    id?: string | null
    name?: string | null
    context_summary?: string | null
    context_summary_chars?: number | null
    summary_max_chars?: number | null
    status?: string | null
  }
  spec?: AiTradingStrategySpec
  validation?: {
    status?: string
    issues?: string[]
    warnings?: string[]
    safe_to_emit_signal?: boolean
  }
}

interface AiTradingSignalEventRecord {
  id: number
  strategy_spec_id: number
  symbol: string
  action: string
  status: string
  handoff_status?: string
  agent_session?: {
    id?: string | null
    name?: string | null
    context_summary?: string | null
    context_summary_chars?: number | null
    summary_max_chars?: number | null
    status?: string | null
  }
  handoff_eligibility?: {
    eligible?: boolean
    blockers?: string[]
    gateway_ready?: boolean
    can_retry?: boolean
    default_handoff_status?: string
    signal_age_seconds?: number | null
    max_handoff_age_seconds?: number | null
  }
  created_at?: string | null
  signal?: Record<string, unknown>
}

interface AiTradingSignalHandoffAttemptRecord {
  id: number
  signal_event_id: number
  result: string
  gateway_ready?: boolean
  agent_session?: {
    id?: string | null
    name?: string | null
    context_summary?: string | null
    context_summary_chars?: number | null
    summary_max_chars?: number | null
    status?: string | null
  }
  blockers?: string[]
  eligibility?: Record<string, unknown>
  error_message?: string | null
  created_at?: string | null
}

interface AiTradingBacktestResultRecord {
  id: number
  status: string
  source?: string
  binding_id?: number | null
  account_name?: string | null
  program_name?: string | null
  exchange?: string | null
  symbols?: string[]
  period?: Record<string, unknown>
  metrics?: Record<string, unknown>
  handoff_ready?: boolean
  completed_at?: string | null
}

interface AiTradingBacktestPreflight {
  ready?: boolean
  blockers?: string[]
  recommended_binding?: Record<string, unknown> | null
  default_request?: {
    binding_id?: number
    start_time_ms?: number
    end_time_ms?: number
    initial_balance?: number
    slippage_percent?: number
    fee_rate?: number
  } | null
  candidate_bindings?: Record<string, unknown>[]
}

interface AiTradingBacktestRunStatus {
  specId: number
  phase: 'preflight' | 'calculating' | 'running' | 'attaching'
  current?: number
  total?: number
  backtestId?: number
}

interface AiTradingBacktestEvidenceDetail {
  strategy_spec_id?: number
  strategy_symbol?: string
  handoff_ready?: boolean
  quality_issues?: string[]
  backtest_result?: {
    id?: number
    status?: string
    exchange?: string
    symbols?: string[]
    metrics?: Record<string, unknown>
    equity_curve_sample?: Array<Record<string, unknown>>
    period?: Record<string, unknown>
  }
  trigger_summary?: {
    total?: number
    returned?: number
    action_counts?: Record<string, number>
    triggers?: Array<Record<string, unknown>>
    markers?: Array<Record<string, unknown>>
  }
}

interface AiTradingMarket {
  symbol?: string
  coin?: string
  exchange_symbol?: string
  display_symbol?: string
  category?: string
  dex?: string
}

type AiTradingSymbolGroupKey = 'crypto' | 'hip3' | 'all'
type AiTradingSymbolGroups = Record<AiTradingSymbolGroupKey, string[]>

interface AiTradingRuntimeStatus {
  gateway?: {
    enabled?: boolean
    url_configured?: boolean
    mode?: string
    default_handoff_status?: string
    target_kind?: string
    max_handoff_age_seconds?: number | null
    production_handoff_approved?: boolean
    runtime_config_blockers?: string[]
  }
  model_adjustment?: {
    ready?: boolean
    configured?: boolean
    provider?: string | null
    model?: string | null
    source?: string
    provider_supported?: boolean
    blockers?: string[]
    next_actions?: string[]
    credential_present?: boolean
    credential_value_returned?: boolean
  }
  strategy_specs?: {
    total?: number
    by_status?: Record<string, number>
    backtest_evidence?: {
      total?: number
      ready?: number
      blocked?: number
      missing?: number
      by_blocker?: Record<string, number>
    }
  }
  agent_sessions?: {
    total?: number
    context_budget?: {
      total?: number
      active?: number
      archived?: number
      with_context_summary?: number
      empty_context_summary?: number
      context_summary_max_chars?: number
      near_budget_threshold_chars?: number
      max_context_summary_chars?: number
      near_budget_count?: number
      over_budget_count?: number
      redacted_context_summary_count?: number
      sensitive_context_summary_count?: number
      secret_policy?: string
    }
  }
  signal_events?: {
    total?: number
    by_status?: Record<string, number>
    handoff_eligibility?: {
      review_candidates?: number
      eligible?: number
      blocked?: number
      by_blocker?: Record<string, number>
    }
  }
  handoff_attempts?: {
    total?: number
    by_result?: Record<string, number>
    gateway_ready?: number
    gateway_not_ready?: number
    latest?: {
      id?: number
      signal_event_id?: number
      strategy_spec_id?: number
      symbol?: string
      action?: string
      result?: string
      gateway_ready?: boolean
      created_at?: string | null
    } | null
  }
}

interface AiTradingAgentSessionRecord {
  id: string
  name?: string | null
  context_summary?: string | null
  context_summary_chars?: number | null
  summary_max_chars?: number | null
  status?: string | null
  strategy_spec_count?: number
  signal_event_count?: number
  symbols?: string[]
  by_strategy_status?: Record<string, number>
  by_signal_status?: Record<string, number>
  latest_strategy_spec_id?: number | null
  latest_signal_event_id?: number | null
  updated_at?: string | null
}

interface AiTradingAgentSessionContext {
  agent_session?: {
    id?: string
    name?: string | null
    context_summary?: string | null
    context_summary_chars?: number | null
    summary_max_chars?: number | null
    status?: string | null
  }
  compression?: Record<string, unknown>
  strategy_specs?: Array<Record<string, unknown>>
  signal_events?: Array<Record<string, unknown>>
  handoff_attempts?: Array<Record<string, unknown>>
}

const AI_TRADING_BACKTEST_DEFAULTS = {
  days: 30,
  initial_balance: 10000,
  slippage_percent: 0.05,
  fee_rate: 0.035,
}
const AI_TRADING_NEW_AGENT_SESSION_VALUE = '__new_ai_trading_agent_session__'

const AI_TRADING_ACTION_TIMEOUT_MS = 45_000
const AI_TRADING_BACKTEST_SUMMARY_METRICS_TEMPLATE = '{"total_return":0,"max_drawdown":0,"sharpe":0,"trade_count":1}'
const AI_TRADING_MODEL_OUTPUT_SENSITIVE_WARNING = 'model_output_sensitive_text_redacted'
const AI_TRADING_MODEL_OUTPUT_DIRECT_ORDER_WARNING = 'model_output_direct_order_intent_ignored'
const AI_TRADING_MODEL_OUTPUT_SAFETY_WARNINGS = [
  AI_TRADING_MODEL_OUTPUT_SENSITIVE_WARNING,
  AI_TRADING_MODEL_OUTPUT_DIRECT_ORDER_WARNING,
]
const AI_TRADING_SYMBOL_TEXT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$/
const AI_TRADING_EXCHANGE_SYMBOL_TEXT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}:[A-Za-z0-9][A-Za-z0-9._-]{0,31}$/
const AI_TRADING_SYMBOL_SENSITIVE_PATTERN = /(api[_-]?key|authorization|bearer|token|secret|private[_-]?key|password)/i
const AI_TRADING_AGENT_SESSION_ID_SENSITIVE_PATTERN = /(api[_-]?key|authorization|bearer|token|secret|private[_-]?key|password)/i

const AI_TRADING_BACKTEST_ROUTE_RE = /^\/(?:app\/)?ai-trading\/backtests\/(\d+)\/?$/
const AI_TRADING_AGENT_SESSION_ROUTE_RE = /^\/(?:app\/)?ai-trading\/sessions\/([^/?#]+)\/?$/

async function authFetchAiTradingAction(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = AI_TRADING_ACTION_TIMEOUT_MS
): Promise<Response> {
  if (typeof AbortController === 'undefined' || typeof window === 'undefined') {
    return authFetch(input, init)
  }

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    return await authFetch(input, {
      ...init,
      signal: controller.signal,
    })
  } catch (error) {
    if ((error as { name?: string })?.name === 'AbortError') {
      throw new Error('AI Trading action timed out. Please retry.')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}

function parseAiTradingBacktestRouteSpecId(): number | null {
  if (typeof window === 'undefined') {
    return null
  }

  const pathMatch = window.location.pathname.match(AI_TRADING_BACKTEST_ROUTE_RE)
  const rawId = pathMatch?.[1]
  if (rawId) {
    const parsed = Number(rawId)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }

  const hash = window.location.hash.slice(1)
  const hashParamIndex = hash.indexOf('?')
  if (hashParamIndex === -1) {
    return null
  }

  const pageName = hash.slice(0, hashParamIndex)
  if (!['ai-trading', 'hyper-ai'].includes(pageName)) {
    return null
  }

  const params = new URLSearchParams(hash.slice(hashParamIndex + 1))
  const hashId = params.get('backtestSpecId') || params.get('backtest_spec_id')
  const parsed = Number(hashId)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function cleanAiTradingAgentSessionRouteId(value?: string | null): string | null {
  if (!value) {
    return null
  }
  let decoded = value
  try {
    decoded = decodeURIComponent(value)
  } catch {
    decoded = value
  }
  const trimmed = decoded.trim()
  if (AI_TRADING_AGENT_SESSION_ID_SENSITIVE_PATTERN.test(trimmed)) {
    return null
  }
  return /^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$/.test(trimmed) ? trimmed : null
}

function sanitizeAiTradingSymbolText(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const raw = value.trim()
  if (!raw || raw.length > 64 || AI_TRADING_SYMBOL_SENSITIVE_PATTERN.test(raw)) {
    return null
  }
  if (AI_TRADING_EXCHANGE_SYMBOL_TEXT_PATTERN.test(raw)) {
    const [dex, symbol] = raw.split(':', 2)
    return `${dex.toLowerCase()}:${symbol.toUpperCase()}`
  }
  if (AI_TRADING_SYMBOL_TEXT_PATTERN.test(raw)) {
    return raw.toUpperCase()
  }
  return null
}

function parseAiTradingAgentSessionRouteId(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  const pathMatch = window.location.pathname.match(AI_TRADING_AGENT_SESSION_ROUTE_RE)
  const pathId = cleanAiTradingAgentSessionRouteId(pathMatch?.[1])
  if (pathId) {
    return pathId
  }

  const hash = window.location.hash.slice(1)
  const hashParamIndex = hash.indexOf('?')
  if (hashParamIndex === -1) {
    return null
  }

  const pageName = hash.slice(0, hashParamIndex)
  if (!['ai-trading', 'hyper-ai'].includes(pageName)) {
    return null
  }

  const params = new URLSearchParams(hash.slice(hashParamIndex + 1))
  return cleanAiTradingAgentSessionRouteId(params.get('agentSessionId') || params.get('agent_session_id') || params.get('sessionId'))
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function textValue(value: unknown, fallback = '-'): string {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  return String(value)
}

type AiTradingContextBudgetSource = {
  context_summary?: string | null
  context_summary_chars?: number | null
  summary_max_chars?: number | null
}

function numberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function formatAiTradingContextBudget(
  source?: AiTradingContextBudgetSource | null,
  draftSummary?: string
): string {
  const chars = draftSummary !== undefined
    ? draftSummary.length
    : numberOrNull(source?.context_summary_chars) ?? String(source?.context_summary || '').length
  const maxChars = numberOrNull(source?.summary_max_chars) ?? 2000
  return `${chars} / ${maxChars}`
}

const SENSITIVE_TOOL_ARG_KEY_PATTERN = /(api[_-]?key|secret|token|private|password|authorization|bearer)/i
const AI_TRADING_CONTEXT_SUMMARY_KEY_PATTERN = /^(agent_)?context_summary$/i
const AI_TRADING_PROMPT_TEXT_KEY_PATTERN = /(context[_-]?summary|agent[_-]?context[_-]?summary|evidence|gateway|response|raw|message|error|exception|trace|log|prompt|completion|rationale|instruction|note|notes|summary)/i
const AI_TRADING_PROMPT_TEXT_SENSITIVE_PATTERN = /(api[_-]?key|secret|token|private[_-]?key|password|authorization|bearer\s+[a-z0-9._=-]+|sk-[a-z0-9_-]{8,}|dashscope[_-]?api|deepseek[_-]?api|qwen[_-]?api)/i

function maskToolArgValue(key: string, value: unknown): unknown {
  if (SENSITIVE_TOOL_ARG_KEY_PATTERN.test(key)) {
    return '***'
  }
  if (Array.isArray(value)) {
    return value.map(item => maskToolArgValue(key, item))
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([childKey, childValue]) => [
        childKey,
        maskToolArgValue(childKey, childValue),
      ])
    )
  }
  return value
}

function sanitizeAiTradingAgentSessionContextForPrompt(value: unknown, key = ''): unknown {
  return sanitizeAiTradingPromptPacket(value, key)
}

function sanitizeAiTradingPromptPacket(value: unknown, key = ''): unknown {
  if (
    AI_TRADING_CONTEXT_SUMMARY_KEY_PATTERN.test(key) &&
    typeof value === 'string' &&
    SENSITIVE_TOOL_ARG_KEY_PATTERN.test(value)
  ) {
    return '[redacted_sensitive_context]'
  }
  if (SENSITIVE_TOOL_ARG_KEY_PATTERN.test(key)) {
    return '***'
  }
  if (
    typeof value === 'string' &&
    AI_TRADING_PROMPT_TEXT_KEY_PATTERN.test(key) &&
    AI_TRADING_PROMPT_TEXT_SENSITIVE_PATTERN.test(value)
  ) {
    return '[redacted_sensitive_text]'
  }
  if (Array.isArray(value)) {
    return value.map(item => sanitizeAiTradingPromptPacket(item, key))
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([childKey, childValue]) => [
        childKey,
        sanitizeAiTradingPromptPacket(childValue, childKey),
      ])
    )
  }
  return value
}

function maskToolArgsForDisplay(args: Record<string, unknown> = {}): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(args).map(([key, value]) => [key, maskToolArgValue(key, value)])
  )
}

function formatToolArgForDisplay(key: string, value: unknown): string {
  return JSON.stringify(maskToolArgValue(key, value))
}

interface CompressionPoint {
  message_id: number
  summary: string
  compressed_at: string
}

interface SkillInfo {
  name: string
  description: string
  description_zh: string
  command: string
  enabled: boolean
}

interface TokenUsage {
  current_tokens: number
  max_tokens: number
  usage_ratio: number
  show_warning: boolean
}

interface LLMProvider {
  id: string
  name: string
  models: string[]
  base_url?: string
}

// Memory category icons and colors
const MEMORY_CATEGORY_STYLES: Record<string, { icon: string; color: string }> = {
  preference: { icon: '🎯', color: 'text-blue-500' },
  decision: { icon: '⚡', color: 'text-amber-500' },
  lesson: { icon: '📖', color: 'text-green-500' },
  insight: { icon: '💡', color: 'text-purple-500' },
  context: { icon: '📌', color: 'text-gray-500' },
}

// Memory Modal component - read-only view of AI memories
function MemoryModal({
  open,
  onClose
}: {
  open: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [memories, setMemories] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open) {
      setLoading(true)
      authFetch('/api/hyper-ai/memories?limit=50')
        .then(res => res.json())
        .then(data => setMemories(data.memories || []))
        .catch(() => setMemories([]))
        .finally(() => setLoading(false))
    }
  }, [open])

  if (!open) return null

  // Group memories by category
  const grouped: Record<string, any[]> = {}
  for (const m of memories) {
    const cat = m.category || 'context'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(m)
  }

  const categoryOrder = ['preference', 'decision', 'lesson', 'insight', 'context']

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="w-full max-w-3xl bg-background rounded-lg shadow-xl flex flex-col"
           style={{ height: '600px' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold">
              {t('hyperAi.memory.title', 'What Hyper AI Remembered')}
            </h2>
            {memories.length > 0 && (
              <span className="text-xs text-muted-foreground ml-2">
                {t('hyperAi.memory.items', '{{count}} memories', { count: memories.length })}
              </span>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : memories.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Brain className="w-12 h-12 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground max-w-sm">
                {t('hyperAi.memory.empty')}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {categoryOrder.map(cat => {
                const items = grouped[cat]
                if (!items || items.length === 0) return null
                const style = MEMORY_CATEGORY_STYLES[cat] || MEMORY_CATEGORY_STYLES.context
                const label = t(`hyperAi.memory.category.${cat}`, cat)
                return (
                  <div key={cat}>
                    <div className="flex items-center gap-2 mb-2">
                      <span>{style.icon}</span>
                      <span className={`text-sm font-medium ${style.color}`}>{label}</span>
                      <span className="text-xs text-muted-foreground">({items.length})</span>
                    </div>
                    <div className="space-y-2 ml-6">
                      {items.map((m: any) => (
                        <MemoryItem key={m.id} memory={m} />
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MemoryItem({ memory }: { memory: any }) {
  const importance = memory.importance || 0.5
  const stars = Math.round(importance * 5)
  const date = memory.created_at
    ? new Date(memory.created_at).toLocaleDateString()
    : ''

  return (
    <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
      <p className="leading-relaxed">{memory.content}</p>
      <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
        <span>{'★'.repeat(stars)}{'☆'.repeat(5 - stars)}</span>
        {date && <span>{date}</span>}
        {memory.source && <span className="capitalize">{memory.source}</span>}
      </div>
    </div>
  )
}

// LLM Config Modal component
function LLMConfigModal({
  open,
  onClose,
  providers,
  currentProfile,
  onSaved
}: {
  open: boolean
  onClose: () => void
  providers: LLMProvider[]
  currentProfile: any
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [selectedProvider, setSelectedProvider] = useState(currentProfile?.llm_provider || '')
  const [apiKey, setApiKey] = useState('')
  const [modelInput, setModelInput] = useState(currentProfile?.llm_model || '')
  const [customBaseUrl, setCustomBaseUrl] = useState(currentProfile?.llm_base_url || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const currentProvider = providers.find(p => p.id === selectedProvider)

  useEffect(() => {
    if (open) {
      setSelectedProvider(currentProfile?.llm_provider || '')
      setModelInput(currentProfile?.llm_model || '')
      setCustomBaseUrl(currentProfile?.llm_base_url || '')
      setApiKey('')
      setError('')
      setSuccess(false)
    }
  }, [open, currentProfile])

  // When provider changes, set default model if current model is empty
  useEffect(() => {
    if (selectedProvider && !modelInput) {
      const provider = providers.find(p => p.id === selectedProvider)
      if (provider && provider.models.length > 0) {
        setModelInput(provider.models[0])
      }
    }
  }, [selectedProvider])

  const handleSave = async () => {
    if (!selectedProvider || !apiKey) {
      setError(t('hyperAi.onboarding.fillRequired', 'Please fill in all required fields'))
      return
    }

    if (selectedProvider === 'custom' && !customBaseUrl) {
      setError(t('hyperAi.onboarding.baseUrlRequired', 'Base URL is required for custom provider'))
      return
    }

    setSaving(true)
    setError('')
    const fallback = 'Failed to save model configuration'

    try {
      const res = await authFetch('/api/hyper-ai/profile/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          api_key: apiKey,
          model: modelInput,
          base_url: selectedProvider === 'custom' ? customBaseUrl : undefined
        })
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(formatAiTradingModelConfigApiError(res.status, data.detail, fallback))
        return
      }

      setSuccess(true)
      setTimeout(() => {
        onSaved()
        onClose()
      }, 800)
    } catch (e) {
      console.error('Failed to save Hyper AI model config:', e)
      setError(formatAiTradingModelConfigApiError(0, null, fallback))
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="w-full max-w-md bg-background rounded-lg shadow-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t('hyperAi.configTitle', 'Hyper AI Config')}</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t('hyperAi.onboarding.provider', 'AI Provider')}</Label>
            <Select value={selectedProvider} onValueChange={(v) => { setSelectedProvider(v); setModelInput('') }}>
              <SelectTrigger>
                <SelectValue placeholder={t('hyperAi.onboarding.selectProvider', 'Select provider')} />
              </SelectTrigger>
              <SelectContent>
                {providers.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedProvider === 'custom' && (
            <div className="space-y-2">
              <Label>{t('hyperAi.onboarding.baseUrl', 'Base URL')}</Label>
              <Input
                value={customBaseUrl}
                onChange={e => setCustomBaseUrl(e.target.value)}
                placeholder="https://api.example.com/v1"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label>{t('hyperAi.onboarding.apiKey', 'API Key')}</Label>
            <Input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={currentProfile?.llm_configured ? t('hyperAi.onboarding.apiKeyConfigured', 'Enter new API key to update') : 'sk-...'}
            />
          </div>

          {selectedProvider && (
            <div className="space-y-2">
              <Label>{t('hyperAi.onboarding.model', 'Model')}</Label>
              <div className="flex gap-1">
                <Input
                  value={modelInput}
                  onChange={e => setModelInput(e.target.value)}
                  placeholder={t('hyperAi.onboarding.modelPlaceholder', 'Enter or select model')}
                  className="flex-1"
                />
                {currentProvider && currentProvider.models.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="icon" className="shrink-0">
                        <ChevronDown className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="max-h-60 overflow-y-auto">
                      {currentProvider.models.map(m => (
                        <DropdownMenuItem key={m} onClick={() => setModelInput(m)}>
                          {m}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="flex items-center gap-2 text-destructive text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="break-all">{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 text-green-600 text-sm">
            <CheckCircle2 className="w-4 h-4" />
            {t('hyperAi.onboarding.connectionSuccess', 'Connection successful!')}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <Button
            variant="outline"
            onClick={onClose}
            className="flex-1"
            data-testid="ai-trading-model-config-later-button"
          >
            {currentProfile?.llm_configured
              ? t('common.cancel', 'Cancel')
              : t('hyperAi.aiTradingConfigureLater', 'Configure later')}
          </Button>
          <Button onClick={handleSave} disabled={!selectedProvider || !apiKey || saving} className="flex-1">
            {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
            {saving ? t('hyperAi.onboarding.testing', 'Testing...') : t('common.save', 'Save')}
          </Button>
        </div>
      </div>
    </div>
  )
}

// Welcome message component
function BotConvIcon() {
  return (
    <svg viewBox="0 0 1024 1024" className="w-4 h-4 flex-shrink-0" fill="currentColor">
      <path d="M0 0m128 0l768 0q128 0 128 128l0 768q0 128-128 128l-768 0q-128 0-128-128l0-768q0-128 128-128Z" fill="#E1EBFF"/>
      <path d="M640.704 213.12A75.136 75.136 0 0 0 588.544 192c-18.944 0-37.44 7.552-50.688 21.12a89.536 89.536 0 0 0-20.032 72.32v14.336A97.152 97.152 0 0 1 479.616 364.8c-26.88 26.048-61.632 43.52-98.688 48.384-6.4 0-17.728-2.304-19.648-2.304a124.672 124.672 0 0 0-140.672 46.528 33.088 33.088 0 0 0 4.544 39.68L328.384 600.32l-131.584 182.272a32.192 32.192 0 0 0 10.944 44.608c10.624 6.4 23.488 6.4 34.048 0l179.968-133.504 104.768 104.768a32 32 0 0 0 38.592 4.928 127.168 127.168 0 0 0 46.848-143.68v-5.312l-3.392-11.712c1.92-32.896 16.256-63.936 39.68-86.976a122.24 122.24 0 0 1 77.184-50.304h14.72c25.344 3.84 51.072-3.392 70.72-19.648a71.424 71.424 0 0 0 4.928-96L640.64 213.12z" fill="#3478FF"/>
    </svg>
  )
}

function TelegramSmallIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 text-[#26A5E4]" fill="currentColor">
      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
    </svg>
  )
}

function DiscordSmallIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-3.5 h-3.5 text-[#5865F2]" fill="currentColor">
      <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.947 2.418-2.157 2.418z"/>
    </svg>
  )
}

function NotificationBellSmallIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 1024 1024" fill="currentColor">
      <path d="M512 0c282.666667 0 512 229.333333 512 512S794.666667 1024 512 1024 0 794.666667 0 512 229.333333 0 512 0z" fill="#2E74EE" opacity=".12" />
      <path d="M505.6 771.2L309.333333 611.2h-29.866666c-19.2 0-34.133333-14.933333-34.133334-34.133333V442.666667c0-19.2 14.933333-33.066667 34.133334-33.066667h36.266666l188.8-155.733333s48-30.933333 48 26.666666v462.933334c0 36.266667-20.266667 38.4-34.133333 34.133333-8.533333-2.133333-12.8-6.4-12.8-6.4z m117.333333-160c-6.4 0-12.8-2.133333-17.066666-7.466667-8.533333-9.6-7.466667-24.533333 2.133333-32 17.066667-14.933333 26.666667-36.266667 26.666667-58.666666s-9.6-43.733333-25.6-58.666667c-9.6-8.533333-9.6-23.466667-2.133334-32 8.533333-9.6 22.4-10.666667 32-2.133333 25.6 23.466667 40.533333 57.6 40.533334 92.8 0 35.2-14.933333 69.333333-41.6 92.8-4.266667 3.2-9.6 5.333333-14.933334 5.333333z m21.333334 88.533333c-8.533333 0-17.066667-5.333333-21.333334-13.866666-4.266667-11.733333 1.066667-24.533333 12.8-28.8 58.666667-23.466667 97.066667-77.866667 97.066667-139.733334s-38.4-116.266667-98.133333-139.733333c-11.733333-4.266667-17.066667-18.133333-12.8-28.8s18.133333-17.066667 29.866666-12.8c37.333333 14.933333 68.266667 39.466667 90.666667 70.4 23.466667 33.066667 35.2 70.4 35.2 110.933333 0 39.466667-11.733333 77.866667-35.2 109.866667-22.4 32-53.333333 56.533333-90.666667 70.4-2.133333 1.066667-4.266667 2.133333-7.466666 2.133333z" fill="#2E74EE" />
    </svg>
  )
}

function WelcomeMessage({
  nickname,
  t,
  onSuggestionClick
}: {
  nickname?: string
  t: any
  onSuggestionClick: (question: string) => void
}) {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [isNewUser, setIsNewUser] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authFetch('/api/hyper-ai/suggestions')
      .then(res => res.json())
      .then(data => {
        setSuggestions(data.suggestions || [])
        setIsNewUser(data.is_new_user ?? true)
      })
      .catch(() => {
        setSuggestions([])
        setIsNewUser(true)
      })
      .finally(() => setLoading(false))
  }, [])

  const greeting = nickname
    ? t('hyperAi.welcomeWithName', { name: nickname, defaultValue: `你好，${nickname}！我是 Hyper AI，你的专属交易助手。` })
    : t('hyperAi.welcomeNoName', '你好！我是 Hyper AI，Hyper Alpha Arena 的智能助手。')

  // Default suggestions for new users (follows i18n)
  const defaultSuggestions = [
    t('hyperAi.defaultSuggestions.intro', 'What can you help me with?'),
    t('hyperAi.defaultSuggestions.setup', 'Guide me through the initial setup'),
    t('hyperAi.defaultSuggestions.first', 'I want to create my first trading strategy'),
    t('hyperAi.defaultSuggestions.strategyRadar', 'Help me find strategy ideas from Strategy Radar'),
    t('hyperAi.defaultSuggestions.walletSignals', 'How do I connect Hyper Insight wallet signals?'),
  ]

  const displaySuggestions = (isNewUser || suggestions.length === 0) ? defaultSuggestions : suggestions

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
        <Bot className="w-8 h-8 text-primary" />
      </div>
      <p className="text-lg mb-4">{greeting}</p>
      <div className="text-sm text-muted-foreground space-y-1 max-w-md">
        <p>{t('hyperAi.welcomeCapabilities', '我可以帮你：')}</p>
        <ul className="text-left list-disc list-inside space-y-1 mt-2">
          <li>{t('hyperAi.capability1', '了解系统功能和使用方法')}</li>
          <li>{t('hyperAi.capability2', '生成和优化 AI 交易策略')}</li>
          <li>{t('hyperAi.capability3', '管理 AI 交易员和钱包配置')}</li>
          <li>{t('hyperAi.capability4', '分析市场数据和交易表现')}</li>
        </ul>
        <p className="mt-4">{t('hyperAi.welcomePrompt', '有什么想了解的，直接问我就行。')}</p>
      </div>

      {/* Suggestion buttons */}
      {!loading && displaySuggestions.length > 0 && (
        <div className="mt-6 space-y-2 w-full max-w-md">
          {displaySuggestions.map((question, idx) => (
            <button
              key={idx}
              onClick={() => onSuggestionClick(question)}
              className="w-full px-4 py-3 text-left text-sm rounded-lg border border-border bg-card hover:bg-accent hover:border-primary/50 transition-colors"
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function HyperAiPage() {
  const { t, i18n } = useTranslation()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConvId, setCurrentConvId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [compressionPoints, setCompressionPoints] = useState<CompressionPoint[]>([])
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [profile, setProfile] = useState<any>(null)
  const [nickname, setNickname] = useState<string>('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showConfig, setShowConfig] = useState(true)
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showMemoryModal, setShowMemoryModal] = useState(false)
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [activeSkill, setActiveSkill] = useState<string | null>(null)
  const [skillsLoading, setSkillsLoading] = useState(false)
  const [skillsEditMode, setSkillsEditMode] = useState(false)
  const [pendingSkillToggles, setPendingSkillToggles] = useState<Record<string, boolean>>({})
  const [showBotModal, setShowBotModal] = useState(false)
  const [showDiscordBotModal, setShowDiscordBotModal] = useState(false)
  const [botConfig, setBotConfig] = useState<{ platform: string; bot_username: string | null; status: string } | null>(null)
  const [discordBotConfig, setDiscordBotConfig] = useState<{ platform: string; bot_username: string | null; bot_app_id?: string; status: string } | null>(null)
  const [showNotificationModal, setShowNotificationModal] = useState(false)
  const [notificationCount, setNotificationCount] = useState(0)
  const [externalTools, setExternalTools] = useState<ToolInfo[]>([])
  const [showToolModal, setShowToolModal] = useState(false)
  const [selectedTool, setSelectedTool] = useState<ToolInfo | null>(null)
  const [tradingSymbols, setTradingSymbols] = useState<string[]>([])
  const [tradingSymbolGroups, setTradingSymbolGroups] = useState<AiTradingSymbolGroups>({
    crypto: [],
    hip3: [],
    all: [],
  })
  const [tradingSymbolGroup, setTradingSymbolGroup] = useState<AiTradingSymbolGroupKey>('all')
  const [tradingSymbolSource, setTradingSymbolSource] = useState<'watchlist' | 'universe' | 'available' | 'none'>('none')
  const [tradingSymbolsLoading, setTradingSymbolsLoading] = useState(false)
  const [tradingSymbolsError, setTradingSymbolsError] = useState<string | null>(null)
  const [strategyDraft, setStrategyDraft] = useState<AiTradingStrategySpec | null>(null)
  const [strategyDraftRecord, setStrategyDraftRecord] = useState<AiTradingStrategySpecRecord | null>(null)
  const [strategyDraftLoadingSymbol, setStrategyDraftLoadingSymbol] = useState<string | null>(null)
  const [strategyDraftSaving, setStrategyDraftSaving] = useState(false)
  const [strategyDraftApproving, setStrategyDraftApproving] = useState(false)
  const [strategyAdjustInstruction, setStrategyAdjustInstruction] = useState('')
  const [strategyAdjusting, setStrategyAdjusting] = useState(false)
  const [strategyModelAdjusting, setStrategyModelAdjusting] = useState(false)
  const [strategySignalPreviewLoading, setStrategySignalPreviewLoading] = useState(false)
  const [strategyBacktestSummaryId, setStrategyBacktestSummaryId] = useState('')
  const [strategyBacktestSummaryMetricsText, setStrategyBacktestSummaryMetricsText] = useState(AI_TRADING_BACKTEST_SUMMARY_METRICS_TEMPLATE)
  const [strategyProgramBacktestResultId, setStrategyProgramBacktestResultId] = useState('')
  const [strategyProgramBacktestRunConfirmed, setStrategyProgramBacktestRunConfirmed] = useState(false)
  const [strategyBacktestLoadingId, setStrategyBacktestLoadingId] = useState<number | null>(null)
  const [strategyBacktestLoadingSource, setStrategyBacktestLoadingSource] = useState<'summary' | 'program' | 'latest' | 'preflight' | 'run' | 'evidence' | null>(null)
  const [strategyBacktestRunStatus, setStrategyBacktestRunStatus] = useState<AiTradingBacktestRunStatus | null>(null)
  const [strategyBacktestEvidenceDetail, setStrategyBacktestEvidenceDetail] = useState<AiTradingBacktestEvidenceDetail | null>(null)
  const [strategyBacktestEvidenceDialogOpen, setStrategyBacktestEvidenceDialogOpen] = useState(false)
  const [strategyBacktestEvidencePageSpecId, setStrategyBacktestEvidencePageSpecId] = useState<number | null>(() => parseAiTradingBacktestRouteSpecId())
  const [strategyBacktestEvidencePageLoading, setStrategyBacktestEvidencePageLoading] = useState(false)
  const [strategyBacktestEvidencePageError, setStrategyBacktestEvidencePageError] = useState<string | null>(null)
  const [strategyBacktestEvidencePageReloadKey, setStrategyBacktestEvidencePageReloadKey] = useState(0)
  const [agentSessionDetailPageId, setAgentSessionDetailPageId] = useState<string | null>(() => parseAiTradingAgentSessionRouteId())
  const [agentSessionDetailContext, setAgentSessionDetailContext] = useState<AiTradingAgentSessionContext | null>(null)
  const [agentSessionDetailLoading, setAgentSessionDetailLoading] = useState(false)
  const [agentSessionDetailError, setAgentSessionDetailError] = useState<string | null>(null)
  const [agentSessionDetailReloadKey, setAgentSessionDetailReloadKey] = useState(0)
  const [agentSessionDetailCompressing, setAgentSessionDetailCompressing] = useState(false)
  const [signalHandoffLoadingId, setSignalHandoffLoadingId] = useState<number | null>(null)
  const [signalHandoffConfirmedEventIds, setSignalHandoffConfirmedEventIds] = useState<Record<number, boolean>>({})
  const [signalHandoffAttemptsLoadingId, setSignalHandoffAttemptsLoadingId] = useState<number | null>(null)
  const [signalRejectLoadingId, setSignalRejectLoadingId] = useState<number | null>(null)
  const [strategyDraftError, setStrategyDraftError] = useState<string | null>(null)
  const [aiTradingRuntime, setAiTradingRuntime] = useState<AiTradingRuntimeStatus | null>(null)
  const [recentAgentSessions, setRecentAgentSessions] = useState<AiTradingAgentSessionRecord[]>([])
  const [archivedAgentSessions, setArchivedAgentSessions] = useState<AiTradingAgentSessionRecord[]>([])
  const [selectedAiTradingAgentSessionId, setSelectedAiTradingAgentSessionId] = useState('')
  const [agentSessionNameDraft, setAgentSessionNameDraft] = useState('')
  const [agentSessionSummaryDraft, setAgentSessionSummaryDraft] = useState('')
  const [agentSessionSaving, setAgentSessionSaving] = useState(false)
  const [agentSessionArchiving, setAgentSessionArchiving] = useState(false)
  const [agentSessionArchiveConfirmed, setAgentSessionArchiveConfirmed] = useState(false)
  const [agentSessionCompressing, setAgentSessionCompressing] = useState(false)
  const [agentSessionContext, setAgentSessionContext] = useState<AiTradingAgentSessionContext | null>(null)
  const [agentSessionContextLoading, setAgentSessionContextLoading] = useState(false)
  const [agentSessionContextError, setAgentSessionContextError] = useState<string | null>(null)
  const [recentStrategySpecs, setRecentStrategySpecs] = useState<AiTradingStrategySpecRecord[]>([])
  const [recentSignalEvents, setRecentSignalEvents] = useState<AiTradingSignalEventRecord[]>([])
  const [recentBacktestResults, setRecentBacktestResults] = useState<AiTradingBacktestResultRecord[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const aiTradingGatewayRuntimeBlockers = aiTradingRuntime?.gateway?.runtime_config_blockers || []
  const aiTradingModelAdjustment = aiTradingRuntime?.model_adjustment
  const aiTradingAgentContextBudget = aiTradingRuntime?.agent_sessions?.context_budget
  const aiTradingModelAdjustmentBlockers = aiTradingModelAdjustment?.blockers || []
  const aiTradingModelAdjustmentNextActions = aiTradingModelAdjustment?.next_actions || []
  const aiTradingGatewayReady = Boolean(
    aiTradingRuntime?.gateway?.enabled &&
    aiTradingRuntime.gateway?.url_configured &&
    (aiTradingRuntime.gateway?.default_handoff_status || 'available') === 'available' &&
    aiTradingGatewayRuntimeBlockers.length === 0
  )
  const aiTradingModelAdjustmentReady = Boolean(
    aiTradingModelAdjustment
      ? aiTradingModelAdjustment.ready
      : profile?.llm_configured && ['deepseek', 'qwen'].includes(String(profile?.llm_provider || '').toLowerCase())
  )
  const aiTradingAgentContextWatchCount = (
    (aiTradingAgentContextBudget?.near_budget_count || 0) +
    (aiTradingAgentContextBudget?.redacted_context_summary_count || 0) +
    (aiTradingAgentContextBudget?.sensitive_context_summary_count || 0)
  )
  const aiTradingAgentContextOverBudgetCount = aiTradingAgentContextBudget?.over_budget_count || 0
  const aiTradingAgentContextBudgetLabel = (): string => {
    if (!aiTradingAgentContextBudget) {
      return t('hyperAi.aiTradingContextBudgetUnavailable', 'ctx pending')
    }
    if (aiTradingAgentContextOverBudgetCount > 0) {
      return t('hyperAi.aiTradingContextBudgetOver', 'ctx over {{count}}', {
        count: aiTradingAgentContextOverBudgetCount,
      })
    }
    if (aiTradingAgentContextWatchCount > 0) {
      return t('hyperAi.aiTradingContextBudgetWatch', 'ctx watch {{count}}', {
        count: aiTradingAgentContextWatchCount,
      })
    }
    return t('hyperAi.aiTradingContextBudgetMax', 'ctx max {{used}} / {{limit}}', {
      used: aiTradingAgentContextBudget.max_context_summary_chars || 0,
      limit: aiTradingAgentContextBudget.context_summary_max_chars || 2000,
    })
  }
  const aiTradingAgentContextBudgetTone = aiTradingAgentContextOverBudgetCount > 0
    ? 'text-red-600'
    : aiTradingAgentContextWatchCount > 0
      ? 'text-yellow-600'
      : 'text-muted-foreground'
  const aiTradingAgentSessions = useMemo(
    () => [...recentAgentSessions, ...archivedAgentSessions],
    [recentAgentSessions, archivedAgentSessions]
  )
  const aiTradingAgentSessionById = useMemo(
    () => new Map(aiTradingAgentSessions.map(session => [session.id, session])),
    [aiTradingAgentSessions]
  )
  const selectedAiTradingAgentSession = aiTradingAgentSessions.find(
    session => session.id === selectedAiTradingAgentSessionId
  )
  const selectedAiTradingAgentSessionArchived = selectedAiTradingAgentSession?.status === 'archived'
  const isAiTradingAgentSessionArchived = (
    agentSessionId?: string | null,
    agentSessionStatus?: string | null
  ): boolean => {
    if (agentSessionStatus === 'archived') {
      return true
    }
    const cleanAgentSessionId = String(agentSessionId || '').trim()
    if (!cleanAgentSessionId) {
      return false
    }
    return aiTradingAgentSessionById.get(cleanAgentSessionId)?.status === 'archived'
  }
  const isStrategyRecordActionBlockedByArchivedSession = (
    record?: AiTradingStrategySpecRecord | null
  ): boolean => Boolean(
    record?.agent_session?.id &&
    isAiTradingAgentSessionArchived(record.agent_session.id, record.agent_session.status)
  )
  const aiTradingStrategyRecordById = useMemo(() => {
    const records = [...recentStrategySpecs]
    if (strategyDraftRecord) {
      records.push(strategyDraftRecord)
    }
    return new Map(records.map(record => [record.id, record]))
  }, [recentStrategySpecs, strategyDraftRecord])
  const backtestMetricValue = (metrics: Record<string, unknown> | undefined, keys: string[]): number | null => {
    if (!metrics) {
      return null
    }
    for (const key of keys) {
      const raw = metrics[key]
      if (raw === null || raw === undefined || raw === '') {
        continue
      }
      const parsed = Number(raw)
      if (Number.isFinite(parsed)) {
        return parsed
      }
    }
    return null
  }
  const hasBacktestQualityMetrics = (metrics: Record<string, unknown> | undefined): boolean => {
    const tradeCount = backtestMetricValue(metrics, ['trade_count', 'total_trades', 'num_trades', 'trades'])
    const maxDrawdown = backtestMetricValue(metrics, ['max_drawdown', 'maximum_drawdown', 'max_drawdown_pct', 'max_dd'])
    const performanceMetric = backtestMetricValue(metrics, [
      'total_return',
      'return_pct',
      'pnl_pct',
      'net_pnl',
      'sharpe',
      'sortino',
      'win_rate',
      'profit_factor',
    ])
    return Boolean(tradeCount && tradeCount > 0 && maxDrawdown !== null && performanceMetric !== null)
  }
  const isBacktestReady = (backtest?: AiTradingBacktestSummary): boolean => (
    Boolean(
      backtest?.accepted_for_handoff &&
      ['passed', 'accepted', 'approved'].includes(String(backtest.status || '').toLowerCase()) &&
      backtest.backtest_id &&
      hasBacktestQualityMetrics(backtest.metrics)
    )
  )
  const backtestStatusLabel = (backtest?: AiTradingBacktestSummary): string => {
    if (isBacktestReady(backtest)) {
      return 'backtest ready'
    }
    return backtest?.status || 'backtest needed'
  }
  const backtestStatusClassName = (backtest?: AiTradingBacktestSummary): string => (
    isBacktestReady(backtest)
      ? 'bg-green-500/10 text-green-600'
      : 'bg-yellow-500/10 text-yellow-600'
  )
  const formatBacktestMetric = (metrics: Record<string, unknown> | undefined, keys: string[], suffix = ''): string => {
    const value = backtestMetricValue(metrics, keys)
    if (value === null) {
      return '-'
    }
    return `${Number(value.toFixed(2))}${suffix}`
  }
  const backtestResultLine = (record: AiTradingBacktestResultRecord): string => {
    const trades = formatBacktestMetric(record.metrics, ['trade_count', 'total_trades'])
    const ret = formatBacktestMetric(record.metrics, ['total_return', 'return_pct'], '%')
    const drawdown = formatBacktestMetric(record.metrics, ['max_drawdown', 'max_drawdown_percent'], '%')
    return `${trades} trades · ${ret} return · ${drawdown} dd`
  }
  const formatEvidenceValue = (value: unknown, suffix = ''): string => {
    const parsed = Number(value)
    if (!Number.isFinite(parsed)) {
      return '-'
    }
    return `${Number(parsed.toFixed(2))}${suffix}`
  }
  const evidenceActionCounts = (detail: AiTradingBacktestEvidenceDetail | null): Array<[string, number]> => (
    Object.entries(detail?.trigger_summary?.action_counts || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
  )
  const evidenceEquitySeries = (detail: AiTradingBacktestEvidenceDetail | null): Array<{ timestamp: number; equity: number }> => (
    (detail?.backtest_result?.equity_curve_sample || [])
      .map((point, index) => ({
        timestamp: Number(point.timestamp ?? index),
        equity: Number(point.equity),
      }))
      .filter(point => Number.isFinite(point.timestamp) && Number.isFinite(point.equity))
  )
  const evidenceEquityPath = (detail: AiTradingBacktestEvidenceDetail | null): string => {
    const series = evidenceEquitySeries(detail)
    if (series.length === 0) {
      return ''
    }
    const width = 320
    const height = 120
    const padding = 10
    const minEquity = Math.min(...series.map(point => point.equity))
    const maxEquity = Math.max(...series.map(point => point.equity))
    const span = maxEquity - minEquity || 1
    return series.map((point, index) => {
      const x = series.length === 1
        ? width / 2
        : padding + (index / (series.length - 1)) * (width - padding * 2)
      const y = height - padding - ((point.equity - minEquity) / span) * (height - padding * 2)
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    }).join(' ')
  }
  const evidenceTriggerRows = (detail: AiTradingBacktestEvidenceDetail | null): Array<Record<string, unknown>> => (
    (detail?.trigger_summary?.triggers || []).slice(0, 25)
  )
  const isSignalHandoffEligible = (event: AiTradingSignalEventRecord): boolean => (
    event.handoff_eligibility?.eligible ??
    (
      aiTradingGatewayReady &&
      event.status === 'review_candidate' &&
      event.handoff_status !== 'submitted'
    )
  )
  const setSignalHandoffEventConfirmed = (eventId: number, checked: boolean) => {
    setSignalHandoffConfirmedEventIds(prev => {
      const next = { ...prev }
      if (checked) {
        next[eventId] = true
      } else {
        delete next[eventId]
      }
      return next
    })
  }
  const formatDurationCompact = (seconds: unknown): string => {
    const value = Number(seconds)
    if (!Number.isFinite(value)) {
      return ''
    }
    if (value >= 3600) {
      return `${Math.round(value / 3600)}h`
    }
    if (value >= 60) {
      return `${Math.round(value / 60)}m`
    }
    return `${Math.max(0, Math.round(value))}s`
  }
  const signalBlockerLabel = (blocker: string, event?: AiTradingSignalEventRecord): string => {
    if (blocker === 'signal_event_stale_for_handoff') {
      const age = formatDurationCompact(event?.handoff_eligibility?.signal_age_seconds)
      const maxAge = formatDurationCompact(event?.handoff_eligibility?.max_handoff_age_seconds)
      const label = t('hyperAi.aiTradingSignalExpired', 'Signal expired')
      return age && maxAge ? `${label} (${age} > ${maxAge})` : label
    }
    const labels: Record<string, string> = {
      gateway_disabled: t('hyperAi.aiTradingGatewayDisabled', 'Gateway disabled'),
      gateway_url_not_configured: t('hyperAi.aiTradingGatewayUrlMissing', 'Gateway URL missing'),
      strategy_backtest_required_before_handoff: t('hyperAi.aiTradingBacktestRequired', 'Backtest required'),
      strategy_backtest_trade_count_required: t('hyperAi.aiTradingTradeCountRequired', 'Trade count required'),
      strategy_backtest_max_drawdown_required: t('hyperAi.aiTradingDrawdownRequired', 'Drawdown required'),
      strategy_backtest_performance_metric_required: t('hyperAi.aiTradingPerformanceMetricRequired', 'Performance metric required'),
      signal_not_eligible_for_backend_handoff: t('hyperAi.aiTradingSignalNotEligible', 'Signal not eligible'),
      signal_payload_missing: t('hyperAi.aiTradingSignalPayloadMissing', 'Signal payload missing'),
      signal_version_mismatch: t('hyperAi.aiTradingSignalVersionMismatch', 'Signal version mismatch'),
      signal_candidate_type_invalid: t('hyperAi.aiTradingSignalTypeInvalid', 'Signal type invalid'),
      signal_venue_must_be_hyperliquid: t('hyperAi.aiTradingSignalVenueInvalid', 'Venue must be Hyperliquid'),
      signal_action_not_tradeable: t('hyperAi.aiTradingSignalActionNotTradeable', 'Signal action not tradeable'),
      signal_event_action_mismatch: t('hyperAi.aiTradingSignalActionMismatch', 'Signal action mismatch'),
      signal_symbol_missing: t('hyperAi.aiTradingSignalSymbolMissing', 'Signal symbol missing'),
      signal_event_symbol_mismatch: t('hyperAi.aiTradingSignalSymbolMismatch', 'Signal symbol mismatch'),
      execution_boundary_missing: t('hyperAi.aiTradingExecutionBoundaryMissing', 'Execution boundary missing'),
      signal_missing_signal_only_boundary: t('hyperAi.aiTradingSignalOnlyBoundaryMissing', 'signal_only missing'),
      signal_missing_not_an_order_boundary: t('hyperAi.aiTradingNotAnOrderBoundaryMissing', 'not_an_order missing'),
      signal_missing_user_confirmation_boundary: t('hyperAi.aiTradingUserConfirmationBoundaryMissing', 'User confirmation missing'),
      signal_allows_direct_ai_order_placement: t('hyperAi.aiTradingDirectAiOrderBlocked', 'Direct AI order not allowed'),
      signal_missing_order_backend_only_boundary: t('hyperAi.aiTradingOrderBackendOnlyMissing', 'Order backend boundary missing'),
      production_handoff_approval_required: t('hyperAi.aiTradingProductionApprovalRequired', 'Production approval required'),
      production_gateway_mode_must_be_http_json: t('hyperAi.aiTradingProductionGatewayModeHttpRequired', 'HTTP gateway required'),
      production_gateway_url_must_be_https: t('hyperAi.aiTradingProductionGatewayHttpsRequired', 'HTTPS gateway required'),
      production_gateway_url_must_not_be_local_or_private: t('hyperAi.aiTradingProductionGatewayPublicRequired', 'Public gateway required'),
      production_gateway_url_must_not_be_placeholder: t('hyperAi.aiTradingProductionGatewayPlaceholderBlocked', 'Placeholder gateway blocked'),
      production_gateway_url_must_not_embed_credentials_or_query: t('hyperAi.aiTradingProductionGatewayUrlSecretBlocked', 'Gateway URL contains secrets'),
      production_gateway_token_required: t('hyperAi.aiTradingProductionGatewayTokenRequired', 'Gateway token required'),
      production_gateway_timeout_invalid: t('hyperAi.aiTradingProductionGatewayTimeoutInvalid', 'Gateway timeout invalid'),
      production_gateway_timeout_too_high: t('hyperAi.aiTradingProductionGatewayTimeoutTooHigh', 'Gateway timeout too high'),
      production_signal_max_handoff_age_required: t('hyperAi.aiTradingProductionMaxAgeRequired', 'Signal age gate required'),
      production_signal_max_handoff_age_too_high: t('hyperAi.aiTradingProductionMaxAgeTooHigh', 'Signal age gate too high'),
      event_status_not_review_candidate: t('hyperAi.aiTradingEventNotReviewCandidate', 'Not review candidate'),
      handoff_already_submitted: t('hyperAi.aiTradingHandoffAlreadySubmitted', 'Already submitted'),
      agent_session_archived: t('hyperAi.aiTradingAgentSessionArchivedBlocker', 'Agent session archived'),
      signal_event_created_at_missing: t('hyperAi.aiTradingSignalCreatedAtMissing', 'Signal time missing'),
    }
    return labels[blocker] || blocker.replace(/_/g, ' ')
  }
  const signalHandoffTitle = (event: AiTradingSignalEventRecord): string => {
    if (isSignalHandoffEligible(event)) {
      if (!signalHandoffConfirmedEventIds[event.id]) {
        return t('hyperAi.aiTradingSignalHandoffConfirmRequired', 'Confirm this signal handoff before submitting it to the order backend')
      }
      if (event.handoff_status === 'failed') {
        return t('hyperAi.aiTradingRetryHandoff', 'Retry handoff')
      }
      return t('hyperAi.aiTradingSubmitHandoff', 'Submit handoff')
    }
    const blockers = event.handoff_eligibility?.blockers || []
    if (blockers.length > 0) {
      return blockers.map(blocker => signalBlockerLabel(blocker, event)).join(', ')
    }
    return t('hyperAi.aiTradingGatewayDisabled', 'Gateway disabled')
  }
  const signalStatusLabel = (event: AiTradingSignalEventRecord): string => {
    if (event.status === 'submitted' || event.handoff_status === 'submitted') {
      return t('hyperAi.aiTradingStatusSubmitted', 'Submitted')
    }
    if (event.status === 'rejected' || event.handoff_status === 'rejected') {
      return t('hyperAi.aiTradingStatusRejected', 'Rejected')
    }
    if (event.handoff_status === 'failed') {
      if (isSignalHandoffEligible(event)) {
        return t('hyperAi.aiTradingStatusRetryReady', 'Retry ready')
      }
      return t('hyperAi.aiTradingStatusFailed', 'Failed')
    }
    if (isSignalHandoffEligible(event)) {
      return t('hyperAi.aiTradingStatusReady', 'Ready')
    }
    return t('hyperAi.aiTradingStatusBlocked', 'Blocked')
  }
  const signalStatusClassName = (event: AiTradingSignalEventRecord): string => {
    if (event.status === 'submitted' || event.handoff_status === 'submitted') {
      return 'bg-blue-500/10 text-blue-600'
    }
    if (event.status === 'rejected' || event.handoff_status === 'rejected') {
      return 'bg-red-500/10 text-red-600'
    }
    if (event.handoff_status === 'failed') {
      return isSignalHandoffEligible(event)
        ? 'bg-green-500/10 text-green-600'
        : 'bg-orange-500/10 text-orange-600'
    }
    if (isSignalHandoffEligible(event)) {
      return 'bg-green-500/10 text-green-600'
    }
    return 'bg-yellow-500/10 text-yellow-600'
  }
  const signalBlockerSummary = (event: AiTradingSignalEventRecord): string => {
    const blockers = event.handoff_eligibility?.blockers || []
    if (blockers.length === 0) {
      return event.handoff_status || 'not_submitted'
    }
    return signalBlockerLabel(blockers[0], event)
  }
  const gatewayRuntimeBlockerSummary = (): string => (
    aiTradingGatewayRuntimeBlockers.length > 0
      ? aiTradingGatewayRuntimeBlockers.map(blocker => signalBlockerLabel(blocker)).join(', ')
      : ''
  )
  const gatewayTargetLabel = (): string => {
    const targetKind = aiTradingRuntime?.gateway?.target_kind
    const mode = String(aiTradingRuntime?.gateway?.mode || 'http').toLowerCase()
    if (targetKind === 'local_mock') {
      return `${t('hyperAi.aiTradingGatewayTargetLocalMock', 'Local mock')} / ${mode}`
    }
    if (targetKind === 'external_order_backend') {
      return `${t('hyperAi.aiTradingGatewayTargetExternalBackend', 'External backend')} / ${mode}`
    }
    return `${t('hyperAi.aiTradingGatewayTargetNotConfigured', 'Not configured')} / ${mode}`
  }
  const modelAdjustmentBlockerLabel = (blocker: string): string => {
    const labels: Record<string, string> = {
      model_profile_not_configured: t('hyperAi.aiTradingModelProfileMissing', 'Profile missing'),
      model_profile_credential_missing: t('hyperAi.aiTradingModelCredentialMissing', 'Key missing'),
      model_profile_credential_unreadable: t('hyperAi.aiTradingModelCredentialUnreadable', 'Key unreadable'),
      model_provider_not_deepseek_or_qwen: t('hyperAi.aiTradingModelProviderUnsupported', 'DeepSeek/Qwen required'),
      model_name_missing: t('hyperAi.aiTradingModelNameMissing', 'Model missing'),
      model_base_url_missing: t('hyperAi.aiTradingModelEndpointMissing', 'Endpoint missing'),
      model_base_url_rejected_sensitive: t('hyperAi.aiTradingModelEndpointRejected', 'Endpoint rejected'),
    }
    return labels[blocker] || t('hyperAi.aiTradingModelBlocked', 'Blocked')
  }
  const modelAdjustmentBlockerSummary = (): string => (
    Array.from(new Set(aiTradingModelAdjustmentBlockers.map(modelAdjustmentBlockerLabel))).join(', ')
  )
  const modelAdjustmentNextActionSummary = (): string => (
    Array.from(new Set(aiTradingModelAdjustmentNextActions.map(action => String(action).trim()).filter(Boolean))).slice(0, 2).join(' ')
  )
  const modelAdjustmentStatusLabel = (): string => {
    if (aiTradingModelAdjustmentReady) {
      return t('hyperAi.aiTradingModelReady', 'Ready')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_profile_not_configured')) {
      return t('hyperAi.aiTradingModelProfileMissing', 'Profile missing')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_provider_not_deepseek_or_qwen')) {
      return t('hyperAi.aiTradingModelProviderUnsupported', 'DeepSeek/Qwen required')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_profile_credential_missing')) {
      return t('hyperAi.aiTradingModelCredentialMissing', 'Key missing')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_profile_credential_unreadable')) {
      return t('hyperAi.aiTradingModelCredentialUnreadable', 'Key unreadable')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_name_missing')) {
      return t('hyperAi.aiTradingModelNameMissing', 'Model missing')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_base_url_missing')) {
      return t('hyperAi.aiTradingModelEndpointMissing', 'Endpoint missing')
    }
    if (aiTradingModelAdjustmentBlockers.includes('model_base_url_rejected_sensitive')) {
      return t('hyperAi.aiTradingModelEndpointRejected', 'Endpoint rejected')
    }
    return t('hyperAi.aiTradingModelBlocked', 'Blocked')
  }
  const modelAdjustmentDetailLabel = (): string => {
    const provider = aiTradingModelAdjustment?.provider || profile?.llm_provider
    const model = aiTradingModelAdjustment?.model || profile?.llm_model
    if (provider && model) {
      return `${provider} / ${model}`
    }
    if (provider) {
      return String(provider)
    }
    return t('hyperAi.aiTradingModelNotConfigured', 'DeepSeek/Qwen profile')
  }
  const modelAdjustmentReadinessDetailLabel = (): string => {
    const identity = modelAdjustmentDetailLabel()
    const nextAction = modelAdjustmentNextActionSummary()
    if (nextAction) {
      return nextAction
    }
    const blockerSummary = modelAdjustmentBlockerSummary()
    return blockerSummary ? `${identity} / ${blockerSummary}` : identity
  }
  const modelAdjustmentUnavailableTitle = (): string => {
    const nextAction = modelAdjustmentNextActionSummary()
    if (nextAction) {
      return nextAction
    }
    const blockerSummary = modelAdjustmentBlockerSummary()
    return blockerSummary
      ? t('hyperAi.aiTradingModelAdjustmentBlockedBy', 'Model adjustment blocked: {{summary}}', {
          summary: blockerSummary,
        })
      : t('hyperAi.aiTradingModelAdjustmentUnavailable', 'Configure DeepSeek or Qwen for model adjustment')
  }
  const aiTradingValidationWarningLabel = (warning: string): string => {
    if (warning === AI_TRADING_MODEL_OUTPUT_SENSITIVE_WARNING) {
      return t('hyperAi.aiTradingModelOutputSensitiveRedacted', 'Model output redacted')
    }
    if (warning === AI_TRADING_MODEL_OUTPUT_DIRECT_ORDER_WARNING) {
      return t('hyperAi.aiTradingModelOutputDirectOrderIgnored', 'Direct order intent ignored')
    }
    return warning
  }
  const archivedSessionActionBlockerLabel = t(
    'hyperAi.aiTradingAgentSessionArchivedBlocker',
    'Agent session archived'
  )
  const archivedSessionActionTitle = t(
    'hyperAi.aiTradingAgentSessionArchivedActionBlocked',
    'Agent session archived; create a new session or select an active session before changing strategy, backtest, signal, or handoff state.'
  )
  const currentStrategyValidationWarnings = Array.from(new Set([
    ...(strategyDraftRecord?.validation?.warnings || []),
    ...(strategyDraftRecord?.spec?.validation?.warnings || []),
    ...(strategyDraft?.validation?.warnings || []),
  ].map(String)))
  const currentStrategyModelAdjustmentMetadata = asRecord(asRecord(strategyDraft?.metadata).model_adjustment)
  const currentStrategyModelOutputSafetyLabels = [
    (
      currentStrategyValidationWarnings.includes(AI_TRADING_MODEL_OUTPUT_SENSITIVE_WARNING) ||
      currentStrategyModelAdjustmentMetadata.model_output_sensitive_text_redacted === true
    )
      ? aiTradingValidationWarningLabel(AI_TRADING_MODEL_OUTPUT_SENSITIVE_WARNING)
      : null,
    (
      currentStrategyValidationWarnings.includes(AI_TRADING_MODEL_OUTPUT_DIRECT_ORDER_WARNING) ||
      currentStrategyModelAdjustmentMetadata.model_output_direct_order_intent_ignored === true
    )
      ? aiTradingValidationWarningLabel(AI_TRADING_MODEL_OUTPUT_DIRECT_ORDER_WARNING)
      : null,
  ].filter(Boolean) as string[]
  const currentStrategyBacktest = strategyDraftRecord?.spec?.backtest || strategyDraft?.backtest
  const currentStrategyBacktestReady = isBacktestReady(currentStrategyBacktest)
  const currentStrategyRecordArchivedSessionBlocked = isStrategyRecordActionBlockedByArchivedSession(strategyDraftRecord)
  const currentStrategyActionBlockedByArchivedSession = Boolean(
    currentStrategyRecordArchivedSessionBlocked ||
    (!strategyDraftRecord && selectedAiTradingAgentSessionArchived)
  )
  const currentStrategySaveBlockedByArchivedSession = Boolean(selectedAiTradingAgentSessionArchived)
  const currentStrategyAdjustBlockedByArchivedSession = currentStrategyRecordArchivedSessionBlocked
  const currentStrategyModelAdjustBlockedByArchivedSession = Boolean(
    currentStrategyRecordArchivedSessionBlocked ||
    (!strategyDraftRecord && selectedAiTradingAgentSessionArchived)
  )
  const isStrategyRecordIdActionBlockedByArchivedSession = (recordId?: number | null): boolean => {
    if (!recordId) {
      return currentStrategyActionBlockedByArchivedSession
    }
    return isStrategyRecordActionBlockedByArchivedSession(aiTradingStrategyRecordById.get(recordId))
  }
  const canBuildStrategySignalPreview = Boolean(
    strategyDraftRecord?.status === 'approved' &&
    currentStrategyBacktestReady &&
    !currentStrategyRecordArchivedSessionBlocked
  )
  const canUseAiTradingModelAdjust = Boolean(
    aiTradingModelAdjustmentReady
  )
  const strategySignalPreviewTitle = currentStrategyActionBlockedByArchivedSession
    ? archivedSessionActionTitle
    : !strategyDraftRecord
      ? t('hyperAi.aiTradingSaveBeforeSignalPreview', 'Save and approve the strategy spec before signal preview')
    : strategyDraftRecord.status !== 'approved'
      ? t('hyperAi.aiTradingApproveBeforeSignalPreview', 'Approve the strategy spec before signal preview')
      : !currentStrategyBacktestReady
        ? t('hyperAi.aiTradingBacktestBeforeSignalPreview', 'Attach or run a handoff-ready backtest before signal preview')
        : t('hyperAi.aiTradingSignalPreview', 'Signal preview')

  // Get current language
  const currentLang = i18n.language?.startsWith('zh') ? 'zh' : 'en'

  useEffect(() => {
    fetchConversations()
    fetchProviders()
    fetchProfile()
    fetchSkills()
    fetchBotConfig()
    fetchDiscordBotConfig()
    fetchNotificationConfig()
    fetchExternalTools()
    fetchTradingSymbols()
    fetchAiTradingRuntime()
    fetchAiTradingRecords()
  }, [])

  useEffect(() => {
    // Don't fetch messages while sending - it would overwrite the streaming message
    if (currentConvId && !sending) {
      fetchMessages(currentConvId)
    }
  }, [currentConvId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  useEffect(() => {
    if (selectedAiTradingAgentSessionId === AI_TRADING_NEW_AGENT_SESSION_VALUE) {
      return
    }
    if (aiTradingAgentSessions.length === 0) {
      return
    }
    const selectedStillExists = aiTradingAgentSessions.some(
      session => session.id === selectedAiTradingAgentSessionId
    )
    if (!selectedAiTradingAgentSessionId || !selectedStillExists) {
      setSelectedAiTradingAgentSessionId(recentAgentSessions[0]?.id || aiTradingAgentSessions[0].id)
    }
  }, [aiTradingAgentSessions, recentAgentSessions, selectedAiTradingAgentSessionId])

  useEffect(() => {
    if (selectedAiTradingAgentSession) {
      setAgentSessionNameDraft(selectedAiTradingAgentSession.name || '')
      setAgentSessionSummaryDraft(selectedAiTradingAgentSession.context_summary || '')
    } else if (selectedAiTradingAgentSessionId === AI_TRADING_NEW_AGENT_SESSION_VALUE) {
      setAgentSessionNameDraft('')
      setAgentSessionSummaryDraft('')
    }
    setAgentSessionArchiveConfirmed(false)
  }, [selectedAiTradingAgentSession, selectedAiTradingAgentSessionId])

  // Check for pending prompt from other pages (e.g. Factor Analysis "Ask AI")
  useEffect(() => {
    const pending = localStorage.getItem('hyper-ai-pending-prompt')
    if (pending) {
      localStorage.removeItem('hyper-ai-pending-prompt')
      setInputValue(pending)
      // Focus the textarea after a brief delay
      setTimeout(() => textareaRef.current?.focus(), 200)
    }
  }, [])

  useEffect(() => {
    const syncBacktestRoute = () => {
      setStrategyBacktestEvidencePageSpecId(parseAiTradingBacktestRouteSpecId())
      setAgentSessionDetailPageId(parseAiTradingAgentSessionRouteId())
    }
    window.addEventListener('popstate', syncBacktestRoute)
    window.addEventListener('hashchange', syncBacktestRoute)
    return () => {
      window.removeEventListener('popstate', syncBacktestRoute)
      window.removeEventListener('hashchange', syncBacktestRoute)
    }
  }, [])

  useEffect(() => {
    if (!agentSessionDetailPageId) {
      setAgentSessionDetailLoading(false)
      setAgentSessionDetailError(null)
      setAgentSessionDetailContext(null)
      return
    }

    let cancelled = false
    const loadAgentSessionDetailPage = async () => {
      setAgentSessionDetailLoading(true)
      setAgentSessionDetailError(null)
      setAgentSessionDetailContext(null)
      const fallback = 'Failed to load agent session'
      try {
        const res = await authFetchAiTradingAction(
          `/api/ai-trading/agent-sessions/${encodeURIComponent(agentSessionDetailPageId)}/context?strategy_limit=20&signal_limit=50`
        )
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          if (!cancelled) {
            setAgentSessionDetailError(formatAiTradingAgentSessionApiError(res.status, data.detail, fallback))
          }
          return
        }
        if (cancelled) {
          return
        }
        const context = data.context as AiTradingAgentSessionContext
        setAgentSessionDetailContext(context)
        setSelectedAiTradingAgentSessionId(agentSessionDetailPageId)
      } catch (e) {
        if (cancelled) {
          return
        }
        console.error('Failed to load AI Trading agent session detail page:', e)
        setAgentSessionDetailError(formatAiTradingAgentSessionApiError(0, null, fallback))
      } finally {
        if (!cancelled) {
          setAgentSessionDetailLoading(false)
        }
      }
    }

    loadAgentSessionDetailPage()
    return () => {
      cancelled = true
    }
  }, [agentSessionDetailPageId, agentSessionDetailReloadKey])

  useEffect(() => {
    if (!strategyBacktestEvidencePageSpecId) {
      setStrategyBacktestEvidencePageLoading(false)
      setStrategyBacktestEvidencePageError(null)
      return
    }

    let cancelled = false
    const loadBacktestEvidencePage = async () => {
      setStrategyBacktestEvidencePageLoading(true)
      setStrategyBacktestEvidencePageError(null)
      const fallback = 'Failed to load backtest evidence'
      try {
        const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${strategyBacktestEvidencePageSpecId}/backtest-evidence?trigger_limit=50`)
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          if (!cancelled) {
            setStrategyBacktestEvidencePageError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
          }
          return
        }
        if (cancelled) {
          return
        }
        const evidence = data.evidence || {}
        setStrategyBacktestEvidenceDetail(evidence as AiTradingBacktestEvidenceDetail)
      } catch (e) {
        if (cancelled) {
          return
        }
        console.error('Failed to load AI trading backtest evidence page:', e)
        setStrategyBacktestEvidencePageError(formatAiTradingStrategyActionApiError(0, null, fallback))
      } finally {
        if (!cancelled) {
          setStrategyBacktestEvidencePageLoading(false)
        }
      }
    }

    loadBacktestEvidencePage()
    return () => {
      cancelled = true
    }
  }, [strategyBacktestEvidencePageSpecId, strategyBacktestEvidencePageReloadKey])

  const handleBacktestEvidencePageBack = () => {
    window.history.pushState({}, '', '/app/ai-trading')
    setStrategyBacktestEvidencePageSpecId(null)
    setStrategyBacktestEvidencePageError(null)
    setStrategyBacktestEvidenceDialogOpen(false)
  }

  const handleOpenBacktestEvidencePage = (recordId?: number) => {
    const targetRecordId = recordId || strategyBacktestEvidenceDetail?.strategy_spec_id
    if (!targetRecordId) {
      return
    }
    window.history.pushState({}, '', `/app/ai-trading/backtests/${targetRecordId}`)
    setStrategyBacktestEvidencePageSpecId(targetRecordId)
    setStrategyBacktestEvidenceDialogOpen(false)
  }

  const handleAgentSessionDetailPageBack = () => {
    window.history.pushState({}, '', '/app/ai-trading')
    setAgentSessionDetailPageId(null)
    setAgentSessionDetailError(null)
  }

  const handleOpenAgentSessionDetailPage = (agentSessionId?: string) => {
    const targetSessionId = cleanAiTradingAgentSessionRouteId(agentSessionId || selectedAiTradingAgentSession?.id)
    if (!targetSessionId) {
      return
    }
    window.history.pushState({}, '', `/app/ai-trading/sessions/${encodeURIComponent(targetSessionId)}`)
    setAgentSessionDetailPageId(targetSessionId)
  }

  const handleCompressAgentSessionDetailContext = async () => {
    if (!agentSessionDetailPageId) {
      return
    }
    setAgentSessionDetailCompressing(true)
    setAgentSessionDetailError(null)
    const fallback = 'Failed to compress agent session context'
    try {
      const res = await authFetchAiTradingAction(
        `/api/ai-trading/agent-sessions/${encodeURIComponent(agentSessionDetailPageId)}/compress-context?strategy_limit=20&signal_limit=50`,
        { method: 'POST' },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setAgentSessionDetailError(formatAiTradingAgentSessionApiError(res.status, data.detail, fallback))
        return
      }
      if (data.context) {
        setAgentSessionDetailContext(data.context as AiTradingAgentSessionContext)
      }
      const summary = data.context_summary || data.agent_session?.context_summary || ''
      if (selectedAiTradingAgentSessionId === agentSessionDetailPageId) {
        setAgentSessionSummaryDraft(summary)
      }
      refreshAiTradingState()
    } catch (e) {
      console.error('Failed to compress AI Trading agent session detail context:', e)
      setAgentSessionDetailError(formatAiTradingAgentSessionApiError(0, null, fallback))
    } finally {
      setAgentSessionDetailCompressing(false)
    }
  }

  const fetchBotConfig = async () => {
    try {
      const res = await authFetch('/api/bot/config/telegram')
      const data = await res.json()
      setBotConfig(data.config || null)
    } catch (e) {
      console.error('Failed to fetch bot config:', e)
    }
  }

  const fetchDiscordBotConfig = async () => {
    try {
      const res = await authFetch('/api/bot/config/discord')
      const data = await res.json()
      setDiscordBotConfig(data.config || null)
    } catch (e) {
      console.error('Failed to fetch discord bot config:', e)
    }
  }

  const fetchNotificationConfig = async () => {
    try {
      const res = await authFetch('/api/bot/notification-config')
      const data = await res.json()
      const cfg = data.config || { ai_trader: true, program_trader: true, signal_pools: {} }
      let count = 0
      if (cfg.ai_trader) count++
      if (cfg.program_trader) count++
      count += Object.values(cfg.signal_pools as Record<string, boolean>).filter(Boolean).length
      setNotificationCount(count)
    } catch (e) {
      console.error('Failed to fetch notification config:', e)
    }
  }

  const fetchExternalTools = async () => {
    try {
      const res = await authFetch('/api/hyper-ai/tools')
      const data = await res.json()
      setExternalTools(data.tools || [])
    } catch (e) {
      console.error('Failed to fetch external tools:', e)
    }
  }

  const fetchTradingSymbols = async () => {
    setTradingSymbolsLoading(true)
    setTradingSymbolsError(null)
    const fallback = 'Failed to load trading symbols'
    try {
      const [watchlistRes, universeRes, availableRes] = await Promise.all([
        authFetch('/api/hyperliquid/symbols/watchlist'),
        authFetch('/api/ai-trading/market-universe?limit=50'),
        authFetch('/api/hyperliquid/symbols/available'),
      ])
      const responseErrors: Array<{ status: number; detail: unknown }> = []
      const readSymbolResponse = async (res: Response) => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
          responseErrors.push({ status: res.status, detail: data.detail })
          return {}
        }
        return data
      }
      const [watchlistData, universeData, availableData] = await Promise.all([
        readSymbolResponse(watchlistRes),
        readSymbolResponse(universeRes),
        readSymbolResponse(availableRes),
      ])
      const allSymbolSourcesFailed = !watchlistRes.ok && !universeRes.ok && !availableRes.ok
      if (allSymbolSourcesFailed) {
        const error = responseErrors[0] || { status: 0, detail: null }
        setTradingSymbolsError(formatAiTradingMarketUniverseApiError(error.status, error.detail, fallback))
        setTradingSymbolGroups({ crypto: [], hip3: [], all: [] })
        setTradingSymbolGroup('all')
        setTradingSymbols([])
        setTradingSymbolSource('none')
        return
      }
      const watchlist = Array.isArray(watchlistData.symbols)
        ? watchlistData.symbols
          .map(sanitizeAiTradingSymbolText)
          .filter((symbol: string | null): symbol is string => Boolean(symbol))
        : []
      const cryptoPreset = Array.isArray(universeData.presets?.crypto_top_20)
        ? universeData.presets.crypto_top_20
        : []
      const hip3Preset = Array.isArray(universeData.presets?.hip3_top_20)
        ? universeData.presets.hip3_top_20
        : []
      const marketSymbol = (entry: AiTradingMarket | string): string | undefined => (
        typeof entry === 'string'
          ? entry
          : entry.coin || entry.exchange_symbol || entry.symbol || entry.display_symbol
      )
      const cryptoSymbols = cryptoPreset
        .map(marketSymbol)
        .map(sanitizeAiTradingSymbolText)
        .filter((symbol: string | null): symbol is string => Boolean(symbol))
      const hip3Symbols = hip3Preset
        .map(marketSymbol)
        .map(sanitizeAiTradingSymbolText)
        .filter((symbol: string | null): symbol is string => Boolean(symbol))
      const universe = Array.from(new Set([...cryptoSymbols, ...hip3Symbols]))
      const available = Array.isArray(availableData.symbols)
        ? availableData.symbols.map((entry: { symbol?: string } | string) => (
            typeof entry === 'string' ? entry : entry.symbol
          ))
          .map(sanitizeAiTradingSymbolText)
          .filter((symbol: string | null): symbol is string => Boolean(symbol))
        : []

      if (watchlist.length > 0) {
        const symbols = watchlist.slice(0, 20)
        setTradingSymbolGroups({ crypto: symbols, hip3: [], all: symbols })
        setTradingSymbolGroup('all')
        setTradingSymbols(symbols)
        setTradingSymbolSource('watchlist')
      } else if (universe.length > 0) {
        const groups = {
          crypto: Array.from(new Set(cryptoSymbols)).slice(0, 20),
          hip3: Array.from(new Set(hip3Symbols)).slice(0, 20),
          all: universe.slice(0, 40),
        }
        setTradingSymbolGroups(groups)
        setTradingSymbolGroup('all')
        setTradingSymbols(groups.all)
        setTradingSymbolSource('universe')
      } else if (available.length > 0) {
        const symbols = available.slice(0, 20)
        setTradingSymbolGroups({ crypto: symbols, hip3: [], all: symbols })
        setTradingSymbolGroup('all')
        setTradingSymbols(symbols)
        setTradingSymbolSource('available')
      } else {
        setTradingSymbolGroups({ crypto: [], hip3: [], all: [] })
        setTradingSymbolGroup('all')
        setTradingSymbols([])
        setTradingSymbolSource('none')
      }
    } catch (e) {
      console.error('Failed to fetch trading symbols:', e)
      setTradingSymbolsError(formatAiTradingMarketUniverseApiError(0, null, fallback))
      setTradingSymbolGroups({ crypto: [], hip3: [], all: [] })
      setTradingSymbolGroup('all')
      setTradingSymbols([])
      setTradingSymbolSource('none')
    } finally {
      setTradingSymbolsLoading(false)
    }
  }

  const fetchAiTradingRuntime = async () => {
    try {
      const res = await authFetch('/api/ai-trading/runtime')
      if (res.ok) {
        const data = await res.json()
        setAiTradingRuntime(data)
      }
    } catch (e) {
      console.error('Failed to fetch AI Trading runtime:', e)
    }
  }

  const fetchAiTradingRecords = async () => {
    try {
      const selectedSessionForRecords = selectedAiTradingAgentSessionId &&
        selectedAiTradingAgentSessionId !== AI_TRADING_NEW_AGENT_SESSION_VALUE
          ? selectedAiTradingAgentSessionId
          : ''
      const historyLimit = selectedSessionForRecords ? 20 : 3
      const sessionFilter = selectedSessionForRecords
        ? `&agent_session_id=${encodeURIComponent(selectedSessionForRecords)}`
        : ''
      const [sessionRes, archivedSessionRes, specRes, signalRes, backtestRes] = await Promise.all([
        authFetch('/api/ai-trading/agent-sessions?limit=10'),
        authFetch('/api/ai-trading/agent-sessions?status=archived&limit=10'),
        authFetch(`/api/ai-trading/strategy-specs?limit=${historyLimit}${sessionFilter}`),
        authFetch(`/api/ai-trading/signal-events?limit=${historyLimit}${sessionFilter}`),
        authFetch('/api/ai-trading/backtest-results?status=completed&limit=3'),
      ])
      const sessionData = sessionRes.ok ? await sessionRes.json() : {}
      const archivedSessionData = archivedSessionRes.ok ? await archivedSessionRes.json() : {}
      const specData = specRes.ok ? await specRes.json() : {}
      const signalData = signalRes.ok ? await signalRes.json() : {}
      const backtestData = backtestRes.ok ? await backtestRes.json() : {}
      setRecentAgentSessions(Array.isArray(sessionData.agent_sessions) ? sessionData.agent_sessions : [])
      setArchivedAgentSessions(Array.isArray(archivedSessionData.agent_sessions) ? archivedSessionData.agent_sessions : [])
      setRecentStrategySpecs(Array.isArray(specData.specs) ? specData.specs : [])
      setRecentSignalEvents(Array.isArray(signalData.signal_events) ? signalData.signal_events : [])
      setRecentBacktestResults(Array.isArray(backtestData.backtest_results) ? backtestData.backtest_results : [])
    } catch (e) {
      console.error('Failed to fetch AI Trading records:', e)
    }
  }

  const refreshAiTradingState = () => {
    fetchAiTradingRuntime()
    fetchAiTradingRecords()
  }

  const handleLLMConfigSaved = () => {
    fetchProfile()
    refreshAiTradingState()
  }

  const fetchAiTradingAgentSessionContext = async (agentSessionId: string, loadIntoChat = false) => {
    if (!agentSessionId || agentSessionId === AI_TRADING_NEW_AGENT_SESSION_VALUE) {
      setAgentSessionContext(null)
      setAgentSessionContextError(null)
      return null
    }
    setAgentSessionContextLoading(true)
    setAgentSessionContextError(null)
    setAgentSessionContext(null)
    const fallback = 'Failed to load agent session context'
    try {
      const res = await authFetchAiTradingAction(
        `/api/ai-trading/agent-sessions/${encodeURIComponent(agentSessionId)}/context?strategy_limit=10&signal_limit=20`
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const message = formatAiTradingAgentSessionApiError(res.status, data.detail, fallback)
        setAgentSessionContextError(message)
        if (loadIntoChat) {
          setStrategyDraftError(message)
        }
        return null
      }
      const context = data.context as AiTradingAgentSessionContext
      setAgentSessionContext(context)
      if (loadIntoChat) {
        const promptContext = sanitizeAiTradingAgentSessionContextForPrompt(context)
        const prompt = currentLang === 'zh'
          ? `请基于这个 AI Trading Agent Session context packet 复核当前会话：总结策略状态、信号 handoff 状态、缺失的回测/风控约束，以及下一步应该让用户确认什么。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(promptContext, null, 2)}\n\`\`\``
          : `Review this AI Trading Agent Session context packet. Summarize strategy state, signal handoff state, missing backtest/risk constraints, and what the user should confirm next. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(promptContext, null, 2)}\n\`\`\``
        setInputValue(prompt)
        setTimeout(() => textareaRef.current?.focus(), 50)
      }
      return context
    } catch (e) {
      console.error('Failed to load AI Trading agent session context:', e)
      const message = formatAiTradingAgentSessionApiError(0, null, fallback)
      setAgentSessionContextError(message)
      if (loadIntoChat) {
        setStrategyDraftError(message)
      }
      return null
    } finally {
      setAgentSessionContextLoading(false)
    }
  }

  const handleCompressAgentSessionContext = async () => {
    if (!selectedAiTradingAgentSession) {
      return
    }
    setAgentSessionCompressing(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to compress agent session context'
    try {
      const res = await authFetchAiTradingAction(
        `/api/ai-trading/agent-sessions/${encodeURIComponent(selectedAiTradingAgentSession.id)}/compress-context?strategy_limit=10&signal_limit=20`,
        { method: 'POST' },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingAgentSessionApiError(res.status, data.detail, fallback))
        return
      }
      const summary = data.context_summary || data.agent_session?.context_summary || ''
      setAgentSessionSummaryDraft(summary)
      if (data.context) {
        setAgentSessionContext(data.context as AiTradingAgentSessionContext)
      }
      refreshAiTradingState()
    } catch (e) {
      console.error('Failed to compress AI Trading agent session context:', e)
      setStrategyDraftError(formatAiTradingAgentSessionApiError(0, null, fallback))
    } finally {
      setAgentSessionCompressing(false)
    }
  }

  useEffect(() => {
    fetchAiTradingRecords()
    if (
      selectedAiTradingAgentSessionId &&
      selectedAiTradingAgentSessionId !== AI_TRADING_NEW_AGENT_SESSION_VALUE
    ) {
      fetchAiTradingAgentSessionContext(selectedAiTradingAgentSessionId)
    } else {
      setAgentSessionContext(null)
      setAgentSessionContextError(null)
    }
  }, [selectedAiTradingAgentSessionId])

  const handleSaveAgentSession = async () => {
    setAgentSessionSaving(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to save agent session'
    try {
      const isNewSession = selectedAiTradingAgentSessionId === AI_TRADING_NEW_AGENT_SESSION_VALUE || !selectedAiTradingAgentSession
      const endpoint = isNewSession
        ? '/api/ai-trading/agent-sessions'
        : `/api/ai-trading/agent-sessions/${encodeURIComponent(selectedAiTradingAgentSession.id)}`
      const res = await authFetchAiTradingAction(endpoint, {
        method: isNewSession ? 'POST' : 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: agentSessionNameDraft || undefined,
          context_summary: agentSessionSummaryDraft || undefined,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingAgentSessionApiError(res.status, data.detail, fallback))
        return
      }
      const record = data.agent_session as AiTradingAgentSessionRecord
      if (record?.id) {
        setSelectedAiTradingAgentSessionId(record.id)
      }
      refreshAiTradingState()
    } catch (e) {
      console.error('Failed to save AI Trading agent session:', e)
      setStrategyDraftError(formatAiTradingAgentSessionApiError(0, null, fallback))
    } finally {
      setAgentSessionSaving(false)
    }
  }

  const handleArchiveAgentSession = async () => {
    if (!selectedAiTradingAgentSession) {
      return
    }
    if (!agentSessionArchiveConfirmed) {
      setStrategyDraftError(t('hyperAi.aiTradingArchiveSessionConfirmRequired', 'Confirm this agent-session archive before continuing'))
      return
    }
    setAgentSessionArchiving(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to archive agent session'
    try {
      const res = await authFetchAiTradingAction(
        `/api/ai-trading/agent-sessions/${encodeURIComponent(selectedAiTradingAgentSession.id)}`,
        { method: 'DELETE' },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingAgentSessionApiError(res.status, data.detail, fallback))
        return
      }
      setSelectedAiTradingAgentSessionId(AI_TRADING_NEW_AGENT_SESSION_VALUE)
      setAgentSessionArchiveConfirmed(false)
      refreshAiTradingState()
    } catch (e) {
      console.error('Failed to archive AI Trading agent session:', e)
      setStrategyDraftError(formatAiTradingAgentSessionApiError(0, null, fallback))
    } finally {
      setAgentSessionArchiving(false)
    }
  }

  const handleTradingSymbolGroupChange = (group: AiTradingSymbolGroupKey) => {
    setTradingSymbolGroup(group)
    setTradingSymbols(tradingSymbolGroups[group])
  }

  const handleTradingSymbolPrompt = (symbol: string) => {
    const safeSymbol = sanitizeAiTradingSymbolText(symbol)
    if (!safeSymbol) {
      setTradingSymbolsError(formatAiTradingMarketUniverseApiError(0, 'symbols_unavailable', 'Trading symbol is unavailable'))
      return
    }
    const prompt = currentLang === 'zh'
      ? `请作为 Hyperliquid AI Trading Agent，针对 ${safeSymbol} 做一版可执行前的策略分析：先检查该标的的数据可用性、当前市场状态、入场/出场逻辑、仓位和杠杆约束、最大亏损限制、是否需要止盈止损或替代风控；如果策略不满足风控，请明确给出 HOLD。先给出方案和需要我确认的约束，不要直接下单。`
      : `Act as a Hyperliquid AI Trading Agent for ${safeSymbol}. Before execution, check data availability, current market state, entry/exit logic, position and leverage constraints, max-loss limits, and whether take-profit/stop-loss or alternative risk controls are required. If risk constraints are not met, return HOLD. Provide the plan and constraints for my confirmation first; do not place an order directly.`
    setInputValue(prompt)
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  const handleStrategySpecDraft = async (symbol: string) => {
    const safeSymbol = sanitizeAiTradingSymbolText(symbol)
    if (!safeSymbol) {
      setStrategyDraftError(formatAiTradingMarketUniverseApiError(0, 'symbols_unavailable', 'Trading symbol is unavailable'))
      return
    }
    setStrategyDraftLoadingSymbol(safeSymbol)
    setStrategyDraftError(null)
    const fallback = 'Failed to draft strategy spec'
    try {
      const strategyText = currentLang === 'zh'
        ? `为 ${safeSymbol} 设计一版 15m 到 1h 的 Hyperliquid 趋势/突破策略，必须包含止损、止盈、最大亏损、杠杆限制；如果条件不完整则输出 HOLD。`
        : `Design a 15m to 1h Hyperliquid trend/breakout strategy for ${safeSymbol}. Include stop-loss, take-profit, max loss, and leverage constraints; return HOLD if conditions are incomplete.`
      const res = await authFetchAiTradingAction('/api/ai-trading/strategy-spec/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: safeSymbol,
          strategy_text: strategyText,
          timeframe: '15m',
          risk_profile: 'balanced',
          max_loss_pct: 1,
          max_leverage: 3,
          require_stop_loss: true,
          require_take_profit: true,
          model_provider: profile?.llm_provider || undefined,
          model_name: profile?.llm_model || undefined,
          model_source: profile?.llm_provider ? 'hyper_ai_profile' : undefined,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }

      const spec = data.spec as AiTradingStrategySpec
      setStrategyDraft(spec)
      setStrategyDraftRecord(null)
      const reviewPrompt = currentLang === 'zh'
        ? `请审核下面这份 AI Trading Strategy Spec：先指出缺失的约束、是否需要补充止盈止损、是否满足实盘前的风控；如果不满足，请给出 HOLD 和需要我确认的问题。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)}\n\`\`\``
        : `Review this AI Trading Strategy Spec. Identify missing constraints, whether stop-loss/take-profit need refinement, and whether the spec passes pre-live risk checks. If it does not pass, return HOLD and ask for the required confirmations. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)}\n\`\`\``
      setInputValue(reviewPrompt)
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to draft AI trading strategy spec:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyDraftLoadingSymbol(null)
    }
  }

  const persistStrategyDraft = async (): Promise<AiTradingStrategySpecRecord | null> => {
    if (!strategyDraft) {
      return null
    }
    if (currentStrategySaveBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return null
    }
    setStrategyDraftSaving(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to save strategy spec'
    try {
      const savePayload: Record<string, unknown> = {
        name: `${strategyDraft.symbol || 'AI'} ${strategyDraft.timeframe || '15m'} Review`,
        source: 'hyper_ai_panel',
        spec: strategyDraft,
      }
      if (
        selectedAiTradingAgentSession &&
        selectedAiTradingAgentSessionId !== AI_TRADING_NEW_AGENT_SESSION_VALUE
      ) {
        savePayload.agent_session_id = selectedAiTradingAgentSession.id
        savePayload.agent_session_name = selectedAiTradingAgentSession.name || selectedAiTradingAgentSession.id
        if (selectedAiTradingAgentSession.context_summary) {
          savePayload.agent_context_summary = selectedAiTradingAgentSession.context_summary
        }
      }
      const res = await authFetchAiTradingAction('/api/ai-trading/strategy-specs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(savePayload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return null
      }
      const record = data.spec_record as AiTradingStrategySpecRecord
      setStrategyDraftRecord(record)
      if (record.agent_session?.id) {
        setSelectedAiTradingAgentSessionId(record.agent_session.id)
      }
      if (record.spec) {
        setStrategyDraft(record.spec)
      }
      refreshAiTradingState()
      return record
    } catch (e) {
      console.error('Failed to save AI trading strategy spec:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
      return null
    } finally {
      setStrategyDraftSaving(false)
    }
  }

  const handleSaveStrategyDraft = async () => {
    await persistStrategyDraft()
  }

  const handleApproveStrategyDraft = async () => {
    if (currentStrategyActionBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    setStrategyDraftApproving(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to approve strategy spec'
    try {
      const record = strategyDraftRecord || (await persistStrategyDraft())
      if (!record) {
        return
      }
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${record.id}/approve`, {
        method: 'POST',
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const approved = data.spec_record as AiTradingStrategySpecRecord
      setStrategyDraftRecord(approved)
      if (approved.spec) {
        setStrategyDraft(approved.spec)
      }
      refreshAiTradingState()
    } catch (e) {
      console.error('Failed to approve AI trading strategy spec:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyDraftApproving(false)
    }
  }

  const handleAdjustStrategyDraft = async () => {
    if (!strategyDraft) {
      return
    }
    const instruction = strategyAdjustInstruction.trim()
    if (!instruction) {
      setStrategyDraftError(t('hyperAi.aiTradingAdjustInstructionRequired', 'Enter a strategy adjustment first'))
      return
    }
    if (currentStrategyAdjustBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }

    setStrategyAdjusting(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to adjust strategy spec'
    try {
      const isPersisted = Boolean(strategyDraftRecord?.id)
      const res = await authFetchAiTradingAction(
        isPersisted
          ? `/api/ai-trading/strategy-specs/${strategyDraftRecord?.id}/adjust`
          : '/api/ai-trading/strategy-spec/adjust',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isPersisted
              ? { instruction, source: 'hyper_ai_panel' }
              : { spec: strategyDraft, instruction, source: 'hyper_ai_panel' }
          ),
        }
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }

      const record = data.spec_record as AiTradingStrategySpecRecord | undefined
      const spec = (record?.spec || data.spec) as AiTradingStrategySpec
      if (record) {
        setStrategyDraftRecord(record)
      }
      setStrategyDraft(spec)
      setStrategyAdjustInstruction('')
      setStrategyBacktestEvidenceDetail(null)
      refreshAiTradingState()

      const reviewPrompt = currentLang === 'zh'
        ? `请审核这份已按自然语言调整后的 AI Trading Strategy Spec：重点检查旧回测是否已失效、是否需要重新回测/重新审批、止盈止损和风险约束是否足够。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)}\n\`\`\``
        : `Review this adjusted AI Trading Strategy Spec. Check whether prior backtest evidence was invalidated, whether re-approval/re-backtest is required, and whether stop-loss/take-profit and risk constraints are sufficient. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)}\n\`\`\``
      setInputValue(reviewPrompt)
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to adjust AI trading strategy spec:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyAdjusting(false)
    }
  }

  const handleModelAdjustStrategyDraft = async () => {
    if (!strategyDraft) {
      return
    }
    const instruction = strategyAdjustInstruction.trim()
    if (!instruction) {
      setStrategyDraftError(t('hyperAi.aiTradingAdjustInstructionRequired', 'Enter a strategy adjustment first'))
      return
    }
    if (currentStrategyModelAdjustBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }

    setStrategyModelAdjusting(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to adjust strategy spec with model'
    try {
      const isPersisted = Boolean(strategyDraftRecord?.id)
      const selectedSessionContextPayload = (
        !isPersisted &&
        selectedAiTradingAgentSession &&
        selectedAiTradingAgentSessionId !== AI_TRADING_NEW_AGENT_SESSION_VALUE
      )
        ? {
            agent_session_id: selectedAiTradingAgentSession.id,
            agent_session_name: selectedAiTradingAgentSession.name || undefined,
            agent_context_summary: agentSessionSummaryDraft || selectedAiTradingAgentSession.context_summary || undefined,
          }
        : {}
      const res = await authFetchAiTradingAction(
        isPersisted
          ? `/api/ai-trading/strategy-specs/${strategyDraftRecord?.id}/model-adjust`
          : '/api/ai-trading/strategy-spec/model-adjust',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isPersisted
              ? { instruction, source: 'hyper_ai_panel_model' }
              : {
                  spec: strategyDraft,
                  instruction,
                  source: 'hyper_ai_panel_model',
                  ...selectedSessionContextPayload,
                }
          ),
        }
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }

      const record = data.spec_record as AiTradingStrategySpecRecord | undefined
      const spec = (record?.spec || data.spec) as AiTradingStrategySpec
      if (record) {
        setStrategyDraftRecord(record)
      }
      setStrategyDraft(spec)
      setStrategyAdjustInstruction('')
      setStrategyBacktestEvidenceDetail(null)
      refreshAiTradingState()

      const modelAdjustmentMetadata = asRecord(asRecord(spec.metadata).model_adjustment)
      const modelOutputSafetyWarnings = (spec.validation?.warnings || [])
        .map(String)
        .filter(warning => AI_TRADING_MODEL_OUTPUT_SAFETY_WARNINGS.includes(warning))
      const reviewPacket = {
        model_context: data.model_context,
        model_suggestion: data.model_suggestion,
        model_output_safety: {
          sensitive_text_redacted: modelAdjustmentMetadata.model_output_sensitive_text_redacted === true,
          direct_order_intent_ignored: modelAdjustmentMetadata.model_output_direct_order_intent_ignored === true,
          validation_warnings: modelOutputSafetyWarnings,
        },
        adjusted_spec: spec,
      }
      const reviewPrompt = currentLang === 'zh'
        ? `请审核 DeepSeek/Qwen 调整后的 AI Trading Strategy Spec：确认模型建议没有绕过 signal-only 边界、旧回测是否已失效、是否需要重新审批和重新回测。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(reviewPacket), null, 2)}\n\`\`\``
        : `Review this DeepSeek/Qwen adjusted AI Trading Strategy Spec. Confirm the model suggestion did not bypass signal-only boundaries, whether prior backtest evidence was invalidated, and whether re-approval/re-backtest is required. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(reviewPacket), null, 2)}\n\`\`\``
      setInputValue(reviewPrompt)
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to adjust AI trading strategy spec with model:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyModelAdjusting(false)
    }
  }

  const handleAttachBacktestSummary = async (
    recordId?: number,
    inlineRecord?: AiTradingStrategySpecRecord
  ) => {
    setStrategyDraftError(null)
    if (!recordId && currentStrategyActionBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    if (inlineRecord) {
      setStrategyDraftRecord(inlineRecord)
      if (inlineRecord.spec) {
        setStrategyDraft(inlineRecord.spec)
      }
    }
    let targetRecordId = recordId
    if (!targetRecordId) {
      const record = strategyDraftRecord || (await persistStrategyDraft())
      if (!record) {
        return
      }
      targetRecordId = record.id
    }
    if (isStrategyRecordIdActionBlockedByArchivedSession(targetRecordId)) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }

    const backtestId = strategyBacktestSummaryId.trim()
    if (!backtestId) {
      setStrategyDraftError(t('hyperAi.aiTradingBacktestIdRequired', 'Enter a backtest ID before attaching evidence'))
      return
    }
    const metricsText = strategyBacktestSummaryMetricsText.trim()
    if (!metricsText) {
      setStrategyDraftError(t('hyperAi.aiTradingBacktestMetricsRequired', 'Enter metrics JSON before attaching evidence'))
      return
    }

    let metrics: Record<string, unknown>
    try {
      const parsed = JSON.parse(metricsText)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setStrategyDraftError(t('hyperAi.aiTradingBacktestMetricsObjectRequired', 'Metrics JSON must be an object'))
        return
      }
      metrics = parsed as Record<string, unknown>
    } catch {
      setStrategyDraftError(t('hyperAi.aiTradingInvalidBacktestMetricsJson', 'Invalid metrics JSON'))
      return
    }

    setStrategyBacktestLoadingId(targetRecordId)
    setStrategyBacktestLoadingSource('summary')
    const fallback = 'Failed to attach backtest summary'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${targetRecordId}/backtest-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backtest_id: backtestId,
          status: 'passed',
          accepted_for_handoff: true,
          metrics,
          source: 'hyper_ai_panel_external_summary',
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const record = data.spec_record as AiTradingStrategySpecRecord
      setStrategyDraftRecord(record)
      if (record.spec) {
        setStrategyDraft(record.spec)
      }
      setStrategyBacktestSummaryId('')
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Strategy Spec #${record.id} 的回测摘要：确认 backtest id、metrics、是否足以允许后续 signal handoff；不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(record.spec?.backtest || {}), null, 2)}\n\`\`\``
        : `Review the backtest summary attached to AI Trading Strategy Spec #${record.id}. Confirm the backtest id, metrics, and whether it is sufficient for later signal handoff. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(record.spec?.backtest || {}), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to attach AI trading backtest summary:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyBacktestLoadingId(null)
      setStrategyBacktestLoadingSource(null)
    }
  }

  const handleAttachProgramBacktestResult = async (
    recordId?: number,
    providedBacktestResultId?: number,
    inlineRecord?: AiTradingStrategySpecRecord
  ) => {
    setStrategyDraftError(null)
    if (!recordId && currentStrategyActionBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    if (inlineRecord) {
      setStrategyDraftRecord(inlineRecord)
      if (inlineRecord.spec) {
        setStrategyDraft(inlineRecord.spec)
      }
    }
    let targetRecordId = recordId
    if (!targetRecordId) {
      const record = strategyDraftRecord || (await persistStrategyDraft())
      if (!record) {
        setStrategyDraftError('Save or draft a strategy spec before attaching a Program Backtest result')
        return
      }
      targetRecordId = record.id
    }
    if (isStrategyRecordIdActionBlockedByArchivedSession(targetRecordId)) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }

    let backtestResultId = providedBacktestResultId
    if (backtestResultId == null) {
      const backtestResultIdText = strategyProgramBacktestResultId.trim()
      if (!backtestResultIdText) {
        setStrategyDraftError(t('hyperAi.aiTradingProgramBacktestResultIdRequired', 'Enter a Program Backtest result ID before attaching evidence'))
        return
      }
      backtestResultId = Number(backtestResultIdText)
    }
    if (!Number.isInteger(backtestResultId) || backtestResultId <= 0) {
      setStrategyDraftError('Program Backtest result ID must be a positive integer')
      return
    }

    setStrategyBacktestLoadingId(targetRecordId)
    setStrategyBacktestLoadingSource('program')
    const fallback = 'Failed to attach Program Backtest result'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${targetRecordId}/backtest-result`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backtest_result_id: backtestResultId,
          accepted_for_handoff: true,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const record = data.spec_record as AiTradingStrategySpecRecord
      setStrategyDraftRecord(record)
      if (record.spec) {
        setStrategyDraft(record.spec)
      }
      if (providedBacktestResultId == null) {
        setStrategyProgramBacktestResultId('')
      }
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Strategy Spec #${record.id} 绑定的 Program BacktestResult #${backtestResultId}：确认这是当前用户自己的回测、metrics 是否满足 handoff gate、是否仍然只作为 signal evidence 而不是订单。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(record.spec?.backtest || {}), null, 2)}\n\`\`\``
        : `Review the Program BacktestResult #${backtestResultId} attached to AI Trading Strategy Spec #${record.id}. Confirm it belongs to the current user, whether metrics satisfy the handoff gate, and that it remains signal evidence rather than an order. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(record.spec?.backtest || {}), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to attach AI trading Program Backtest result:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyBacktestLoadingId(null)
      setStrategyBacktestLoadingSource(null)
    }
  }

  const handleAttachLatestProgramBacktestResult = async (recordId?: number) => {
    setStrategyDraftError(null)
    if (!recordId && currentStrategyActionBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    let targetRecordId = recordId
    if (!targetRecordId) {
      const record = strategyDraftRecord || (await persistStrategyDraft())
      if (!record) {
        setStrategyDraftError('Save or draft a strategy spec before attaching Program Backtest evidence')
        return
      }
      targetRecordId = record.id
    }
    if (isStrategyRecordIdActionBlockedByArchivedSession(targetRecordId)) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }

    setStrategyBacktestLoadingId(targetRecordId)
    setStrategyBacktestLoadingSource('latest')
    const fallback = 'Failed to attach latest Program Backtest result'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${targetRecordId}/backtest-result/latest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accepted_for_handoff: true }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const record = data.spec_record as AiTradingStrategySpecRecord
      setStrategyDraftRecord(record)
      if (record.spec) {
        setStrategyDraft(record.spec)
      }
      const backtest = record.spec?.backtest || {}
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Strategy Spec #${record.id} 自动绑定的最新同标的 Program Backtest evidence：确认 metrics 是否满足 handoff gate、标的是否匹配、是否仍然只是 signal evidence。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(backtest), null, 2)}\n\`\`\``
        : `Review the latest symbol-matching Program Backtest evidence attached to AI Trading Strategy Spec #${record.id}. Confirm metrics satisfy the handoff gate, the symbol matches, and it remains signal evidence rather than an order. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(backtest), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to attach latest AI trading Program Backtest result:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyBacktestLoadingId(null)
      setStrategyBacktestLoadingSource(null)
    }
  }

  const requestStrategyBacktestPreflight = async (recordId: number): Promise<AiTradingBacktestPreflight> => {
    const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${recordId}/backtest-preflight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(AI_TRADING_BACKTEST_DEFAULTS),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(formatAiTradingStrategyActionApiError(res.status, data.detail, 'Failed to build backtest preflight'))
    }
    return data.preflight || {}
  }

  const resolveStrategyRecordIdForBacktest = async (
    recordId: number | undefined,
    errorMessage: string
  ): Promise<number | null> => {
    if (recordId) {
      return recordId
    }
    const record = strategyDraftRecord || (await persistStrategyDraft())
    if (!record) {
      setStrategyDraftError(errorMessage)
      return null
    }
    return record.id
  }

  const handleStrategyBacktestPreflight = async (recordId?: number) => {
    setStrategyDraftError(null)
    if (!recordId && currentStrategyActionBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    const targetRecordId = await resolveStrategyRecordIdForBacktest(
      recordId,
      'Save or draft a strategy spec before building a backtest preflight'
    )
    if (!targetRecordId) {
      return
    }
    if (isStrategyRecordIdActionBlockedByArchivedSession(targetRecordId)) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }

    setStrategyBacktestLoadingId(targetRecordId)
    setStrategyBacktestLoadingSource('preflight')
    const fallback = 'Failed to build backtest preflight'
    try {
      const preflight = await requestStrategyBacktestPreflight(targetRecordId)
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Strategy Spec #${targetRecordId} 的 Program Backtest preflight：确认 recommended binding 是否属于当前用户、symbol 是否匹配、default_request 是否可以作为下一步回测请求；这一步不执行回测、不下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(preflight), null, 2)}\n\`\`\``
        : `Review the Program Backtest preflight for AI Trading Strategy Spec #${targetRecordId}. Confirm the recommended binding belongs to the current user, the symbol matches, and the default_request is suitable for the next backtest step. This does not run a backtest or place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(preflight), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to build AI trading backtest preflight:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyBacktestLoadingId(null)
      setStrategyBacktestLoadingSource(null)
    }
  }

  const handleRunStrategyProgramBacktest = async (recordId?: number) => {
    setStrategyDraftError(null)
    if (!recordId && currentStrategyActionBlockedByArchivedSession) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    const targetRecordId = await resolveStrategyRecordIdForBacktest(
      recordId,
      'Save or draft a strategy spec before running a Program Backtest'
    )
    if (!targetRecordId) {
      return
    }
    if (isStrategyRecordIdActionBlockedByArchivedSession(targetRecordId)) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    if (!strategyProgramBacktestRunConfirmed) {
      setStrategyDraftError(t('hyperAi.aiTradingRunBacktestConfirmRequired', 'Confirm this historical Program Backtest run before starting it'))
      return
    }

    setStrategyBacktestLoadingId(targetRecordId)
    setStrategyBacktestLoadingSource('run')
    setStrategyBacktestRunStatus({ specId: targetRecordId, phase: 'preflight' })
    const fallback = 'Failed to run Program Backtest'

    try {
      const preflight = await requestStrategyBacktestPreflight(targetRecordId)
      const requestBody = preflight.default_request
      if (!preflight.ready || !requestBody?.binding_id || !requestBody.start_time_ms || !requestBody.end_time_ms) {
        const blockers = preflight.blockers?.length ? preflight.blockers.join(', ') : 'missing_default_request'
        const prompt = currentLang === 'zh'
          ? `AI Trading Strategy Spec #${targetRecordId} 的 Program Backtest 预检未通过，暂不启动回测。请先修复 blockers，然后再运行；这一步没有下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(preflight), null, 2)}\n\`\`\``
          : `Program Backtest preflight for AI Trading Strategy Spec #${targetRecordId} is blocked, so the backtest was not started. Fix the blockers first; no order was placed.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(preflight), null, 2)}\n\`\`\``
        setInputValue(prompt)
        setStrategyDraftError(formatAiTradingStrategyActionApiError(0, `Backtest preflight blocked: ${blockers}`, fallback))
        return
      }

      setStrategyBacktestRunStatus({ specId: targetRecordId, phase: 'calculating' })
      const response = await authFetch('/api/programs/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      if (!response.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(response.status, null, 'Failed to start Program Backtest'))
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, 'Program Backtest stream was unavailable'))
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let backtestId: number | null = null
      let completePayload: Record<string, unknown> | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) {
            continue
          }
          const event = JSON.parse(line.slice(6)) as Record<string, unknown>
          const eventType = String(event.type || '')

          if (eventType === 'calculating') {
            setStrategyBacktestRunStatus({ specId: targetRecordId, phase: 'calculating', backtestId: backtestId || undefined })
          } else if (eventType === 'init') {
            backtestId = Number(event.backtest_id) || null
            setStrategyBacktestRunStatus({
              specId: targetRecordId,
              phase: 'running',
              total: Number(event.total_triggers) || undefined,
              backtestId: backtestId || undefined,
            })
          } else if (eventType === 'progress') {
            setStrategyBacktestRunStatus({
              specId: targetRecordId,
              phase: 'running',
              current: Number(event.current) || undefined,
              total: Number(event.total) || undefined,
              backtestId: backtestId || undefined,
            })
          } else if (eventType === 'complete') {
            completePayload = event
            backtestId = Number(event.backtest_id) || backtestId
          } else if (eventType === 'error') {
            setStrategyDraftError(formatAiTradingStrategyActionApiError(0, 'Program Backtest failed', fallback))
            return
          }
        }
      }

      if (!backtestId) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, 'Program Backtest completed without a backtest id'))
        return
      }

      setStrategyBacktestRunStatus({ specId: targetRecordId, phase: 'attaching', backtestId })
      const attachRes = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${targetRecordId}/backtest-result`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backtest_result_id: backtestId,
          accepted_for_handoff: true,
          notes: 'Created from Hyper AI AI Trading Program Backtest run. Evidence only, not an order.',
        }),
      })
      const attachData = await attachRes.json().catch(() => ({}))
      if (!attachRes.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(attachRes.status, attachData.detail, 'Failed to attach completed Program Backtest result'))
        return
      }

      const record = attachData.spec_record as AiTradingStrategySpecRecord
      setStrategyDraftRecord(record)
      if (record.spec) {
        setStrategyDraft(record.spec)
      }
      const attachedBacktest = record.spec?.backtest || { program_backtest_result_id: backtestId }
      const prompt = currentLang === 'zh'
        ? `Program Backtest #${backtestId} 已完成并绑定到 AI Trading Strategy Spec #${targetRecordId}。请复核结果质量、drawdown、trade_count、handoff gate，以及是否需要调整策略；不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket({ result: completePayload, attached_backtest: attachedBacktest }), null, 2)}\n\`\`\``
        : `Program Backtest #${backtestId} completed and was attached to AI Trading Strategy Spec #${targetRecordId}. Review result quality, drawdown, trade_count, handoff gate, and whether the strategy should be adjusted. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket({ result: completePayload, attached_backtest: attachedBacktest }), null, 2)}\n\`\`\``
      setInputValue(prompt)
      setStrategyProgramBacktestRunConfirmed(false)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to run AI trading Program Backtest:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyBacktestLoadingId(null)
      setStrategyBacktestLoadingSource(null)
      setStrategyBacktestRunStatus(null)
    }
  }

  const handleInspectStrategyBacktestEvidence = async (recordId?: number) => {
    setStrategyDraftError(null)
    const targetRecordId = await resolveStrategyRecordIdForBacktest(
      recordId,
      'Save or draft a strategy spec before inspecting backtest evidence'
    )
    if (!targetRecordId) {
      return
    }

    setStrategyBacktestLoadingId(targetRecordId)
    setStrategyBacktestLoadingSource('evidence')
    const fallback = 'Failed to load backtest evidence'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${targetRecordId}/backtest-evidence?trigger_limit=25`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const evidence = data.evidence || {}
      setStrategyBacktestEvidenceDetail(evidence as AiTradingBacktestEvidenceDetail)
      setStrategyBacktestEvidenceDialogOpen(true)
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Strategy Spec #${targetRecordId} 绑定的 Program Backtest evidence：重点检查 metrics、equity curve sample、trigger/action 分布、quality_issues 和 handoff_ready；不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(evidence), null, 2)}\n\`\`\``
        : `Review the Program Backtest evidence attached to AI Trading Strategy Spec #${targetRecordId}. Focus on metrics, equity curve sample, trigger/action distribution, quality_issues, and handoff_ready. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(evidence), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to inspect AI trading backtest evidence:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategyBacktestLoadingId(null)
      setStrategyBacktestLoadingSource(null)
    }
  }

  const handleStrategySignalPreview = async () => {
    if (currentStrategyRecordArchivedSessionBlocked) {
      setStrategyDraftError(archivedSessionActionTitle)
      return
    }
    if (!strategyDraftRecord || strategyDraftRecord.status !== 'approved') {
      setStrategyDraftError('Approve the strategy spec before building a signal preview')
      return
    }
    if (!currentStrategyBacktestReady) {
      setStrategyDraftError('Attach or run a handoff-ready backtest before building a signal preview')
      return
    }
    setStrategySignalPreviewLoading(true)
    setStrategyDraftError(null)
    const fallback = 'Failed to build signal preview'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${strategyDraftRecord.id}/signal-events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ market_context: {} }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const signalEvent = data.signal_event
      const signalPreview = signalEvent?.signal || signalEvent
      const reviewPrompt = currentLang === 'zh'
        ? `请审核下面这份 AI Trading Signal Event #${signalEvent?.id || '-'}：确认它是否仍然只是 signal candidate、是否满足 approved strategy spec 的风控边界、是否还缺少给订单后端的字段。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(signalPreview), null, 2)}\n\`\`\``
        : `Review AI Trading Signal Event #${signalEvent?.id || '-'}. Confirm that it is still only a signal candidate, whether it satisfies the approved strategy spec risk boundary, and which fields are still missing before backend handoff. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(signalPreview), null, 2)}\n\`\`\``
      setInputValue(reviewPrompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to build AI trading signal preview:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    } finally {
      setStrategySignalPreviewLoading(false)
    }
  }

  const handleInspectStrategySpecRecord = async (recordId: number) => {
    setStrategyDraftError(null)
    const fallback = 'Failed to load strategy spec'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/strategy-specs/${recordId}`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const record = data.spec_record as AiTradingStrategySpecRecord
      const spec = record.spec || record
      const prompt = currentLang === 'zh'
        ? `请审核这份已保存的 AI Trading Strategy Spec #${record.id}，重点检查风控、止盈止损、执行边界和需要补充的问题。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)}\n\`\`\``
        : `Review saved AI Trading Strategy Spec #${record.id}. Check risk, take-profit/stop-loss, execution boundaries, and missing questions. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)}\n\`\`\``
      setInputValue(prompt)
      setStrategyDraftRecord(record)
      if (record.spec) {
        setStrategyDraft(record.spec)
      }
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to load AI trading strategy spec:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    }
  }

  const handleInspectSignalEventRecord = async (eventId: number) => {
    setStrategyDraftError(null)
    const fallback = 'Failed to load signal event'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/signal-events/${eventId}`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingStrategyActionApiError(res.status, data.detail, fallback))
        return
      }
      const event = data.signal_event as AiTradingSignalEventRecord
      const signal = event.signal || event
      const prompt = currentLang === 'zh'
        ? `请审核这份 AI Trading Signal Event #${event.id}，确认它是否仍然只是候选信号、handoff 状态是否正确、是否缺少订单后端字段。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(signal), null, 2)}\n\`\`\``
        : `Review AI Trading Signal Event #${event.id}. Confirm it is still only a candidate signal, whether handoff status is correct, and what order-backend fields are missing. Do not place an order.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(signal), null, 2)}\n\`\`\``
      setInputValue(prompt)
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to load AI trading signal event:', e)
      setStrategyDraftError(formatAiTradingStrategyActionApiError(0, null, fallback))
    }
  }

  const handleSubmitSignalEventHandoff = async (eventId: number) => {
    if (!signalHandoffConfirmedEventIds[eventId]) {
      setStrategyDraftError(t('hyperAi.aiTradingSignalHandoffConfirmRequired', 'Confirm this signal handoff before submitting it to the order backend'))
      return
    }

    setSignalHandoffLoadingId(eventId)
    setStrategyDraftError(null)
    const fallback = 'Failed to submit signal handoff'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/signal-events/${eventId}/handoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmed_by_user: true,
          confirmation_source: 'hyper_ai_recent_signal_panel',
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingSignalActionApiError(res.status, data.detail, fallback))
        return
      }
      const event = data.signal_event as AiTradingSignalEventRecord
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Signal Event #${event.id} 的 handoff 结果：确认订单后端接收状态、handoff 状态、以及是否仍满足 signal-only 审计边界。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(event), null, 2)}\n\`\`\``
        : `Review the handoff result for AI Trading Signal Event #${event.id}. Confirm order-backend receipt status, handoff status, and whether the signal-only audit boundary still holds. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(event), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to submit AI trading signal handoff:', e)
      setStrategyDraftError(formatAiTradingSignalActionApiError(0, null, fallback))
    } finally {
      setSignalHandoffEventConfirmed(eventId, false)
      setSignalHandoffLoadingId(null)
    }
  }

  const handleInspectSignalHandoffAttempts = async (eventId: number) => {
    setSignalHandoffAttemptsLoadingId(eventId)
    setStrategyDraftError(null)
    const fallback = 'Failed to load handoff attempts'
    try {
      const res = await authFetchAiTradingAction(`/api/ai-trading/signal-events/${eventId}/handoff-attempts?limit=10`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingSignalActionApiError(res.status, data.detail, fallback))
        return
      }
      const attempts = Array.isArray(data.attempts)
        ? data.attempts as AiTradingSignalHandoffAttemptRecord[]
        : []
      const prompt = currentLang === 'zh'
        ? `请审计 AI Trading Signal Event #${eventId} 的 handoff attempts：确认是否有 blocked/failed/submitted 历史、blockers 是否合理、是否有重复提交风险，以及是否仍保持 signal-only / no-secret 边界。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket({ signal_event_id: eventId, attempts }), null, 2)}\n\`\`\``
        : `Audit the handoff attempts for AI Trading Signal Event #${eventId}. Check blocked/failed/submitted history, whether blockers are reasonable, duplicate-submission risk, and whether the signal-only/no-secret boundary still holds. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket({ signal_event_id: eventId, attempts }), null, 2)}\n\`\`\``
      setInputValue(prompt)
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to load AI trading signal handoff attempts:', e)
      setStrategyDraftError(formatAiTradingSignalActionApiError(0, null, fallback))
    } finally {
      setSignalHandoffAttemptsLoadingId(null)
    }
  }

  const handleRejectSignalEvent = async (eventId: number) => {
    setSignalRejectLoadingId(eventId)
    setStrategyDraftError(null)
    const fallback = 'Failed to reject signal event'
    try {
      const reason = currentLang === 'zh'
        ? 'User rejected this signal candidate from the Hyper AI panel before handoff.'
        : 'User rejected this signal candidate from the Hyper AI panel before handoff.'
      const res = await authFetchAiTradingAction(`/api/ai-trading/signal-events/${eventId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setStrategyDraftError(formatAiTradingSignalActionApiError(res.status, data.detail, fallback))
        return
      }
      const event = data.signal_event as AiTradingSignalEventRecord
      const prompt = currentLang === 'zh'
        ? `请复核 AI Trading Signal Event #${event.id} 的拒绝结果：确认该信号已不可 handoff、拒绝原因是否充分、是否还需要更新 strategy spec 或风险约束。不要直接下单。\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(event), null, 2)}\n\`\`\``
        : `Review the rejection result for AI Trading Signal Event #${event.id}. Confirm that the signal can no longer be handed off, whether the rejection reason is sufficient, and whether the strategy spec or risk constraints should be updated. Do not place an order directly.\n\n\`\`\`json\n${JSON.stringify(sanitizeAiTradingPromptPacket(event), null, 2)}\n\`\`\``
      setInputValue(prompt)
      refreshAiTradingState()
      setTimeout(() => textareaRef.current?.focus(), 50)
    } catch (e) {
      console.error('Failed to reject AI trading signal event:', e)
      setStrategyDraftError(formatAiTradingSignalActionApiError(0, null, fallback))
    } finally {
      setSignalRejectLoadingId(null)
    }
  }

  const fetchConversations = async () => {
    try {
      const res = await authFetch('/api/hyper-ai/conversations')
      const data = await res.json()
      setConversations(data.conversations || [])
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    }
  }

  const fetchMessages = async (convId: number) => {
    try {
      const res = await authFetch(`/api/hyper-ai/conversations/${convId}/messages`)
      const data = await res.json()
      setMessages(data.messages || [])
      setCompressionPoints(data.compression_points || [])
      setTokenUsage(data.token_usage || null)
    } catch (e) {
      console.error('Failed to fetch messages:', e)
    }
  }

  const fetchProviders = async () => {
    try {
      const res = await authFetch('/api/hyper-ai/providers')
      const data = await res.json()
      setProviders(data.providers || [])
    } catch (e) {
      console.error('Failed to fetch providers:', e)
    }
  }

  const fetchProfile = async () => {
    try {
      const res = await authFetch('/api/hyper-ai/profile')
      const data = await res.json()
      setProfile(data)
      if (data.nickname) {
        setNickname(data.nickname)
      }
    } catch (e) {
      console.error('Failed to fetch profile:', e)
    }
  }

  const fetchSkills = async () => {
    try {
      const res = await authFetch('/api/hyper-ai/skills')
      const data = await res.json()
      setSkills(data.skills || [])
    } catch (e) {
      console.error('Failed to fetch skills:', e)
    }
  }

  const toggleSkill = async (skillName: string, enabled: boolean) => {
    setSkillsLoading(true)
    try {
      await authFetch(`/api/hyper-ai/skills/${skillName}/toggle`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      })
      setSkills(prev => prev.map(s =>
        s.name === skillName ? { ...s, enabled } : s
      ))
    } catch (e) {
      console.error('Failed to toggle skill:', e)
    } finally {
      setSkillsLoading(false)
    }
  }

  const handleSkillsEditSave = async () => {
    setSkillsLoading(true)
    try {
      for (const [name, enabled] of Object.entries(pendingSkillToggles)) {
        await authFetch(`/api/hyper-ai/skills/${name}/toggle`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled })
        })
      }
      setSkills(prev => prev.map(s =>
        pendingSkillToggles[s.name] !== undefined
          ? { ...s, enabled: pendingSkillToggles[s.name] }
          : s
      ))
    } catch (e) {
      console.error('Failed to save skill toggles:', e)
    } finally {
      setSkillsLoading(false)
      setSkillsEditMode(false)
      setPendingSkillToggles({})
    }
  }

  const handleSkillsEditCancel = () => {
    setSkillsEditMode(false)
    setPendingSkillToggles({})
  }

  const handleNewConversation = () => {
    // Lazy creation: just clear current state, don't create in DB yet
    setCurrentConvId(null)
    setMessages([])
    setCompressionPoints([])
    setTokenUsage(null)
    setActiveSkill(null)
  }

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return

    const userMessage = inputValue.trim()
    setInputValue('')
    setSending(true)
    setStreamingContent('')

    // Add user message and placeholder assistant message
    const tempAssistantId = Date.now()
    setMessages(prev => [
      ...prev,
      { role: 'user', content: userMessage },
      {
        role: 'assistant',
        content: '',
        isStreaming: true,
        statusText: t('hyperAi.connecting', 'Connecting...'),
        toolCalls: []
      }
    ])

    try {
      const res = await authFetch('/api/hyper-ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: currentConvId,
          lang: currentLang
        })
      })

      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const detail = data?.detail
        const message = typeof detail === 'string'
          ? detail
          : detail?.message || t('hyperAi.sendFailed', 'Failed to send message')
        throw new Error(message)
      }

      if (data.status === 'already_running') {
        setMessages(prev => prev.slice(0, -2))
        setInputValue(userMessage)
        setSending(false)
        if (data.conversation_id) {
          setCurrentConvId(data.conversation_id)
          fetchMessages(data.conversation_id)
        }
        return
      }

      if (data.task_id) {
        // Poll for streaming response
        pollTaskResponse(data.task_id, data.conversation_id)
        if (!currentConvId) {
          setCurrentConvId(data.conversation_id)
        }
      } else {
        throw new Error(t('hyperAi.missingTask', 'No AI task was created'))
      }
    } catch (e) {
      console.error('Failed to send message:', e)
      // Remove temporary user + assistant messages because the backend did not
      // accept this message.
      setMessages(prev => prev.slice(0, -2))
      setInputValue(userMessage)
      setSending(false)
    }
  }

  const handleToolConfirmation = async (taskId: string, confirmationId: string, confirmed: boolean) => {
    const nextStatus = confirmed ? 'confirmed' : 'cancelled'
    setMessages(prev => prev.map(message => ({
      ...message,
      toolCalls: message.toolCalls?.map(entry =>
        entry.type === 'confirmation_required' && entry.confirmationId === confirmationId
          ? { ...entry, status: nextStatus }
          : entry
      )
    })))

    try {
      const res = await authFetch('/api/hyper-ai/confirm-tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          confirmation_id: confirmationId,
          confirmed,
        }),
      })
      if (!res.ok) {
        throw new Error(`Confirmation failed: ${res.status}`)
      }
    } catch (e) {
      console.error('Failed to submit tool confirmation:', e)
      setMessages(prev => prev.map(message => ({
        ...message,
        toolCalls: message.toolCalls?.map(entry =>
          entry.type === 'confirmation_required' && entry.confirmationId === confirmationId
            ? { ...entry, status: 'failed' }
            : entry
        )
      })))
    }
  }

  const pollTaskResponse = async (taskId: string, convId: number) => {
    let content = ''
    let reasoning = ''
    let toolCalls: ToolCallEntry[] = []
    let doneToolCallsLog: ToolCallLogEntry[] | null = null
    let doneReasoningSnapshot: string | null = null
    let isInterrupted = false
    let interruptedRound = 0

    // Update currentConvId immediately if not set
    if (!currentConvId && convId) {
      setCurrentConvId(convId)
    }

    try {
      const pollResult = await pollAiStream(taskId, {
        interval: 300,
        onChunk: (chunk) => {
          const eventType = chunk.event_type
          const data = chunk.data

          if (eventType === 'content' && data.text) {
            content += data.text
            setStreamingContent(content)
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? { ...m, content, statusText: '' }
                : m
            ))
          } else if (eventType === 'reasoning' && data.content) {
            reasoning += data.content
            const reasoningText = data.content as string
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? {
                    ...m,
                    statusText: `Thinking: ${reasoningText.slice(0, 80)}...`,
                    toolCalls: [...(m.toolCalls || []), { type: 'reasoning', content: reasoningText }],
                  }
                : m
            ))
          } else if (eventType === 'tool_call' && data.name) {
            toolCalls.push({ type: 'tool_call', name: data.name, args: data.args || {} })
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? {
                    ...m,
                    statusText: `${t('hyperAi.calling', 'Calling')} ${data.name}...`,
                    toolCalls: [...(m.toolCalls || []), { type: 'tool_call', name: data.name, args: data.args }]
                  }
                : m
            ))
          } else if (eventType === 'tool_result' && data.name) {
            toolCalls.push({ type: 'tool_result', name: data.name, result: data.result })
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? {
                    ...m,
                    statusText: '',
                    toolCalls: [...(m.toolCalls || []), { type: 'tool_result', name: data.name, result: data.result }]
                  }
                : m
            ))
          } else if (eventType === 'skill_loaded' && data.skill_name) {
            setActiveSkill(data.skill_name as string)
          } else if (eventType === 'subagent_progress') {
            const agent = data.subagent || 'Agent'
            let statusMsg = ''
            const progressEntry: any = { type: 'subagent_progress', subagent: agent, step: data.step }

            if (data.step === 'reasoning') {
              statusMsg = `${agent}: ${t('hyperAi.subagentProcessing', 'processing')}...`
              progressEntry.content = data.content || ''
            } else if (data.step === 'tool_call') {
              statusMsg = `${agent}: → ${data.tool || ''}`
              progressEntry.tool = data.tool || ''
            } else if (data.step === 'tool_result') {
              statusMsg = `${agent}: ← ${data.tool || ''}`
              progressEntry.tool = data.tool || ''
            } else if (data.step === 'tool_round') {
              const roundInfo = data.round && data.max_rounds ? ` ${data.round}/${data.max_rounds}` : (data.round ? ` ${data.round}` : '')
              statusMsg = `${agent}: ${t('hyperAi.subagentRound', 'round')}${roundInfo}...`
              progressEntry.round = data.round
              progressEntry.max_rounds = data.max_rounds
            } else {
              statusMsg = `${agent}: ${t('hyperAi.subagentProcessing', 'processing')}...`
            }

            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? { ...m, statusText: statusMsg, toolCalls: [...(m.toolCalls || []), progressEntry] }
                : m
            ))
          } else if (eventType === 'retry') {
            const attempt = data.attempt || 2
            const maxRetries = data.max_retries || 3
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? { ...m, statusText: `${t('hyperAi.retrying', 'Retrying')} (${attempt}/${maxRetries})...` }
                : m
            ))
          } else if (eventType === 'confirmation_required') {
            const confirmationEntry: ToolCallEntry = {
              type: 'confirmation_required',
              taskId,
              confirmationId: data.confirmation_id,
              name: data.tool_name,
              args: data.args || {},
              description: data.description || '',
              status: 'pending',
            }
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? {
                    ...m,
                    statusText: t('hyperAi.confirmationRequired', 'Confirmation required'),
                    toolCalls: [...(m.toolCalls || []), confirmationEntry],
                  }
                : m
            ))
            // Force scroll after DOM renders the confirmation card
            setTimeout(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
            }, 100)
          } else if (eventType === 'tool_error') {
            const errorEntry: ToolCallEntry = {
              type: 'tool_error',
              name: data.name,
              message: data.message || data.code || '',
              severity: data.severity || data.status,
            }
            setMessages(prev => prev.map((m, idx) =>
              idx === prev.length - 1 && m.isStreaming
                ? {
                    ...m,
                    statusText: data.message || t('hyperAi.toolWarning', 'Tool warning'),
                    toolCalls: [...(m.toolCalls || []), errorEntry],
                  }
                : m
            ))
          } else if (eventType === 'interrupted') {
            isInterrupted = true
            interruptedRound = data.round || 0
            if (data.conversation_id) {
              setCurrentConvId(data.conversation_id)
            }
          } else if (eventType === 'error') {
            console.error('Stream error:', data.message)
          } else if (eventType === 'done') {
            if (data.content) content = data.content
            if (data.conversation_id) setCurrentConvId(data.conversation_id)
            if (data.token_usage) setTokenUsage(data.token_usage)
            if (data.compression_points) setCompressionPoints(data.compression_points)
            if (data.tool_calls_log) doneToolCallsLog = data.tool_calls_log
            if (data.reasoning_snapshot) doneReasoningSnapshot = data.reasoning_snapshot
          }
        },
        onTaskLost: () => {
          // Task buffer expired — reload conversation to get final result
          if (convId) {
            fetchMessages(convId)
          }
        },
      })

      if (pollResult.status === 'lost') {
        setSending(false)
        return
      }

      // Finalize message - prefer backend done event data, fallback to streaming conversion
      const localToolCallsLog = toolCalls.filter(tc => tc.type === 'tool_call' || tc.type === 'tool_result')
        .reduce((acc: ToolCallLogEntry[], tc) => {
          if (tc.type === 'tool_call' && tc.name) {
            acc.push({ tool: tc.name, args: tc.args || {}, result: '' })
          } else if (tc.type === 'tool_result' && tc.name && acc.length > 0) {
            // Find matching tool call and add result
            const lastCall = acc[acc.length - 1]
            if (lastCall.tool === tc.name) {
              lastCall.result = tc.result || ''
            }
          }
          return acc
        }, [])
      const finalToolCallsLog = doneToolCallsLog || (localToolCallsLog.length > 0 ? localToolCallsLog : null)
      const finalReasoning = doneReasoningSnapshot || reasoning || undefined

      setMessages(prev => prev.map((m, idx) =>
        idx === prev.length - 1 && m.isStreaming
          ? {
              ...m,
              content: content || m.content,
              reasoning_snapshot: finalReasoning,
              tool_calls_log: finalToolCallsLog ? JSON.stringify(finalToolCallsLog) : undefined,
              isStreaming: false,
              statusText: undefined,
              toolCalls: undefined,
              isInterrupted,
              interruptedRound: isInterrupted ? interruptedRound : undefined,
              is_complete: !isInterrupted
            }
          : m
      ))
      setStreamingContent('')
      setSending(false)
      fetchConversations()
    } catch (e) {
      console.error('Polling error:', e)
      setMessages(prev => prev.map((m, idx) =>
        idx === prev.length - 1 && m.isStreaming
          ? { ...m, isStreaming: false, content: content || t('hyperAi.connectionLost', 'Connection lost') }
          : m
      ))
      setSending(false)
    }
  }

  const handleContinue = () => {
    setInputValue(t('hyperAi.continueMessage', 'Please continue'))
    setTimeout(() => handleSend(), 100)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const pageEvidence = strategyBacktestEvidenceDetail?.strategy_spec_id === strategyBacktestEvidencePageSpecId
    ? strategyBacktestEvidenceDetail
    : null
  const pageActionCounts = Object.entries(pageEvidence?.trigger_summary?.action_counts || {})
    .sort((a, b) => b[1] - a[1])
  const agentSessionDetail = agentSessionDetailContext?.agent_session || null
  const agentSessionDetailSpecs = Array.isArray(agentSessionDetailContext?.strategy_specs)
    ? agentSessionDetailContext.strategy_specs
    : []
  const agentSessionDetailSignals = Array.isArray(agentSessionDetailContext?.signal_events)
    ? agentSessionDetailContext.signal_events
    : []
  const agentSessionDetailAttempts = Array.isArray(agentSessionDetailContext?.handoff_attempts)
    ? agentSessionDetailContext.handoff_attempts
    : []
  const agentSessionDetailSymbols = Array.from(new Set([
    ...agentSessionDetailSpecs.map(spec => textValue(asRecord(spec).symbol, '')),
    ...agentSessionDetailSignals.map(signal => textValue(asRecord(signal).symbol, '')),
    ...agentSessionDetailAttempts.map(attempt => textValue(asRecord(attempt).symbol, '')),
  ].filter(Boolean))).slice(0, 12)
  const agentSessionDetailStrategyStatusCounts = Object.entries(
    agentSessionDetailSpecs.reduce<Record<string, number>>((counts, spec) => {
      const status = textValue(asRecord(spec).status, 'unknown')
      counts[status] = (counts[status] || 0) + 1
      return counts
    }, {})
  ).sort(([a], [b]) => a.localeCompare(b))
  const agentSessionDetailSignalStatusCounts = Object.entries(
    agentSessionDetailSignals.reduce<Record<string, number>>((counts, signal) => {
      const status = textValue(asRecord(signal).status, 'unknown')
      counts[status] = (counts[status] || 0) + 1
      return counts
    }, {})
  ).sort(([a], [b]) => a.localeCompare(b))
  const agentSessionDetailHandoffCounts = Object.entries(
    agentSessionDetailSignals.reduce<Record<string, number>>((counts, signal) => {
      const handoff = textValue(asRecord(signal).handoff_status, 'unknown')
      counts[handoff] = (counts[handoff] || 0) + 1
      return counts
    }, {})
  ).sort(([a], [b]) => a.localeCompare(b))
  const agentSessionDetailAttemptCounts = Object.entries(
    agentSessionDetailAttempts.reduce<Record<string, number>>((counts, attempt) => {
      const result = textValue(asRecord(attempt).result, 'unknown')
      counts[result] = (counts[result] || 0) + 1
      return counts
    }, {})
  ).sort(([a], [b]) => a.localeCompare(b))
  const agentSessionDetailCompression = asRecord(agentSessionDetailContext?.compression)
  const agentSessionDetailLimitRows = [
    {
      label: t('hyperAi.aiTradingSpecsShort', 'Specs'),
      returned: textValue(agentSessionDetailCompression.strategy_limit, '0'),
      requested: textValue(agentSessionDetailCompression.strategy_requested_limit),
      max: textValue(agentSessionDetailCompression.strategy_max_limit),
    },
    {
      label: t('hyperAi.aiTradingSignals', 'Signals'),
      returned: textValue(agentSessionDetailCompression.signal_limit, '0'),
      requested: textValue(agentSessionDetailCompression.signal_requested_limit),
      max: textValue(agentSessionDetailCompression.signal_max_limit),
    },
    {
      label: t('hyperAi.aiTradingAttempts', 'Attempts'),
      returned: textValue(agentSessionDetailCompression.attempt_limit, '0'),
      requested: textValue(agentSessionDetailCompression.attempt_requested_limit),
      max: textValue(agentSessionDetailCompression.attempt_max_limit),
    },
  ]
  const agentSessionDetailContextBudget = formatAiTradingContextBudget(
    agentSessionDetail,
    undefined
  )
  const selectedAiTradingAgentSessionContextBudget = formatAiTradingContextBudget(
    selectedAiTradingAgentSession,
    agentSessionSummaryDraft
  )

  if (agentSessionDetailPageId) {
    return (
      <div className="flex h-full flex-col bg-background" data-testid="ai-trading-agent-session-detail-page">
        <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={handleAgentSessionDetailPageBack}
              title={t('hyperAi.aiTradingBackToAgent', 'Back to AI Trading')}
              aria-label={t('hyperAi.aiTradingBackToAgent', 'Back to AI Trading')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <div className="flex min-w-0 items-center gap-2">
                <Bot className="h-4 w-4 shrink-0 text-primary" />
                <h2 className="truncate text-base font-semibold">
                  {t('hyperAi.aiTradingAgentSessionDetail', 'Agent session detail')}
                </h2>
                <span className="shrink-0 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  {agentSessionDetail?.status || t('hyperAi.aiTradingStatusActive', 'active')}
                </span>
              </div>
              <div className="mt-0.5 truncate text-xs text-muted-foreground">
                {agentSessionDetail?.name || agentSessionDetailPageId}
                {' · '}
                {agentSessionDetailPageId}
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5"
              onClick={handleCompressAgentSessionDetailContext}
              disabled={agentSessionDetailLoading || agentSessionDetailCompressing}
              title={t('hyperAi.aiTradingCompressSessionContext', 'Compress context')}
            >
              {agentSessionDetailCompressing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">{t('hyperAi.aiTradingCompressSessionContext', 'Compress context')}</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => setAgentSessionDetailReloadKey(value => value + 1)}
              disabled={agentSessionDetailLoading || agentSessionDetailCompressing}
              title={t('common.refresh', 'Refresh')}
              aria-label={t('common.refresh', 'Refresh')}
            >
              {agentSessionDetailLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {agentSessionDetailError && (
            <div className="mx-auto mb-4 max-w-6xl rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
              {agentSessionDetailError}
            </div>
          )}

          {agentSessionDetailLoading && !agentSessionDetailContext ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('common.loading', 'Loading...')}
            </div>
          ) : agentSessionDetailContext ? (
            <div className="mx-auto max-w-6xl space-y-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingStatus', 'Status')}</div>
                  <div className="mt-1 truncate text-lg font-semibold">
                    {agentSessionDetail?.status || 'active'}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {agentSessionDetailContext.compression?.format ? String(agentSessionDetailContext.compression.format) : 'ai_trading_agent_session_context.v1'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingSymbols', 'Symbols')}</div>
                  <div className="mt-1 truncate text-lg font-semibold">
                    {agentSessionDetailSymbols.length || 0}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {agentSessionDetailSymbols.join(', ') || '-'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingSpecsShort', 'Specs')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {agentSessionDetailSpecs.length}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {agentSessionDetailStrategyStatusCounts.map(([status, count]) => `${status}:${count}`).join(', ') || '-'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingSignals', 'Signals')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {agentSessionDetailSignals.length}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {agentSessionDetailSignalStatusCounts.map(([status, count]) => `${status}:${count}`).join(', ') || '-'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingHandoff', 'Handoff')}</div>
                  <div className="mt-1 truncate text-lg font-semibold">
                    {agentSessionDetailHandoffCounts.map(([status, count]) => `${status}:${count}`).join(', ') || '-'}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {t('hyperAi.aiTradingSignalOnly', 'Signal only')}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingAttempts', 'Attempts')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {agentSessionDetailAttempts.length}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {agentSessionDetailAttemptCounts.map(([status, count]) => `${status}:${count}`).join(', ') || '-'}
                  </div>
                </div>
              </div>

              <div className="rounded-md border bg-muted/10 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                  <Brain className="h-4 w-4 text-primary" />
                  {t('hyperAi.aiTradingAgentSessionContextLimits', 'Context limits')}
                </div>
                <div className="grid gap-2 md:grid-cols-4">
                  {agentSessionDetailLimitRows.map((row) => (
                    <div key={row.label} className="rounded border bg-background/70 px-3 py-2 text-xs">
                      <div className="text-muted-foreground">{row.label}</div>
                      <div className="mt-1 font-medium">
                        {row.returned} / {row.requested} / {row.max}
                      </div>
                      <div className="mt-0.5 text-[10px] text-muted-foreground">
                        {t('hyperAi.aiTradingReturnedRequestedMax', 'returned / requested / max')}
                      </div>
                    </div>
                  ))}
                  <div className="rounded border bg-background/70 px-3 py-2 text-xs">
                    <div className="text-muted-foreground">
                      {t('hyperAi.aiTradingSummaryChars', 'Summary chars')}
                    </div>
                    <div className="mt-1 font-medium">
                      {agentSessionDetailContextBudget}
                    </div>
                    <div className="mt-0.5 text-[10px] text-muted-foreground">
                      {t('hyperAi.aiTradingRedactedNoCredentials', 'redacted, no credentials')}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-md border bg-muted/10 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <Brain className="h-4 w-4 text-primary" />
                  {t('hyperAi.aiTradingAgentSessionSummary', 'Context summary')}
                </div>
                <div className="whitespace-pre-wrap break-words rounded bg-background/70 p-3 text-sm text-muted-foreground" data-testid="ai-trading-agent-session-detail-summary">
                  {agentSessionDetail?.context_summary || t('hyperAi.aiTradingNoContextSummary', 'No context summary yet')}
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-3">
                <div className="rounded-md border bg-muted/10 p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <FileJson className="h-4 w-4 text-primary" />
                    {t('hyperAi.aiTradingSessionSpecs', 'Session specs')}
                  </div>
                  <div className="space-y-2">
                    {agentSessionDetailSpecs.map((item) => {
                      const spec = asRecord(item)
                      const risk = asRecord(spec.risk)
                      const backtest = asRecord(spec.backtest)
                      const validationWarnings = Array.isArray(asRecord(spec.validation).warnings)
                        ? (asRecord(spec.validation).warnings as unknown[]).map(String)
                        : []
                      return (
                        <div key={`detail-spec-${textValue(spec.id)}`} className="rounded-md border bg-background/70 p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">
                                {textValue(spec.symbol)} · {textValue(spec.timeframe)}
                              </div>
                              <div className="mt-0.5 truncate text-xs text-muted-foreground">
                                #{textValue(spec.id)} · {textValue(spec.status)}
                              </div>
                            </div>
                            <span className={`shrink-0 rounded px-2 py-1 text-[11px] ${backtestStatusClassName(backtest as AiTradingBacktestSummary)}`}>
                              {backtestStatusLabel(backtest as AiTradingBacktestSummary)}
                            </span>
                          </div>
                          <div className="mt-2 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
                            <div className="rounded bg-muted/40 px-2 py-1">
                              <div className="text-[10px] uppercase text-muted-foreground">Loss</div>
                              <div className="truncate">{textValue(risk.max_loss_pct)}%</div>
                            </div>
                            <div className="rounded bg-muted/40 px-2 py-1">
                              <div className="text-[10px] uppercase text-muted-foreground">Lev</div>
                              <div className="truncate">{textValue(risk.max_leverage)}x</div>
                            </div>
                            <div className="rounded bg-muted/40 px-2 py-1">
                              <div className="text-[10px] uppercase text-muted-foreground">Notional</div>
                              <div className="truncate">${textValue(risk.position_notional_usd)}</div>
                            </div>
                            <div className="rounded bg-muted/40 px-2 py-1">
                              <div className="text-[10px] uppercase text-muted-foreground">Model</div>
                              <div className="truncate">{textValue(asRecord(spec.ai_model).provider, '-')}</div>
                            </div>
                          </div>
                          {validationWarnings.length > 0 && (
                            <div className="mt-2 truncate text-xs text-yellow-600">
                              {validationWarnings.slice(0, 3).map(aiTradingValidationWarningLabel).join(', ')}
                            </div>
                          )}
                        </div>
                      )
                    })}
                    {agentSessionDetailSpecs.length === 0 && (
                      <div className="rounded-md border bg-background/70 p-4 text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoSessionSpecs', 'No strategy specs in this session')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-md border bg-muted/10 p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <MessageCircle className="h-4 w-4 text-primary" />
                    {t('hyperAi.aiTradingSessionSignals', 'Session signals')}
                  </div>
                  <div className="space-y-2">
                    {agentSessionDetailSignals.map((item) => {
                      const signal = asRecord(item)
                      const eligibility = asRecord(signal.handoff_eligibility)
                      const blockers = Array.isArray(eligibility.blockers) ? eligibility.blockers.map(String) : []
                      return (
                        <div key={`detail-signal-${textValue(signal.id)}`} className="rounded-md border bg-background/70 p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">
                                {textValue(signal.symbol)} · {textValue(signal.action)}
                              </div>
                              <div className="mt-0.5 truncate text-xs text-muted-foreground">
                                #{textValue(signal.id)} · spec #{textValue(signal.strategy_spec_id)}
                              </div>
                            </div>
                            <span className={`shrink-0 rounded px-2 py-1 text-[11px] ${
                              textValue(signal.handoff_status) === 'submitted'
                                ? 'bg-green-500/10 text-green-600'
                                : blockers.length > 0
                                  ? 'bg-yellow-500/10 text-yellow-600'
                                  : 'bg-muted text-muted-foreground'
                            }`}>
                              {textValue(signal.status)} / {textValue(signal.handoff_status)}
                            </span>
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground">
                            {blockers.length > 0
                              ? blockers.slice(0, 4).map(blocker => signalBlockerLabel(blocker, signal as unknown as AiTradingSignalEventRecord)).join(', ')
                              : t('hyperAi.aiTradingNoHandoffBlockers', 'No handoff blockers in context')}
                          </div>
                        </div>
                      )
                    })}
                    {agentSessionDetailSignals.length === 0 && (
                      <div className="rounded-md border bg-background/70 p-4 text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoSessionSignals', 'No signal events in this session')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-md border bg-muted/10 p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    {t('hyperAi.aiTradingSessionHandoffAttempts', 'Handoff attempts')}
                  </div>
                  <div className="space-y-2">
                    {agentSessionDetailAttempts.map((item) => {
                      const attempt = asRecord(item)
                      const blockers = Array.isArray(attempt.blockers) ? attempt.blockers.map(String) : []
                      const result = textValue(attempt.result, 'unknown')
                      const resultClassName = result === 'submitted'
                        ? 'bg-green-500/10 text-green-600'
                        : result === 'failed'
                          ? 'bg-red-500/10 text-red-600'
                          : result === 'blocked'
                            ? 'bg-yellow-500/10 text-yellow-600'
                            : 'bg-muted text-muted-foreground'
                      return (
                        <div key={`detail-attempt-${textValue(attempt.id)}`} className="rounded-md border bg-background/70 p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">
                                {textValue(attempt.symbol)} · {textValue(attempt.action)}
                              </div>
                              <div className="mt-0.5 truncate text-xs text-muted-foreground">
                                #{textValue(attempt.id)} · signal #{textValue(attempt.signal_event_id)}
                              </div>
                            </div>
                            <span className={`shrink-0 rounded px-2 py-1 text-[11px] ${resultClassName}`}>
                              {result}
                            </span>
                          </div>
                          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="rounded bg-muted/40 px-2 py-1">
                              {textValue(attempt.gateway_ready) === 'true'
                                ? t('hyperAi.aiTradingGatewayReady', 'Gateway ready')
                                : t('hyperAi.aiTradingGatewayNotReady', 'Gateway not ready')}
                            </span>
                            <span className="truncate">
                              {textValue(attempt.created_at, '-')}
                            </span>
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground">
                            {blockers.length > 0
                              ? blockers.slice(0, 4).map(blocker => signalBlockerLabel(blocker)).join(', ')
                              : t('hyperAi.aiTradingNoHandoffBlockers', 'No handoff blockers in context')}
                          </div>
                        </div>
                      )
                    })}
                    {agentSessionDetailAttempts.length === 0 && (
                      <div className="rounded-md border bg-background/70 p-4 text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoSessionHandoffAttempts', 'No handoff attempts in this session')}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {t('hyperAi.aiTradingAgentSessionNotFound', 'Agent session not found')}
            </div>
          )}
        </div>
      </div>
    )
  }

  if (strategyBacktestEvidencePageSpecId) {
    return (
      <div className="flex h-full flex-col bg-background">
        <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={handleBacktestEvidencePageBack}
              title={t('hyperAi.aiTradingBackToAgent', 'Back to AI Trading')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <div className="flex min-w-0 items-center gap-2">
                <BarChart3 className="h-4 w-4 shrink-0 text-primary" />
                <h2 className="truncate text-base font-semibold">
                  {t('hyperAi.aiTradingBacktestResult', 'Backtest result')}
                </h2>
                <span className="shrink-0 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  Spec #{strategyBacktestEvidencePageSpecId}
                </span>
              </div>
              <div className="mt-0.5 truncate text-xs text-muted-foreground">
                {pageEvidence?.backtest_result?.id
                  ? `Program Backtest #${pageEvidence.backtest_result.id}`
                  : t('common.loading', 'Loading...')}
                {pageEvidence?.strategy_symbol ? ` · ${pageEvidence.strategy_symbol}` : ''}
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {pageEvidence && (
              <span className={`rounded px-2 py-1 text-xs ${
                pageEvidence.handoff_ready
                  ? 'bg-green-500/10 text-green-600'
                  : 'bg-yellow-500/10 text-yellow-600'
              }`}>
                {pageEvidence.handoff_ready
                  ? t('hyperAi.aiTradingStatusReady', 'Ready')
                  : t('hyperAi.aiTradingStatusBlocked', 'Blocked')}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => setStrategyBacktestEvidencePageReloadKey(value => value + 1)}
              disabled={strategyBacktestEvidencePageLoading}
              title={t('common.refresh', 'Refresh')}
            >
              {strategyBacktestEvidencePageLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {strategyBacktestEvidencePageError && (
            <div className="mx-auto mb-4 max-w-6xl rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
              {strategyBacktestEvidencePageError}
            </div>
          )}

          {strategyBacktestEvidencePageLoading && !pageEvidence ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t('common.loading', 'Loading...')}
            </div>
          ) : pageEvidence ? (
            <div className="mx-auto max-w-6xl space-y-4">
              <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingStatus', 'Status')}</div>
                  <div className={`mt-1 text-lg font-semibold ${
                    pageEvidence.handoff_ready ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {pageEvidence.handoff_ready
                      ? t('hyperAi.aiTradingStatusReady', 'Ready')
                      : t('hyperAi.aiTradingStatusBlocked', 'Blocked')}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {pageEvidence.backtest_result?.status || '-'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingReturn', 'Return')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {formatEvidenceValue(pageEvidence.backtest_result?.metrics?.['total_return'], '%')}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {formatEvidenceValue(pageEvidence.backtest_result?.metrics?.['net_pnl'])} PnL
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingDrawdown', 'Drawdown')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {formatEvidenceValue(pageEvidence.backtest_result?.metrics?.['max_drawdown'], '%')}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {formatEvidenceValue(pageEvidence.backtest_result?.metrics?.['profit_factor'])} PF
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingTrades', 'Trades')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {formatEvidenceValue(pageEvidence.backtest_result?.metrics?.['trade_count'])}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {formatEvidenceValue(pageEvidence.backtest_result?.metrics?.['win_rate'], '%')} win
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingSymbol', 'Symbol')}</div>
                  <div className="mt-1 truncate text-lg font-semibold">
                    {(pageEvidence.backtest_result?.symbols || []).join(', ') || pageEvidence.strategy_symbol || '-'}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {pageEvidence.backtest_result?.exchange || '-'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingTriggers', 'Triggers')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {pageEvidence.trigger_summary?.total ?? 0}
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {(pageEvidence.trigger_summary?.markers || []).length} markers
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.45fr_0.8fr]">
                <div className="rounded-md border bg-muted/10 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div className="text-sm font-medium">{t('hyperAi.aiTradingEquityCurve', 'Equity curve')}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {pageEvidence.backtest_result?.period
                        ? JSON.stringify(pageEvidence.backtest_result.period)
                        : '-'}
                    </div>
                  </div>
                  <div className="h-72 rounded bg-background/70 p-3">
                    {evidenceEquityPath(pageEvidence) ? (
                      <svg viewBox="0 0 320 120" className="h-full w-full" preserveAspectRatio="none">
                        <path d={evidenceEquityPath(pageEvidence)} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />
                        {evidenceEquitySeries(pageEvidence).map((point, index, series) => {
                          const minEquity = Math.min(...series.map(item => item.equity))
                          const maxEquity = Math.max(...series.map(item => item.equity))
                          const span = maxEquity - minEquity || 1
                          const x = series.length === 1 ? 160 : 10 + (index / (series.length - 1)) * 300
                          const y = 110 - ((point.equity - minEquity) / span) * 100
                          return <circle key={`${point.timestamp}-${index}`} cx={x} cy={y} r="2.5" className="fill-primary" />
                        })}
                      </svg>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoEquityCurve', 'No equity curve sample')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-md border bg-muted/10 p-4">
                  <div className="mb-3 text-sm font-medium">{t('hyperAi.aiTradingActionDistribution', 'Action distribution')}</div>
                  <div className="space-y-3">
                    {pageActionCounts.map(([action, count]) => {
                      const maxCount = Math.max(...pageActionCounts.map(([, value]) => value), 1)
                      return (
                        <div key={action}>
                          <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                            <span className="truncate">{action}</span>
                            <span className="text-muted-foreground">{count}</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded bg-muted">
                            <div className="h-full bg-primary" style={{ width: `${Math.max(8, (count / maxCount) * 100)}%` }} />
                          </div>
                        </div>
                      )
                    })}
                    {pageActionCounts.length === 0 && (
                      <div className="text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoTriggers', 'No triggers')}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-[0.8fr_1.45fr]">
                <div className="rounded-md border bg-muted/10 p-4">
                  <div className="mb-3 text-sm font-medium">{t('hyperAi.aiTradingQualityIssues', 'Quality issues')}</div>
                  {pageEvidence.quality_issues && pageEvidence.quality_issues.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 text-xs text-yellow-700 dark:text-yellow-300">
                      {pageEvidence.quality_issues.map(issue => (
                        <span key={issue} className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-1">
                          {issue}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">-</div>
                  )}
                </div>

                <div className="rounded-md border">
                  <div className="flex items-center justify-between border-b px-3 py-2">
                    <div className="text-sm font-medium">{t('hyperAi.aiTradingTriggerReview', 'Trigger review')}</div>
                    <div className="text-xs text-muted-foreground">
                      {evidenceTriggerRows(pageEvidence).length}/{pageEvidence.trigger_summary?.total || 0}
                    </div>
                  </div>
                  <div className="max-h-[480px] overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-background text-muted-foreground">
                        <tr className="border-b">
                          <th className="px-3 py-2 text-left font-medium">#</th>
                          <th className="px-3 py-2 text-left font-medium">{t('hyperAi.aiTradingAction', 'Action')}</th>
                          <th className="px-3 py-2 text-left font-medium">{t('hyperAi.aiTradingSymbol', 'Symbol')}</th>
                          <th className="px-3 py-2 text-right font-medium">{t('hyperAi.aiTradingEquity', 'Equity')}</th>
                          <th className="px-3 py-2 text-left font-medium">{t('hyperAi.aiTradingReason', 'Reason')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {evidenceTriggerRows(pageEvidence).map((trigger, index) => (
                          <tr key={`${trigger.id || index}`} className="border-b last:border-0">
                            <td className="px-3 py-2 text-muted-foreground">{String(trigger.trigger_index ?? index)}</td>
                            <td className="px-3 py-2">{String(trigger.decision_action || '-')}</td>
                            <td className="px-3 py-2">{String(trigger.symbol || pageEvidence.strategy_symbol || '-')}</td>
                            <td className="px-3 py-2 text-right">{formatEvidenceValue(trigger.equity_after)}</td>
                            <td className="max-w-[420px] truncate px-3 py-2 text-muted-foreground">{String(trigger.decision_reason || '-')}</td>
                          </tr>
                        ))}
                        {evidenceTriggerRows(pageEvidence).length === 0 && (
                          <tr>
                            <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                              {t('hyperAi.aiTradingNoTriggers', 'No triggers')}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {t('hyperAi.aiTradingNoBacktestEvidence', 'No backtest evidence loaded')}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Left: Conversation List */}
      <div className={`border-r flex flex-col transition-all duration-200 ${sidebarCollapsed ? 'w-0 overflow-hidden border-r-0' : 'w-64'}`}>
        <div className="p-3 flex items-center gap-2">
          <Button onClick={handleNewConversation} className="flex-1" size="sm">
            <Plus className="w-4 h-4 mr-2" />
            {t('hyperAi.newChat', 'New Chat')}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="px-2 shrink-0"
            onClick={() => setSidebarCollapsed(true)}
            title={t('hyperAi.collapseSidebar', 'Collapse sidebar')}
          >
            <PanelLeftClose className="w-4 h-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => setCurrentConvId(conv.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  conv.is_bot_conversation
                    ? 'border border-blue-500/30 bg-blue-500/5 mb-1 '
                    : ''
                }${
                  currentConvId === conv.id
                    ? 'bg-secondary text-secondary-foreground'
                    : 'hover:bg-muted text-muted-foreground'
                }`}
              >
                {conv.is_bot_conversation ? (
                  <>
                    <div className="flex items-center gap-2">
                      <BotConvIcon />
                      <span className="truncate font-medium">{conv.title}</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1.5 ml-6">
                      {botConfig?.status === 'connected' && <TelegramSmallIcon />}
                      {discordBotConfig?.status === 'connected' && <DiscordSmallIcon />}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{conv.title}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {conv.message_count} {t('hyperAi.messages', 'messages')}
                    </div>
                  </>
                )}
              </button>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Center: Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {sidebarCollapsed && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 left-2 z-10 px-2"
            onClick={() => setSidebarCollapsed(false)}
            title={t('hyperAi.expandSidebar', 'Expand sidebar')}
          >
            <PanelLeftOpen className="w-4 h-4" />
          </Button>
        )}
        {!aiTradingModelAdjustmentReady && (
          <div className="px-4 pt-4">
            <div
              className="mx-auto flex max-w-5xl flex-col gap-3 rounded-md border bg-muted/20 p-3 sm:flex-row sm:items-center"
              data-testid="ai-trading-model-config-workspace-entry"
            >
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Brain className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium">
                    {t('hyperAi.aiTradingModelSetup', 'AI Trading Model')}
                  </div>
                  <div className="mt-0.5 text-xs text-muted-foreground" title={modelAdjustmentReadinessDetailLabel()}>
                    {t(
                      'hyperAi.aiTradingConfigureLaterHint',
                      'You can use the workspace now and configure DeepSeek/Qwen API keys later here.'
                    )}{' '}
                    {modelAdjustmentReadinessDetailLabel()}
                  </div>
                </div>
              </div>
              <Button
                type="button"
                size="sm"
                className="h-8 shrink-0"
                data-testid="ai-trading-model-config-workspace-button"
                onClick={() => setShowConfigModal(true)}
              >
                {profile?.llm_configured
                  ? t('hyperAi.aiTradingUpdateApiKey', 'Update API key')
                  : t('hyperAi.aiTradingConfigureApiKey', 'Configure API key')}
              </Button>
            </div>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="flex-1 min-h-0">
            <WelcomeMessage
              nickname={nickname}
              t={t}
              onSuggestionClick={(question) => {
                setInputValue(question)
                setTimeout(() => handleSend(), 100)
              }}
            />
          </div>
        ) : (
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4 max-w-5xl mx-auto">
              {messages.map((msg, idx) => {
                // Check if this message is a compression point
                const compressionPoint = compressionPoints.find(cp => cp.message_id === msg.id)
                return (
                  <div key={idx}>
                    <MessageBubble
                      message={msg}
                      onContinue={msg.isInterrupted && !sending ? handleContinue : undefined}
                      onToolConfirmation={handleToolConfirmation}
                      t={t}
                    />
                    {compressionPoint && (
                      <div className="flex items-center gap-3 my-4 text-xs text-muted-foreground">
                        <div className="flex-1 border-t border-dashed border-muted-foreground/30" />
                        <span className="px-2 py-1 bg-muted rounded text-[10px]">
                          {t('hyperAi.compressionPoint', 'Context compressed')}
                        </span>
                        <div className="flex-1 border-t border-dashed border-muted-foreground/30" />
                      </div>
                    )}
                  </div>
                )
              })}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        )}

        {/* Input Area */}
        <div className="px-4 pb-4 pt-2">
          <div className="max-w-5xl mx-auto relative">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('hyperAi.inputPlaceholder', 'Type a message...')}
              disabled={sending}
              className="w-full min-h-[80px] max-h-[200px] rounded-xl border border-input bg-transparent px-4 py-3 pb-12 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-y"
              rows={3}
            />
            <div className="absolute bottom-3 right-3 flex items-center gap-2">
              {tokenUsage?.show_warning && (
                <p className="text-xs text-amber-500">
                  {t('hyperAi.contextWarning', 'Context remaining: {{percent}}% · Compressing soon', { percent: Math.max(0, Math.round((1 - tokenUsage.usage_ratio) * 100)) })}
                </p>
              )}
              <Button
                onClick={handleSend}
                disabled={!inputValue.trim() || sending}
                size="icon"
                className="rounded-full h-8 w-8 shrink-0"
              >
                {sending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Config Panel */}
      {showConfig && (
        <div className="w-[500px] border-l p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium flex items-center gap-1.5">
              <Settings className="w-4 h-4 shrink-0" />
              {t('hyperAi.configTitle', 'Hyper AI Config')}
            </h3>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setShowConfigModal(true)}>
              <Pencil className="w-3.5 h-3.5" />
            </Button>
          </div>

          <div
            className="rounded-md border bg-muted/20 p-2"
            data-testid="hyper-ai-main-page-model-config-entry"
          >
            <div className="flex min-w-0 items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Brain className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">
                  {t('hyperAi.aiTradingModelSetup', 'AI Trading Model')}
                </div>
                <div className="truncate text-xs text-muted-foreground" title={modelAdjustmentReadinessDetailLabel()}>
                  {modelAdjustmentReadinessDetailLabel()}
                </div>
              </div>
              <Button
                type="button"
                size="sm"
                variant={aiTradingModelAdjustmentReady ? 'outline' : 'default'}
                className="h-8 shrink-0"
                data-testid="ai-trading-model-config-main-page-button"
                onClick={() => setShowConfigModal(true)}
              >
                {profile?.llm_configured
                  ? t('hyperAi.aiTradingUpdateApiKey', 'Update API key')
                  : t('hyperAi.aiTradingConfigureApiKey', 'Configure API key')}
              </Button>
            </div>
          </div>

          {profile && (
            <div
              className="space-y-1.5 text-sm cursor-pointer hover:bg-muted/50 rounded-lg p-2 -mx-2 transition-colors"
              onClick={() => setShowConfigModal(true)}
            >
              <div className="flex items-center">
                <span className="text-muted-foreground shrink-0 w-[72px]">Provider</span>
                <span className="truncate">{profile.llm_provider || 'Not configured'}</span>
              </div>
              <div className="flex items-center">
                <span className="text-muted-foreground shrink-0 w-[72px]">Model</span>
                <span className="truncate">{profile.llm_model || '-'}</span>
              </div>
              {profile.llm_base_url && (
                <div className="flex items-center">
                  <span className="text-muted-foreground shrink-0 w-[72px]">Base URL</span>
                  <span className="truncate">{profile.llm_base_url}</span>
                </div>
              )}
            </div>
          )}

          <div className="border-t pt-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div>
                <h4 className="flex items-center gap-1.5 text-sm font-medium">
                  <Play className="h-4 w-4 shrink-0 text-primary" />
                  {t('hyperAi.aiTrading', 'AI Trading')}
                </h4>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {tradingSymbolSource === 'watchlist'
                    ? t('hyperAi.aiTradingWatchlist', 'Hyperliquid watchlist')
                    : tradingSymbolSource === 'universe'
                      ? t('hyperAi.aiTradingUniverse', 'AI Trading market universe')
                    : tradingSymbolSource === 'available'
                      ? t('hyperAi.aiTradingAvailable', 'Available Hyperliquid symbols')
                      : t('hyperAi.aiTradingNoSymbols', 'No Hyperliquid symbols loaded')}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                onClick={() => {
                  fetchTradingSymbols()
                  refreshAiTradingState()
                }}
                disabled={tradingSymbolsLoading}
                title={t('common.refresh', 'Refresh')}
              >
                {tradingSymbolsLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <SearchIcon className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>

            {tradingSymbolsError && (
              <div className="mb-2 text-xs text-red-500">{tradingSymbolsError}</div>
            )}
            {strategyDraftError && (
              <div className="mb-2 text-xs text-red-500">{strategyDraftError}</div>
            )}
            {aiTradingRuntime && (
              <div className="mb-2 grid grid-cols-2 gap-1 rounded-md border bg-muted/30 p-1.5 text-[11px] xl:grid-cols-6">
                <div className="min-w-0">
                  <div className="truncate text-muted-foreground">{t('hyperAi.aiTradingGateway', 'Gateway')}</div>
                  <div className={`truncate font-medium ${
                    aiTradingGatewayReady
                      ? 'text-green-600'
                      : 'text-yellow-600'
                  }`}>
                    {aiTradingRuntime.gateway?.default_handoff_status || 'disabled'}
                    {aiTradingRuntime.gateway?.max_handoff_age_seconds ? (
                      <span className="text-muted-foreground">
                        {' / '}
                        {formatDurationCompact(aiTradingRuntime.gateway.max_handoff_age_seconds)}
                        {' '}
                        {t('hyperAi.aiTradingMaxAge', 'max')}
                      </span>
                    ) : null}
                  </div>
                  {aiTradingGatewayRuntimeBlockers.length > 0 && (
                    <div className="truncate text-[10px] text-yellow-600" title={gatewayRuntimeBlockerSummary()}>
                      {signalBlockerLabel(aiTradingGatewayRuntimeBlockers[0])}
                    </div>
                  )}
                  {aiTradingGatewayRuntimeBlockers.length === 0 && (
                    <div className="truncate text-[10px] text-muted-foreground" title={gatewayTargetLabel()}>
                      {gatewayTargetLabel()}
                    </div>
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex min-w-0 items-center gap-1">
                    <div className="min-w-0 flex-1 truncate text-muted-foreground">{t('hyperAi.aiTradingModel', 'Model')}</div>
                    <button
                      type="button"
                      data-testid="ai-trading-model-config-button"
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      aria-label={t('hyperAi.aiTradingConfigureModel', 'Configure DeepSeek/Qwen model')}
                      title={t('hyperAi.aiTradingConfigureModel', 'Configure DeepSeek/Qwen model')}
                      onClick={() => setShowConfigModal(true)}
                    >
                      <Settings className="h-3 w-3" />
                    </button>
                  </div>
                  <div className={`truncate font-medium ${
                    aiTradingModelAdjustmentReady
                      ? 'text-green-600'
                      : 'text-yellow-600'
                  }`}>
                    {modelAdjustmentStatusLabel()}
                  </div>
                  <div className="truncate text-[10px] text-muted-foreground" title={modelAdjustmentReadinessDetailLabel()}>
                    {modelAdjustmentReadinessDetailLabel()}
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-muted-foreground">{t('hyperAi.aiTradingSessions', 'Sessions')}</div>
                  <div className="truncate font-medium text-foreground">
                    {aiTradingRuntime.agent_sessions?.total ?? recentAgentSessions.length}
                    <span className="text-muted-foreground">
                      {' '}
                      {t('hyperAi.aiTradingActive', 'active')}
                    </span>
                  </div>
                  <div className={`truncate text-[10px] ${aiTradingAgentContextBudgetTone}`} title={aiTradingAgentContextBudgetLabel()}>
                    {aiTradingAgentContextBudgetLabel()}
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-muted-foreground">{t('hyperAi.aiTradingSpecs', 'Specs')}</div>
                  <div className="truncate font-medium text-foreground">
                    {aiTradingRuntime.strategy_specs?.total ?? 0}
                    <span className="text-muted-foreground">
                      {' / '}
                      {aiTradingRuntime.strategy_specs?.backtest_evidence?.ready ?? 0}
                      {' '}
                      {t('hyperAi.aiTradingBacktestReady', 'backtest ready')}
                    </span>
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-muted-foreground">{t('hyperAi.aiTradingSignals', 'Signals')}</div>
                  <div className="truncate font-medium text-foreground">
                    {aiTradingRuntime.signal_events?.total ?? 0}
                    <span className="text-muted-foreground">
                      {' / '}
                      {aiTradingRuntime.signal_events?.handoff_eligibility?.eligible ?? 0}
                      {' '}
                      {t('hyperAi.aiTradingReady', 'ready')}
                    </span>
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="truncate text-muted-foreground">{t('hyperAi.aiTradingAttempts', 'Attempts')}</div>
                  <div className="truncate font-medium text-foreground">
                    {aiTradingRuntime.handoff_attempts?.total ?? 0}
                    <span className="text-muted-foreground">
                      {' / '}
                      {aiTradingRuntime.handoff_attempts?.by_result?.submitted ?? 0}
                      {' '}
                      {t('hyperAi.aiTradingSubmitted', 'submitted')}
                    </span>
                  </div>
                  <div className="truncate text-[10px] text-muted-foreground" title={Object.entries(aiTradingRuntime.handoff_attempts?.by_result || {}).map(([status, count]) => `${status}:${count}`).join(', ') || '-'}>
                    {Object.entries(aiTradingRuntime.handoff_attempts?.by_result || {}).map(([status, count]) => `${status}:${count}`).join(', ') || '-'}
                  </div>
                </div>
              </div>
            )}

            <div className="mb-2 rounded-md border bg-muted/20 p-2">
              <Label className="mb-1 block text-[11px] text-muted-foreground">
                {t('hyperAi.aiTradingAgentSession', 'Agent session')}
              </Label>
              <Select
                value={selectedAiTradingAgentSessionId || AI_TRADING_NEW_AGENT_SESSION_VALUE}
                onValueChange={setSelectedAiTradingAgentSessionId}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={AI_TRADING_NEW_AGENT_SESSION_VALUE}>
                    {t('hyperAi.aiTradingNewAgentSession', 'New agent session')}
                  </SelectItem>
                  {recentAgentSessions.map(session => (
                    <SelectItem key={session.id} value={session.id}>
                      {session.name || session.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="mt-2 grid grid-cols-[1fr_auto_auto] gap-1">
                <Input
                  value={agentSessionNameDraft}
                  onChange={(e) => setAgentSessionNameDraft(e.target.value)}
                  placeholder={t('hyperAi.aiTradingAgentSessionName', 'Session name')}
                  className="h-8 text-xs"
                  maxLength={120}
                />
                <button
                  type="button"
                  onClick={handleSaveAgentSession}
                  disabled={agentSessionSaving || agentSessionArchiving || selectedAiTradingAgentSession?.status === 'archived'}
                  className="flex h-8 w-8 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                  title={selectedAiTradingAgentSession ? t('hyperAi.aiTradingSaveSession', 'Save session') : t('hyperAi.aiTradingCreateSession', 'Create session')}
                  aria-label={selectedAiTradingAgentSession ? t('hyperAi.aiTradingSaveSession', 'Save session') : t('hyperAi.aiTradingCreateSession', 'Create session')}
                >
                  {agentSessionSaving ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="h-3.5 w-3.5" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleArchiveAgentSession}
                  disabled={
                    !selectedAiTradingAgentSession ||
                    selectedAiTradingAgentSession.status === 'archived' ||
                    agentSessionSaving ||
                    agentSessionArchiving ||
                    !agentSessionArchiveConfirmed
                  }
                  className="flex h-8 w-8 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-red-500/10 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                  title={
                    !agentSessionArchiveConfirmed && selectedAiTradingAgentSession?.status !== 'archived'
                      ? t('hyperAi.aiTradingArchiveSessionConfirmRequired', 'Confirm this agent-session archive before continuing')
                      : t('hyperAi.aiTradingArchiveSession', 'Archive session')
                  }
                  aria-label={t('hyperAi.aiTradingArchiveSession', 'Archive session')}
                >
                  {agentSessionArchiving ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Archive className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
              <label className="mt-2 flex items-start gap-2 rounded-md border bg-background/60 px-2 py-1.5 text-[11px] text-muted-foreground">
                <Checkbox
                  data-testid="ai-trading-agent-session-archive-confirm"
                  checked={agentSessionArchiveConfirmed}
                  onCheckedChange={(checked) => setAgentSessionArchiveConfirmed(checked === true)}
                  disabled={
                    !selectedAiTradingAgentSession ||
                    selectedAiTradingAgentSession.status === 'archived' ||
                    agentSessionSaving ||
                    agentSessionArchiving
                  }
                  className="mt-0.5 h-3.5 w-3.5"
                />
                <span>
                  {t('hyperAi.aiTradingArchiveSessionConfirmInline', 'Archive this agent session; audit records remain available.')}
                </span>
              </label>
              <div className="mt-1 flex items-center justify-between gap-2 text-[10px] text-muted-foreground">
                <span>{t('hyperAi.aiTradingAgentSessionSummary', 'Context summary')}</span>
                <span className="shrink-0 font-medium">
                  {t('hyperAi.aiTradingContextBudgetShort', 'Context')} {selectedAiTradingAgentSessionContextBudget}
                </span>
              </div>
              <Input
                value={agentSessionSummaryDraft}
                onChange={(e) => setAgentSessionSummaryDraft(e.target.value)}
                placeholder={t('hyperAi.aiTradingAgentSessionSummary', 'Context summary')}
                className="mt-1 h-8 text-xs"
                maxLength={2000}
              />
              {selectedAiTradingAgentSession && (
                <div className="mt-2 space-y-1">
                  <div className="grid grid-cols-3 gap-1 text-[11px]">
                    <div className="rounded bg-background/70 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">{t('hyperAi.aiTradingStatus', 'Status')}</div>
                      <div className="truncate font-medium text-foreground">
                        {selectedAiTradingAgentSession.status || 'active'}
                      </div>
                    </div>
                    <div className="rounded bg-background/70 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">{t('hyperAi.aiTradingSpecsShort', 'Specs')}</div>
                      <div className="font-medium text-foreground">
                        {agentSessionContext?.strategy_specs?.length ?? selectedAiTradingAgentSession.strategy_spec_count ?? 0}
                      </div>
                    </div>
                    <div className="rounded bg-background/70 px-2 py-1">
                      <div className="text-[10px] uppercase text-muted-foreground">{t('hyperAi.aiTradingSignalsShort', 'Signals')}</div>
                      <div className="font-medium text-foreground">
                        {agentSessionContext?.signal_events?.length ?? selectedAiTradingAgentSession.signal_event_count ?? 0}
                      </div>
                    </div>
                  </div>
                  <div className="truncate text-[11px] text-muted-foreground">
                    {(selectedAiTradingAgentSession.symbols || []).slice(0, 4).join(', ') || selectedAiTradingAgentSession.id}
                  </div>
                  <div className="grid grid-cols-3 gap-1">
                    <button
                      type="button"
                      onClick={() => fetchAiTradingAgentSessionContext(selectedAiTradingAgentSession.id, true)}
                      disabled={agentSessionContextLoading || agentSessionCompressing}
                      className="flex h-7 items-center justify-center gap-1.5 rounded-md border bg-background text-[11px] text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                      title={t('hyperAi.aiTradingLoadSessionContext', 'Load context')}
                      aria-label={t('hyperAi.aiTradingLoadSessionContext', 'Load context')}
                    >
                      {agentSessionContextLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Brain className="h-3.5 w-3.5" />
                      )}
                      <span>{t('hyperAi.aiTradingLoadSessionContextShort', 'Load context')}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleCompressAgentSessionContext}
                      disabled={agentSessionContextLoading || agentSessionCompressing}
                      className="flex h-7 items-center justify-center gap-1.5 rounded-md border bg-background text-[11px] text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                      title={t('hyperAi.aiTradingCompressSessionContext', 'Compress context')}
                      aria-label={t('hyperAi.aiTradingCompressSessionContext', 'Compress context')}
                    >
                      {agentSessionCompressing ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3.5 w-3.5" />
                      )}
                      <span>{t('hyperAi.aiTradingCompressSessionContextShort', 'Compress')}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenAgentSessionDetailPage(selectedAiTradingAgentSession.id)}
                      disabled={agentSessionContextLoading || agentSessionCompressing}
                      className="flex h-7 items-center justify-center gap-1.5 rounded-md border bg-background text-[11px] text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                      title={t('hyperAi.aiTradingOpenSessionDetail', 'Open session detail')}
                      aria-label={t('hyperAi.aiTradingOpenSessionDetail', 'Open session detail')}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      <span>{t('hyperAi.aiTradingOpenSessionShort', 'Detail')}</span>
                    </button>
                  </div>
                  {agentSessionContextError && (
                    <div className="truncate text-[11px] text-red-500">{agentSessionContextError}</div>
                  )}
                </div>
              )}
            </div>

            {tradingSymbolSource === 'universe' && tradingSymbolGroups.all.length > 0 && (
              <div className="mb-2 grid grid-cols-3 gap-1 rounded-md bg-muted/40 p-1 text-[11px]">
                {([
                  ['all', t('hyperAi.aiTradingAllMarkets', 'All')],
                  ['crypto', t('hyperAi.aiTradingCryptoMarkets', 'Crypto')],
                  ['hip3', t('hyperAi.aiTradingHip3Markets', 'HIP-3')],
                ] as Array<[AiTradingSymbolGroupKey, string]>).map(([group, label]) => {
                  const selected = tradingSymbolGroup === group
                  const count = tradingSymbolGroups[group].length
                  return (
                    <button
                      key={group}
                      type="button"
                      onClick={() => handleTradingSymbolGroupChange(group)}
                      disabled={count === 0}
                      className={`rounded px-1.5 py-1 font-medium transition-colors ${
                        selected
                          ? 'bg-background text-foreground shadow-sm'
                          : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'
                      } disabled:cursor-not-allowed disabled:opacity-40`}
                    >
                      <span>{label}</span>
                      <span className="ml-1 text-muted-foreground">{count}</span>
                    </button>
                  )
                })}
              </div>
            )}

            {tradingSymbols.length > 0 ? (
              <div className="flex max-h-28 flex-wrap gap-1.5 overflow-y-auto pr-1">
                {tradingSymbols.map(symbol => (
                  <div
                    key={symbol}
                    className="flex h-8 items-center overflow-hidden rounded-md border bg-background"
                  >
                    <button
                      type="button"
                      onClick={() => handleTradingSymbolPrompt(symbol)}
                      className="h-full px-2 text-xs font-medium transition-colors hover:bg-primary/10"
                      disabled={sending}
                    >
                      {symbol}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStrategySpecDraft(symbol)}
                      className="flex h-full w-7 items-center justify-center border-l text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={sending || strategyDraftLoadingSymbol !== null}
                      title={t('hyperAi.aiTradingDraftSpec', 'Draft strategy spec')}
                    >
                      {strategyDraftLoadingSymbol === symbol ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <FileJson className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                {tradingSymbolsLoading
                  ? t('common.loading', 'Loading...')
                  : t('hyperAi.aiTradingEmpty', 'Configure a Hyperliquid watchlist in Settings.')}
              </p>
            )}

            {strategyDraft && (
              <div className="mt-3 rounded-md border bg-muted/30 p-2 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5 font-medium">
                    <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-primary" />
                    <span className="truncate">
                      {strategyDraft.symbol || 'Symbol'} · {strategyDraft.timeframe || '-'}
                    </span>
                  </div>
                  <span
                    className={`shrink-0 rounded px-1.5 py-0.5 ${
                      strategyDraftRecord?.status === 'approved'
                        ? 'bg-green-500/10 text-green-600'
                        : strategyDraft.validation?.safe_to_emit_signal
                        ? 'bg-green-500/10 text-green-600'
                        : 'bg-yellow-500/10 text-yellow-600'
                    }`}
                  >
                    {strategyDraftRecord?.status || strategyDraft.validation?.status || 'draft'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-muted-foreground">
                  <span>{t('hyperAi.aiTradingBias', 'Bias')}</span>
                  <span className="truncate text-foreground">{strategyDraft.entry?.bias || '-'}</span>
                  <span>{t('hyperAi.aiTradingMaxLoss', 'Max loss')}</span>
                  <span className="truncate text-foreground">
                    {strategyDraft.risk?.max_loss_pct != null ? `${strategyDraft.risk.max_loss_pct}%` : '-'}
                  </span>
                  <span>{t('hyperAi.aiTradingLeverage', 'Leverage')}</span>
                  <span className="truncate text-foreground">
                    {strategyDraft.risk?.max_leverage != null ? `${strategyDraft.risk.max_leverage}x` : '-'}
                  </span>
                  <span>{t('hyperAi.aiTradingBoundary', 'Boundary')}</span>
                  <span className="truncate text-foreground">
                    {strategyDraft.execution?.signal_only ? 'signal only' : 'review'}
                  </span>
                  <span>{t('hyperAi.aiTradingBacktest', 'Backtest')}</span>
                  <span className={`truncate rounded px-1.5 py-0.5 ${backtestStatusClassName(strategyDraft.backtest)}`}>
                    {backtestStatusLabel(strategyDraft.backtest)}
                  </span>
                </div>
                <div className="mt-2 flex items-end gap-1.5 border-t pt-2">
                  <textarea
                    value={strategyAdjustInstruction}
                    onChange={(event) => setStrategyAdjustInstruction(event.target.value)}
                    placeholder={t('hyperAi.aiTradingAdjustPlaceholder', 'Adjust strategy, risk, TP/SL, timeframe...')}
                    className="min-h-[44px] flex-1 resize-none rounded-md border bg-background px-2 py-1.5 text-xs outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
                    disabled={strategyAdjusting || strategyModelAdjusting || strategyDraftSaving || strategyDraftApproving}
                    rows={2}
                  />
                  <button
                    type="button"
                    onClick={handleAdjustStrategyDraft}
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={
                      strategyAdjusting ||
                      strategyModelAdjusting ||
                      strategyDraftSaving ||
                      strategyDraftApproving ||
                      !strategyAdjustInstruction.trim() ||
                      currentStrategyAdjustBlockedByArchivedSession
                    }
                    title={currentStrategyAdjustBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingApplyAdjustment', 'Apply strategy adjustment')}
                  >
                    {strategyAdjusting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Pencil className="h-3.5 w-3.5" />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={handleModelAdjustStrategyDraft}
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={
                      strategyAdjusting ||
                      strategyModelAdjusting ||
                      strategyDraftSaving ||
                      strategyDraftApproving ||
                      !strategyAdjustInstruction.trim() ||
                      !canUseAiTradingModelAdjust ||
                      currentStrategyModelAdjustBlockedByArchivedSession
                    }
                    title={
                      currentStrategyModelAdjustBlockedByArchivedSession
                        ? archivedSessionActionTitle
                      : canUseAiTradingModelAdjust
                        ? t('hyperAi.aiTradingApplyModelAdjustment', 'Apply with DeepSeek/Qwen')
                        : modelAdjustmentUnavailableTitle()
                    }
                  >
                    {strategyModelAdjusting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Brain className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
                <div className="mt-2 grid gap-1.5 border-t pt-2">
                  <Input
                    data-testid="ai-trading-backtest-summary-id"
                    value={strategyBacktestSummaryId}
                    onChange={(event) => setStrategyBacktestSummaryId(event.target.value)}
                    placeholder={t('hyperAi.aiTradingBacktestIdPrompt', 'Backtest ID from the external/backtest service')}
                    className="h-8 text-xs"
                    disabled={strategyBacktestLoadingId !== null || strategyDraftSaving || strategyDraftApproving || currentStrategyActionBlockedByArchivedSession}
                  />
                  <Input
                    data-testid="ai-trading-program-backtest-result-id"
                    value={strategyProgramBacktestResultId}
                    onChange={(event) => setStrategyProgramBacktestResultId(event.target.value)}
                    placeholder={t('hyperAi.aiTradingProgramBacktestResultIdPrompt', 'Program Backtest result ID')}
                    className="h-8 text-xs"
                    inputMode="numeric"
                    disabled={strategyBacktestLoadingId !== null || strategyDraftSaving || strategyDraftApproving || currentStrategyActionBlockedByArchivedSession}
                  />
                  <textarea
                    data-testid="ai-trading-backtest-summary-metrics"
                    value={strategyBacktestSummaryMetricsText}
                    onChange={(event) => setStrategyBacktestSummaryMetricsText(event.target.value)}
                    placeholder={t('hyperAi.aiTradingBacktestMetricsPrompt', 'Metrics JSON')}
                    className="min-h-[56px] resize-none rounded-md border bg-background px-2 py-1.5 text-xs outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
                    disabled={strategyBacktestLoadingId !== null || strategyDraftSaving || strategyDraftApproving || currentStrategyActionBlockedByArchivedSession}
                    rows={2}
                  />
                  <label className="flex items-start gap-2 rounded-md border bg-background/60 px-2 py-1.5 text-[11px] text-muted-foreground">
                    <Checkbox
                      data-testid="ai-trading-program-backtest-run-confirm"
                      checked={strategyProgramBacktestRunConfirmed}
                      onCheckedChange={(checked) => setStrategyProgramBacktestRunConfirmed(checked === true)}
                      disabled={strategyBacktestLoadingId !== null || strategyDraftSaving || strategyDraftApproving || currentStrategyActionBlockedByArchivedSession}
                      className="mt-0.5 h-3.5 w-3.5"
                    />
                    <span>
                      {t('hyperAi.aiTradingRunBacktestConfirmInline', 'Run Program Backtest using historical data only; no orders will be placed.')}
                    </span>
                  </label>
                </div>
                <div className="mt-2 flex items-center justify-between gap-2 border-t pt-2">
                  <span className="min-w-0 truncate text-muted-foreground">
                    {strategyDraftRecord
                      ? `#${strategyDraftRecord.id} · ${strategyDraftRecord.status}`
                      : t('hyperAi.aiTradingUnsavedDraft', 'Unsaved draft')}
                  </span>
                  <div className="flex shrink-0 flex-wrap items-center justify-end gap-1">
                    <button
                      type="button"
                      onClick={handleSaveStrategyDraft}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || currentStrategySaveBlockedByArchivedSession}
                      title={currentStrategySaveBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingSaveDraft', 'Save draft')}
                    >
                      {strategyDraftSaving ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Save className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleApproveStrategyDraft}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-green-500/10 hover:text-green-600"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyDraftRecord?.status === 'approved' || currentStrategyActionBlockedByArchivedSession}
                      title={currentStrategyActionBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingApproveDraft', 'Approve draft')}
                    >
                      {strategyDraftApproving ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAttachBacktestSummary()}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyBacktestLoadingId !== null || currentStrategyActionBlockedByArchivedSession}
                      title={currentStrategyActionBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingAttachBacktest', 'Attach backtest summary')}
                    >
                      {strategyBacktestLoadingId === strategyDraftRecord?.id && strategyBacktestLoadingSource === 'summary' ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <BarChart3 className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAttachProgramBacktestResult(strategyDraftRecord?.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyBacktestLoadingId !== null || currentStrategyActionBlockedByArchivedSession}
                      title={currentStrategyActionBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingAttachProgramBacktest', 'Attach Program Backtest result')}
                    >
                      {strategyBacktestLoadingId === strategyDraftRecord?.id && strategyBacktestLoadingSource === 'program' ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Link2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAttachLatestProgramBacktestResult(strategyDraftRecord?.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyBacktestLoadingId !== null || currentStrategyActionBlockedByArchivedSession}
                      title={currentStrategyActionBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingAttachLatestProgramBacktest', 'Attach latest matching Program Backtest')}
                    >
                      {strategyBacktestLoadingId === strategyDraftRecord?.id && strategyBacktestLoadingSource === 'latest' ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <History className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStrategyBacktestPreflight(strategyDraftRecord?.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyBacktestLoadingId !== null || currentStrategyActionBlockedByArchivedSession}
                      title={currentStrategyActionBlockedByArchivedSession ? archivedSessionActionTitle : t('hyperAi.aiTradingBacktestPreflight', 'Build backtest preflight')}
                    >
                      {strategyBacktestLoadingId === strategyDraftRecord?.id && strategyBacktestLoadingSource === 'preflight' ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <ShieldCheck className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRunStrategyProgramBacktest(strategyDraftRecord?.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyBacktestLoadingId !== null || currentStrategyActionBlockedByArchivedSession || !strategyProgramBacktestRunConfirmed}
                      title={
                        currentStrategyActionBlockedByArchivedSession
                          ? archivedSessionActionTitle
                          : !strategyProgramBacktestRunConfirmed
                            ? t('hyperAi.aiTradingRunBacktestConfirmRequired', 'Confirm this historical Program Backtest run before starting it')
                            : t('hyperAi.aiTradingRunProgramBacktest', 'Run Program Backtest')
                      }
                    >
                      {strategyBacktestLoadingId === strategyDraftRecord?.id && strategyBacktestLoadingSource === 'run' ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleInspectStrategyBacktestEvidence(strategyDraftRecord?.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || strategyBacktestLoadingId !== null}
                      title={t('hyperAi.aiTradingInspectBacktestEvidence', 'Inspect backtest evidence')}
                    >
                      {strategyBacktestLoadingId === strategyDraftRecord?.id && strategyBacktestLoadingSource === 'evidence' ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <SearchIcon className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleStrategySignalPreview}
                      className="flex h-7 w-7 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                      disabled={strategyDraftSaving || strategyDraftApproving || strategyAdjusting || strategyModelAdjusting || strategySignalPreviewLoading || !canBuildStrategySignalPreview}
                      title={strategySignalPreviewTitle}
                    >
                      {strategySignalPreviewLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <MessageSquare className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>
                {strategyBacktestRunStatus && strategyBacktestRunStatus.specId === strategyDraftRecord?.id && (
                  <div className="mt-2 flex items-center gap-1.5 rounded bg-primary/10 px-2 py-1 text-[11px] text-primary">
                    <Loader2 className="h-3 w-3 shrink-0 animate-spin" />
                    <span className="truncate">
                      {strategyBacktestRunStatus.phase === 'running' && strategyBacktestRunStatus.current != null && strategyBacktestRunStatus.total != null
                        ? `${t('hyperAi.aiTradingBacktestRunning', 'Backtest running')} ${strategyBacktestRunStatus.current}/${strategyBacktestRunStatus.total}`
                        : t('hyperAi.aiTradingBacktestRunning', 'Backtest running')}
                      {strategyBacktestRunStatus.backtestId ? ` · #${strategyBacktestRunStatus.backtestId}` : ''}
                    </span>
                  </div>
                )}
                {strategyDraft.validation?.issues && strategyDraft.validation.issues.length > 0 && (
                  <div className="mt-2 flex items-start gap-1.5 text-yellow-600">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span className="break-words">{strategyDraft.validation.issues.slice(0, 3).join(', ')}</span>
                  </div>
                )}
                {currentStrategyModelOutputSafetyLabels.length > 0 && (
                  <div
                    data-testid="ai-trading-model-output-safety-warning"
                    className="mt-2 flex items-start gap-1.5 rounded bg-yellow-500/10 px-2 py-1 text-[11px] text-yellow-700 dark:text-yellow-300"
                  >
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span className="break-words">{currentStrategyModelOutputSafetyLabels.join(' · ')}</span>
                  </div>
                )}
                {currentStrategyActionBlockedByArchivedSession && (
                  <div className="mt-2 flex items-start gap-1.5 rounded bg-yellow-500/10 px-2 py-1 text-[11px] text-yellow-700 dark:text-yellow-300">
                    <Archive className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>{archivedSessionActionBlockerLabel}</span>
                  </div>
                )}
                {strategyDraftRecord?.status === 'approved' && !currentStrategyBacktestReady && (
                  <div className="mt-2 flex items-start gap-1.5 rounded bg-yellow-500/10 px-2 py-1 text-[11px] text-yellow-700 dark:text-yellow-300">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>{t('hyperAi.aiTradingBacktestBeforeSignalPreview', 'Attach or run a handoff-ready backtest before signal preview')}</span>
                  </div>
                )}
              </div>
            )}

            {strategyBacktestEvidenceDetail && (
              <div className="mt-3 rounded-md border bg-muted/20 p-2 text-xs">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5 font-medium">
                    <BarChart3 className="h-3.5 w-3.5 shrink-0 text-primary" />
                    <span className="truncate">
                      {t('hyperAi.aiTradingBacktestEvidence', 'Backtest evidence')} · #{strategyBacktestEvidenceDetail.backtest_result?.id || '-'}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <span className={`rounded px-1.5 py-0.5 ${
                      strategyBacktestEvidenceDetail.handoff_ready
                        ? 'bg-green-500/10 text-green-600'
                        : 'bg-yellow-500/10 text-yellow-600'
                    }`}>
                      {strategyBacktestEvidenceDetail.handoff_ready
                        ? t('hyperAi.aiTradingStatusReady', 'Ready')
                        : t('hyperAi.aiTradingStatusBlocked', 'Blocked')}
                    </span>
                    <button
                      type="button"
                      onClick={() => setStrategyBacktestEvidenceDialogOpen(true)}
                      className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                      title={t('hyperAi.aiTradingOpenBacktestEvidence', 'Open evidence details')}
                    >
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenBacktestEvidencePage(strategyBacktestEvidenceDetail.strategy_spec_id)}
                      className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                      title={t('hyperAi.aiTradingOpenBacktestEvidencePage', 'Open evidence page')}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setStrategyBacktestEvidenceDetail(null)
                        setStrategyBacktestEvidenceDialogOpen(false)
                      }}
                      className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                      title={t('common.close', 'Close')}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-1">
                  <div className="rounded bg-background/70 px-2 py-1">
                    <div className="text-[10px] uppercase text-muted-foreground">{t('hyperAi.aiTradingReturn', 'Return')}</div>
                    <div className="font-medium text-foreground">
                      {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['total_return'], '%')}
                    </div>
                  </div>
                  <div className="rounded bg-background/70 px-2 py-1">
                    <div className="text-[10px] uppercase text-muted-foreground">{t('hyperAi.aiTradingDrawdown', 'Drawdown')}</div>
                    <div className="font-medium text-foreground">
                      {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['max_drawdown'], '%')}
                    </div>
                  </div>
                  <div className="rounded bg-background/70 px-2 py-1">
                    <div className="text-[10px] uppercase text-muted-foreground">{t('hyperAi.aiTradingTrades', 'Trades')}</div>
                    <div className="font-medium text-foreground">
                      {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['trade_count'])}
                    </div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {evidenceActionCounts(strategyBacktestEvidenceDetail).map(([action, count]) => (
                    <span key={action} className="rounded bg-background/70 px-1.5 py-0.5 text-[11px] text-muted-foreground">
                      {action}: <span className="text-foreground">{count}</span>
                    </span>
                  ))}
                  {evidenceActionCounts(strategyBacktestEvidenceDetail).length === 0 && (
                    <span className="rounded bg-background/70 px-1.5 py-0.5 text-[11px] text-muted-foreground">
                      {t('hyperAi.aiTradingNoTriggers', 'No triggers')}
                    </span>
                  )}
                </div>
                {strategyBacktestEvidenceDetail.quality_issues && strategyBacktestEvidenceDetail.quality_issues.length > 0 && (
                  <div className="mt-2 flex items-start gap-1.5 text-yellow-600">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span className="break-words">{strategyBacktestEvidenceDetail.quality_issues.slice(0, 3).join(', ')}</span>
                  </div>
                )}
                {strategyBacktestEvidenceDetail.trigger_summary?.triggers && strategyBacktestEvidenceDetail.trigger_summary.triggers.length > 0 && (
                  <div className="mt-2 space-y-1 border-t pt-2">
                    {strategyBacktestEvidenceDetail.trigger_summary.triggers.slice(0, 3).map((trigger, index) => (
                      <div key={`${trigger.id || index}`} className="min-w-0 rounded bg-background/60 px-2 py-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-medium">
                            {String(trigger.decision_action || '-')} · {String(trigger.symbol || strategyBacktestEvidenceDetail.strategy_symbol || '-')}
                          </span>
                          <span className="shrink-0 text-[11px] text-muted-foreground">
                            {formatEvidenceValue(trigger.equity_after)}
                          </span>
                        </div>
                        {trigger.decision_reason && (
                          <div className="truncate text-[11px] text-muted-foreground">
                            {String(trigger.decision_reason)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {(recentBacktestResults.length > 0 || recentAgentSessions.length > 0 || archivedAgentSessions.length > 0 || recentStrategySpecs.length > 0 || recentSignalEvents.length > 0) && (
              <div className="mt-3 space-y-2 text-xs">
                {recentBacktestResults.length > 0 && (
                  <div className="rounded-md border bg-muted/20 p-2">
                    <div className="mb-1.5 flex items-center gap-1.5 font-medium">
                      <BarChart3 className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span>{t('hyperAi.aiTradingProgramBacktests', 'Program backtests')}</span>
                    </div>
                    <div className="space-y-1">
                      {recentBacktestResults.map(record => (
                        <div key={record.id} className="flex items-center gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium">
                              {(record.symbols || []).join(', ') || record.exchange || 'Backtest'} · {record.program_name || `#${record.id}`}
                            </div>
                            <div className="truncate text-[11px] text-muted-foreground">
                              #{record.id} · {record.status} · {backtestResultLine(record)}
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleAttachProgramBacktestResult(undefined, record.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null || !record.handoff_ready}
                            title={t('hyperAi.aiTradingAttachProgramBacktest', 'Attach Program Backtest result')}
                          >
                            {strategyBacktestLoadingId !== null && strategyBacktestLoadingSource === 'program' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Link2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(recentAgentSessions.length > 0 || archivedAgentSessions.length > 0) && (
                  <div className="rounded-md border bg-muted/20 p-2">
                    <div className="mb-1.5 flex items-center gap-1.5 font-medium">
                      <Blocks className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span>{t('hyperAi.aiTradingRecentSessions', 'Recent agent sessions')}</span>
                    </div>
                    <div className="space-y-1">
                      {recentAgentSessions.map(session => (
                        <div
                          key={session.id}
                          className={`flex items-stretch gap-1 rounded border transition-colors ${
                            selectedAiTradingAgentSessionId === session.id ? 'border-primary/60 bg-primary/10' : 'bg-background/60'
                          }`}
                        >
                          <button
                            type="button"
                            onClick={() => setSelectedAiTradingAgentSessionId(session.id)}
                            className="min-w-0 flex-1 px-2 py-1.5 text-left transition-colors hover:bg-primary/10"
                            title={t('hyperAi.aiTradingSelectSession', 'Select session')}
                          >
                            <div className="flex min-w-0 items-center justify-between gap-2">
                              <div className="truncate font-medium">{session.name || session.id}</div>
                              <div className="shrink-0 text-[11px] text-muted-foreground">
                                {(session.strategy_spec_count ?? 0)}
                                {' '}
                                {t('hyperAi.aiTradingSpecsShort', 'specs')}
                                {' / '}
                                {(session.signal_event_count ?? 0)}
                                {' '}
                                {t('hyperAi.aiTradingSignalsShort', 'signals')}
                              </div>
                            </div>
                            <div className="truncate text-[11px] text-muted-foreground">
                              {(session.symbols || []).slice(0, 4).join(', ') || t('hyperAi.aiTradingNoSymbols', 'No symbols')}
                              {' · '}
                              {t('hyperAi.aiTradingContextBudgetTiny', 'ctx')} {formatAiTradingContextBudget(session)}
                            </div>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleOpenAgentSessionDetailPage(session.id)}
                            className="flex w-8 shrink-0 items-center justify-center border-l text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            title={t('hyperAi.aiTradingOpenSessionDetail', 'Open session detail')}
                            aria-label={t('hyperAi.aiTradingOpenSessionDetail', 'Open session detail')}
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                      {archivedAgentSessions.length > 0 && (
                        <div className="pt-1">
                          <div className="mb-1 text-[10px] uppercase text-muted-foreground">
                            {t('hyperAi.aiTradingArchivedSessions', 'Archived sessions')}
                          </div>
                          <div className="space-y-1">
                            {archivedAgentSessions.map(session => (
                              <div
                                key={session.id}
                                className={`flex items-stretch gap-1 rounded border opacity-80 transition-colors ${
                                  selectedAiTradingAgentSessionId === session.id ? 'border-primary/60 bg-primary/10' : 'bg-background/60'
                                }`}
                              >
                                <button
                                  type="button"
                                  onClick={() => setSelectedAiTradingAgentSessionId(session.id)}
                                  className="min-w-0 flex-1 px-2 py-1.5 text-left transition-colors hover:bg-primary/10"
                                  title={t('hyperAi.aiTradingSelectArchivedSession', 'Select archived session')}
                                >
                                  <div className="flex min-w-0 items-center justify-between gap-2">
                                    <div className="truncate font-medium">{session.name || session.id}</div>
                                    <div className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                                      {session.status || 'archived'}
                                    </div>
                                  </div>
                                  <div className="truncate text-[11px] text-muted-foreground">
                                    {(session.strategy_spec_count ?? 0)}
                                    {' '}
                                    {t('hyperAi.aiTradingSpecsShort', 'specs')}
                                    {' / '}
                                    {(session.signal_event_count ?? 0)}
                                    {' '}
                                    {t('hyperAi.aiTradingSignalsShort', 'signals')}
                                    {' · '}
                                    {(session.symbols || []).slice(0, 3).join(', ') || t('hyperAi.aiTradingNoSymbols', 'No symbols')}
                                    {' · '}
                                    {t('hyperAi.aiTradingContextBudgetTiny', 'ctx')} {formatAiTradingContextBudget(session)}
                                  </div>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleOpenAgentSessionDetailPage(session.id)}
                                  className="flex w-8 shrink-0 items-center justify-center border-l text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                                  title={t('hyperAi.aiTradingOpenSessionDetail', 'Open session detail')}
                                  aria-label={t('hyperAi.aiTradingOpenSessionDetail', 'Open session detail')}
                                >
                                  <ExternalLink className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {recentStrategySpecs.length > 0 && (
                  <div className="rounded-md border bg-muted/20 p-2">
                    <div className="mb-1.5 flex items-center gap-1.5 font-medium">
                      <FileJson className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span>
                        {selectedAiTradingAgentSession
                          ? t('hyperAi.aiTradingSessionSpecs', 'Session specs')
                          : t('hyperAi.aiTradingRecentSpecs', 'Recent specs')}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {recentStrategySpecs.map(record => (
                        <div key={record.id} className="flex items-center gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium">{record.symbol} · {record.name}</div>
                            <div className="truncate text-[11px] text-muted-foreground">
                              #{record.id}
                              {' · '}
                              {record.status}
                              {record.agent_session?.name ? ` · ${record.agent_session.name}` : ''}
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleInspectStrategySpecRecord(record.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            title={t('hyperAi.aiTradingInspectSpec', 'Inspect spec')}
                          >
                            <SearchIcon className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleAttachBacktestSummary(record.id, record)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null || isStrategyRecordActionBlockedByArchivedSession(record)}
                            title={isStrategyRecordActionBlockedByArchivedSession(record) ? archivedSessionActionTitle : t('hyperAi.aiTradingAttachBacktest', 'Attach backtest summary')}
                          >
                            {strategyBacktestLoadingId === record.id && strategyBacktestLoadingSource === 'summary' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <BarChart3 className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleAttachProgramBacktestResult(record.id, undefined, record)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null || isStrategyRecordActionBlockedByArchivedSession(record)}
                            title={isStrategyRecordActionBlockedByArchivedSession(record) ? archivedSessionActionTitle : t('hyperAi.aiTradingAttachProgramBacktest', 'Attach Program Backtest result')}
                          >
                            {strategyBacktestLoadingId === record.id && strategyBacktestLoadingSource === 'program' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Link2 className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleAttachLatestProgramBacktestResult(record.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null || isStrategyRecordActionBlockedByArchivedSession(record)}
                            title={isStrategyRecordActionBlockedByArchivedSession(record) ? archivedSessionActionTitle : t('hyperAi.aiTradingAttachLatestProgramBacktest', 'Attach latest matching Program Backtest')}
                          >
                            {strategyBacktestLoadingId === record.id && strategyBacktestLoadingSource === 'latest' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <History className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleStrategyBacktestPreflight(record.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null || isStrategyRecordActionBlockedByArchivedSession(record)}
                            title={isStrategyRecordActionBlockedByArchivedSession(record) ? archivedSessionActionTitle : t('hyperAi.aiTradingBacktestPreflight', 'Build backtest preflight')}
                          >
                            {strategyBacktestLoadingId === record.id && strategyBacktestLoadingSource === 'preflight' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <ShieldCheck className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRunStrategyProgramBacktest(record.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null || isStrategyRecordActionBlockedByArchivedSession(record) || !strategyProgramBacktestRunConfirmed}
                            title={
                              isStrategyRecordActionBlockedByArchivedSession(record)
                                ? archivedSessionActionTitle
                                : !strategyProgramBacktestRunConfirmed
                                  ? t('hyperAi.aiTradingRunBacktestConfirmRequired', 'Confirm this historical Program Backtest run before starting it')
                                  : t('hyperAi.aiTradingRunProgramBacktest', 'Run Program Backtest')
                            }
                          >
                            {strategyBacktestLoadingId === record.id && strategyBacktestLoadingSource === 'run' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Play className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleInspectStrategyBacktestEvidence(record.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={strategyBacktestLoadingId !== null}
                            title={t('hyperAi.aiTradingInspectBacktestEvidence', 'Inspect backtest evidence')}
                          >
                            {strategyBacktestLoadingId === record.id && strategyBacktestLoadingSource === 'evidence' ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <SearchIcon className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {recentSignalEvents.length > 0 && (
                  <div className="rounded-md border bg-muted/20 p-2">
                    <div className="mb-1.5 flex items-center gap-1.5 font-medium">
                      <MessageSquare className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span>
                        {selectedAiTradingAgentSession
                          ? t('hyperAi.aiTradingSessionSignals', 'Session signals')
                          : t('hyperAi.aiTradingRecentSignals', 'Recent signals')}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {recentSignalEvents.map(event => (
                        <div key={event.id} className="flex items-center gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="flex min-w-0 items-center gap-1.5">
                              <span className="truncate font-medium">{event.symbol} · {event.action}</span>
                              <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] ${signalStatusClassName(event)}`}>
                                {signalStatusLabel(event)}
                              </span>
                            </div>
                            <div className="truncate text-[11px] text-muted-foreground">
                              #{event.id} · {event.status} · {signalBlockerSummary(event)}
                              {event.agent_session?.name ? ` · ${event.agent_session.name}` : ''}
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleInspectSignalEventRecord(event.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            title={t('hyperAi.aiTradingInspectSignal', 'Inspect signal')}
                          >
                            <SearchIcon className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleInspectSignalHandoffAttempts(event.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                            disabled={signalHandoffAttemptsLoadingId !== null}
                            title={t('hyperAi.aiTradingInspectHandoffAttempts', 'Inspect handoff attempts')}
                          >
                            {signalHandoffAttemptsLoadingId === event.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <History className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRejectSignalEvent(event.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-red-500/10 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={event.status !== 'review_candidate' || signalRejectLoadingId !== null || signalHandoffLoadingId !== null}
                            title={t('hyperAi.aiTradingRejectSignal', 'Reject signal')}
                          >
                            {signalRejectLoadingId === event.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <X className="h-3.5 w-3.5" />
                            )}
                          </button>
                          {isSignalHandoffEligible(event) && event.handoff_status !== 'submitted' && (
                            <label
                              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-green-500/10 hover:text-green-600"
                              title={t('hyperAi.aiTradingConfirmSignalHandoff', 'Confirm signal handoff')}
                              aria-label={t('hyperAi.aiTradingConfirmSignalHandoff', 'Confirm signal handoff')}
                            >
                              <Checkbox
                                data-testid="ai-trading-signal-handoff-confirm"
                                checked={Boolean(signalHandoffConfirmedEventIds[event.id])}
                                onCheckedChange={(checked) => setSignalHandoffEventConfirmed(event.id, checked === true)}
                                disabled={signalHandoffLoadingId !== null || signalRejectLoadingId !== null}
                                className="h-3.5 w-3.5"
                              />
                            </label>
                          )}
                          <button
                            type="button"
                            onClick={() => handleSubmitSignalEventHandoff(event.id)}
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground transition-colors hover:bg-green-500/10 hover:text-green-600 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={
                              !isSignalHandoffEligible(event) ||
                              !signalHandoffConfirmedEventIds[event.id] ||
                              signalHandoffLoadingId !== null ||
                              event.handoff_status === 'submitted'
                            }
                            title={signalHandoffTitle(event)}
                          >
                            {signalHandoffLoadingId === event.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Play className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Memory Entry */}
          <div className="pt-4">
            <button
              onClick={() => setShowMemoryModal(true)}
              className="w-full flex items-center gap-1.5 py-1 rounded-lg text-sm hover:bg-muted/50 transition-colors text-left"
            >
              <Brain className="w-4 h-4 text-primary shrink-0" />
              <span className="text-sm font-medium">{t('hyperAi.memory.button', 'Memory')}</span>
              <ChevronRight className="w-3 h-3 text-muted-foreground ml-auto shrink-0" />
            </button>
          </div>

          <div className="pt-4">
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-sm font-medium flex items-center gap-1.5">
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 1024 1024" fill="currentColor">
                  <path d="M556.8 960H166.4c-25.6 0-51.2-12.8-70.4-25.6-19.2-19.2-32-44.8-32-70.4v-115.2c6.4-19.2 12.8-38.4 32-51.2 12.8-6.4 19.2-12.8 32-12.8s25.6 6.4 44.8 12.8H192c12.8 6.4 19.2 6.4 32 6.4s25.6 0 32-6.4c12.8-6.4 19.2-12.8 25.6-19.2 6.4-6.4 12.8-19.2 19.2-25.6 6.4-12.8 6.4-19.2 6.4-32s0-25.6-6.4-32c-6.4-12.8-12.8-19.2-19.2-25.6s-19.2-12.8-25.6-19.2c-12.8-6.4-19.2-6.4-32-6.4s-19.2 0-32 6.4h-6.4-6.4c-6.4 6.4-19.2 6.4-25.6 12.8-12.8 6.4-25.6 6.4-38.4 6.4-19.2 0-32-12.8-38.4-25.6-6.4-12.8-12.8-25.6-12.8-44.8V390.4c0-25.6 12.8-51.2 32-70.4 19.2-19.2 44.8-32 70.4-32h83.2c-6.4-19.2-6.4-32-6.4-51.2 0-25.6 6.4-51.2 12.8-70.4l38.4-57.6c19.2-19.2 38.4-32 57.6-38.4 25.6-12.8 44.8-12.8 70.4-12.8s51.2 6.4 70.4 12.8l57.6 38.4c19.2 19.2 32 38.4 38.4 57.6 12.8 25.6 12.8 44.8 12.8 70.4 0 19.2 0 38.4-6.4 51.2h25.6c25.6 0 51.2 12.8 70.4 32 19.2 19.2 25.6 44.8 25.6 70.4v19.2c0 12.8-12.8 32-38.4 32-25.6 0-32-12.8-38.4-25.6v-25.6c0-6.4 0-12.8-6.4-19.2-6.4-6.4-6.4-6.4-19.2-6.4H441.6l51.2-64c19.2-19.2 25.6-38.4 25.6-64 0-12.8 0-32-6.4-44.8-6.4-12.8-12.8-25.6-25.6-32-12.8-12.8-19.2-19.2-32-25.6-12.8-6.4-25.6-6.4-44.8-6.4-12.8 0-25.6 0-44.8 6.4-12.8 6.4-25.6 12.8-32 25.6-12.8 12.8-19.2 19.2-25.6 32-6.4 12.8-6.4 25.6-6.4 44.8 0 12.8 0 25.6 6.4 38.4 6.4 12.8 12.8 25.6 19.2 32l51.2 64H153.6c-6.4 0-12.8 0-19.2 6.4-6.4 6.4-6.4 12.8-6.4 19.2v89.6s6.4 0 6.4-6.4c6.4 0 6.4-6.4 12.8-6.4 19.2-6.4 38.4-12.8 64-12.8 19.2 0 44.8 6.4 64 12.8 19.2 6.4 38.4 19.2 51.2 32 12.8 12.8 25.6 32 32 51.2 6.4 19.2 12.8 38.4 12.8 64 0 19.2-6.4 44.8-12.8 64-6.4 19.2-19.2 38.4-32 51.2-12.8 12.8-32 25.6-51.2 32-19.2 6.4-38.4 12.8-64 12.8-19.2 0-44.8-6.4-64-12.8-6.4 0-12.8-6.4-19.2-6.4v96c0 6.4 0 12.8 6.4 19.2 6.4 6.4 12.8 6.4 19.2 6.4h396.8c19.2 6.4 25.6 19.2 25.6 38.4 6.4 25.6 0 32-19.2 38.4z m204.8-76.8c-6.4-6.4-25.6-19.2-32-19.2-6.4 0-25.6 12.8-32 19.2-6.4 6.4-19.2 12.8-25.6 12.8-6.4 0-12.8 0-12.8-6.4l-51.2-25.6c-12.8-12.8-19.2-25.6-12.8-44.8 0 0 6.4-6.4 6.4-12.8 0-12.8-6.4-19.2-12.8-25.6-6.4-6.4-19.2-12.8-25.6-12.8-12.8 0-25.6-12.8-32-32 0 0-6.4-25.6-6.4-44.8 0-19.2 6.4-44.8 6.4-44.8 6.4-19.2 12.8-32 32-32s38.4-19.2 38.4-38.4c0-6.4-6.4-12.8-6.4-12.8-6.4-19.2 0-38.4 12.8-44.8l57.6-32c6.4 0 12.8-6.4 12.8-6.4 12.8 0 19.2 6.4 25.6 12.8 6.4 6.4 25.6 19.2 32 19.2 6.4 0 25.6-12.8 32-19.2 6.4-6.4 19.2-12.8 25.6-12.8 6.4 0 12.8 0 12.8 6.4l51.2 25.6c12.8 12.8 19.2 25.6 12.8 44.8 0 0-6.4 6.4-6.4 12.8 0 19.2 19.2 38.4 38.4 38.4 12.8 0 25.6 12.8 32 32 0 0 6.4 25.6 6.4 44.8 0 19.2-6.4 44.8-6.4 44.8-6.4 19.2-12.8 32-32 32-12.8 0-19.2 6.4-25.6 12.8s-12.8 19.2-12.8 25.6c0 6.4 6.4 12.8 6.4 12.8 6.4 19.2 0 38.4-12.8 44.8l-57.6 32c-6.4 0-12.8 6.4-12.8 6.4-12.8 0-19.2-6.4-25.6-12.8z m-38.4-70.4c19.2 0 32 6.4 51.2 19.2 6.4 6.4 12.8 6.4 12.8 12.8l32-19.2c0-6.4 0-12.8-6.4-25.6 0-44.8 32-83.2 76.8-89.6v-19.2-19.2c-44.8-6.4-76.8-44.8-76.8-89.6 0-6.4 0-19.2 6.4-25.6l-32-19.2-12.8 12.8c-19.2 12.8-32 19.2-51.2 19.2s-32-6.4-51.2-19.2c-6.4-6.4-12.8-6.4-12.8-12.8l-32 19.2c0 6.4 6.4 12.8 6.4 25.6 0 44.8-32 83.2-76.8 89.6v38.4c44.8 6.4 76.8 44.8 76.8 89.6 0 6.4 0 19.2-6.4 25.6l25.6 12.8 12.8-12.8c25.6-6.4 44.8-12.8 57.6-12.8z m0-38.4c-44.8 0-83.2-38.4-83.2-83.2 0-44.8 38.4-83.2 83.2-83.2 44.8 0 83.2 38.4 83.2 83.2 6.4 44.8-32 83.2-83.2 83.2z m0-115.2c-6.4 0-19.2 6.4-25.6 6.4-6.4 6.4-6.4 12.8-6.4 25.6 0 19.2 12.8 32 32 32s32-12.8 32-32-12.8-32-32-32z" />
                </svg>
                {t('hyperAi.skills', 'Skills')}
              </h4>
              {skills.length > 0 && !skillsEditMode && (
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSkillsEditMode(true)}>
                  <Pencil className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground/60 mb-2 px-0.5">
              {t('hyperAi.skillsHint', 'Auto-loaded by AI, or type /command')}
            </p>
            {skills.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                {t('hyperAi.skillsLoading', 'Loading...')}
              </p>
            ) : (
              <>
                <div className="space-y-1">
                  {skills.map(skill => {
                    const isEnabled = pendingSkillToggles[skill.name] !== undefined
                      ? pendingSkillToggles[skill.name]
                      : skill.enabled
                    return (
                      <div
                        key={skill.name}
                        className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-muted/50 transition-colors"
                      >
                        {skillsEditMode ? (
                          <Switch
                            checked={isEnabled}
                            onCheckedChange={v => setPendingSkillToggles(prev => ({ ...prev, [skill.name]: v }))}
                            disabled={skillsLoading}
                            className="scale-75 origin-left shrink-0"
                          />
                        ) : activeSkill === skill.name ? (
                          <svg className="w-3.5 h-3.5 shrink-0 text-red-500" viewBox="0 0 1024 1024" fill="currentColor">
                            <path d="M896.512 471.04c-23.04 0-38.4 15.36-38.4 38.4s15.36 38.4 38.4 38.4 38.4-15.36 38.4-38.4c0-23.552-15.36-38.4-38.4-38.4z m-76.8-267.264c-23.04 0-38.4 15.36-38.4 38.4s15.36 38.4 38.4 38.4 38.4-15.36 38.4-38.4-15.36-38.4-38.4-38.4z m-192.512-38.4c23.04 0 38.4-15.36 38.4-38.4s-15.36-38.4-38.4-38.4-38.4 15.36-38.4 38.4 15.36 38.4 38.4 38.4z m-230.4 0c23.04 0 38.4-15.36 38.4-38.4s-15.36-38.4-38.4-38.4-38.4 15.36-38.4 38.4 15.36 38.4 38.4 38.4zM165.888 241.664c-23.04 0-38.4 15.36-38.4 38.4s15.36 38.4 38.4 38.4 38.4-15.36 38.4-38.4-15.36-38.4-38.4-38.4zM127.488 471.04c-23.04 0-38.4 15.36-38.4 38.4s15.36 38.4 38.4 38.4 38.4-15.36 38.4-38.4c0-23.552-15.36-38.4-38.4-38.4z m508.416 203.264c-24.576 16.384-53.76 32.768-82.432 36.864-12.288 4.096-28.672 4.096-41.472 4.096-12.288 0-28.672 0-41.472-4.096-33.28-4.096-57.856-20.48-82.432-36.864-49.664-36.864-82.432-98.304-82.432-163.84 0-114.688 90.624-204.8 206.336-204.8s206.336 90.112 206.336 204.8c0 65.536-32.768 126.976-82.432 163.84z m-58.88 154.112c0 37.888-25.088 62.976-62.976 62.976s-62.976-25.088-62.976-62.976v-59.392c18.944 6.144 44.032 6.144 62.976 6.144s44.032-6.144 62.976-6.144v59.392zM512 247.808c-150.016 0-269.312 118.272-269.312 267.264 0 107.008 61.44 198.656 153.6 240.64v65.024c0 65.024 50.176 114.688 115.2 114.688 65.536 0 115.2-49.664 115.2-114.688v-65.024c92.16-41.984 153.6-133.632 153.6-240.64 1.024-148.992-118.272-267.264-268.288-267.264z" />
                          </svg>
                        ) : (
                          <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${isEnabled ? 'bg-green-500' : 'bg-muted-foreground/30'}`} />
                        )}
                        <span className="text-xs truncate flex-1">
                          {t(`hyperAi.skillNames.${skill.name}`, skill.name)}
                        </span>
                        <span className="text-[10px] text-muted-foreground/50 shrink-0 font-mono">{skill.command}</span>
                      </div>
                    )
                  })}
                </div>
                {skillsEditMode && (
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleSkillsEditCancel}
                      className="h-7 px-3 text-xs"
                    >
                      {t('hyperAi.skillsCancel', 'Cancel')}
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSkillsEditSave}
                      disabled={skillsLoading}
                      className="h-7 px-3 text-xs"
                    >
                      {t('hyperAi.skillsSave', 'Save')}
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* External Tools */}
          {externalTools.length > 0 && (
            <div className="pt-4">
              <h4 className="text-sm font-medium flex items-center gap-1.5 mb-2">
                <Wrench className="w-4 h-4 shrink-0" />
                {t('hyperAi.tools', 'Tools')}
              </h4>
              <div className="space-y-1">
                {externalTools.map(tool => (
                  <div
                    key={tool.name}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => { setSelectedTool(tool); setShowToolModal(true) }}
                  >
                    <SearchIcon className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                    <span className="text-xs truncate flex-1">
                      {currentLang === 'zh' ? tool.display_name_zh : tool.display_name}
                    </span>
                    {tool.configured ? (
                      <span className="w-2 h-2 rounded-full bg-green-500 shrink-0"></span>
                    ) : (
                      <span className="text-[10px] text-primary shrink-0">
                        {t('tools.setup', 'Setup')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bot Integrations */}
          <div className="pt-4">
            <h4 className="text-sm font-medium flex items-center gap-1.5 mb-2">
              <Blocks className="w-4 h-4 shrink-0" />
              {t('hyperAi.integrations', 'Integrations')}
              <button
                onClick={() => setShowNotificationModal(true)}
                className="ml-auto flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-primary/10 hover:bg-primary/20 transition-colors"
                title={t('bot.notificationSettings', 'Push Notifications')}
              >
                <NotificationBellSmallIcon />
                {notificationCount > 0 && (
                  <span className="text-[10px] text-primary font-medium min-w-[14px] text-center">
                    {notificationCount}
                  </span>
                )}
              </button>
            </h4>
            <div className="space-y-2">
              {/* Telegram Bot */}
              <div
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => setShowBotModal(true)}
              >
                <TelegramSmallIcon />
                <span className="text-xs">{t('hyperAi.telegramBot', 'Telegram Bot')}</span>
                {botConfig && botConfig.status === 'connected' ? (
                  <>
                    <span className="ml-auto text-[10px] text-muted-foreground">@{botConfig.bot_username}</span>
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  </>
                ) : (
                  <span className="ml-auto text-[10px] text-primary">
                    {t('bot.setup', 'Setup')}
                  </span>
                )}
              </div>
              {/* Discord Bot - Coming Soon */}
              <div
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => setShowDiscordBotModal(true)}
              >
                <DiscordSmallIcon />
                <span className="text-xs">{t('hyperAi.discordBot', 'Discord Bot')}</span>
                {discordBotConfig && discordBotConfig.status === 'connected' ? (
                  <>
                    <span className="ml-auto text-[10px] text-muted-foreground">@{discordBotConfig.bot_username}</span>
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  </>
                ) : (
                  <span className="ml-auto text-[10px] text-primary">
                    {t('bot.setup', 'Setup')}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LLM Config Modal */}
      <LLMConfigModal
        open={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        providers={providers}
        currentProfile={profile}
        onSaved={handleLLMConfigSaved}
      />

      {/* Memory Modal */}
      <MemoryModal
        open={showMemoryModal}
        onClose={() => setShowMemoryModal(false)}
      />

      <Dialog open={strategyBacktestEvidenceDialogOpen} onOpenChange={setStrategyBacktestEvidenceDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader className="border-b pb-3">
            <div className="flex items-center justify-between gap-3">
              <DialogTitle className="flex min-w-0 items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4 shrink-0 text-primary" />
                <span className="truncate">
                  {t('hyperAi.aiTradingBacktestEvidence', 'Backtest evidence')}
                  {strategyBacktestEvidenceDetail?.backtest_result?.id
                    ? ` #${strategyBacktestEvidenceDetail.backtest_result.id}`
                    : ''}
                </span>
              </DialogTitle>
              {strategyBacktestEvidenceDetail?.strategy_spec_id && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 shrink-0"
                  onClick={() => handleOpenBacktestEvidencePage(strategyBacktestEvidenceDetail.strategy_spec_id)}
                  title={t('hyperAi.aiTradingOpenBacktestEvidencePage', 'Open evidence page')}
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              )}
            </div>
          </DialogHeader>
          {strategyBacktestEvidenceDetail ? (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="grid gap-3 p-1 md:grid-cols-4">
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingStatus', 'Status')}</div>
                  <div className={`mt-1 text-lg font-semibold ${
                    strategyBacktestEvidenceDetail.handoff_ready ? 'text-green-600' : 'text-yellow-600'
                  }`}>
                    {strategyBacktestEvidenceDetail.handoff_ready
                      ? t('hyperAi.aiTradingStatusReady', 'Ready')
                      : t('hyperAi.aiTradingStatusBlocked', 'Blocked')}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {strategyBacktestEvidenceDetail.backtest_result?.status || '-'}
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingReturn', 'Return')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['total_return'], '%')}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['net_pnl'])} PnL
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingDrawdown', 'Drawdown')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['max_drawdown'], '%')}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['profit_factor'])} PF
                  </div>
                </div>
                <div className="rounded-md border bg-muted/20 p-3">
                  <div className="text-xs text-muted-foreground">{t('hyperAi.aiTradingTrades', 'Trades')}</div>
                  <div className="mt-1 text-lg font-semibold">
                    {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['trade_count'])}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatEvidenceValue(strategyBacktestEvidenceDetail.backtest_result?.metrics?.['win_rate'], '%')} win
                  </div>
                </div>
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
                <div className="rounded-md border bg-muted/10 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="text-sm font-medium">{t('hyperAi.aiTradingEquityCurve', 'Equity curve')}</div>
                    <div className="text-xs text-muted-foreground">
                      {(strategyBacktestEvidenceDetail.backtest_result?.symbols || []).join(', ') || strategyBacktestEvidenceDetail.strategy_symbol || '-'}
                    </div>
                  </div>
                  <div className="h-40 rounded bg-background/70 p-2">
                    {evidenceEquityPath(strategyBacktestEvidenceDetail) ? (
                      <svg viewBox="0 0 320 120" className="h-full w-full" preserveAspectRatio="none">
                        <path d={evidenceEquityPath(strategyBacktestEvidenceDetail)} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />
                        {evidenceEquitySeries(strategyBacktestEvidenceDetail).map((point, index, series) => {
                          const minEquity = Math.min(...series.map(item => item.equity))
                          const maxEquity = Math.max(...series.map(item => item.equity))
                          const span = maxEquity - minEquity || 1
                          const x = series.length === 1 ? 160 : 10 + (index / (series.length - 1)) * 300
                          const y = 110 - ((point.equity - minEquity) / span) * 100
                          return <circle key={`${point.timestamp}-${index}`} cx={x} cy={y} r="2.5" className="fill-primary" />
                        })}
                      </svg>
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoEquityCurve', 'No equity curve sample')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-md border bg-muted/10 p-3">
                  <div className="mb-2 text-sm font-medium">{t('hyperAi.aiTradingActionDistribution', 'Action distribution')}</div>
                  <div className="space-y-2">
                    {evidenceActionCounts(strategyBacktestEvidenceDetail).map(([action, count]) => {
                      const maxCount = Math.max(...evidenceActionCounts(strategyBacktestEvidenceDetail).map(([, value]) => value), 1)
                      return (
                        <div key={action}>
                          <div className="mb-1 flex items-center justify-between text-xs">
                            <span className="truncate">{action}</span>
                            <span className="text-muted-foreground">{count}</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded bg-muted">
                            <div className="h-full bg-primary" style={{ width: `${Math.max(8, (count / maxCount) * 100)}%` }} />
                          </div>
                        </div>
                      )
                    })}
                    {evidenceActionCounts(strategyBacktestEvidenceDetail).length === 0 && (
                      <div className="text-sm text-muted-foreground">
                        {t('hyperAi.aiTradingNoTriggers', 'No triggers')}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {strategyBacktestEvidenceDetail.quality_issues && strategyBacktestEvidenceDetail.quality_issues.length > 0 && (
                <div className="mt-3 rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-300">
                  <div className="mb-1 font-medium">{t('hyperAi.aiTradingQualityIssues', 'Quality issues')}</div>
                  <div className="flex flex-wrap gap-1">
                    {strategyBacktestEvidenceDetail.quality_issues.map(issue => (
                      <span key={issue} className="rounded bg-background/70 px-2 py-1 text-xs">{issue}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-3 rounded-md border">
                <div className="flex items-center justify-between border-b px-3 py-2">
                  <div className="text-sm font-medium">{t('hyperAi.aiTradingTriggerReview', 'Trigger review')}</div>
                  <div className="text-xs text-muted-foreground">
                    {evidenceTriggerRows(strategyBacktestEvidenceDetail).length}/{strategyBacktestEvidenceDetail.trigger_summary?.total || 0}
                  </div>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-background text-muted-foreground">
                      <tr className="border-b">
                        <th className="px-3 py-2 text-left font-medium">#</th>
                        <th className="px-3 py-2 text-left font-medium">{t('hyperAi.aiTradingAction', 'Action')}</th>
                        <th className="px-3 py-2 text-left font-medium">{t('hyperAi.aiTradingSymbol', 'Symbol')}</th>
                        <th className="px-3 py-2 text-right font-medium">{t('hyperAi.aiTradingEquity', 'Equity')}</th>
                        <th className="px-3 py-2 text-left font-medium">{t('hyperAi.aiTradingReason', 'Reason')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evidenceTriggerRows(strategyBacktestEvidenceDetail).map((trigger, index) => (
                        <tr key={`${trigger.id || index}`} className="border-b last:border-0">
                          <td className="px-3 py-2 text-muted-foreground">{String(trigger.trigger_index ?? index)}</td>
                          <td className="px-3 py-2">{String(trigger.decision_action || '-')}</td>
                          <td className="px-3 py-2">{String(trigger.symbol || strategyBacktestEvidenceDetail.strategy_symbol || '-')}</td>
                          <td className="px-3 py-2 text-right">{formatEvidenceValue(trigger.equity_after)}</td>
                          <td className="max-w-[360px] truncate px-3 py-2 text-muted-foreground">{String(trigger.decision_reason || '-')}</td>
                        </tr>
                      ))}
                      {evidenceTriggerRows(strategyBacktestEvidenceDetail).length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                            {t('hyperAi.aiTradingNoTriggers', 'No triggers')}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-sm text-muted-foreground">
              {t('hyperAi.aiTradingNoBacktestEvidence', 'No backtest evidence loaded')}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Bot Integration Modal */}
      <BotIntegrationModal
        open={showBotModal}
        onClose={() => setShowBotModal(false)}
        platform="telegram"
        onConnected={fetchBotConfig}
        currentBotUsername={botConfig?.status === 'connected' ? botConfig.bot_username : undefined}
      />

      {/* Discord Bot Integration Modal */}
      <BotIntegrationModal
        open={showDiscordBotModal}
        onClose={() => setShowDiscordBotModal(false)}
        platform="discord"
        onConnected={fetchDiscordBotConfig}
        currentBotUsername={discordBotConfig?.status === 'connected' ? discordBotConfig.bot_username : undefined}
        currentBotAppId={discordBotConfig?.bot_app_id}
      />

      {/* Notification Config Modal */}
      <NotificationConfigModal
        open={showNotificationModal}
        onClose={() => setShowNotificationModal(false)}
        onConfigChange={(count) => setNotificationCount(count)}
      />
      <ToolConfigModal
        open={showToolModal}
        onClose={() => { setShowToolModal(false); setSelectedTool(null) }}
        tool={selectedTool}
        onSaved={fetchExternalTools}
      />
    </div>
  )
}

// Message bubble component with avatar, markdown, tool calls, and interrupt recovery
// Wrapped with React.memo to prevent re-rendering when parent state (e.g. inputValue)
// changes but message props remain the same. Without memo, every keystroke in the
// textarea triggers re-render of ALL message bubbles (including expensive ReactMarkdown),
// causing noticeable input lag when conversation history is long.
const MessageBubble = memo(function MessageBubble({
  message,
  onContinue,
  onToolConfirmation,
  t
}: {
  message: Message
  onContinue?: () => void
  onToolConfirmation: (taskId: string, confirmationId: string, confirmed: boolean) => void
  t: (key: string, fallback?: string) => string
}) {
  const [showReasoning, setShowReasoning] = useState(false)
  const [showToolCalls, setShowToolCalls] = useState(false)
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({})
  const isUser = message.role === 'user'

  // Parse tool calls log from stored messages
  const toolCallsLog: ToolCallLogEntry[] = message.tool_calls_log
    ? (() => { try { return JSON.parse(message.tool_calls_log) } catch { return [] } })()
    : []

  /**
   * Extract created entities from tool call results.
   * These are displayed as interactive cards above the AI's text response.
   */
  const createdEntities: CreatedEntityCard[] = toolCallsLog
    .filter(entry => {
      if (!['save_prompt', 'save_program', 'save_signal_pool', 'create_ai_trader', 'save_factor'].includes(entry.tool)) return false
      try {
        const result = JSON.parse(entry.result)
        return result.success === true && result.view_url
      } catch {
        return false
      }
    })
    .map(entry => {
      const result = JSON.parse(entry.result)
      const toolToType: Record<string, CreatedEntityCard['type']> = {
        save_prompt: 'prompt',
        save_program: 'program',
        save_signal_pool: 'signal_pool',
        create_ai_trader: 'ai_trader',
        save_factor: 'factor'
      }
      return {
        type: toolToType[entry.tool],
        id: result.prompt_id || result.program_id || result.pool_id || result.trader_id || result.factor_id,
        name: result.name || result.pool_name || result.trader_name,
        content: result.template_text || result.code || result.expression || (result.signals ? JSON.stringify(result.signals, null, 2) : undefined),
        viewUrl: result.view_url
      } as CreatedEntityCard
    })

  const toggleCardExpanded = (cardId: string) => {
    setExpandedCards(prev => ({ ...prev, [cardId]: !prev[cardId] }))
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message content */}
      <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
        isUser
          ? 'bg-primary text-primary-foreground'
          : 'bg-muted min-w-[400px]'
      }`}>
        {/* Status text during streaming */}
        {message.isStreaming && message.statusText && (
          <div className="flex items-center gap-2 text-xs mb-2 text-primary animate-pulse">
            <PacmanLoader className="w-6 h-3" />
            <span>{message.statusText}</span>
          </div>
        )}

        {/* Real-time tool calls during streaming */}
        {message.isStreaming && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mb-2 text-xs bg-background/50 rounded p-2 max-h-32 overflow-y-auto">
            {message.toolCalls.filter(e => e.type !== 'confirmation_required').slice(-8).map((entry, idx) => (
              <div key={idx} className="mb-1 last:mb-0">
                {entry.type === 'tool_call' && (
                  <span className="text-blue-500">→ {entry.name}</span>
                )}
                {entry.type === 'tool_result' && (
                  <span className="text-green-500">← {entry.name}: done</span>
                )}
                {entry.type === 'reasoning' && (
                  <span className="text-gray-500 italic">{(entry.content || '').slice(0, 100)}...</span>
                )}
                {entry.type === 'subagent_progress' && entry.step === 'reasoning' && (
                  <span className="text-gray-500 italic">[{entry.subagent}] {(entry.content || '').slice(0, 100)}...</span>
                )}
                {entry.type === 'subagent_progress' && entry.step === 'tool_call' && (
                  <span className="text-blue-400">[{entry.subagent}] → {entry.tool}</span>
                )}
                {entry.type === 'subagent_progress' && entry.step === 'tool_result' && (
                  <span className="text-green-400">[{entry.subagent}] ← {entry.tool}: done</span>
                )}
                {entry.type === 'subagent_progress' && entry.step === 'tool_round' && (
                  <span className="text-orange-400">[{entry.subagent}] {t('hyperAi.subagentRound', 'round')}{entry.round ? ` ${entry.round}${entry.max_rounds ? `/${entry.max_rounds}` : ''}` : ''}</span>
                )}
                {entry.type === 'tool_error' && (
                  <span className="text-amber-500">[{entry.name}] {entry.message || entry.severity}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Confirmation cards rendered outside the scrollable tool log for visibility */}
        {message.isStreaming && message.toolCalls?.filter(e => e.type === 'confirmation_required').map((entry, idx) => (
          <div key={`confirm-${idx}`} className="mb-2 rounded border border-amber-300 bg-amber-50 p-3 text-amber-950 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-100">
            <div className="mb-1 flex items-center gap-1 text-sm font-medium">
              <AlertCircle className="h-4 w-4" />
              {t('hyperAi.confirmationRequired', 'Confirmation required')}
            </div>
            <div className="mb-2 text-xs text-muted-foreground">
              {entry.description || entry.name}
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                className="h-7 px-2 text-xs"
                disabled={entry.status !== 'pending' || !entry.taskId || !entry.confirmationId}
                onClick={() => entry.taskId && entry.confirmationId && onToolConfirmation(entry.taskId, entry.confirmationId, true)}
              >
                <CheckCircle2 className="mr-1 h-3 w-3" />
                {entry.status === 'confirmed' ? t('hyperAi.confirmed', 'Confirmed') : t('common.confirm', 'Confirm')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-xs"
                disabled={entry.status !== 'pending' || !entry.taskId || !entry.confirmationId}
                onClick={() => entry.taskId && entry.confirmationId && onToolConfirmation(entry.taskId, entry.confirmationId, false)}
              >
                <X className="mr-1 h-3 w-3" />
                {entry.status === 'cancelled' ? t('hyperAi.cancelled', 'Cancelled') : t('common.cancel', 'Cancel')}
              </Button>
              {entry.status === 'failed' && (
                <span className="self-center text-[11px] text-destructive">
                  {t('hyperAi.confirmationFailed', 'Confirmation failed')}
                </span>
              )}
            </div>
          </div>
        ))}

        {/* Tool calls log for completed messages - moved above content */}
        {!message.isStreaming && toolCallsLog.length > 0 && (
          <details className="mb-3 text-xs border rounded-md">
            <summary className="px-3 py-2 cursor-pointer bg-muted/50 hover:bg-muted font-medium flex items-center gap-1">
              <Wrench className="w-3 h-3" />
              {t('hyperAi.toolCallsDetail', 'Tool calls')} ({toolCallsLog.length})
            </summary>
            <div className="p-3 space-y-3 max-h-96 overflow-y-auto">
              {toolCallsLog.map((entry, idx) => (
                <div key={idx} className="border-b pb-2 last:border-b-0 last:pb-0">
                  <div className="font-medium text-blue-600 dark:text-blue-400 mb-1">
                    {idx + 1}. {entry.tool}
                  </div>
                  {entry.args && Object.keys(entry.args).length > 0 && (
                    <div className="mb-1 ml-2 text-muted-foreground">
                      {Object.entries(maskToolArgsForDisplay(entry.args)).map(([key, value]) => (
                        <div key={key}>{key}: {formatToolArgForDisplay(key, value)}</div>
                      ))}
                    </div>
                  )}
                  <div className="ml-2 text-green-600 dark:text-green-400">
                    Result: {entry.result.length > 200 ? entry.result.slice(0, 200) + '...' : entry.result}
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Created entity cards - displayed above reasoning and main content */}
        {!message.isStreaming && createdEntities.length > 0 && (
          <div className="mb-3 space-y-2">
            {createdEntities.map((entity, idx) => {
              const cardId = `${entity.type}-${entity.id}`
              const isExpanded = expandedCards[cardId]
              const typeLabels: Record<CreatedEntityCard['type'], { label: string; icon: string; color: string }> = {
                prompt: { label: t('hyperAi.createdPrompt', 'Prompt Created'), icon: '📝', color: 'border-l-green-500' },
                program: { label: t('hyperAi.createdProgram', 'Program Created'), icon: '🐍', color: 'border-l-blue-500' },
                signal_pool: { label: t('hyperAi.createdSignalPool', 'Signal Pool Created'), icon: '📊', color: 'border-l-purple-500' },
                ai_trader: { label: t('hyperAi.createdAiTrader', 'AI Trader Created'), icon: '🤖', color: 'border-l-amber-500' },
                factor: { label: t('hyperAi.createdFactor', 'Factor Saved'), icon: '📐', color: 'border-l-violet-500' }
              }
              const { label, icon, color } = typeLabels[entity.type]

              return (
                <div key={cardId} className={`border rounded-lg border-l-4 ${color} bg-background text-foreground`}>
                  {/* Card header */}
                  <div className="px-3 py-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>{icon}</span>
                      <span className="text-sm font-medium text-green-600 dark:text-green-400">✓ {label}</span>
                    </div>
                  </div>

                  {/* Card body */}
                  <div className="px-3 pb-2">
                    <div className="text-sm mb-2">
                      <span className="text-muted-foreground">{t('hyperAi.entityName', 'Name')}:</span>{' '}
                      <span className="font-medium">{entity.name}</span>
                      <span className="text-muted-foreground ml-2">(ID: {entity.id})</span>
                    </div>

                    {/* Expandable content preview */}
                    {entity.content && (
                      <div className="mb-2">
                        <button
                          onClick={() => toggleCardExpanded(cardId)}
                          className="text-xs text-primary hover:underline flex items-center gap-1"
                        >
                          {isExpanded ? (
                            <><ChevronDown className="w-3 h-3" />{t('hyperAi.hideContent', 'Hide content')}</>
                          ) : (
                            <><ChevronRight className="w-3 h-3" />{t('hyperAi.viewContent', 'View content')}</>
                          )}
                        </button>
                        {isExpanded && (
                          <div className="mt-2 max-h-64 overflow-y-auto rounded border bg-muted/30 p-2">
                            <pre className="text-xs whitespace-pre-wrap font-mono">{entity.content}</pre>
                          </div>
                        )}
                      </div>
                    )}

                    {/* View in page link */}
                    <a
                      href={entity.viewUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      {t('hyperAi.viewInPage', 'View in page')} →
                    </a>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Reasoning snapshot for completed messages - moved above content */}
        {!message.isStreaming && message.reasoning_snapshot && (
          <details className="mb-3 text-xs border rounded-md">
            <summary className="px-3 py-2 cursor-pointer bg-muted/50 hover:bg-muted font-medium">
              {t('hyperAi.reasoningProcess', 'Reasoning process')}
            </summary>
            <div className="p-3 max-h-96 overflow-y-auto">
              <pre className="whitespace-pre-wrap text-muted-foreground">{message.reasoning_snapshot}</pre>
            </div>
          </details>
        )}

        {/* Main content with Markdown */}
        <div className={`text-sm prose prose-sm max-w-none ${
          isUser ? 'prose-invert' : 'dark:prose-invert'
        }`}>
          {message.content ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                /**
                 * Custom link renderer for Hyper AI chat:
                 * - Internal hash links (e.g., /#trader-management) open in new tab
                 *   so the chat conversation is not interrupted
                 * - External links also open in new tab with security attributes
                 */
                a: ({ href, children }) => {
                  const isInternal = href?.startsWith('/') || href?.startsWith('#')
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel={isInternal ? undefined : 'noopener noreferrer'}
                      className={isUser
                        ? 'text-white underline hover:text-white/80'
                        : 'text-primary hover:underline'
                      }
                    >
                      {children}
                    </a>
                  )
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : message.isStreaming ? (
            <span className="text-muted-foreground italic">{t('hyperAi.generating', 'Generating...')}</span>
          ) : null}
        </div>

        {/* Streaming cursor */}
        {message.isStreaming && message.content && (
          <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
        )}

        {/* Interrupted message - continue button */}
        {message.isInterrupted && onContinue && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400 mb-2">
              <AlertCircle className="w-3 h-3" />
              <span>
                {t('hyperAi.interruptedAt', 'Interrupted at round {{round}}').replace('{{round}}', String(message.interruptedRound || '?'))}
              </span>
            </div>
            <Button size="sm" variant="outline" onClick={onContinue} className="text-xs">
              <Play className="w-3 h-3 mr-1" />
              {t('hyperAi.continueButton', 'Continue')}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
})
