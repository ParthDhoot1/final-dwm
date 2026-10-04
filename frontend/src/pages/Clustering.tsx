import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { ClusterResponse, formatPct, postJson } from '../api/analysis'

const colors = ['#5ee0b5', '#8b9cf7', '#f0b565', '#ef7f81', '#67b4e8', '#c889e9', '#d5dc7c', '#f19ec4', '#89cbb0', '#ef9657']

function ElbowChart({ scores }: { scores: ClusterResponse['scores'] }) {
  return <article className="analysis-card elbow-card"><div className="analysis-card-heading"><h2>Elbow curve</h2><span>Lower inertia is better; look for the bend</span></div><div className="elbow-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={scores} margin={{ top: 12, right: 18, bottom: 5, left: 0 }}><CartesianGrid stroke="#ffffff10" vertical={false} /><XAxis dataKey="k" tick={{ fill: '#73877d', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 9, color: '#e9f2ee', fontSize: 10 }} /><Line type="monotone" dataKey="inertia" stroke="#5ee0b5" strokeWidth={2} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div></article>
}

export default function Clustering() {
  const [k, setK] = useState(4)
  const [data, setData] = useState<ClusterResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadClusters(clusterCount = k) {
    setBusy(true); setError('')
    try { setData(await postJson<ClusterResponse>('/api/cluster/run', { k: clusterCount })) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not cluster the SPX history.') }
    finally { setBusy(false) }
  }
  useEffect(() => { void loadClusters(4) }, [])

  return <section className="analysis-page">
    <div className="analysis-page-heading"><div><p className="eyebrow">MARKETMINER / CLUSTERING</p><h1>Market regimes</h1><p>Group rolling 60-session periods by return, volatility and drawdown.</p></div><div className="cluster-controls"><label htmlFor="cluster-k">Clusters <b>{k}</b></label><input id="cluster-k" type="range" min="2" max="10" value={k} onChange={(event) => setK(Number(event.target.value))} /><button className="analysis-button" disabled={busy} onClick={() => void loadClusters()}>{busy ? 'Updating…' : 'Run clustering'}</button></div></div>
    <div className="analysis-note">This dataset contains one index, so clusters represent SPX market regimes rather than groups of different stocks. K-means uses StandardScaler and a fixed random seed; PCA projects windows to two dimensions for display.</div>
    {error && <div className="analysis-error">{error}</div>}
    {data && <>
      <div className="cluster-profile-grid">{data.profiles.map((profile) => <article className="analysis-card profile-card" key={profile.cluster_id}><div className="profile-title"><i style={{ background: colors[profile.cluster_id % colors.length] }} />Cluster {profile.cluster_id + 1}<b>{profile.label}</b></div><div className="profile-stats"><span>{profile.windows.toLocaleString()} windows</span><span>Mean return <b>{formatPct(profile.mean_annualized_return_pct)}</b></span><span>Annualized volatility <b>{profile.mean_annualized_volatility_pct.toFixed(1)}%</b></span><span>Mean 60-day drawdown <b>{profile.mean_max_drawdown_pct.toFixed(1)}%</b></span></div></article>)}</div>
      <ElbowChart scores={data.scores} />
      <div className="analysis-two-col"><article className="analysis-card"><div className="analysis-card-heading"><h2>PCA regime map</h2><span>{data.points.length} rolling windows</span></div><div className="large-chart"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 12, right: 14, bottom: 8, left: 0 }}><CartesianGrid stroke="#ffffff10" /><XAxis type="number" dataKey="x" name="PC 1" tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><YAxis type="number" dataKey="y" name="PC 2" tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 9, color: '#e9f2ee', fontSize: 10 }} formatter={(value, name) => [typeof value === 'number' ? value.toFixed(3) : value, name]} />{data.profiles.map((profile) => <Scatter key={profile.cluster_id} data={data.points.filter((point) => point.cluster_id === profile.cluster_id)} name={profile.label} fill={colors[profile.cluster_id % colors.length]} />)}</ScatterChart></ResponsiveContainer></div></article><article className="analysis-card"><div className="analysis-card-heading"><h2>Silhouette by k</h2><span>Higher is better · 0–1 scale</span></div><div className="large-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.scores} margin={{ top: 15, right: 18, bottom: 5, left: 0 }}><CartesianGrid stroke="#ffffff10" vertical={false} /><XAxis dataKey="k" tick={{ fill: '#73877d', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis domain={[-1, 1]} tick={{ fill: '#73877d', fontSize: 9 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101b18', border: '1px solid #ffffff20', borderRadius: 9, color: '#e9f2ee', fontSize: 10 }} /><Line type="monotone" dataKey="silhouette" stroke="#8b9cf7" strokeWidth={2} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div><p className="chart-caption">Selected k = {data.k}; inertia is also computed for k=2–10 by the API.</p></article></div>
    </>}
  </section>
}
