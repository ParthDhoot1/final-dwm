"""Shared indicator and train/test helpers for offline SPX analysis."""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.sample_data import SAMPLE_CSV

SIGNAL_COLUMNS = [
    "RSI_OVERSOLD", "RSI_OVERBOUGHT", "MACD_CROSS_UP", "MACD_CROSS_DOWN",
    "PRICE_ABOVE_SMA50", "PRICE_BELOW_SMA50", "BB_BREAKOUT_UP",
    "BB_BREAKOUT_DOWN", "VOLUME_SPIKE",
]
SIGNAL_LABELS = {
    "RSI_OVERSOLD": "RSI below 30", "RSI_OVERBOUGHT": "RSI above 70",
    "MACD_CROSS_UP": "MACD crossed above signal", "MACD_CROSS_DOWN": "MACD crossed below signal",
    "PRICE_ABOVE_SMA50": "Price above SMA 50", "PRICE_BELOW_SMA50": "Price below SMA 50",
    "BB_BREAKOUT_UP": "Close above upper Bollinger Band", "BB_BREAKOUT_DOWN": "Close below lower Bollinger Band",
    "VOLUME_SPIKE": "Volume above 1.5× its 20-day average",
}


@lru_cache(maxsize=1)
def market_frame() -> pd.DataFrame:
    """Load the sample file once and compute causal indicators for each date."""
    if not Path(SAMPLE_CSV).exists():
        raise FileNotFoundError(f"Sample data file not found: {SAMPLE_CSV}")
    frame = pd.read_csv(SAMPLE_CSV, parse_dates=["Date"])
    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(frame.columns):
        raise ValueError("SPX.csv must include Date, Open, High, Low, Close, and Volume columns.")
    frame = frame.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    close = pd.to_numeric(frame.get("Adj Close", frame["Close"]), errors="coerce").fillna(frame["Close"])
    frame["price"] = close.astype(float)
    frame["daily_return"] = frame["price"].pct_change()

    delta = frame["price"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    frame["rsi"] = 100 - (100 / (1 + rs))
    frame.loc[(loss == 0) & (gain > 0), "rsi"] = 100

    ema12 = frame["price"].ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = frame["price"].ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd"] = ema12 - ema26
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    frame["sma50"] = frame["price"].rolling(50, min_periods=50).mean()
    middle = frame["price"].rolling(20, min_periods=20).mean()
    band_std = frame["price"].rolling(20, min_periods=20).std()
    frame["bb_upper"] = middle + 2 * band_std
    frame["bb_lower"] = middle - 2 * band_std
    volume = pd.to_numeric(frame["Volume"], errors="coerce").fillna(0)
    volume_average = volume.rolling(20, min_periods=20).mean()

    frame["RSI_OVERSOLD"] = frame["rsi"] < 30
    frame["RSI_OVERBOUGHT"] = frame["rsi"] > 70
    frame["MACD_CROSS_UP"] = (frame["macd"] > frame["macd_signal"]) & (frame["macd"].shift(1) <= frame["macd_signal"].shift(1))
    frame["MACD_CROSS_DOWN"] = (frame["macd"] < frame["macd_signal"]) & (frame["macd"].shift(1) >= frame["macd_signal"].shift(1))
    frame["PRICE_ABOVE_SMA50"] = frame["price"] > frame["sma50"]
    frame["PRICE_BELOW_SMA50"] = frame["price"] < frame["sma50"]
    frame["BB_BREAKOUT_UP"] = frame["price"] > frame["bb_upper"]
    frame["BB_BREAKOUT_DOWN"] = frame["price"] < frame["bb_lower"]
    frame["VOLUME_SPIKE"] = (volume_average > 0) & (volume > 1.5 * volume_average)
    frame["NEXT_DAY_RETURN"] = frame["daily_return"].shift(-1)
    frame["NEXT_DAY_UP"] = frame["NEXT_DAY_RETURN"] > 0
    frame["NEXT_DAY_DOWN"] = frame["NEXT_DAY_RETURN"] <= 0
    return frame


def chronological_split(frame: pd.DataFrame, train_ratio: float = 0.7) -> tuple[int, pd.DataFrame]:
    """Return the split index after excluding rows lacking causal indicators."""
    valid = frame.dropna(subset=["rsi", "macd_signal", "sma50", "bb_upper", "bb_lower", "NEXT_DAY_RETURN"]).copy()
    split = int(len(valid) * train_ratio)
    return split, valid

