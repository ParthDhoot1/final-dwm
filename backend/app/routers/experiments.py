"""Save, list, retrieve, and delete local backtest experiments."""

from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.experiment import Experiment

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parameters: dict[str, Any]
    result: dict[str, Any]


def serialize(item: Experiment) -> dict[str, Any]:
    created = item.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return {"id": item.id, "name": item.name, "rule_id": item.rule_id,
            "created_at": created.isoformat(), "parameters": item.parameters, "result": item.result}


@router.get("")
def list_experiments(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [serialize(item) for item in db.query(Experiment).order_by(Experiment.created_at.desc(), Experiment.id.desc()).all()]


@router.post("", status_code=201)
def save_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    rule = payload.result.get("selected_rule")
    if not isinstance(rule, dict) or not rule.get("rule_id"):
        raise HTTPException(status_code=422, detail="A completed backtest result with a selected rule is required.")
    item = Experiment(name=payload.name.strip(), rule_id=rule["rule_id"], parameters=payload.parameters, result=payload.result)
    if not item.name:
        raise HTTPException(status_code=422, detail="Experiment name cannot be blank.")
    db.add(item)
    db.commit()
    db.refresh(item)
    return serialize(item)


@router.get("/{experiment_id}")
def get_experiment(experiment_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(Experiment, experiment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return serialize(item)


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)) -> None:
    item = db.get(Experiment, experiment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    db.delete(item)
    db.commit()
