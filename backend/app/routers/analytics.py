"""Clustering, frequent-pattern and backtesting API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas.analytics import BacktestRequest, ClusterRequest, PatternRequest, SequenceRequest
from app.services.backtesting import run_backtest
from app.services.clustering import cluster_regimes
from app.services.patterns import mine_rules
from app.services.sequences import mine_sequences

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/cluster/run")
def cluster_run(request: ClusterRequest) -> dict[str, Any]:
    """Cluster rolling 60-session SPX market-regime windows with K-means."""
    try:
        return cluster_regimes(request.k)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/patterns/mine")
def patterns_mine(request: PatternRequest) -> dict[str, Any]:
    """Mine association rules on the chronological training portion only."""
    return mine_rules(request.min_support, request.min_confidence, request.train_ratio, request.algorithm)


@router.post("/patterns/sequences")
def patterns_sequences(request: SequenceRequest) -> dict[str, Any]:
    """Mine recurring sequential signals in train-only 3–5 session windows."""
    return mine_sequences(request.min_support, request.window_days, request.train_ratio)


@router.post("/backtest/run")
def backtest_run(request: BacktestRequest) -> dict[str, Any]:
    """Backtest a training-mined rule on the held-out test period."""
    return run_backtest(request)
