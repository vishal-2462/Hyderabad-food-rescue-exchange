from fastapi import APIRouter, HTTPException

from app import schemas
from app.store import get_store

router = APIRouter(prefix="/donors", tags=["donors"])


@router.get("", response_model=list[schemas.Donor])
def list_donors() -> list[schemas.Donor]:
    store = get_store()
    return [schemas.Donor.model_validate(donor) for donor in store.donors.values()]


@router.get("/{donor_id}", response_model=schemas.Donor)
def get_donor(donor_id: str) -> schemas.Donor:
    store = get_store()
    donor = store.donors.get(donor_id)
    if donor is None:
        raise HTTPException(status_code=404, detail="Donor not found")
    return schemas.Donor.model_validate(donor)
