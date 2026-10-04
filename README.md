# MarketMiner

MarketMiner is an educational data-mining dashboard for exploring historical SPX movement patterns using the supplied offline CSV.

## Architecture

```text
Browser (React + Vite + Recharts)
   │ HTTP /health and /api/*
   ▼
FastAPI (analytics + experiment APIs)
   ├── pandas / scikit-learn / mlxtend / PrefixSpan
   ├── cached SPX CSV analysis
   └── SQLAlchemy
   ▼
SQLite (saved experiments)
```

The analysis flow is OHLCV data → technical indicators → regime clustering and signal mining → chronological holdout backtest → dashboard visualizations. The browser calls the backend through `VITE_API_URL`; the API reads settings from `.env`.

The API owns data access and analysis so the frontend stays focused on interaction and charts. SQLite is the zero-configuration local store; the database URL can be changed through environment settings without changing application code.

## Offline sample dataset

`backend/sample_data/SPX.csv` is the supplied S&P 500 historical OHLCV dataset. It contains 23,323 rows from 1927-12-30 through 2020-11-04 with `Date`, `Open`, `High`, `Low`, `Close`, `Adj Close`, and `Volume` columns. Volume is zero through 1949-12-30, so treat early volume-dependent indicator results as unavailable; this historical sample does not include recent market data. Live data fetching and caching are still part of the data module phase.

The Explorer reads this CSV through `GET /api/data/sample`. It reports full-period total return, CAGR, daily-return volatility annualized with 252 trading days, zero-risk-free-rate Sharpe ratio, maximum drawdown, a monthly adjusted-close chart, and the 12 latest OHLCV rows. The endpoint is an offline sample view and does not fetch current market data.

## Regime, pattern, and strategy analysis

- `POST /api/cluster/run` clusters overlapping 60-session SPX windows using four scaled features (annualized return, annualized volatility, window return, and maximum drawdown). K-means uses `random_state=42`; PCA coordinates and inertia/silhouette scores are returned. These are market regimes for one index, not stock groups. Automatic profile labels use the centroid's mean return and volatility.
- `POST /api/patterns/mine` builds RSI, MACD, SMA-50, Bollinger Band, and volume-spike signals and mines single- and two-signal rules for next-session up/down with Apriori or FP-Growth. Support, confidence, and lift are computed on the first 70% of the valid chronological observations; the last training row is omitted because its next-day label would cross into the holdout segment.
- `POST /api/patterns/sequences` uses PrefixSpan to find repeated signal sequences within 3–5 session windows. It uses only training data and retains at most one event per date under a documented fixed priority to avoid inventing an order among same-day signals.
- `POST /api/backtest/run` chooses a training-mined `NEXT_DAY_UP` rule and evaluates it only on the held-out segment. A signal known at day t enters at day t+1 open; stop and target checks use OHLC, with a stop assumed first if both levels are touched in the same daily candle. Trades are long-only, one position at a time, and compare with Buy & Hold using the same entry/exit friction.

The Explorer, Clustering, Patterns, and Backtest pages use these APIs and the same local dataset. Identical mining and clustering requests are cached in process. `GET /api/experiments`, `POST /api/experiments`, `GET /api/experiments/{id}`, and `DELETE /api/experiments/{id}` manage saved backtest results in SQLite. The Experiments page can review and delete saved runs; the About page explains the methods and limitations. The sample ends in 2020; this app does not fetch current market data and is not financial advice.

## Run locally

Backend (Python 3.11+):

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs and http://localhost:8000/health.

Frontend (Node.js 20+):

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally http://localhost:5173). During development, Vite proxies `/health` to the backend so the browser can call it on the same origin. Set `VITE_API_URL` in `frontend/.env.local` when the API runs elsewhere or when serving a production frontend.

## Pages

Overview, Explorer, Clustering, Patterns, Backtest, Experiments, and About are implemented. A production frontend can be built with `npm run build` from `frontend/`.
# dwm
# dwm-frontend
# final-dwm
# final-dwm
