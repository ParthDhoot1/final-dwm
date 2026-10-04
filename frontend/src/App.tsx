import { lazy, Suspense, useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router-dom'

const Explorer = lazy(() => import('./pages/Explorer'))
const Clustering = lazy(() => import('./pages/Clustering'))
const Patterns = lazy(() => import('./pages/Patterns'))
const Backtest = lazy(() => import('./pages/Backtest'))
const Experiments = lazy(() => import('./pages/Experiments'))
const About = lazy(() => import('./pages/About'))

const pages = ['Explorer', 'Clustering', 'Patterns', 'Backtest', 'Experiments', 'About']
const apiBase = import.meta.env.VITE_API_URL || ''

function Landing() {
  const [health, setHealth] = useState('Checking API…')
  useEffect(() => {
    fetch(`${apiBase}/health`).then((response) => {
      if (!response.ok) throw new Error('API unavailable')
      return response.json()
    }).then((data: { status: string }) => setHealth(`API ${data.status}`))
      .catch(() => setHealth('API offline — start the backend'))
  }, [])
  return <section className="hero"><p className="eyebrow">DATA MINING · MARKET PATTERNS</p><h1>Find the shape<br />behind the <span>market.</span></h1><p className="lede">Explore stock behavior with clustering, discover recurring signals, and test strategies against history.</p><Link className="button" to="/explorer">Start analysis <span>↗</span></Link><div className="status"><i />{health}</div><div className="sparkline" aria-hidden="true">⌁ ⌁ ⌁ ⌁ ⌁ ⌁ ⌁ ⌁ ⌁</div></section>
}

export default function App() {
  return <div className="shell"><aside className="sidebar"><Link to="/" className="brand"><span className="brand-icon">M</span>market<span>miner</span></Link><p className="nav-label">WORKSPACE</p><nav><NavLink end to="/" className="nav-link">⌂ <span>Overview</span></NavLink>{pages.map((page, i) => <NavLink key={page} to={`/${page.toLowerCase()}`} className="nav-link"><b>{['◷', '◉', '⌘', '↗', '▤', 'ⓘ'][i]}</b><span>{page}</span></NavLink>)}</nav><div className="sidebar-foot"><span className="live-dot"/>Research mode<br/><small>Educational project</small></div></aside><main><header><span>Market intelligence workspace</span><span className="date">DATA MINING PROJECT <b>·</b> 2026</span></header><Suspense fallback={<section className="analysis-page"><div className="analysis-loading">Loading analysis…</div></section>}><Routes><Route path="/" element={<Landing />} /><Route path="/explorer" element={<Explorer />} /><Route path="/clustering" element={<Clustering />} /><Route path="/patterns" element={<Patterns />} /><Route path="/backtest" element={<Backtest />} /><Route path="/experiments" element={<Experiments />} /><Route path="/about" element={<About />} /><Route path="*" element={<section className="page"><p className="eyebrow">MARKETMINER / 404</p><h1>Page not found</h1><Link className="button" to="/">Return home</Link></section>} /></Routes></Suspense><footer>MarketMiner <span>For educational use only · Not financial advice</span></footer></main></div>
}
