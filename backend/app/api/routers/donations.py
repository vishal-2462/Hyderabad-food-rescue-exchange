from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app import models, schemas
from app.security import get_current_user, require_roles
from app.services.freshness_engine import infer_shelf_life_hours
from app.services.request_actions import approve_request_with_donation
from app.services.matching import rank_matches
from app.services.state_machine import InvalidTransitionError, assert_donation_transition, assert_request_transition
from app.store import get_store

router = APIRouter(prefix="/donations", tags=["donations"])


def _assert_donor_access(current_user: models.User, donation_or_donor_id: models.Donation | str) -> None:
    donor_id = donation_or_donor_id if isinstance(donation_or_donor_id, str) else donation_or_donor_id.donor_id
    if current_user.profile_id != donor_id:
        raise HTTPException(status_code=403, detail="You do not have access to this donor listing")


def _serialize_match(result) -> schemas.MatchCandidate:
    return schemas.MatchCandidate(
        request_id=result.request_id,
        ngo_id=result.ngo_id,
        request_title=result.request_title,
        ngo_name=result.ngo_name,
        total_score=result.total_score,
        distance_km=result.distance_km,
        factor_scores=schemas.MatchFactorScores(
            distance=result.factor_scores.distance,
            expiry_urgency=result.factor_scores.expiry_urgency,
            safety_window=result.factor_scores.safety_window,
            capacity=result.factor_scores.capacity,
            demand=result.factor_scores.demand,
            reliability=result.factor_scores.reliability,
        ),
        explanation=result.explanation,
    )


@router.get("", response_model=list[schemas.Donation])
def list_donations(status: models.DonationStatus | None = Query(default=None)) -> list[schemas.Donation]:
    store = get_store()
    donations = list(store.donations.values())
    if status is not None:
        donations = [donation for donation in donations if donation.status == status]
    return [schemas.Donation.model_validate(donation) for donation in donations]


@router.get("/{donation_id}", response_model=schemas.Donation)
def get_donation(donation_id: str) -> schemas.Donation:
    store = get_store()
    donation = store.donations.get(donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    return schemas.Donation.model_validate(donation)


@router.post("", response_model=schemas.Donation, status_code=201)
def create_donation(
    payload: schemas.DonationCreate,
    current_user: models.User = Depends(require_roles(models.UserRole.DONOR)),
) -> schemas.Donation:
    store = get_store()
    if payload.donor_id not in store.donors:
        raise HTTPException(status_code=404, detail="Donor not found")
    _assert_donor_access(current_user, payload.donor_id)
    if payload.pickup_start < payload.prepared_time:
        raise HTTPException(status_code=400, detail="pickup_start must be after prepared_time")
    if payload.pickup_end <= payload.pickup_start:
        raise HTTPException(status_code=400, detail="pickup_end must be after pickup_start")
    inferred_shelf_life_hours = infer_shelf_life_hours(payload.food_type, payload.storage_condition, payload.shelf_life_hours)
    derived_safe_until = payload.prepared_time + timedelta(hours=inferred_shelf_life_hours)
    expires_at = min(payload.expires_at, derived_safe_until) if payload.expires_at is not None else derived_safe_until
    if expires_at <= payload.pickup_start:
        raise HTTPException(status_code=400, detail="expires_at must be after pickup_start")

    donation = models.Donation(
        id=store.new_id("donation"),
        donor_id=payload.donor_id,
        title=payload.title,
        category=payload.category,
        food_type=payload.food_type,
        prepared_time=payload.prepared_time,
        storage_condition=payload.storage_condition,
        quantity=payload.quantity,
        unit=payload.unit,
        meals_estimate=payload.meals_estimate,
        safety_window_hours=payload.safety_window_hours,
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        pickup_start=payload.pickup_start,
        pickup_end=payload.pickup_end,
        status=models.DonationStatus.AVAILABLE,
        location=models.Location(**payload.location.model_dump()),
        shelf_life_hours=payload.shelf_life_hours,
        image_url=payload.image_url,
        image_freshness_label=payload.image_freshness_label,
        image_visual_label=payload.image_visual_label,
        image_visual_confidence=payload.image_visual_confidence,
        notes=payload.notes,
    )
    store.add_donation(donation)
    store.add_notification(
        audience="donor",
        recipient_id=payload.donor_id,
        title="Donation posted",
        message=f"{payload.title} is now available for Hyderabad NGO matching.",
        level=models.NotificationLevel.SUCCESS,
    )
    return schemas.Donation.model_validate(donation)


@router.get("/{donation_id}/matches", response_model=list[schemas.MatchCandidate])
def get_matches(donation_id: str, limit: int = Query(default=5, ge=1, le=20)) -> list[schemas.MatchCandidate]:
    store = get_store()
    donation = store.donations.get(donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    if donation.status in {models.DonationStatus.CANCELLED, models.DonationStatus.EXPIRED, models.DonationStatus.DELIVERED}:
        return []

    matches = rank_matches(donation, list(store.requests.values()), store.ngos, store.donors)
    return [_serialize_match(result) for result in matches[:limit]]


@router.post("/{donation_id}/reserve", response_model=schemas.Donation)
def reserve_donation(
    donation_id: str,
    payload: schemas.ReserveDonationRequest,
    current_user: models.User = Depends(require_roles(models.UserRole.DONOR)),
) -> schemas.Donation:
    store = get_store()
    donation = store.donations.get(donation_id)
    request = store.requests.get(payload.request_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    _assert_donor_access(current_user, donation)

    try:
        approve_request_with_donation(store, request, donation)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store.add_notification(
        audience="admin",
        title="Donation reserved",
        message=f"{donation.title} has been reserved for {request.title}.",
        level=models.NotificationLevel.SUCCESS,
    )
    return schemas.Donation.model_validate(donation)


@router.post("/{donation_id}/status", response_model=schemas.Donation)
def update_donation_status(
    donation_id: str,
    payload: schemas.DonationStatusChange,
    current_user: models.User = Depends(get_current_user),
) -> schemas.Donation:
    store = get_store()
    donation = store.donations.get(donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    if current_user.role == models.UserRole.DONOR:
        _assert_donor_access(current_user, donation)

    try:
        assert_donation_transition(donation.status, payload.status)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.request_id is not None and payload.request_id not in store.requests:
        raise HTTPException(status_code=404, detail="Request not found")

    donation.status = payload.status
    if payload.status == models.DonationStatus.REQUESTED:
        donation.request_id = payload.request_id or donation.request_id
    if payload.status == models.DonationStatus.RESERVED:
        donation.request_id = payload.request_id or donation.request_id
        donation.reserved_for_request_id = payload.request_id or donation.reserved_for_request_id
    if payload.status == models.DonationStatus.PICKED_UP:
        donation.picked_up_at = datetime.now(timezone.utc)
    if payload.status == models.DonationStatus.DELIVERED:
        donation.delivered_at = datetime.now(timezone.utc)
        if donation.request_id and donation.request_id in store.requests:
            request = store.requests[donation.request_id]
            request.status = models.RequestStatus.FULFILLED
            request.matched_donation_id = donation.id
            ngo = store.ngos.get(request.ngo_id)
            if ngo is not None:
                ngo.current_load = max(ngo.current_load - donation.quantity, 0)
    if payload.status == models.DonationStatus.AVAILABLE:
        donation.request_id = None
        donation.reserved_for_request_id = None

    return schemas.Donation.model_validate(donation)
