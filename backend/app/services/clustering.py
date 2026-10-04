"""K-means clustering of rolling SPX market-regime windows."""

from functools import lru_cache
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.services.analytics import market_frame


def _regime_label(mean_return: float, annualized_vol: float) -> str:
    """Assign a readable label from each cluster centroid's return and risk."""
    if annualized_vol >= 0.22 and mean_return >= 0.08:
        return "High-volatility advance"
    if annualized_vol >= 0.22 and mean_return < 0:
        return "High-volatility selloff"
    if mean_return >= 0.08:
        return "Steady advance"
    if mean_return <= -0.08:
        return "Declining regime"
    return "Range-bound regime"


@lru_cache(maxsize=1)
def _cluster_inputs() -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray, list[dict[str, float]]]:
    """Build window features, their 2D projection, and model-selection scores once."""
    frame = market_frame()
    returns = frame["daily_return"].to_numpy(dtype=float)
    prices = frame["price"].to_numpy(dtype=float)
    dates = frame["Date"].dt.strftime("%Y-%m-%d").to_numpy()
    rows = []
    window, step = 60, 21
    for end in range(window, len(frame) + 1, step):
        start = end - window
        segment = returns[start + 1:end]
        segment = segment[np.isfinite(segment)]
        if len(segment) < window - 2 or prices[start] <= 0:
            continue
        window_return = prices[end - 1] / prices[start] - 1
        peak = np.maximum.accumulate(prices[start:end])
        drawdown = float(np.min(prices[start:end] / peak - 1))
        rows.append({
            "start_date": dates[start], "end_date": dates[end - 1],
            "mean_return": float(np.mean(segment) * 252),
            "annualized_volatility": float(np.std(segment, ddof=1) * np.sqrt(252)),
            "window_return": float(window_return), "max_drawdown": drawdown,
        })
    features = np.asarray([[r["mean_return"], r["annualized_volatility"], r["window_return"], r["max_drawdown"]] for r in rows])
    scaled = StandardScaler().fit_transform(features)
    coordinates = PCA(n_components=2, random_state=42).fit_transform(scaled)
    scores = []
    for candidate_k in range(2, min(10, len(rows) - 1) + 1):
        candidate = KMeans(n_clusters=candidate_k, random_state=42, n_init=10).fit(scaled)
        sil = silhouette_score(scaled, candidate.labels_, sample_size=min(500, len(rows)), random_state=42)
        scores.append({"k": candidate_k, "inertia": float(candidate.inertia_), "silhouette": float(sil)})
    return rows, scaled, coordinates, scores


@lru_cache(maxsize=9)
def cluster_regimes(k: int = 4) -> dict[str, Any]:
    """Cluster overlapping 60-session periods; this sample has one index, not many stocks."""
    rows, scaled, coordinates, scores = _cluster_inputs()
    window, step = 60, 21
    if len(rows) < k:
        raise ValueError("Not enough valid 60-session windows for the requested cluster count.")
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = model.fit_predict(scaled)

    profiles = []
    for label in range(k):
        members = [row for row, cluster_id in zip(rows, labels) if int(cluster_id) == label]
        if not members:
            continue
        mean_return = float(np.mean([r["mean_return"] for r in members]))
        annualized_vol = float(np.mean([r["annualized_volatility"] for r in members]))
        profiles.append({
            "cluster_id": label,
            "label": _regime_label(mean_return, annualized_vol),
            "windows": len(members),
            "mean_annualized_return_pct": mean_return * 100,
            "mean_annualized_volatility_pct": annualized_vol * 100,
            "mean_window_return_pct": float(np.mean([r["window_return"] for r in members]) * 100),
            "mean_max_drawdown_pct": float(np.mean([r["max_drawdown"] for r in members]) * 100),
        })
    profiles.sort(key=lambda profile: profile["cluster_id"])
    points = [
        {**row, "cluster_id": int(label), "x": float(coord[0]), "y": float(coord[1])}
        for row, label, coord in zip(rows, labels, coordinates)
    ]
    return {
        "k": k, "window_sessions": window, "step_sessions": step,
        "method_note": "Windows describe SPX market regimes, not clusters of separate stocks.",
        "profiles": profiles, "points": points, "scores": scores,
    }
