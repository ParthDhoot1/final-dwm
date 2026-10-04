import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BacktestResponse, formatNumber, formatPct, requestJson } from '../api/analysis'

type Experiment = { id: number; name: string; rule_id: string; created_at: string; parameters: Record<string, unknown>; result: BacktestResponse }

export default function Experiments() {
  const [items, setItems] = useState<Experiment[]>([])
  const [selected, setSelected] = useState<Experiment | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(true)
  async function refresh() {
    setBusy(true); setError('')
    try { setItems(await requestJson<Experiment[]>('/api/experiments')) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load saved runs.') }
    finally { setBusy(false) }
  }
  useEffect(() => { void refresh() }, [])
  async function remove(id: number) {
    try { await requestJson<void>(`/api/experiments/${id}`, { method: 'DELETE' }); if (selected?.id === id) setSelected(null); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not delete the run.') }
  }
  return <section className="analysis-page">
    <div className="analysis-page-heading"><div><p className="eyebrow">MARKETMINER / EXPERIMENTS</p><h1>Saved runs</h1><p>Keep completed backtests and compare their recorded settings and outcomes.</p></div><button className="analysis-button" onClick={() => void refresh()} disabled={busy}>{busy ? 'Loading…' : 'Refresh'}</button></div>
    {error && <div className="analysis-error">{error}</div>}
    {busy && !items.length ? <div className="analysis-loading">Loading saved runs…</div> : items.length ? <div className="analysis-two-col">
      <article className="analysis-card"><div className="analysis-card-heading"><h2>Experiment history</h2><span>{items.length} saved</span></div><div className="experiment-list">{items.map((item) => <div className={`experiment-row ${selected?.id === item.id ? 'selected' : ''}`} key={item.id}><button className="experiment-open" onClick={() => setSelected(item)}><b>{item.name}</b><span>{new Date(item.created_at).toLocaleString()}</span><small>{item.rule_id}</small></button><button className="text-button danger" onClick={() => void remove(item.id)} aria-label={`Delete ${item.name}`}>Delete</button></div>)}</div></article>
      {selected ? <article className="analysis-card"><div className="analysis-card-heading"><div><h2>{selected.name}</h2><span>{selected.result.split.test_start_date} — {selected.result.split.test_end_date}</span></div></div><div className="saved-metrics"><span>Strategy <b>{formatPct(selected.result.metrics.strategy_total_return_pct)}</b></span><span>Buy &amp; Hold <b>{formatPct(selected.result.metrics.buy_hold_total_return_pct)}</b></span><span>Trades <b>{selected.result.metrics.number_of_trades}</b></span><span>Sharpe <b>{selected.result.metrics.strategy_sharpe.toFixed(2)}</b></span></div><div className="large-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={selected.result.equity_curve}><CartesianGrid stroke="#ffffff10" vertical={false} /><XAxis dataKey="date" tickFormatter={(v: string) => v.slice(0, 4)} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis tickFormatter={(v: number) => formatNumber(v, 0)} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 9, color: '#e9f2ee', fontSize: 10 }} /><Area dataKey="strategy" name="Strategy" stroke="#5ee0b5" fill="#5ee0b51a" /><Line dataKey="buy_hold" name="Buy & Hold" stroke="#8b9cf7" dot={false} /></AreaChart></ResponsiveContainer></div><div className="chart-caption">Settings: {Object.entries(selected.parameters).map(([key, value]) => `${key.replace(/_/g, ' ')} ${String(value)}`).join(' · ')}</div></article> : <article className="analysis-card empty-state">Select a saved run to reload its metrics and equity curve.</article>}
    </div> : <article className="analysis-card empty-state">No saved backtests yet. Run one on the <Link className="inline-link" to="/backtest">Backtest page</Link>, then save its results.</article>}
  </section>
}
