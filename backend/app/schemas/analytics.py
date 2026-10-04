"""Validated request parameters for analytics endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class ClusterRequest(BaseModel):
    k: int = Field(default=4, ge=2, le=10)


class PatternRequest(BaseModel):
    min_support: float = Field(default=0.01, gt=0, le=0.5)
    min_confidence: float = Field(default=0.5, ge=0, le=1)
    train_ratio: float = Field(default=0.7, ge=0.5, le=0.9)
    algorithm: Literal["apriori", "fpgrowth"] = "apriori"


class SequenceRequest(BaseModel):
    min_support: float = Field(default=0.01, gt=0, le=0.5)
    window_days: int = Field(default=5, ge=3, le=5)
    train_ratio: float = Field(default=0.7, ge=0.5, le=0.9)


class BacktestRequest(PatternRequest):
    rule_id: str | None = None
    initial_capital: float = Field(default=10_000, gt=0)
    position_size_pct: float = Field(default=100, gt=0, le=100)
    holding_days: int = Field(default=5, ge=1, le=60)
    stop_loss_pct: float | None = Field(default=5.0, ge=0, le=100)
    take_profit_pct: float | None = Field(default=10.0, ge=0, le=200)
    transaction_cost_pct: float = Field(default=0.1, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)
