from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app import models, schemas
from app.security import get_current_user, require_roles
from app.services.request_actions import approve_request_with_donation, reject_request
from app.services.state_machine import InvalidTransitionError, assert_donation_transition, assert_request_transition
from app.store import get_store

router = APIRouter(prefix="/requests", tags=["requests"])


def _assert_ngo_access(current_user: models.User, ngo_id: str) -> None:
    if current_user.profile_id != ngo_id:
        raise HTTPException(status_code=403, detail="You do not have access to this NGO account")


def _assert_donor_access(current_user: models.User, donation: models.Donation) -> None:
    if current_user.profile_id != donation.donor_id:
        raise HTTPException(status_code=403, detail="You do not have access to this donor listing")


@router.get("", response_model=list[schemas.Request])
def list_requests(status: models.RequestStatus | None = Query(default=None)) -> list[schemas.Request]:
    store = get_store()
    requests = list(store.requests.values())
    if status is not None:
        requests = [request for request in requests if request.status == status]
    return [schemas.Request.model_validate(request) for request in requests]


@router.get("/{request_id}", response_model=schemas.Request)
def get_request(request_id: str) -> schemas.Request:
    store = get_store()
    request = store.requests.get(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return schemas.Request.model_validate(request)


def _priority_from_expiry_hours(hours_to_expiry: float) -> int:
    if hours_to_expiry <= 6:
        return 5
    if hours_to_expiry <= 12:
        return 4
    return 3


@router.post("", response_model=schemas.Request, status_code=201)
def create_request(
    payload: schemas.RequestCreate | schemas.DonationRequestCreate,
    current_user: models.User = Depends(require_roles(models.UserRole.NGO)),
) -> schemas.Request:
    store = get_store()
    if payload.ngo_id not in store.ngos:
        raise HTTPException(status_code=404, detail="NGO not found")

    _assert_ngo_access(current_user, payload.ngo_id)

    ngo = store.ngos[payload.ngo_id]

    if isinstance(payload, schemas.DonationRequestCreate):
        donation = store.donations.get(payload.donation_id)
        if donation is None:
            raise HTTPException(status_code=404, detail="Donation not found")

        try:
            assert_donation_transition(
                donation.status,
                models.DonationStatus.REQUESTED,
                allow_same_state=False,
            )
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        now = datetime.now(timezone.utc)
        hours_to_expiry = max((donation.expires_at - now).total_seconds() / 3600, 0)
        donor = store.donors.get(donation.donor_id)
        request = models.Request(
            id=store.new_id("request"),
            ngo_id=payload.ngo_id,
            title=f"Request for {donation.title}",
            category=donation.category,
            quantity_needed=donation.quantity,
            unit=donation.unit,
            people_served=max(donation.meals_estimate, donation.quantity),
            priority=_priority_from_expiry_hours(hours_to_expiry),
            created_at=now,
            needed_by=donation.pickup_end,
            max_distance_km=donor.preferred_radius_km if donor is not None else 15.0,
            status=models.RequestStatus.REQUESTED,
            location=models.Location(
                area=ngo.location.area,
                address=ngo.location.address,
                city=ngo.location.city,
                lat=ngo.location.lat,
                lng=ngo.location.lng,
            ),
            meal_slot=None,
            notes=f"{ngo.name} requested the donation listing '{donation.title}'.",
            matched_donation_id=donation.id,
        )
        store.add_request(request)

        donation.status = models.DonationStatus.REQUESTED
        donation.request_id = request.id

        store.add_notification(
            audience="donor",
            recipient_id=donation.donor_id,
            title="Approval required",
            message=f"{ngo.name} requested {donation.title}. Review and approve or reject the request.",
            level=models.NotificationLevel.INFO,
        )
        store.add_notification(
            audience="ngo",
            recipient_id=ngo.id,
            title="Donation request sent",
            message=f"Your team requested {donation.title} from the live donation board.",
            level=models.NotificationLevel.SUCCESS,
        )
        return schemas.Request.model_validate(request)

    request = models.Request(
        id=store.new_id("request"),
        ngo_id=payload.ngo_id,
        title=payload.title,
        category=payload.category,
        quantity_needed=payload.quantity_needed,
        unit=payload.unit,
        people_served=payload.people_served,
        priority=payload.priority,
        created_at=datetime.now(timezone.utc),
        needed_by=payload.needed_by,
        max_distance_km=payload.max_distance_km,
        status=models.RequestStatus.OPEN,
        location=models.Location(**payload.location.model_dump()),
        meal_slot=payload.meal_slot,
        notes=payload.notes,
    )
    store.add_request(request)
    store.add_notification(
        audience="ngo",
        recipient_id=payload.ngo_id,
        title="Request opened",
        message=f"{payload.title} is now visible to matching donors.",
        level=models.NotificationLevel.INFO,
    )
    return schemas.Request.model_validate(request)


@router.post("/{request_id}/approve", response_model=schemas.Request)
def approve_request(
    request_id: str,
    payload: schemas.RequestApprovalPayload,
    current_user: models.User = Depends(require_roles(models.UserRole.DONOR)),
) -> schemas.Request:
    store = get_store()
    request = store.requests.get(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    donation_id = payload.donation_id or request.matched_donation_id
    if donation_id is None:
        raise HTTPException(status_code=400, detail="A donation_id is required to approve this request")

    donation = store.donations.get(donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    _assert_donor_access(current_user, donation)

    try:
        approve_request_with_donation(store, request, donation)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store.add_notification(
        audience="ngo",
        recipient_id=request.ngo_id,
        title="Request approved",
        message=f"Your request '{request.title}' was approved for donation '{donation.title}'.",
        level=models.NotificationLevel.SUCCESS,
    )
    store.add_notification(
        audience="donor",
        recipient_id=donation.donor_id,
        title="Request approved",
        message=f"{donation.title} has been committed to {request.title}.",
        level=models.NotificationLevel.SUCCESS,
    )
    return schemas.Request.model_validate(request)


@router.post("/{request_id}/reject", response_model=schemas.Request)
def reject_request_route(
    request_id: str,
    current_user: models.User = Depends(require_roles(models.UserRole.DONOR)),
) -> schemas.Request:
    store = get_store()
    request = store.requests.get(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.matched_donation_id is None:
        raise HTTPException(status_code=400, detail="Only donation-linked requests can be rejected directly")

    donation = store.donations.get(request.matched_donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    _assert_donor_access(current_user, donation)

    try:
        reject_request(store, request)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store.add_notification(
        audience="ngo",
        recipient_id=request.ngo_id,
        title="Request rejected",
        message=f"Your request '{request.title}' was rejected by the donor.",
        level=models.NotificationLevel.WARNING,
    )
    return schemas.Request.model_validate(request)


@router.post("/{request_id}/status", response_model=schemas.Request)
def update_request_status(
    request_id: str,
    payload: schemas.RequestStatusChange,
    _current_user: models.User = Depends(get_current_user),
) -> schemas.Request:
    store = get_store()
    request = store.requests.get(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    try:
        assert_request_transition(request.status, payload.status)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.donation_id is not None and payload.donation_id not in store.donations:
        raise HTTPException(status_code=404, detail="Donation not found")

    request.status = payload.status
    request.matched_donation_id = payload.donation_id or request.matched_donation_id
    return schemas.Request.model_validate(request)
