"""Endpoints that expose local sample market data."""

from typing import Any

from fastapi import APIRouter

from app.services.sample_data import load_spx_analysis

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/sample", response_model=None)
def get_sample_analysis() -> dict[str, Any]:
    """Return analysis computed from the bundled SPX historical CSV."""
    return load_spx_analysis()
