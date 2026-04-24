from fastapi import APIRouter, HTTPException

from app import schemas
from app.store import get_store

router = APIRouter(prefix="/ngos", tags=["ngos"])


@router.get("", response_model=list[schemas.NGO])
def list_ngos() -> list[schemas.NGO]:
    store = get_store()
    return [schemas.NGO.model_validate(ngo) for ngo in store.ngos.values()]


@router.get("/{ngo_id}", response_model=schemas.NGO)
def get_ngo(ngo_id: str) -> schemas.NGO:
    store = get_store()
    ngo = store.ngos.get(ngo_id)
    if ngo is None:
        raise HTTPException(status_code=404, detail="NGO not found")
    return schemas.NGO.model_validate(ngo)
