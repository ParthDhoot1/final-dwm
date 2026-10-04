import { useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

type PricePoint = { date: string; close: number }
type RecentRow = { date: string; open: number; high: number; low: number; close: number; volume: number }
type Analysis = {
  symbol: string; dataset_name: string; row_count: number; start_date: string; end_date: string
  latest_close: number; total_return_pct: number; cagr_pct: number
  annualized_volatility_pct: number; sharpe_ratio: number; max_drawdown_pct: number
  zero_volume_rows: number; price_series: PricePoint[]; recent_rows: RecentRow[]
}

const apiBase = import.meta.env.VITE_API_URL || ''
const money = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const pct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`

export default function Explorer() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [error, setError] = useState('')
  const [range, setRange] = useState<'5Y' | '20Y' | 'ALL'>('ALL')

  useEffect(() => {
    fetch(`${apiBase}/api/data/sample`)
      .then((response) => { if (!response.ok) throw new Error(`Could not load dataset (${response.status})`); return response.json() })
      .then(setAnalysis)
      .catch((reason: Error) => setError(reason.message))
  }, [])

  const visibleSeries = useMemo(() => {
    if (!analysis) return []
    const lastYear = Number(analysis.end_date.slice(0, 4))
    const years = range === '5Y' ? 5 : range === '20Y' ? 20 : Infinity
    return analysis.price_series.filter((point) => Number(point.date.slice(0, 4)) >= lastYear - years)
  }, [analysis, range])

  if (error) return <section className="explorer page"><p className="eyebrow">MARKETMINER / DATA EXPLORER</p><h1>SPX analysis</h1><div className="analysis-error">{error}. Make sure the FastAPI backend is running.</div></section>
  if (!analysis) return <section className="explorer page"><p className="eyebrow">MARKETMINER / DATA EXPLORER</p><h1>SPX analysis</h1><div className="analysis-loading">Loading historical dataset…</div></section>

  const metrics = [
    { label: 'Total return', value: pct(analysis.total_return_pct), note: `${analysis.start_date.slice(0, 4)}–${analysis.end_date.slice(0, 4)}`, positive: analysis.total_return_pct >= 0 },
    { label: 'CAGR', value: pct(analysis.cagr_pct), note: 'Annualized growth', positive: analysis.cagr_pct >= 0 },
    { label: 'Annualized volatility', value: `${analysis.annualized_volatility_pct.toFixed(2)}%`, note: 'Daily returns × √252', positive: false },
    { label: 'Max drawdown', value: `${analysis.max_drawdown_pct.toFixed(2)}%`, note: 'Peak to trough', positive: false },
  ]

  return <section className="explorer page">
    <div className="explorer-heading"><div><p className="eyebrow">MARKETMINER / DATA EXPLORER</p><h1>SPX analysis</h1><p className="dataset-subtitle">{analysis.dataset_name} <span>·</span> Offline dataset</p></div><div className="dataset-badge"><i />CSV LOADED</div></div>
    <div className="dataset-meta"><span><b>{analysis.row_count.toLocaleString()}</b> daily observations</span><span>{analysis.start_date} — {analysis.end_date}</span><span>Latest close <b>{money(analysis.latest_close)}</b></span></div>
    <div className="metric-grid">{metrics.map((metric) => <article className="metric-card" key={metric.label}><span>{metric.label}</span><strong className={metric.positive ? 'positive' : ''}>{metric.value}</strong><small>{metric.note}</small></article>)}</div>
    <div className="analysis-card chart-card"><div className="chart-heading"><div><h2>Adjusted close</h2><p>Monthly observations · S&P 500 index points</p></div><div className="range-switch">{(['5Y', '20Y', 'ALL'] as const).map((item) => <button className={range === item ? 'selected' : ''} key={item} onClick={() => setRange(item)}>{item}</button>)}</div></div>
      <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><LineChart data={visibleSeries} margin={{ top: 15, right: 18, left: 4, bottom: 4 }}><CartesianGrid stroke="#ffffff10" vertical={false} /><XAxis dataKey="date" tickFormatter={(value: string) => value.slice(0, 4)} minTickGap={55} tick={{ fill: '#70847a', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis domain={['auto', 'auto']} width={58} tickFormatter={(value: number) => value.toLocaleString('en-US')} tick={{ fill: '#70847a', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 10, color: '#e9f2ee', fontSize: 12 }} labelFormatter={(label) => `Date: ${label}`} formatter={(value) => [money(Number(value)), 'Adjusted close']} /><Line type="monotone" dataKey="close" stroke="#5ee0b5" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#5ee0b5' }} /></LineChart></ResponsiveContainer></div>
      <div className="chart-caption">Chart uses adjusted close, sampled at the last trading day of each month.</div>
    </div>
    <div className="analysis-lower"><article className="analysis-card stat-card"><p className="eyebrow">RISK-ADJUSTED SNAPSHOT</p><h2>Sharpe ratio <strong>{analysis.sharpe_ratio.toFixed(2)}</strong></h2><p>Calculated from daily adjusted-close returns, annualized using 252 trading days, and assuming a zero risk-free rate.</p></article><article className="data-note"><span>Dataset note</span><p>This file ends on {analysis.end_date}. Volume is zero on {analysis.zero_volume_rows.toLocaleString()} rows, so volume-based analysis should account for missing historical volume.</p></article></div>
    <div className="analysis-card table-card"><div className="chart-heading"><div><h2>Latest observations</h2><p>Most recent 12 trading days in the supplied file</p></div></div><div className="table-scroll"><table><thead><tr><th>Date</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th></tr></thead><tbody>{analysis.recent_rows.map((row) => <tr key={row.date}><td>{row.date}</td><td>{money(row.open)}</td><td>{money(row.high)}</td><td>{money(row.low)}</td><td>{money(row.close)}</td><td>{Math.round(row.volume).toLocaleString('en-US')}</td></tr>)}</tbody></table></div></div>
  </section>
}
