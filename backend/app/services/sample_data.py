"""Read and summarize the bundled SPX CSV for the offline Explorer view."""

import csv
from functools import lru_cache
import math
from datetime import date
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from fastapi import HTTPException

SAMPLE_CSV = Path(__file__).resolve().parents[2] / "sample_data" / "SPX.csv"


@lru_cache(maxsize=1)
def load_spx_analysis() -> dict[str, Any]:
    """Return summary metrics, monthly adjusted closes, and recent daily rows."""
    if not SAMPLE_CSV.exists():
        raise HTTPException(status_code=503, detail="The offline SPX sample CSV is missing.")

    with SAMPLE_CSV.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise HTTPException(status_code=422, detail="The SPX CSV is missing required OHLCV columns.")

        rows: list[dict[str, Any]] = []
        for raw in reader:
            try:
                trading_date = date.fromisoformat(raw["Date"])
                close = float(raw.get("Adj Close") or raw["Close"])
                row = {
                    "date": trading_date.isoformat(),
                    "open": float(raw["Open"]),
                    "high": float(raw["High"]),
                    "low": float(raw["Low"]),
                    "close": float(raw["Close"]),
                    "adjusted_close": close,
                    "volume": float(raw["Volume"] or 0),
                }
            except (KeyError, TypeError, ValueError):
                continue
            if all(math.isfinite(row[key]) for key in ("open", "high", "low", "close", "adjusted_close", "volume")):
                rows.append(row)

    if len(rows) < 2:
        raise HTTPException(status_code=422, detail="The SPX CSV contains too few valid observations.")

    rows.sort(key=lambda row: row["date"])
    prices = [row["adjusted_close"] for row in rows]
    daily_returns = [current / previous - 1 for previous, current in zip(prices, prices[1:]) if previous > 0]
    years = (date.fromisoformat(rows[-1]["date"]) - date.fromisoformat(rows[0]["date"])).days / 365.25
    peak = prices[0]
    max_drawdown = 0.0
    for price in prices:
        peak = max(peak, price)
        if peak > 0:
            max_drawdown = min(max_drawdown, price / peak - 1)

    # One observation per calendar month keeps the browser chart responsive.
    monthly: dict[str, dict[str, Any]] = {}
    for row in rows:
        monthly[row["date"][:7]] = {"date": row["date"], "close": row["adjusted_close"]}

    annualized_vol = stdev(daily_returns) * math.sqrt(252) if len(daily_returns) > 1 else 0.0
    avg_return = mean(daily_returns) if daily_returns else 0.0
    total_return = prices[-1] / prices[0] - 1
    cagr = (prices[-1] / prices[0]) ** (1 / years) - 1 if years > 0 and prices[0] > 0 else 0.0
    sharpe = avg_return / stdev(daily_returns) * math.sqrt(252) if len(daily_returns) > 1 and stdev(daily_returns) > 0 else 0.0

    return {
        "symbol": "SPX",
        "dataset_name": "S&P 500 historical sample",
        "row_count": len(rows),
        "start_date": rows[0]["date"],
        "end_date": rows[-1]["date"],
        "latest_close": rows[-1]["close"],
        "total_return_pct": total_return * 100,
        "cagr_pct": cagr * 100,
        "annualized_volatility_pct": annualized_vol * 100,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_drawdown * 100,
        "zero_volume_rows": sum(row["volume"] == 0 for row in rows),
        "price_series": list(monthly.values()),
        "recent_rows": list(reversed(rows[-12:])),
    }
