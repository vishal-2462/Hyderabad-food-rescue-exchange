from fastapi import APIRouter

from app import schemas
from app.services.impact import aggregate_impact
from app.store import get_store

router = APIRouter(prefix="/impact", tags=["impact"])


@router.get("/metrics", response_model=schemas.ImpactMetrics)
def get_impact_metrics() -> schemas.ImpactMetrics:
    store = get_store()
    metrics = aggregate_impact(
        list(store.donations.values()),
        list(store.requests.values()),
        list(store.donors.values()),
        list(store.ngos.values()),
    )
    return schemas.ImpactMetrics.model_validate(metrics)
