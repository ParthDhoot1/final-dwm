"""Sequential signal pattern discovery with PrefixSpan."""

import math
from functools import lru_cache
from typing import Any

from prefixspan import PrefixSpan

from app.services.analytics import SIGNAL_COLUMNS, SIGNAL_LABELS, chronological_split, market_frame

# If multiple signal types trigger on one date, keep the first by this fixed
# priority so same-day indicators are not given an invented within-day order.
EVENT_PRIORITY = [
    "MACD_CROSS_UP", "MACD_CROSS_DOWN", "RSI_OVERSOLD", "RSI_OVERBOUGHT",
    "BB_BREAKOUT_UP", "BB_BREAKOUT_DOWN", "VOLUME_SPIKE",
    "PRICE_ABOVE_SMA50", "PRICE_BELOW_SMA50",
]


@lru_cache(maxsize=32)
def mine_sequences(min_support: float = 0.01, window_days: int = 5, train_ratio: float = 0.7) -> dict[str, Any]:
    """Mine recurring 3–5-session event subsequences within train-only windows."""
    _, valid = chronological_split(market_frame(), train_ratio)
    split = int(len(valid) * train_ratio)
    train = valid.iloc[:max(split - 1, 0)]
    events = []
    for _, row in train.iterrows():
        event = next((signal for signal in EVENT_PRIORITY if bool(row[signal])), None)
        events.append(event)

    sequences = []
    window_ranges = []
    for start in range(max(0, len(events) - window_days + 1)):
        stop = start + window_days
        sequence = [event for event in events[start:stop] if event is not None]
        if sequence:
            sequences.append(sequence)
            window_ranges.append((start, stop))
    if not sequences:
        return {"patterns": [], "window_days": window_days, "train_rows": len(train), "sequence_windows": 0, "min_support": min_support}

    minimum_count = max(2, math.ceil(min_support * len(sequences)))
    miner = PrefixSpan(sequences)
    # The database contains at most window_days events, so patterns cannot grow
    # beyond the selected 3–5 session horizon.
    mined = miner.frequent(minimum_count)
    results = []
    for count, pattern in mined:
        if len(pattern) < 2:
            continue
        results.append({
            "sequence": list(pattern),
            "labels": [SIGNAL_LABELS.get(signal, signal) for signal in pattern],
            "support": count / len(sequences),
            "count": int(count),
        })
    results.sort(key=lambda result: (result["count"], len(result["sequence"])), reverse=True)
    return {
        "patterns": results[:50],
        "window_days": window_days,
        "train_rows": len(train),
        "sequence_windows": len(sequences),
        "min_support": min_support,
        "train_end_date": train.iloc[-1]["Date"].date().isoformat() if len(train) else None,
        "method_note": "Each window spans 3–5 consecutive trading sessions. At most one signal per day is retained by a fixed priority; same-day signals are not ordered.",
    }
