export const apiBase = import.meta.env.VITE_API_URL || ''

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init)
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Request failed (${response.status})`)
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

export const formatPct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
export const formatPercent = (value: number) => `${value.toFixed(2)}%`
export const formatNumber = (value: number, digits = 2) => value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })

export type PatternRule = {
  rule_id: string; antecedent: string[]; antecedent_labels: string[]; consequent: 'NEXT_DAY_UP' | 'NEXT_DAY_DOWN'
  consequent_label: string; support: number; confidence: number; lift: number; count: number; actionable: boolean
}

export type PatternResponse = {
  algorithm: 'apriori' | 'fpgrowth'; frequent_itemsets: Array<{ items: string[]; support: number; count: number }>
  rules: PatternRule[]; train_rows: number; test_rows: number; split_date: string | null; train_end_date: string
  base_rates: Record<string, number>; min_support: number; min_confidence: number
}
export type SequenceResponse = {
  patterns: Array<{ sequence: string[]; labels: string[]; support: number; count: number }>
  window_days: number; train_rows: number; sequence_windows: number; min_support: number
  train_end_date: string | null; method_note: string
}

export type ClusterPoint = {
  start_date: string; end_date: string; cluster_id: number; x: number; y: number
  mean_return: number; annualized_volatility: number; window_return: number; max_drawdown: number
}
export type ClusterProfile = {
  cluster_id: number; label: string; windows: number; mean_annualized_return_pct: number
  mean_annualized_volatility_pct: number; mean_window_return_pct: number; mean_max_drawdown_pct: number
}
export type ClusterResponse = {
  k: number; window_sessions: number; step_sessions: number; method_note: string
  profiles: ClusterProfile[]; points: ClusterPoint[]; scores: Array<{ k: number; inertia: number; silhouette: number }>
}

export type BacktestResponse = {
  selected_rule: PatternRule
  split: { train_ratio: number; train_rows: number; test_rows: number; train_end_date: string; test_start_date: string; test_end_date: string; explanation: string }
  metrics: { strategy_total_return_pct: number; buy_hold_total_return_pct: number; strategy_cagr_pct: number; buy_hold_cagr_pct: number; strategy_sharpe: number; buy_hold_sharpe: number; strategy_sortino: number; strategy_max_drawdown_pct: number; buy_hold_max_drawdown_pct: number; win_rate_pct: number; profit_factor: number | null; number_of_trades: number; initial_capital: number; ending_equity: number; position_size_pct: number }
  equity_curve: Array<{ date: string; strategy: number; buy_hold: number }>
  drawdown_series: Array<{ date: string; strategy: number; buy_hold: number }>
  monthly_returns: Array<{ month: string; strategy_pct: number; buy_hold_pct: number }>
  trades: Array<{ signal_date: string; entry_date: string; exit_date: string; entry_price: number; exit_price: number; net_return_pct: number; net_pnl: number; exit_reason: string }>
  trade_log_note: string
}
