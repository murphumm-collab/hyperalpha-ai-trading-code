import React, { useCallback, useEffect, useRef, useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { RefreshCw } from 'lucide-react'
import {
  getHyperliquidAvailableSymbols,
  getHyperliquidWatchlist,
  updateHyperliquidWatchlist,
  getBinanceAvailableSymbols,
  getBinanceWatchlist,
  updateBinanceWatchlist,
  getNewsSources,
  updateNewsSources,
  testNewsSource,
  getNewsStats,
} from '@/lib/api'
import { authFetch } from '@/lib/authFetch'
import { useAuth } from '@/contexts/AuthContext'
import {
  extractAiTradingAgentContextLocators,
  extractAiTradingProductionEvidenceExplain,
  extractAiTradingProductionEvidenceTemplateGuidance,
  formatAiTradingProductionEvidenceBlocker,
} from '@/lib/aiTradingReadiness'
import type {
  HyperliquidSymbolMeta,
  BinanceSymbolMeta,
  NewsSourceConfig,
  NewsStatsResponse,
  TestNewsSourceResponse,
} from '@/lib/api'
import type {
  AiTradingAgentContextLocatorMeta,
  AiTradingAgentContextLocatorView,
  AiTradingProductionEvidenceExplainView,
  AiTradingProductionEvidenceTemplateGuidanceView,
  AiTradingProductionComponent,
  AiTradingProductionReadiness,
} from '@/lib/aiTradingReadiness'
import DataCoverageHeatmap from './DataCoverageHeatmap'
import ExchangeIcon from '@/components/exchange/ExchangeIcon'
import { CoinIcon } from '@/components/ui/coin-icon'

const AI_TRADING_EVIDENCE_MAX_JSON_CHARS = 40000

interface StorageStats {
  exchange: string
  total_size_mb: number
  tables: Record<string, number>
  retention_days: number
  symbol_count: number
  estimated_per_symbol_per_day_mb: number
}

interface AdminUser {
  id: number
  username: string
  email?: string | null
  role: 'user' | 'admin' | 'operator'
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

interface AdminAuditLog {
  id: number
  action: string
  actor_user_id?: number | null
  actor_username?: string | null
  target_user_id?: number | null
  target_username?: string | null
  old_value?: string | null
  new_value?: string | null
  details?: Record<string, unknown>
  created_at?: string | null
}

interface AiRuntimeUserStats {
  user_id?: number | null
  username?: string | null
  email?: string | null
  total_tasks: number
  running_tasks: number
  remote_running_tasks?: number
  persisted_running_tasks?: number
  stale_running_tasks?: number
  completed_tasks: number
  error_tasks: number
  oldest_running_age_seconds?: number | null
  oldest_persisted_running_age_seconds?: number | null
}

interface AiRuntimeStats {
  runner_id?: string
  running_tasks: number
  remote_running_tasks?: number
  effective_running_tasks?: number
  persisted_running_tasks?: number
  stale_running_tasks?: number
  completed_buffered_tasks: number
  error_buffered_tasks: number
  total_buffered_tasks: number
  task_max_workers: number
  task_max_running_global: number
  task_max_running_per_user: number
  task_threads: number
  task_queue: number
  background_max_workers: number
  background_threads: number
  background_queue: number
  distributed_admission?: {
    enabled: boolean
    available: boolean
    running_tasks?: number
    lease_ttl_seconds?: number
    fail_open?: boolean
    last_error?: string | null
  }
  dispatch_queue?: {
    enabled: boolean
    claim_stale_seconds?: number
    pending: number
    claimed: number
    running: number
    completed: number
    failed: number
    total: number
    last_error?: string | null
  }
  users: AiRuntimeUserStats[]
}

export default function SettingsPage() {
  const { t, i18n } = useTranslation()
  const { user: authUser, setUser: setAuthUser } = useAuth()
  const [activeTab, setActiveTab] = useState('watchlist')

  // Language state
  const currentLang = i18n.language === 'zh' ? 'zh' : 'en'

  // Hyperliquid Watchlist state
  const [hlAvailableSymbols, setHlAvailableSymbols] = useState<HyperliquidSymbolMeta[]>([])
  const [hlWatchlistSymbols, setHlWatchlistSymbols] = useState<string[]>([])
  const [hlMaxSymbols, setHlMaxSymbols] = useState(10)
  const [hlLoading, setHlLoading] = useState(true)
  const [hlSaving, setHlSaving] = useState(false)
  const [hlError, setHlError] = useState<string | null>(null)
  const [hlSuccess, setHlSuccess] = useState<string | null>(null)
  const [hlSearchQuery, setHlSearchQuery] = useState('')

  // Binance Watchlist state
  const [bnAvailableSymbols, setBnAvailableSymbols] = useState<BinanceSymbolMeta[]>([])
  const [bnWatchlistSymbols, setBnWatchlistSymbols] = useState<string[]>([])
  const [bnMaxSymbols, setBnMaxSymbols] = useState(10)
  const [bnLoading, setBnLoading] = useState(true)
  const [bnSaving, setBnSaving] = useState(false)
  const [bnError, setBnError] = useState<string | null>(null)
  const [bnSuccess, setBnSuccess] = useState<string | null>(null)
  const [bnSearchQuery, setBnSearchQuery] = useState('')

  // Legacy aliases for compatibility
  const availableSymbols = hlAvailableSymbols
  const watchlistSymbols = hlWatchlistSymbols
  const maxWatchlistSymbols = hlMaxSymbols
  const watchlistLoading = hlLoading
  const watchlistSaving = hlSaving
  const watchlistError = hlError
  const watchlistSuccess = hlSuccess

  // Storage stats state - per exchange
  const [storageStats, setStorageStats] = useState<Record<string, StorageStats>>({})
  const [storageLoading, setStorageLoading] = useState(false)
  const [retentionDays, setRetentionDays] = useState<Record<string, string>>({
    hyperliquid: '365',
    binance: '365',
  })
  const [retentionSaving, setRetentionSaving] = useState(false)
  const [retentionError, setRetentionError] = useState<string | null>(null)
  const [retentionSuccess, setRetentionSuccess] = useState<string | null>(null)

  // Backfill state - per exchange
  const [backfillStatus, setBackfillStatus] = useState<Record<string, {
    status: string
    progress: number
    task_id?: number
    symbols?: string[]
    error_message?: string
  }>>({})
  const [backfillStarting, setBackfillStarting] = useState<Record<string, boolean>>({})
  // Track if we just completed a backfill (for one-time success message)
  const [backfillJustCompleted, setBackfillJustCompleted] = useState<Record<string, boolean>>({})

  // News sources state
  const [newsSources, setNewsSources] = useState<NewsSourceConfig[]>([])
  const [newsSourcesSnapshot, setNewsSourcesSnapshot] = useState('[]')
  const [newsStats, setNewsStats] = useState<NewsStatsResponse | null>(null)
  const [newsLoading, setNewsLoading] = useState(false)
  const [newsSaving, setNewsSaving] = useState(false)
  const [newsError, setNewsError] = useState<string | null>(null)
  const [newsSuccess, setNewsSuccess] = useState<string | null>(null)
  const [newsFormAdapter, setNewsFormAdapter] = useState<'rss_generic' | 'cryptopanic' | 'finnhub_calendar'>('rss_generic')
  const [newsTestUrl, setNewsTestUrl] = useState('')
  const [newsFormInterval, setNewsFormInterval] = useState('300')
  const [newsFormAuthToken, setNewsFormAuthToken] = useState('')
  const [newsFormApiKey, setNewsFormApiKey] = useState('')
  const [newsTesting, setNewsTesting] = useState(false)
  const [newsTestError, setNewsTestError] = useState<string | null>(null)
  const [newsTestResult, setNewsTestResult] = useState<TestNewsSourceResponse | null>(null)

  // Admin user management state
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [adminUsersLoading, setAdminUsersLoading] = useState(false)
  const [adminUsersError, setAdminUsersError] = useState<string | null>(null)
  const [adminUsersSuccess, setAdminUsersSuccess] = useState<string | null>(null)
  const [adminRoleSaving, setAdminRoleSaving] = useState<Record<number, boolean>>({})
  const [adminAuditLogs, setAdminAuditLogs] = useState<AdminAuditLog[]>([])
  const [adminAuditLoading, setAdminAuditLoading] = useState(false)
  const [adminAuditError, setAdminAuditError] = useState<string | null>(null)
  const [aiRuntimeStats, setAiRuntimeStats] = useState<AiRuntimeStats | null>(null)
  const [aiRuntimeLoading, setAiRuntimeLoading] = useState(false)
  const [aiRuntimeError, setAiRuntimeError] = useState<string | null>(null)
  const [aiTradingReadiness, setAiTradingReadiness] = useState<AiTradingProductionReadiness | null>(null)
  const [aiTradingReadinessLoading, setAiTradingReadinessLoading] = useState(false)
  const [aiTradingReadinessError, setAiTradingReadinessError] = useState<string | null>(null)
  const [aiTradingEvidenceExplain, setAiTradingEvidenceExplain] =
    useState<AiTradingProductionEvidenceExplainView | null>(null)
  const [aiTradingEvidenceExplainLoading, setAiTradingEvidenceExplainLoading] = useState(false)
  const [aiTradingEvidenceExplainError, setAiTradingEvidenceExplainError] = useState<string | null>(null)
  const [aiTradingEvidenceValidationJson, setAiTradingEvidenceValidationJson] = useState('')
  const [aiTradingEvidenceValidation, setAiTradingEvidenceValidation] =
    useState<AiTradingProductionEvidenceExplainView | null>(null)
  const [aiTradingEvidenceValidationLoading, setAiTradingEvidenceValidationLoading] = useState(false)
  const [aiTradingEvidenceValidationError, setAiTradingEvidenceValidationError] = useState<string | null>(null)
  const [aiTradingEvidenceTemplateLoading, setAiTradingEvidenceTemplateLoading] = useState(false)
  const [aiTradingEvidenceTemplateGuidance, setAiTradingEvidenceTemplateGuidance] =
    useState<AiTradingProductionEvidenceTemplateGuidanceView | null>(null)

  // Determine current exchange from active tab
  const currentExchange = activeTab === 'hyperliquid-data' ? 'hyperliquid' : activeTab === 'binance-data' ? 'binance' : null
  const canManageUsers = authUser?.role === 'admin' || authUser?.role === 'operator' || authUser?.isAdmin || authUser?.isGlobalAdmin

  const toggleLanguage = (lang: 'en' | 'zh') => {
    i18n.changeLanguage(lang)
    // Sync language to backend for Bot integration
    authFetch('/api/config/ui_language', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: lang }),
    }).catch(() => {})
  }

  const fetchWatchlist = useCallback(async () => {
    setHlLoading(true)
    setBnLoading(true)
    setHlError(null)
    setBnError(null)
    try {
      // Fetch both Hyperliquid and Binance data in parallel
      const [hlAvailable, hlWatchlist, bnAvailable, bnWatchlist] = await Promise.all([
        getHyperliquidAvailableSymbols(),
        getHyperliquidWatchlist(),
        getBinanceAvailableSymbols(),
        getBinanceWatchlist(),
      ])
      setHlAvailableSymbols(hlAvailable.symbols || [])
      setHlMaxSymbols(hlWatchlist.max_symbols ?? 10)
      setHlWatchlistSymbols(hlWatchlist.symbols || [])
      setBnAvailableSymbols(bnAvailable.symbols || [])
      setBnMaxSymbols(bnWatchlist.max_symbols ?? 10)
      setBnWatchlistSymbols(bnWatchlist.symbols || [])
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load watchlist'
      setHlError(errorMsg)
      setBnError(errorMsg)
    } finally {
      setHlLoading(false)
      setBnLoading(false)
    }
  }, [])

  const fetchStorageStats = useCallback(async (exchange: string) => {
    setStorageLoading(true)
    try {
      const res = await authFetch(`/api/system/storage-stats?exchange=${exchange}`)
      if (res.ok) {
        const data: StorageStats = await res.json()
        setStorageStats((prev) => ({ ...prev, [exchange]: data }))
        setRetentionDays((prev) => ({ ...prev, [exchange]: data.retention_days.toString() }))
      }
    } catch (err) {
      console.error('Failed to fetch storage stats:', err)
    } finally {
      setStorageLoading(false)
    }
  }, [])

  const fetchNewsSourcesData = useCallback(async () => {
    setNewsLoading(true)
    setNewsError(null)
    try {
      const [sourcesRes, statsRes] = await Promise.all([
        getNewsSources(),
        getNewsStats(),
      ])
      const nextSources = sourcesRes.sources || []
      setNewsSources(nextSources)
      setNewsSourcesSnapshot(JSON.stringify(nextSources))
      setNewsStats(statsRes)
    } catch (err) {
      setNewsError(err instanceof Error ? err.message : 'Failed to load news sources')
    } finally {
      setNewsLoading(false)
    }
  }, [])

  // Load watchlist on mount
  useEffect(() => {
    fetchWatchlist()
  }, [fetchWatchlist])

  // Load storage stats when exchange data tab is active
  useEffect(() => {
    if (currentExchange && !storageStats[currentExchange]) {
      fetchStorageStats(currentExchange)
    }
  }, [currentExchange, storageStats, fetchStorageStats])

  useEffect(() => {
    if (activeTab === 'news-sources' && !newsLoading && !newsStats && newsSources.length === 0) {
      fetchNewsSourcesData()
    }
  }, [activeTab, newsLoading, newsStats, newsSources.length, fetchNewsSourcesData])

  const fetchAdminUsers = useCallback(async () => {
    setAdminUsersLoading(true)
    setAdminUsersError(null)
    try {
      const res = await authFetch('/api/users/admin/users')
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to load users')
      }
      const data: AdminUser[] = await res.json()
      setAdminUsers(data)
    } catch (err) {
      setAdminUsersError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setAdminUsersLoading(false)
    }
  }, [])

  const fetchAdminAuditLogs = useCallback(async () => {
    setAdminAuditLoading(true)
    setAdminAuditError(null)
    try {
      const res = await authFetch('/api/users/admin/audit-logs?limit=20')
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to load audit logs')
      }
      const data: AdminAuditLog[] = await res.json()
      setAdminAuditLogs(data)
    } catch (err) {
      setAdminAuditError(err instanceof Error ? err.message : 'Failed to load audit logs')
    } finally {
      setAdminAuditLoading(false)
    }
  }, [])

  const fetchAiRuntimeStats = useCallback(async () => {
    setAiRuntimeLoading(true)
    setAiRuntimeError(null)
    try {
      const res = await authFetch('/api/ai-stream/admin/runtime')
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to load AI runtime')
      }
      const data: AiRuntimeStats = await res.json()
      setAiRuntimeStats(data)
    } catch (err) {
      setAiRuntimeError(err instanceof Error ? err.message : 'Failed to load AI runtime')
    } finally {
      setAiRuntimeLoading(false)
    }
  }, [])

  const fetchAiTradingReadiness = useCallback(async () => {
    setAiTradingReadinessLoading(true)
    setAiTradingReadinessError(null)
    try {
      const res = await authFetch('/api/ai-trading/admin/production-readiness')
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to load AI Trading readiness')
      }
      setAiTradingReadiness(data.readiness || null)
    } catch (err) {
      setAiTradingReadinessError(err instanceof Error ? err.message : 'Failed to load AI Trading readiness')
    } finally {
      setAiTradingReadinessLoading(false)
    }
  }, [])

  const fetchAiTradingEvidenceExplain = useCallback(async () => {
    setAiTradingEvidenceExplainLoading(true)
    setAiTradingEvidenceExplainError(null)
    try {
      const res = await authFetch('/api/ai-trading/admin/production-evidence-explain')
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to load AI Trading production evidence checklist')
      }
      setAiTradingEvidenceExplain(extractAiTradingProductionEvidenceExplain(data.explain) || null)
    } catch (err) {
      setAiTradingEvidenceExplainError(
        err instanceof Error ? err.message : 'Failed to load AI Trading production evidence checklist'
      )
    } finally {
      setAiTradingEvidenceExplainLoading(false)
    }
  }, [])

  const validateAiTradingEvidence = useCallback(async () => {
    const trimmed = aiTradingEvidenceValidationJson.trim()
    setAiTradingEvidenceValidationError(null)
    setAiTradingEvidenceValidation(null)
    if (!trimmed) {
      setAiTradingEvidenceValidationError(
        t('settings.aiTradingEvidenceValidationRequired', 'Paste evidence JSON before validating')
      )
      return
    }
    if (trimmed.length > AI_TRADING_EVIDENCE_MAX_JSON_CHARS) {
      setAiTradingEvidenceValidationError(
        t('settings.aiTradingEvidenceValidationTooLarge', 'Evidence JSON is too large for dry-run validation')
      )
      return
    }

    let parsedEvidence: unknown
    try {
      parsedEvidence = JSON.parse(trimmed)
    } catch {
      setAiTradingEvidenceValidationError(
        t('settings.aiTradingEvidenceValidationInvalidJson', 'Evidence JSON is not valid')
      )
      return
    }

    setAiTradingEvidenceValidationLoading(true)
    try {
      const res = await authFetch('/api/ai-trading/admin/production-evidence-validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evidence: parsedEvidence }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to validate AI Trading production evidence')
      }
      setAiTradingEvidenceValidation(extractAiTradingProductionEvidenceExplain(data.validation) || null)
      setAiTradingEvidenceTemplateGuidance(
        extractAiTradingProductionEvidenceTemplateGuidance(data.guidance) || null
      )
    } catch (err) {
      setAiTradingEvidenceValidationError(
        err instanceof Error ? err.message : 'Failed to validate AI Trading production evidence'
      )
    } finally {
      setAiTradingEvidenceValidationLoading(false)
    }
  }, [aiTradingEvidenceValidationJson, t])

  const loadAiTradingEvidenceTemplate = useCallback(async () => {
    setAiTradingEvidenceTemplateLoading(true)
    setAiTradingEvidenceValidationError(null)
    setAiTradingEvidenceValidation(null)
    try {
      const res = await authFetch('/api/ai-trading/admin/production-evidence-template')
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to load AI Trading production evidence template')
      }
      setAiTradingEvidenceValidationJson(JSON.stringify(data.template || {}, null, 2))
      setAiTradingEvidenceTemplateGuidance(
        extractAiTradingProductionEvidenceTemplateGuidance(data.guidance) || null
      )
    } catch (err) {
      setAiTradingEvidenceValidationError(
        err instanceof Error ? err.message : 'Failed to load AI Trading production evidence template'
      )
    } finally {
      setAiTradingEvidenceTemplateLoading(false)
    }
  }, [])

  const fetchAdminData = useCallback(async () => {
    await Promise.all([
      fetchAdminUsers(),
      fetchAdminAuditLogs(),
      fetchAiRuntimeStats(),
      fetchAiTradingReadiness(),
      fetchAiTradingEvidenceExplain(),
    ])
  }, [
    fetchAdminAuditLogs,
    fetchAdminUsers,
    fetchAiRuntimeStats,
    fetchAiTradingEvidenceExplain,
    fetchAiTradingReadiness,
  ])

  useEffect(() => {
    if (
      activeTab === 'admin-users'
      && canManageUsers
      && adminUsers.length === 0
      && adminAuditLogs.length === 0
      && !aiRuntimeStats
      && !aiTradingReadiness
      && !aiTradingEvidenceExplain
      && !adminUsersLoading
      && !adminAuditLoading
      && !aiRuntimeLoading
      && !aiTradingReadinessLoading
      && !aiTradingEvidenceExplainLoading
    ) {
      fetchAdminData()
    }
  }, [
    activeTab,
    adminAuditLoading,
    adminAuditLogs.length,
    adminUsers.length,
    adminUsersLoading,
    aiTradingEvidenceExplain,
    aiTradingEvidenceExplainLoading,
    aiTradingReadiness,
    aiTradingReadinessLoading,
    aiRuntimeLoading,
    aiRuntimeStats,
    canManageUsers,
    fetchAdminData,
  ])

  useEffect(() => {
    if (activeTab === 'admin-users' && !canManageUsers) {
      setActiveTab('watchlist')
    }
  }, [activeTab, canManageUsers])

  // Fetch backfill status for an exchange
  const fetchBackfillStatus = useCallback(async (exchange: string) => {
    try {
      const res = await authFetch(`/api/system/${exchange}/backfill/status`)
      if (res.ok) {
        const data = await res.json()
        setBackfillStatus(prev => {
          const prevStatus = prev[exchange]?.status
          // Track completion for one-time message
          if ((prevStatus === 'running' || prevStatus === 'pending') && data.status === 'completed') {
            setBackfillJustCompleted(p => ({ ...p, [exchange]: true }))
          }
          return { ...prev, [exchange]: data }
        })
      }
    } catch (err) {
      console.error(`Failed to fetch ${exchange} backfill status:`, err)
    }
  }, [])

  // Use ref to track if polling should continue
  const pollingRef = useRef<Record<string, boolean>>({})

  useEffect(() => {
    if (currentExchange) {
      // Initial fetch
      fetchBackfillStatus(currentExchange)
      pollingRef.current[currentExchange] = true

      // Poll while running - use functional update to get latest status
      const interval = setInterval(async () => {
        const res = await authFetch(`/api/system/${currentExchange}/backfill/status`)
        if (res.ok) {
          const data = await res.json()
          setBackfillStatus(prev => {
            const prevStatus = prev[currentExchange]?.status
            // Track completion for one-time message
            if ((prevStatus === 'running' || prevStatus === 'pending') && data.status === 'completed') {
              setBackfillJustCompleted(p => ({ ...p, [currentExchange]: true }))
            }
            return { ...prev, [currentExchange]: data }
          })
          // Stop polling if completed or failed
          if (data.status !== 'running' && data.status !== 'pending') {
            pollingRef.current[currentExchange] = false
          }
        }
      }, 2000)

      return () => {
        clearInterval(interval)
        pollingRef.current[currentExchange] = false
      }
    }
  }, [activeTab, currentExchange, fetchBackfillStatus])

  const handleStartBackfill = async (exchange: string, force: boolean = false) => {
    setBackfillStarting(prev => ({ ...prev, [exchange]: true }))
    setBackfillJustCompleted(prev => ({ ...prev, [exchange]: false }))
    try {
      const url = force
        ? `/api/system/${exchange}/backfill?force=true`
        : `/api/system/${exchange}/backfill`
      const res = await authFetch(url, { method: 'POST' })
      if (res.ok) {
        await fetchBackfillStatus(exchange)
      } else {
        const data = await res.json()
        alert(data.detail || 'Failed to start backfill')
      }
    } catch (err) {
      console.error('Failed to start backfill:', err)
    } finally {
      setBackfillStarting(prev => ({ ...prev, [exchange]: false }))
    }
  }

  const toggleWatchlistSymbol = (symbol: string) => {
    const symbolUpper = symbol.toUpperCase()
    setHlError(null)
    setHlSuccess(null)
    setHlWatchlistSymbols((prev) => {
      if (prev.includes(symbolUpper)) {
        return prev.filter((s) => s !== symbolUpper)
      }
      if (prev.length >= hlMaxSymbols) {
        setHlError(t('settings.maxSymbolsReached', `Maximum ${hlMaxSymbols} symbols`))
        return prev
      }
      return [...prev, symbolUpper]
    })
  }

  const toggleBnWatchlistSymbol = (symbol: string) => {
    const symbolUpper = symbol.toUpperCase()
    setBnError(null)
    setBnSuccess(null)
    setBnWatchlistSymbols((prev) => {
      if (prev.includes(symbolUpper)) {
        return prev.filter((s) => s !== symbolUpper)
      }
      if (prev.length >= bnMaxSymbols) {
        setBnError(t('settings.maxSymbolsReached', `Maximum ${bnMaxSymbols} symbols`))
        return prev
      }
      return [...prev, symbolUpper]
    })
  }

  const handleSaveWatchlist = async () => {
    setHlSaving(true)
    setHlError(null)
    setHlSuccess(null)
    try {
      await updateHyperliquidWatchlist(hlWatchlistSymbols)
      setHlSuccess(t('settings.watchlistSaved', 'Watchlist saved'))
    } catch (err) {
      setHlError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setHlSaving(false)
    }
  }

  const handleSaveBnWatchlist = async () => {
    setBnSaving(true)
    setBnError(null)
    setBnSuccess(null)
    try {
      await updateBinanceWatchlist(bnWatchlistSymbols)
      setBnSuccess(t('settings.watchlistSaved', 'Watchlist saved'))
    } catch (err) {
      setBnError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setBnSaving(false)
    }
  }

  // Filtered symbols for search
  const filteredHlSymbols = useMemo(() => {
    if (!hlSearchQuery.trim()) return hlAvailableSymbols
    const query = hlSearchQuery.toUpperCase()
    return hlAvailableSymbols.filter((sym) =>
      sym.name?.toUpperCase().includes(query) || sym.symbol?.toUpperCase().includes(query)
    )
  }, [hlAvailableSymbols, hlSearchQuery])

  const filteredBnSymbols = useMemo(() => {
    if (!bnSearchQuery.trim()) return bnAvailableSymbols
    const query = bnSearchQuery.toUpperCase()
    return bnAvailableSymbols.filter((sym) =>
      sym.name?.toUpperCase().includes(query) || sym.symbol?.toUpperCase().includes(query)
    )
  }, [bnAvailableSymbols, bnSearchQuery])

  const handleSaveRetention = async () => {
    if (!currentExchange) return
    const days = parseInt(retentionDays[currentExchange], 10)
    if (isNaN(days) || days < 7 || days > 730) {
      setRetentionError(t('settings.retentionRange', 'Must be between 7 and 730 days'))
      return
    }
    setRetentionSaving(true)
    setRetentionError(null)
    setRetentionSuccess(null)
    try {
      const res = await authFetch('/api/system/retention-days', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days, exchange: currentExchange }),
      })
      if (!res.ok) throw new Error('Failed to update')
      setRetentionSuccess(t('settings.retentionSaved', 'Retention updated'))
      const stats = storageStats[currentExchange]
      if (stats) {
        setStorageStats((prev) => ({
          ...prev,
          [currentExchange]: { ...stats, retention_days: days },
        }))
      }
    } catch (err) {
      setRetentionError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setRetentionSaving(false)
    }
  }

  const enabledNewsSourceCount = useMemo(
    () => newsSources.filter((source) => source.enabled).length,
    [newsSources]
  )

  const hasUnsavedNewsSources = useMemo(
    () => JSON.stringify(newsSources) !== newsSourcesSnapshot,
    [newsSources, newsSourcesSnapshot]
  )

  const newsCountsByDomain = useMemo(() => {
    return Object.entries(newsStats?.last_24h?.by_domain || {}).reduce<Record<string, number>>((acc, [domain, count]) => {
      const normalizedDomain = domain.replace(/^www\./, '')
      acc[normalizedDomain] = (acc[normalizedDomain] || 0) + count
      return acc
    }, {})
  }, [newsStats])

  const extractDomain = (url: string) => {
    try {
      return new URL(url).hostname.replace(/^www\./, '')
    } catch {
      return url
    }
  }

  const formatDateTime = (value?: string | null) => {
    if (!value) return t('settings.notAvailable', 'N/A')
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return t('settings.notAvailable', 'N/A')
    return date.toLocaleString(currentLang === 'zh' ? 'zh-CN' : 'en-US')
  }

  const getAdminRoleBadgeVariant = (role: string): 'default' | 'secondary' | 'outline' => {
    if (role === 'admin') return 'default'
    if (role === 'operator') return 'secondary'
    return 'outline'
  }

  const getReadinessBadgeVariant = (ready: boolean): 'default' | 'destructive' => {
    return ready ? 'default' : 'destructive'
  }

  const formatReadinessComponentName = (component: string) => {
    const labels: Record<string, string> = {
      auth: t('settings.aiTradingReadinessAuth', 'Auth'),
      signal_handoff: t('settings.aiTradingReadinessSignalHandoff', 'Signal Handoff'),
      ai_stream: t('settings.aiTradingReadinessAiStream', 'AI Stream'),
      hard_risk: t('settings.aiTradingReadinessHardRisk', 'Hard Risk'),
      model_policy: t('settings.aiTradingReadinessModelPolicy', 'Model Policy'),
      handoff_audit: t('settings.aiTradingReadinessHandoffAudit', 'Handoff Audit'),
      agent_session_context: t('settings.aiTradingReadinessAgentContext', 'Agent Context'),
    }
    return labels[component] || component.replace(/_/g, ' ')
  }

  const formatReadinessCode = (code: string) => {
    const labels: Record<string, string> = {
      'handoff_audit:handoff_attempt_failed_present': t(
        'settings.aiTradingReadinessHandoffFailedPresent',
        'Failed handoff attempts present'
      ),
      'handoff_audit:handoff_attempt_blocked_present': t(
        'settings.aiTradingReadinessHandoffBlockedPresent',
        'Blocked handoff attempts present'
      ),
      'agent_session_context:agent_session_context_over_budget_present': t(
        'settings.aiTradingReadinessAgentContextOverBudget',
        'Agent context summary over budget'
      ),
      'agent_session_context:agent_session_context_near_budget_present': t(
        'settings.aiTradingReadinessAgentContextNearBudget',
        'Agent context summary near budget'
      ),
      'agent_session_context:agent_session_context_redacted_present': t(
        'settings.aiTradingReadinessAgentContextRedacted',
        'Redacted agent context present'
      ),
      'agent_session_context:agent_session_context_sensitive_present': t(
        'settings.aiTradingReadinessAgentContextSensitive',
        'Sensitive-looking agent context present'
      ),
      handoff_attempt_failed_present: t(
        'settings.aiTradingReadinessHandoffFailedPresent',
        'Failed handoff attempts present'
      ),
      handoff_attempt_blocked_present: t(
        'settings.aiTradingReadinessHandoffBlockedPresent',
        'Blocked handoff attempts present'
      ),
      agent_session_context_over_budget_present: t(
        'settings.aiTradingReadinessAgentContextOverBudget',
        'Agent context summary over budget'
      ),
      agent_session_context_near_budget_present: t(
        'settings.aiTradingReadinessAgentContextNearBudget',
        'Agent context summary near budget'
      ),
      agent_session_context_redacted_present: t(
        'settings.aiTradingReadinessAgentContextRedacted',
        'Redacted agent context present'
      ),
      agent_session_context_sensitive_present: t(
        'settings.aiTradingReadinessAgentContextSensitive',
        'Sensitive-looking agent context present'
      ),
    }
    return labels[code] || code.replace(/_/g, ' ')
  }

  const formatProductionEvidenceItemName = (id: string) => {
    const labels: Record<string, string> = {
      macos_reboot_recovery: t('settings.aiTradingEvidenceMacosReboot', 'macOS reboot recovery'),
      real_model_profile_live_acceptance: t('settings.aiTradingEvidenceModelProfile', 'Live model profile'),
      real_order_backend_handoff: t('settings.aiTradingEvidenceOrderBackend', 'Order backend handoff'),
      production_auth_hard_risk_readiness: t('settings.aiTradingEvidenceAuthRisk', 'Auth and hard risk'),
      admin_readiness_real_auth_visual: t('settings.aiTradingEvidenceAdminVisual', 'Admin readiness visual'),
      production_agent_session_visual: t('settings.aiTradingEvidenceSessionVisual', 'Agent session visual'),
      real_exchange_execution: t('settings.aiTradingEvidenceExchangeExecution', 'Exchange execution'),
    }
    return labels[id] || id.replace(/_/g, ' ')
  }

  const getAgentContextLocators = (report: AiTradingProductionComponent): AiTradingAgentContextLocatorView[] => {
    const locatorMeta: AiTradingAgentContextLocatorMeta[] = [
      {
        key: 'latest_over_budget',
        label: t('settings.aiTradingReadinessLatestOverBudget', 'Latest over-budget'),
        tone: 'text-red-500',
      },
      {
        key: 'latest_redacted_context',
        label: t('settings.aiTradingReadinessLatestRedacted', 'Latest redacted'),
        tone: 'text-amber-600',
      },
      {
        key: 'latest_sensitive_context',
        label: t('settings.aiTradingReadinessLatestSensitive', 'Latest sensitive-looking'),
        tone: 'text-amber-600',
      },
    ]
    return extractAiTradingAgentContextLocators(report, locatorMeta)
  }

  const handleToggleNewsSource = (index: number, enabled: boolean) => {
    setNewsError(null)
    setNewsSuccess(null)
    setNewsSources((prev) => prev.map((source, sourceIndex) => (
      sourceIndex === index ? { ...source, enabled } : source
    )))
  }

  const handleSaveNewsSources = async () => {
    setNewsSaving(true)
    setNewsError(null)
    setNewsSuccess(null)
    try {
      const result = await updateNewsSources(newsSources)
      setNewsSources(result.sources || [])
      setNewsSourcesSnapshot(JSON.stringify(result.sources || []))
      setNewsSuccess(t('settings.newsSourcesSaved', 'News sources saved'))
      const stats = await getNewsStats()
      setNewsStats(stats)
    } catch (err) {
      setNewsError(err instanceof Error ? err.message : 'Failed to save news sources')
    } finally {
      setNewsSaving(false)
    }
  }

  const buildNewsSourceConfig = (
    adapter: 'rss_generic' | 'cryptopanic' | 'finnhub_calendar',
    url: string
  ) => {
    const interval = parseInt(newsFormInterval, 10)
    const intervalSeconds = Number.isFinite(interval) && interval > 0 ? interval : 300

    const config: Record<string, any> = {}
    if (adapter === 'cryptopanic' && newsFormAuthToken.trim()) {
      config.auth_token = newsFormAuthToken.trim()
    }
    if (adapter === 'finnhub_calendar' && newsFormApiKey.trim()) {
      config.api_key = newsFormApiKey.trim()
    }

    return {
      type: adapter === 'rss_generic' ? 'rss' : 'api',
      adapter,
      url,
      enabled: true,
      interval_seconds: intervalSeconds,
      config,
    } satisfies NewsSourceConfig
  }

  const handleTestNewsSource = async () => {
    const trimmedUrl = newsTestUrl.trim()
    if (!trimmedUrl) {
      setNewsTestError(t('settings.newsSourceUrlRequired', 'Please enter a source URL'))
      setNewsTestResult(null)
      return
    }

    try {
      new URL(trimmedUrl)
    } catch {
      setNewsTestError(t('settings.newsSourceUrlInvalid', 'Please enter a valid URL'))
      setNewsTestResult(null)
      return
    }

    const interval = parseInt(newsFormInterval, 10)
    if (!Number.isFinite(interval) || interval < 10) {
      setNewsTestError(t('settings.newsSourceIntervalInvalid', 'Interval must be at least 10 seconds'))
      setNewsTestResult(null)
      return
    }

    if (newsFormAdapter === 'cryptopanic' && !newsFormAuthToken.trim()) {
      setNewsTestError(t('settings.newsSourceAuthTokenRequired', 'Please enter a CryptoPanic auth token'))
      setNewsTestResult(null)
      return
    }

    if (newsFormAdapter === 'finnhub_calendar' && !newsFormApiKey.trim()) {
      setNewsTestError(t('settings.newsSourceApiKeyRequired', 'Please enter a Finnhub API key'))
      setNewsTestResult(null)
      return
    }

    setNewsTesting(true)
    setNewsTestError(null)
    setNewsTestResult(null)
    setNewsSuccess(null)

    try {
      const sourceConfig = buildNewsSourceConfig(newsFormAdapter, trimmedUrl)
      const result = await testNewsSource({
        url: trimmedUrl,
        adapter: newsFormAdapter,
        config: sourceConfig.config || {},
      })
      setNewsTestResult(result)
      if (!result.success) {
        setNewsTestError(result.error || t('settings.newsSourceTestFailed', 'Test failed'))
      }
    } catch (err) {
      setNewsTestError(err instanceof Error ? err.message : 'Failed to test source')
    } finally {
      setNewsTesting(false)
    }
  }

  const handleAddNewsSource = () => {
    const trimmedUrl = newsTestUrl.trim()
    if (!newsTestResult?.success || !trimmedUrl) {
      return
    }

    if (newsSources.some((source) => source.url === trimmedUrl)) {
      setNewsTestError(t('settings.newsSourceDuplicate', 'This source already exists'))
      return
    }

    const nextSources = [...newsSources, buildNewsSourceConfig(newsFormAdapter, trimmedUrl)]

    setNewsSources(nextSources)
    setNewsFormAdapter('rss_generic')
    setNewsTestUrl('')
    setNewsFormInterval('300')
    setNewsFormAuthToken('')
    setNewsFormApiKey('')
    setNewsTestError(null)
    setNewsTestResult(null)
    setNewsSuccess(t('settings.newsSourceAdded', 'Source added to the list. Save to apply.'))
  }

  const handleNewsSourceIntervalChange = (index: number, value: string) => {
    setNewsError(null)
    setNewsSuccess(null)
    setNewsSources((prev) => prev.map((source, sourceIndex) => {
      if (sourceIndex !== index) return source
      const parsed = parseInt(value, 10)
      return {
        ...source,
        interval_seconds: Number.isFinite(parsed) && parsed > 0 ? parsed : source.interval_seconds,
      }
    }))
  }

  const handleUpdateAdminRole = async (userId: number, role: AdminUser['role']) => {
    setAdminRoleSaving(prev => ({ ...prev, [userId]: true }))
    setAdminUsersError(null)
    setAdminUsersSuccess(null)
    try {
      const res = await authFetch(`/api/users/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to update role')
      }
      const updated: AdminUser = await res.json()
      setAdminUsers(prev => prev.map(user => user.id === userId ? updated : user))
      if (authUser?.localUserId === updated.id) {
        const hasAdminRole = updated.role === 'admin' || updated.role === 'operator'
        setAuthUser({
          ...authUser,
          role: updated.role,
          isAdmin: hasAdminRole,
        })
      }
      await fetchAdminAuditLogs()
      setAdminUsersSuccess(t('settings.adminRoleSaved', 'Role updated'))
    } catch (err) {
      setAdminUsersError(err instanceof Error ? err.message : 'Failed to update role')
    } finally {
      setAdminRoleSaving(prev => ({ ...prev, [userId]: false }))
    }
  }

  const aiEffectiveRunningTasks = aiRuntimeStats?.effective_running_tasks ?? aiRuntimeStats?.running_tasks ?? 0
  const aiRemoteRunningTasks = aiRuntimeStats?.remote_running_tasks ?? 0
  const aiTradingReadinessComponents = Object.entries(aiTradingReadiness?.checks || {})

  return (
    <div className="p-6 h-[calc(100vh-64px)] flex flex-col overflow-hidden">
      {/* Language Settings - Compact row with border */}
      <div className="flex items-center gap-3 mb-6 shrink-0 p-4 border rounded-lg bg-card">
        <span className="text-sm font-medium">{t('settings.language', 'Language')}</span>
        <select
          value={currentLang}
          onChange={(e) => toggleLanguage(e.target.value as 'en' | 'zh')}
          className="border rounded px-2 py-1 text-sm bg-background"
        >
          <option value="en">English</option>
          <option value="zh">中文</option>
        </select>
      </div>

      {/* Tabs: Watchlist | Hyperliquid Data | Binance Data | News Sources | Admin */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
        <TabsList className={`grid w-full shrink-0 ${canManageUsers ? 'grid-cols-5 max-w-4xl' : 'grid-cols-4 max-w-3xl'}`}>
          <TabsTrigger value="watchlist">{t('settings.watchlist', 'Watchlist')}</TabsTrigger>
          <TabsTrigger value="hyperliquid-data" className="flex items-center gap-1.5">
            <ExchangeIcon exchangeId="hyperliquid" size={16} />
            Hyperliquid
          </TabsTrigger>
          <TabsTrigger value="binance-data" className="flex items-center gap-1.5">
            <ExchangeIcon exchangeId="binance" size={16} />
            Binance
          </TabsTrigger>
          <TabsTrigger value="news-sources">{t('settings.newsSources', 'News Sources')}</TabsTrigger>
          {canManageUsers && (
            <TabsTrigger value="admin-users">{t('settings.adminUsers', 'Admin')}</TabsTrigger>
          )}
        </TabsList>

        {/* Watchlist Tab */}
        <TabsContent value="watchlist" className="mt-4 flex-1 min-h-0 flex flex-col overflow-auto">
          <div className="space-y-6">
            {/* Hyperliquid Watchlist */}
            <Card>
              <CardHeader className="shrink-0 pb-3">
                <div className="flex items-center gap-2">
                  <ExchangeIcon exchangeId="hyperliquid" size={24} />
                  <CardTitle className="text-base">Hyperliquid</CardTitle>
                </div>
                <CardDescription className="text-xs">
                  {t('settings.selectedCount', 'Selected')}: {hlWatchlistSymbols.length} / {hlMaxSymbols}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                {hlLoading ? (
                  <div className="text-muted-foreground text-sm">{t('common.loading', 'Loading...')}</div>
                ) : (
                  <>
                    {/* Search input */}
                    <div className="mb-3">
                      <Input
                        type="text"
                        placeholder={t('settings.searchSymbol', 'Search symbol...')}
                        value={hlSearchQuery}
                        onChange={(e) => setHlSearchQuery(e.target.value)}
                        className="h-8 text-sm"
                      />
                    </div>
                    <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto">
                      {filteredHlSymbols.map((sym) => {
                        const symbolName = sym.name || sym.symbol || ''
                        const isSelected = hlWatchlistSymbols.includes(symbolName.toUpperCase())
                        return (
                          <Button
                            key={symbolName}
                            variant={isSelected ? 'default' : 'outline'}
                            size="sm"
                            className="h-7 px-2 text-xs gap-1.5"
                            onClick={() => toggleWatchlistSymbol(symbolName)}
                          >
                            <CoinIcon symbol={symbolName} size={14} />
                            {symbolName}
                          </Button>
                        )
                      })}
                    </div>
                  </>
                )}
              </CardContent>
              <CardFooter className="shrink-0 border-t pt-3 flex items-center gap-3">
                <Button
                  size="sm"
                  onClick={handleSaveWatchlist}
                  disabled={hlSaving || hlLoading}
                >
                  {hlSaving ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
                </Button>
                {hlError && <span className="text-red-500 text-xs">{hlError}</span>}
                {hlSuccess && <span className="text-green-500 text-xs">{hlSuccess}</span>}
              </CardFooter>
            </Card>

            {/* Binance Watchlist */}
            <Card>
              <CardHeader className="shrink-0 pb-3">
                <div className="flex items-center gap-2">
                  <ExchangeIcon exchangeId="binance" size={24} />
                  <CardTitle className="text-base">Binance</CardTitle>
                </div>
                <CardDescription className="text-xs">
                  {t('settings.selectedCount', 'Selected')}: {bnWatchlistSymbols.length} / {bnMaxSymbols}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                {bnLoading ? (
                  <div className="text-muted-foreground text-sm">{t('common.loading', 'Loading...')}</div>
                ) : (
                  <>
                    {/* Search input */}
                    <div className="mb-3">
                      <Input
                        type="text"
                        placeholder={t('settings.searchSymbol', 'Search symbol...')}
                        value={bnSearchQuery}
                        onChange={(e) => setBnSearchQuery(e.target.value)}
                        className="h-8 text-sm"
                      />
                    </div>
                    <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto">
                      {filteredBnSymbols.map((sym) => {
                        const symbolName = sym.name || sym.symbol || ''
                        const isSelected = bnWatchlistSymbols.includes(symbolName.toUpperCase())
                        return (
                          <Button
                            key={symbolName}
                            variant={isSelected ? 'default' : 'outline'}
                            size="sm"
                            className="h-7 px-2 text-xs gap-1.5"
                            onClick={() => toggleBnWatchlistSymbol(symbolName)}
                          >
                            <CoinIcon symbol={symbolName} size={14} />
                            {symbolName}
                          </Button>
                        )
                      })}
                    </div>
                  </>
                )}
              </CardContent>
              <CardFooter className="shrink-0 border-t pt-3 flex items-center gap-3">
                <Button
                  size="sm"
                  onClick={handleSaveBnWatchlist}
                  disabled={bnSaving || bnLoading}
                >
                  {bnSaving ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
                </Button>
                {bnError && <span className="text-red-500 text-xs">{bnError}</span>}
                {bnSuccess && <span className="text-green-500 text-xs">{bnSuccess}</span>}
              </CardFooter>
            </Card>
          </div>
        </TabsContent>

        {/* Hyperliquid Data Tab */}
        <TabsContent value="hyperliquid-data" className="mt-4 flex-1 min-h-0 flex flex-col">
          <Card className="flex flex-col flex-1 min-h-0">
            <CardHeader className="shrink-0">
              <CardTitle className="flex items-center gap-2">
                <ExchangeIcon exchangeId="hyperliquid" size={24} />
                {t('settings.dataCollection', 'Data Collection')}
              </CardTitle>
              <CardDescription>
                {t('settings.dataCollectionDesc', 'Market flow data storage statistics')}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto min-h-0 space-y-6">
              {storageLoading ? (
                <div className="text-muted-foreground">{t('common.loading', 'Loading...')}</div>
              ) : storageStats['hyperliquid'] ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.currentStorage', 'Current Storage')}
                      </div>
                      <div className="text-xl font-semibold">{storageStats['hyperliquid'].total_size_mb} MB</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.collectedSymbols', 'Collected Symbols')}
                      </div>
                      <div className="text-xl font-semibold">{storageStats['hyperliquid'].symbol_count}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.retentionDays', 'Retention Days')}
                      </div>
                      <div className="text-xl font-semibold">{storageStats['hyperliquid'].retention_days}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.maxStorageEstimate', 'Max Storage Estimate')}
                      </div>
                      <div className="text-xl font-semibold">
                        {(watchlistSymbols.length * parseInt(retentionDays['hyperliquid'] || '365', 10) * storageStats['hyperliquid'].estimated_per_symbol_per_day_mb).toFixed(1)} MB
                      </div>
                    </div>
                  </div>
                  <div className="pt-4 border-t">
                    <div className="text-sm font-medium mb-2">
                      {t('settings.setRetention', 'Set Retention Period')}
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        value={retentionDays['hyperliquid'] || '365'}
                        onChange={(e) => setRetentionDays((prev) => ({ ...prev, hyperliquid: e.target.value }))}
                        className="w-24"
                        min={7}
                        max={730}
                      />
                      <span className="text-sm text-muted-foreground">{t('settings.days', 'days')}</span>
                      <Button onClick={handleSaveRetention} disabled={retentionSaving} size="sm">
                        {retentionSaving ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
                      </Button>
                    </div>
                    {retentionError && <div className="text-red-500 text-sm mt-2">{retentionError}</div>}
                    {retentionSuccess && <div className="text-green-500 text-sm mt-2">{retentionSuccess}</div>}
                    <div className="text-xs text-muted-foreground mt-1">
                      {t('settings.retentionHint', 'Data older than this will be automatically cleaned up (7-730 days)')}
                    </div>
                  </div>
                  {/* Hyperliquid Backfill Section */}
                  <div className="pt-4 border-t">
                    <div className="text-sm font-medium mb-2">
                      {t('settings.backfillHistory', 'Backfill Historical Data')}
                    </div>
                    <div className="text-xs text-muted-foreground mb-3">
                      {t('settings.hyperliquidBackfillDesc', 'K-lines (~5000 records, ~3.5 days per symbol)')}
                    </div>
                    {backfillStatus['hyperliquid']?.status === 'running' || backfillStatus['hyperliquid']?.status === 'pending' ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all duration-300"
                              style={{ width: `${backfillStatus['hyperliquid']?.progress || 0}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{backfillStatus['hyperliquid']?.progress || 0}%</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {t('settings.backfillRunning', 'Backfilling')} {backfillStatus['hyperliquid']?.symbols?.join(', ')}...
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Button
                          onClick={() => handleStartBackfill('hyperliquid')}
                          disabled={backfillStarting['hyperliquid']}
                          size="sm"
                          variant="outline"
                        >
                          {backfillStarting['hyperliquid'] ? t('common.loading', 'Loading...') : t('settings.startBackfill', 'Start Backfill')}
                        </Button>
                        {backfillJustCompleted['hyperliquid'] && (
                          <div className="text-xs text-green-500">
                            {t('settings.backfillCompleted', 'Last backfill completed successfully')}
                          </div>
                        )}
                        {backfillStatus['hyperliquid']?.status === 'failed' && backfillStatus['hyperliquid']?.task_id && (
                          <div className="text-xs text-red-500">
                            {t('settings.backfillFailed', 'Last backfill failed')}: {backfillStatus['hyperliquid']?.error_message}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-muted-foreground">{t('settings.noData', 'No data available')}</div>
              )}
              <div className="pt-4 border-t">
                <div className="text-sm font-medium mb-3">{t('settings.marketFlowCoverage', 'Market Flow Coverage')}</div>
                <DataCoverageHeatmap exchange="hyperliquid" dataType="market_flow" />
              </div>
              <div className="pt-4 border-t">
                <div className="text-sm font-medium mb-3">{t('settings.klineCoverage', 'K-line Coverage')}</div>
                <DataCoverageHeatmap exchange="hyperliquid" dataType="klines" />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Binance Data Tab */}
        <TabsContent value="binance-data" className="mt-4 flex-1 min-h-0 flex flex-col">
          <Card className="flex flex-col flex-1 min-h-0">
            <CardHeader className="shrink-0">
              <CardTitle className="flex items-center gap-2">
                <ExchangeIcon exchangeId="binance" size={24} />
                {t('settings.dataCollection', 'Data Collection')}
              </CardTitle>
              <CardDescription>
                {t('settings.dataCollectionDesc', 'Market flow data storage statistics')}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto min-h-0 space-y-6">
              {storageLoading ? (
                <div className="text-muted-foreground">{t('common.loading', 'Loading...')}</div>
              ) : storageStats['binance'] ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.currentStorage', 'Current Storage')}
                      </div>
                      <div className="text-xl font-semibold">{storageStats['binance'].total_size_mb} MB</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.collectedSymbols', 'Collected Symbols')}
                      </div>
                      <div className="text-xl font-semibold">{storageStats['binance'].symbol_count}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.retentionDays', 'Retention Days')}
                      </div>
                      <div className="text-xl font-semibold">{storageStats['binance'].retention_days}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">
                        {t('settings.maxStorageEstimate', 'Max Storage Estimate')}
                      </div>
                      <div className="text-xl font-semibold">
                        {(watchlistSymbols.length * parseInt(retentionDays['binance'] || '365', 10) * storageStats['binance'].estimated_per_symbol_per_day_mb).toFixed(1)} MB
                      </div>
                    </div>
                  </div>
                  <div className="pt-4 border-t">
                    <div className="text-sm font-medium mb-2">
                      {t('settings.setRetention', 'Set Retention Period')}
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        value={retentionDays['binance'] || '365'}
                        onChange={(e) => setRetentionDays((prev) => ({ ...prev, binance: e.target.value }))}
                        className="w-24"
                        min={7}
                        max={730}
                      />
                      <span className="text-sm text-muted-foreground">{t('settings.days', 'days')}</span>
                      <Button onClick={handleSaveRetention} disabled={retentionSaving} size="sm">
                        {retentionSaving ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
                      </Button>
                    </div>
                    {retentionError && <div className="text-red-500 text-sm mt-2">{retentionError}</div>}
                    {retentionSuccess && <div className="text-green-500 text-sm mt-2">{retentionSuccess}</div>}
                    <div className="text-xs text-muted-foreground mt-1">
                      {t('settings.retentionHint', 'Data older than this will be automatically cleaned up (7-730 days)')}
                    </div>
                  </div>
                  {/* Backfill Section */}
                  <div className="pt-4 border-t">
                    <div className="text-sm font-medium mb-2">
                      {t('settings.backfillHistory', 'Backfill Historical Data')}
                    </div>
                    <div className="text-xs text-muted-foreground mb-3">
                      {t('settings.backfillDesc', 'K-lines (25h), OI (30d), Funding Rate (365d), Long/Short Ratio (30d)')}
                    </div>
                    {backfillStatus['binance']?.status === 'running' || backfillStatus['binance']?.status === 'pending' ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all duration-300"
                              style={{ width: `${backfillStatus['binance']?.progress || 0}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{backfillStatus['binance']?.progress || 0}%</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="text-xs text-muted-foreground">
                            {t('settings.backfillRunning', 'Backfilling')} {backfillStatus['binance']?.symbols?.join(', ')}...
                          </div>
                          <Button
                            onClick={() => handleStartBackfill('binance', true)}
                            disabled={backfillStarting['binance']}
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs"
                          >
                            {t('settings.restartBackfill', 'Restart')}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Button
                          onClick={() => handleStartBackfill('binance')}
                          disabled={backfillStarting['binance']}
                          size="sm"
                          variant="outline"
                        >
                          {backfillStarting['binance'] ? t('common.loading', 'Loading...') : t('settings.startBackfill', 'Start Backfill')}
                        </Button>
                        {backfillJustCompleted['binance'] && (
                          <div className="text-xs text-green-500">
                            {t('settings.backfillCompleted', 'Last backfill completed successfully')}
                          </div>
                        )}
                        {backfillStatus['binance']?.status === 'failed' && backfillStatus['binance']?.task_id && (
                          <div className="text-xs text-red-500">
                            {t('settings.backfillFailed', 'Last backfill failed')}: {backfillStatus['binance']?.error_message}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-muted-foreground">{t('settings.noData', 'No data available')}</div>
              )}
              <div className="pt-4 border-t">
                <div className="text-sm font-medium mb-3">{t('settings.marketFlowCoverage', 'Market Flow Coverage')}</div>
                <DataCoverageHeatmap exchange="binance" dataType="market_flow" />
              </div>
              <div className="pt-4 border-t">
                <div className="text-sm font-medium mb-3">{t('settings.klineCoverage', 'K-line Coverage')}</div>
                <DataCoverageHeatmap exchange="binance" dataType="klines" />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="news-sources" className="mt-4 flex-1 min-h-0 flex flex-col overflow-auto">
          <div className="space-y-6">
            <Card>
              <CardHeader className="shrink-0">
                <CardTitle>{t('settings.newsSources', 'News Sources')}</CardTitle>
                <CardDescription>
                  {t('settings.newsSourcesDesc', 'Manage RSS sources and review collection health')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {newsLoading ? (
                  <div className="text-muted-foreground text-sm">{t('common.loading', 'Loading...')}</div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">
                          {t('settings.newsTotalArticles', 'Total Articles')}
                        </div>
                        <div className="text-xl font-semibold">{newsStats?.total_articles ?? 0}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">
                          {t('settings.newsLast24h', 'New in 24h')}
                        </div>
                        <div className="text-xl font-semibold">{newsStats?.last_24h?.total ?? 0}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">
                          {t('settings.newsEnabledSources', 'Enabled Sources')}
                        </div>
                        <div className="text-xl font-semibold">{enabledNewsSourceCount}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">
                          {t('settings.newsLatestCollected', 'Latest Article')}
                        </div>
                        <div className="text-sm font-medium break-words">
                          {formatDateTime(newsStats?.latest_article_at)}
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 border-t space-y-3">
                      <div className="text-sm font-medium">
                        {t('settings.newsConfiguredSources', 'Configured Sources')}
                      </div>
                      {newsSources.length === 0 ? (
                        <div className="text-sm text-muted-foreground">
                          {t('settings.newsNoSources', 'No news sources configured')}
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {newsSources.map((source, index) => {
                            const domain = extractDomain(source.url)
                            const last24hCount = newsCountsByDomain[domain] ?? 0
                            return (
                              <div
                                key={`${source.url}-${index}`}
                                className="flex flex-col gap-3 rounded-lg border p-3 md:flex-row md:items-center md:justify-between"
                              >
                                <div className="min-w-0 flex-1 space-y-1">
                                  <div className="flex items-center gap-2">
                                    <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                                      {domain}
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                      {t('settings.newsCollected24h', '{{count}} in 24h', { count: last24hCount })}
                                    </span>
                                  </div>
                                  <div className="truncate text-sm text-muted-foreground">
                                    {source.url}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    {t('settings.newsIntervalSeconds', 'Interval')}: {source.interval_seconds}s
                                  </div>
                                </div>
                                <div className="flex items-center gap-3 flex-wrap md:flex-nowrap">
                                  <Input
                                    type="number"
                                    min={10}
                                    className="w-24 h-8 text-xs"
                                    value={source.interval_seconds}
                                    onChange={(e) => handleNewsSourceIntervalChange(index, e.target.value)}
                                  />
                                  <span className="text-xs text-muted-foreground">
                                    {source.enabled
                                      ? t('settings.enabled', 'Enabled')
                                      : t('settings.disabled', 'Disabled')}
                                  </span>
                                  <Switch
                                    checked={source.enabled}
                                    onCheckedChange={(checked) => handleToggleNewsSource(index, checked)}
                                  />
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
              <CardFooter className="border-t pt-3 flex items-center gap-3">
                <Button
                  size="sm"
                  onClick={handleSaveNewsSources}
                  disabled={newsLoading || newsSaving || !hasUnsavedNewsSources}
                >
                  {newsSaving ? t('common.saving', 'Saving...') : t('common.save', 'Save')}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={fetchNewsSourcesData}
                  disabled={newsLoading || newsSaving}
                >
                  {t('common.refresh', 'Refresh')}
                </Button>
                {newsError && <span className="text-red-500 text-xs">{newsError}</span>}
                {newsSuccess && <span className="text-green-500 text-xs">{newsSuccess}</span>}
              </CardFooter>
            </Card>

            <Card>
              <CardHeader className="shrink-0">
                <CardTitle>{t('settings.addNewsSource', 'Add New Source')}</CardTitle>
                <CardDescription>
                  {t('settings.addNewsSourceDesc', 'Test an RSS feed before adding it to the source list')}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-4">
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">{t('settings.newsSourceType', 'Source Type')}</div>
                    <Select
                      value={newsFormAdapter}
                      onValueChange={(value: 'rss_generic' | 'cryptopanic' | 'finnhub_calendar') => {
                        setNewsFormAdapter(value)
                        setNewsTestResult(null)
                        setNewsTestError(null)
                      }}
                    >
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="rss_generic">RSS / Atom</SelectItem>
                        <SelectItem value="cryptopanic">CryptoPanic</SelectItem>
                        <SelectItem value="finnhub_calendar">Finnhub Calendar</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <div className="text-xs text-muted-foreground">{t('settings.newsIntervalSeconds', 'Interval')}</div>
                    <Input
                      type="number"
                      min={10}
                      value={newsFormInterval}
                      onChange={(e) => {
                        setNewsFormInterval(e.target.value)
                        setNewsTestResult(null)
                        setNewsTestError(null)
                      }}
                    />
                  </div>
                  {newsFormAdapter === 'cryptopanic' && (
                    <div className="space-y-2 md:col-span-2">
                      <div className="text-xs text-muted-foreground">{t('settings.newsAuthToken', 'Auth Token')}</div>
                      <Input
                        type="password"
                        value={newsFormAuthToken}
                        onChange={(e) => {
                          setNewsFormAuthToken(e.target.value)
                          setNewsTestResult(null)
                          setNewsTestError(null)
                        }}
                      />
                    </div>
                  )}
                  {newsFormAdapter === 'finnhub_calendar' && (
                    <div className="space-y-2 md:col-span-2">
                      <div className="text-xs text-muted-foreground">{t('settings.newsApiKey', 'API Key')}</div>
                      <Input
                        type="password"
                        value={newsFormApiKey}
                        onChange={(e) => {
                          setNewsFormApiKey(e.target.value)
                          setNewsTestResult(null)
                          setNewsTestError(null)
                        }}
                      />
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-3 md:flex-row">
                  <Input
                    type="url"
                    placeholder={t('settings.newsSourceUrlPlaceholder', 'https://example.com/rss')}
                    value={newsTestUrl}
                    onChange={(e) => {
                      setNewsTestUrl(e.target.value)
                      setNewsTestError(null)
                      setNewsTestResult(null)
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestNewsSource}
                    disabled={newsTesting}
                  >
                    {newsTesting ? t('settings.testing', 'Testing...') : t('settings.test', 'Test')}
                  </Button>
                  <Button
                    type="button"
                    onClick={handleAddNewsSource}
                    disabled={!newsTestResult?.success}
                  >
                    {t('settings.add', 'Add')}
                  </Button>
                </div>

                {newsTestError && (
                  <div className="text-sm text-red-500">{newsTestError}</div>
                )}

                {newsTestResult?.success && (
                  <div className="rounded-lg border p-4 space-y-3">
                    <div className="text-sm font-medium">
                      {t('settings.newsSourceTestSuccess', 'Fetched {{count}} articles', {
                        count: newsTestResult.total_fetched ?? newsTestResult.articles.length,
                      })}
                    </div>
                    {newsTestResult.articles.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs uppercase tracking-wide text-muted-foreground">
                          {t('settings.newsSampleTitles', 'Sample Titles')}
                        </div>
                        {newsTestResult.articles.slice(0, 5).map((article, index) => (
                          <div key={`${article.source_url}-${index}`} className="text-sm">
                            {article.title || article.source_url}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="rounded-md bg-muted/50 p-3 space-y-1">
                      <div className="text-sm font-medium">
                        {newsTestResult.validation?.schema_match
                          ? t('settings.newsSchemaMatchYes', 'Schema validation passed')
                          : t('settings.newsSchemaMatchNo', 'Schema validation found issues')}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.newsSchemaValidationSummary', 'Valid {{valid}} / Invalid {{invalid}}', {
                          valid: newsTestResult.validation?.valid_articles ?? 0,
                          invalid: newsTestResult.validation?.invalid_articles ?? 0,
                        })}
                      </div>
                      {!!newsTestResult.validation?.issues?.length && (
                        <div className="space-y-1">
                          {newsTestResult.validation.issues.slice(0, 5).map((issue, index) => (
                            <div key={`${issue.source_url}-${index}`} className="text-xs text-amber-600">
                              {issue.issues.join(', ')}: {issue.source_url}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {canManageUsers && (
          <TabsContent value="admin-users" className="mt-4 flex-1 min-h-0 flex flex-col overflow-auto">
            <Card>
              <CardHeader className="shrink-0">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <CardTitle>{t('settings.adminUsers', 'Admin Users')}</CardTitle>
                    <CardDescription>
                      {t('settings.adminUsersDesc', 'Account roles and access')}
                    </CardDescription>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={fetchAdminData}
                    disabled={
                      adminUsersLoading
                      || adminAuditLoading
                      || aiRuntimeLoading
                      || aiTradingReadinessLoading
                      || aiTradingEvidenceExplainLoading
                    }
                    className="w-full gap-2 md:w-auto"
                  >
                    <RefreshCw
                      className={`h-4 w-4 ${
                        adminUsersLoading
                        || adminAuditLoading
                        || aiRuntimeLoading
                        || aiTradingReadinessLoading
                        || aiTradingEvidenceExplainLoading
                          ? 'animate-spin'
                          : ''
                      }`}
                    />
                    {t('common.refresh', 'Refresh')}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div>
                    <div className="text-sm text-muted-foreground">{t('settings.totalUsers', 'Total Users')}</div>
                    <div className="text-xl font-semibold">{adminUsers.length}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">{t('settings.adminRoles', 'Admins')}</div>
                    <div className="text-xl font-semibold">
                      {adminUsers.filter((user) => user.role === 'admin' || user.role === 'operator').length}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">{t('settings.activeUsers', 'Active Users')}</div>
                    <div className="text-xl font-semibold">
                      {adminUsers.filter((user) => user.is_active).length}
                    </div>
                  </div>
                </div>

                {adminUsersError && <div className="text-sm text-red-500">{adminUsersError}</div>}
                {adminUsersSuccess && <div className="text-sm text-green-500">{adminUsersSuccess}</div>}

                <div className="border-t pt-4 space-y-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm font-medium">{t('settings.aiRuntime', 'AI Runtime')}</div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiRuntimeDesc', 'Shared model capacity and per-user occupancy')}
                      </div>
                      {aiRuntimeStats?.runner_id && (
                        <div className="max-w-full truncate text-xs text-muted-foreground">
                          {t('settings.aiRuntimeRunner', 'Runner')} {aiRuntimeStats.runner_id}
                        </div>
                      )}
                    </div>
                    {aiRuntimeStats && (
                      <Badge
                        variant={
                          aiRuntimeStats.task_max_running_global > 0
                            && aiEffectiveRunningTasks >= aiRuntimeStats.task_max_running_global
                            ? 'destructive'
                            : 'outline'
                        }
                      >
                        {aiEffectiveRunningTasks}/{aiRuntimeStats.task_max_running_global || t('settings.unlimited', 'unlimited')}
                      </Badge>
                    )}
                  </div>

                  {aiRuntimeError && <div className="text-sm text-red-500">{aiRuntimeError}</div>}

                  {aiRuntimeLoading && !aiRuntimeStats ? (
                    <div className="text-sm text-muted-foreground">{t('common.loading', 'Loading...')}</div>
                  ) : aiRuntimeStats ? (
                    <div className="space-y-3">
                      <div className="grid gap-4 sm:grid-cols-5">
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.localRunningTasks', 'Local Running')}</div>
                          <div className="text-xl font-semibold">{aiRuntimeStats.running_tasks}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.remoteRunningTasks', 'Remote Running')}</div>
                          <div className="text-xl font-semibold">{aiRemoteRunningTasks}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.taskQueue', 'Task Queue')}</div>
                          <div className="text-xl font-semibold">{aiRuntimeStats.task_queue}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.backgroundQueue', 'Background Queue')}</div>
                          <div className="text-xl font-semibold">{aiRuntimeStats.background_queue}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.perUserLimit', 'Per User Limit')}</div>
                          <div className="text-xl font-semibold">{aiRuntimeStats.task_max_running_per_user}</div>
                        </div>
                      </div>

                      <div className="grid gap-3 rounded-md border p-3 text-sm sm:grid-cols-2 md:grid-cols-6 md:items-center">
                        <div>
                          <div className="text-xs text-muted-foreground">
                            {t('settings.distributedAdmission', 'Distributed Admission')}
                          </div>
                          <div className="font-medium">
                            {aiRuntimeStats.distributed_admission?.enabled
                              ? t('settings.enabled', 'Enabled')
                              : t('settings.disabled', 'Disabled')}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">{t('settings.status', 'Status')}</div>
                          <div className="font-medium">
                            {aiRuntimeStats.distributed_admission?.enabled
                              ? (aiRuntimeStats.distributed_admission.available
                                ? t('settings.available', 'Available')
                                : t('settings.unavailable', 'Unavailable'))
                              : t('settings.notAvailable', 'N/A')}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">{t('settings.redisLeases', 'Redis Leases')}</div>
                          <div className="font-medium">
                            {aiRuntimeStats.distributed_admission?.running_tasks ?? t('settings.notAvailable', 'N/A')}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">{t('settings.leaseTtl', 'Lease TTL')}</div>
                          <div className="font-medium">
                            {aiRuntimeStats.distributed_admission?.lease_ttl_seconds
                              ? `${aiRuntimeStats.distributed_admission.lease_ttl_seconds}s`
                              : t('settings.notAvailable', 'N/A')}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">{t('settings.persistedRunningTasks', 'Persisted')}</div>
                          <div className="font-medium">{aiRuntimeStats.persisted_running_tasks ?? 0}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">{t('settings.staleRunningTasks', 'Stale DB')}</div>
                          <div className="font-medium">{aiRuntimeStats.stale_running_tasks ?? 0}</div>
                        </div>
                        {aiRuntimeStats.distributed_admission?.last_error && (
                          <div className="min-w-0 text-xs text-red-500 md:col-span-6">
                            {aiRuntimeStats.distributed_admission.last_error}
                          </div>
                        )}
                      </div>

                      {aiRuntimeStats.dispatch_queue && (
                        <div className="grid gap-3 rounded-md border p-3 text-sm sm:grid-cols-2 md:grid-cols-7 md:items-center">
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.dispatchQueue', 'Dispatch Queue')}</div>
                            <div className="font-medium">
                              {aiRuntimeStats.dispatch_queue.enabled
                                ? t('settings.enabled', 'Enabled')
                                : t('settings.disabled', 'Disabled')}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.pending', 'Pending')}</div>
                            <div className="font-medium">{aiRuntimeStats.dispatch_queue.pending}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.claimed', 'Claimed')}</div>
                            <div className="font-medium">{aiRuntimeStats.dispatch_queue.claimed}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.claimTimeout', 'Claim Timeout')}</div>
                            <div className="font-medium">
                              {aiRuntimeStats.dispatch_queue.claim_stale_seconds
                                ? `${aiRuntimeStats.dispatch_queue.claim_stale_seconds}s`
                                : t('settings.notAvailable', 'N/A')}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.runningTasks', 'Running')}</div>
                            <div className="font-medium">{aiRuntimeStats.dispatch_queue.running}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.completed', 'Completed')}</div>
                            <div className="font-medium">{aiRuntimeStats.dispatch_queue.completed}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">{t('settings.failed', 'Failed')}</div>
                            <div className="font-medium">{aiRuntimeStats.dispatch_queue.failed}</div>
                          </div>
                          {aiRuntimeStats.dispatch_queue.last_error && (
                            <div className="min-w-0 text-xs text-red-500 md:col-span-6">
                              {aiRuntimeStats.dispatch_queue.last_error}
                            </div>
                          )}
                        </div>
                      )}

                      {aiRuntimeStats.users.length === 0 ? (
                        <div className="text-sm text-muted-foreground">
                          {t('settings.noAiRuntimeUsers', 'No buffered AI tasks')}
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {aiRuntimeStats.users.map((entry, index) => (
                            <div
                              key={`${entry.user_id ?? 'anonymous'}-${index}`}
                              className="grid gap-3 rounded-lg border p-3 md:grid-cols-[minmax(160px,1fr)_100px_100px_100px_100px_120px] md:items-center"
                            >
                              <div className="min-w-0">
                                <div className="truncate text-sm font-medium">
                                  {entry.username || t('settings.anonymousUser', 'Anonymous')}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  ID {entry.user_id ?? t('settings.notAvailable', 'N/A')}
                                </div>
                              </div>
                              <div>
                                <div className="text-xs text-muted-foreground">{t('settings.localRunningTasks', 'Local')}</div>
                                <div className="text-sm font-medium">{entry.running_tasks}</div>
                              </div>
                              <div>
                                <div className="text-xs text-muted-foreground">{t('settings.remoteRunningTasks', 'Remote')}</div>
                                <div className="text-sm font-medium">{entry.remote_running_tasks ?? 0}</div>
                              </div>
                              <div>
                                <div className="text-xs text-muted-foreground">{t('settings.totalTasks', 'Total')}</div>
                                <div className="text-sm font-medium">{entry.total_tasks}</div>
                              </div>
                              <div>
                                <div className="text-xs text-muted-foreground">{t('settings.errorTasks', 'Errors')}</div>
                                <div className="text-sm font-medium">{entry.error_tasks}</div>
                              </div>
                              <div>
                                <div className="text-xs text-muted-foreground">{t('settings.oldestRunning', 'Oldest')}</div>
                                <div className="text-sm font-medium">
                                  {entry.oldest_running_age_seconds == null
                                    ? t('settings.notAvailable', 'N/A')
                                    : `${entry.oldest_running_age_seconds}s`}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">
                      {t('settings.noAiRuntimeStats', 'No runtime stats loaded')}
                    </div>
                  )}
                </div>

                <div className="border-t pt-4 space-y-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm font-medium">
                        {t('settings.aiTradingReadiness', 'AI Trading Production Readiness')}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingReadinessDesc', 'No-network production gate for Auth, handoff, stream capacity, hard risk, and model policy')}
                      </div>
                    </div>
                    {aiTradingReadiness && (
                      <Badge variant={getReadinessBadgeVariant(aiTradingReadiness.production_ready)}>
                        {aiTradingReadiness.production_ready
                          ? t('settings.ready', 'Ready')
                          : t('settings.blocked', 'Blocked')}
                      </Badge>
                    )}
                  </div>

                  {aiTradingReadinessError && <div className="text-sm text-red-500">{aiTradingReadinessError}</div>}

                  {aiTradingReadinessLoading && !aiTradingReadiness ? (
                    <div className="text-sm text-muted-foreground">{t('common.loading', 'Loading...')}</div>
                  ) : aiTradingReadiness ? (
                    <div className="space-y-3">
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.readinessBlockers', 'Blockers')}</div>
                          <div className="text-xl font-semibold">{aiTradingReadiness.blockers.length}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.readinessWarnings', 'Warnings')}</div>
                          <div className="text-xl font-semibold">{aiTradingReadiness.warnings.length}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">{t('settings.readinessComponents', 'Components')}</div>
                          <div className="text-xl font-semibold">
                            {aiTradingReadinessComponents.filter(([, report]) => report.ready).length}/{aiTradingReadinessComponents.length}
                          </div>
                        </div>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
                        {aiTradingReadinessComponents.map(([component, report]) => {
                          const blockers = report.blockers || []
                          const warnings = report.warnings || []
                          const agentContextLocators = component === 'agent_session_context'
                            ? getAgentContextLocators(report)
                            : []
                          return (
                            <div key={component} className="min-w-0 rounded-md border p-3 text-sm">
                              <div className="mb-2 flex items-center justify-between gap-2">
                                <div className="truncate font-medium">{formatReadinessComponentName(component)}</div>
                                <Badge variant={getReadinessBadgeVariant(report.ready)}>
                                  {report.ready ? t('settings.ready', 'Ready') : t('settings.blocked', 'Blocked')}
                                </Badge>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {t('settings.readinessBlockerCount', '{{count}} blockers', { count: blockers.length })}
                              </div>
                              {blockers.length > 0 && (
                                <div className="mt-2 space-y-1">
                                  {blockers.slice(0, 3).map((blocker) => (
                                    <div key={blocker} className="truncate text-xs text-red-500" title={blocker}>
                                      {formatReadinessCode(blocker)}
                                    </div>
                                  ))}
                                  {blockers.length > 3 && (
                                    <div className="text-xs text-muted-foreground">
                                      {t('settings.readinessMoreBlockers', '+{{count}} more', { count: blockers.length - 3 })}
                                    </div>
                                  )}
                                </div>
                              )}
                              {warnings.length > 0 && (
                                <div className="mt-2 space-y-1">
                                  <div className="text-xs text-amber-600">
                                    {t('settings.readinessWarningCount', '{{count}} warnings', { count: warnings.length })}
                                  </div>
                                  {warnings.slice(0, 2).map((warning) => (
                                    <div key={warning} className="truncate text-xs text-amber-600" title={warning}>
                                      {formatReadinessCode(warning)}
                                    </div>
                                  ))}
                                  {warnings.length > 2 && (
                                    <div className="text-xs text-muted-foreground">
                                      {t('settings.readinessMoreWarnings', '+{{count}} more', { count: warnings.length - 2 })}
                                    </div>
                                  )}
                                </div>
                              )}
                              {agentContextLocators.length > 0 && (
                                <div className="mt-3 space-y-2 border-t pt-2">
                                  <div className="text-xs font-medium text-muted-foreground">
                                    {t('settings.aiTradingReadinessLatestContextLocators', 'Latest context locators')}
                                  </div>
                                  {agentContextLocators.map((locator) => (
                                    <div key={locator.key} className="min-w-0 space-y-1">
                                      <div className={`text-xs font-medium ${locator.tone}`}>{locator.label}</div>
                                      <div className="break-all text-xs text-muted-foreground">
                                        #{locator.id ?? t('settings.notAvailable', 'N/A')} · {locator.agentSessionId || t('settings.notAvailable', 'N/A')}
                                      </div>
                                      <div className="text-xs text-muted-foreground">
                                        {(locator.status || t('settings.notAvailable', 'N/A'))}
                                        {' · '}
                                        {locator.contextSummaryChars === null
                                          ? t('settings.readinessContextLocatorCharsUnknown', 'chars N/A')
                                          : t('settings.readinessContextLocatorChars', '{{count}} chars', {
                                              count: locator.contextSummaryChars,
                                            })}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>

                      {aiTradingReadiness.blockers.length > 0 && (
                        <div className="rounded-md border p-3">
                          <div className="mb-2 text-sm font-medium">{t('settings.readinessTopBlockers', 'Top Blockers')}</div>
                          <div className="space-y-1">
                            {aiTradingReadiness.blockers.slice(0, 8).map((blocker) => (
                              <div key={blocker} className="truncate text-xs text-red-500" title={blocker}>
                                {formatReadinessCode(blocker)}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {aiTradingReadiness.warnings.length > 0 && (
                        <div className="rounded-md border p-3">
                          <div className="mb-2 text-sm font-medium">{t('settings.readinessTopWarnings', 'Top Warnings')}</div>
                          <div className="space-y-1">
                            {aiTradingReadiness.warnings.slice(0, 8).map((warning) => (
                              <div key={warning} className="truncate text-xs text-amber-600" title={warning}>
                                {formatReadinessCode(warning)}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {aiTradingReadiness.next_actions.length > 0 && (
                        <div className="rounded-md border p-3">
                          <div className="mb-2 text-sm font-medium">{t('settings.readinessNextActions', 'Next Actions')}</div>
                          <div className="grid gap-2 md:grid-cols-2">
                            {aiTradingReadiness.next_actions.map((action) => (
                              <div key={action} className="text-xs text-muted-foreground">
                                {action}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">
                      {t('settings.noAiTradingReadiness', 'No AI Trading readiness report loaded')}
                    </div>
                  )}
                </div>

                <div className="border-t pt-4 space-y-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm font-medium">
                        {t('settings.aiTradingEvidenceChecklist', 'AI Trading Production Evidence')}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceChecklistDesc', 'External acceptance checklist for live-order cutover')}
                      </div>
                    </div>
                    {aiTradingEvidenceExplain && (
                      <Badge variant={getReadinessBadgeVariant(aiTradingEvidenceExplain.readyForLiveOrders)}>
                        {aiTradingEvidenceExplain.readyForLiveOrders
                          ? t('settings.ready', 'Ready')
                          : t('settings.blocked', 'Blocked')}
                      </Badge>
                    )}
                  </div>

                  {aiTradingEvidenceExplainError && (
                    <div className="text-sm text-red-500">{aiTradingEvidenceExplainError}</div>
                  )}

                  {aiTradingEvidenceExplainLoading && !aiTradingEvidenceExplain ? (
                    <div className="text-sm text-muted-foreground">{t('common.loading', 'Loading...')}</div>
                  ) : aiTradingEvidenceExplain ? (
                    <div className="space-y-3">
                      <div className="grid gap-4 sm:grid-cols-4">
                        <div>
                          <div className="text-sm text-muted-foreground">
                            {t('settings.aiTradingEvidenceAccepted', 'Accepted')}
                          </div>
                          <div className="text-xl font-semibold">
                            {aiTradingEvidenceExplain.productionEvidence.acceptedCount}/{aiTradingEvidenceExplain.productionEvidence.requiredCount}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">
                            {t('settings.aiTradingEvidenceProvided', 'Evidence')}
                          </div>
                          <div className="text-xl font-semibold">
                            {aiTradingEvidenceExplain.productionEvidence.provided
                              ? t('settings.provided', 'Provided')
                              : t('settings.notProvided', 'Not provided')}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">
                            {t('settings.aiTradingEvidenceItems', 'Items')}
                          </div>
                          <div className="text-xl font-semibold">
                            {aiTradingEvidenceExplain.items.filter((item) => item.ready).length}/{aiTradingEvidenceExplain.items.length}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">
                            {t('settings.aiTradingEvidenceLiveOrders', 'Live orders')}
                          </div>
                          <div className="text-xl font-semibold">
                            {aiTradingEvidenceExplain.readyForLiveOrders
                              ? t('settings.ready', 'Ready')
                              : t('settings.blocked', 'Blocked')}
                          </div>
                        </div>
                      </div>
                      <div className="rounded-md border p-3">
                        <div className="mb-2 flex items-center justify-between gap-3">
                          <div className="text-sm font-medium">
                            {t('settings.aiTradingEvidenceProgress', 'Evidence progress')}
                          </div>
                          <Badge variant={getReadinessBadgeVariant(aiTradingEvidenceExplain.progress.pendingCount === 0)}>
                            {aiTradingEvidenceExplain.progress.status || aiTradingEvidenceExplain.productionTrack || '-'}
                          </Badge>
                        </div>
                        <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-4">
                          <div>
                            {t('settings.aiTradingEvidenceAccepted', 'Accepted')}: {aiTradingEvidenceExplain.progress.acceptedCount}/{aiTradingEvidenceExplain.progress.requiredCount}
                          </div>
                          <div>
                            {t('settings.aiTradingEvidencePending', 'Pending')}: {aiTradingEvidenceExplain.progress.pendingCount}
                          </div>
                          <div>
                            {t('settings.readinessBlockers', 'Blockers')}: {aiTradingEvidenceExplain.progress.blockedCount}
                          </div>
                          <div className="truncate" title={aiTradingEvidenceExplain.progress.liveOrderGateBlockers.map(formatAiTradingProductionEvidenceBlocker).join(', ') || '-'}>
                            {t('settings.aiTradingEvidenceGate', 'Gate')}: {aiTradingEvidenceExplain.progress.liveOrderGateBlockers.length > 0
                              ? aiTradingEvidenceExplain.progress.liveOrderGateBlockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker).join(', ')
                              : t('settings.ready', 'Ready')}
                          </div>
                        </div>
                        {aiTradingEvidenceExplain.progress.nextRequiredItemIds.length > 0 && (
                          <div className="mt-2 truncate text-xs text-muted-foreground" title={aiTradingEvidenceExplain.progress.nextRequiredItemIds.map(formatProductionEvidenceItemName).join(', ')}>
                            {t('settings.aiTradingEvidenceNextRequired', 'Next required')}: {aiTradingEvidenceExplain.progress.nextRequiredItemIds.slice(0, 4).map(formatProductionEvidenceItemName).join(', ')}
                          </div>
                        )}
                        {aiTradingEvidenceExplain.progress.nextRequiredActions.length > 0 && (
                          <div className="mt-2 truncate text-xs text-muted-foreground" title={aiTradingEvidenceExplain.progress.nextRequiredActions.join(' | ')}>
                            {t('settings.aiTradingEvidenceNextActions', 'Evidence Actions')}: {aiTradingEvidenceExplain.progress.nextRequiredActions.slice(0, 2).join(' | ')}
                          </div>
                        )}
                      </div>
                      <div className="truncate text-xs text-muted-foreground" title={aiTradingEvidenceExplain.productionEvidence.expiresAt || '-'}>
                        {t('settings.aiTradingEvidenceExpiresAt', 'Evidence expires')}: {aiTradingEvidenceExplain.productionEvidence.expiresAt || '-'}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceRunId', 'Evidence run ID')}: {aiTradingEvidenceExplain.productionEvidence.evidenceRunIdPresent
                          ? t('settings.provided', 'Provided')
                          : t('settings.notProvided', 'Not provided')}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceRunIdBounds', 'Run ID length')}: {aiTradingEvidenceExplain.minEvidenceRunIdChars || '-'}-{aiTradingEvidenceExplain.maxEvidenceRunIdChars || '-'}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceMaxValidity', 'Max validity')}: {aiTradingEvidenceExplain.maxEvidenceValidityDays || '-'}d
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceClockSkew', 'Clock skew')}: {aiTradingEvidenceExplain.maxClockSkewSeconds || '-'}s
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceValidationAge', 'Validation age')}: {aiTradingEvidenceExplain.maxItemValidationAgeDays || '-'}d
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceCutoverWindowMax', 'Cutover window max')}: {aiTradingEvidenceExplain.maxCutoverWindowHours || '-'}h
                      </div>
                      <div
                        className="truncate text-xs text-muted-foreground"
                        title={`${aiTradingEvidenceExplain.productionEvidence.cutoverWindowStartAt || '-'} -> ${aiTradingEvidenceExplain.productionEvidence.cutoverWindowEndAt || '-'}`}
                      >
                        {t('settings.aiTradingEvidenceCutoverWindow', 'Cutover window')}: {aiTradingEvidenceExplain.productionEvidence.cutoverWindowPresent
                          ? `${aiTradingEvidenceExplain.productionEvidence.cutoverWindowStartAt || '-'} -> ${aiTradingEvidenceExplain.productionEvidence.cutoverWindowEndAt || '-'}`
                          : t('settings.notProvided', 'Not provided')}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.aiTradingEvidenceCutoverApproval', 'Cutover approval')}: {aiTradingEvidenceExplain.productionEvidence.cutoverApprovalRefPresent
                          ? t('settings.provided', 'Provided')
                          : t('settings.notProvided', 'Not provided')}
                      </div>
                      {aiTradingEvidenceExplain.productionEvidence.blockers.length > 0 && (
                        <div className="rounded-md border p-3">
                          <div className="mb-2 text-sm font-medium">
                            {t('settings.readinessBlockers', 'Blockers')}
                          </div>
                          <div className="grid gap-1 md:grid-cols-2">
                            {aiTradingEvidenceExplain.productionEvidence.blockers.slice(0, 8).map((blocker) => (
                              <div
                                key={blocker}
                                className="truncate text-xs text-red-500"
                                title={formatAiTradingProductionEvidenceBlocker(blocker)}
                              >
                                {formatAiTradingProductionEvidenceBlocker(blocker)}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {aiTradingEvidenceExplain.items.map((item) => (
                          <div key={item.id} className="min-w-0 rounded-md border p-3 text-sm">
                            <div className="mb-2 flex items-center justify-between gap-2">
                              <div className="min-w-0">
                                <div className="truncate font-medium">{formatProductionEvidenceItemName(item.id)}</div>
                                <div className="truncate text-xs text-muted-foreground" title={item.id}>
                                  {item.evidenceStatus}
                                </div>
                              </div>
                              <Badge variant={getReadinessBadgeVariant(item.ready)}>
                                {item.ready ? t('settings.ready', 'Ready') : t('settings.blocked', 'Blocked')}
                              </Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                              <div>
                                {t('settings.readinessBlockers', 'Blockers')}: {item.blockers.length}
                              </div>
                              <div>
                                {t('settings.aiTradingEvidenceArtifactRefs', 'Artifact refs')}: {item.artifactRefCount}
                              </div>
                              <div className="col-span-2 truncate" title={item.missingSummaryTerms.join(', ') || item.requiredSummaryTerms.join(', ') || '-'}>
                                {t('settings.aiTradingEvidenceSummaryTerms', 'Summary terms')}: {item.missingSummaryTerms.length > 0
                                  ? item.missingSummaryTerms.slice(0, 2).join(', ')
                                  : `${item.requiredSummaryTerms.length} ${t('settings.required', 'required')}`}
                              </div>
                            </div>
                            {item.blockers.length > 0 && (
                              <div className="mt-2 space-y-1">
                                {item.blockers.slice(0, 3).map((blocker) => (
                                  <div
                                    key={blocker}
                                    className="truncate text-xs text-red-500"
                                    title={formatAiTradingProductionEvidenceBlocker(blocker)}
                                  >
                                    {formatAiTradingProductionEvidenceBlocker(blocker)}
                                  </div>
                                ))}
                                {item.blockers.length > 3 && (
                                  <div className="text-xs text-muted-foreground">
                                    {t('settings.readinessMoreBlockers', '+{{count}} more', { count: item.blockers.length - 3 })}
                                  </div>
                                )}
                              </div>
                            )}
                            {item.operatorGuidance.length > 0 && (
                              <div className="mt-3 space-y-1 border-t pt-2">
                                {item.operatorGuidance.slice(0, 2).map((guidance) => (
                                  <div key={guidance} className="text-xs text-muted-foreground">
                                    {guidance}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>

                      {aiTradingEvidenceExplain.nextActions.length > 0 && (
                        <div className="rounded-md border p-3">
                          <div className="mb-2 text-sm font-medium">
                            {t('settings.aiTradingEvidenceNextActions', 'Evidence Actions')}
                          </div>
                          <div className="grid gap-2 md:grid-cols-2">
                            {aiTradingEvidenceExplain.nextActions.slice(0, 5).map((action) => (
                              <div key={action} className="text-xs text-muted-foreground">
                                {action}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="rounded-md border p-3">
                        <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                          <div>
                            <div className="text-sm font-medium">
                              {t('settings.aiTradingEvidenceValidate', 'Validate Evidence JSON')}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {t('settings.aiTradingEvidenceValidateDesc', 'Admin-only dry run for sanitized external evidence')}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={loadAiTradingEvidenceTemplate}
                              disabled={aiTradingEvidenceTemplateLoading || aiTradingEvidenceValidationLoading}
                            >
                              {aiTradingEvidenceTemplateLoading
                                ? t('common.loading', 'Loading...')
                                : t('settings.aiTradingEvidenceTemplateAction', 'Load template')}
                            </Button>
                            <Button
                              size="sm"
                              onClick={validateAiTradingEvidence}
                              disabled={aiTradingEvidenceValidationLoading || aiTradingEvidenceTemplateLoading}
                            >
                              {aiTradingEvidenceValidationLoading
                                ? t('common.loading', 'Loading...')
                                : t('settings.aiTradingEvidenceValidateAction', 'Validate')}
                            </Button>
                          </div>
                        </div>
                        <Textarea
                          value={aiTradingEvidenceValidationJson}
                          onChange={(event) => setAiTradingEvidenceValidationJson(event.target.value)}
                          placeholder={t('settings.aiTradingEvidenceValidatePlaceholder', 'Paste production evidence JSON')}
                          maxLength={AI_TRADING_EVIDENCE_MAX_JSON_CHARS}
                          className="min-h-[120px] resize-y font-mono text-xs"
                        />
                        {aiTradingEvidenceTemplateGuidance && (
                          <div className="mt-3 border-t pt-3">
                            <div className="mb-2 flex items-center justify-between gap-2">
                              <div className="text-sm font-medium">
                                {t('settings.aiTradingEvidenceTemplateGuidance', 'Template guidance')}
                              </div>
                              <Badge variant="outline">{aiTradingEvidenceTemplateGuidance.secretPolicy || 'metadata_only'}</Badge>
                            </div>
                            {aiTradingEvidenceTemplateGuidance.nextRequiredActions.length > 0 && (
                              <div className="mb-2 truncate text-xs text-muted-foreground" title={aiTradingEvidenceTemplateGuidance.nextRequiredActions.join(' | ')}>
                                {t('settings.aiTradingEvidenceNextActions', 'Evidence Actions')}: {aiTradingEvidenceTemplateGuidance.nextRequiredActions.slice(0, 2).join(' | ')}
                              </div>
                            )}
                            <div className="grid gap-2 md:grid-cols-2">
                              {aiTradingEvidenceTemplateGuidance.items.slice(0, 4).map((item) => (
                                <div key={item.id} className="min-w-0 border-t pt-2">
                                  <div className="truncate text-xs font-medium">{formatProductionEvidenceItemName(item.id)}</div>
                                  <div className="truncate text-xs text-muted-foreground" title={item.operatorGuidance.join(' | ')}>
                                    {item.operatorGuidance[0] || item.description}
                                  </div>
                                  <div className="truncate text-xs text-muted-foreground" title={item.requiredSummaryTerms.join(', ')}>
                                    {t('settings.aiTradingEvidenceSummaryTerms', 'Summary terms')}: {item.requiredSummaryTerms.slice(0, 2).join(', ') || '-'}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {aiTradingEvidenceValidationError && (
                          <div className="mt-2 text-sm text-red-500">{aiTradingEvidenceValidationError}</div>
                        )}
                        {aiTradingEvidenceValidation && (
                          <div className="mt-3 grid gap-3 md:grid-cols-[220px_1fr]">
                            <div className="rounded-md border p-3">
                              <div className="text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceAccepted', 'Accepted')}
                              </div>
                              <div className="text-xl font-semibold">
                                {aiTradingEvidenceValidation.productionEvidence.acceptedCount}/{aiTradingEvidenceValidation.productionEvidence.requiredCount}
                              </div>
                              <Badge
                                className="mt-2"
                                variant={getReadinessBadgeVariant(aiTradingEvidenceValidation.productionEvidence.ready)}
                              >
                                {aiTradingEvidenceValidation.productionEvidence.ready
                                  ? t('settings.ready', 'Ready')
                                  : t('settings.blocked', 'Blocked')}
                              </Badge>
                              <div className="mt-2 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceLiveOrders', 'Live orders')}: {
                                  aiTradingEvidenceValidation.readyForLiveOrders
                                    ? t('settings.ready', 'Ready')
                                    : t('settings.blocked', 'Blocked')
                                }
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidencePending', 'Pending')}: {aiTradingEvidenceValidation.progress.pendingCount}
                              </div>
                              <div className="mt-1 truncate text-xs text-muted-foreground" title={aiTradingEvidenceValidation.progress.liveOrderGateBlockers.map(formatAiTradingProductionEvidenceBlocker).join(', ') || '-'}>
                                {t('settings.aiTradingEvidenceGate', 'Gate')}: {aiTradingEvidenceValidation.progress.liveOrderGateBlockers.length > 0
                                  ? aiTradingEvidenceValidation.progress.liveOrderGateBlockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker).join(', ')
                                  : t('settings.ready', 'Ready')}
                              </div>
                              {aiTradingEvidenceValidation.progress.nextRequiredItemIds.length > 0 && (
                                <div className="mt-1 truncate text-xs text-muted-foreground" title={aiTradingEvidenceValidation.progress.nextRequiredItemIds.map(formatProductionEvidenceItemName).join(', ')}>
                                  {t('settings.aiTradingEvidenceNextRequired', 'Next required')}: {aiTradingEvidenceValidation.progress.nextRequiredItemIds.slice(0, 3).map(formatProductionEvidenceItemName).join(', ')}
                                </div>
                              )}
                              {aiTradingEvidenceValidation.progress.nextRequiredActions.length > 0 && (
                                <div className="mt-1 truncate text-xs text-muted-foreground" title={aiTradingEvidenceValidation.progress.nextRequiredActions.join(' | ')}>
                                  {t('settings.aiTradingEvidenceNextActions', 'Evidence Actions')}: {aiTradingEvidenceValidation.progress.nextRequiredActions.slice(0, 2).join(' | ')}
                                </div>
                              )}
                              <div className="mt-1 truncate text-xs text-muted-foreground" title={aiTradingEvidenceValidation.productionEvidence.expiresAt || '-'}>
                                {t('settings.aiTradingEvidenceExpiresAt', 'Evidence expires')}: {aiTradingEvidenceValidation.productionEvidence.expiresAt || '-'}
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceRunId', 'Evidence run ID')}: {aiTradingEvidenceValidation.productionEvidence.evidenceRunIdPresent
                                  ? t('settings.provided', 'Provided')
                                  : t('settings.notProvided', 'Not provided')}
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceRunIdBounds', 'Run ID length')}: {aiTradingEvidenceValidation.minEvidenceRunIdChars || '-'}-{aiTradingEvidenceValidation.maxEvidenceRunIdChars || '-'}
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceMaxValidity', 'Max validity')}: {aiTradingEvidenceValidation.maxEvidenceValidityDays || '-'}d
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceClockSkew', 'Clock skew')}: {aiTradingEvidenceValidation.maxClockSkewSeconds || '-'}s
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceValidationAge', 'Validation age')}: {aiTradingEvidenceValidation.maxItemValidationAgeDays || '-'}d
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceCutoverWindowMax', 'Cutover window max')}: {aiTradingEvidenceValidation.maxCutoverWindowHours || '-'}h
                              </div>
                              <div
                                className="mt-1 truncate text-xs text-muted-foreground"
                                title={`${aiTradingEvidenceValidation.productionEvidence.cutoverWindowStartAt || '-'} -> ${aiTradingEvidenceValidation.productionEvidence.cutoverWindowEndAt || '-'}`}
                              >
                                {t('settings.aiTradingEvidenceCutoverWindow', 'Cutover window')}: {aiTradingEvidenceValidation.productionEvidence.cutoverWindowPresent
                                  ? `${aiTradingEvidenceValidation.productionEvidence.cutoverWindowStartAt || '-'} -> ${aiTradingEvidenceValidation.productionEvidence.cutoverWindowEndAt || '-'}`
                                  : t('settings.notProvided', 'Not provided')}
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {t('settings.aiTradingEvidenceCutoverApproval', 'Cutover approval')}: {aiTradingEvidenceValidation.productionEvidence.cutoverApprovalRefPresent
                                  ? t('settings.provided', 'Provided')
                                  : t('settings.notProvided', 'Not provided')}
                              </div>
                            </div>
                            <div className="rounded-md border p-3">
                              <div className="mb-2 text-sm font-medium">
                                {t('settings.readinessBlockers', 'Blockers')}
                              </div>
                              {aiTradingEvidenceValidation.productionEvidence.blockers.length > 0 ? (
                                <div className="grid gap-1 md:grid-cols-2">
                                  {aiTradingEvidenceValidation.productionEvidence.blockers.slice(0, 8).map((blocker) => (
                                    <div
                                      key={blocker}
                                      className="truncate text-xs text-red-500"
                                      title={formatAiTradingProductionEvidenceBlocker(blocker)}
                                    >
                                      {formatAiTradingProductionEvidenceBlocker(blocker)}
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-xs text-muted-foreground">
                                  {t('settings.aiTradingEvidenceNoBlockers', 'No evidence blockers')}
                                </div>
                              )}
                              {aiTradingEvidenceValidation.items.some((item) => !item.ready) && (
                                <div className="mt-3 grid gap-2 md:grid-cols-2">
                                  {aiTradingEvidenceValidation.items.filter((item) => !item.ready).slice(0, 6).map((item) => (
                                    <div key={item.id} className="min-w-0 rounded border p-2">
                                      <div className="truncate text-xs font-medium">
                                        {formatProductionEvidenceItemName(item.id)}
                                      </div>
                                      <div className="truncate text-xs text-muted-foreground">
                                        {item.blockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker).join(', ')}
                                      </div>
                                      {item.missingSummaryTerms.length > 0 && (
                                        <div
                                          className="truncate text-xs text-muted-foreground"
                                          title={item.missingSummaryTerms.join(', ')}
                                        >
                                          {t('settings.aiTradingEvidenceMissingTerms', 'Missing terms')}: {item.missingSummaryTerms.slice(0, 2).join(', ')}
                                        </div>
                                      )}
                                      {item.operatorGuidance.length > 0 && (
                                        <div
                                          className="truncate text-xs text-muted-foreground"
                                          title={item.operatorGuidance.join(' | ')}
                                        >
                                          {t('settings.aiTradingEvidenceFixHint', 'Fix')}: {item.operatorGuidance[0]}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">
                      {t('settings.noAiTradingEvidenceChecklist', 'No AI Trading production evidence checklist loaded')}
                    </div>
                  )}
                </div>

                {adminUsersLoading && adminUsers.length === 0 ? (
                  <div className="text-sm text-muted-foreground">{t('common.loading', 'Loading...')}</div>
                ) : adminUsers.length === 0 ? (
                  <div className="text-sm text-muted-foreground">{t('settings.noUsers', 'No users found')}</div>
                ) : (
                  <div className="space-y-2">
                    <div className="hidden grid-cols-[minmax(160px,1fr)_minmax(180px,1fr)_140px_180px] gap-3 px-3 text-xs font-medium uppercase text-muted-foreground md:grid">
                      <div>{t('settings.user', 'User')}</div>
                      <div>{t('settings.email', 'Email')}</div>
                      <div>{t('settings.status', 'Status')}</div>
                      <div>{t('settings.role', 'Role')}</div>
                    </div>
                    {adminUsers.map((user) => (
                      <div
                        key={user.id}
                        className="grid gap-3 rounded-lg border p-3 md:grid-cols-[minmax(160px,1fr)_minmax(180px,1fr)_140px_180px] md:items-center"
                      >
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">{user.username}</div>
                          <div className="text-xs text-muted-foreground">
                            ID {user.id} - {formatDateTime(user.created_at)}
                          </div>
                        </div>
                        <div className="min-w-0 text-sm text-muted-foreground">
                          <span className="block truncate">{user.email || t('settings.notAvailable', 'N/A')}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={getAdminRoleBadgeVariant(user.role)}>{user.role}</Badge>
                          {!user.is_active && (
                            <Badge variant="outline" className="text-muted-foreground">
                              {t('settings.disabled', 'Disabled')}
                            </Badge>
                          )}
                        </div>
                        <Select
                          value={user.role || 'user'}
                          onValueChange={(value) => handleUpdateAdminRole(user.id, value as AdminUser['role'])}
                          disabled={adminRoleSaving[user.id]}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="user">{t('settings.roleUser', 'User')}</SelectItem>
                            <SelectItem value="operator">{t('settings.roleOperator', 'Operator')}</SelectItem>
                            <SelectItem value="admin">{t('settings.roleAdmin', 'Admin')}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    ))}
                  </div>
                )}

                <div className="border-t pt-4 space-y-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="text-sm font-medium">{t('settings.adminAuditLogs', 'Recent Role Changes')}</div>
                      <div className="text-xs text-muted-foreground">
                        {t('settings.adminAuditLogsDesc', 'Persistent audit trail for admin role updates')}
                      </div>
                    </div>
                    <Badge variant="outline">{adminAuditLogs.length}</Badge>
                  </div>

                  {adminAuditError && <div className="text-sm text-red-500">{adminAuditError}</div>}

                  {adminAuditLoading && adminAuditLogs.length === 0 ? (
                    <div className="text-sm text-muted-foreground">{t('common.loading', 'Loading...')}</div>
                  ) : adminAuditLogs.length === 0 ? (
                    <div className="text-sm text-muted-foreground">
                      {t('settings.noAdminAuditLogs', 'No role changes recorded')}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {adminAuditLogs.map((log) => (
                        <div
                          key={log.id}
                          className="grid gap-3 rounded-lg border p-3 md:grid-cols-[minmax(160px,1fr)_minmax(160px,1fr)_minmax(140px,1fr)_minmax(180px,1fr)] md:items-center"
                        >
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">
                              {log.target_username || t('settings.notAvailable', 'N/A')}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              ID {log.target_user_id ?? t('settings.notAvailable', 'N/A')}
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={getAdminRoleBadgeVariant(log.old_value || 'user')}>
                              {log.old_value || 'user'}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {t('settings.roleChangeTo', 'to')}
                            </span>
                            <Badge variant={getAdminRoleBadgeVariant(log.new_value || 'user')}>
                              {log.new_value || 'user'}
                            </Badge>
                          </div>
                          <div className="min-w-0 text-sm text-muted-foreground">
                            <span className="block truncate">
                              {log.actor_username || t('settings.notAvailable', 'N/A')}
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDateTime(log.created_at)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
