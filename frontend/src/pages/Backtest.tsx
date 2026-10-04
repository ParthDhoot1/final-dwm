import { useEffect, useState } from 'react'
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BacktestResponse, PatternResponse, formatNumber, formatPct, postJson, requestJson } from '../api/analysis'

export default function Backtest() {
  const [rules, setRules] = useState<PatternResponse['rules']>([])
  const [ruleId, setRuleId] = useState('')
  const [result, setResult] = useState<BacktestResponse | null>(null)
  const [capital, setCapital] = useState(10000)
  const [positionSize, setPositionSize] = useState(100)
  const [holding, setHolding] = useState(5)
  const [stopLoss, setStopLoss] = useState(5)
  const [takeProfit, setTakeProfit] = useState(10)
  const [cost, setCost] = useState(0.1)
  const [slippage, setSlippage] = useState(0.05)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    postJson<PatternResponse>('/api/patterns/mine', { min_support: 0.01, min_confidence: 0.5, train_ratio: 0.7 })
      .then((data) => {
        const available = data.rules.filter((rule) => rule.consequent === 'NEXT_DAY_UP')
        setRules(available)
        setRuleId(available.find((rule) => rule.actionable)?.rule_id ?? available[0]?.rule_id ?? '')
      }).catch((reason: Error) => setError(reason.message))
  }, [])

  async function run() {
    setBusy(true); setError('')
    try {
      setResult(await postJson<BacktestResponse>('/api/backtest/run', {
        rule_id: ruleId || undefined, initial_capital: capital, position_size_pct: positionSize, holding_days: holding,
        stop_loss_pct: stopLoss, take_profit_pct: takeProfit,
        transaction_cost_pct: cost, slippage_pct: slippage,
        min_support: 0.01, min_confidence: 0.5, train_ratio: 0.7,
      }))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Backtest failed.') }
    finally { setBusy(false) }
  }
  async function saveRun() {
    if (!result) return
    const name = window.prompt('Name this backtest', `${result.selected_rule.rule_id} · ${new Date().toLocaleDateString()}`)
    if (!name?.trim()) return
    setSaving(true); setError(''); setSaved('')
    try {
      await requestJson('/api/experiments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        name: name.trim(), parameters: { rule_id: ruleId, initial_capital: capital, position_size_pct: positionSize, holding_days: holding, stop_loss_pct: stopLoss, take_profit_pct: takeProfit, transaction_cost_pct: cost, slippage_pct: slippage, train_ratio: 0.7 }, result,
      }) })
      setSaved('Saved to Experiments.')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save this backtest.') }
    finally { setSaving(false) }
  }
  useEffect(() => { if (ruleId) void run() }, [ruleId])

  const metrics = result?.metrics
  return <section className="analysis-page">
    <div className="analysis-page-heading"><div><p className="eyebrow">MARKETMINER / BACKTEST</p><h1>Strategy backtest</h1><p>Train-set rule, test-set trades, and next-session execution.</p></div><button className="analysis-button run-backtest" disabled={busy || !ruleId} onClick={() => void run()}>{busy ? 'Running…' : 'Run backtest'}</button></div>
    <article className="analysis-card strategy-controls"><label>Long entry rule<select value={ruleId} onChange={(event) => setRuleId(event.target.value)}><option value="">Select a NEXT_DAY_UP rule</option>{rules.map((rule) => <option key={rule.rule_id} value={rule.rule_id}>{rule.antecedent_labels.join(' + ')} → Next day up · lift {rule.lift.toFixed(2)}</option>)}</select></label><label>Initial capital<input type="number" min="100" value={capital} onChange={(event) => setCapital(Number(event.target.value))} /></label><label>Position size %<input type="number" min="1" max="100" value={positionSize} onChange={(event) => setPositionSize(Number(event.target.value))} /></label><label>Hold (sessions)<input type="number" min="1" max="60" value={holding} onChange={(event) => setHolding(Number(event.target.value))} /></label><label>Stop-loss %<input type="number" min="0" step="0.5" value={stopLoss} onChange={(event) => setStopLoss(Number(event.target.value))} /></label><label>Take-profit %<input type="number" min="0" step="0.5" value={takeProfit} onChange={(event) => setTakeProfit(Number(event.target.value))} /></label><label>Cost per side %<input type="number" min="0" step="0.01" value={cost} onChange={(event) => setCost(Number(event.target.value))} /></label><label>Slippage per side %<input type="number" min="0" step="0.01" value={slippage} onChange={(event) => setSlippage(Number(event.target.value))} /></label></article>
    {error && <div className="analysis-error">{error}</div>}
    {result && metrics && <>
      <div className="split-banner"><span><b>Train:</b> {result.split.train_rows.toLocaleString()} rows through {result.split.train_end_date}</span><span><b>Test:</b> {result.split.test_rows.toLocaleString()} rows, {result.split.test_start_date}–{result.split.test_end_date}</span><span>{result.split.explanation}</span><button className="analysis-button" onClick={() => void saveRun()} disabled={saving}>{saving ? 'Saving…' : 'Save this run'}</button>{saved && <span className="save-confirmation">{saved}</span>}</div>
      <div className="metric-grid backtest-metrics"><article className="metric-card"><span>Strategy return</span><strong className={metrics.strategy_total_return_pct >= 0 ? 'positive' : ''}>{formatPct(metrics.strategy_total_return_pct)}</strong><small>Buy &amp; Hold {formatPct(metrics.buy_hold_total_return_pct)}</small></article><article className="metric-card"><span>Strategy CAGR</span><strong>{formatPct(metrics.strategy_cagr_pct)}</strong><small>Buy &amp; Hold {formatPct(metrics.buy_hold_cagr_pct)}</small></article><article className="metric-card"><span>Strategy Sharpe</span><strong>{metrics.strategy_sharpe.toFixed(2)}</strong><small>Buy &amp; Hold {metrics.buy_hold_sharpe.toFixed(2)}</small></article><article className="metric-card"><span>Maximum drawdown</span><strong>{metrics.strategy_max_drawdown_pct.toFixed(2)}%</strong><small>Buy &amp; Hold {metrics.buy_hold_max_drawdown_pct.toFixed(2)}%</small></article><article className="metric-card"><span>Win rate</span><strong>{metrics.win_rate_pct.toFixed(1)}%</strong><small>{metrics.number_of_trades} completed trades</small></article><article className="metric-card"><span>Profit factor</span><strong>{metrics.profit_factor === null ? '—' : metrics.profit_factor.toFixed(2)}</strong><small>Gross wins ÷ gross losses</small></article><article className="metric-card"><span>Sortino ratio</span><strong>{metrics.strategy_sortino.toFixed(2)}</strong><small>Downside-risk adjusted</small></article><article className="metric-card"><span>Ending equity</span><strong>{formatNumber(metrics.ending_equity, 2)}</strong><small>From {formatNumber(metrics.initial_capital, 0)} initial capital</small></article></div>
      <div className="analysis-two-col"><article className="analysis-card"><div className="analysis-card-heading"><h2>Equity curve</h2><span>Test period only</span></div><div className="large-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={result.equity_curve} margin={{ top: 15, right: 16, left: 4, bottom: 5 }}><CartesianGrid stroke="#ffffff10" vertical={false} /><XAxis dataKey="date" tickFormatter={(v: string) => v.slice(0, 4)} minTickGap={35} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis tickFormatter={(v: number) => formatNumber(v, 0)} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 9, color: '#e9f2ee', fontSize: 10 }} labelFormatter={(v) => `Date: ${v}`} formatter={(v) => [formatNumber(Number(v)), '']} /><Area type="monotone" dataKey="strategy" name="Strategy" stroke="#5ee0b5" fill="#5ee0b51a" strokeWidth={2} /><Line type="monotone" dataKey="buy_hold" name="Buy & Hold" stroke="#8b9cf7" dot={false} strokeWidth={1.5} /></AreaChart></ResponsiveContainer></div></article><article className="analysis-card"><div className="analysis-card-heading"><h2>Drawdown</h2><span>Peak-to-trough decline</span></div><div className="large-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.drawdown_series} margin={{ top: 15, right: 16, left: 4, bottom: 5 }}><CartesianGrid stroke="#ffffff10" vertical={false} /><XAxis dataKey="date" tickFormatter={(v: string) => v.slice(0, 4)} minTickGap={35} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis tickFormatter={(v: number) => `${v.toFixed(0)}%`} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 9, color: '#e9f2ee', fontSize: 10 }} /><Line type="monotone" dataKey="strategy" name="Strategy" stroke="#5ee0b5" dot={false} strokeWidth={1.7} /><Line type="monotone" dataKey="buy_hold" name="Buy & Hold" stroke="#8b9cf7" dot={false} strokeWidth={1.4} /></LineChart></ResponsiveContainer></div></article></div>
      <div className="analysis-two-col"><article className="analysis-card"><div className="analysis-card-heading"><h2>Monthly returns</h2><span>Test data</span></div><div className="table-scroll compact-months"><table><thead><tr><th>Month</th><th>Strategy</th><th>Buy &amp; Hold</th></tr></thead><tbody>{[...result.monthly_returns].reverse().slice(0, 18).map((row) => <tr key={row.month}><td>{row.month}</td><td className={row.strategy_pct >= 0 ? 'positive-cell' : 'negative-cell'}>{formatPct(row.strategy_pct)}</td><td>{formatPct(row.buy_hold_pct)}</td></tr>)}</tbody></table></div></article><article className="analysis-card"><div className="analysis-card-heading"><h2>Recent trades</h2><span>{result.trade_log_note}</span></div>{result.trades.length ? <div className="table-scroll"><table><thead><tr><th>Signal day</th><th>Entry</th><th>Exit</th><th>Net return</th><th>Exit reason</th></tr></thead><tbody>{result.trades.slice(0, 18).map((trade, index) => <tr key={`${trade.signal_date}-${index}`}><td>{trade.signal_date}</td><td>{trade.entry_date} @ {formatNumber(trade.entry_price)}</td><td>{trade.exit_date} @ {formatNumber(trade.exit_price)}</td><td className={trade.net_return_pct >= 0 ? 'positive-cell' : 'negative-cell'}>{formatPct(trade.net_return_pct)}</td><td>{trade.exit_reason}</td></tr>)}</tbody></table></div> : <div className="empty-state">No entry signals occurred in this test segment for the selected rule.</div>}</article></div>
    </>}
  </section>
}
